"""Unit tests for src/mapreduce/mapper.py and reducer.py.

Runs the actual scripts as subprocesses (exactly how Hadoop Streaming
invokes them) over small, fast, in-memory-generated inputs, so a change to
either script is caught immediately without needing a slow end-to-end
benchmark-scale run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.business.enums import CalculationStatus  # noqa: E402
from src.ingestion.synthetic_benchmark_generator import generate_chunk, to_component_events  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
_MAPPER = _ROOT / "src" / "mapreduce" / "mapper.py"
_REDUCER = _ROOT / "src" / "mapreduce" / "reducer.py"


def _run_pipeline(events_tsv: str) -> list[str]:
    mapped = subprocess.run(
        [sys.executable, str(_MAPPER)], input=events_tsv, capture_output=True, text=True, check=True
    )
    sorted_lines = "\n".join(sorted(mapped.stdout.splitlines())) + "\n"
    reduced = subprocess.run(
        [sys.executable, str(_REDUCER)], input=sorted_lines, capture_output=True, text=True, check=True
    )
    return [line for line in reduced.stdout.splitlines() if line]


def test_mapper_passes_through_well_formed_lines():
    result = subprocess.run(
        [sys.executable, str(_MAPPER)],
        input="999998\tPOI1\tTISSU\t2025-06-01\tSYNTHETIC\n",
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "999998\tPOI1\tTISSU\t2025-06-01\tSYNTHETIC\n"


def test_mapper_skips_malformed_lines_and_reports_them():
    result = subprocess.run(
        [sys.executable, str(_MAPPER)],
        input="not\tenough\tfields\n999998\tPOI1\tTISSU\t2025-06-01\tSYNTHETIC\n",
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == "999998\tPOI1\tTISSU\t2025-06-01\tSYNTHETIC\n"
    assert "MAPPER_SKIP_MALFORMED_LINE" in result.stderr


def test_mapper_reducer_pipeline_matches_expected_calculation():
    events_tsv = (
        "999998\tPOI-A\tTISSU\t2025-08-04\tSYNTHETIC\n"
        "999998\tPOI-A\tTISSU_SEC\t2025-08-05\tSYNTHETIC\n"
        "999998\tPOI-A\tFOURNITURE\t2025-08-03\tSYNTHETIC\n"
        "999998\tPOI-A\tFIL\t2025-08-04\tSYNTHETIC\n"
        "999998\tPOI-A\tOK_PRODUCTION\t2025-08-08\tSYNTHETIC\n"
    )
    lines = _run_pipeline(events_tsv)
    assert len(lines) == 1
    fields = lines[0].split("\t")
    id_sim, poi_sim, date_theorique, iso_year, iso_week, week_key, sem_theorique, blocking, status = fields
    assert (id_sim, poi_sim) == ("999998", "POI-A")
    assert date_theorique == "2025-08-08"
    assert (iso_year, iso_week, week_key) == ("2025", "32", "202532")
    assert sem_theorique == "202532"
    assert blocking == "OK_PRODUCTION"
    assert status == CalculationStatus.CALCULATED.value


def test_mapper_reducer_handles_a_tie():
    events_tsv = (
        "999998\tPOI-TIE\tTISSU\t2025-08-08\tSYNTHETIC\n"
        "999998\tPOI-TIE\tTISSU_SEC\t2025-08-08\tSYNTHETIC\n"
        "999998\tPOI-TIE\tFOURNITURE\t2025-08-06\tSYNTHETIC\n"
        "999998\tPOI-TIE\tFIL\t2025-08-07\tSYNTHETIC\n"
        "999998\tPOI-TIE\tOK_PRODUCTION\t2025-08-08\tSYNTHETIC\n"
    )
    lines = _run_pipeline(events_tsv)
    fields = lines[0].split("\t")
    blocking = set(fields[7].split(";"))
    assert blocking == {"TISSU", "TISSU_SEC", "OK_PRODUCTION"}


def test_mapper_reducer_handles_a_missing_component():
    events_tsv = (
        "999998\tPOI-MISSING\tTISSU\t2025-08-04\tSYNTHETIC\n"
        "999998\tPOI-MISSING\tFOURNITURE\t2025-08-03\tSYNTHETIC\n"
        "999998\tPOI-MISSING\tFIL\t2025-08-04\tSYNTHETIC\n"
        "999998\tPOI-MISSING\tOK_PRODUCTION\t2025-08-06\tSYNTHETIC\n"
    )  # TISSU_SEC event absent entirely
    lines = _run_pipeline(events_tsv)
    fields = lines[0].split("\t")
    assert fields[2] == ""  # no date_theorique
    assert fields[8] == CalculationStatus.INCOMPLETE_DATA.value


def test_mapper_reducer_groups_multiple_pois_independently():
    df = generate_chunk(0, 30, seed=99)
    events = to_component_events(df)
    events_tsv = events.to_csv(sep="\t", index=False, header=False, lineterminator="\n")
    lines = _run_pipeline(events_tsv)
    assert len(lines) == 30
    poi_sims = {line.split("\t")[1] for line in lines}
    assert poi_sims == set(df["POI_Sim"])
