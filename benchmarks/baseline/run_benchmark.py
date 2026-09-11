"""Reproducible baseline benchmark.

Measures the wall-clock time of the canonical-dataset build stage (the
theoretical-week calculation applied to every POI) for both the naive
per-row baseline (src/business/canonical.py) and the vectorized
optimization (src/optimization/vectorized_canonical.py), across the real
extract and several synthetic dataset sizes.

Usage (from the project root, after `python scripts/generate_synthetic_dataset.py`):

    python benchmarks/baseline/run_benchmark.py

Writes:
    outputs/benchmarks/baseline_results.csv
    outputs/benchmarks/baseline_results.json
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from configs import settings
from src.business.canonical import build_canonical_dataset
from src.business.enums import DataOrigin
from src.optimization.vectorized_canonical import build_canonical_dataset_vectorized

# (dataset_label, loader, data_origin, repetitions_baseline, repetitions_optimized)
_REAL_PATH = settings.RAW_SQL_FILES["plan_t_simplanifpoi"]


def _load_real() -> pd.DataFrame:
    from src.ingestion.sql_ingestion import load_sql_table_as_dataframe

    return load_sql_table_as_dataframe(_REAL_PATH)


def _load_synthetic(name: str) -> pd.DataFrame:
    return pd.read_parquet(settings.BENCHMARK_DATASETS_DIR / f"synthetic_{name}.parquet")


DATASETS = [
    {"label": "real_12302", "loader": _load_real, "origin": DataOrigin.REAL, "reps_baseline": 3, "reps_opt": 5,
     "available": _REAL_PATH.exists()},
    {"label": "synthetic_small_1k", "loader": lambda: _load_synthetic("small"), "origin": DataOrigin.SYNTHETIC,
     "reps_baseline": 5, "reps_opt": 10,
     "available": (settings.BENCHMARK_DATASETS_DIR / "synthetic_small.parquet").exists()},
    {"label": "synthetic_medium_10k", "loader": lambda: _load_synthetic("medium"), "origin": DataOrigin.SYNTHETIC,
     "reps_baseline": 3, "reps_opt": 5,
     "available": (settings.BENCHMARK_DATASETS_DIR / "synthetic_medium.parquet").exists()},
    {"label": "synthetic_large_100k", "loader": lambda: _load_synthetic("large"), "origin": DataOrigin.SYNTHETIC,
     "reps_baseline": 1, "reps_opt": 5,
     "available": (settings.BENCHMARK_DATASETS_DIR / "synthetic_large.parquet").exists()},
    {"label": "synthetic_stress_500k", "loader": lambda: _load_synthetic("stress"), "origin": DataOrigin.SYNTHETIC,
     "reps_baseline": 1, "reps_opt": 3,
     "available": (settings.BENCHMARK_DATASETS_DIR / "synthetic_stress.parquet").exists()},
]


def _time_calls(fn, n_reps: int) -> list[float]:
    timings = []
    for _ in range(n_reps):
        t0 = time.perf_counter()
        fn()
        timings.append(time.perf_counter() - t0)
    return timings


def run() -> list[dict]:
    results = []
    for spec in DATASETS:
        if not spec["available"]:
            print(f"skip {spec['label']}: dataset not found (generate it first)")
            continue

        df = spec["loader"]()
        n_rows = len(df)
        print(f"\n=== {spec['label']} ({n_rows:,} rows) ===")

        baseline_times = _time_calls(
            lambda: build_canonical_dataset(df, data_origin=spec["origin"]), spec["reps_baseline"]
        )
        baseline_median = statistics.median(baseline_times)
        print(f"  baseline   : median={baseline_median:.4f}s over {len(baseline_times)} run(s) "
              f"({n_rows / baseline_median:,.0f} rows/s)")

        optimized_times = _time_calls(
            lambda: build_canonical_dataset_vectorized(df, data_origin=spec["origin"]), spec["reps_opt"]
        )
        optimized_median = statistics.median(optimized_times)
        print(f"  vectorized : median={optimized_median:.4f}s over {len(optimized_times)} run(s) "
              f"({n_rows / optimized_median:,.0f} rows/s)")
        print(f"  speedup    : {baseline_median / optimized_median:.1f}x")

        results.append(
            {
                "dataset": spec["label"],
                "rows": n_rows,
                "baseline_median_s": round(baseline_median, 5),
                "baseline_reps": len(baseline_times),
                "baseline_throughput_rows_per_s": round(n_rows / baseline_median, 1),
                "vectorized_median_s": round(optimized_median, 5),
                "vectorized_reps": len(optimized_times),
                "vectorized_throughput_rows_per_s": round(n_rows / optimized_median, 1),
                "speedup_x": round(baseline_median / optimized_median, 2),
            }
        )
    return results


def main() -> None:
    settings.OUTPUTS_BENCHMARKS.mkdir(parents=True, exist_ok=True)
    results = run()

    out_json = settings.OUTPUTS_BENCHMARKS / "baseline_results.json"
    out_csv = settings.OUTPUTS_BENCHMARKS / "baseline_results.csv"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    pd.DataFrame(results).to_csv(out_csv, index=False)
    print(f"\nResults written to {out_json} and {out_csv}")


if __name__ == "__main__":
    main()
