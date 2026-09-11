# Final Delivery Audit

## 1. Audit Date

2026-09-10 (end of the combined Phase 1 + Phase 2 working session).

## 2. Overall Status

**READY_WITH_MINOR_NOTES**

The project is functionally complete, all automated tests pass, raw data
integrity is verified, and real/synthetic data are clearly separated and
labelled. The only reason this is not an unqualified READY_FOR_DELIVERY is
that no Git repository has ever been initialized in this workspace (see
section 12) and the real canonical output was regenerated mid-session by
an ordinary, intended pipeline re-run (see section 8) — both are disclosed
in detail below, neither reflects a defect in the deliverable itself.

## 3. Workspace Inventory

Top-level layout (sizes after this audit's cleanup; `.venv` and `.claude`
are hidden dirs not shown by a plain `du -sh */`):

```text
MASTER_PROMPT.md          Original project brief (pre-existing, untouched)
README.md                 Setup/run/test/benchmark commands, Phase 1 + Phase 2
requirements.txt          Pinned-minimum Python dependencies
.gitignore                Covers caches, venv, derived data, large generated artifacts

configs/        21K   settings.py -- paths + business-rule constants, all documented
data/          423M   raw/ (18M, immutable) + interim/ + processed/ + canonical/
                       + synthetic/demo_2025_2026/ (208K, tracked) and
                       synthetic/benchmark_scale_2025_2026/ (395M, gitignored,
                       reproducible via seed=42)
docs/          504K   context/ analysis/ execution/ (pre-existing evidence,
                       read-only source of truth) + architecture/ business_rules/
                       decisions/ report/ (written this session)
scripts/       105K   9 entry-point scripts (pipeline, CLI, benchmark/Hadoop tooling)
src/           363K   28 modules: business/ ingestion/ mapreduce/ optimization/
                       preprocessing/ simulation/
tests/         320K   16 test files, 87 collected tests
benchmarks/     11M   baseline/ (scripts) + datasets/ (gitignored, reproducible)
                       + optimized/ (empty, scaffold from MASTER_PROMPT structure,
                       never needed -- optimization work lives in
                       src/optimization/ + benchmarks/baseline/ instead)
outputs/       103M   benchmarks/ logs/ mapreduce/ results/ -- all gitignored,
                       fully regenerable
notebooks/       0    exploration/ performance/ validation/ -- empty, scaffold
                       from MASTER_PROMPT structure, never used (no exploratory
                       notebook work was needed for this project)
rapport/         0    Empty. Not created by any script/session in this project
                       (French for "report" -- almost certainly the user's own
                       staging space for the internship report itself). Left
                       untouched.
.venv/         264M   A real virtual environment matching README's own setup
                       instructions. Gitignored. Not created by this audit.
.claude/        1K    launch.json for this AI coding tool's browser-preview
                       feature (used to test the web UI during development).
                       Now gitignored (see section 6).
```

Total workspace: ~800MB, but only ~20MB of that is meant to be delivered/
tracked (`src/`, `scripts/`, `tests/`, `docs/`, `configs/`, `data/raw/`,
`data/synthetic/demo_2025_2026/`, top-level files); the rest is `.venv`,
generated benchmark data, and job scratch output, all reproducible and
gitignored.

## 4. Files/Folders Removed

| Path | Reason | Why safe |
|---|---|---|
| `outputs/mapreduce/benchmark/scale_1000000.{mapped,sorted}.tsv` (590MB) | Pure intermediate scratch from a local-emulation MapReduce run (raw mapper output and its sorted form) | Fully reproducible via `python scripts/run_hadoop_job.py --mode local-emulation`; the final `.reduced.tsv`, `.job_result.json`, and `.correctness_report.json` (the actual evidence) were kept |
| `outputs/mapreduce/benchmark/scale_100000.{mapped,sorted}.tsv` (59MB) | Same as above, 100k scale | Same as above |
| `outputs/mapreduce/demo.{mapped,sorted}.tsv` (264KB) | Same as above, demo scale | Same as above |
| All `__pycache__/` directories outside `.venv` (14 dirs) | Compiled bytecode cache | Regenerated automatically on next Python run; already gitignored |
| `.pytest_cache/`, `.hypothesis/` | Test-runner cache/state | Regenerated automatically on next `pytest` run; already gitignored |

