"""Phases 2 and 3: optimize the inputs, join them, and sweep the parameters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import geoparquet_io as gpio
import pandas as pd

from uruguay_settlements.config import (
    BUILDINGS_PARQUET,
    BUILDINGS_RAW,
    INE_ASENTAMIENTOS_POPULATION,
    MIN_DWELLINGS_DEFINITION,
    PERSONS_PER_DWELLING,
    PROJECTED_CRS,
    RESIDENTIAL_SHARES,
    RNAI_PARQUET,
    URUGUAY_POPULATION,
)
from uruguay_settlements.download import active_oai_rows, parse_count

# The scenario used for the per-settlement outputs and the headline number.
# No size filter, because Overture already under-detects here and discarding
# small footprints would compound that. 0.90 residential share and 3.4 persons
# per dwelling are the middle of each sweep axis.
CENTRAL_SIZE_FILTER_LABEL = "No filter"
CENTRAL_RESIDENTIAL_SHARE = 0.90
CENTRAL_PERSONS_PER_DWELLING = 3.4


def optimize_buildings(src: Path = BUILDINGS_RAW, dest: Path = BUILDINGS_PARQUET) -> Path:
    """Rewrite the Overture extract in Hilbert order with a bbox column.

    Overture ships a bbox struct, but the S3 extract lands in whatever order
    the global parts were scanned. Hilbert ordering puts spatial neighbours in
    the same row group, so the settlement join reads a small fraction of the
    file instead of all of it.
    """
    if dest.exists():
        print(f"    cached: {dest} ({dest.stat().st_size / 1024 / 1024:,.1f} MB)")
        return dest

    gpio.read(str(src)).add_bbox().sort_hilbert().write(
        str(dest), geoparquet_version="1.1", overwrite=True
    )
    print(f"    wrote {dest.stat().st_size / 1024 / 1024:,.1f} MB -> {dest}")
    return dest


def _geometry_expr(con: duckdb.DuckDBPyConnection, path: Path, alias: str) -> str:
    """Return SQL that yields a GEOMETRY from the file's geometry column.

    Whether a GeoParquet file reads back as GEOMETRY or as a WKB blob depends
    on the writer and on the DuckDB spatial version, and both writers here are
    outside our control. Reading the declared type is cheaper than pinning
    versions.
    """
    schema = con.execute(f"DESCRIBE SELECT geometry FROM '{path}' LIMIT 0").fetchall()
    # DuckDB reports a CRS-carrying geometry as GEOMETRY('OGC:CRS84'), so match
    # the prefix rather than the whole type name.
    column_type = schema[0][1].upper()
    if column_type.startswith("GEOMETRY"):
        return f"{alias}.geometry"
    return f"ST_GeomFromWKB({alias}.geometry)"


def open_connection() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


def join_buildings_to_settlements(
    con: duckdb.DuckDBPyConnection,
    settlements: Path = RNAI_PARQUET,
    buildings: Path = BUILDINGS_PARQUET,
) -> None:
    """Build `settlement_buildings_raw`: one row per footprint per settlement.

    The bbox comparison runs first and is what makes this tractable. It rejects
    almost every building in the country with four double comparisons, and only
    the survivors pay for `ST_Intersects` on decoded polygons.
    """
    settlement_geom = _geometry_expr(con, settlements, "s")
    building_geom = _geometry_expr(con, buildings, "b")

    con.execute(
        f"""
        CREATE OR REPLACE TABLE settlements AS
        SELECT
            CAST(s."Codigo_AI" AS BIGINT)   AS codigo_ai,
            s."Nombre_AI"                   AS nombre_ai,
            s."Nombre_dep"                  AS nombre_dep,
            s."Nombre_loc"                  AS nombre_loc,
            s."Fecha_desd"                  AS fecha_desde,
            {settlement_geom}               AS geom,
            s.bbox                          AS bbox
        FROM '{settlements}' s
        """
    )

    con.execute(
        f"""
        CREATE OR REPLACE TABLE settlement_buildings_raw AS
        SELECT
            s.codigo_ai,
            ST_Area(ST_Transform({building_geom}, 'EPSG:4326', '{PROJECTED_CRS}')) AS area_m2
        FROM settlements s
        JOIN '{buildings}' b
          ON  b.bbox.xmin <= s.bbox.xmax
          AND b.bbox.xmax >= s.bbox.xmin
          AND b.bbox.ymin <= s.bbox.ymax
          AND b.bbox.ymax >= s.bbox.ymin
          AND ST_Intersects(s.geom, {building_geom})
        """
    )

    matched = con.execute("SELECT count(*) FROM settlement_buildings_raw").fetchone()[0]
    print(f"    {matched:,} footprints fall inside a settlement")


def count_by_settlement(con: duckdb.DuckDBPyConnection, min_area: int | None) -> pd.DataFrame:
    """Footprint counts per settlement under one size filter.

    Every settlement appears, including those with no footprints at all, since
    a zero is the finding rather than a missing row.
    """
    area_filter = f"AND r.area_m2 >= {min_area}" if min_area else ""
    return con.execute(
        f"""
        SELECT
            s.codigo_ai,
            s.nombre_ai,
            s.nombre_dep,
            s.nombre_loc,
            s.fecha_desde,
            count(r.area_m2) AS footprints
        FROM settlements s
        LEFT JOIN settlement_buildings_raw r
          ON r.codigo_ai = s.codigo_ai {area_filter}
        GROUP BY ALL
        """
    ).fetchdf()


def run_sweep(counts_by_filter: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Cross the three sweep axes.

    Residential share and persons per dwelling are plain multipliers on the
    national footprint total, so each size filter needs only one aggregation.
    """
    rows = []
    for label, frame in counts_by_filter.items():
        footprints = int(frame["footprints"].sum())
        for share in RESIDENTIAL_SHARES:
            dwellings = footprints * share
            for persons in PERSONS_PER_DWELLING:
                population = dwellings * persons
                rows.append(
                    {
                        "size_filter": label,
                        "residential_share": share,
                        "persons_per_dwelling": persons,
                        "footprints": footprints,
                        "est_dwellings": round(dwellings),
                        "est_population": round(population),
                        "pct_of_uruguay": population / URUGUAY_POPULATION * 100,
                        "ratio_to_ine": population / INE_ASENTAMIENTOS_POPULATION,
                    }
                )
    return pd.DataFrame(rows)


