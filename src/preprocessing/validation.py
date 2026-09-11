"""Schema and data-quality validation for the raw ingested tables.

Implements docs/execution/09_pipeline_architecture.md stage 2/3 (Schema
Validation, Data Quality) and the checks enumerated in
docs/context/Data Model.md / Data Relationships.md. Every check here is
read-only: it reports issues, it never repairs or drops rows (that decision
belongs to the cleaning stage and must remain visible/traceable).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd


@dataclass
class KeyCheckResult:
    table: str
    key_columns: tuple[str, ...]
    total_rows: int
    distinct_keys: int
    duplicate_rows: int
    duplicate_key_examples: list[tuple] = field(default_factory=list)

    @property
    def is_unique(self) -> bool:
        return self.duplicate_rows == 0


@dataclass
class ReferentialCheckResult:
    child_table: str
    parent_table: str
    join_columns: tuple[str, ...]
    child_rows: int
    matched_rows: int
    orphan_rows: int
    match_rate: float


@dataclass
class ValidationReport:
    key_checks: list[KeyCheckResult] = field(default_factory=list)
    referential_checks: list[ReferentialCheckResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key_checks": [asdict(k) for k in self.key_checks],
            "referential_checks": [asdict(r) for r in self.referential_checks],
        }


def check_key_uniqueness(df: pd.DataFrame, key_columns: tuple[str, ...], table_name: str) -> KeyCheckResult:
    keys = df[list(key_columns)]
    dup_mask = keys.duplicated(keep=False)
    distinct = keys.drop_duplicates().shape[0]
    examples = (
        keys[dup_mask].drop_duplicates().head(5).apply(tuple, axis=1).tolist()
        if dup_mask.any()
        else []
    )
    return KeyCheckResult(
        table=table_name,
        key_columns=key_columns,
        total_rows=len(df),
        distinct_keys=distinct,
        duplicate_rows=int(dup_mask.sum()),
        duplicate_key_examples=examples,
    )


def check_referential_integrity(
    child_df: pd.DataFrame,
    parent_df: pd.DataFrame,
    join_columns: tuple[str, ...],
    child_table: str,
    parent_table: str,
) -> ReferentialCheckResult:
    join_cols = list(join_columns)
    parent_keys = set(map(tuple, parent_df[join_cols].itertuples(index=False, name=None)))
    child_keys = child_df[join_cols].itertuples(index=False, name=None)
    matched = sum(1 for k in child_keys if k in parent_keys)
    total = len(child_df)
    orphans = total - matched
    return ReferentialCheckResult(
        child_table=child_table,
        parent_table=parent_table,
        join_columns=join_columns,
        child_rows=total,
        matched_rows=matched,
        orphan_rows=orphans,
        match_rate=round(matched / total, 4) if total else 0.0,
    )


def orphan_mask(child_df: pd.DataFrame, parent_df: pd.DataFrame, join_columns: tuple[str, ...]) -> pd.Series:
    """Boolean mask over child_df rows whose join key has no match in parent_df."""
    join_cols = list(join_columns)
    parent_keys = set(map(tuple, parent_df[join_cols].itertuples(index=False, name=None)))
    return ~child_df[join_cols].apply(tuple, axis=1).isin(parent_keys)


def validate_raw_tables(
    simplanif: pd.DataFrame, simplanifpoi: pd.DataFrame, simplanifstock: pd.DataFrame
) -> ValidationReport:
    """Run the confirmed-schema checks from docs/context/Data Model.md.

    - plan_t_simplanif: PK Id_Sim
    - plan_t_simplanifpoi: PK Id_SimPoi, UNIQUE (Id_Sim, POI_Sim)
    - plan_t_simplanifstock: PK Id_stock, UNIQUE (Id_Sim, Code_Sim, Taille_Sim, Date_Sim, Client)
    - Referential: simplanifpoi.Id_Sim -> simplanif.Id_Sim (NOT DEMONSTRATED in the
      supplied extract, see docs/analysis/TASK1); simplanifstock.Id_Sim -> simplanif.Id_Sim
      (~91% match in the supplied extract).
    """
    report = ValidationReport()

    report.key_checks.append(check_key_uniqueness(simplanif, ("Id_Sim",), "plan_t_simplanif"))
    report.key_checks.append(check_key_uniqueness(simplanifpoi, ("Id_SimPoi",), "plan_t_simplanifpoi"))
    report.key_checks.append(
        check_key_uniqueness(simplanifpoi, ("Id_Sim", "POI_Sim"), "plan_t_simplanifpoi")
    )
    report.key_checks.append(check_key_uniqueness(simplanifstock, ("Id_stock",), "plan_t_simplanifstock"))
    report.key_checks.append(
        check_key_uniqueness(
            simplanifstock,
            ("Id_Sim", "Code_Sim", "Taille_Sim", "Date_Sim", "Client"),
            "plan_t_simplanifstock",
        )
    )

    report.referential_checks.append(
        check_referential_integrity(
            simplanifpoi, simplanif, ("Id_Sim",), "plan_t_simplanifpoi", "plan_t_simplanif"
        )
    )
    report.referential_checks.append(
        check_referential_integrity(
            simplanifstock, simplanif, ("Id_Sim",), "plan_t_simplanifstock", "plan_t_simplanif"
        )
    )

    return report