No source code, test, documentation, configuration, raw data, or
meaningful result file was removed. Total reclaimed: ~650MB of disposable
scratch.

## 5. Files/Folders Added

| Path | Reason | Purpose |
|---|---|---|
| `docs/execution/17_final_delivery_audit.md` | This audit, as requested | Delivery-readiness record |
| `data/synthetic/benchmark_scale_2025_2026/.gitkeep` | New `.gitignore` rule needs a placeholder | Keeps the directory present in a fresh checkout even though its generated contents are ignored |
| `outputs/mapreduce/.gitkeep` | Same reason | Same reason |

## 6. Files Modified

| Path | Reason | Type of modification |
|---|---|---|
| `.gitignore` | Two Phase 2 generated-artifact trees (`data/synthetic/benchmark_scale_2025_2026/`, 395MB; `outputs/mapreduce/`, was 722MB) were not covered by the existing ignore rules, unlike every other generated-output directory | Added two new ignore blocks (with `.gitkeep` exceptions, matching the existing pattern used for `data/interim/`, `outputs/logs/`, etc.); added `.claude/` next to the existing `.vscode/`/`.idea/` IDE-tooling exclusions |
| `docs/report/phase2_summary.md` | One inline code span wrapped across a markdown line break, rendering as `` `data/canonical/ `` / `` poi_canonical.parquet` `` on two lines | Cosmetic reflow of one line; no content or meaning changed |

No source code (`src/`, `scripts/`, `configs/`) was modified during this
audit — inspection found no defects there warranting a change (see
section 9). `data/canonical/poi_canonical.parquet` and `outputs/results/*`
were regenerated as a side effect of the Step 13 final-execution check
(re-running `python scripts/run_pipeline.py`, exactly as instructed) — see
section 8 for the full disclosure.

## 7. Files Intentionally Kept

- **`docs/analysis/PHASE0_Initial_Project_Assessment.md` and
  `docs/analysis/TASK1_Raw_SQL_Deep_Analysis.md`** reference a planned
  module/file structure (e.g. `src/business/semtheorique.py`,
  `src/preprocessing/normalize.py`, `docs/decisions/DEC-001_*.md`) that
  differs from what was actually built (`src/business/rules.py`,
  `docs/decisions/0001-*.md`, etc.). These are **pre-existing evidence
  documents** from an earlier planning/profiling pass, explicitly treated
  throughout this project as read-only source-of-truth material (per
  MASTER_PROMPT.md and the Phase 1 reading-order instructions), not living
  specifications. The divergence is expected — plans and final
  implementations naturally differ — and rewriting historical evidence
  documents to match the final code would destroy their value as a record
  of what was known/planned at the time. Left unmodified.
- **`notebooks/{exploration,performance,validation}/`,
  `benchmarks/optimized/`** are empty. They are part of the directory
  structure MASTER_PROMPT.md itself specifies. No exploratory-notebook or
  separate "optimized implementation" work was ever needed (the vectorized
  optimization lives in `src/optimization/` and is benchmarked directly
  from `benchmarks/baseline/`, which was simpler and avoided duplicating
  the pipeline). Kept as harmless, documented scaffold rather than removed,
  since Git does not track empty directories anyway and removing them
  would silently deviate from the specified structure without any benefit.
- **`rapport/`** (empty) — not created by any script or session activity in
  this project; almost certainly the user's own staging area, most likely
  for the internship report itself (this audit's own instructions mention
  "before the internship report is written"). Left completely untouched.
- **`.venv/`** (264MB) — a real, working virtual environment matching the
  README's own setup instructions; already gitignored. Not removed, since
  doing so would not improve the deliverable (it is never committed) and
  might disrupt an environment currently in use.
- **`outputs/mapreduce/*.hadoop_output.tsv`, `*.reduced.tsv`,
  `*.job_result.json`, `*.correctness_report.json`** — kept (unlike the
  `.mapped.tsv`/`.sorted.tsv` intermediates) because these ARE the actual
  evidence of the Phase 2 correctness/performance results referenced in
  `docs/report/phase2_summary.md` and `docs/decisions/0005`.

