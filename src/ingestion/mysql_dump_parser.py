"""Read-only parser for the `MySQL Data Transfer` (mysqldump-style) SQL export
files found under ``data/raw/sql/``.

Evidence: the three raw files were inspected directly (see
``docs/analysis/PHASE0_Initial_Project_Assessment.md`` and
``docs/analysis/TASK1_Raw_SQL_Deep_Analysis.md``). Each row is emitted as a
single, self-contained line of the exact form::

    INSERT INTO `table_name` VALUES ('v1', 'v2', null, ...);

This was verified for all three files in this session: the count of lines
matching ``^INSERT INTO`` equals the documented row count for every table
(431 / 12302 / 116200), and no such line is missing a trailing ``);``.
This module relies on that observed format; it does not attempt to be a
general MySQL dump parser and does not support multi-row ``VALUES`` lists.

This module never opens the raw files for writing. Raw data is immutable
(see MASTER_PROMPT.md section 2.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

_CREATE_TABLE_RE = re.compile(r"CREATE TABLE `(?P<table>[^`]+)` \(")
_COLUMN_LINE_RE = re.compile(r"^\s*`(?P<name>[^`]+)`\s+(?P<type>[a-zA-Z]+)")
_INSERT_PREFIX_RE = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` VALUES \(")

# Lines inside a CREATE TABLE block that are constraints, not columns.
_NON_COLUMN_PREFIXES = ("PRIMARY KEY", "UNIQUE KEY", "KEY ", "CONSTRAINT", "INDEX")


@dataclass(frozen=True)
class TableSchema:
    table_name: str
    columns: tuple[str, ...]


def parse_create_table(sql_path: str | Path) -> TableSchema:
    """Extract the ordered column list from the ``CREATE TABLE`` statement.

    Reads only the header of the dump (stops once the closing of the
    CREATE TABLE block is reached), so this is cheap even for the
    multi-megabyte dumps.
    """
    sql_path = Path(sql_path)
    table_name: str | None = None
    columns: list[str] = []
    in_table = False

    with sql_path.open("r", encoding="latin-1") as fh:
        for line in fh:
            if not in_table:
                m = _CREATE_TABLE_RE.search(line)
                if m:
                    table_name = m.group("table")
                    in_table = True
                continue

            stripped = line.strip()
            if stripped.startswith(")"):
                break
            if any(stripped.startswith(p) for p in _NON_COLUMN_PREFIXES):
                continue
            m = _COLUMN_LINE_RE.match(line)
            if m:
                columns.append(m.group("name"))

    if table_name is None:
        raise ValueError(f"No CREATE TABLE statement found in {sql_path}")
    return TableSchema(table_name=table_name, columns=tuple(columns))


def _parse_value_tuple(body: str) -> list[str | None]:
    """Parse the comma-separated value list found between the outer
    parentheses of a single ``INSERT ... VALUES (...)`` row.

    Handles single-quoted strings with backslash-escaped characters
    (the encoding used throughout these dumps) and the bare literal
    ``null`` (case-insensitive) for SQL NULL.
    """
    values: list[str | None] = []
    i, n = 0, len(body)
    while i < n:
        while i < n and body[i] in " \t,":
            i += 1
        if i >= n:
            break
        if body[i] == "'":
            i += 1
            buf: list[str] = []
            while i < n:
                c = body[i]
                if c == "\\" and i + 1 < n:
                    nc = body[i + 1]
                    buf.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0"}.get(nc, nc))
                    i += 2
                    continue
                if c == "'":
                    i += 1
                    break
                buf.append(c)
                i += 1
            values.append("".join(buf))
        else:
            j = i
            while j < n and body[j] not in ",)":
                j += 1
            token = body[i:j].strip()
            i = j
            values.append(None if token.lower() == "null" else token)
    return values


def iter_rows(sql_path: str | Path, expected_table: str | None = None) -> Iterator[list[str | None]]:
    """Stream raw value tuples from an ``INSERT INTO`` dump, one row at a time.

    Yields lists of raw string values (``None`` for SQL NULL) in column
    order as declared by the dump's own ``CREATE TABLE`` statement. Type
    conversion is intentionally NOT performed here — that is the job of
    the cleaning stage, which must make conversion failures explicit
    rather than silently coercing (see docs/context/Edge Cases & Data
    Quality Handling.md, item 4).
    """
    sql_path = Path(sql_path)
    with sql_path.open("r", encoding="latin-1") as fh:
        for line_no, line in enumerate(fh, start=1):
            m = _INSERT_PREFIX_RE.match(line)
            if not m:
                continue
            if expected_table is not None and m.group("table") != expected_table:
                raise ValueError(
                    f"{sql_path}:{line_no}: expected table `{expected_table}`, "
                    f"found `{m.group('table')}`"
                )
            rest = line[m.end():]
            close_idx = rest.rfind(");")
            if close_idx == -1:
                raise ValueError(f"{sql_path}:{line_no}: malformed INSERT line (no trailing ');')")
            body = rest[:close_idx]
            yield _parse_value_tuple(body)


def load_table(sql_path: str | Path) -> tuple[TableSchema, list[list[str | None]]]:
    """Load an entire dump into memory as (schema, rows). Convenience wrapper
    for the small/medium files (plan_t_simplanif, plan_t_simplanifpoi).
    For plan_t_simplanifstock prefer streaming via :func:`iter_rows`.
    """
    schema = parse_create_table(sql_path)
    rows = list(iter_rows(sql_path, expected_table=schema.table_name))
    return schema, rows
