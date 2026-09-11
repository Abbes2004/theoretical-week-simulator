# Phase 1 Architecture Overview

## Module map

```text
configs/settings.py         Paths + business-rule constants (all documented
                             as CONFIRMED/RECOMMENDATION/UNKNOWN inline)

src/ingestion/
  mysql_dump_parser.py       Read-only parser for the mysqldump-style .sql
                              exports (CREATE TABLE + one-row-per-line
                              INSERT). No general MySQL parsing attempted.
  sql_ingestion.py            Loads the 3 raw SQL tables -> DataFrames of
                              raw strings, writes data/interim/*.raw.parquet
  excel_ingestion.py          Loads table.xlsx / cde.xls / consommation
                              tissu par type.xlsx sheets -> DataFrames
  pdf_ingestion.py             Read-only text extraction from the PO PDFs
                              (documentation lineage only, not used by the calculation)
  synthetic_generator.py      Reproducible SYNTHETIC POI generator (seeded,
                              general-purpose mix -- used by Phase 1 tests/benchmarks)
  synthetic_demo_dataset.py   Reproducible SYNTHETIC demo dataset generator
                              (curated edge cases + bulk rows, all fully
                              calculable -- see docs/decisions/0003)

src/preprocessing/
  validation.py                PK uniqueness + referential-integrity checks
  cleaning.py                  Identifier normalization (Id_Sim, POI_Sim,
                              Code_Sim case-folding, Qte numeric coercion)

src/business/                  PURE, I/O-free business logic
  enums.py                     Applicability / CalculationStatus / DataOrigin / QualityFlag
  date_parsing.py               parse_date(): missing vs invalid vs suspicious
  iso_week.py                   ISO-8601 (year, week) conversion
  rules.py                      calculate_theoretical_week(): the MAX() engine
  canonical.py                  Adapts raw POI rows -> canonical schema
                              (docs/execution/08) by calling rules.py per row

src/optimization/
  vectorized_canonical.py       Same logic as canonical.py, vectorized;
                              equivalence enforced by
                              tests/unit/test_vectorized_equivalence.py

src/simulation/
  simulator.py                  Explainable per-POI output + historical
                              validation (match-rate) machinery
  webapp.py                     Flask UI (lookup + browse)

scripts/
  run_pipeline.py                End-to-end: ingest -> validate -> canonical
  cli.py                         click CLI: pipeline / lookup / stats / serve
                                (all data-facing commands take --dataset real|demo)
  generate_synthetic_dataset.py  Writes benchmarks/datasets/synthetic_*.parquet
  generate_demo_dataset.py       Writes data/synthetic/demo_2025_2026/ (see docs/decisions/0003)

benchmarks/baseline/
  run_benchmark.py               Baseline vs vectorized timing, all dataset sizes
  profile_bottleneck.py          cProfile-based bottleneck evidence

tests/
  unit/          Business-rule engine, date parsing, ISO week, dump parser, webapp
                 rendering, vectorized-vs-baseline equivalence (Hypothesis property
                 tests included)
  integration/   raw (fixture SQL) -> canonical -> schema, + real-data smoke test
  validation/    Historical match-rate machinery + synthetic demo dataset
                 (determinism, range/calculability, edge cases, real-data immutability)
```

## Data flow (implemented in Phase 1)

```text
data/raw/sql/*.sql  ───────────────►  sql_ingestion.py  ──►  data/interim/*.raw.parquet
                                                                     │
                                            validation.py  ◄─────────┘  (PK + referential report)
                                                                     │
                                            canonical.py  (or vectorized_canonical.py)
                                                                     │
                                                                     ▼
                                              data/canonical/poi_canonical.parquet / .csv
                                                                     │
                                        simulator.py (lookup / batch / historical validation)
                                                                     │
                                          scripts/cli.py  &  src/simulation/webapp.py
```

`plan_t_simplanif` and `plan_t_simplanifstock` are ingested and validated
(key uniqueness, referential match rate against `plan_t_simplanif`) but are
**not** merged into the canonical dataset: no confirmed join key exists
between POI and Stock (see docs/decisions/0001, point 6). They remain
available in `data/interim/` for future investigation once a real join key
is confirmed.

## Synthetic demo dataset flow (pre-Phase-2, see docs/decisions/0003)

```text
data/raw/sql/plan_t_simplanifpoi.sql (READ-ONLY: POI_Sim scaffold + date-preservation check)
        │
        ▼
synthetic_demo_dataset.py  ──►  data/synthetic/demo_2025_2026/input/poi_demo_synthetic_completed.{parquet,csv}
        │
        ▼
canonical.py (same engine, DATA_ORIGIN=SYNTHETIC)  ──►  data/synthetic/demo_2025_2026/canonical/poi_demo_synthetic_canonical.{parquet,csv}
        │
        ▼
scripts/cli.py --dataset demo   &   src/simulation/webapp.py ?dataset=demo (red warning banner)
```

This tree is entirely separate from the real `data/canonical/` tree and is
never read by `scripts/run_pipeline.py` or written by anything that also
touches real data.