def definition_check(counts: pd.DataFrame) -> dict[str, Any]:
    """Measure detection failure against the definition itself.

    INE-PIAI defines an asentamiento as a grouping of more than 10 dwellings,
    so every settlement in the register has at least that many. Wherever
    Overture finds fewer, the footprint layer has missed buildings that are
    known to exist.
    """
    below = counts[counts["footprints"] < MIN_DWELLINGS_DEFINITION]
    empty = counts[counts["footprints"] == 0]
    return {
        "n_settlements": len(counts),
        "n_below_definition": len(below),
        "pct_below_definition": len(below) / len(counts) * 100 if len(counts) else 0.0,
        "n_zero": len(empty),
        "worst": below.nsmallest(10, "footprints")[["nombre_ai", "nombre_dep", "footprints"]],
    }


def by_departamento(counts: pd.DataFrame) -> pd.DataFrame:
    """Footprints and central-scenario estimates for each departamento."""
    grouped = (
        counts.groupby("nombre_dep", as_index=False)
        .agg(
            n_settlements=("codigo_ai", "count"),
            footprints=("footprints", "sum"),
            n_below_definition=(
                "footprints",
                lambda s: int((s < MIN_DWELLINGS_DEFINITION).sum()),
            ),
        )
        .rename(columns={"nombre_dep": "departamento"})
    )
    grouped["est_dwellings"] = (grouped["footprints"] * CENTRAL_RESIDENTIAL_SHARE).round()
    grouped["est_population"] = (grouped["est_dwellings"] * CENTRAL_PERSONS_PER_DWELLING).round()
    return grouped.sort_values("est_population", ascending=False).reset_index(drop=True)


