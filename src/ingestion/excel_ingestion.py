"""Load the supporting Excel workbooks into pandas DataFrames.

Evidence for sheet contents: docs/analysis/TASK2_Supporting_Sources_Business_Mapping.md.
As with sql_ingestion.py, no cleaning happens here -- values are read as-is.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs import settings  # noqa: E402


def load_workbook(path: str | Path) -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(path)
    return {sheet: xl.parse(sheet) for sheet in xl.sheet_names}


def ingest_all_excel(write_interim: bool = True) -> dict[str, dict[str, pd.DataFrame]]:
    """Returns {workbook_key: {sheet_name: DataFrame}}.

    Workbook keys match configs.settings.RAW_EXCEL_FILES:
      - "table": sheets 'tablerecappoi_piq', 'plan_t_simplaniffourniture'
      - "consommation_tissu": sheet 'Feuil1'
      - "cde": sheets 'Liste cde tissu', 'detail prevision reception',
               'cde FN', 'detail reception FN'
    """
    settings.DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    workbooks: dict[str, dict[str, pd.DataFrame]] = {}
    for key, path in settings.RAW_EXCEL_FILES.items():
        sheets = load_workbook(path)
        workbooks[key] = sheets
        if write_interim:
            for sheet_name, df in sheets.items():
                safe_sheet = sheet_name.replace(" ", "_").replace("/", "_")
                out_path = settings.DATA_INTERIM / f"excel.{key}.{safe_sheet}.raw.parquet"
                # Excel cells can carry mixed types (e.g. some numeric-looking
                # columns hold text codes); coerce object columns to str so
                # parquet always accepts them without inventing a schema.
                df_to_write = df.copy()
                for col in df_to_write.columns:
                    if df_to_write[col].dtype == object:
                        df_to_write[col] = df_to_write[col].astype(str).where(df_to_write[col].notna(), None)
                df_to_write.to_parquet(out_path, index=False)
    return workbooks


if __name__ == "__main__":
    workbooks = ingest_all_excel()
    for key, sheets in workbooks.items():
        for sheet_name, df in sheets.items():
            print(f"{key} / {sheet_name}: {len(df):,} rows x {len(df.columns)} cols")
