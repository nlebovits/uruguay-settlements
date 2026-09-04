"""Constants, paths, and data sources.

Every demographic figure here comes from a Uruguayan source and carries its
citation in the comment above it. `docs/sources.md` holds the full reference
list with access dates. Nothing in this file is inherited from the Argentine
analysis this work replicates; see `docs/differences-from-argentina.md`.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"

# Phase 1 downloads. The RNAI arrives already optimized, since gpio's
# ArcGIS extractor writes GeoParquet directly and a GeoJSON staging copy
# would only be thrown away.
OAI_CSV = DATA_DIR / "montevideo_oai_2026-04.csv"
BUILDINGS_RAW = DATA_DIR / "buildings_ury_raw.parquet"

# Phase 2 optimized GeoParquet
RNAI_PARQUET = DATA_DIR / "rnai_2024.parquet"
BUILDINGS_PARQUET = DATA_DIR / "buildings_ury.parquet"

# Phase 4 outputs
OUTPUT_GEOJSON = RESULTS_DIR / "settlement_estimates.geojson"
OUTPUT_MD = RESULTS_DIR / "settlement_analysis_summary.md"
OUTPUT_VALIDATION = RESULTS_DIR / "montevideo_validation.csv"

# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #

# Registro Nacional de Asentamientos Irregulares, active settlements at
# 2024-12-31. DINISU - MVOT. The service returns all features in one request:
# maxRecordCount is 2000 and the layer holds 667 polygons.
RNAI_SERVICE_URL = (
    "https://sit.mvot.gub.uy/arcgis/rest/services/05_MVOT/HABITAT_Y_VIVIENDA/MapServer/2"
)

# Observatorio de Asentamientos Irregulares, Intendencia de Montevideo.
# Per-settlement dwelling and person estimates, April 2026 release.
OAI_CSV_URL = (
    "https://ckan-data.montevideo.gub.uy/dataset/"
    "d35210d3-5e31-4c42-8903-dc4974509902/resource/"
    "b5d67559-feb9-4a25-bca1-deb0c2f4c337/download/"
    "asentamientos_en_montevideo_abril_2026.csv"
)

# Overture Maps buildings, release 2026-08-19.0, read straight from the
# public bucket. Catalogued at github.com/nlebovits/overture-portolan.
OVERTURE_RELEASE = "2026-08-19.0"
OVERTURE_BUILDINGS_GLOB = (
    f"s3://overturemaps-us-west-2/release/{OVERTURE_RELEASE}"
    "/theme=buildings/type=building/*.parquet"
)

# Uruguay's mainland bounding box, with a margin. Used as a containment filter
# on Overture's bbox struct so DuckDB prunes row groups instead of reading the
# global buildings layer.
URUGUAY_BBOX = (-58.55, -35.10, -53.00, -30.05)

# UTM 21S covers all of Uruguay. Footprint areas are computed here, since
# EPSG:4326 areas are in square degrees and meaningless for a size filter.
PROJECTED_CRS = "EPSG:32721"

# --------------------------------------------------------------------------- #
# Uruguayan demographic parameters
# --------------------------------------------------------------------------- #

# Persons per dwelling inside asentamientos.
#
#   3.4  Last national measurement. PMB-UEM (2012), Cuadro 5, from Censo 2011:
#        48,708 viviendas and 165,271 personas across 589 settlements. The same
#        table gives 3.6 for 2006, so the series was already falling.
#   3.55 Implied by the Montevideo Observatorio de Asentamientos, April 2026:
#        132,874 personas / 37,413 viviendas across its 345 active settlements.
#   3.0  The 2011 national figure carried forward on the national trend in
#        household size, which fell from 2.82 (Censo 2011) to 2.5 (Censo 2023).
#        3.4 x (2.5 / 2.82) = 3.01.
#
# The three bracket the plausible range. None is a national measurement for
# 2026, because Uruguay has not published one.
PERSONS_PER_DWELLING = {
    3.0: "2011 national figure scaled by the fall in household size to 2023",
    3.4: "PMB-UEM 2012, Cuadro 5, from Censo 2011",
    3.55: "Implied by Montevideo OAI, April 2026",
}

# Fraction of footprints inside a settlement that are dwellings rather than
# sheds, outbuildings, or shops. This is a declared assumption, not a citation.
# No Uruguayan source publishes it. The sweep shows how much the answer moves.
RESIDENTIAL_SHARES = [0.85, 0.90, 0.95, 1.00]

# Footprint area cutoffs, in square metres, carried over from the Argentine
# analysis. They are generic noise filters, not country-specific parameters.
BUILDING_SIZE_FILTERS: list[tuple[int | None, str]] = [
    (None, "No filter"),
    (6, ">=6 m2"),
    (10, ">=10 m2"),
]

# INE, Censo 2023. Total population of Uruguay.
URUGUAY_POPULATION = 3_499_451

# INE, weighted Censo 2023 microdata, published 2026-05-14. The weighting
# corrected an estimated 10.3% census omission that fell hardest on low-income
# households. People in asentamientos rose from 158,727 (4.5% of the
# population) to 193,260 (5.5%).
INE_ASENTAMIENTOS_POPULATION = 193_260
INE_ASENTAMIENTOS_POPULATION_UNWEIGHTED = 158_727

# INE-PIAI (2006), quoted verbatim in the RNAI 2024 methodology report: an
# asentamiento is a grouping "a partir de 10 viviendas". A settlement with
# fewer than 10 footprints therefore signals under-detection by Overture, not
# a genuinely small settlement.
MIN_DWELLINGS_DEFINITION = 10

# Counts published in the RNAI 2024 report, used as load-bearing assertions in
# the pipeline rather than as decoration.
RNAI_EXPECTED_SETTLEMENTS = 667
OAI_EXPECTED_ACTIVE = 345

# Montevideo OAI `estado` values that mean the settlement is no longer active.
# The remaining values leave exactly the 345 settlements the RNAI report counts
# for Montevideo.
OAI_INACTIVE_STATES = frozenset({"Regularizado", "Relocalizado", "Dimensión dominial resuelta"})
