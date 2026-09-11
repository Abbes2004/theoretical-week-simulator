"""Integration tests: raw -> canonical -> simulator.

docs/execution/13_testing_strategy.md, "Integration": raw -> canonical
transformation, canonical -> simulator, output schema.

These tests use the SQL dump parser and canonical builder against small,
in-memory fixtures written in the same textual format as the real dumps
(rather than depending on the multi-megabyte files under data/raw/, which
are covered separately by the real-data smoke test at the bottom of this
file).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.business.canonical import CANONICAL_COLUMNS, build_canonical_dataset  # noqa: E402
from src.business.enums import CalculationStatus, DataOrigin  # noqa: E402
from src.ingestion.mysql_dump_parser import load_table  # noqa: E402
from configs import settings  # noqa: E402

_FIXTURE_SQL = """\
CREATE TABLE `plan_t_simplanifpoi_fixture` (
  `Id_SimPoi` int(11) NOT NULL,
  `Id_Sim` int(11) DEFAULT NULL,
  `POI_Sim` varchar(100) DEFAULT NULL,
  `DateTissu` date DEFAULT NULL,
  `DateTissuSec` date DEFAULT NULL,
  `DateFourniture` date DEFAULT NULL,
  `DateFil` date DEFAULT NULL,
  `DateOKProduction` date DEFAULT NULL,
  `DateMax` date DEFAULT NULL,
  `SemTheorique` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`Id_SimPoi`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

INSERT INTO `plan_t_simplanifpoi_fixture` VALUES ('1', '100', 'POI-A', '2025-08-04', '2025-08-05', '2025-08-03', '2025-08-04', '2025-08-08', '2025-08-08', '202532');
INSERT INTO `plan_t_simplanifpoi_fixture` VALUES ('2', '100', 'POI-B', '2025-08-04', null, '2025-08-03', '2025-08-04', null, null, null);
INSERT INTO `plan_t_simplanifpoi_fixture` VALUES ('3', '100', 'POI-C', 'ABC', '2025-08-05', '2025-08-03', '2025-08-04', '2025-08-08', null, null);
"""


@pytest.fixture()
def fixture_sql_path(tmp_path: Path) -> Path:
    path = tmp_path / "plan_t_simplanifpoi_fixture.sql"
    path.write_text(_FIXTURE_SQL, encoding="utf-8")
    return path


def test_raw_sql_to_canonical_end_to_end(fixture_sql_path: Path):
    schema, rows = load_table(fixture_sql_path)
    poi_df = pd.DataFrame(rows, columns=list(schema.columns))

    canonical = build_canonical_dataset(poi_df, data_origin=DataOrigin.SYNTHETIC)

    assert list(canonical.columns) == list(CANONICAL_COLUMNS)
    assert len(canonical) == 3

    poi_a = canonical[canonical["poi_sim"] == "POI-A"].iloc[0]
    assert poi_a["calculation_status"] == CalculationStatus.CALCULATED.value
    assert str(poi_a["date_theorique"]) == "2025-08-08"
    assert poi_a["blocking_element"] == ["OK_PRODUCTION"]
    assert poi_a["data_origin"] == DataOrigin.SYNTHETIC.value

    poi_b = canonical[canonical["poi_sim"] == "POI-B"].iloc[0]
    assert poi_b["calculation_status"] == CalculationStatus.INCOMPLETE_DATA.value
    assert poi_b["date_theorique"] is None

    poi_c = canonical[canonical["poi_sim"] == "POI-C"].iloc[0]
    assert poi_c["calculation_status"] == CalculationStatus.INVALID_DATA.value
    assert "TISSU" in poi_c["invalid_components"]


def test_canonical_dataset_grain_is_one_row_per_poi(fixture_sql_path: Path):
    """docs/execution/08: target grain is one row per (Id_Sim, POI_Sim)."""
    schema, rows = load_table(fixture_sql_path)
    poi_df = pd.DataFrame(rows, columns=list(schema.columns))
    canonical = build_canonical_dataset(poi_df, data_origin=DataOrigin.SYNTHETIC)
    key = canonical[["id_sim", "poi_sim"]]
    assert len(key) == len(key.drop_duplicates())


# ---------------------------------------------------------------------------
# Real-data smoke test: skipped automatically if the raw files are absent
# (e.g. a checkout that intentionally excludes data/raw/ per its size).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not settings.RAW_SQL_FILES["plan_t_simplanifpoi"].exists(),
    reason="real raw data/raw/sql/plan_t_simplanifpoi.sql not present in this checkout",
)
def test_real_poi_extract_smoke():
    from src.ingestion.sql_ingestion import load_sql_table_as_dataframe

    poi_df = load_sql_table_as_dataframe(settings.RAW_SQL_FILES["plan_t_simplanifpoi"])
    # Confirmed by docs/analysis/PHASE0_Initial_Project_Assessment.md.
    assert len(poi_df) == 12302
    assert len(poi_df.columns) == 80
    assert poi_df["Id_Sim"].nunique() == 1
    assert poi_df["Id_Sim"].iloc[0] == "5601"

    canonical = build_canonical_dataset(poi_df.head(200), data_origin=DataOrigin.REAL)
    assert len(canonical) == 200
    # Every real row is missing at least one required component in this
    # extract (documented limitation: see docs/execution/08 "Current
    # Limitation"), so none should ever be misreported as CALCULATED.
    assert (canonical["calculation_status"] != CalculationStatus.CALCULATED.value).all()
