"""Phase 4: write the per-settlement export, the validation table, and the report."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import duckdb
import pandas as pd

from uruguay_settlements.config import (
    INE_ASENTAMIENTOS_POPULATION,
    INE_ASENTAMIENTOS_POPULATION_UNWEIGHTED,
    MIN_DWELLINGS_DEFINITION,
    OVERTURE_RELEASE,
    PERSONS_PER_DWELLING,
    URUGUAY_POPULATION,
)
from uruguay_settlements.pipeline import (
    CENTRAL_PERSONS_PER_DWELLING,
    CENTRAL_RESIDENTIAL_SHARE,
    CENTRAL_SIZE_FILTER_LABEL,
)


def write_geojson(con: duckdb.DuckDBPyConnection, path) -> None:
    """Export the per-settlement table, geometry included."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        COPY (SELECT * FROM settlement_estimates)
        TO '{path}' WITH (FORMAT GDAL, DRIVER 'GeoJSON')
        """
    )
    print(f"    wrote {path}")


def write_validation_csv(validation: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "codigo_ai",
        "nombre_ai",
        "nombre_loc",
        "footprints",
        "oai_viviendas",
        "oai_personas",
        "ratio",
        "abs_error",
    ]
    validation[columns].sort_values("oai_viviendas", ascending=False).to_csv(path, index=False)
    print(f"    wrote {path}")


def _table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join("---" for _ in headers) + "|")
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(out) + "\n\n"


def write_summary(
    path,
    *,
    sweep: pd.DataFrame,
    departamentos: pd.DataFrame,
    definition: dict[str, Any],
    validation_summary: dict[str, Any],
    oai_summary: dict[str, Any],
    coverage: pd.DataFrame,
    settlement_count: int,
) -> None:
    """Write the markdown report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    central = sweep[
        (sweep["residential_share"] == CENTRAL_RESIDENTIAL_SHARE)
        & (sweep["persons_per_dwelling"] == CENTRAL_PERSONS_PER_DWELLING)
        & (sweep["size_filter"] == CENTRAL_SIZE_FILTER_LABEL)
    ].iloc[0]

    lines: list[str] = []
    add = lines.append

    add("# Uruguay informal settlement population estimates\n\n")
    add(f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')} UTC ")
    add(f"from Overture Maps release {OVERTURE_RELEASE} and the RNAI 2024 register.\n\n")

    # ---------------------------------------------------------------- headline
    add("## Headline\n\n")
    add(
        f"Overture finds **{int(central['footprints']):,} building footprints** inside "
        f"Uruguay's {settlement_count} registered asentamientos irregulares. At "
        f"{CENTRAL_RESIDENTIAL_SHARE:.0%} residential share and "
        f"{CENTRAL_PERSONS_PER_DWELLING} persons per dwelling, that implies "
        f"**{int(central['est_population']):,} people**, "
        f"{central['pct_of_uruguay']:.2f}% of Uruguay's population.\n\n"
    )
    add(
        f"INE's reweighted Censo 2023 puts {INE_ASENTAMIENTOS_POPULATION:,} people in "
        f"asentamientos, 5.5% of the population. The footprint estimate is "
        f"**{central['ratio_to_ine']:.2f}x** that figure. Before the May 2026 "
        f"reweighting, INE's own number was {INE_ASENTAMIENTOS_POPULATION_UNWEIGHTED:,}, "
        "so the official count moved by 22% in one revision.\n\n"
    )

    # ------------------------------------------------------------- sensitivity
    add("## Sensitivity\n\n")
    add(
        "The sweep covers three footprint size filters, four residential shares, and "
        "three persons-per-dwelling values. Only the persons-per-dwelling values have "
        "a Uruguayan citation for every value; see `docs/methodology.md`.\n\n"
    )
    add(
        _table(
            [
                "Size filter",
                "Residential share",
                "Persons/dwelling",
                "Footprints",
                "Est. dwellings",
                "Est. population",
                "% of Uruguay",
                "vs INE",
            ],
            [
                [
                    row["size_filter"],
                    f"{row['residential_share']:.0%}",
                    f"{row['persons_per_dwelling']}",
                    f"{int(row['footprints']):,}",
                    f"{int(row['est_dwellings']):,}",
                    f"{int(row['est_population']):,}",
                    f"{row['pct_of_uruguay']:.2f}%",
                    f"{row['ratio_to_ine']:.2f}x",
                ]
                for _, row in sweep.iterrows()
            ],
        )
    )
    add(
        f"**Range:** {int(sweep['est_population'].min()):,} to "
        f"{int(sweep['est_population'].max()):,} people "
        f"({sweep['ratio_to_ine'].min():.2f}x to {sweep['ratio_to_ine'].max():.2f}x INE).\n\n"
    )

    inert = [
        label
        for label, footprints in sweep.groupby("size_filter")["footprints"].first().items()
        if label != CENTRAL_SIZE_FILTER_LABEL
        and footprints
        == sweep[sweep["size_filter"] == CENTRAL_SIZE_FILTER_LABEL]["footprints"].iloc[0]
    ]
    if inert:
        add(
            f"The {' and '.join(inert)} filter removes nothing: the smallest Overture "
            f"footprint inside any settlement is already above that cutoff. Overture "
            f"does not carry the sub-6 m2 structures a size filter is meant to catch, "
            f"which is one reason it under-detects here.\n\n"
        )

    # -------------------------------------------------------- definition check
    add("## Detection check against the definition\n\n")
    add(
        "INE-PIAI defines an asentamiento as a grouping of more than 10 dwellings, so "
        "every settlement in the register has at least that many. Wherever Overture "
        "finds fewer, the footprint layer has missed buildings known to exist. This establishes "
        "only a minimum undercount.\n\n"
    )
    add(
        _table(
            ["Metric", "Value"],
            [
                ["Settlements", f"{definition['n_settlements']:,}"],
                [
                    f"Fewer than {MIN_DWELLINGS_DEFINITION} footprints",
                    f"{definition['n_below_definition']:,} "
                    f"({definition['pct_below_definition']:.1f}%)",
                ],
                ["No footprints at all", f"{definition['n_zero']:,}"],
            ],
        )
    )
    if len(definition["worst"]):
        add("Worst detected:\n\n")
        add(
            _table(
                ["Settlement", "Departamento", "Footprints"],
                [
                    [str(r["nombre_ai"]), str(r["nombre_dep"]), str(int(r["footprints"]))]
                    for _, r in definition["worst"].iterrows()
                ],
            )
        )

    # ------------------------------------------------------- montevideo check
    add("## Montevideo validation\n\n")
    add(
        "The Observatorio de Asentamientos Irregulares publishes dwelling and person "
        "counts for each active Montevideo settlement. The national estimate excludes these "
        "estimate: the Observatorio's field sheet lists satellite building counting "
        "among its own sources, so calibrating on them would be partly circular. They "
        "show where footprint counting agrees with a register built from field work "
        "plus administrative and imagery sources.\n\n"
    )
    add(
        _table(
            ["Metric", "Value"],
            [
                ["OAI active settlements", f"{validation_summary['oai_active']:,}"],
                ["RNAI Montevideo polygons", f"{validation_summary['rnai_montevideo']:,}"],
                ["Joined on settlement code", f"{validation_summary['matched']:,}"],
                ["Overture footprints", f"{validation_summary['footprints_total']:,}"],
                ["OAI viviendas", f"{validation_summary['oai_viviendas_total']:,}"],
                ["OAI personas", f"{validation_summary['oai_personas_total']:,}"],
                ["Median footprints / viviendas", f"{validation_summary['median_ratio']:.2f}"],
                ["Mean absolute error", f"{validation_summary['mean_abs_error']:.1f} dwellings"],
                ["Correlation", f"{validation_summary['correlation']:.3f}"],
                [
                    "Within 25% of OAI",
                    f"{validation_summary['within_25pct']:,} of {validation_summary['matched']:,}",
                ],
            ],
        )
    )
    add(
        f"Across those settlements the OAI implies "
        f"{oai_summary['persons_per_dwelling']:.2f} persons per dwelling "
        f"({oai_summary['people']:,} people in {oai_summary['dwellings']:,} dwellings), "
        "which is the 3.55 value in the sweep.\n\n"
    )
    if validation_summary["unmatched_oai"] or validation_summary["unmatched_rnai"]:
        add(
            f"Unmatched codes: {len(validation_summary['unmatched_oai'])} in the OAI "
            f"only, {len(validation_summary['unmatched_rnai'])} in the RNAI only.\n\n"
        )

    # ------------------------------------------------------------ departamento
    add("## By departamento\n\n")
    add(
        f"Central scenario: no size filter, {CENTRAL_RESIDENTIAL_SHARE:.0%} residential "
        f"share, {CENTRAL_PERSONS_PER_DWELLING} persons per dwelling.\n\n"
    )
    add(
        _table(
            [
                "Departamento",
                "Settlements",
                "Footprints",
                "Est. dwellings",
                "Est. population",
                "Below definition",
            ],
            [
                [
                    str(r["departamento"]),
                    f"{int(r['n_settlements']):,}",
                    f"{int(r['footprints']):,}",
                    f"{int(r['est_dwellings']):,}",
                    f"{int(r['est_population']):,}",
                    f"{int(r['n_below_definition']):,}",
                ]
                for _, r in departamentos.iterrows()
            ],
        )
    )

    # ------------------------------------------------------ attribute coverage
    add("## What Overture does not carry here\n\n")
    add(
        "This data cannot support the vertical-density or building-type analyses from "
        "the Argentine work. Measured attribute coverage explains why.\n\n"
    )
    add(
        _table(
            ["Attribute", "All Uruguay", "Inside settlements"],
            [
                [
                    str(row["attribute"]),
                    f"{int(row['national']):,} ({row['national_pct']:.2f}%)",
                    f"{int(row['in_settlements']):,} ({row['in_settlements_pct']:.2f}%)",
                ]
                for _, row in coverage.iterrows()
            ],
        )
    )
    add(
        "Overture reports height for no building inside a Uruguayan settlement, so there is no "
        "vertical-density analysis to run. `subtype` is almost entirely absent too, "
        "so the residential share stays a declared assumption: Overture "
        "cannot say which of these footprints are dwellings.\n\n"
    )

    # ------------------------------------------------------------- parameters
    add("## Parameters\n\n")
    add(
        _table(
            ["Persons per dwelling", "Basis"],
            [[str(k), v] for k, v in PERSONS_PER_DWELLING.items()],
        )
    )
    add(
        f"Uruguay's population is {URUGUAY_POPULATION:,} (INE, Censo 2023). Residential "
        "share is a declared assumption with no Uruguayan source behind it; the sweep "
        "exists because of that.\n\n"
    )

    add("---\n\n")
    add("Generated by `uruguay-settlements estimate`. Sources in `docs/sources.md`.\n")

    path.write_text("".join(lines), encoding="utf-8")
    print(f"    wrote {path}")
