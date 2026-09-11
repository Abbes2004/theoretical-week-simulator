"""Profile the baseline canonical-build stage to identify the real
bottleneck before optimizing (docs/execution/11_benchmarking_plan.md,
"Bottleneck": "Profile the local baseline before deciding what to
distribute").

Usage:
    python benchmarks/baseline/profile_bottleneck.py

Writes outputs/benchmarks/bottleneck_profile.txt (top 25 functions by
cumulative time, cProfile output).
"""

from __future__ import annotations

import cProfile
import pstats
import sys
from io import StringIO
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from configs import settings
from src.business.canonical import build_canonical_dataset
from src.business.enums import DataOrigin


def main() -> None:
    settings.OUTPUTS_BENCHMARKS.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(settings.BENCHMARK_DATASETS_DIR / "synthetic_medium.parquet")

    profiler = cProfile.Profile()
    profiler.enable()
    build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC)
    profiler.disable()

    buffer = StringIO()
    stats = pstats.Stats(profiler, stream=buffer).sort_stats("cumulative")
    stats.print_stats(25)

    out_path = settings.OUTPUTS_BENCHMARKS / "bottleneck_profile.txt"
    header = f"Baseline profile: build_canonical_dataset over {len(df):,} synthetic rows\n\n"
    out_path.write_text(header + buffer.getvalue(), encoding="utf-8")
    print(header + buffer.getvalue())
    print(f"-> {out_path}")


if __name__ == "__main__":
    main()
