"""Large-scale SYNTHETIC benchmark dataset generator (Phase 2).

Purpose: produce fully-calculable synthetic POI datasets at 100k/500k/1M
(and, only on explicit request, 5M) scale so the local baseline, local
vectorized, and Hadoop MapReduce implementations can be benchmarked on
equivalent, reproducible, honestly-labelled workloads.

This reuses the exact same business-rule engine as Phase 1
(`src.business.canonical.build_canonical_dataset_vectorized`) to compute
the `canonical_reference/` output, so the "correct answer" used for the
Hadoop-vs-local comparison is never a second, independently reimplemented
copy of the calculation.

Memory discipline: this development machine has ~8GB RAM total (often
<1.5GB free at any given moment -- see
docs/decisions/0004-hadoop-environment-and-benchmark-design.md). Data is
generated and written in bounded chunks (`configs.settings.BENCHMARK_CHUNK_SIZE`
rows at a time, default 100,000) as partitioned Parquet files
(`part-00000.parquet`, `part-00001.parquet`, ...) rather than ever building
one giant in-memory DataFrame for the full requested scale.

Data rules (same as docs/decisions/0003 for the demo dataset):
- `data/raw/` is never opened by this module.
- Every row is synthetic; identifiers use a sentinel `Id_Sim`
  (`configs.settings.BENCHMARK_ID_SIM = 999998`), distinct from the real
  data's ranges AND from the demo dataset's own sentinel (999999).
- No historical `SemTheorique`/`DateMax` is fabricated.
- No POI-Stock/material/quantity/manual-override relationship is invented;
  the input table only ever populates the five documented component-date
  columns plus identifiers.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs.settings import (  # noqa: E402
    BENCHMARK_CHUNK_SIZE,
    BENCHMARK_ID_SIM,
    BENCHMARK_RANGE_END,
    BENCHMARK_RANGE_START,
    BENCHMARK_SCHEMA_VERSION,
    BENCHMARK_SEED,
    COMPONENT_DATE_COLUMNS,
)
from src.business.canonical import CANONICAL_COLUMNS  # noqa: E402
from src.business.enums import DataOrigin  # noqa: E402
from src.business.rules import COMPONENTS  # noqa: E402
from src.optimization.vectorized_canonical import build_canonical_dataset_vectorized  # noqa: E402

RANGE_START: date = date.fromisoformat(BENCHMARK_RANGE_START)
RANGE_END: date = date.fromisoformat(BENCHMARK_RANGE_END)
_SPAN_DAYS = (RANGE_END - RANGE_START).days

_RAW_COLUMNS = (
    "Id_SimPoi",
    "Id_Sim",
    "POI_Sim",
    "DateTissu",
    "DateTissuSec",
    "DateFourniture",
    "DateFil",
    "DateOKProduction",
    "DateMax",
    "SemTheorique",
)

_N_COMPONENTS = len(COMPONENTS)

# Fractions of each chunk deliberately forced into a tie / an ISO
# year-boundary case, so these properties are guaranteed at every scale
# rather than left to chance (same rationale as the 513-row demo dataset,
# docs/decisions/0003, applied here at proportional volume).
_TIE_FRACTION = 0.02
_ISO_BOUNDARY_FRACTION = 0.01

# The only dates in [2025-01-01, 2026-06-30] where the calendar year
# differs from the ISO week-year, verified directly with
# date.isocalendar() (see src/ingestion/synthetic_demo_dataset.py for the
# same verification note): 2025-12-29/30/31 all fall in ISO week 01 of
# ISO year 2026.
_ISO_BOUNDARY_DATES = (date(2025, 12, 29), date(2025, 12, 30), date(2025, 12, 31))
_ISO_BOUNDARY_OFFSETS = tuple((d - RANGE_START).days for d in _ISO_BOUNDARY_DATES)


def _rng_for_chunk(seed: int, chunk_index: int) -> np.random.Generator:
    """Independent, reproducible RNG substream per chunk (NumPy SeedSequence
    spawning), so chunk N's rows never depend on how many chunks were
    generated before it and results are identical whether generated in one
    pass or resumed/parallelized chunk-by-chunk."""
    seed_sequence = np.random.SeedSequence(seed)
    child = seed_sequence.spawn(chunk_index + 1)[chunk_index]
    return np.random.default_rng(child)


def generate_chunk(chunk_index: int, chunk_size: int, seed: int = BENCHMARK_SEED) -> pd.DataFrame:
    """Generate one chunk (partition) of the raw-schema input table.

    Vectorized (NumPy array operations over the whole chunk at once): no
    Python-level per-row loop, so this stays fast even at chunk_size=100_000.
    """
    rng = _rng_for_chunk(seed, chunk_index)

    offsets = rng.integers(0, _SPAN_DAYS + 1, size=(chunk_size, _N_COMPONENTS))

    n_tie = int(round(chunk_size * _TIE_FRACTION))
    n_iso = int(round(chunk_size * _ISO_BOUNDARY_FRACTION))
    tie_rows = rng.choice(chunk_size, size=n_tie, replace=False) if n_tie else np.array([], dtype=int)
    remaining = np.setdiff1d(np.arange(chunk_size), tie_rows, assume_unique=False)
    iso_rows = rng.choice(remaining, size=min(n_iso, len(remaining)), replace=False) if n_iso else np.array([], dtype=int)

    # Force a guaranteed tie: pick 2 or 3 components per tie-row to share a
    # common maximum offset; the rest of that row's components get an offset
    # drawn uniformly at or below that maximum, so the shared value really
    # is the row's max.
    for row in tie_rows:
        k = rng.integers(2, 4)  # 2 or 3 tied components
        tie_cols = rng.choice(_N_COMPONENTS, size=k, replace=False)
        tie_value = rng.integers(0, _SPAN_DAYS + 1)
        offsets[row, :] = rng.integers(0, tie_value + 1, size=_N_COMPONENTS) if tie_value > 0 else 0
        offsets[row, tie_cols] = tie_value

    # Force a guaranteed ISO year-boundary case: one component lands exactly
    # on 2025-12-29/30/31 and is that row's maximum.
    for row in iso_rows:
        boundary_offset = int(rng.choice(_ISO_BOUNDARY_OFFSETS))
        col = rng.integers(0, _N_COMPONENTS)
        offsets[row, :] = rng.integers(0, boundary_offset + 1, size=_N_COMPONENTS) if boundary_offset > 0 else 0
        offsets[row, col] = boundary_offset

    dates = np.datetime64(RANGE_START) + offsets.astype("timedelta64[D]")
    date_strs = np.datetime_as_string(dates, unit="D")  # shape (chunk_size, 5), 'YYYY-MM-DD'

    global_start = chunk_index * chunk_size
    row_ids = np.arange(global_start, global_start + chunk_size)
    poi_sim = np.array([f"BENCH{chunk_index:05d}{i:08d}CD" for i in range(chunk_size)])

    df = pd.DataFrame(
        {
            "Id_SimPoi": (900_200_000 + row_ids),
            "Id_Sim": str(BENCHMARK_ID_SIM),
            "POI_Sim": poi_sim,
            "DateTissu": date_strs[:, 0],
            "DateTissuSec": date_strs[:, 1],
            "DateFourniture": date_strs[:, 2],
            "DateFil": date_strs[:, 3],
            "DateOKProduction": date_strs[:, 4],
            "DateMax": None,
            "SemTheorique": None,
        },
        columns=list(_RAW_COLUMNS),
    )
    return df


def to_component_events(raw_chunk: pd.DataFrame) -> pd.DataFrame:
    """Melt the wide 5-date-column input into the long-form
    (Id_Sim, POI_Sim, component_name, availability_date, DATA_ORIGIN)
    representation used as the Hadoop mapper's input.

    This representation is a SYNTHETIC COMPUTATIONAL BENCHMARK
    REPRESENTATION invented for this evaluation, not a confirmed company
    schema -- see docs/decisions/0004.
    """
    frames = []
    for component, column in COMPONENT_DATE_COLUMNS.items():
        frames.append(
            pd.DataFrame(
                {
                    "Id_Sim": raw_chunk["Id_Sim"],
                    "POI_Sim": raw_chunk["POI_Sim"],
                    "component_name": component,
                    "availability_date": raw_chunk[column],
                    "DATA_ORIGIN": DataOrigin.SYNTHETIC.value,
                }
            )
        )
    events = pd.concat(frames, ignore_index=True)
    return events.sort_values(["POI_Sim", "component_name"]).reset_index(drop=True)


@dataclass(frozen=True)
class ChunkPaths:
    input_path: Path
    events_path: Path
    reference_path: Path


def iter_chunks(scale: int, chunk_size: int = BENCHMARK_CHUNK_SIZE) -> Iterator[tuple[int, int]]:
    """Yield (chunk_index, this_chunk_size) pairs covering `scale` rows."""
    n_full, remainder = divmod(scale, chunk_size)
    for i in range(n_full):
        yield i, chunk_size
    if remainder:
        yield n_full, remainder


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def generate_benchmark_dataset(
    scale: int,
    *,
    seed: int = BENCHMARK_SEED,
    chunk_size: int = BENCHMARK_CHUNK_SIZE,
    input_dir: Path,
    events_dir: Path,
    reference_dir: Path,
    progress: bool = True,
) -> dict:
    """Generate `scale` synthetic POIs, chunk by chunk, writing partitioned
    Parquet under the three given directories. Returns a metadata dict
    (row/event counts, per-file hashes, status distribution, blocking
    distribution) suitable for json.dump into metadata/generation_metadata.json.
    """
    for d in (input_dir, events_dir, reference_dir):
        d.mkdir(parents=True, exist_ok=True)

    file_hashes: dict[str, str] = {}
    total_rows = 0
    total_events = 0
    status_totals: dict[str, int] = {}
    blocking_totals: dict[str, int] = {}

    for chunk_index, this_size in iter_chunks(scale, chunk_size):
        raw_chunk = generate_chunk(chunk_index, this_size, seed=seed)
        events_chunk = to_component_events(raw_chunk)
        reference_chunk = build_canonical_dataset_vectorized(raw_chunk, data_origin=DataOrigin.SYNTHETIC)

        input_path = input_dir / f"part-{chunk_index:05d}.parquet"
        events_path = events_dir / f"part-{chunk_index:05d}.parquet"
        reference_path = reference_dir / f"part-{chunk_index:05d}.parquet"

        raw_chunk.to_parquet(input_path, index=False)
        events_chunk.to_parquet(events_path, index=False)

        ref_to_write = reference_chunk.copy()
        for col in ("blocking_element", "missing_components", "invalid_components", "suspicious_components", "data_quality_flag"):
            ref_to_write[col] = ref_to_write[col].apply(lambda v: ";".join(v) if isinstance(v, list) else v)
        ref_to_write.to_parquet(reference_path, index=False)

        for path in (input_path, events_path, reference_path):
            file_hashes[str(path.relative_to(input_dir.parent.parent))] = _sha256(path)

        total_rows += len(raw_chunk)
        total_events += len(events_chunk)
        for status, count in reference_chunk["calculation_status"].value_counts().items():
            status_totals[status] = status_totals.get(status, 0) + int(count)
        for elements in reference_chunk["blocking_element"]:
            for e in elements:
                blocking_totals[e] = blocking_totals.get(e, 0) + 1

        if progress:
            print(f"    chunk {chunk_index}: {this_size:,} POIs -> {input_path.name} "
                  f"({total_rows:,}/{scale:,} total)")

        del raw_chunk, events_chunk, reference_chunk, ref_to_write

    return {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "data_origin": "SYNTHETIC",
        "seed": seed,
        "range_start": RANGE_START.isoformat(),
        "range_end": RANGE_END.isoformat(),
        "id_sim_sentinel": BENCHMARK_ID_SIM,
        "requested_scale": scale,
        "chunk_size": chunk_size,
        "n_chunks": len(list(iter_chunks(scale, chunk_size))),
        "total_poi_rows": total_rows,
        "total_component_events": total_events,
        "events_per_poi": total_events / total_rows if total_rows else 0,
        "calculation_status_distribution": status_totals,
        "blocking_element_distribution": blocking_totals,
        "file_hashes_sha256": file_hashes,
    }
