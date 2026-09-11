"""Unit tests for src/business/rules.py.

Every case here traces back to a row in docs/execution/13_testing_strategy.md
("Core Cases") or an item in docs/context/Edge Cases & Data Quality
Handling.md. All input data in this file is synthetic
(DATA_ORIGIN = SYNTHETIC), used only to validate the calculation logic in
isolation -- it is never presented as company history.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from business.enums import Applicability, CalculationStatus, QualityFlag  # noqa: E402
from business.rules import COMPONENTS, calculate_theoretical_week  # noqa: E402


def all_dates(**overrides) -> dict[str, object]:
    base = {c: None for c in COMPONENTS}
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Core cases (docs/execution/13_testing_strategy.md)
# ---------------------------------------------------------------------------


def test_all_components_available_returns_max_date():
    dates = all_dates(
        TISSU="2025-08-04",
        TISSU_SEC="2025-08-05",
        FOURNITURE="2025-08-03",
        FIL="2025-08-04",
        OK_PRODUCTION="2025-08-08",
    )
    result = calculate_theoretical_week(dates)
    assert result.status == CalculationStatus.CALCULATED
    assert result.date_theorique == date(2025, 8, 8)
    assert result.blocking_elements == ("OK_PRODUCTION",)


def test_single_latest_component_is_sole_blocker():
    dates = all_dates(
        TISSU="2025-08-04",
        TISSU_SEC="2025-08-04",
        FOURNITURE="2025-08-03",
        FIL="2025-08-04",
        OK_PRODUCTION="2025-08-06",
    )
    result = calculate_theoretical_week(dates)
    assert result.blocking_elements == ("OK_PRODUCTION",)


def test_tied_latest_components_all_returned():
    dates = all_dates(
        TISSU="2025-08-08",
        TISSU_SEC="2025-08-08",
        FOURNITURE="2025-08-06",
        FIL="2025-08-07",
        OK_PRODUCTION="2025-08-08",
    )
    result = calculate_theoretical_week(dates)
    assert result.status == CalculationStatus.CALCULATED
    assert result.date_theorique == date(2025, 8, 8)
    assert set(result.blocking_elements) == {"TISSU", "TISSU_SEC", "OK_PRODUCTION"}


def test_optional_component_missing_is_ignored_when_overridden_not_required():
    dates = all_dates(
        TISSU="2025-08-04",
        TISSU_SEC=None,
        FOURNITURE="2025-08-03",
        FIL="2025-08-04",
        OK_PRODUCTION="2025-08-05",
    )
    result = calculate_theoretical_week(
        dates, applicability_overrides={"TISSU_SEC": Applicability.NOT_REQUIRED}
    )
    assert result.status == CalculationStatus.CALCULATED
    assert result.components["TISSU_SEC"].applicability == Applicability.NOT_REQUIRED
    assert result.date_theorique == date(2025, 8, 5)
    assert result.blocking_elements == ("OK_PRODUCTION",)


def test_required_component_missing_yields_incomplete_data_and_no_date():
    dates = all_dates(
        TISSU="2025-08-04",
        TISSU_SEC="2025-08-05",
        FOURNITURE="2025-08-03",
        FIL=None,
        OK_PRODUCTION="2025-08-06",
    )
    result = calculate_theoretical_week(dates)
    assert result.status == CalculationStatus.INCOMPLETE_DATA
    assert result.date_theorique is None
    assert result.sem_theorique is None
    assert result.missing_components == ("FIL",)
    assert QualityFlag.MISSING_COMPONENT_DATE in result.quality_flags


@pytest.mark.parametrize("bad_value", ["2025-99-40", "31/31/2025", "ABC", ""])
def test_invalid_date_format_flags_invalid_data(bad_value):
    dates = all_dates(
        TISSU=bad_value if bad_value else None,
        TISSU_SEC="2025-08-05",
        FOURNITURE="2025-08-03",
        FIL="2025-08-04",
        OK_PRODUCTION="2025-08-06",
    )
    result = calculate_theoretical_week(dates)
    if bad_value == "":
        # Empty string is treated as "no value", not a malformed date.
        assert result.status == CalculationStatus.INCOMPLETE_DATA
    else:
        assert result.status == CalculationStatus.INVALID_DATA
        assert result.invalid_components == ("TISSU",)
        assert QualityFlag.INVALID_DATE in result.quality_flags
    assert result.date_theorique is None


def test_no_applicable_components_yields_not_applicable():
    dates = all_dates()
    overrides = {c: Applicability.NOT_REQUIRED for c in COMPONENTS}
    result = calculate_theoretical_week(dates, applicability_overrides=overrides)
    assert result.status == CalculationStatus.NOT_APPLICABLE
    assert result.date_theorique is None
    assert QualityFlag.NO_APPLICABLE_COMPONENTS in result.quality_flags


@pytest.mark.parametrize(
    "d,expected_iso_year,expected_iso_week",
    [
        (date(2020, 12, 31), 2020, 53),  # 2020 has an ISO week 53
        (date(2023, 1, 1), 2022, 52),    # Sunday -> belongs to the previous ISO year
        (date(2025, 12, 29), 2026, 1),   # Monday of the first ISO week of 2026
    ],
)
def test_iso_week_year_boundary(d, expected_iso_year, expected_iso_week):
    dates = all_dates(
        TISSU=d.isoformat(),
        TISSU_SEC=d.isoformat(),
        FOURNITURE=d.isoformat(),
        FIL=d.isoformat(),
        OK_PRODUCTION=d.isoformat(),
    )
    result = calculate_theoretical_week(dates)
    assert result.status == CalculationStatus.CALCULATED
    assert result.iso_week.iso_year == expected_iso_year
    assert result.iso_week.iso_week == expected_iso_week
    assert result.sem_theorique == f"{expected_iso_year}{expected_iso_week:02d}"


def test_suspicious_future_date_is_flagged_but_still_calculated():
    dates = all_dates(
        TISSU="2099-01-01",
        TISSU_SEC="2025-08-05",
        FOURNITURE="2025-08-03",
        FIL="2025-08-04",
        OK_PRODUCTION="2025-08-06",
    )
    result = calculate_theoretical_week(dates)
    assert result.status == CalculationStatus.CALCULATED
    assert "TISSU" in result.suspicious_components
    assert QualityFlag.SUSPICIOUS_DATE in result.quality_flags
    # The suspicious date is still the latest -> still drives the result.
    assert result.date_theorique == date(2099, 1, 1)
    assert result.blocking_elements == ("TISSU",)


def test_missing_value_is_distinguished_from_invalid_value():
    """A NULL date is not, by itself, a data-quality error (edge case 1 vs 4)."""
    dates = all_dates(TISSU=None)
    detail = calculate_theoretical_week(dates).components["TISSU"]
    assert detail.parsed.is_valid is True
    assert detail.parsed.value is None
    assert detail.applicability == Applicability.REQUIRED_BUT_UNAVAILABLE


# ---------------------------------------------------------------------------
# Property checks (docs/execution/13_testing_strategy.md, "Property Checks")
# ---------------------------------------------------------------------------

from hypothesis import given, strategies as st  # noqa: E402

_date_strategy = st.dates(min_value=date(2000, 1, 1), max_value=date(2035, 12, 31))


@given(dates=st.lists(_date_strategy, min_size=5, max_size=5))
def test_property_theoretical_date_not_earlier_than_any_included_date(dates):
    raw = dict(zip(COMPONENTS, (d.isoformat() for d in dates)))
    result = calculate_theoretical_week(raw)
    assert result.status == CalculationStatus.CALCULATED
    for d in dates:
        assert result.date_theorique >= d


@given(dates=st.lists(_date_strategy, min_size=5, max_size=5, unique=True))
def test_property_every_blocker_has_the_theoretical_date(dates):
    raw = dict(zip(COMPONENTS, (d.isoformat() for d in dates)))
    result = calculate_theoretical_week(raw)
    for component in result.blocking_elements:
        assert result.components[component].parsed.value == result.date_theorique


@given(dates=st.lists(_date_strategy, min_size=5, max_size=5, unique=True))
def test_property_lowering_a_non_maximum_date_cannot_increase_result(dates):
    raw = dict(zip(COMPONENTS, (d.isoformat() for d in dates)))
    original = calculate_theoretical_week(raw)
    non_blocking = [c for c in COMPONENTS if c not in original.blocking_elements]
    if not non_blocking:
        return
    target = non_blocking[0]
    lowered_raw = dict(raw)
    lowered_raw[target] = date(2000, 1, 1).isoformat()
    lowered = calculate_theoretical_week(lowered_raw)
    assert lowered.date_theorique <= original.date_theorique


@given(dates=st.lists(_date_strategy, min_size=4, max_size=4, unique=True))
def test_property_adding_a_later_required_component_cannot_decrease_result(dates):
    partial = dict(zip(COMPONENTS[:4], (d.isoformat() for d in dates)))
    overrides = {COMPONENTS[4]: Applicability.NOT_REQUIRED}
    before = calculate_theoretical_week(
        {**partial, COMPONENTS[4]: None}, applicability_overrides=overrides
    )
    later_date = max(dates) + __import__("datetime").timedelta(days=10)
    after = calculate_theoretical_week({**partial, COMPONENTS[4]: later_date.isoformat()})
    assert after.date_theorique >= before.date_theorique
