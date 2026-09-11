"""Phase 2 benchmark: local baseline vs. local vectorized vs. real/local-emulated
Hadoop MapReduce, across the required benchmark scales.

Measures and reports SEPARATELY, per docs/execution/11_benchmarking_plan.md
and the Phase 2 instructions:
    - dataset generation time        (read from metadata/scale_<N>.json,
                                       already measured by generate_benchmark_dataset.py)
    - input conversion/preparation   (prepare_hadoop_input.py)
    - HDFS upload / MapReduce job / HDFS download  (run_hadoop_job.py, real
      cluster) OR map/shuffle-sort/reduce (local-emulation fallback)
    - total end-to-end time
    - local baseline and local vectorized canonical-build time (no Hadoop
      involved at all -- same measurement as Phase 1's
      benchmarks/baseline/run_benchmark.py, repeated here on the Phase 2
      benchmark_scale dataset so all three implementations are compared on
      literally the same input)

Usage:
    python benchmarks/baseline/run_phase2_benchmark.py
    python benchmarks/baseline/run_phase2_benchmark.py --scales 100000 500000 1000000 --hadoop-scales 100000

Real Hadoop-cluster wall-clock at 100k rows already measured in this
session to run tens of minutes (this hardware has ~1 vCPU / ~380MB usable
container memory per worker -- see docs/decisions/0005), so by default
only the SMALLEST requested scale gets a real/auto Hadoop run; larger
scales default to local-emulation (still honestly labelled) unless
`--hadoop-scales` is passed explicitly. This is a deliberate, documented
practicality trade-off, not a hidden limitation -- see the printed NOTE
and docs/decisions/0005 for the reasoning and the extrapolation evidence.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from configs import settings
from scripts.prepare_hadoop_input import prepare_benchmark_input
from scripts.run_hadoop_job import run_job
from src.business.canonical import build_canonical_dataset
from src.business.enums import DataOrigin
from src.optimization.vectorized_canonical import build_canonical_dataset_vectorized

DEFAULT_SCALES = [100_000, 500_000, 1_000_000]
DEFAULT_HADOOP_SCALES = [100_000]  # only the smallest scale gets a real/auto Hadoop run by default


def _load_scale_input(scale: int) -> pd.DataFrame:
    input_dir = settings.BENCHMARK_SCALE_INPUT_DIR / f"scale_{scale}"
    parts = sorted(input_dir.glob("part-*.parquet"))
    if not parts:
        raise SystemExit(f"No input partitions for scale {scale} under {input_dir}. "
                          f"Run: python scripts/generate_benchmark_dataset.py --scale {scale}")
    return pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)


def _generation_time(scale: int) -> float | None:
    meta_path = settings.BENCHMARK_SCALE_METADATA_DIR / f"scale_{scale}.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8")).get("generation_wall_clock_seconds")


def _time_reps(fn, n_reps: int) -> list[float]:
    out = []
    for _ in range(n_reps):
        t0 = time.perf_counter()
        fn()
        out.append(time.perf_counter() - t0)
    return out


def _reps_for_scale(scale: int) -> tuple[int, int]:
    """Returns (baseline_reps, vectorized_reps). Baseline is O(n) per-row
    Python and gets slow fast; large scales get 1 exploratory rep."""
    if scale <= 100_000:
        return 3, 5
    if scale <= 500_000:
        return 1, 5
    return 1, 3


def benchmark_scale(scale: int, run_hadoop: bool) -> dict:
    print(f"\n=== scale {scale:,} ===")
    df = _load_scale_input(scale)
    n_rows = len(df)

    baseline_reps, vectorized_reps = _reps_for_scale(scale)

    baseline_times = _time_reps(lambda: build_canonical_dataset(df, data_origin=DataOrigin.SYNTHETIC), baseline_reps)
    baseline_median = statistics.median(baseline_times)
    print(f"  local baseline  : median={baseline_median:.3f}s over {baseline_reps} rep(s) "
          f"({n_rows / baseline_median:,.0f} rows/s)"
          + (" [EXPLORATORY: 1 run -- see note below]" if baseline_reps == 1 else ""))

    vectorized_times = _time_reps(
        lambda: build_canonical_dataset_vectorized(df, data_origin=DataOrigin.SYNTHETIC), vectorized_reps
    )
    vectorized_median = statistics.median(vectorized_times)
    print(f"  local vectorized: median={vectorized_median:.3f}s over {vectorized_reps} rep(s) "
          f"({n_rows / vectorized_median:,.0f} rows/s)")

    result = {
        "scale": scale,
        "rows": n_rows,
        "generation_wall_clock_seconds": _generation_time(scale),
        "local_baseline_median_s": round(baseline_median, 4),
        "local_baseline_reps": baseline_reps,
        "local_baseline_exploratory": baseline_reps == 1,
        "local_baseline_throughput_rows_per_s": round(n_rows / baseline_median, 1),
        "local_vectorized_median_s": round(vectorized_median, 4),
        "local_vectorized_reps": vectorized_reps,
        "local_vectorized_throughput_rows_per_s": round(n_rows / vectorized_median, 1),
        "hadoop": None,
    }

    if run_hadoop:
        print(f"  preparing Hadoop input for scale {scale:,}...")
        t0 = time.perf_counter()
        input_tsv = prepare_benchmark_input(scale)
        input_conversion_s = time.perf_counter() - t0
        print(f"    input conversion: {input_conversion_s:.2f}s -> {input_tsv}")

        print("  running MapReduce job (real cluster if reachable, else local-emulation)...")
        t0 = time.perf_counter()
        job = run_job(input_tsv, settings.MAPREDUCE_BENCHMARK_DIR, label=f"scale_{scale}", mode="auto")
        total_job_s = time.perf_counter() - t0
        print(f"    mode={job.mode}, total={total_job_s:.2f}s, phases={job.timings_seconds}")

        result["hadoop"] = {
            "mode": job.mode,
            "input_conversion_s": round(input_conversion_s, 3),
            "phase_timings_s": job.timings_seconds,
            "total_job_s": round(total_job_s, 3),
            "total_end_to_end_s": round(input_conversion_s + total_job_s, 3),
            "reps": 1,
            "exploratory": True,
            "exploratory_reason": (
                "Real/emulated Hadoop run timed once per scale in this session: at this cluster's "
                "measured per-task overhead (~1 vCPU, 384MB containers per worker -- see "
                "docs/decisions/0005), a single run at the smallest required scale already took "
                "several minutes; three repetitions across all required scales was not practical "
                "within the session's time budget. See docs/decisions/0005 for the full reasoning "
                "and the extrapolation used to decide which scales got a real-cluster attempt."
            ),
            "environment": job.environment,
        }

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scales", type=int, nargs="+", default=DEFAULT_SCALES)
    parser.add_argument("--hadoop-scales", type=int, nargs="*", default=DEFAULT_HADOOP_SCALES)
    args = parser.parse_args()

    settings.OUTPUTS_BENCHMARKS.mkdir(parents=True, exist_ok=True)
    results = []
    for scale in args.scales:
        results.append(benchmark_scale(scale, run_hadoop=scale in args.hadoop_scales))

    out_path = settings.OUTPUTS_BENCHMARKS / "phase2_results.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n-> {out_path}")

    print("\n=== Summary ===")
    for r in results:
        hadoop_note = ""
        if r["hadoop"]:
            hadoop_note = f", hadoop({r['hadoop']['mode']})={r['hadoop']['total_end_to_end_s']:.1f}s"
        print(f"scale={r['scale']:>9,}  baseline={r['local_baseline_median_s']:.3f}s  "
              f"vectorized={r['local_vectorized_median_s']:.3f}s{hadoop_note}")


if __name__ == "__main__":
    main()
