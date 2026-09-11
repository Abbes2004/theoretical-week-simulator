"""Derive a Hadoop-compatible TSV input file from an existing dataset.

This is the "Hadoop input representation" step: it reads an already
generated dataset's wide-form POI table (5 date columns) and reshapes it
into the long-form component-event representation
(Id_Sim, POI_Sim, component_name, availability_date, DATA_ORIGIN),
documented in docs/decisions/0004-hadoop-environment-and-benchmark-design.md
as a SYNTHETIC COMPUTATIONAL BENCHMARK REPRESENTATION, not a confirmed
company schema.

Never writes into data/synthetic/demo_2025_2026/ or
data/synthetic/benchmark_scale_2025_2026/{input,component_events,canonical_reference}/
-- output always goes to outputs/mapreduce/ or
data/synthetic/benchmark_scale_2025_2026/hadoop_input/ (a new, additive
subfolder of that tree, never touching the four required subfolders).

Usage:
    python scripts/prepare_hadoop_input.py --source demo
    python scripts/prepare_hadoop_input.py --source benchmark --scale 100000
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs import settings
from src.ingestion.synthetic_benchmark_generator import to_component_events


def prepare_demo_input() -> Path:
    if not settings.DEMO_INPUT_PARQUET.exists():
        raise SystemExit(
            f"{settings.DEMO_INPUT_PARQUET} not found. Run "
            "`python scripts/generate_demo_dataset.py` first."
        )
    df = pd.read_parquet(settings.DEMO_INPUT_PARQUET)  # read-only
    events = to_component_events(df)

    settings.MAPREDUCE_DEMO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = settings.MAPREDUCE_DEMO_DIR / "events.tsv"
    events.to_csv(out_path, sep="\t", index=False, header=False)
    print(f"{len(df):,} POIs -> {len(events):,} component events -> {out_path}")
    return out_path


def prepare_benchmark_input(scale: int) -> Path:
    events_dir = settings.BENCHMARK_SCALE_EVENTS_DIR / f"scale_{scale}"
    if not events_dir.exists():
        raise SystemExit(
            f"{events_dir} not found. Run "
            f"`python scripts/generate_benchmark_dataset.py --scale {scale}` first."
        )
    part_files = sorted(events_dir.glob("part-*.parquet"))
    if not part_files:
        raise SystemExit(f"No partition files found under {events_dir}")

    settings.BENCHMARK_SCALE_HADOOP_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = settings.BENCHMARK_SCALE_HADOOP_INPUT_DIR / f"scale_{scale}.tsv"

    total_events = 0
    t0 = time.time()
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        for i, part_path in enumerate(part_files):
            part = pd.read_parquet(part_path)  # read-only; one partition at a time
            part.to_csv(fh, sep="\t", index=False, header=False, lineterminator="\n")
            total_events += len(part)
            del part
            print(f"  partition {i + 1}/{len(part_files)} ({part_path.name}) written "
                  f"({total_events:,} events so far)")
    elapsed = time.time() - t0
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"{total_events:,} component events -> {out_path} ({size_mb:.1f} MB, {elapsed:.1f}s)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["demo", "benchmark"], required=True)
    parser.add_argument("--scale", type=int, help="Required when --source benchmark.")
    args = parser.parse_args()

    if args.source == "demo":
        prepare_demo_input()
    else:
        if args.scale is None:
            parser.error("--scale is required when --source benchmark")
        prepare_benchmark_input(args.scale)


if __name__ == "__main__":
    main()