def montevideo_validation(
    counts: pd.DataFrame, oai_rows: list[dict[str, str]]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compare footprint counts to the Montevideo Observatorio's own figures.

    Both registers code a settlement as department + CCZ + serial, inherited
    from the INE-PIAI 2006 census, so `Codigo_AI` and `id asentamiento` join
    directly. The result is reported, never fed back into the estimate: the
    Observatorio's field sheet lists satellite building counting among its own
    sources, so treating it as ground truth would be partly circular.
    """
    active = active_oai_rows(oai_rows)
    coded = [r for r in active if parse_count(r["id asentamiento"]) is not None]
    if len(coded) != len(active):
        print(f"    note: {len(active) - len(coded)} OAI rows carry no settlement code")
    oai = pd.DataFrame(
        {
            "codigo_ai": [parse_count(r["id asentamiento"]) for r in coded],
            "oai_viviendas": [parse_count(r["viviendas"]) for r in coded],
            "oai_personas": [parse_count(r["personas"]) for r in coded],
        }
    )

    montevideo = counts[counts["nombre_dep"] == "Montevideo"]
    merged = montevideo.merge(oai, on="codigo_ai", how="inner")
    merged = merged[merged["oai_viviendas"].notna() & (merged["oai_viviendas"] > 0)]
    if merged.empty:
        raise RuntimeError(
            "No Montevideo settlement joined between the RNAI and the Observatorio. "
            "Both registers are supposed to share the INE-PIAI 2006 settlement code, "
            "so an empty join means that assumption no longer holds."
        )

    merged["ratio"] = merged["footprints"] / merged["oai_viviendas"]
    merged["abs_error"] = (merged["footprints"] - merged["oai_viviendas"]).abs()

    summary = {
        "oai_active": len(active),
        "rnai_montevideo": len(montevideo),
        "matched": len(merged),
        "unmatched_oai": sorted(set(oai["codigo_ai"]) - set(montevideo["codigo_ai"])),
        "unmatched_rnai": sorted(set(montevideo["codigo_ai"]) - set(oai["codigo_ai"])),
        "footprints_total": int(merged["footprints"].sum()),
        "oai_viviendas_total": int(merged["oai_viviendas"].sum()),
        "oai_personas_total": int(merged["oai_personas"].sum()),
        "median_ratio": float(merged["ratio"].median()),
        "mean_abs_error": float(merged["abs_error"].mean()),
        "correlation": float(merged["footprints"].corr(merged["oai_viviendas"])),
        "within_25pct": int(((merged["ratio"] >= 0.75) & (merged["ratio"] <= 1.25)).sum()),
    }
    return merged, summary


def build_settlement_table(
    con: duckdb.DuckDBPyConnection,
    counts_by_filter: dict[str, pd.DataFrame],
    validation: pd.DataFrame,
) -> None:
    """Assemble the per-settlement export table inside DuckDB.

    DuckDB holds the geometry, so the frames go back in as views and the
    geometry is joined on rather than round-tripped through Python.
    """
    labels = list(counts_by_filter)
    base = counts_by_filter[labels[0]][
        ["codigo_ai", "nombre_ai", "nombre_dep", "nombre_loc", "fecha_desde", "footprints"]
    ].rename(columns={"footprints": "footprints_all"})

    for label, column in zip(labels[1:], ("footprints_min6", "footprints_min10"), strict=True):
        base = base.merge(
            counts_by_filter[label][["codigo_ai", "footprints"]].rename(
                columns={"footprints": column}
            ),
            on="codigo_ai",
        )

    base = base.merge(
        validation[["codigo_ai", "oai_viviendas", "oai_personas"]], on="codigo_ai", how="left"
    )
    base["est_dwellings"] = (base["footprints_all"] * CENTRAL_RESIDENTIAL_SHARE).round()
    base["est_population"] = (base["est_dwellings"] * CENTRAL_PERSONS_PER_DWELLING).round()
    base["meets_definition"] = base["footprints_all"] >= MIN_DWELLINGS_DEFINITION

    con.register("settlement_estimates_df", base)
    con.execute(
        """
        CREATE OR REPLACE TABLE settlement_estimates AS
        SELECT e.*, s.geom AS geometry
        FROM settlement_estimates_df e
        JOIN settlements s ON s.codigo_ai = e.codigo_ai
        ORDER BY e.nombre_dep, e.nombre_ai
        """
    )
