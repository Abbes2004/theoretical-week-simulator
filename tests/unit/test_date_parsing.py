"""Unit tests for src/business/date_parsing.py and src/business/iso_week.py.

docs/execution/13_testing_strategy.md, "Unit": "date parsing", "week
conversion".
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from business.date_parsing import parse_date  # noqa: E402
from business.iso_week import IsoWeek  # noqa: E402


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, None),
        ("", None),
        ("2025-08-04", date(2025, 8, 4)),
        ("04/08/2025", date(2025, 8, 4)),
        (date(2025, 8, 4), date(2025, 8, 4)),
    ],
)
def test_parse_date_valid_inputs(raw, expected):
    result = parse_date(raw)
    assert result.is_valid is True
    assert result.value == expected


@pytest.mark.parametrize("raw", ["2025-99-40", "31/31/2025", "ABC", "0000-00-00"])
def test_parse_date_invalid_inputs(raw):
    result = parse_date(raw)
    assert result.is_valid is False
    assert result.value is None
    assert result.reason is not None


def test_parse_date_nan_is_treated_as_missing():
    result = parse_date(float("nan"))
    assert result.is_valid is True
    assert result.value is None


def test_iso_week_matches_confirmed_evidence():
    """Evidence: docs/analysis/TASK2_Supporting_Sources_Business_Mapping.md
    confirms DateAccesoire=2025-07-30 <-> EtatAccessoire='202531' (13/13
    exact matches, recomputed in this session)."""
    week = IsoWeek.from_date(date(2025, 7, 30))
    assert week.iso_year == 2025
    assert week.iso_week == 31
    assert week.week_key == "202531"
    assert week.label == "S31"
