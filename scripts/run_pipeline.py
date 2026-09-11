"""Reproducible end-to-end Phase 1 pipeline: raw SQL -> canonical dataset.

Usage (from the project root):

    python scripts/run_pipeline.py

Produces:
    data/interim/*.raw.parquet          (ingested raw tables, verbatim)
    outputs/results/validation_report.json
    data/canonical/poi_canonical.parquet
    data/canonical/poi_canonical.csv
    outputs/results/historical_validation_summary.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs import settings
from src.business.canonical import build_canonical_dataset
from src.business.enums import DataOrigin
from src.ingestion.excel_ingestion import ingest_all_excel
from src.ingestion.pdf_ingestion import ingest_all_pdfs
from src.ingestion.sql_ingestion import ingest_all_sql_tables
from src.preprocessing.validation import validate_raw_tables
from src.simulation.simulator import validate_against_historical


def main() -> None:
    settings.DATA_CANONICAL.mkdir(parents=True, exist_ok=True)
    settings.OUTPUTS_RESULTS.mkdir(parents=True, exist_ok=True)

    print("[0/4] Ingesting supporting Excel/PDF sources (documentation lineage; "
          "not used by the calculation -- see docs/decisions/0001)...")
    excel = ingest_all_excel(write_interim=True)
    for key, sheets in excel.items():
        for sheet_name, df in sheets.items():
            print(f"    excel:{key}/{sheet_name}: {len(df):,} rows x {len(df.columns)} cols")
    pdfs = ingest_all_pdfs(write_interim=True)
    for name, text in pdfs.items():
        print(f"    pdf:{name}: {len(text):,} characters -> data/interim/pdf_text/")

    print("[1/4] Ingesting raw SQL dumps (immutable, read-only)...")
    t0 = time.time()
    tables = ingest_all_sql_tables(write_interim=True)
    simplanif = tables["plan_t_simplanif"]
    simplanifpoi = tables["plan_t_simplanifpoi"]
    simplanifstock = tables["plan_t_simplanifstock"]
    print(
        f"    plan_t_simplanif={len(simplanif):,} rows, "
        f"plan_t_simplanifpoi={len(simplanifpoi):,} rows, "
        f"plan_t_simplanifstock={len(simplanifstock):,} rows "
        f"({time.time() - t0:.2f}s)"
    )

    print("[2/4] Validating schema, keys, and referential integrity...")
    report = validate_raw_tables(simplanif, simplanifpoi, simplanifstock)
    report_path = settings.OUTPUTS_RESULTS / "validation_report.json"
    report_path.write_text(json.dumps(report.to_dict(), indent=2, default=str), encoding="utf-8")
    for kc in report.key_checks:
        status = "OK" if kc.is_unique else f"DUPLICATES={kc.duplicate_rows}"
        print(f"    key {kc.table}{kc.key_columns}: {kc.total_rows:,} rows -> {status}")
    for rc in report.referential_checks:
        print(
            f"    ref {rc.child_table}.{rc.join_columns} -> {rc.parent_table}: "
            f"{rc.matched_rows:,}/{rc.child_rows:,} matched ({rc.match_rate:.1%})"
        )
    print(f"    -> {report_path}")

    print("[3/4] Building canonical POI dataset (applying the business-rule engine)...")
    t0 = time.time()
    canonical = build_canonical_dataset(simplanifpoi, data_origin=DataOrigin.REAL)
    elapsed = time.time() - t0
    parquet_path = settings.DATA_CANONICAL / "poi_canonical.parquet"
    csv_path = settings.DATA_CANONICAL / "poi_canonical.csv"
    canonical.to_parquet(parquet_path, index=False)
    # CSV needs list-typed columns flattened to a readable string form.
    csv_ready = canonical.copy()
    for col in ("blocking_element", "missing_components", "invalid_components", "suspicious_components", "data_quality_flag"):
        csv_ready[col] = csv_ready[col].apply(lambda v: ";".join(v) if isinstance(v, list) else v)
    csv_ready.to_csv(csv_path, index=False)
    print(f"    {len(canonical):,} POIs processed in {elapsed:.2f}s -> {parquet_path}")
    print("    status distribution:")
    for status, count in canonical["calculation_status"].value_counts().items():
        print(f"      {status}: {count:,}")

    print("[4/4] Comparing against historical SemTheorique where available...")
    summary = validate_against_historical(canonical)
    summary_path = settings.OUTPUTS_RESULTS / "historical_validation_summary.json"
    summary_path.write_text(json.dumps(summary.__dict__, indent=2), encoding="utf-8")
    print(f"    comparable POIs: {summary.comparable_pois} / {summary.total_pois}")
    if summary.match_rate is None:
        print("    match rate: N/A (no POI in this extract has both a CALCULATED result "
              "and a populated, parseable historical SemTheorique)")
    else:
        print(f"    match rate: {summary.match_rate:.1%}")
    print(f"    -> {summary_path}")


if __name__ == "__main__":
    main()