## Why business logic is isolated in `src/business/`

`src/business/rules.py` takes plain Python values in and returns a plain
dataclass out — no pandas, no file paths. This lets:

- unit tests run in milliseconds without touching any I/O;
- the exact same function be called once per row (baseline) or have its
  logic re-expressed as vectorized array operations (optimization) with a
  test asserting the two stay equivalent;
- a future Hadoop mapper/reducer reuse the identical rule instead of
  reimplementing it a third time.

## What Phase 1 deliberately does not do

- No Hadoop/MapReduce (Phase 2 per the user's instructions).
- No POI↔Stock join (no confirmed key — see docs/decisions/0001).
- No component-applicability inference beyond `ALL_REQUIRED` (no confirmed
  rule for "not required" — see docs/decisions/0001).
- No study-period filtering (no confirmed date range).

---

# Phase 2 Architecture (Hadoop MapReduce + scalable benchmarks)

See docs/decisions/0004 (environment inspection, benchmark dataset design)
and docs/decisions/0005 (the real 3-VM Hadoop cluster, YARN resource fix,
correctness results, benchmark results) for full detail. Summary here.

## Module map (additions)

```text
src/ingestion/
  synthetic_benchmark_generator.py   Chunked, memory-bounded generator for
                                      data/synthetic/benchmark_scale_2025_2026/
                                      (100k/500k/1M required, 5M opt-in only)

src/mapreduce/
  mapper.py            Hadoop Streaming mapper (stdlib only, no project
                        imports -- shipped to and run on cluster nodes)
  reducer.py            Hadoop Streaming reducer (stdlib only; a
                        deliberate, tested transcription of
                        src/business/rules.calculate_theoretical_week's
                        ALL_REQUIRED-policy logic -- see the module
                        docstring for why it doesn't import src.business
                        directly, and how the correctness-gate tests
                        cover the resulting duplication risk)
  cluster.py             SSH/SCP helpers for the real 3-VM cluster
                        (tws-master alias, project-scoped remote paths)
  environment.py         Local-Windows-host Hadoop/Java detection (used
                        only to decide/label the local-emulation fallback)

scripts/
  generate_benchmark_dataset.py   --scale 100000|500000|1000000
                                  (--scale 5000000 --confirm-large optional)
  prepare_hadoop_input.py         Wide POI table -> long-form component-event TSV
  run_hadoop_job.py               Real cluster (SSH) with automatic
                                  local-emulation fallback; phase-by-phase timing
  compare_hadoop_local.py         Runs a job then diffs it against the
                                  vectorized canonical reference; exit 1 on any mismatch

tests/
  unit/test_synthetic_benchmark_generator.py   Determinism, range, 5-events/POI,
                                                guaranteed ties/ISO-boundary cases
  unit/test_mapreduce_logic.py                  mapper.py/reducer.py as subprocesses
  validation/test_hadoop_local_equivalence.py   Full run_job() pipeline vs. local
                                                reference; real-data immutability check
```

## Data flow (Phase 2)

```text
synthetic_benchmark_generator.py (chunked, seeded)
        │
        ├──► data/synthetic/benchmark_scale_2025_2026/input/scale_<N>/part-*.parquet
        ├──► .../component_events/scale_<N>/part-*.parquet   (long-form, 5 rows/POI)
        └──► .../canonical_reference/scale_<N>/part-*.parquet (vectorized engine's answer)
                        │
        prepare_hadoop_input.py (only for the scale being run)
                        │
                        ▼
        .../hadoop_input/scale_<N>.tsv
                        │
        run_hadoop_job.py --mode auto
                        │
          ┌─────────────┴─────────────┐
          ▼ (cluster reachable)       ▼ (cluster unreachable)
   scp to master -> HDFS put   mapper.py | sort | reducer.py
   -> hadoop jar streaming        (LOCAL EMULATION, same
   -> HDFS getmerge -> scp back    mapper.py/reducer.py files,
   (REAL multi-node execution)     no HDFS/YARN/JVM overhead)
          │                             │
          └─────────────┬───────────────┘
                        ▼
        compare_hadoop_local.py: diff vs. canonical_reference
        (Id_Sim, POI_Sim, date_theorique, iso_year, iso_week,
         week_key, sem_theorique, blocking_element, calculation_status)
```

## The real cluster

3 VirtualBox VMs (Lubuntu), Hadoop 3.4.2 / OpenJDK 1.8.0_482, genuinely
multi-node: `master` runs NameNode+SecondaryNameNode+ResourceManager;
`worker1`/`worker2` each run DataNode+NodeManager. Each worker has 1 vCPU
and ~960MiB RAM. YARN's defaults (8192MB/8 vcores per node) were unsafe
for this hardware and were overridden to 384MB/1 vcore (see docs/decisions/0005
for the exact XML changes and backups). Connectivity is SSH-key-based
(`tws-master` alias in `~/.ssh/config`); `src/mapreduce/cluster.py` is the
only module that talks to it, and every remote path it touches is
project-scoped (`/tws_phase2/...` on HDFS, `~/tws_phase2/...` on master's
local filesystem).
