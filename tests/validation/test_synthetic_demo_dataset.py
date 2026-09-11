"""Validation tests for the SYNTHETIC pre-Phase-2 demonstration dataset.

See src/ingestion/synthetic_demo_dataset.py and
docs/decisions/0003-synthetic-demo-dataset.md. These tests cover exactly
the properties the demo dataset was built to guarantee: deterministic
generation, valid in-range dates, full calculability, consistent
DATA_ORIGIN=SYNTHETIC labelling, correct MAX()/ISO-week behaviour at the
year boundary, and -- critically -- that generating this dataset never
touches the real raw files or the real canonical outputs.
"""

from __future__ import annotations

import hashlib
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from configs import settings  # noqa: E402
from src.business.canonical import build_canonical_dataset  # noqa: E402
from src.business.enums import CalculationStatus, DataOrigin  # noqa: E402
from src.business.rules import COMPONENTS  # noqa: E402
from src.ingestion.synthetic_demo_dataset import (  # noqa: E402
    RANGE_END,
    RANGE_START,
    build_demo_dataset,
    build_edge_cases,
)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_tree(paths: list[Path]) -> dict[str, str]:
    return {str(p): _hash_file(p) for p in paths if p.exists()}


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_generation_is_deterministic_for_fixed_seed():
    df1, stats1 = build_demo_dataset(real_poi_df=None, n_bulk=50, seed=123)
    df2, stats2 = build_demo_dataset(real_poi_df=None, n_bulk=50, seed=123)
    pd.testing.assert_frame_equal(df1, df2)
    assert stats1 == stats2


def test_different_seeds_produce_different_bulk_dates():
    df1, _ = build_demo_dataset(real_poi_df=None, n_bulk=50, seed=1)
    df2, _ = build_demo_dataset(real_poi_df=None, n_bulk=50, seed=2)
    assert not df1["DateTissu"].equals(df2["DateTissu"])


# ---------------------------------------------------------------------------
# Date validity / range / calculability
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def demo_canonical() -> pd.DataFrame:
    df, _ = build_demo_dataset(real_poi_df=None, n_bulk=200, seed=settings.DEMO_SEED)
    return build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)


def test_all_component_dates_are_valid_and_within_range(demo_canonical):
    date_columns = ["date_tissu", "date_tissu_sec", "date_fourniture", "date_fil", "date_ok_production"]
    for col in date_columns:
        values = demo_canonical[col].dropna()
        assert len(values) == len(demo_canonical), f"{col} has missing values in the demo dataset"
        assert (values.map(lambda d: isinstance(d, date))).all()
        assert (values >= RANGE_START).all(), f"{col} has a value before {RANGE_START}"
        assert (values <= RANGE_END).all(), f"{col} has a value after {RANGE_END}"


def test_every_demo_record_is_calculable(demo_canonical):
    assert (demo_canonical["calculation_status"] == CalculationStatus.CALCULATED.value).all()
    assert (demo_canonical["date_theorique"].notna()).all()
    assert (demo_canonical["sem_theorique"].notna()).all()


def test_data_origin_is_synthetic_everywhere(demo_canonical):
    assert (demo_canonical["data_origin"] == DataOrigin.SYNTHETIC.value).all()


def test_date_theorique_equals_max_of_components(demo_canonical):
    component_cols = ["date_tissu", "date_tissu_sec", "date_fourniture", "date_fil", "date_ok_production"]
    computed_max = demo_canonical[component_cols].max(axis=1)
    assert (demo_canonical["date_theorique"] == computed_max).all()


def test_no_historical_reference_is_fabricated():
    """The demo input must not invent a historical SemTheorique/DateMax --
    that would fabricate a manual-override relationship that doesn't exist."""
    df, _ = build_demo_dataset(real_poi_df=None, n_bulk=20, seed=7)
    assert df["SemTheorique"].isna().all()
    assert df["DateMax"].isna().all()


# ---------------------------------------------------------------------------
# Edge cases (deterministic, hand-specified expectations)
# ---------------------------------------------------------------------------


def test_edge_cases_cover_each_component_as_sole_blocker():
    cases = {c.key: c for c in build_edge_cases()}
    for component in COMPONENTS:
        case = cases[f"BLOCK_{component}"]
        assert case.expected_blocking == (component,)