## 8. Data Integrity

- **Raw data** (`data/raw/`): all 8 files verified byte-identical via
  MD5 against the checksums recorded at the very start of Phase 1, and
  file modification timestamps are unchanged (`2026-08-19 12:45/12:46`,
  the original extraction time) — confirmed again at the end of this audit,
  after every pipeline/test/cleanup action performed in this session.
  **Never modified.**
- **Real vs. synthetic separation**: every derived/generated row carries
  an explicit `data_origin` column (`REAL`/`SYNTHETIC`), enforced by
  dedicated tests (`test_data_origin_is_never_mislabeled_as_real`,
  `test_data_origin_is_synthetic_everywhere`,
  `test_data_origin_is_synthetic_in_component_events`). Synthetic datasets
  live in a separate `data/synthetic/` tree with `SYNTHETIC` in their own
  directory names (`demo_2025_2026`, `benchmark_scale_2025_2026`) and
  every metadata file/README under them states `"data_origin": "SYNTHETIC"`
  explicitly. No filename, comment, or documentation line found during
  this audit implies synthetic/generated/benchmark data is real company
  data.
- **Generated/derived data**: `data/interim/`, `data/processed/`,
  `data/canonical/`, `outputs/results/`, `outputs/benchmarks/`,
  `outputs/mapreduce/`, `data/synthetic/benchmark_scale_2025_2026/`, and
  `benchmarks/datasets/` are all reproducible from `data/raw/` (or a fixed
  seed) via documented commands, and are gitignored accordingly (see
  section 6).
