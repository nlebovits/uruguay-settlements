"""Phase 1: fetch the three inputs, cached on disk.

Two of the three are small and arrive in seconds. The Overture extract is the
slow one: DuckDB reads the footer of every part file in the global buildings
layer before it can prune, so the first run costs tens of minutes and every
run after that reads the cached parquet.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import duckdb
import geoparquet_io as gpio
import requests

from uruguay_settlements.config import (
    BUILDINGS_RAW,
    OAI_CSV,
    OAI_CSV_URL,
    OAI_EXPECTED_ACTIVE,
    OAI_INACTIVE_STATES,
    OVERTURE_BUILDINGS_GLOB,
    RNAI_EXPECTED_SETTLEMENTS,
    RNAI_PARQUET,
    RNAI_SERVICE_URL,
    URUGUAY_BBOX,
)

USER_AGENT = "uruguay-settlements/0.1 (+https://github.com/nlebovits/uruguay-settlements)"


def download_rnai(dest: Path = RNAI_PARQUET) -> int:
    """Fetch the RNAI 2024 active-settlement polygons as optimized GeoParquet.

    `gpio.extract_arcgis` pages the service and reprojects to EPSG:4326; the
    chained calls add the bbox column and Hilbert order that let DuckDB prune
    row groups during the spatial join. Returns the settlement count.

    The register is updated over time, so a count other than 667 is reported
    rather than raised. The analysis still runs, and the report says what it
    ran on.
    """
    if dest.exists():
        count = duckdb.sql(f"SELECT count(*) FROM '{dest}'").fetchone()[0]
        print(f"    cached: {dest} ({count} settlements)")
        return int(count)

    table = gpio.extract_arcgis(RNAI_SERVICE_URL, output_crs="EPSG:4326")
    count = table.num_rows
    if count == 0:
        raise RuntimeError(f"RNAI service returned no features: {RNAI_SERVICE_URL}")
    if count != RNAI_EXPECTED_SETTLEMENTS:
        print(
            f"    note: {count} settlements, not the {RNAI_EXPECTED_SETTLEMENTS} "
            "the 2024 report documents"
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    table.add_bbox().sort_hilbert().write(str(dest), geoparquet_version="1.1", overwrite=True)
    print(f"    saved {dest.stat().st_size:,} bytes -> {dest} ({count} settlements)")
    return count


def download_oai(dest: Path = OAI_CSV) -> list[dict[str, str]]:
    """Fetch the Montevideo Observatorio de Asentamientos CSV, April 2026."""
    if dest.exists():
        print(f"    cached: {dest}")
    else:
        response = requests.get(OAI_CSV_URL, headers={"User-Agent": USER_AGENT}, timeout=300)
        response.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(response.content)
        print(f"    saved {len(response.content):,} bytes -> {dest}")
    return read_oai_rows(dest)


def read_oai_rows(path: Path = OAI_CSV) -> list[dict[str, str]]:
    """Parse the OAI CSV. Kept separate from the download so tests can call it."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def active_oai_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the settlements that still meet the definition.

    Regularised, relocated, and tenure-resolved settlements have left the
    register, and the OAI leaves their dwelling and person fields empty. What
    remains should be the 345 active settlements the RNAI 2024 report counts
    for Montevideo.
    """
    return [row for row in rows if row["estado"].strip() not in OAI_INACTIVE_STATES]


def parse_count(raw: str | None) -> int | None:
    """Read an OAI count field. Blank and unparseable values become None."""
    if raw is None:
        return None
    text = raw.strip().replace(".", "").replace(",", ".")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def summarise_oai(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Totals for the active Montevideo settlements, with the implied ratio."""
    active = active_oai_rows(rows)
    dwellings = sum(parse_count(r["viviendas"]) or 0 for r in active)
    people = sum(parse_count(r["personas"]) or 0 for r in active)
    return {
        "n_settlements": len(active),
        "dwellings": dwellings,
        "people": people,
        "persons_per_dwelling": people / dwellings if dwellings else None,
        "matches_expected": len(active) == OAI_EXPECTED_ACTIVE,
    }


def extract_overture_buildings(dest: Path = BUILDINGS_RAW) -> Path:
    """Cut Uruguay out of the global Overture buildings layer.

    The filter is a containment test on Overture's `bbox` struct rather than a
    geometry predicate. Comparing four doubles lets DuckDB drop row groups from
    the parquet footer statistics without decoding any WKB.
    """
    if dest.exists():
        print(f"    cached: {dest} ({dest.stat().st_size / 1024 / 1024:,.1f} MB)")
        return dest

    xmin, ymin, xmax, ymax = URUGUAY_BBOX
    print(f"    reading {OVERTURE_BUILDINGS_GLOB}")
    print("    this reads the footer of every global part file; expect tens of minutes")

    dest.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.execute("SET s3_region='us-west-2'")
    con.execute("SET preserve_insertion_order=false")
    con.execute(
        f"""
        COPY (
            SELECT id, subtype, class, num_floors, height, bbox, geometry
            FROM read_parquet('{OVERTURE_BUILDINGS_GLOB}', hive_partitioning=false)
            WHERE bbox.xmin > {xmin} AND bbox.xmax < {xmax}
              AND bbox.ymin > {ymin} AND bbox.ymax < {ymax}
        ) TO '{dest}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    con.close()

    print(f"    saved {dest.stat().st_size / 1024 / 1024:,.1f} MB -> {dest}")
    return dest
