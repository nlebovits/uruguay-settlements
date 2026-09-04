"""The sweep and the breakdowns are plain arithmetic over footprint counts.
They are also where a silent off-by-one would quietly change a headline
number, so they are pinned here."""

from __future__ import annotations

import pandas as pd
import pytest

from uruguay_settlements.config import (
    INE_ASENTAMIENTOS_POPULATION,
    PERSONS_PER_DWELLING,
    RESIDENTIAL_SHARES,
    URUGUAY_POPULATION,
)
from uruguay_settlements.pipeline import (
    CENTRAL_PERSONS_PER_DWELLING,
    CENTRAL_RESIDENTIAL_SHARE,
    by_departamento,
    definition_check,
    run_sweep,
)


def counts(**footprints_by_name: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "codigo_ai": list(range(len(footprints_by_name))),
            "nombre_ai": list(footprints_by_name),
            "nombre_dep": ["Montevideo"] * len(footprints_by_name),
            "nombre_loc": ["Montevideo"] * len(footprints_by_name),
            "fecha_desde": [2000] * len(footprints_by_name),
            "footprints": list(footprints_by_name.values()),
        }
    )


def test_sweep_covers_every_combination():
    frames = {"No filter": counts(a=100), ">=6 m2": counts(a=90)}
    sweep = run_sweep(frames)
    assert len(sweep) == 2 * len(RESIDENTIAL_SHARES) * len(PERSONS_PER_DWELLING)


def test_sweep_arithmetic():
    sweep = run_sweep({"No filter": counts(a=600, b=400)})
    row = sweep[(sweep["residential_share"] == 0.90) & (sweep["persons_per_dwelling"] == 3.4)].iloc[
        0
    ]
    assert row["footprints"] == 1000
    assert row["est_dwellings"] == 900
    assert row["est_population"] == pytest.approx(3060)
    assert row["pct_of_uruguay"] == pytest.approx(3060 / URUGUAY_POPULATION * 100)
    assert row["ratio_to_ine"] == pytest.approx(3060 / INE_ASENTAMIENTOS_POPULATION)


def test_full_occupancy_row_is_the_raw_footprint_count():
    sweep = run_sweep({"No filter": counts(a=1000)})
    row = sweep[(sweep["residential_share"] == 1.00) & (sweep["persons_per_dwelling"] == 3.4)].iloc[
        0
    ]
    assert row["est_dwellings"] == 1000


def test_definition_check_counts_settlements_below_ten():
    frame = counts(a=0, b=3, c=9, d=10, e=250)
    result = definition_check(frame)
    assert result["n_settlements"] == 5
    assert result["n_below_definition"] == 3
    assert result["n_zero"] == 1
    assert result["pct_below_definition"] == pytest.approx(60.0)
    assert list(result["worst"]["footprints"]) == [0, 3, 9]


def test_definition_check_on_a_fully_detected_register():
    result = definition_check(counts(a=10, b=40))
    assert result["n_below_definition"] == 0
    assert len(result["worst"]) == 0


def test_by_departamento_uses_the_central_scenario():
    frame = counts(a=100, b=200)
    frame.loc[1, "nombre_dep"] = "Canelones"
    grouped = by_departamento(frame)
    canelones = grouped[grouped["departamento"] == "Canelones"].iloc[0]
    expected_dwellings = round(200 * CENTRAL_RESIDENTIAL_SHARE)
    assert canelones["est_dwellings"] == expected_dwellings
    assert canelones["est_population"] == round(expected_dwellings * CENTRAL_PERSONS_PER_DWELLING)
    # Ordered by population, so the larger departamento leads.
    assert grouped.iloc[0]["departamento"] == "Canelones"
