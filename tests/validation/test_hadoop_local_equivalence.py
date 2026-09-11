"""Correctness gate (automated): MapReduce (local-emulation, or real Hadoop
when scripts/run_hadoop_job.py detects it) output must exactly match the
local vectorized canonical reference.

This exercises the full scripts/run_hadoop_job.py pipeline (mapper.py as a
subprocess, external `sort`, reducer.py as a subprocess) rather than
calling the pure functions directly, so it also catches integration bugs
in the TSV framing/field ordering -- exactly the kind of bug that slipped
through a manual run at 100k scale during development (a list-vs-string
`blocking_element` mismatch between the demo and benchmark canonical
formats) before scripts/compare_hadoop_local.py's normalizer was fixed.

Also verifies that generating/running any of this Phase 2 machinery never
modifies data/raw/, the real data/canonical/ output, or
data/synthetic/demo_2025_2026/.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from configs import settings  # noqa: E402
from scripts.compare_hadoop_local import _load_hadoop_output, _normalize_blocking_element  # noqa: E402
from scripts.run_hadoop_job import run_job  # noqa: E402
from src.business.canonical import build_canonical_dataset  # noqa: E402
from src.business.enums import DataOrigin  # noqa: E402
from src.ingestion.synthetic_benchmark_generator import generate_chunk, to_component_events  # noqa: E402


def _hash_tree(paths: list[Path]) -> dict[str, str]:
    out = {}
    for p in paths:
        if p.exists():
            out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


@pytest.fixture()
def small_dataset(tmp_path):
    df = generate_chunk(0, 300, seed=123)
    events = to_component_events(df)
    events_path = tmp_path / "events.tsv"
    events.to_csv(events_path, sep="\t", index=False, header=False, lineterminator="\n")
    reference = build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    return events_path, reference


def test_hadoop_pipeline_output_exactly_matches_local_reference(tmp_path, small_dataset):
    events_path, reference = small_dataset
    work_dir = tmp_path / "mr_work"

    # Deliberately local-emulation, not "auto": with the real 3-VM cluster
    # reachable (see docs/decisions/0005), "auto" would submit a real
    # Hadoop Streaming job, which took ~15 minutes for a similarly-sized
    # (513-row) input in this session -- fine for a one-off manual check,
    # but it would make the routine test suite impractically slow. Real
    # cluster correctness is verified separately and documented (513-row
    # demo and the 100,000-POI benchmark scale, both exact matches -- see
    # docs/decisions/0005) and by test_real_cluster_correctness_slow below
    # (opt-in only, not run by default).
    result = run_job(events_path, work_dir, label="pytest_small", mode="local-emulation")
    assert result.n_input_lines == 300 * 5
    assert result.n_output_lines == 300

    hadoop_df = _load_hadoop_output(Path(result.output_path))

    ref = reference[["id_sim", "poi_sim", "date_theorique", "iso_year", "iso_week", "week_key",
                      "sem_theorique", "blocking_element", "calculation_status"]].copy()
    ref["id_sim"] = ref["id_sim"].astype(str)
    ref["date_theorique"] = ref["date_theorique"].apply(lambda d: d.isoformat() if d else "")
    ref["iso_year"] = ref["iso_year"].apply(lambda v: "" if pd.isna(v) else str(int(v)))
    ref["iso_week"] = ref["iso_week"].apply(lambda v: "" if pd.isna(v) else str(int(v)))
    ref["week_key"] = ref["week_key"].fillna("")
    ref["sem_theorique"] = ref["sem_theorique"].fillna("")
    ref["blocking_element"] = ref["blocking_element"].apply(_normalize_blocking_element)

    merged = hadoop_df.merge(ref, on=["id_sim", "poi_sim"], suffixes=("_hadoop", "_local"))
    assert len(merged) == 300

    for field in ["date_theorique", "iso_year", "iso_week", "week_key", "sem_theorique", "calculation_status"]:
        mismatches = merged[merged[f"{field}_hadoop"] != merged[f"{field}_local"]]
        assert mismatches.empty, f"{field} mismatches:\n{mismatches[['id_sim', 'poi_sim', f'{field}_hadoop', f'{field}_local']]}"

    tie_mismatches = merged[
        merged.apply(lambda r: sorted(r["blocking_element_hadoop"]) != sorted(r["blocking_element_local"]), axis=1)
    ]
    assert tie_mismatches.empty


def test_hadoop_job_is_correctly_labelled_local_emulation(tmp_path, small_dataset):
    events_path, _ = small_dataset
    result = run_job(events_path, tmp_path / "mr_work2", label="pytest_mode_check", mode="local-emulation")
    assert result.mode == "local_emulation"
    assert any("LOCAL EMULATION" in note for note in result.notes)


@pytest.mark.skipif(
    os.environ.get("TWS_TEST_REAL_CLUSTER") != "1",
    reason="Opt-in only (set TWS_TEST_REAL_CLUSTER=1): submits a real Hadoop Streaming "
    "job to the 3-VM cluster, which took several minutes even for a 300-row input in "
    "this session (see docs/decisions/0005). Real-cluster correctness is already "
    "verified and documented for the 513-row demo and the 100,000-POI benchmark scale "
    "(both exact matches); this test exists for occasional re-verification, not routine runs.",
)
def test_real_cluster_correctness_slow(tmp_path, small_dataset):
    events_path, reference = small_dataset
    result = run_job(events_path, tmp_path / "mr_work_real", label="pytest_real_cluster", mode="real")
    assert result.mode == "real_hadoop_cluster"

    hadoop_df = _load_hadoop_output(Path(result.output_path))
    ref = reference[["id_sim", "poi_sim", "calculation_status"]].copy()
    ref["id_sim"] = ref["id_sim"].astype(str)
    merged = hadoop_df.merge(ref, on=["id_sim", "poi_sim"], suffixes=("_hadoop", "_local"))
    assert len(merged) == 300
    assert (merged["calculation_status_hadoop"] == merged["calculation_status_local"]).all()


def test_generating_and_running_mapreduce_never_touches_protected_data(tmp_path):
    protected_paths = (
        list(settings.RAW_SQL_FILES.values())
        + list(settings.RAW_EXCEL_FILES.values())
        + settings.RAW_PDF_FILES
        + ([settings.DATA_CANONICAL / "poi_canonical.parquet"] if (settings.DATA_CANONICAL / "poi_canonical.parquet").exists() else [])
        + ([settings.DEMO_CANONICAL_PARQUET] if settings.DEMO_CANONICAL_PARQUET.exists() else [])
        + ([settings.DEMO_INPUT_PARQUET] if settings.DEMO_INPUT_PARQUET.exists() else [])
    )
    before = _hash_tree(protected_paths)

    df = generate_chunk(0, 50, seed=321)
    events = to_component_events(df)
    events_path = tmp_path / "events.tsv"
    events.to_csv(events_path, sep="\t", index=False, header=False, lineterminator="\n")
    run_job(events_path, tmp_path / "mr_work3", label="pytest_protect_check", mode="local-emulation")
    build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)

    after = _hash_tree(protected_paths)
    assert before == after
