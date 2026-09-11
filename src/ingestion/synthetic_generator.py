"""Reproducible synthetic POI dataset generator.

Used ONLY for:
  - unit/integration/validation tests that need edge cases the real extract
    does not contain (e.g. a populated historical SemTheorique, or a
    deliberate tie), per docs/execution/13_testing_strategy.md
    ("Synthetic Data") and MASTER_PROMPT.md section 16;
  - benchmark scale-up beyond the 12,302 real POI rows
    (docs/execution/11_benchmarking_plan.md, "Scaling").

Every row produced here carries DATA_ORIGIN = SYNTHETIC end to end (see
src/business/canonical.py, ``data_origin`` parameter) and MUST NEVER be
written into data/interim, data/processed, or data/canonical alongside real
rows -- see MASTER_PROMPT.md section 2.3. Synthetic output belongs in
benchmarks/datasets/.

The generator is deterministic for a fixed seed (default: configs.settings.RANDOM_SEED).
It does not reproduce any real company data; row shapes mimic only the
*schema* documented in docs/context/plan_t_simplanifpoi.md, not real values.
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs.settings import COMPONENT_DATE_COLUMNS, RANDOM_SEED  # noqa: E402
from src.business.rules import COMPONENTS, calculate_theoretical_week  # noqa: E402

_RAW_POI_COLUMNS = (
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


@dataclass(frozen=True)
class SyntheticMix:
    """Row-category proportions. Must sum to 1.0."""

    complete_all_dates: float = 0.55
    complete_with_tie: float = 0.10
    missing_one_required: float = 0.20
    missing_all: float = 0.05
    invalid_date: float = 0.05
    suspicious_date: float = 0.05

    def validate(self) -> None:
        total = (
            self.complete_all_dates
            + self.complete_with_tie
            + self.missing_one_required
            + self.missing_all
            + self.invalid_date
            + self.suspicious_date
        )
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"SyntheticMix proportions must sum to 1.0, got {total}")


_BASE_DATE = date(2025, 1, 6)  # a Monday, for deterministic ISO-week arithmetic
_INVALID_SAMPLES = ("2025-99-40", "31/31/2025", "ABC", "0000-00-00")


def _random_date(rng: random.Random, day_span: int = 365) -> date:
    return _BASE_DATE + timedelta(days=rng.randint(0, day_span))


def generate_synthetic_poi_rows(
    n_rows: int,
    *,
    seed: int = RANDOM_SEED,
    id_sim: int = 900000,
    mix: SyntheticMix = SyntheticMix(),
    populate_historical: bool = True,
    historical_mismatch_rate: float = 0.1,
) -> pd.DataFrame:
    """Generate ``n_rows`` synthetic POI records as raw strings, matching the
    real ``plan_t_simplanifpoi`` column names so they can flow through the
    exact same ingestion/canonical code path as real data.
    """
    mix.validate()
    rng = random.Random(seed)
    rows: list[dict] = []

    boundaries = [
        mix.complete_all_dates,
        mix.complete_all_dates + mix.complete_with_tie,
        mix.complete_all_dates + mix.complete_with_tie + mix.missing_one_required,
        mix.complete_all_dates + mix.complete_with_tie + mix.missing_one_required + mix.missing_all,
        mix.complete_all_dates
        + mix.complete_with_tie
        + mix.missing_one_required
        + mix.missing_all
        + mix.invalid_date,
    ]

    for i in range(n_rows):
        r = rng.random()
        component_values: dict[str, str | None] = {}

        if r < boundaries[0]:
            # All five components present, distinct dates.
            for comp in COMPONENTS:
                component_values[comp] = _random_date(rng).isoformat()
        elif r < boundaries[1]:
            # All five present, with an intentional tie on the maximum date.
            shared_max = _random_date(rng)
            tied = rng.sample(COMPONENTS, k=2)
            for comp in COMPONENTS:
                if comp in tied:
                    component_values[comp] = shared_max.isoformat()
                else:
                    component_values[comp] = (
                        shared_max - timedelta(days=rng.randint(1, 30))
                    ).isoformat()
        elif r < boundaries[2]:
            # Exactly one required component missing.
            missing = rng.choice(COMPONENTS)
            for comp in COMPONENTS:
                component_values[comp] = None if comp == missing else _random_date(rng).isoformat()
        elif r < boundaries[3]:
            for comp in COMPONENTS:
                component_values[comp] = None
        elif r < boundaries[4]:
            bad = rng.choice(_INVALID_SAMPLES)
            broken = rng.choice(COMPONENTS)
            for comp in COMPONENTS:
                component_values[comp] = bad if comp == broken else _random_date(rng).isoformat()
        else:
            far_future = date(2099, 1, 1)
            suspicious = rng.choice(COMPONENTS)
            for comp in COMPONENTS:
                component_values[comp] = (
                    far_future.isoformat() if comp == suspicious else _random_date(rng).isoformat()
                )

        raw_component_dates = {
            comp: component_values[comp] for comp in COMPONENTS
        }
        historical_sem_theorique = None
        historical_date_max = None
        if populate_historical:
            result = calculate_theoretical_week(raw_component_dates)
            if result.status.value == "CALCULATED":
                if rng.random() < historical_mismatch_rate:
                    # Deliberately wrong historical value, to exercise
                    # mismatch detection (docs/context/Edge Cases & Data
                    # Quality Handling.md item 8).
                    fake = (result.date_theorique + timedelta(days=14))
                    historical_sem_theorique = f"{fake.isocalendar()[0]}{fake.isocalendar()[1]:02d}"
                else:
                    historical_sem_theorique = result.sem_theorique
                historical_date_max = result.date_theorique.isoformat()

        poi_sim = f"SYN{id_sim}{i:06d}"
        rows.append(
            {
                "Id_SimPoi": 1_000_000 + i,
                "Id_Sim": str(id_sim),
                "POI_Sim": poi_sim,
                COMPONENT_DATE_COLUMNS["TISSU"]: raw_component_dates["TISSU"],
                COMPONENT_DATE_COLUMNS["TISSU_SEC"]: raw_component_dates["TISSU_SEC"],
                COMPONENT_DATE_COLUMNS["FOURNITURE"]: raw_component_dates["FOURNITURE"],
                COMPONENT_DATE_COLUMNS["FIL"]: raw_component_dates["FIL"],
                COMPONENT_DATE_COLUMNS["OK_PRODUCTION"]: raw_component_dates["OK_PRODUCTION"],
                "DateMax": historical_date_max,
                "SemTheorique": historical_sem_theorique,
            }
        )

    return pd.DataFrame(rows, columns=list(_RAW_POI_COLUMNS))


if __name__ == "__main__":
    df = generate_synthetic_poi_rows(20)
    print(df.head(20).to_string())
