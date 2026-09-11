"""Generate the SYNTHETIC demonstration dataset (pre-Phase-2).

Usage (from the project root):

    python scripts/generate_demo_dataset.py

Reads data/raw/sql/plan_t_simplanifpoi.sql READ-ONLY (only to borrow
realistic POI_Sim identifier strings and to check whether any real date
happens to already fall in the demo's [2025-01-01, 2026-06-30] window --
see src/ingestion/synthetic_demo_dataset.py). Writes ONLY under
data/synthetic/demo_2025_2026/ -- never touches data/raw/, data/interim/,
data/processed/, or data/canonical/ (the real derived-data tree).

Produces:
    data/synthetic/demo_2025_2026/input/poi_demo_synthetic_completed.parquet
    data/synthetic/demo_2025_2026/input/poi_demo_synthetic_completed.csv
    data/synthetic/demo_2025_2026/canonical/poi_demo_synthetic_canonical.parquet
    data/synthetic/demo_2025_2026/canonical/poi_demo_synthetic_canonical.csv
    data/synthetic/demo_2025_2026/metadata/generation_metadata.json
    data/synthetic/demo_2025_2026/metadata/README.md
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs import settings
from src.business.canonical import build_canonical_dataset
from src.business.enums import DataOrigin
from src.ingestion.synthetic_demo_dataset import build_demo_dataset


def _flatten_list_column(series):
    return series.apply(lambda v: ";".join(v) if isinstance(v, list) else v)


def _write_csv_friendly(df, path: Path) -> None:
    out = df.copy()
    for col in ("blocking_element", "missing_components", "invalid_components", "suspicious_components", "data_quality_flag"):
        if col in out.columns:
            out[col] = _flatten_list_column(out[col])
    out.to_csv(path, index=False)


def main() -> None:
    for d in (settings.DEMO_INPUT_DIR, settings.DEMO_CANONICAL_DIR, settings.DEMO_METADATA_DIR):
        d.mkdir(parents=True, exist_ok=True)

    real_poi_df = None
    real_path = settings.RAW_SQL_FILES["plan_t_simplanifpoi"]
    if real_path.exists():
        print(f"[1/4] Reading (read-only) {real_path.name} for POI_Sim identifier scaffold...")
        from src.ingestion.sql_ingestion import load_sql_table_as_dataframe

        real_poi_df = load_sql_table_as_dataframe(real_path)
        print(f"    {len(real_poi_df):,} real POI rows available as an identifier source")
    else:
        print("[1/4] Real POI extract not found -- generating demo identifiers without a real scaffold.")

    print("[2/4] Building the SYNTHETIC demo input table...")
    demo_df, stats = build_demo_dataset(real_poi_df)
    print(f"    {stats.n_edge_cases} curated edge-case rows + {stats.n_bulk} bulk rows = {len(demo_df)} total")
    print(f"    date preservation check (real date valid AND in [{stats.range_start}, {stats.range_end}]): "
          f"{stats.preserved_from_real or '{} (none)'}")
    print(f"    synthetic replacements generated: {stats.replaced_synthetic}")

    demo_df.to_parquet(settings.DEMO_INPUT_PARQUET, index=False)
    demo_df.to_csv(settings.DEMO_INPUT_CSV, index=False)
    print(f"    -> {settings.DEMO_INPUT_PARQUET}")
    print(f"    -> {settings.DEMO_INPUT_CSV}")

    print("[3/4] Running the existing business-rule engine (DATA_ORIGIN=SYNTHETIC)...")
    canonical = build_canonical_dataset(demo_df, data_origin=DataOrigin.SYNTHETIC)
    canonical.to_parquet(settings.DEMO_CANONICAL_PARQUET, index=False)
    _write_csv_friendly(canonical, settings.DEMO_CANONICAL_CSV)
    print(f"    -> {settings.DEMO_CANONICAL_PARQUET}")
    print(f"    -> {settings.DEMO_CANONICAL_CSV}")

    status_counts = canonical["calculation_status"].value_counts().to_dict()
    blocking_counter: Counter[str] = Counter()
    for elements in canonical["blocking_element"]:
        for e in elements:
            blocking_counter[e] += 1
    origin_counts = canonical["data_origin"].value_counts().to_dict()

    print("[4/4] Writing metadata...")
    metadata = {
        "data_origin": "SYNTHETIC",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": stats.seed,
        "range_start": stats.range_start,
        "range_end": stats.range_end,
        "id_sim_sentinel": settings.DEMO_ID_SIM,
        "row_counts": {
            "edge_cases": stats.n_edge_cases,
            "bulk": stats.n_bulk,
            "total": len(demo_df),
        },
        "real_poi_sim_source_count": stats.real_poi_sim_source_count,
        "date_preservation": {
            "preserved_from_real_per_component": stats.preserved_from_real,
            "replaced_with_synthetic_per_component": stats.replaced_synthetic,
            "note": (
                "A real component date is preserved only if it parses as a valid "
                "date AND falls within [range_start, range_end]. The real POI "
                "extract's populated dates are all from 2021 (outside this "
                "2025-2026 window), so in practice every date was replaced -- "
                "see docs/decisions/0003-synthetic-demo-dataset.md."
            ),
        },
        "calculation_status_distribution": status_counts,
        "blocking_element_distribution": dict(blocking_counter),
        "data_origin_distribution": origin_counts,
        "generator": "src/ingestion/synthetic_demo_dataset.py:build_demo_dataset",
        "reproducibility": "Deterministic for a fixed seed: random.Random(seed) + pandas DataFrame.sample(random_state=seed).",
    }
    settings.DEMO_METADATA_JSON.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    print(f"    -> {settings.DEMO_METADATA_JSON}")

    readme = f"""# Synthetic Demo Dataset (demo_2025_2026)

