"""Identifier normalization and typed conversion of raw ingested tables.

Normalization never overwrites or discards the original raw value: every
normalized column is added alongside the source column so the
transformation stays traceable to its input (MASTER_PROMPT.md section 18 /
docs/execution/08, "Provenance").
"""

from __future__ import annotations

import pandas as pd


def normalize_id_sim(df: pd.DataFrame, column: str = "Id_Sim") -> pd.DataFrame:
    """Id_Sim is documented as int(11); the raw ingestion keeps it as a
    string. Coerce to nullable Int64, recording failures rather than
    silently dropping them.
    """
    out = df.copy()
    out[f"{column}_int"] = pd.to_numeric(out[column], errors="coerce").astype("Int64")
    return out


def normalize_poi_sim(df: pd.DataFrame, column: str = "POI_Sim") -> pd.DataFrame:
    """Strip incidental whitespace. Case is preserved: docs/analysis findings
    show POI_Sim codes are consistently upper-case in the supplied extract,
    and no evidence supports case-folding this identifier (unlike Code_Sim,
    see normalize_code_sim).
    """
    out = df.copy()
    out[f"{column}_norm"] = out[column].astype("string").str.strip()
    return out


def normalize_code_sim(df: pd.DataFrame, column: str = "Code_Sim") -> pd.DataFrame:
    """Fold case for the stock material code.

    Evidence: docs/analysis/PHASE0_Initial_Project_Assessment.md observed 8
    codes appearing in both upper and lower case (e.g. 'YT16169'/'yt16169'),
    affecting 1,715 rows, and confirmed the distinct-code count drops from
    7,331 to 7,323 under case folding. This is treated as a data-entry
    artifact (RECOMMENDATION), not as two different materials.
    """
    out = df.copy()
    out[f"{column}_norm"] = out[column].astype("string").str.strip().str.upper()
    return out


def normalize_quantity(df: pd.DataFrame, column: str = "Qte") -> pd.DataFrame:
    out = df.copy()
    out[f"{column}_numeric"] = pd.to_numeric(out[column], errors="coerce")
    return out
