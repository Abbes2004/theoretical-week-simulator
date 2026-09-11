"""Correctness gate: compare the MapReduce (real Hadoop or local-emulation)
output against the local vectorized canonical reference, field by field.

Usage:
    python scripts/compare_hadoop_local.py --source demo
    python scripts/compare_hadoop_local.py --source benchmark --scale 100000

Runs, in order:
    1. scripts/prepare_hadoop_input.py (derive the long-form TSV, if not already present)
    2. scripts/run_hadoop_job.py       (mapper -> shuffle -> reducer)
    3. loads the corresponding canonical reference (the demo canonical
       output for --source demo; canonical_reference/scale_<N>/*.parquet
       for --source benchmark, which was computed by the SAME vectorized
       engine at generation time)
    4. compares every comparable POI on:
       Id_Sim, POI_Sim, date_theorique, iso_year, iso_week, week_key,
       sem_theorique, blocking_element, calculation_status

Writes a JSON report and exits non-zero if any mismatch is found -- this
script never claims correctness it did not verify.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs import settings
from scripts.prepare_hadoop_input import prepare_benchmark_input, prepare_demo_input
from scripts.run_hadoop_job import run_job

_HADOOP_OUTPUT_COLUMNS = (
    "id_sim", "poi_sim", "date_theorique", "iso_year", "iso_week",
    "week_key", "sem_theorique", "blocking_element", "calculation_status",
)


def _load_hadoop_output(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", header=None, names=_HADOOP_OUTPUT_COLUMNS, dtype=str, keep_default_na=False)
    df["blocking_element"] = df["blocking_element"].apply(lambda s: sorted(s.split(";")) if s else [])
    return df


def _load_reference(source: str, scale: int | None) -> pd.DataFrame:
    if source == "demo":
        ref = pd.read_parquet(settings.DEMO_CANONICAL_PARQUET)
    else:
        ref_dir = settings.BENCHMARK_SCALE_REFERENCE_DIR / f"scale_{scale}"
        parts = sorted(ref_dir.glob("part-*.parquet"))
        if not parts:
            raise SystemExit(f"No canonical reference partitions found under {ref_dir}")
        ref = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)

    out = ref[["id_sim", "poi_sim", "date_theorique", "iso_year", "iso_week", "week_key",
               "sem_theorique", "blocking_element", "calculation_status"]].copy()
    out["id_sim"] = out["id_sim"].astype(str)
    out["date_theorique"] = out["date_theorique"].apply(lambda d: d.isoformat() if pd.notna(d) and d is not None else "")
    out["iso_year"] = out["iso_year"].apply(lambda v: str(int(v)) if pd.notna(v) else "")
    out["iso_week"] = out["iso_week"].apply(lambda v: str(int(v)) if pd.notna(v) else "")
    out["week_key"] = out["week_key"].fillna("")
    out["sem_theorique"] = out["sem_theorique"].fillna("")
    out["blocking_element"] = out["blocking_element"].apply(_normalize_blocking_element)
    return out


def _normalize_blocking_element(v) -> list[str]:
    """`blocking_element` is a Python list in the demo canonical parquet
    (never round-tripped through a string join) but a semicolon-joined
    string in the benchmark canonical_reference parquet (flattened before
    writing, for CSV-friendliness -- see
    src/ingestion/synthetic_benchmark_generator.py). Handle both, plus the
    numpy-array shape a parquet round-trip can produce for list columns
    (see the regression documented in tests/unit/test_webapp.py)."""
    if isinstance(v, str):
        return sorted(v.split(";")) if v else []
    if isinstance(v, list):
        return sorted(v)
    if hasattr(v, "tolist"):
        return sorted(v.tolist())
    return []


def compare(hadoop_df: pd.DataFrame, reference_df: pd.DataFrame) -> dict:
    merged = hadoop_df.merge(
        reference_df, on=["id_sim", "poi_sim"], how="outer", suffixes=("_hadoop", "_local"), indicator=True
    )

    only_hadoop = merged[merged["_merge"] == "left_only"]
    only_local = merged[merged["_merge"] == "right_only"]
    both = merged[merged["_merge"] == "both"].copy()

    compare_fields = ["date_theorique", "iso_year", "iso_week", "week_key", "sem_theorique",
                       "calculation_status"]
    mismatches = []
    for field in compare_fields:
        diff_mask = both[f"{field}_hadoop"] != both[f"{field}_local"]
        for _, row in both[diff_mask].iterrows():
            mismatches.append(
                {
                    "id_sim": row["id_sim"], "poi_sim": row["poi_sim"], "field": field,
                    "hadoop": row[f"{field}_hadoop"], "local": row[f"{field}_local"],
                }
            )

    blocking_diff_mask = both.apply(
        lambda r: sorted(r["blocking_element_hadoop"]) != sorted(r["blocking_element_local"]), axis=1
    )
    for _, row in both[blocking_diff_mask].iterrows():
        mismatches.append(
            {
                "id_sim": row["id_sim"], "poi_sim": row["poi_sim"], "field": "blocking_element",
                "hadoop": row["blocking_element_hadoop"], "local": row["blocking_element_local"],
            }
        )

    return {
        "compared_pois": len(both),
        "only_in_hadoop_output": len(only_hadoop),
        "only_in_local_reference": len(only_local),
        "field_mismatches": len(mismatches),
        "mismatch_examples": mismatches[:20],
        "exact_match": len(only_hadoop) == 0 and len(only_local) == 0 and len(mismatches) == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=["demo", "benchmark"], required=True)
    parser.add_argument("--scale", type=int)
    parser.add_argument("--mode", choices=["auto", "real", "local-emulation"], default="auto")
    args = parser.parse_args()

    if args.source == "benchmark" and args.scale is None:
        parser.error("--scale is required when --source benchmark")

    label = "demo" if args.source == "demo" else f"scale_{args.scale}"

    print(f"[1/3] Preparing Hadoop input ({label})...")
    if args.source == "demo":
        input_path = prepare_demo_input()
        work_dir = settings.MAPREDUCE_DEMO_DIR
    else:
        input_path = prepare_benchmark_input(args.scale)
        work_dir = settings.MAPREDUCE_BENCHMARK_DIR

    print("[2/3] Running the MapReduce job...")
    t0 = time.time()
    job_result = run_job(input_path, work_dir, label, mode=args.mode)
    print(f"    mode={job_result.mode}, {time.time() - t0:.1f}s wall clock")

    print("[3/3] Comparing against the local vectorized canonical reference...")
    hadoop_df = _load_hadoop_output(Path(job_result.output_path))
    reference_df = _load_reference(args.source, args.scale)
    report = compare(hadoop_df, reference_df)
    report["source"] = args.source
    report["scale"] = args.scale
    report["job_mode"] = job_result.mode

    report_path = work_dir / f"{label}.correctness_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"\nCompared POIs: {report['compared_pois']:,}")
    print(f"Only in Hadoop output: {report['only_in_hadoop_output']}")
    print(f"Only in local reference: {report['only_in_local_reference']}")
    print(f"Field mismatches: {report['field_mismatches']}")
    print(f"EXACT MATCH: {report['exact_match']}")
    print(f"-> {report_path}")

    if not report["exact_match"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
