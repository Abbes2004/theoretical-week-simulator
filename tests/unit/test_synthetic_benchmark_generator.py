"""Unit tests for src/ingestion/synthetic_benchmark_generator.py.

Covers the properties required by the Phase 2 instructions: deterministic
generation, valid/in-range dates, exactly five component events per
completed POI, consistent SYNTHETIC labelling, and guaranteed presence of
ties and the ISO year-boundary case at every scale (not left to chance).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.business.canonical import build_canonical_dataset  # noqa: E402
from src.business.enums import DataOrigin  # noqa: E402
from src.business.rules import COMPONENTS  # noqa: E402
from src.ingestion.synthetic_benchmark_generator import (  # noqa: E402
    RANGE_END,
    RANGE_START,
    generate_chunk,
    to_component_events,
)

_CHUNK_SIZE = 2_000


def test_generation_is_deterministic_for_fixed_seed():
    df1 = generate_chunk(0, _CHUNK_SIZE, seed=42)
    df2 = generate_chunk(0, _CHUNK_SIZE, seed=42)
    pd.testing.assert_frame_equal(df1, df2)


def test_different_chunk_index_gives_different_independent_data():
    df0 = generate_chunk(0, _CHUNK_SIZE, seed=42)
    df1 = generate_chunk(1, _CHUNK_SIZE, seed=42)
    assert not df0["DateTissu"].equals(df1["DateTissu"])
    assert set(df0["POI_Sim"]).isdisjoint(set(df1["POI_Sim"]))


def test_all_dates_are_valid_and_within_range():
    df = generate_chunk(0, _CHUNK_SIZE, seed=1)
    date_cols = ["DateTissu", "DateTissuSec", "DateFourniture", "DateFil", "DateOKProduction"]
    for col in date_cols:
        parsed = pd.to_datetime(df[col], format="%Y-%m-%d")
        assert (parsed.dt.date >= RANGE_START).all()
        assert (parsed.dt.date <= RANGE_END).all()


def test_every_completed_poi_produces_five_component_events():
    df = generate_chunk(0, 500, seed=2)
    events = to_component_events(df)
    assert len(events) == 500 * len(COMPONENTS)
    counts = events.groupby("POI_Sim").size()
    assert (counts == len(COMPONENTS)).all()
    assert set(events["component_name"].unique()) == set(COMPONENTS)


def test_data_origin_is_synthetic_in_component_events():
    df = generate_chunk(0, 200, seed=3)
    events = to_component_events(df)
    assert (events["DATA_ORIGIN"] == DataOrigin.SYNTHETIC.value).all()


def test_every_row_is_calculable_via_the_real_business_engine():
    df = generate_chunk(0, _CHUNK_SIZE, seed=4)
    canonical = build_canonical_dataset(df.head(500), data_origin=DataOrigin.SYNTHETIC)
    assert (canonical["calculation_status"] == "CALCULATED").all()


def test_blocking_components_are_varied():
    df = generate_chunk(0, _CHUNK_SIZE, seed=5)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    seen = set()
    for elements in canonical["blocking_element"]:
        seen.update(elements)
    assert seen == set(COMPONENTS), f"expected all 5 components to appear as blockers, got {seen}"


def test_ties_are_guaranteed_present():
    df = generate_chunk(0, _CHUNK_SIZE, seed=6)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    n_ties = (canonical["blocking_element"].apply(len) >= 2).sum()
    assert n_ties > 0


def test_iso_year_boundary_case_is_guaranteed_present():
    df = generate_chunk(0, _CHUNK_SIZE, seed=7)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    boundary = canonical[canonical["date_theorique"].isin(
        [date(2025, 12, 29), date(2025, 12, 30), date(2025, 12, 31)]
    )]
    assert len(boundary) > 0
    assert (boundary["iso_year"] == 2026).all()
    assert (boundary["iso_week"] == 1).all()
    assert (boundary["week_key"] == "202601").all()


@pytest.mark.parametrize("chunk_size", [1, 7, 999])
def test_generation_handles_small_and_odd_chunk_sizes(chunk_size):
    df = generate_chunk(0, chunk_size, seed=8)
    assert len(df) == chunk_size
