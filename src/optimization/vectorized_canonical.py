"""Vectorized (pandas-native) re-implementation of canonical dataset
construction, built ONLY after profiling identified the per-row Python loop
in src/business/canonical.py as the dominant cost
(see outputs/benchmarks/bottleneck_profile.txt and
docs/decisions/0002-vectorized-optimization.md).

This module implements the exact same logical calculation as
src/business/rules.calculate_theoretical_week under the default
ALL_REQUIRED applicability policy (no per-row applicability overrides,
which the baseline engine supports but which are not exercised by the
current real or synthetic datasets). Equivalence with the baseline is
enforced by tests/unit/test_vectorized_equivalence.py, which runs both
implementations over the same random/edge-case data and asserts identical
output -- per docs/execution/11_benchmarking_plan.md and
docs/execution/12_hadoop_mapreduce_plan.md ("Correctness ... Expected:
Result == Result").

Strategy: parse each of the five date columns with the fast, fully
vectorized `pd.to_datetime` path first (this matches the ISO 'YYYY-MM-DD'
format used throughout the real dumps); any value that fails the fast path
but is not blank is re-parsed with the slow, format-tolerant
`business.date_parsing.parse_date` (rare in practice, so the cost is
bounded by how much genuinely malformed data exists).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs.settings import COMPONENT_DATE_COLUMNS  # noqa: E402
from src.business.canonical import CANONICAL_COLUMNS  # noqa: E402
from src.business.date_parsing import is_suspicious, parse_date  # noqa: E402
from src.business.enums import CalculationStatus, DataOrigin, QualityFlag  # noqa: E402
from src.business.rules import COMPONENTS  # noqa: E402

_PLAUSIBLE_MIN = date(2000, 1, 1)
_PLAUSIBLE_MAX = date(2035, 12, 31)


def _parse_component_column(raw: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Return (parsed_dates, invalid_mask) for one component column.

    parsed_dates is a datetime64[ns] Series (NaT for missing AND invalid).
    invalid_mask is True only for non-blank values that could not be parsed
    at all (distinguishing "invalid" from "missing").
    """
    text = raw.astype("string")
    is_blank = text.isna() | (text.str.strip() == "")

    fast = pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")
    needs_fallback = (~is_blank) & fast.isna()

    if needs_fallback.any():
        fallback_values = text[needs_fallback].map(lambda v: parse_date(v).value)
        fast = fast.copy()
        fast.loc[needs_fallback] = pd.to_datetime(fallback_values)

    invalid_mask = (~is_blank) & fast.isna()
    return fast, invalid_mask


def _dt_to_date_or_none(series: pd.Series) -> pd.Series:
    """Convert a datetime64 Series to a Series of ``date`` objects / ``None``.

    Plain ``.dt.date`` is avoided here: on some pandas versions it leaves an
    all-NaT column as datetime64 instead of converting to NaN/object,
    which would make NaT (not None) leak into the canonical dataset and
    break equivalence with the baseline engine (which always uses ``None``
    for a missing date).
    """
    return series.apply(lambda v: v.date() if pd.notna(v) else None)