- **Disclosed exception**: as part of this audit's Step 13 (final
  execution check), `python scripts/run_pipeline.py` was re-run as
  instructed. This regenerated `data/canonical/poi_canonical.parquet`,
  `poi_canonical.csv`, `data/interim/*`, and `outputs/results/*` — their
  file hashes now differ from an earlier session snapshot (a similar,
  independently-observed hash change during Phase 2 was already disclosed
  in `docs/report/phase2_summary.md` section 6). The regenerated content
  was inspected and is logically identical to every prior run: 12,302
  rows, 100% `INCOMPLETE_DATA`, `DATA_ORIGIN=REAL`, same `(id_sim,
  poi_sim)` identifiers, same referential-match percentages (0.0% POI→Sim,
  91.1% Stock→Sim). This is the file's intended, designed behavior
  (Phase 1's own reproducible-derived-output pipeline), not data loss,
  corruption, or fabrication — but it is recorded here for full
  transparency rather than left unmentioned.

## 9. Code Quality

- No `TODO`/`FIXME`/`XXX` markers found anywhere in `src/`, `scripts/`, or
  `configs/`.
- No hard-coded Windows machine-specific paths (`D:\`, `C:\Users\...`)
  found in any source file — every path is built from
  `Path(__file__).resolve()...` relative to the project root, confirmed by
  a full-tree grep.
- `configs/settings.py` does contain `/home/abbes/...`-style paths, but
  these are the real Hadoop cluster's own remote filesystem locations
  (`HADOOP_CLUSTER_REMOTE_HOME`, `HADOOP_CLUSTER_HADOOP_HOME`,
  `HADOOP_CLUSTER_REMOTE_STAGING`), inherently environment-specific by
  nature (they describe a fixed external cluster, not this workspace), and
  already documented inline with comments explaining what they are and why
  they're fixed. Not a portability defect in the local project; a
  legitimate, disclosed dependency on the one specific cluster this
  session was authorized to use.
- No secrets, credentials, API keys, tokens, or private key material found
  anywhere in the tracked workspace (explicit pattern grep across `.py`,
  `.md`, `.json`, `.txt`, `.xml`, `.cfg`, `.ini` files; the SSH keypair
  generated for cluster access lives in the Windows user's own `~/.ssh/`,
  outside this project directory, and was never copied into it).
- `requirements.txt` cross-checked against every third-party import found
  in `src/`, `scripts/`, `configs/`, `benchmarks/`, and `tests/`: no
  missing and no unused declared dependency. (`openpyxl`/`xlrd` are used
  indirectly via `pandas.read_excel`'s engine selection, `pyarrow` via
  `pandas.to_parquet`/`read_parquet` — expected, not dead declarations.)
- `src/mapreduce/reducer.py` deliberately duplicates a small piece of
  business logic from `src/business/rules.py` (documented at length in its
  own module docstring and in `docs/decisions/0005`) because it must run,
  dependency-free, on the real cluster's nodes. This is a known,
  intentional, tested exception to "one source of truth for business
  logic," not an oversight — flagged here again for visibility.
- No dead code, duplicate scripts, or duplicate datasets were found beyond
  the disposable job-scratch files already removed (section 4).

## 10. Testing Results

Executed (not merely inspected) via `python -m pytest tests/ -v`:

```text
86 passed, 1 skipped in 44.32s
```

- **0 failed.**
- **1 skipped by design**: `test_real_cluster_correctness_slow` — opt-in
  only (`TWS_TEST_REAL_CLUSTER=1`), since it submits a real job to the
  physical 3-VM cluster and takes several minutes; real-cluster
  correctness is already proven and documented separately (513/513 and
  100,000/100,000 POIs, both exact matches — see
  `docs/decisions/0005-real-hadoop-cluster-execution.md`).
- No warnings were emitted by pytest in this run.
- Coverage: pure business-rule engine (incl. 4 Hypothesis property tests),
  date parsing, ISO week conversion, the SQL-dump parser, the canonical
  pipeline (fixture-based + a real-data smoke test), the vectorized
  optimization's equivalence to baseline (on synthetic data and the full
  real 12,302-row extract), the demo dataset (determinism, range,
  calculability, every edge case, real-data immutability), the Phase 2
  benchmark generator (determinism, range, 5-events-per-POI, guaranteed
  ties/ISO-boundary cases), the Hadoop mapper/reducer (as subprocesses),
  the cluster SSH/SCP retry helpers, and the end-to-end Hadoop-vs-local
  correctness gate.
- Separately, the main pipeline (`scripts/run_pipeline.py`), the CLI
  (`stats`/`lookup`, both `--dataset real` and `--dataset demo`) were
  executed live during this audit and produced the expected output (see
  section 8 and section 13's checklist).

## 11. Reproducibility

A third person with this repository and the raw data present could:

1. `pip install -r requirements.txt` (pinned minimum versions, all
   standard PyPI packages, no private/internal dependencies).
2. `python scripts/run_pipeline.py` — ingest, validate, build the
   canonical dataset from `data/raw/`. Verified working in this audit.
3. `python -m pytest tests/ -q` — 86 passed, 1 intentionally skipped.
   Verified in this audit.
4. `python scripts/cli.py stats` / `lookup` / `serve` — verified working
   for both `--dataset real` and `--dataset demo` in this audit.
5. `python scripts/generate_demo_dataset.py` and
   `python scripts/generate_benchmark_dataset.py --scale N` — deterministic
   (seed=42), reproduce the exact datasets shipped/described in
   `docs/decisions/0003` and `docs/decisions/0004`.
6. Hadoop/MapReduce commands (`prepare_hadoop_input.py`, `run_hadoop_job.py`,
   `compare_hadoop_local.py`) work in `local-emulation` mode with zero
   external dependencies beyond this repo + Python + a `sort` binary
   (documented). Real-cluster execution additionally requires the specific
   3-VM cluster described in `docs/decisions/0005` — this is an external
   prerequisite, explicitly documented as such (SSH host aliases, cluster
   topology, resource limits), not something a third party can reproduce
   without equivalent infrastructure. This is disclosed, not hidden.

No step in the README references a file, script, or command that does not
exist (spot-checked every command block in `README.md` against the actual
`scripts/`/`benchmarks/` tree during this audit).

## 12. Git / Repository Status

**No Git repository exists in this workspace** (`git status` reports "not
a git repository" at the project root and at every parent directory). This
has been true for the entire duration of this project — Phase 1, the demo
dataset, and Phase 2 were all built and verified without version control
ever being initialized. This audit did **not** run `git init`, since doing
so is a structural decision outside this audit's explicit
"cleanup/verify," not "restructure" mandate, and was not requested.

Given there is no repository, the usual tracked/untracked/ignored
inspection does not apply; instead, `.gitignore` was audited *as a
specification of what a future `git add .` should exclude* (see section
6 for the two gaps found and fixed) and a secrets scan was run directly
against the filesystem (section 9) rather than via `git diff`/`git log`.
No commit was made, and nothing was pushed anywhere, consistent with the
"do not commit or push unless explicitly instructed" constraint.

## 13. Remaining Issues

### Blocking

None.

### Non-blocking

- No Git repository has been initialized. If delivery is expected as a
  Git repository (rather than a plain file tree/zip), this needs an
  explicit `git init` + initial commit, which was intentionally not done
  here without being asked.
- `data/canonical/poi_canonical.parquet` was regenerated during this
  audit's mandated final-execution check (section 8); its file hash no
  longer matches an earlier point-in-time snapshot recorded in
  `docs/report/phase2_summary.md`, even though the content is logically
  identical. Anyone diffing against that earlier snapshot by hash alone
  (rather than by content) will see a change.

### Recommendations

- Consider whether `rapport/` should be populated, removed, or documented
  before final handoff — it is currently an empty, unexplained directory
  from this project's perspective (though very likely the user's own
  in-progress report space).
- If the project will be delivered via Git, initialize the repository
  fresh from the current state (after this audit) so the tracked history
  starts clean, rather than trying to reconstruct history for work already
  done.
- The two pre-existing `docs/analysis/` files with forward-looking,
  now-superseded file-path references (section 7) could optionally get a
  one-line "superseded by the as-built structure in docs/architecture/
  overview.md" note if a reader unfamiliar with the project's history
  might otherwise be confused — not done here, to avoid altering
  pre-existing evidence documents without being asked.

## 14. Final Delivery Checklist

- [x] Functionally complete
- [x] Tests passing (86 passed, 1 intentionally skipped, 0 failed)
- [x] Business rule verified (MAX of 5 components, ISO week, tie-preserving
      blocking element, missing/invalid-data handling — implementation,
      tests, and documentation all consistent; re-verified in this audit)
- [x] Data pipeline coherent (raw → interim → canonical, re-run and
      verified in this audit)
- [x] Real/synthetic data clearly separated (`data_origin` field + tree
      separation + tests enforcing it)
- [x] Raw data protected (byte-identical, timestamps unchanged, re-verified)
- [x] Documentation coherent (only forward-looking references in
      pre-existing, intentionally-unmodified planning documents — see
      section 7)
- [x] README usable (every command verified to exist and run in this audit)
- [x] Dependencies reproducible (`requirements.txt` cross-checked against
      actual imports)
- [x] No accidental secrets (explicit scan, none found)
- [x] No unnecessary temporary files (650MB of scratch removed in this audit)
- [x] No obvious dead/duplicate files
- [x] No broken references (aside from pre-existing evidence docs, see
      section 7, left unmodified by design)
- [x] Paths reasonably portable (no hard-coded local machine paths in code;
      the one environment-specific path family is the documented external
      cluster)
- [x] Benchmarks/results organized (`docs/report/`, `docs/decisions/`,
      `outputs/benchmarks/`, `outputs/mapreduce/`, all with clear labels)
- [x] Hadoop component documented (`docs/decisions/0004`, `0005`,
      `docs/report/phase2_summary.md`)
- [ ] Git repository clean/reasonable — **no repository exists** (see
      section 12; not fixed without explicit instruction)
- [x] Project reproducible (section 11)
- [x] Project ready to deliver (as a file tree; Git packaging is the one
      open item)

## 15. Final Verdict

**READY_WITH_MINOR_NOTES**

The simulator, its tests, its documentation, and both the local and real-
Hadoop-cluster execution paths are complete, correct (86/86 non-skipped
tests passing, business rule re-verified against its own documentation),
and honestly documented, including every limitation and every disclosed
data-regeneration event. The only two open items are non-blocking and
explicitly outside what this audit was authorized to decide unilaterally:
whether to initialize Git for delivery, and what to do with the user's own
(apparently in-progress) `rapport/` directory. Both are called out above
rather than resolved by assumption.
