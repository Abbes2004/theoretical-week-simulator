"""Generate reproducible synthetic POI datasets for benchmarking.

Usage:
    python scripts/generate_synthetic_dataset.py

Writes benchmarks/datasets/synthetic_<size>.parquet plus a
.meta.json sidecar recording the generation parameters (seed, row count,
mix), so every benchmark dataset is reproducible and clearly distinguished
from real company data (MASTER_PROMPT.md section 2.3).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.settings import BENCHMARK_DATASETS_DIR, RANDOM_SEED
from src.ingestion.synthetic_generator import generate_synthetic_poi_rows

SIZES = {
    "small": 1_000,
    "medium": 10_000,
    "large": 100_000,
    "stress": 500_000,
}


def main() -> None:
    BENCHMARK_DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    for name, n_rows in SIZES.items():
        df = generate_synthetic_poi_rows(n_rows, seed=RANDOM_SEED, id_sim=900000 + hash(name) % 1000)
        out_path = BENCHMARK_DATASETS_DIR / f"synthetic_{name}.parquet"
        df.to_parquet(out_path, index=False)
        meta = {
            "data_origin": "SYNTHETIC",
            "name": name,
            "rows": n_rows,
            "seed": RANDOM_SEED,
            "generator": "src/ingestion/synthetic_generator.py:generate_synthetic_poi_rows",
        }
        (BENCHMARK_DATASETS_DIR / f"synthetic_{name}.meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        print(f"{name}: {n_rows:,} rows -> {out_path}")


if __name__ == "__main__":
    main()
