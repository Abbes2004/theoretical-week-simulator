# Decision 0003 — Synthetic demonstration dataset (pre-Phase-2)

Status: Accepted. Date: 2026-09-10.

## Context

Phase 1 (Decision 0001) established that the real `plan_t_simplanifpoi`
extract cannot produce a single `CALCULATED` result: every row is missing
at least one required component date. This is the correct, honest outcome
for that data, but it means the simulator and web UI have never actually
shown a computed `SemTheorique`, a blocking element, or a tie. Before
starting the Phase 2 Hadoop/MapReduce work, a reproducible demonstration
dataset is needed so these behaviours are visible and testable, without
ever pretending it is real company data.

## Decisions

1. **Separate tree, not a real-data variant.** The dataset lives entirely
   under `data/synthetic/demo_2025_2026/` (`input/`, `canonical/`,
   `metadata/`), never under `data/interim/`, `data/processed/`, or
   `data/canonical/`. Generating it can only ever write inside that one
   directory (enforced in code review and by
   `tests/validation/test_synthetic_demo_dataset.py`, which hashes the real
   raw files and the real canonical output before/after generation and
   asserts no change).

2. **Sentinel `Id_Sim = 999999`.** Chosen because it falls outside every
   `Id_Sim` range observed in the real data in this session:
   `plan_t_simplanif` 10775-12039, `plan_t_simplanifpoi` 5601 only,
   `plan_t_simplanifstock` 3322-10876. This makes an accidental join or
   concatenation between a demo row and a real row structurally impossible
   on the `(Id_Sim, POI_Sim)` grain key, even though...

3. **...`POI_Sim` identifier *strings* for the 500 bulk rows are reused
   from the real extract** (a random, seeded sample), per the instruction
   to treat the real extract as an identifier/schema scaffold. This is
   safe specifically because of decision 2: the (Id_Sim, POI_Sim) pair is
   never identical to a real row's pair, only the POI_Sim text looks
   realistic. The 13 curated edge-case rows use descriptive synthetic
   identifiers (`DEMO-EDGE-<case>`) instead, since they don't need to look
   like real codes.

4. **Every date is generated fresh unless a real date already qualifies.**
   For each of the 500 bulk rows, the corresponding real row's 5 component
   dates are checked: if a real date parses and falls within
   `[2025-01-01, 2026-06-30]`, it is preserved; otherwise a synthetic
   replacement is drawn from a seeded RNG. In practice, **0 real dates
   qualify** (the real extract's few populated dates are all from
   2021-08 to 2021-10), so every date in the demo dataset is a synthetic
   replacement. This is measured and recorded per component in
   `metadata/generation_metadata.json`, not assumed.

5. **No historical field is fabricated.** `SemTheorique`/`DateMax` are left
   NULL in the demo input table. Inventing a plausible-looking historical
   value would fabricate exactly the kind of manual-override relationship
   the project rules forbid, and there is nothing to validate it against.

6. **Edge cases are hand-specified, not left to chance.** A generator that
   only draws i.i.d. random dates would likely produce ties and every
   blocking component eventually, but "likely" is not "guaranteed" and
   would not reliably hit the exact required cases (a 2-way tie, a 3-way
   tie, the literal date `2025-12-29`, the exact range boundaries). 13
   curated rows guarantee these deterministically; 500 additional bulk
   rows (independently random per component, seeded) provide realistic
   volume and natural distribution across all five blocking components
   (observed: 97-112 occurrences each across a run).

7. **Verified, not assumed, ISO year-boundary claim.** Within
   `[2025-01-01, 2026-06-30]`, `date.isocalendar()` was used directly (see
   `src/ingestion/synthetic_demo_dataset.py::build_edge_cases`) to confirm
   that 2025-12-29/30/31 are the *only* dates in range where the calendar
   year differs from the ISO week-year (all three land in ISO week 01 of
   ISO year 2026); neither 2025-01-01 nor 2026-01-01 exhibits this (both
   land in ISO week 1 of their own calendar year). The edge-case set
   reflects exactly what was verified, not a general claim about ISO weeks
   at large.

8. **Dataset selection is explicit, never silent.** The CLI (`--dataset
   real|demo`, default `real`) and the web UI (`?dataset=real|demo`,
   default `real` unless started with `--dataset demo`) both require an
   explicit choice to view synthetic data, and the web UI renders a
   persistent red banner whenever the demo dataset is active. The dataset
   choice is threaded through every link on the page so browsing cannot
   silently drift from one dataset to the other.

## Consequence

Running `python scripts/generate_demo_dataset.py` and then
`python scripts/cli.py stats --dataset demo` shows 513/513 `CALCULATED`
POIs, a blocking-element distribution spread across all five components,
and all 13 documented edge cases resolving to their expected result. This
does not change, weaken, or contradict Decision 0001: the real dataset's
100% `INCOMPLETE_DATA` result is still the correct, default, and only
result shown unless `--dataset demo` / `?dataset=demo` is explicitly
requested.
