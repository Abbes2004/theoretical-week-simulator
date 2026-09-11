"""Validation-layer tests: compare calculated SemTheorique against a
historical/reference value.

docs/execution/13_testing_strategy.md, "Historical Validation": calculate
row by row, compare, classify discrepancies, measure match rate.

The real POI extract (data/raw/sql/plan_t_simplanifpoi.sql) has
SemTheorique 100% NULL (see docs/analysis/PHASE0_Initial_Project_Assessment.md),
so it cannot exercise this comparison end-to-end. These tests use the
reproducible SYNTHETIC generator (src/ingestion/synthetic_generator.py) to
prove the match-rate machinery itself is correct; they are not a claim
about historical accuracy against real company data.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from business.canonical import build_canonical_dataset  # noqa: E402
from business.enums import DataOrigin  # noqa: E402
from src.ingestion.synthetic_generator import SyntheticMix, generate_synthetic_poi_rows  # noqa: E402
from src.simulation.simulator import validate_against_historical  # noqa: E402


def test_perfect_historical_match_when_no_mismatch_injected():
    df = generate_synthetic_poi_rows(
        500,
        seed=1,
        mix=SyntheticMix(
            complete_all_dates=0.6,
            complete_with_tie=0.2,
            missing_one_required=0.1,
            missing_all=0.05,
            invalid_date=0.025,
            suspicious_date=0.025,
        ),
        populate_historical=True,
        historical_mismatch_rate=0.0,
    )
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    summary = validate_against_historical(canonical)

    assert summary.comparable_pois > 0
    assert summary.match_rate == 1.0
    assert summary.mismatches == 0


def test_known_mismatch_rate_is_detected():
    df = generate_synthetic_poi_rows(
        2000,
        seed=2,
        populate_historical=True,
        historical_mismatch_rate=0.2,
    )
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    summary = validate_against_historical(canonical)

    assert summary.comparable_pois > 0
    # Allow sampling variance around the injected 20% mismatch rate.
    assert 0.70 <= summary.match_rate <= 0.90


def test_no_comparable_pois_reports_none_not_a_false_rate():
    """Mirrors the real extract: SemTheorique never populated -> match_rate
    must be None (unknown), never silently 0.0 or 1.0."""
    df = generate_synthetic_poi_rows(50, seed=3, populate_historical=False)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    summary = validate_against_historical(canonical)

    assert summary.comparable_pois == 0
    assert summary.match_rate is None


def test_data_origin_is_never_mislabeled_as_real():
    df = generate_synthetic_poi_rows(20, seed=4)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    assert (canonical["data_origin"] == DataOrigin.SYNTHETIC.value).all()
