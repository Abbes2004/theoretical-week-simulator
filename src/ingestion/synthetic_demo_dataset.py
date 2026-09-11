"""Reproducible SYNTHETIC demonstration dataset (pre-Phase-2).

Purpose: Phase 1 showed that the real `plan_t_simplanifpoi` extract cannot
produce a single `CALCULATED` result (every row is missing at least one
required component date -- see docs/decisions/0001). Before starting the
Hadoop/MapReduce work in Phase 2, this module builds a small, clearly
labelled `DATA_ORIGIN = SYNTHETIC` dataset in which every record IS
calculable, so the simulator and web UI can actually demonstrate
`SemTheorique`, blocking elements, and ties.

Non-negotiable rules enforced here (see the calling instructions and
docs/decisions/0003-synthetic-demo-dataset.md):

- `data/raw/` is only ever opened for reading.
- Nothing here writes into `data/interim/`, `data/processed/`, or
  `data/canonical/` (the REAL derived-data tree) -- this dataset lives
  entirely under `data/synthetic/demo_2025_2026/`.
- Every row carries `DATA_ORIGIN = SYNTHETIC` once run through
  `src/business/canonical.build_canonical_dataset`.
- No POI-Stock, material, quantity, or manual-override relationship is
  fabricated: the demo input table only ever populates the five documented
  component-date columns (plus the identifying columns needed by the
  existing canonical builder). `SemTheorique`/`DateMax` (the *historical*
  columns) are deliberately left NULL -- this dataset has no historical
  reference to compare against, and inventing one would be exactly the
  kind of unconfirmed relationship the project rules forbid.
- Identifiers are NOT reused verbatim as (Id_Sim, POI_Sim): `Id_Sim` is
  forced to a sentinel value (`configs.settings.DEMO_ID_SIM`) that cannot
  collide with any Id_Sim seen in the real data, specifically so a demo
  canonical row can never be mistaken for, or accidentally joined with, a
  real one. `POI_Sim` values ARE reused from the real extract for the bulk
  rows (a real, valid identifier *shape*, per "reuse ... as an
  identifier/schema scaffold") -- but always paired with the sentinel
  Id_Sim, and always under `data/synthetic/`.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs.settings import (  # noqa: E402
    COMPONENT_DATE_COLUMNS,
    DEMO_BULK_ROWS,
    DEMO_ID_SIM,
    DEMO_RANGE_END,
    DEMO_RANGE_START,
    DEMO_SEED,
)
from src.business.date_parsing import parse_date  # noqa: E402
from src.business.rules import COMPONENTS  # noqa: E402

RANGE_START: date = date.fromisoformat(DEMO_RANGE_START)
RANGE_END: date = date.fromisoformat(DEMO_RANGE_END)
_SPAN_DAYS = (RANGE_END - RANGE_START).days

_RAW_COLUMNS = (
    "Id_SimPoi",
    "Id_Sim",
    "POI_Sim",
    "DateTissu",
    "DateTissuSec",
    "DateFourniture",
    "DateFil",
    "DateOKProduction",
    "DateMax",
    "SemTheorique",
)

# Offsets chosen far outside any real Id_SimPoi observed in the raw dump, so
# a demo row's technical PK can never collide with a real one even if the
# two datasets were ever concatenated by mistake.
_EDGE_ID_SIMPOI_BASE = 900_000_000
_BULK_ID_SIMPOI_BASE = 900_100_000


def _rand_date(rng: random.Random) -> date:
    return RANGE_START + timedelta(days=rng.randint(0, _SPAN_DAYS))


def _iso(d: date) -> str:
    return d.isoformat()


@dataclass(frozen=True)
class EdgeCase:
    key: str
    description: str
    dates: dict[str, date]
    expected_blocking: tuple[str, ...]
    expected_date_theorique: date


def build_edge_cases() -> list[EdgeCase]:
    """Curated, deterministic edge cases (NOT randomly generated) so the
    required properties are guaranteed rather than left to chance:
    each of the five components as sole blocker, a 2-way tie, a 3-way tie,
    a 5-way tie, the range boundaries, and the ISO year-boundary cluster
    around 2025-12-29 -- the only place within [2025-01-01, 2026-06-30]
    where the calendar year differs from the ISO week-year (verified by
    direct `date.isocalendar()` computation; there is no such date near
    either end of the range in the other direction -- 2025-01-01 and
    2026-01-01 both fall in ISO week 1 of their own calendar year).
    """
    d = date  # local alias for brevity below

    def single_block(name: str, blocker_offset_days: int) -> EdgeCase:
        base = RANGE_START + timedelta(days=200)
        dates = {c: base - timedelta(days=10 + i * 3) for i, c in enumerate(COMPONENTS)}
        dates[name] = base + timedelta(days=blocker_offset_days)
        max_date = max(dates.values())
        blockers = tuple(c for c, v in dates.items() if v == max_date)
        return EdgeCase(
            key=f"BLOCK_{name}",
            description=f"{name} is the sole blocking component",
            dates=dates,
            expected_blocking=blockers,
            expected_date_theorique=max_date,
        )

    cases: list[EdgeCase] = [single_block(c, 20) for c in COMPONENTS]

    # 2-way tie: TISSU and FIL share the latest date.
    tie2_max = d(2025, 6, 15)
    tie2 = {
        "TISSU": tie2_max,
        "TISSU_SEC": tie2_max - timedelta(days=5),
        "FOURNITURE": tie2_max - timedelta(days=12),
        "FIL": tie2_max,
        "OK_PRODUCTION": tie2_max - timedelta(days=3),
    }
    cases.append(
        EdgeCase(
            key="TIE_2WAY",
            description="TISSU and FIL tie for the latest (blocking) date",
            dates=tie2,
            expected_blocking=("TISSU", "FIL"),
            expected_date_theorique=tie2_max,
        )
    )

    # 3-way tie: TISSU, TISSU_SEC, OK_PRODUCTION share the latest date.
    tie3_max = d(2025, 9, 1)
    tie3 = {
        "TISSU": tie3_max,
        "TISSU_SEC": tie3_max,
        "FOURNITURE": tie3_max - timedelta(days=30),
        "FIL": tie3_max - timedelta(days=1),
        "OK_PRODUCTION": tie3_max,
    }
    cases.append(
        EdgeCase(
            key="TIE_3WAY",
            description="TISSU, TISSU_SEC and OK_PRODUCTION tie for the latest date",
            dates=tie3,
            expected_blocking=("TISSU", "TISSU_SEC", "OK_PRODUCTION"),
            expected_date_theorique=tie3_max,
        )
    )

    # 5-way tie: every component identical.
    tie5_max = d(2025, 3, 10)
    tie5 = {c: tie5_max for c in COMPONENTS}
    cases.append(
        EdgeCase(
            key="TIE_5WAY",
            description="All five components share the exact same date",
            dates=tie5,
            expected_blocking=tuple(COMPONENTS),
            expected_date_theorique=tie5_max,
        )
    )

    # Range-start boundary: every component AT the earliest allowed date.
    cases.append(
        EdgeCase(
            key="RANGE_START",
            description=f"All components dated exactly at the range start ({RANGE_START.isoformat()})",
            dates={c: RANGE_START for c in COMPONENTS},
            expected_blocking=tuple(COMPONENTS),
            expected_date_theorique=RANGE_START,
        )
    )

    # Range-end boundary: the blocking component sits AT the latest allowed date.
    range_end_dates = {c: RANGE_END - timedelta(days=5 + i * 4) for i, c in enumerate(COMPONENTS)}
    range_end_dates["OK_PRODUCTION"] = RANGE_END
    cases.append(
        EdgeCase(
            key="RANGE_END",
            description=f"OK_PRODUCTION dated exactly at the range end ({RANGE_END.isoformat()})",
            dates=range_end_dates,
            expected_blocking=("OK_PRODUCTION",),
            expected_date_theorique=RANGE_END,
        )
    )

    # ISO year-boundary cluster: calendar year 2025, ISO week-year 2026.
    # date.isocalendar() for these three dates (verified directly):
    #   2025-12-29 -> ISO 2026-W01   2025-12-30 -> ISO 2026-W01   2025-12-31 -> ISO 2026-W01
    for boundary_date, key_suffix in (
        (d(2025, 12, 29), "2025_12_29"),
        (d(2025, 12, 30), "2025_12_30"),
        (d(2025, 12, 31), "2025_12_31"),
    ):
        dates = {c: boundary_date - timedelta(days=2 + i) for i, c in enumerate(COMPONENTS)}
        dates["TISSU"] = boundary_date
        cases.append(
            EdgeCase(
                key=f"ISO_YEAR_BOUNDARY_{key_suffix}",
                description=(
                    f"TISSU dated {boundary_date.isoformat()}: calendar year 2025, "
                    f"but ISO week-year 2026 (ISO week 01) -- calendar year != ISO year"
                ),
                dates=dates,
                expected_blocking=("TISSU",),
                expected_date_theorique=boundary_date,
            )
        )

    return cases


def _edge_case_rows(cases: list[EdgeCase]) -> list[dict]:
    rows = []
    for i, case in enumerate(cases):
        row = {col: None for col in _RAW_COLUMNS}
        row["Id_SimPoi"] = _EDGE_ID_SIMPOI_BASE + i
        row["Id_Sim"] = str(DEMO_ID_SIM)
        row["POI_Sim"] = f"DEMO-EDGE-{case.key}"
        for component, d in case.dates.items():
            row[COMPONENT_DATE_COLUMNS[component]] = _iso(d)
        rows.append(row)
    return rows


@dataclass
class GenerationStats:
    seed: int
    range_start: str
    range_end: str
    n_bulk: int
    n_edge_cases: int
    real_poi_sim_source_count: int
    preserved_from_real: dict[str, int] = field(default_factory=dict)
    replaced_synthetic: dict[str, int] = field(default_factory=dict)


def _preserve_or_generate(
    raw_value: object, rng: random.Random, counters: tuple[dict, dict], component: str
) -> str:
    """Preserve a real component date only if it parses and falls within the
    mandated [RANGE_START, RANGE_END] window; otherwise draw a fresh
    synthetic date. Both outcomes are counted for metadata/generation_metadata.json.
    """
    preserved_counts, replaced_counts = counters
    parsed = parse_date(raw_value)
    if parsed.is_valid and parsed.value is not None and RANGE_START <= parsed.value <= RANGE_END:
        preserved_counts[component] = preserved_counts.get(component, 0) + 1
        return _iso(parsed.value)
    replaced_counts[component] = replaced_counts.get(component, 0) + 1
    return _iso(_rand_date(rng))


def build_demo_dataset(
    real_poi_df: pd.DataFrame | None = None,
    *,
    n_bulk: int = DEMO_BULK_ROWS,
    seed: int = DEMO_SEED,
) -> tuple[pd.DataFrame, GenerationStats]:
    """Build the full demo input table (edge cases + bulk rows).

    ``real_poi_df`` is the raw `plan_t_simplanifpoi` DataFrame (as produced
    by src/ingestion/sql_ingestion.py); it is used ONLY as a source of
    realistic `POI_Sim` identifier strings and, per the preservation rule,
    as a source of already-valid in-range dates (see module docstring).
    Every row's `Id_Sim` is forced to the sentinel `DEMO_ID_SIM` regardless
    of the source. If ``real_poi_df`` is None, fresh synthetic identifiers
    are generated instead (used by tests that must not depend on the large
    raw SQL file being present).
    """
    rng = random.Random(seed)
    preserved: dict[str, int] = {}
    replaced: dict[str, int] = {}
    counters = (preserved, replaced)

    edge_cases = build_edge_cases()
    rows = _edge_case_rows(edge_cases)

    if real_poi_df is not None and len(real_poi_df) > 0:
        sample_n = min(n_bulk, len(real_poi_df))
        sampled = real_poi_df.sample(n=sample_n, random_state=seed).reset_index(drop=True)
        poi_sim_values = sampled["POI_Sim"].tolist()
        source_rows = sampled.to_dict("records")
        real_source_count = len(real_poi_df)
    else:
        poi_sim_values = [f"DEMO{i:06d}CD" for i in range(n_bulk)]
        source_rows = [dict.fromkeys(_RAW_COLUMNS) for _ in range(n_bulk)]
        real_source_count = 0

    for i, (poi_sim, source_row) in enumerate(zip(poi_sim_values, source_rows)):
        row = {col: None for col in _RAW_COLUMNS}
        row["Id_SimPoi"] = _BULK_ID_SIMPOI_BASE + i
        row["Id_Sim"] = str(DEMO_ID_SIM)
        row["POI_Sim"] = poi_sim
        for component, column in COMPONENT_DATE_COLUMNS.items():
            raw_value = source_row.get(column)
            row[column] = _preserve_or_generate(raw_value, rng, counters, component)
        rows.append(row)

    df = pd.DataFrame(rows, columns=list(_RAW_COLUMNS))

    stats = GenerationStats(
        seed=seed,
        range_start=RANGE_START.isoformat(),
        range_end=RANGE_END.isoformat(),
        n_bulk=len(poi_sim_values),
        n_edge_cases=len(edge_cases),
        real_poi_sim_source_count=real_source_count,
        preserved_from_real=preserved,
        replaced_synthetic=replaced,
    )
    return df, stats
