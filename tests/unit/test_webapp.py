"""Regression tests for src/simulation/webapp.py.

Covers a real bug found while testing the demo dataset in the browser: a
parquet round-trip returns list-typed columns (e.g. `blocking_element`) as
numpy arrays rather than Python lists, so rendering code must not assume
`isinstance(value, list)`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from configs import settings  # noqa: E402
from src.business.canonical import build_canonical_dataset  # noqa: E402
from src.business.enums import DataOrigin  # noqa: E402
from src.ingestion.synthetic_demo_dataset import build_demo_dataset  # noqa: E402
from src.simulation.webapp import _join_list_cell, create_app  # noqa: E402


def test_join_list_cell_handles_list_and_ndarray_and_none():
    assert _join_list_cell(["TISSU", "FIL"]) == "TISSU, FIL"
    assert _join_list_cell(np.array(["TISSU", "FIL"])) == "TISSU, FIL"
    assert _join_list_cell([]) == ""
    assert _join_list_cell(None) == ""


@pytest.fixture()
def demo_parquet(tmp_path, monkeypatch) -> Path:
    df, _ = build_demo_dataset(real_poi_df=None, n_bulk=0, seed=settings.DEMO_SEED)
    canonical = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    path = tmp_path / "poi_demo_synthetic_canonical.parquet"
    canonical.to_parquet(path, index=False)  # forces the list-column -> ndarray round trip
    monkeypatch.setattr(settings, "DEMO_CANONICAL_PARQUET", path)
    return path


def test_browse_page_renders_blocking_elements_after_parquet_roundtrip(demo_parquet):
    app = create_app(default_dataset="demo")
    client = app.test_client()
    response = client.get("/browse?dataset=demo&status=CALCULATED")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # DEMO-EDGE-BLOCK_TISSU's blocking_element is ["TISSU"] before it round-trips
    # through parquet as a numpy array -- this must still render as text, not "".
    assert "DEMO-EDGE-BLOCK_TISSU" in html
    assert "<td>TISSU</td>" in html
    assert "TISSU, FIL" in html  # TIE_2WAY


def test_demo_dataset_shows_warning_banner(demo_parquet):
    app = create_app(default_dataset="demo")
    client = app.test_client()
    response = client.get("/?dataset=demo")
    html = response.get_data(as_text=True)
    assert "SYNTHETIC DEMO DATA" in html


def test_real_dataset_view_has_no_demo_banner(demo_parquet, tmp_path, monkeypatch):
    empty_real_dir = tmp_path / "real_canonical"
    empty_real_dir.mkdir()
    monkeypatch.setattr(settings, "DATA_CANONICAL", empty_real_dir)
    app = create_app(default_dataset="real")
    client = app.test_client()
    response = client.get("/?dataset=real")
    html = response.get_data(as_text=True)
    assert "SYNTHETIC DEMO DATA" not in html
