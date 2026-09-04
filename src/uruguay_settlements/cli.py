"""Entrypoint. Runs the four phases with per-phase timing."""

from __future__ import annotations

import argparse
import time
from contextlib import contextmanager

from uruguay_settlements.config import (
    BUILDING_SIZE_FILTERS,
    OUTPUT_GEOJSON,
    OUTPUT_MD,
    OUTPUT_VALIDATION,
)
from uruguay_settlements.download import (
    download_oai,
    download_rnai,
    extract_overture_buildings,
    summarise_oai,
)
from uruguay_settlements.pipeline import (
    attribute_coverage,
    build_settlement_table,
    by_departamento,
    count_by_settlement,
    definition_check,
    join_buildings_to_settlements,
    montevideo_validation,
    open_connection,
    optimize_buildings,
    run_sweep,
)
from uruguay_settlements.report import write_geojson, write_summary, write_validation_csv

TIMINGS: dict[str, float] = {}


@contextmanager
def timed(label: str):
    """Time a pipeline phase, record it, and report start and finish."""
    print(f"\n> {label} ...")
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    TIMINGS[label] = elapsed
    print(f"  {label} done in {elapsed:,.1f}s")


def estimate() -> None:
    pipeline_start = time.perf_counter()

    with timed("Download RNAI settlement register"):
        settlement_count = download_rnai()

    with timed("Download Montevideo Observatorio counts"):
        oai_rows = download_oai()
        oai_summary = summarise_oai(oai_rows)
        print(
            f"    {oai_summary['n_settlements']} active settlements, "
            f"{oai_summary['dwellings']:,} viviendas, {oai_summary['people']:,} personas "
            f"({oai_summary['persons_per_dwelling']:.2f} per dwelling)"
        )
        if not oai_summary["matches_expected"]:
            print("    note: active count differs from the 345 the RNAI report documents")

    with timed("Extract Overture buildings for Uruguay"):
        extract_overture_buildings()

    with timed("Optimize buildings (bbox + Hilbert)"):
        optimize_buildings()

    with timed("Join footprints to settlements"):
        con = open_connection()
        join_buildings_to_settlements(con)

    with timed("Count, sweep, and validate"):
        counts_by_filter = {
            label: count_by_settlement(con, min_area) for min_area, label in BUILDING_SIZE_FILTERS
        }
        unfiltered = counts_by_filter["No filter"]

        sweep = run_sweep(counts_by_filter)
        definition = definition_check(unfiltered)
        departamentos = by_departamento(unfiltered)
        validation, validation_summary = montevideo_validation(unfiltered, oai_rows)
        coverage = attribute_coverage(con)

        print(
            f"    {definition['n_below_definition']} of {definition['n_settlements']} "
            f"settlements fall below the 10-dwelling definition"
        )
        print(
            f"    Montevideo: {validation_summary['matched']} settlements joined, "
            f"median footprints/viviendas {validation_summary['median_ratio']:.2f}"
        )

    with timed("Export GeoJSON, CSV, and summary"):
        build_settlement_table(con, counts_by_filter, validation)
        write_geojson(con, OUTPUT_GEOJSON)
        write_validation_csv(validation, OUTPUT_VALIDATION)
        write_summary(
            OUTPUT_MD,
            sweep=sweep,
            departamentos=departamentos,
            definition=definition,
            validation_summary=validation_summary,
            oai_summary=oai_summary,
            coverage=coverage,
            settlement_count=settlement_count,
        )
        con.close()

    total = time.perf_counter() - pipeline_start
    width = max(len(label) for label in TIMINGS)
    print("\n" + "=" * (width + 24))
    print("TIMING")
    print("=" * (width + 24))
    for label, elapsed in TIMINGS.items():
        print(f"  {label:<{width}}  {elapsed:8,.1f}s  ({elapsed / total:4.0%})")
    print("-" * (width + 24))
    print(f"  {'TOTAL':<{width}}  {total:8,.1f}s")

    print("\nOutputs:")
    for path in (OUTPUT_MD, OUTPUT_GEOJSON, OUTPUT_VALIDATION):
        print(f"  {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="uruguay-settlements",
        description=(
            "Estimate the population of Uruguay's informal settlements from Overture "
            "building footprints and the national RNAI register."
        ),
    )
    parser.add_subparsers(dest="command", required=True).add_parser(
        "estimate", help="run the full pipeline"
    )
    parser.parse_args()
    estimate()
