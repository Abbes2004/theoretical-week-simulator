"""Unit tests for src/ingestion/mysql_dump_parser.py.

Format assumptions encoded here (single INSERT per row, backslash-escaped
quotes, lowercase `null`) were verified directly against all three raw dump
files in this session (see module docstring in mysql_dump_parser.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from ingestion.mysql_dump_parser import iter_rows, parse_create_table  # noqa: E402

_SAMPLE = """\
CREATE TABLE `sample_table` (
  `Id` int(11) NOT NULL,
  `Name` varchar(50) DEFAULT NULL,
  `Notes` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`Id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

INSERT INTO `sample_table` VALUES ('1', 'Alice', 'no comma here');
INSERT INTO `sample_table` VALUES ('2', 'Bob, Jr.', 'has an escaped quote: \\'quoted\\'');
INSERT INTO `sample_table` VALUES ('3', null, null);
"""


def test_parse_create_table_extracts_columns_in_order(tmp_path: Path):
    path = tmp_path / "sample.sql"
    path.write_text(_SAMPLE, encoding="utf-8")
    schema = parse_create_table(path)
    assert schema.table_name == "sample_table"
    assert schema.columns == ("Id", "Name", "Notes")


def test_iter_rows_handles_embedded_commas_and_escaped_quotes(tmp_path: Path):
    path = tmp_path / "sample.sql"
    path.write_text(_SAMPLE, encoding="utf-8")
    rows = list(iter_rows(path, expected_table="sample_table"))
    assert rows == [
        ["1", "Alice", "no comma here"],
        ["2", "Bob, Jr.", "has an escaped quote: 'quoted'"],
        ["3", None, None],
    ]
