"""Load the three raw SQL dumps into pandas DataFrames.

This stage performs NO cleaning and NO type coercion beyond what is needed
to get raw string/None values into a DataFrame: every value read from the
dump is kept as the original string (or ``None``). Parsing dates, folding
identifier case, etc. happens in ``src/preprocessing/cleaning.py`` -- kept
separate so a conversion failure is never silently absorbed here (see
docs/execution/09_pipeline_architecture.md, stage 1 "Ingestion": "Load raw
files without modifying them").
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs import settings  # noqa: E402
from src.ingestion.mysql_dump_parser import iter_rows, parse_create_table  # noqa: E402


def load_sql_table_as_dataframe(sql_path: str | Path) -> pd.DataFrame:
    """Read one dump file into a DataFrame of raw strings (object dtype)."""
    schema = parse_create_table(sql_path)
    rows = list(iter_rows(sql_path, expected_table=schema.table_name))
    return pd.DataFrame(rows, columns=list(schema.columns), dtype=object)


def ingest_all_sql_tables(write_interim: bool = True) -> dict[str, pd.DataFrame]:
    """Ingest plan_t_simplanif, plan_t_simplanifpoi, plan_t_simplanifstock.

    Returns a dict keyed by table name. When ``write_interim`` is True, each
    DataFrame is also written to ``data/interim/<table>.raw.parquet`` for
    reproducibility and to avoid re-parsing the multi-megabyte dumps on
    every run.
    """
    settings.DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    tables: dict[str, pd.DataFrame] = {}
    for name, path in settings.RAW_SQL_FILES.items():
        df = load_sql_table_as_dataframe(path)
        tables[name] = df
        if write_interim:
            out_path = settings.DATA_INTERIM / f"{name}.raw.parquet"
            df.to_parquet(out_path, index=False)
    return tables


if __name__ == "__main__":
    tables = ingest_all_sql_tables()
    for name, df in tables.items():
        print(f"{name}: {len(df):,} rows x {len(df.columns)} cols "
              f"-> data/interim/{name}.raw.parquet")
