# Phase 1 — Implemented Business Rules vs. Confirmed Company Rules

This document is the single place that states, for every rule actually
implemented in `src/business/rules.py`, whether it is CONFIRMED by project
documentation/data or a RECOMMENDATION adopted in the absence of a
confirmed rule. See docs/context/Business Rules.md and docs/context/Open
Questions & Business Validation.md for the full evidence discussion this
is derived from.

| # | Rule as implemented | Status | Evidence |
|---|---|---|---|
| 1 | `DateTheorique = MAX(applicable component dates)` | CONFIRMED | Cahier des charges section 1/3.3; docs/context/Business Rules.md section 3 |
| 2 | Five components: Tissu, TissuSec, Fourniture, Fil, OK Production | CONFIRMED | Cahier des charges; project_context.md section 2 |
| 3 | `BlockingElement` = component(s) whose date == `DateTheorique` | CONFIRMED (concept) | Business Rules.md section 4 |
| 4 | Ties: all tied components returned, no priority order invented | CONFIRMED (as an explicit non-rule) | Business Rules.md section 4: "must therefore not invent a priority between tied elements" |
| 5 | Every component is `REQUIRED` for every POI (`ALL_REQUIRED` policy) | RECOMMENDATION | No confirmed applicability rule exists (Open Questions Q6/Q7); `Ind*` fields are 0 in 100% of the real extract, so they cannot be used yet |
| 6 | A missing/invalid required component blocks the whole result (no partial `MAX()`) | RECOMMENDATION, derived from a confirmed premise | Business Rules.md section 5 ("cannot theoretically start before all required elements are available") implies a partial MAX would be misleading |
| 7 | Week convention = ISO-8601 (`iso_year`, `iso_week`, `week_key = YYYYWW`) | RECOMMENDATION (CONFIRMED for an adjacent field only) | CONFIRMED for `plan_t_simplaniffourniture.EtatAccessoire` (13/13 exact matches); NOT directly confirmed for `SemTheorique` (always NULL) |
| 8 | Invalid date format -> `INVALID_DATA` status, excluded from MAX | RECOMMENDATION | Edge Cases & Data Quality Handling.md item 4 |
| 9 | Suspicious (out-of-range) date -> flagged, still used in MAX | RECOMMENDATION | Edge Cases & Data Quality Handling.md item 5: "not auto-delete" |
| 10 | No applicable component -> `NOT_APPLICABLE`, no MAX(empty) | RECOMMENDATION | Edge Cases & Data Quality Handling.md item 10 |
| 11 | POI↔Stock not joined; Stock not used in the calculation | CONFIRMED absence of evidence | TASK1: 0/185 direct matches under the one shared `Id_Sim` |
| 12 | `Ind*`, `Etat*`, `Statut*`, `*_old`/`*_Manuel` fields not used in the calculation | CONFIRMED absence of evidence | Open Questions Q12-Q14, Q20-Q21: meaning unconfirmed |
| 13 | Study-period scope: no filter applied (process every POI) | UNKNOWN, left unresolved | No document supplies `START_DATE`/`END_DATE` (Open Questions Q23) |

## Explicit non-rules (deliberately NOT implemented)

- **Quantity-based availability** (`Qte >= BesoinTissu` or any stock
  accumulation rule): explicitly flagged as a hypothesis that must not be
  used until validated (Business Rules.md section 13; Open Questions
  Q15-Q17). Not implemented.
- **Manual/historical override precedence** (`*_Manuel`, `DateMaxMan`,
  etc. taking priority over calculated dates): unconfirmed whether these
  are even active in the source system (Open Questions Q20-Q21). Not
  implemented; these columns are ingested (visible in
  `data/interim/plan_t_simplanifpoi.raw.parquet`) but not read by
  `src/business/rules.py`.
- **Tie-break priority order** among blocking components: explicitly
  rejected by Business Rules.md section 4. Not implemented; all ties are
  returned.

## How to change a RECOMMENDATION once a rule is confirmed

Every RECOMMENDATION above corresponds to exactly one function or constant:

- Applicability policy -> `src/business/rules.determine_applicability()`
  and `configs.settings.DEFAULT_APPLICABILITY_POLICY`.
- Week convention -> `src/business/iso_week.py`.
- Invalid/suspicious date handling -> `src/business/date_parsing.py`.
- Study-period filter -> `configs.settings.STUDY_PERIOD_START/END` (not
  yet wired into the pipeline; add a filter step in
  `src/preprocessing/cleaning.py` once a confirmed range exists).

Changing any of these is a one-file change followed by re-running
`pytest tests/unit/test_business_rules.py` — the property-based tests will
catch most logical regressions automatically.
