# Theoretical Week Simulator

Computes the theoretical production week (`SemTheorique`) of a Production
Order Item as the latest availability date among five required components
(main fabric, secondary fabric, accessories/supplies, sewing thread,
production approval), identifies the blocking component(s), and reports an
explicit status instead of guessing when data is missing or invalid.

**Phase 1** (local pipeline, simulator, CLI, web UI) and **Phase 2**
(real Hadoop MapReduce on a 3-VM cluster, correctness validation, scalable
synthetic benchmarks) are both complete. See `docs/report/phase1_summary.md`
for the Phase 1 write-up, and `docs/report/phase2_summary.md` for Phase 2 (Hadoop
correctness/performance results, honestly including that real Hadoop was
found to be dramatically slower than local processing on this hardware).

## Requirements

- Python 3.11+ (developed and tested on 3.14)
- See `requirements.txt`

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Run the pipeline

Ingests the raw SQL dumps under `data/raw/sql/` (never modified), validates
schema/keys/referential integrity, builds the canonical POI dataset, and
compares against historical `SemTheorique` where available:

```bash
python scripts/run_pipeline.py
```

Produces:
- `data/interim/*.raw.parquet` — raw tables, verbatim
- `outputs/results/validation_report.json` — key/referential-integrity report
- `data/canonical/poi_canonical.parquet` and `.csv` — the canonical dataset
- `outputs/results/historical_validation_summary.json` — match-rate summary

## Use the simulator

Look up one POI and see its full calculation, with its component dates,
status, and (when calculable) its theoretical week and blocking element:

```bash
python scripts/cli.py lookup --id-sim 5601 --poi-sim 0133898091CD
```

Print the overall status distribution and historical match rate for the
current canonical dataset:

```bash
python scripts/cli.py stats
```

Launch the web UI (POI lookup + a filterable/paginated browse view):

```bash
python scripts/cli.py serve
```

Then open `http://127.0.0.1:5000`.

## Synthetic demonstration dataset (pre-Phase-2)

