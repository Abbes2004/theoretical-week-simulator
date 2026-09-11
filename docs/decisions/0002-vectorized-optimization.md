# Decision 0002 — Vectorized optimization of the canonical-build stage

Status: Accepted (Phase 1). Date: 2026-09-10.

## Measured baseline

`benchmarks/baseline/run_benchmark.py` measured the naive, per-row
canonical-build stage (`src/business/canonical.build_canonical_dataset`,
implemented with `DataFrame.iterrows()` and one pure-function call per
row) on the real 12,302-row POI extract and on four reproducible synthetic
datasets (1k/10k/100k/500k rows, seed=42):

| Dataset | Rows | Baseline median | Throughput |
|---|---:|---:|---:|
| real_12302 | 12,302 | 3.26 s | 3,771 rows/s |
| synthetic_small_1k | 1,000 | 0.21 s | 4,658 rows/s |
| synthetic_medium_10k | 10,000 | 2.18 s | 4,580 rows/s |
| synthetic_large_100k | 100,000 | 24.02 s | 4,163 rows/s |
| synthetic_stress_500k | 500,000 | 119.95 s | 4,168 rows/s |

(Environment: single local machine, CPython 3.14.4, pandas 3.0.2, Windows;
timings are `time.perf_counter()` medians, see the script for repetition
counts. Full numbers: outputs/benchmarks/baseline_results.json.)

Throughput is essentially flat (~4,000-4,700 rows/s) across dataset sizes,
i.e. the cost is linear in row count with no evidence of a size-dependent
bottleneck (no quadratic joins, no blow-up) — consistent with
docs/execution/09_pipeline_architecture.md's warning to profile before
distributing anything.

## Bottleneck (measured, not assumed)

`benchmarks/baseline/profile_bottleneck.py` (cProfile, 10,000 synthetic
rows, full output in outputs/benchmarks/bottleneck_profile.txt) shows the
5.4s run split roughly as:

- `DataFrame.iterrows()` machinery (Series construction per row,
  `__getitem__`/`.get()` per cell): ~2.5s cumulative — the dominant cost,
  not the business logic itself.
- `datetime.strptime` (called once per component per row, including
  locale lookups via `_strptime`/`locale.getlocale`): ~1.5s cumulative.
- The actual `calculate_theoretical_week` control flow (comparisons,
  dataclass construction): a small remainder.

Conclusion: **the bottleneck is per-row Python/pandas overhead, not the
`MAX()` calculation itself** — exactly the caution in
docs/execution/12_hadoop_mapreduce_plan.md ("do not distribute a trivial
`MAX()` operation merely for demonstration... if the real bottleneck is
preparation, the distributed design should address that bottleneck").
This also means a Phase-2 Hadoop prototype must not assume the mapper/
reducer split alone would help; the same per-record overhead would exist
per mapper task unless the record processing itself is vectorized or
batched.

## Optimization implemented

`src/optimization/vectorized_canonical.py` re-implements the exact same
logical calculation as the baseline (`ALL_REQUIRED` policy only — the
baseline's per-POI `applicability_overrides` parameter is not exposed here
because neither the real nor the synthetic benchmark data uses it) using
column-wise pandas/numpy operations:

- all five date columns parsed in one vectorized `pd.to_datetime` pass
  (fast path matching the real 'YYYY-MM-DD' format), with a fallback to
  the slow per-value parser only for the (rare) values that fail the fast
  path;
- missing/invalid/suspicious classification via boolean array operations;
- `date_theorique` via `DataFrame.max(axis=1)` over the five parsed
  columns;
- `blocking_element` via a boolean equality matrix instead of a per-row
  dataclass rebuild.

## Correctness gate

Speed is worthless without correctness. `tests/unit/test_vectorized_equivalence.py`
runs both implementations over the same input (3 synthetic seeds x 800
rows, and the full real 12,302-row extract) and asserts row-for-row
identical output on every field that matters
(`date_theorique`, `iso_year`/`iso_week`, `week_key`, `blocking_element`,
`calculation_status`, `missing_components`, `invalid_components`). All
pass. This mirrors the correctness requirement
docs/execution/12_hadoop_mapreduce_plan.md sets for a future Hadoop
version (`HadoopResult == LocalResult`).

## Measured result

| Dataset | Rows | Baseline | Vectorized | Speedup |
|---|---:|---:|---:|---:|
| real_12302 | 12,302 | 3.26 s | 0.21 s | 15.3x |
| synthetic_small_1k | 1,000 | 0.21 s | 0.061 s | 3.5x |
| synthetic_medium_10k | 10,000 | 2.18 s | 0.32 s | 6.9x |
| synthetic_large_100k | 100,000 | 24.02 s | 3.12 s | 7.7x |
| synthetic_stress_500k | 500,000 | 119.95 s | 15.09 s | 8.0x |

(Same run as above; see outputs/benchmarks/baseline_results.csv for raw
numbers and repetition counts.)

The real-extract speedup (15.3x) is higher than the synthetic speedups
(3.5-8.0x) because almost every real row hits the same missing-component
short-circuit (`INCOMPLETE_DATA`, TISSU/TISSU_SEC both 100% NULL), which
the vectorized boolean-array path handles even more cheaply than the mixed
synthetic workload; this is a real, reproducible property of the extract's
data-quality profile, not a benchmark artifact — see Decision 0001.

## Not done in Phase 1 (explicitly out of scope)

- No further micro-optimization (e.g. Cython, multiprocessing) was
  attempted: MASTER_PROMPT.md requires optimizing "only where justified by
  evidence," and the vectorized version already removes the measured
  bottleneck by roughly an order of magnitude.
- No Hadoop/MapReduce implementation — Phase 2, per the user's Phase 1
  instructions.