def test_edge_cases_include_a_tie_and_are_computed_correctly():
    df, _ = build_demo_dataset(real_poi_df=None, n_bulk=0, seed=settings.DEMO_SEED)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    by_poi = canonical.set_index("poi_sim")

    for case in build_edge_cases():
        row = by_poi.loc[f"DEMO-EDGE-{case.key}"]
        assert row["date_theorique"] == case.expected_date_theorique, case.key
        assert set(row["blocking_element"]) == set(case.expected_blocking), case.key
        assert row["calculation_status"] == CalculationStatus.CALCULATED.value, case.key


def test_iso_year_boundary_cluster_has_correct_iso_year_and_week():
    df, _ = build_demo_dataset(real_poi_df=None, n_bulk=0, seed=settings.DEMO_SEED)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    by_poi = canonical.set_index("poi_sim")

    for suffix in ("2025_12_29", "2025_12_30", "2025_12_31"):
        row = by_poi.loc[f"DEMO-EDGE-ISO_YEAR_BOUNDARY_{suffix}"]
        assert row["date_theorique"].year == 2025
        assert row["iso_year"] == 2026
        assert row["iso_week"] == 1
        assert row["week_key"] == "202601"
        assert row["sem_theorique_label"] == "S01"


def test_range_boundaries_are_included_and_calculable():
    df, _ = build_demo_dataset(real_poi_df=None, n_bulk=0, seed=settings.DEMO_SEED)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    by_poi = canonical.set_index("poi_sim")

    assert by_poi.loc["DEMO-EDGE-RANGE_START", "date_theorique"] == RANGE_START
    assert by_poi.loc["DEMO-EDGE-RANGE_END", "date_theorique"] == RANGE_END


# ---------------------------------------------------------------------------
# Real data / real outputs are never touched by generating the demo dataset
# ---------------------------------------------------------------------------


def test_generating_demo_dataset_does_not_touch_real_raw_files():
    raw_files = list(settings.RAW_SQL_FILES.values()) + list(settings.RAW_EXCEL_FILES.values()) + settings.RAW_PDF_FILES
    existing = [p for p in raw_files if p.exists()]
    if not existing:
        pytest.skip("no real raw files present in this checkout")

    before = _hash_tree(existing)
    real_poi_df = None
    if settings.RAW_SQL_FILES["plan_t_simplanifpoi"].exists():
        from src.ingestion.sql_ingestion import load_sql_table_as_dataframe

        real_poi_df = load_sql_table_as_dataframe(settings.RAW_SQL_FILES["plan_t_simplanifpoi"])

    build_demo_dataset(real_poi_df, n_bulk=10, seed=settings.DEMO_SEED)

    after = _hash_tree(existing)
    assert before == after


def test_generating_demo_dataset_does_not_touch_real_canonical_output(tmp_path, monkeypatch):
    real_canonical_dir = settings.DATA_CANONICAL
    real_canonical_files = list(real_canonical_dir.glob("*")) if real_canonical_dir.exists() else []
    before = _hash_tree(real_canonical_files)

    # Point the demo output paths at a scratch directory so this test cannot
    # possibly write into the real tree even if a future edit introduces a bug.
    scratch = tmp_path / "demo_2025_2026"
    monkeypatch.setattr(settings, "DEMO_DATASET_DIR", scratch)
    monkeypatch.setattr(settings, "DEMO_INPUT_DIR", scratch / "input")
    monkeypatch.setattr(settings, "DEMO_CANONICAL_DIR", scratch / "canonical")
    monkeypatch.setattr(settings, "DEMO_METADATA_DIR", scratch / "metadata")

    df, _ = build_demo_dataset(real_poi_df=None, n_bulk=10, seed=settings.DEMO_SEED)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    (scratch / "canonical").mkdir(parents=True, exist_ok=True)
    canonical.to_parquet(scratch / "canonical" / "poi_demo_synthetic_canonical.parquet", index=False)

    after = _hash_tree(real_canonical_files)
    assert before == after
    assert not (real_canonical_dir / "poi_demo_synthetic_canonical.parquet").exists()
