"""Build the canonical POI dataset defined in
docs/execution/08_canonical_dataset_specification.md, by applying the pure
calculation engine (src/business/rules.py) to every raw POI row.

Grain: one row per simulated POI, identified by (id_sim, poi_sim), per
docs/execution/08 ("Target Grain").
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs.settings import COMPONENT_DATE_COLUMNS  # noqa: E402
from src.business.enums import DataOrigin  # noqa: E402
from src.business.rules import calculate_theoretical_week  # noqa: E402

CANONICAL_COLUMNS: tuple[str, ...] = (
    "id_sim",
    "poi_sim",
    "id_simpoi",
    "date_tissu",
    "date_tissu_sec",
    "date_fourniture",
    "date_fil",
    "date_ok_production",
    "date_theorique",
    "iso_year",
    "iso_week",
    "week_key",
    "sem_theorique",
    "sem_theorique_label",
    "blocking_element",
    "calculation_status",
    "missing_components",
    "invalid_components",
    "suspicious_components",
    "data_origin",
    "data_quality_flag",
    "historical_sem_theorique",
    "historical_date_max",
    "source_table",
)


def _component_dates_from_row(row: pd.Series) -> dict[str, object]:
    return {component: row.get(column) for component, column in COMPONENT_DATE_COLUMNS.items()}


def build_canonical_row(
    *,
    id_sim: object,
    poi_sim: object,
    id_simpoi: object = None,
    component_raw_dates: dict[str, object],
    historical_sem_theorique: object = None,
    historical_date_max: object = None,
    data_origin: DataOrigin = DataOrigin.REAL,
    source_table: str = "plan_t_simplanifpoi",
) -> dict:
    result = calculate_theoretical_week(component_raw_dates)
    c = result.components
    return {
        "id_sim": id_sim,
        "poi_sim": poi_sim,
        "id_simpoi": id_simpoi,
        "date_tissu": c["TISSU"].parsed.value,
        "date_tissu_sec": c["TISSU_SEC"].parsed.value,
        "date_fourniture": c["FOURNITURE"].parsed.value,
        "date_fil": c["FIL"].parsed.value,
        "date_ok_production": c["OK_PRODUCTION"].parsed.value,
        "date_theorique": result.date_theorique,
        "iso_year": result.iso_week.iso_year if result.iso_week else None,
        "iso_week": result.iso_week.iso_week if result.iso_week else None,
        "week_key": result.sem_theorique,
        "sem_theorique": result.sem_theorique,
        "sem_theorique_label": result.iso_week.label if result.iso_week else None,
        "blocking_element": list(result.blocking_elements),
        "calculation_status": result.status.value,
        "missing_components": list(result.missing_components),
        "invalid_components": list(result.invalid_components),
        "suspicious_components": list(result.suspicious_components),
        "data_origin": data_origin.value,
        "data_quality_flag": [f.value for f in result.quality_flags],
        "historical_sem_theorique": historical_sem_theorique,
        "historical_date_max": historical_date_max,
        "source_table": source_table,
    }


def build_canonical_dataset(
    poi_df: pd.DataFrame,
    *,
    data_origin: DataOrigin = DataOrigin.REAL,
    id_sim_column: str = "Id_Sim",
    poi_sim_column: str = "POI_Sim",
    id_simpoi_column: str = "Id_SimPoi",
) -> pd.DataFrame:
    """Apply the calculation engine to every row of a raw POI DataFrame.

    ``poi_df`` is expected to still hold raw string/None values as produced
    by src/ingestion/sql_ingestion.py (or an equivalent synthetic generator
    with the same column names) -- date parsing happens inside
    calculate_theoretical_week, not before this call.
    """
    rows = []
    for _, row in poi_df.iterrows():
        component_dates = _component_dates_from_row(row)
        rows.append(
            build_canonical_row(
                id_sim=row.get(id_sim_column),
                poi_sim=row.get(poi_sim_column),
                id_simpoi=row.get(id_simpoi_column),
                component_raw_dates=component_dates,
                historical_sem_theorique=row.get("SemTheorique"),
                historical_date_max=row.get("DateMax"),
                data_origin=data_origin,
            )
        )
    return pd.DataFrame(rows, columns=list(CANONICAL_COLUMNS))
