"""Central configuration: paths and business-rule constants.

No business rule value in this file is invented. Constants that encode an
assumption not yet confirmed by the company are marked as such and are kept
overridable so the pipeline never hardcodes an unvalidated rule deep inside
the code.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_RAW_SQL = DATA_RAW / "sql"
DATA_RAW_EXCEL = DATA_RAW / "excel"
DATA_RAW_PDF = DATA_RAW / "pdf"

DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_CANONICAL = PROJECT_ROOT / "data" / "canonical"

# Synthetic demonstration dataset (pre-Phase-2). Deliberately a SEPARATE tree
# from data/{interim,processed,canonical}: it must never be able to collide
# with or silently overwrite a real derived artifact (MASTER_PROMPT.md
# section 2.3). See docs/decisions/0003-synthetic-demo-dataset.md.
DATA_SYNTHETIC = PROJECT_ROOT / "data" / "synthetic"
DEMO_DATASET_DIR = DATA_SYNTHETIC / "demo_2025_2026"
DEMO_INPUT_DIR = DEMO_DATASET_DIR / "input"
DEMO_CANONICAL_DIR = DEMO_DATASET_DIR / "canonical"
DEMO_METADATA_DIR = DEMO_DATASET_DIR / "metadata"

DEMO_INPUT_PARQUET = DEMO_INPUT_DIR / "poi_demo_synthetic_completed.parquet"
DEMO_INPUT_CSV = DEMO_INPUT_DIR / "poi_demo_synthetic_completed.csv"
DEMO_CANONICAL_PARQUET = DEMO_CANONICAL_DIR / "poi_demo_synthetic_canonical.parquet"
DEMO_CANONICAL_CSV = DEMO_CANONICAL_DIR / "poi_demo_synthetic_canonical.csv"
DEMO_METADATA_JSON = DEMO_METADATA_DIR / "generation_metadata.json"
DEMO_METADATA_README = DEMO_METADATA_DIR / "README.md"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
OUTPUTS_LOGS = OUTPUTS_DIR / "logs"
OUTPUTS_BENCHMARKS = OUTPUTS_DIR / "benchmarks"
OUTPUTS_RESULTS = OUTPUTS_DIR / "results"

BENCHMARK_DATASETS_DIR = PROJECT_ROOT / "benchmarks" / "datasets"

RAW_SQL_FILES = {
    "plan_t_simplanif": DATA_RAW_SQL / "plan_t_simplanif.sql",
    "plan_t_simplanifpoi": DATA_RAW_SQL / "plan_t_simplanifpoi.sql",
    "plan_t_simplanifstock": DATA_RAW_SQL / "plan_t_simplanifstock.sql",
}

RAW_EXCEL_FILES = {
    "table": DATA_RAW_EXCEL / "table.xlsx",
    "consommation_tissu": DATA_RAW_EXCEL / "consommation tissu par type.xlsx",
    "cde": DATA_RAW_EXCEL / "cde.xls",
}

RAW_PDF_FILES = sorted(DATA_RAW_PDF.glob("*.pdf"))

# ---------------------------------------------------------------------------
# Business rule constants
# ---------------------------------------------------------------------------

# The five components explicitly identified in the cahier des charges and in
# docs/context/Business Rules.md. Order here is only for stable output
# formatting and carries no priority/tie-break meaning.
COMPONENTS: tuple[str, ...] = ("TISSU", "TISSU_SEC", "FOURNITURE", "FIL", "OK_PRODUCTION")

# Mapping from canonical component name to the source POI column holding its
# candidate availability date. CONFIRMED as the observed field names; the
# exact calculation *behind* each date is NOT confirmed (see
# docs/context/Business Rules.md section 6 and section 15).
COMPONENT_DATE_COLUMNS: dict[str, str] = {
    "TISSU": "DateTissu",
    "TISSU_SEC": "DateTissuSec",
    "FOURNITURE": "DateFourniture",
    "FIL": "DateFil",
    "OK_PRODUCTION": "DateOKProduction",
}

# RECOMMENDATION (not a confirmed company rule): in the absence of a
# validated "is this component required for this POI" rule (open question,
# see docs/context/Open Questions & Business Validation.md Q6-Q7), Phase 1
# treats every one of the five components as REQUIRED_BUT_UNAVAILABLE when
# its date is NULL, rather than NOT_REQUIRED. This is the conservative
# choice: it never silently drops a component from the calculation, and it
# is surfaced as an explicit, overridable policy (see
# src/business/applicability.py) rather than being hardcoded into the MAX()
# calculation itself.
DEFAULT_APPLICABILITY_POLICY = "ALL_REQUIRED"

# ISO week convention. Evidence: docs/analysis/TASK2_Supporting_Sources_Business_Mapping.md
# confirms (13/13 exact matches, computed in this session) that
# plan_t_simplaniffourniture.EtatAccessoire stores the ISO-8601 (year, week)
# of DateAccesoire, e.g. DateAccesoire=2025-07-30 -> EtatAccessoire='202531'
# (ISO week 31 of 2025). This is CONFIRMED for that field only.
# It has NOT been confirmed for SemTheorique itself, because SemTheorique is
# 100% NULL in every POI extract available to this project (see
# docs/execution/08_canonical_dataset_specification.md, "Current Limitation").
# Using ISO-8601 for SemTheorique is therefore a RECOMMENDATION, not a
# confirmed fact, and is documented as such wherever SemTheorique is produced.
WEEK_CONVENTION = "ISO_8601"

# Study period filter: UNKNOWN. No document in docs/context or docs/execution
# provides a confirmed START_DATE/END_DATE. Left as None so the pipeline
# never invents a scope filter (see docs/context/Open Questions & Business
# Validation.md Q23). Set both to enable client-side filtering.
STUDY_PERIOD_START: str | None = None
STUDY_PERIOD_END: str | None = None

# A date is flagged SUSPICIOUS (not rejected) outside this range. This is a
# RECOMMENDATION for surfacing likely data-entry errors, not a confirmed
# business rule about production scheduling.
PLAUSIBLE_DATE_MIN = "2000-01-01"
PLAUSIBLE_DATE_MAX = "2035-12-31"

RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Synthetic demonstration dataset (see src/ingestion/synthetic_demo_dataset.py
# and docs/decisions/0003-synthetic-demo-dataset.md)
# ---------------------------------------------------------------------------

# A sentinel Id_Sim value that cannot collide with any Id_Sim observed in the
# real data (plan_t_simplanif: 10775-12039; plan_t_simplanifpoi: 5601 only;
# plan_t_simplanifstock: 3322-10876, all re-verified in this session).
DEMO_ID_SIM = 999999

# Inclusive generation window mandated for the demo dataset.
DEMO_RANGE_START = "2025-01-01"
DEMO_RANGE_END = "2026-06-30"

DEMO_SEED = RANDOM_SEED  # fixed and reproducible; recorded again in metadata/generation_metadata.json
DEMO_BULK_ROWS = 500

# ---------------------------------------------------------------------------
# Phase 2 — large-scale synthetic benchmark dataset (see
# src/ingestion/synthetic_benchmark_generator.py and
# docs/decisions/0004-hadoop-environment-and-benchmark-design.md)
# ---------------------------------------------------------------------------

BENCHMARK_SCALE_DIR = DATA_SYNTHETIC / "benchmark_scale_2025_2026"
BENCHMARK_SCALE_INPUT_DIR = BENCHMARK_SCALE_DIR / "input"
BENCHMARK_SCALE_EVENTS_DIR = BENCHMARK_SCALE_DIR / "component_events"
BENCHMARK_SCALE_REFERENCE_DIR = BENCHMARK_SCALE_DIR / "canonical_reference"
BENCHMARK_SCALE_METADATA_DIR = BENCHMARK_SCALE_DIR / "metadata"
BENCHMARK_SCALE_HADOOP_INPUT_DIR = BENCHMARK_SCALE_DIR / "hadoop_input"

# A sentinel Id_Sim distinct from both the real data ranges (see DEMO_ID_SIM
# above) and from the demo dataset's own sentinel (999999), so the three
# datasets can never collide on (Id_Sim, POI_Sim) even if ever concatenated.
BENCHMARK_ID_SIM = 999998

BENCHMARK_RANGE_START = DEMO_RANGE_START  # same mandated window: 2025-01-01
BENCHMARK_RANGE_END = DEMO_RANGE_END      # .. through 2026-06-30
BENCHMARK_SEED = RANDOM_SEED

# Required supported scales (run by default when requested individually).
BENCHMARK_SCALES: tuple[int, ...] = (100_000, 500_000, 1_000_000)
# Optional, explicit-opt-in-only scale (never run unless the CLI caller
# passes --scale 5000000 --confirm-large).
BENCHMARK_SCALE_XL = 5_000_000

# Chunk size used while generating/writing partitioned Parquet, chosen to
# keep peak memory bounded regardless of total scale (this development
# machine has ~8GB RAM total; see docs/decisions/0004).
BENCHMARK_CHUNK_SIZE = 100_000

BENCHMARK_SCHEMA_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Hadoop MapReduce run artifacts (Phase 2). Deliberately kept OUTSIDE
# data/synthetic/demo_2025_2026/ and data/synthetic/benchmark_scale_2025_2026/
# {input,component_events,canonical_reference,metadata}/ so preparing or
# running a Hadoop/local-emulation job can never overwrite a protected
# dataset tree -- see docs/decisions/0004-hadoop-environment-and-benchmark-design.md.
# ---------------------------------------------------------------------------

MAPREDUCE_OUTPUT_DIR = OUTPUTS_DIR / "mapreduce"
MAPREDUCE_DEMO_DIR = MAPREDUCE_OUTPUT_DIR / "demo"
MAPREDUCE_BENCHMARK_DIR = MAPREDUCE_OUTPUT_DIR / "benchmark"

# ---------------------------------------------------------------------------
# Real Hadoop cluster (3-VM VirtualBox cluster: master/worker1/worker2), see
# docs/decisions/0005-real-hadoop-cluster-execution.md. Connection relies on
# the `tws-master` SSH alias configured in ~/.ssh/config (passwordless key
# auth). All remote paths are project-scoped so this never touches anything
# else on the cluster's filesystem or HDFS.
# ---------------------------------------------------------------------------

HADOOP_CLUSTER_SSH_HOST = "tws-master"
HADOOP_CLUSTER_REMOTE_HOME = "/home/abbes"
HADOOP_CLUSTER_HADOOP_HOME = "/home/abbes/hadoop-3.4.2"
HADOOP_CLUSTER_STREAMING_JAR = f"{HADOOP_CLUSTER_HADOOP_HOME}/share/hadoop/tools/lib/hadoop-streaming-3.4.2.jar"
HADOOP_CLUSTER_REMOTE_STAGING = "/home/abbes/tws_phase2"  # project-scoped local-fs staging dir on master
HADOOP_CLUSTER_HDFS_PROJECT_PATH = "/tws_phase2"           # project-scoped HDFS path, never touches anything else