The real extract cannot produce a single `CALCULATED` result (see "Known
limitation" below), so the simulator and web UI have a separate,
reproducible, clearly-labelled `DATA_ORIGIN = SYNTHETIC` demo dataset that
CAN — 513 fully-calculable POIs (13 curated edge cases + 500 seeded random
rows) with dates in `2025-01-01`..`2026-06-30`, covering every blocking
component, ties, and the ISO year-boundary. See
`docs/decisions/0003-synthetic-demo-dataset.md` and
`data/synthetic/demo_2025_2026/metadata/README.md` for full detail. It
lives in its own tree (`data/synthetic/demo_2025_2026/`) and can never
overwrite the real canonical dataset.

```bash
# 1. Generate (deterministic, seed=42; re-running overwrites only this demo tree)
python scripts/generate_demo_dataset.py

# 2. Validate
python -m pytest tests/validation/test_synthetic_demo_dataset.py -q

# 3. Launch the UI on the demo dataset (shows a red SYNTHETIC DEMO banner)
python scripts/cli.py serve --dataset demo
#    -- or switch datasets live in the browser via the "Switch to ..." link
#    -- or from the CLI: python scripts/cli.py stats --dataset demo
#                        python scripts/cli.py lookup --id-sim 999999 --poi-sim DEMO-EDGE-TIE_3WAY --dataset demo

# 4. Return to the real dataset (the default; no flag needed)
python scripts/cli.py serve
```

## Run the tests

```bash
python -m pytest tests/ -q
```

86 tests (60 Phase 1 + 26 Phase 2): unit tests for the pure business-rule
engine (including Hypothesis property-based tests), the ISO-week/date-parsing
helpers, the SQL-dump parser, and the web UI's parquet-list-column rendering;
integration tests from a synthetic fixture through to the canonical schema
plus a real-data smoke test; validation tests for the historical match-rate
machinery and for the synthetic demo dataset (determinism, in-range dates,
full calculability, every edge case's expected blocking element/tie/ISO
week, and that real raw files and real canonical outputs are never touched
by generating it); an equivalence test proving the vectorized optimization
produces identical output to the baseline engine on both synthetic data and
the full real extract; and Phase 2 tests for the benchmark-scale generator,
the mapper/reducer subprocess behavior, cluster-helper retry logic, and the
end-to-end Hadoop-vs-local correctness gate.

## Run the benchmarks

```bash
python scripts/generate_synthetic_dataset.py   # writes benchmarks/datasets/synthetic_*.parquet (SYNTHETIC, seeded, reproducible)
python benchmarks/baseline/profile_bottleneck.py
python benchmarks/baseline/run_benchmark.py
```

Writes `outputs/benchmarks/bottleneck_profile.txt` and
`outputs/benchmarks/baseline_results.{json,csv}`. See
`docs/decisions/0002-vectorized-optimization.md` for the methodology and
measured results (baseline vs. vectorized, 3.5x-15.3x faster depending on
dataset composition, all proven logically equivalent by test).

## Phase 2 — Hadoop MapReduce and large-scale benchmarks

Full detail: `docs/decisions/0004-hadoop-environment-and-benchmark-design.md`,
`docs/decisions/0005-real-hadoop-cluster-execution.md`,
`docs/report/phase2_summary.md`. Real execution runs on a 3-VM Hadoop 3.4.2
cluster (VirtualBox: `master` + `worker1` + `worker2`, ~1GB RAM/node) over
SSH; whenever that cluster is unreachable, everything below automatically
falls back to an honestly-labelled **local-emulation** mode (same
mapper/reducer files, no real HDFS/YARN) rather than silently claiming a
distributed run.

```bash
# 1. Generate a benchmark scale (SYNTHETIC, seeded, partitioned Parquet)
python scripts/generate_benchmark_dataset.py --scale 100000
python scripts/generate_benchmark_dataset.py --scale 500000
python scripts/generate_benchmark_dataset.py --scale 1000000
# 5,000,000 is optional and NEVER generated implicitly:
python scripts/generate_benchmark_dataset.py --scale 5000000 --confirm-large

# 2. Correctness gate: MapReduce output vs. the local vectorized reference
python scripts/compare_hadoop_local.py --source demo
python scripts/compare_hadoop_local.py --source benchmark --scale 100000
python scripts/compare_hadoop_local.py --source benchmark --scale 1000000

# 3. Run just the MapReduce job (real cluster if reachable, else local-emulation)
python scripts/prepare_hadoop_input.py --source benchmark --scale 500000
python scripts/run_hadoop_job.py --input data/synthetic/benchmark_scale_2025_2026/hadoop_input/scale_500000.tsv --label scale_500000
python scripts/run_hadoop_job.py --input ... --mode local-emulation   # force local, skip the cluster
python scripts/run_hadoop_job.py --input ... --mode real              # force the cluster, error if unreachable

# 4. Full baseline / vectorized benchmark across scales (Hadoop only for the
#    smallest scale by default -- real-cluster runs take ~20-25 min even at
#    100,000 POIs on this hardware; pass --hadoop-scales to change)
python benchmarks/baseline/run_phase2_benchmark.py
python benchmarks/baseline/run_phase2_benchmark.py --hadoop-scales 100000 500000
```

Confirmed results this session: real cluster exact-matched the local
vectorized reference on **both** the 513-row demo (~15 min) and the
100,000-POI benchmark scale (~23.5 min, 0/100,000 mismatches) — see
`docs/report/phase2_summary.md` for the full numbers, including that real
Hadoop was ~85x slower than local-emulation and ~315x slower than local
vectorized processing on identical, verified-identical output.

Tests: `python -m pytest tests/ -q` (adds generator, mapper/reducer, and
Hadoop/local equivalence tests to the Phase 1 suite — see "Run the tests").
One test (`test_real_cluster_correctness_slow`) submits a real job to the
cluster and is skipped by default (opt in with `TWS_TEST_REAL_CLUSTER=1`);
real-cluster correctness is already verified and documented above.

## Known limitation (data, not code)

The real `plan_t_simplanifpoi` extract (12,302 rows, `Id_Sim=5601`) has
`SemTheorique`, `DateMax`, `DateTissu`, and `DateTissuSec` **100% NULL**,
and no row has more than 3 of the 5 required component dates populated.
Running the pipeline against real data therefore correctly reports every
POI as `INCOMPLETE_DATA` and a historical match rate of `N/A` — this is the
honest, expected result given the supplied data, not a bug. It is exercised
end-to-end and documented in `docs/decisions/0001-phase1-scope-and-key-decisions.md`
and `docs/report/phase1_summary.md`. Engine correctness for the cases the
real data cannot exercise (a complete POI, a tie, a historical match/
mismatch) is proven with the reproducible, clearly-labelled synthetic
generator (`src/ingestion/synthetic_generator.py`) and covered by
`tests/validation/test_historical_validation.py`.

## Project layout

See `docs/architecture/overview.md` for the full module map and data flow.
`data/raw/` is never modified by any part of this codebase — every
ingestion module opens it read-only (see `data/raw/README.md`).

## Documentation index

- `docs/context/`, `docs/analysis/`, `docs/execution/` — pre-existing
  evidence base (data dictionaries, prior SQL/Excel/PDF analysis, execution
  specifications) that this Phase 1 build was implemented against.
- `docs/decisions/` — architectural decisions made in this phase, with
  their evidence and consequences.
- `docs/business_rules/phase1_implementation.md` — every implemented rule,
  labelled CONFIRMED or RECOMMENDATION, with a pointer to the exact code
  location to change if a rule is later confirmed differently.
- `docs/architecture/overview.md` — module map and data flow.
- `docs/report/phase1_summary.md` — the full Phase 1 write-up.
- `docs/decisions/0003-synthetic-demo-dataset.md` — rationale and
  guarantees for the synthetic demo dataset.