**DATA_ORIGIN = SYNTHETIC.** This is NOT real company data. Every date in
this dataset was either generated by a seeded random-number generator or
(rarely, and explicitly logged above) preserved from a real date that
happened to already fall in the target window. See
`docs/decisions/0003-synthetic-demo-dataset.md` for the full rationale.

## What this is

A small, fully-calculable POI dataset built specifically so the Phase 1
simulator and web UI can demonstrate a `CALCULATED` result, a blocking
component, and a tie -- none of which the real `plan_t_simplanifpoi`
extract can produce (100% of its rows are `INCOMPLETE_DATA`; see
`docs/decisions/0001-phase1-scope-and-key-decisions.md`).

## Generation parameters

- Seed: `{stats.seed}` (fixed, reproducible -- re-running
  `python scripts/generate_demo_dataset.py` produces byte-identical output)
- Date range: `{stats.range_start}` to `{stats.range_end}` (inclusive)
- Rows: {stats.n_edge_cases} curated edge cases + {stats.n_bulk} bulk rows = {len(demo_df)} total
- `Id_Sim` sentinel: `{settings.DEMO_ID_SIM}` (outside every real `Id_Sim` range observed
  in `plan_t_simplanif` (10775-12039), `plan_t_simplanifpoi` (5601), and
  `plan_t_simplanifstock` (3322-10876), so a demo row can never be mistaken
  for, or accidentally joined with, a real one)
- `POI_Sim` for the {stats.n_bulk} bulk rows: identifier *strings* reused from the
  real extract (`{stats.real_poi_sim_source_count:,}` rows available as source), always paired
  with the sentinel `Id_Sim` above -- the real Id_Sim/POI_Sim *pair* is never reused.
- `POI_Sim` for the {stats.n_edge_cases} edge-case rows: descriptive synthetic identifiers
  (`DEMO-EDGE-<case>`), not derived from real data at all.
- `SemTheorique` / `DateMax` (the historical/reference columns) are left
  NULL in the input table: this dataset has no historical reference to
  compare against, and inventing one would fabricate an unconfirmed
  manual-override relationship.

## Status distribution

```json
{json.dumps(status_counts, indent=2)}
```

## Blocking-element distribution (across all CALCULATED rows)

```json
{json.dumps(dict(blocking_counter), indent=2)}
```

## Edge cases included (deterministic, not random)

| Key | What it demonstrates |
|---|---|
| `BLOCK_TISSU` / `BLOCK_TISSU_SEC` / `BLOCK_FOURNITURE` / `BLOCK_FIL` / `BLOCK_OK_PRODUCTION` | Each of the five components as the sole blocking element |
| `TIE_2WAY` | TISSU and FIL tie for the latest date |
| `TIE_3WAY` | TISSU, TISSU_SEC and OK_PRODUCTION tie for the latest date |
| `TIE_5WAY` | All five components share the exact same date |
| `RANGE_START` | All components dated exactly {stats.range_start} |
| `RANGE_END` | Blocking component dated exactly {stats.range_end} |
| `ISO_YEAR_BOUNDARY_2025_12_29/30/31` | Calendar year 2025, ISO week-year 2026 (ISO week 01) -- the only place in this date range where the calendar year differs from the ISO week-year (verified directly with `date.isocalendar()`; no equivalent case exists near the start of the range) |

## Commands

```bash
# 1. Generate (deterministic; re-running overwrites only this demo tree)
python scripts/generate_demo_dataset.py

# 2. Validate
python -m pytest tests/validation/test_synthetic_demo_dataset.py -q

# 3. Launch the UI on the demo dataset
python scripts/cli.py serve --dataset demo

# 4. Return to the real dataset (default; no flag needed)
python scripts/cli.py serve
```
"""
    settings.DEMO_METADATA_README.write_text(readme, encoding="utf-8")
    print(f"    -> {settings.DEMO_METADATA_README}")

    print("\nStatus distribution:", status_counts)
    print("Blocking-element distribution:", dict(blocking_counter))


if __name__ == "__main__":
    main()
