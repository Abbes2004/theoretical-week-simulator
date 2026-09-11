#!/usr/bin/env python
"""Hadoop Streaming reducer for the theoretical-week MapReduce job (Phase 2).

Contract (see docs/execution/12_hadoop_mapreduce_plan.md and
docs/decisions/0004-hadoop-environment-and-benchmark-design.md):

    stdin (sorted/grouped by (Id_Sim, POI_Sim), either by real Hadoop's
    shuffle with `-D stream.num.map.output.key.fields=2`, or by piping
    through plain `sort` in local-emulation mode -- see
    scripts/run_hadoop_job.py):
        Id_Sim \t POI_Sim \t component_name \t availability_date \t DATA_ORIGIN

    stdout (one line per POI):
        Id_Sim \t POI_Sim \t date_theorique \t iso_year \t iso_week \t
        week_key \t sem_theorique \t blocking_element(;-joined) \t
        calculation_status

For each key, the reducer gathers up to five component events, validates
completeness (a component absent from its group is treated exactly like a
NULL date -- the same rule the local engine uses), computes the maximum
applicable date, derives the ISO year/week/week_key, and returns every
tied blocking component.

DELIBERATELY SELF-CONTAINED (stdlib only, no import of `src.business`):
this script is shipped to and executed ON THE REAL HADOOP CLUSTER'S NODES
(3-VM cluster, see docs/decisions/0005-real-hadoop-cluster-execution.md),
which do not have this project's workspace or `configs`/`src` packages
installed -- only Python 3 + the standard library. `_calculate` below is a
direct, deliberately minimal port of the same ALL_REQUIRED-policy logic in
`src/business/rules.calculate_theoretical_week` (the policy every mapper/
reducer invocation already used, since neither script ever passes
`applicability_overrides`). It is NOT re-derived business logic -- it is
the same five-line rule (missing/invalid required component blocks the
result; otherwise MAX of the five dates, ISO week of that date, every
component tied at the max is a blocker) transcribed without the
pandas/dataclass machinery that only the local engine needs.

Because this is a manual transcription, not a shared import, it is backed
by an automated correctness gate rather than trusted by inspection alone:
tests/validation/test_hadoop_local_equivalence.py and
scripts/compare_hadoop_local.py run this exact reducer.py (via subprocess,
exactly as Hadoop Streaming invokes it) and diff its output field-by-field
against `src.business.canonical.build_canonical_dataset` /
`vectorized_canonical.build_canonical_dataset_vectorized` on the same
input. Both the 513-row demo dataset and the 100k/1M-row benchmark scales
pass with 0 mismatches (see docs/decisions/0005 for the exact results) --
that is what guarantees these two implementations still agree, not the
fact that they look similar.

Run standalone for testing:
    type events.tsv | python src/mapreduce/mapper.py | sort | python src/mapreduce/reducer.py
"""

from __future__ import annotations

import sys
from datetime import date

COMPONENTS = ("TISSU", "TISSU_SEC", "FOURNITURE", "FIL", "OK_PRODUCTION")


def _parse_date(raw: str | None) -> tuple[date | None, bool]:
    """Returns (parsed_date_or_None, is_valid). Mirrors
    src/business/date_parsing.parse_date for the one format this pipeline's
    generators ever emit ('YYYY-MM-DD'); missing/empty is valid-but-None,
    anything else that doesn't parse as that exact format is invalid."""
    if not raw:
        return None, True
    try:
        year_s, month_s, day_s = raw.split("-")
        if len(year_s) != 4 or len(month_s) != 2 or len(day_s) != 2:
            return None, False
        return date(int(year_s), int(month_s), int(day_s)), True
    except (ValueError, TypeError):
        return None, False


def _calculate(component_dates: dict[str, str | None]) -> tuple[str, str, str, str, str, str]:
    """Returns (date_theorique, iso_year, iso_week, week_key, sem_theorique,
    blocking_element_joined, status) as strings ('' where not applicable)."""
    parsed: dict[str, date | None] = {}
    invalid: list[str] = []
    missing: list[str] = []

    for component in COMPONENTS:
        raw = component_dates.get(component)
        value, is_valid = _parse_date(raw)
        parsed[component] = value
        if not is_valid:
            invalid.append(component)
        elif value is None:
            missing.append(component)

    if invalid:
        status = "INVALID_DATA"
    elif missing:
        status = "INCOMPLETE_DATA"
    else:
        status = "CALCULATED"

    if status != "CALCULATED":
        return "", "", "", "", "", "", status

    date_theorique = max(parsed[c] for c in COMPONENTS)
    blocking = [c for c in COMPONENTS if parsed[c] == date_theorique]
    iso_year, iso_week, _weekday = date_theorique.isocalendar()
    week_key = f"{iso_year}{iso_week:02d}"
    return date_theorique.isoformat(), str(iso_year), str(iso_week), week_key, week_key, ";".join(blocking), status


def _emit(id_sim: str, poi_sim: str, component_dates: dict[str, str | None]) -> None:
    date_theorique, iso_year, iso_week, week_key, sem_theorique, blocking, status = _calculate(component_dates)
    sys.stdout.write(
        "\t".join([id_sim, poi_sim, date_theorique, iso_year, iso_week, week_key, sem_theorique, blocking, status])
        + "\n"
    )


def main() -> None:
    current_key: tuple[str, str] | None = None
    component_dates: dict[str, str | None] = {}
    malformed = 0
    unknown_component = 0
    n_keys = 0

    for raw_line in sys.stdin:
        line = raw_line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 5:
            malformed += 1
            sys.stderr.write(f"REDUCER_SKIP_MALFORMED_LINE\t{line}\n")
            continue
        id_sim, poi_sim, component_name, availability_date, _data_origin = parts
        key = (id_sim, poi_sim)

        if key != current_key:
            if current_key is not None:
                _emit(current_key[0], current_key[1], component_dates)
                n_keys += 1
            current_key = key
            component_dates = {c: None for c in COMPONENTS}

        if component_name in component_dates:
            component_dates[component_name] = availability_date or None
        else:
            unknown_component += 1
            sys.stderr.write(f"REDUCER_UNKNOWN_COMPONENT\t{component_name}\n")

    if current_key is not None:
        _emit(current_key[0], current_key[1], component_dates)
        n_keys += 1

    sys.stderr.write(
        f"REDUCER_SUMMARY\tkeys={n_keys}\tmalformed_skipped={malformed}\tunknown_component={unknown_component}\n"
    )


if __name__ == "__main__":
    main()
