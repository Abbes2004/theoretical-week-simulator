# Phase 1 Summary — Normal (Local) Theoretical-Week Simulator

Follows the section skeleton of docs/execution/14_report_structure.md,
covering sections 1-7 and 9-10 (section 8, Hadoop/MapReduce, is explicitly
out of scope for Phase 1).

## 1-2. Context and problem

See docs/context/project_context.md and the cahier des charges
(docs/cahier_des_charges/RapportStageSimulateurDisponibilite.pdf). In
short: compute the theoretical production week of a jeans-manufacturing
Production Order Item as the latest availability date among five required
components (main fabric, secondary fabric, accessories, thread, production
approval), identify the blocking component, and handle missing/invalid
data explicitly rather than guessing.

## 3. Data understanding (OBSERVED, re-verified in this session)

| Source | Rows | Columns | Key facts |
|---|---:|---:|---|
| `plan_t_simplanif.sql` | 431 | 36 | `Id_Sim` PK, range 10775-12039 |
| `plan_t_simplanifpoi.sql` | 12,302 | 80 | PK `Id_SimPoi`, unique `(Id_Sim, POI_Sim)`; single `Id_Sim=5601`; `DateTissu`/`DateTissuSec`/`DateMax`/`SemTheorique` 100% NULL; `DateFourniture` 9/12,302, `DateFil` 29/12,302, `DateOKProduction` 50/12,302 populated |
| `plan_t_simplanifstock.sql` | 116,200 | 9 | PK `Id_stock`; 34 distinct `Id_Sim`; 91.1% join to `plan_t_simplanif.Id_Sim` |
| `table.xlsx` | 8 + 19 rows (2 sheets) | - | `plan_t_simplaniffourniture` confirms ISO-8601 week encoding |
| `consommation tissu par type.xlsx` | 48 | 4 | Clean fabric-per-garment-type reference table, no SQL join key |
| `cde.xls` | 12+2+4+10 rows (4 sheets) | - | Purchase-order-adjacent data; `YT#####` material codes shared with stock `Code_Sim` |
| 2 PO PDFs | - | - | Finished-goods sales orders; no identifier overlap with any SQL table |

Referential integrity, re-measured by running the actual Phase 1 pipeline
against the real data (`python scripts/run_pipeline.py`):

```text
plan_t_simplanifpoi.Id_Sim   -> plan_t_simplanif.Id_Sim   : 0 / 12,302 matched (0.0%)
plan_t_simplanifstock.Id_Sim -> plan_t_simplanif.Id_Sim   : 105,895 / 116,200 matched (91.1%)
```

These numbers exactly match docs/analysis/PHASE0 and TASK1, confirming the
parser and pipeline are reading the same data the same way.

## 4. Business logic implemented

See docs/business_rules/phase1_implementation.md for the full rule-by-rule
CONFIRMED/RECOMMENDATION table, and docs/decisions/0001 for the reasoning.
In one line: `date_theorique = MAX(5 required component dates)`,
`sem_theorique = ISO-8601 week of date_theorique`,
`blocking_element = every component tied at date_theorique`; any missing or
invalid required component yields an explicit `INCOMPLETE_DATA` /
`INVALID_DATA` status instead of a guessed date.

## 5. Architecture

See docs/architecture/overview.md. Business logic
(`src/business/rules.py`) is pure and I/O-free; ingestion, cleaning,
canonical-dataset construction, the CLI, and the Flask UI are thin layers
around it.

## 6. Local baseline

- `python scripts/run_pipeline.py` runs ingestion -> validation -> canonical
  build end-to-end against the real data.
- `python scripts/cli.py lookup --id-sim <id> --poi-sim <poi>` explains one
  POI's calculation.
- `python scripts/cli.py serve` launches the web UI (lookup + browse, with
  status filtering).
- 43 automated tests (`pytest tests/`): 19+ unit tests on the pure engine
  (including 4 Hypothesis property tests), integration tests (fixture-based
  raw->canonical, plus a real-data smoke test), validation tests
  (historical match-rate machinery on synthetic data), a dedicated
  SQL-dump-parser test, and a baseline-vs-vectorized equivalence test
  (3 synthetic seeds + the full real extract). All pass.

### Result on the real extract

```text
Total POIs: 12,302
  INCOMPLETE_DATA: 12,302 (100.0%)
Historical match rate: N/A (0 comparable POIs)
```

This is not a bug. Every one of the 12,302 real POIs is missing at least
one required component date (see the Data Understanding table above), so
under the `ALL_REQUIRED` policy every one is correctly reported as
incomplete rather than being assigned a guessed date. This exact outcome
was already flagged as the expected "Current Limitation" in
docs/execution/08_canonical_dataset_specification.md before this session
started, and is now confirmed by actually running the pipeline.