def build_canonical_dataset_vectorized(
    poi_df: pd.DataFrame,
    *,
    data_origin: DataOrigin = DataOrigin.REAL,
    id_sim_column: str = "Id_Sim",
    poi_sim_column: str = "POI_Sim",
    id_simpoi_column: str = "Id_SimPoi",
) -> pd.DataFrame:
    n = len(poi_df)
    parsed: dict[str, pd.Series] = {}
    invalid: dict[str, pd.Series] = {}

    for component, column in COMPONENT_DATE_COLUMNS.items():
        raw = poi_df[column] if column in poi_df.columns else pd.Series([None] * n)
        parsed[component], invalid[component] = _parse_component_column(raw)

    missing = {c: parsed[c].isna() & ~invalid[c] for c in COMPONENTS}
    suspicious = {
        c: parsed[c].notna()
        & (parsed[c] < pd.Timestamp(_PLAUSIBLE_MIN))
        | (parsed[c] > pd.Timestamp(_PLAUSIBLE_MAX))
        for c in COMPONENTS
    }

    any_invalid = np.logical_or.reduce([invalid[c].to_numpy() for c in COMPONENTS])
    any_missing = np.logical_or.reduce([missing[c].to_numpy() for c in COMPONENTS])

    status = np.where(
        any_invalid,
        CalculationStatus.INVALID_DATA.value,
        np.where(any_missing, CalculationStatus.INCOMPLETE_DATA.value, CalculationStatus.CALCULATED.value),
    )

    date_matrix = pd.concat([parsed[c] for c in COMPONENTS], axis=1)
    date_matrix.columns = list(COMPONENTS)
    date_theorique = date_matrix.max(axis=1)

    is_calculated = status == CalculationStatus.CALCULATED.value
    date_theorique = date_theorique.where(is_calculated)

    iso = date_theorique.dt.isocalendar()
    iso_year = iso["year"].where(is_calculated)
    iso_week = iso["week"].where(is_calculated)
    week_key = np.where(
        is_calculated,
        iso_year.astype("Int64").astype("string") + iso_week.astype("Int64").astype("string").str.zfill(2),
        None,
    )
    sem_label = np.where(is_calculated, "S" + iso_week.astype("Int64").astype("string").str.zfill(2), None)

    blocking_matrix = pd.DataFrame(
        {c: (date_matrix[c] == date_theorique).to_numpy() for c in COMPONENTS}
    )

    blocking_element = []
    missing_components = []
    invalid_components = []
    suspicious_components = []
    quality_flags = []

    missing_arr = {c: missing[c].to_numpy() for c in COMPONENTS}
    invalid_arr = {c: invalid[c].to_numpy() for c in COMPONENTS}
    suspicious_arr = {c: suspicious[c].to_numpy() for c in COMPONENTS}
    blocking_arr = {c: blocking_matrix[c].to_numpy() for c in COMPONENTS}

    for i in range(n):
        row_status = status[i]
        row_missing = [c for c in COMPONENTS if missing_arr[c][i]]
        row_invalid = [c for c in COMPONENTS if invalid_arr[c][i]]
        row_suspicious = [c for c in COMPONENTS if suspicious_arr[c][i]]
        flags = []
        if row_invalid:
            flags.append(QualityFlag.INVALID_DATE.value)
        if row_suspicious:
            flags.append(QualityFlag.SUSPICIOUS_DATE.value)
        if row_status == CalculationStatus.INCOMPLETE_DATA.value:
            flags.append(QualityFlag.MISSING_COMPONENT_DATE.value)

        if row_status == CalculationStatus.CALCULATED.value:
            blocking_element.append([c for c in COMPONENTS if blocking_arr[c][i]])
            missing_components.append([])
            invalid_components.append([])
        else:
            blocking_element.append([])
            missing_components.append(row_missing)
            invalid_components.append(row_invalid)
        suspicious_components.append(row_suspicious)
        quality_flags.append(flags)

    out = pd.DataFrame(
        {
            "id_sim": poi_df[id_sim_column].to_numpy() if id_sim_column in poi_df.columns else None,
            "poi_sim": poi_df[poi_sim_column].to_numpy() if poi_sim_column in poi_df.columns else None,
            "id_simpoi": poi_df[id_simpoi_column].to_numpy() if id_simpoi_column in poi_df.columns else None,
            "date_tissu": _dt_to_date_or_none(parsed["TISSU"]),
            "date_tissu_sec": _dt_to_date_or_none(parsed["TISSU_SEC"]),
            "date_fourniture": _dt_to_date_or_none(parsed["FOURNITURE"]),
            "date_fil": _dt_to_date_or_none(parsed["FIL"]),
            "date_ok_production": _dt_to_date_or_none(parsed["OK_PRODUCTION"]),
            "date_theorique": _dt_to_date_or_none(date_theorique),
            "iso_year": iso_year,
            "iso_week": iso_week,
            "week_key": week_key,
            "sem_theorique": week_key,
            "sem_theorique_label": sem_label,
            "blocking_element": blocking_element,
            "calculation_status": status,
            "missing_components": missing_components,
            "invalid_components": invalid_components,
            "suspicious_components": suspicious_components,
            "data_origin": data_origin.value,
            "data_quality_flag": quality_flags,
            "historical_sem_theorique": poi_df.get("SemTheorique"),
            "historical_date_max": poi_df.get("DateMax"),
            "source_table": "plan_t_simplanifpoi",
        }
    )
    return out[list(CANONICAL_COLUMNS)]
