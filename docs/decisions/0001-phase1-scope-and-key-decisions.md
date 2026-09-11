# Decision 0001 — Phase 1 scope and key implementation decisions

Status: Accepted (Phase 1). Date: 2026-09-10.

## Context

Phase 1 targets a correct, tested, documented **local** simulator (no
Hadoop/MapReduce). The prior analysis phase (docs/analysis/PHASE0, TASK1,
TASK2) established that:

- the real `plan_t_simplanifpoi` extract (12,302 rows, single
  `Id_Sim = 5601`) has `SemTheorique`, `DateMax`, `DateTissu`, and
  `DateTissuSec` 100% NULL, and at most 3 of the 5 component dates
  populated on any given row (only 4 rows have 3; 12,252 rows have 0);
- `plan_t_simplanifpoi.Id_Sim` does not match any row of
  `plan_t_simplanif` in the supplied extracts (0/12,302);
- no direct key between POI and Stock/material tables is demonstrated;
- the `Ind*` component-requirement indicators are 0 in every row of the
  real extract, so they cannot be used to infer "not required" today.

This means: with real data alone, the business-rule engine can be
exercised and validated for *code correctness*, but not for
*historical-match accuracy*, because there is no real row with a complete
enough input to produce a `CALCULATED` result and a populated historical
`SemTheorique` to compare it against.

## Decisions

1. **Applicability policy = `ALL_REQUIRED`** (configs/settings.py). Every
   one of the five components (Tissu, TissuSec, Fourniture, Fil,
   OkProduction) is treated as required for every POI unless a caller
   explicitly overrides a component to `NOT_REQUIRED`.
   RECOMMENDATION, not a confirmed company rule — see
   docs/context/Open Questions & Business Validation.md Q6/Q7. Chosen
   because it is the conservative option: it never silently drops a
   required component, and it is implemented as a single, swappable
   function (`src/business/rules.determine_applicability`) so a future
   confirmed rule can replace it without touching the rest of the engine.

2. **A missing OR invalid required component blocks the whole
   calculation** (status `INCOMPLETE_DATA` / `INVALID_DATA`, no
   `DateTheorique`/`SemTheorique` produced), rather than computing `MAX()`
   over only the known dates. Justification: docs/context/Business
   Rules.md section 5 states production cannot start before all required
   elements are available, so a partial `MAX()` would silently understate
   the true theoretical date — exactly the "never invent a date" rule in
   MASTER_PROMPT.md section 9.

3. **Week convention = ISO-8601** (`configs.settings.WEEK_CONVENTION`).
   CONFIRMED for `plan_t_simplaniffourniture.EtatAccessoire` (13/13 exact
   matches against `DateAccesoire`, recomputed in this session — see
   docs/analysis/TASK2). Extending it to `SemTheorique` itself is a
   RECOMMENDATION built on adjacent evidence, since `SemTheorique` is never
   populated in any available extract and so cannot be checked directly.
   The canonical schema stores `iso_year` + `iso_week` + `week_key`
   (`YYYYWW`) rather than only a bare week number, per MASTER_PROMPT.md
   section 8.

4. **Ties are preserved, never broken.** `blocking_element` is a list of
   every required component whose date equals `date_theorique`. No
   priority order is invented (docs/context/Business Rules.md section 4).

5. **Study-period filtering is left disabled**
   (`configs.settings.STUDY_PERIOD_START/END = None`). No document
   supplies a confirmed date range (docs/context/Open Questions &
   Business Validation.md Q23), so Phase 1 processes every POI in the
   input rather than inventing a cutoff.

6. **POI ↔ Stock is not joined.** No demonstrated key exists (0/185 direct
   matches under the one shared `Id_Sim`, per docs/analysis/TASK1). The
   canonical dataset is built from `plan_t_simplanifpoi` alone; stock data
   is ingested and validated (for referential-integrity reporting) but not
   merged into the calculation.

7. **Historical validation reports `match_rate = None`, not `0.0`,** when
   there are zero comparable POIs — this is the honest representation of
   "unknown," matching the real extract's actual state, and is unit-tested
   (tests/validation/test_historical_validation.py).

## Consequence

Running the Phase 1 pipeline against the real extract produces
`calculation_status = INCOMPLETE_DATA` for all 12,302 POIs and
`match_rate = None`. This is not a bug: it is the documented, expected
outcome of the "Current Limitation" already called out in
docs/execution/08_canonical_dataset_specification.md, now confirmed by
running the actual pipeline. Correctness of the engine itself is
demonstrated with synthetic data (clearly labelled `DATA_ORIGIN =
SYNTHETIC`) and with unit/property tests — see
docs/report/phase1_summary.md.