Engine correctness (as opposed to historical-match accuracy, which the
real data cannot exercise) is demonstrated with the reproducible
`DATA_ORIGIN = SYNTHETIC` generator: on a 2,000-row synthetic mix, the
pipeline correctly reproduces the expected status distribution (≈70%
CALCULATED, ≈25% INCOMPLETE_DATA, ≈5% INVALID_DATA, matching the
generator's configured mix) and, when a historical value is injected with a
known 10% mismatch rate, measures a 91.0% match rate — see
tests/validation/test_historical_validation.py.

## 7. Performance

See docs/decisions/0002-vectorized-optimization.md for the full
methodology, profiling evidence, and results table. Summary:

- Baseline throughput is flat at ~4,000-4,700 rows/s regardless of dataset
  size (1k to 500k synthetic rows, plus the real 12,302-row extract) —
  the cost is linear, not size-dependent.
- Profiling (cProfile, 10k rows) shows the bottleneck is per-row
  `DataFrame.iterrows()`/`Series` overhead and repeated `datetime.strptime`
  calls, not the `MAX()` calculation itself.
- A vectorized re-implementation of the identical logic
  (`src/optimization/vectorized_canonical.py`), proven equivalent to the
  baseline by test, is 3.5x-15.3x faster depending on dataset
  composition (higher speedup on the real extract, whose rows short-circuit
  early on missing components).

## 9. Results and discussion

- **Correctness**: the pure business-rule engine passes all unit,
  property-based, and integration tests, including every edge case named
  in docs/execution/13_testing_strategy.md and docs/context/Edge Cases &
  Data Quality Handling.md that is testable without an unconfirmed
  business rule.
- **Historical accuracy**: cannot be measured against real data in Phase 1
  — the real extract has no row with both a complete required-component
  set and a populated historical `SemTheorique`. This is a data
  limitation, not an engine limitation, and is the single most important
  open item for Phase 2 (see below).
- **Scaling**: linear in row count for both implementations; the
  vectorized version keeps this project comfortably within local/
  single-machine territory for the dataset sizes discussed in the cahier
  des charges (tens/hundreds of thousands of POs) — 500,000 synthetic rows
  process in ~15 seconds vectorized vs. ~120 seconds baseline.
- **Limitations**: see docs/decisions/0001, section "Consequence," and the
  CONFIRMED-vs-RECOMMENDATION table in docs/business_rules/phase1_implementation.md.
  The dominant limitation is data, not code: the supplied `plan_t_simplanifpoi`
  extract cannot validate the historical formula end-to-end.

## 10a. Addendum — synthetic demonstration dataset (added 2026-09-10, still pre-Phase-2)

Since section 6-9 above were written, a separate, reproducible `DATA_ORIGIN
= SYNTHETIC` demonstration dataset was added specifically because the real
extract cannot show a `CALCULATED` result at all (see section 6). It lives
entirely under `data/synthetic/demo_2025_2026/` and can never overwrite the
real canonical dataset. See `docs/decisions/0003-synthetic-demo-dataset.md`
and `data/synthetic/demo_2025_2026/metadata/README.md` for full detail;
summary:

- 513 rows total: 13 hand-specified edge cases (each of the 5 components as
  sole blocker; a 2-way, 3-way, and 5-way tie; the exact range boundaries
  2025-01-01/2026-06-30; the 2025-12-29/30/31 ISO year-boundary cluster,
  the only place in this range where the calendar year differs from the
  ISO week-year) + 500 seeded-random bulk rows.
- Seed 42, fully deterministic; dates drawn from `[2025-01-01, 2026-06-30]`.
- Result: 513/513 `CALCULATED`; blocking-element distribution `TISSU=108,
  TISSU_SEC=112, FOURNITURE=107, FIL=97, OK_PRODUCTION=101`.
- 17 new automated tests (determinism, in-range validity, full
  calculability, every edge case's expected result, real-data/real-output
  immutability, and a parquet-list-column rendering regression found and
  fixed in the web UI's browse view while testing this dataset).
- Accessible via `--dataset demo` (CLI) or `?dataset=demo` (web UI, which
  renders a persistent red warning banner); the real dataset remains the
  default everywhere.

## 10. Conclusion and next steps (Phase 2, not started)

Phase 1 delivers a correct, tested, benchmarked local simulator built
strictly from evidence, with every unconfirmed rule explicitly labelled
and swappable. The highest-value next steps, in order:

1. Obtain (or get engineer confirmation for) a POI extract with at least
   some rows carrying a populated, real historical `SemTheorique`, to
   allow genuine historical-match validation.
2. Resolve the `Ind*`/`Etat*`/`Statut*` semantics (Open Questions Q12-Q14)
   to potentially move some components from `ALL_REQUIRED` to a validated
   applicability rule.
3. Only then: Phase 2 Hadoop/MapReduce prototype, informed by the Phase 1
   bottleneck finding that per-record overhead (not the `MAX()` itself) is
   what would need to be addressed by any distributed design.
