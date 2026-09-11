"""Batch and single-POI simulator built on top of the canonical dataset.

docs/execution/10_simulator_specification.md defines the expected output
per POI: POI, DateTheorique, SemTheorique, BlockingElement,
CalculationStatus, QualityFlags. This module adapts the canonical dataset
into that explainable, user-facing shape and provides the historical
validation comparison described in
docs/execution/08_canonical_dataset_specification.md ("Validation Metrics").
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PoiSimulationOutput:
    id_sim: object
    poi_sim: object
    date_theorique: object
    sem_theorique: object
    sem_theorique_label: object
    blocking_element: list[str]
    calculation_status: str
    missing_components: list[str]
    invalid_components: list[str]
    suspicious_components: list[str]
    data_quality_flag: list[str]
    component_dates: dict[str, object]
    data_origin: str


_COMPONENT_DATE_FIELDS = {
    "TISSU": "date_tissu",
    "TISSU_SEC": "date_tissu_sec",
    "FOURNITURE": "date_fourniture",
    "FIL": "date_fil",
    "OK_PRODUCTION": "date_ok_production",
}


def to_simulation_output(canonical_row: pd.Series) -> PoiSimulationOutput:
    return PoiSimulationOutput(
        id_sim=canonical_row["id_sim"],
        poi_sim=canonical_row["poi_sim"],
        date_theorique=canonical_row["date_theorique"],
        sem_theorique=canonical_row["sem_theorique"],
        sem_theorique_label=canonical_row["sem_theorique_label"],
        blocking_element=list(canonical_row["blocking_element"]),
        calculation_status=canonical_row["calculation_status"],
        missing_components=list(canonical_row["missing_components"]),
        invalid_components=list(canonical_row["invalid_components"]),
        suspicious_components=list(canonical_row["suspicious_components"]),
        data_quality_flag=list(canonical_row["data_quality_flag"]),
        component_dates={c: canonical_row[f] for c, f in _COMPONENT_DATE_FIELDS.items()},
        data_origin=canonical_row["data_origin"],
    )


def lookup_poi(canonical_df: pd.DataFrame, id_sim: object, poi_sim: str) -> PoiSimulationOutput | None:
    matches = canonical_df[
        (canonical_df["id_sim"].astype(str) == str(id_sim))
        & (canonical_df["poi_sim"].astype(str) == str(poi_sim))
    ]
    if matches.empty:
        return None
    return to_simulation_output(matches.iloc[0])


def run_batch(canonical_df: pd.DataFrame) -> list[PoiSimulationOutput]:
    return [to_simulation_output(row) for _, row in canonical_df.iterrows()]


# ---------------------------------------------------------------------------
# Historical validation (docs/execution/08, "Validation Against Historical
# Data" / docs/execution/13_testing_strategy.md, "Historical Validation")
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationSummary:
    total_pois: int
    complete_pois: int  # calculation_status == CALCULATED
    incomplete_pois: int
    comparable_pois: int  # CALCULATED and historical value present and parseable
    matches: int
    mismatches: int
    match_rate: float | None  # None when there are zero comparable POIs


def validate_against_historical(canonical_df: pd.DataFrame) -> ValidationSummary:
    """Compare calculated week_key against historical_sem_theorique.

    The historical field's exact week convention is UNCONFIRMED (see
    docs/context/Theoretical Week (SemTheorique).md section 15), so this
    comparison only counts a POI as comparable when the historical value,
    read as a bare 6-digit YYYYWW string, matches the calculated week_key
    format. Anything else is left out of the denominator rather than forced
    into a false match or mismatch.
    """
    total = len(canonical_df)
    calculated = canonical_df[canonical_df["calculation_status"] == "CALCULATED"]
    incomplete = total - len(calculated)

    historical = calculated["historical_sem_theorique"].astype("string").str.strip()
    comparable_mask = historical.str.fullmatch(r"\d{6}")
    comparable = calculated[comparable_mask.fillna(False)]

    if comparable.empty:
        return ValidationSummary(
            total_pois=total,
            complete_pois=len(calculated),
            incomplete_pois=incomplete,
            comparable_pois=0,
            matches=0,
            mismatches=0,
            match_rate=None,
        )

    matches = int((comparable["week_key"] == comparable["historical_sem_theorique"]).sum())
    mismatches = len(comparable) - matches
    return ValidationSummary(
        total_pois=total,
        complete_pois=len(calculated),
        incomplete_pois=incomplete,
        comparable_pois=len(comparable),
        matches=matches,
        mismatches=mismatches,
        match_rate=round(matches / len(comparable), 4),
    )
