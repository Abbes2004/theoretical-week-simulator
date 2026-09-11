# `data/raw/` — Excluded From This Repository

This directory is where the **original, internship-provided source files**
live when the project is run locally. It is intentionally excluded from
the public GitHub repository via `.gitignore` (only this `README.md` is
tracked).

## Why these files are not published

The contents of `data/raw/` are the company/project's own source data
(database exports and supporting documents supplied for this internship).
They are not the author's to publish, and this repository must never be
the place they become public. Nothing in `data/raw/` is committed, and no
excerpt, sample row, or derived value that could reconstruct it is stored
here either — only the file *structure* is documented below, so the
pipeline's expectations are clear.

## Expected structure

To run this project locally, recreate this layout and place the original
files accordingly (get them through the same channel you originally
received this project's data from — they are not distributed with this
repository):

```text
data/raw/
├── README.md          (this file — tracked)
├── sql/
│   ├── plan_t_simplanif.sql
│   ├── plan_t_simplanifpoi.sql
│   └── plan_t_simplanifstock.sql
├── excel/
│   ├── cde.xls
│   ├── consommation tissu par type.xlsx
│   └── table.xlsx
└── pdf/
    ├── PO 3034174 72000022 Ladies.pdf
    └── PO 3034281 72000022 Ladies.pdf
```

## Guarantees the codebase makes about this directory

- Every ingestion module (`src/ingestion/`) opens files under `data/raw/`
  **read-only**. Nothing in this project writes, renames, or deletes
  anything here.
- All derived data lives under `data/interim/`, `data/processed/`, and
  `data/canonical/` instead — those are the reproducible outputs of
  running the pipeline against `data/raw/`, and are themselves excluded
  from Git (also generated, also never committed) except for their own
  `.gitkeep` placeholders.
- See `docs/decisions/` and `docs/report/` for how these raw sources were
  profiled, validated, and used — with every finding classified as
  CONFIRMED, OBSERVED, INFERRED, HYPOTHESIS, or UNKNOWN, exactly so the
  documentation stays useful without needing the raw files themselves to
  be public.

## If you are the internship supervisor / grader

The full raw data was available to the working environment during
development. If you need to re-run the pipeline against it, place the
files in the structure above locally — no code change is required.
