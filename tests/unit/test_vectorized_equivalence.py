"""Correctness gate for the vectorized optimization.

docs/execution/11_benchmarking_plan.md and
docs/execution/12_hadoop_mapreduce_plan.md both require that a faster
implementation is only accepted once it is shown to produce identical
results to the baseline on the same input. This test is that gate for
src/optimization/vectorized_canonical.py vs src/business/canonical.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.business.canonical import build_canonical_dataset  # noqa: E402
from src.business.enums import DataOrigin  # noqa: E402
from src.ingestion.synthetic_generator import generate_synthetic_poi_rows  # noqa: E402
from src.optimization.vectorized_canonical import build_canonical_dataset_vectorized  # noqa: E402

_COMPARABLE_COLUMNS = [
    "id_sim",
    "poi_sim",
    "date_tissu",
    "date_tissu_sec",
    "date_fourniture",
    "date_fil",
    "date_ok_production",
    "date_theorique",
    "iso_year",
    "iso_week",
    "week_key",
    "sem_theorique",
    "blocking_element",
    "calculation_status",
    "missing_components",
    "invalid_components",
]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    out = df[_COMPARABLE_COLUMNS].copy()
    for col in ("iso_year", "iso_week"):
        out[col] = out[col].apply(lambda v: None if pd.isna(v) else int(v))
    for col in ("blocking_element", "missing_components", "invalid_components"):
        out[col] = out[col].apply(lambda v: sorted(v) if isinstance(v, list) else v)
    out["id_sim"] = out["id_sim"].astype(str)
    return out.reset_index(drop=True)


@pytest.mark.parametrize("seed", [10, 11, 12])
def test_vectorized_matches_baseline_on_synthetic_mix(seed: int):
    df = generate_synthetic_poi_rows(800, seed=seed)
    baseline = _normalize(build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC))
    vectorized = _normalize(build_canonical_dataset_vectorized(df, data_origin=DataOrigin.SYNTHETIC))
    pd.testing.assert_frame_equal(baseline, vectorized, check_dtype=False)


def test_vectorized_matches_baseline_on_real_extract():
    from configs import settings
    from src.ingestion.sql_ingestion import load_sql_table_as_dataframe

    path = settings.RAW_SQL_FILES["plan_t_simplanifpoi"]
    if not path.exists():
        pytest.skip("real raw data/raw/sql/plan_t_simplanifpoi.sql not present in this checkout")

    poi_df = load_sql_table_as_dataframe(path)
    baseline = _normalize(build_canonical_dataset(poi_df, data_origin=DataOrigin.REAL))
    vectorized = _normalize(build_canonical_dataset_vectorized(poi_df, data_origin=DataOrigin.REAL))
    pd.testing.assert_frame_equal(baseline, vectorized, check_dtype=False)
