"""The Montevideo Observatorio CSV drives the validation table, so the filter
that decides which settlements are still active has to be exactly right."""

from __future__ import annotations

import pytest

from uruguay_settlements.download import (
    active_oai_rows,
    parse_count,
    summarise_oai,
)


def row(estado: str, viviendas: str = "", personas: str = "") -> dict[str, str]:
    return {"estado": estado, "viviendas": viviendas, "personas": personas}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("120", 120),
        ("1.234", 1234),
        ("  87  ", 87),
        ("", None),
        ("   ", None),
        (None, None),
        ("no data", None),
    ],
)
def test_parse_count(raw, expected):
    assert parse_count(raw) == expected


def test_active_rows_drop_settlements_that_left_the_register():
    rows = [
        row("Sin intervención prevista", "100", "340"),
        row("Con intervención parcial", "50", "170"),
        row("Regularizado"),
        row("Relocalizado"),
        row("Dimensión dominial resuelta"),
        row("En proceso de Regularización", "20", "68"),
    ]
    active = active_oai_rows(rows)
    assert len(active) == 3
    assert {r["estado"] for r in active} == {
        "Sin intervención prevista",
        "Con intervención parcial",
        "En proceso de Regularización",
    }


def test_active_rows_tolerate_surrounding_whitespace():
    assert active_oai_rows([row("  Regularizado  ")]) == []


def test_summarise_computes_persons_per_dwelling():
    rows = [
        row("Sin intervención prevista", "100", "340"),
        row("Con intervención parcial", "100", "370"),
        row("Regularizado"),
    ]
    summary = summarise_oai(rows)
    assert summary["n_settlements"] == 2
    assert summary["dwellings"] == 200
    assert summary["people"] == 710
    assert summary["persons_per_dwelling"] == pytest.approx(3.55)
    assert summary["matches_expected"] is False


def test_summarise_survives_a_register_with_no_counts():
    summary = summarise_oai([row("Regularizado")])
    assert summary["dwellings"] == 0
    assert summary["persons_per_dwelling"] is None
