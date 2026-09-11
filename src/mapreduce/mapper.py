#!/usr/bin/env python
"""Hadoop Streaming mapper for the theoretical-week MapReduce job (Phase 2).

Contract (see docs/execution/12_hadoop_mapreduce_plan.md and
docs/decisions/0004-hadoop-environment-and-benchmark-design.md):

    stdin:  Id_Sim \t POI_Sim \t component_name \t availability_date \t DATA_ORIGIN
            (one line per component event -- the long-form representation
            produced by src/ingestion/synthetic_benchmark_generator.py;
            this shape is a SYNTHETIC COMPUTATIONAL BENCHMARK
            REPRESENTATION, not a confirmed company schema)

    stdout: Id_Sim \t POI_Sim \t component_name \t availability_date \t DATA_ORIGIN
            (unchanged -- the mapper's only job is to make the intended key
            explicit for the shuffle: the first two tab-separated fields,
            (Id_Sim, POI_Sim). Real Hadoop Streaming is told to treat those
            two fields as the key via
            `-D stream.num.map.output.key.fields=2`, so a plain external
            `sort` on the whole line groups by (Id_Sim, POI_Sim) correctly.)

Deliberately self-contained (stdlib only): this script is meant to be
shipped to and executed by Hadoop task processes (potentially a different
Python interpreter/working directory than this repo), so it does not
import anything from `src/business` -- there is no calculation to perform
in the map step of this job (see the "Important Warning" in
docs/execution/12_hadoop_mapreduce_plan.md: don't distribute a trivial
MAX(); all of the actual calculation happens once, per key, in the
reducer).

Run standalone for testing:
    type events.tsv | python src/mapreduce/mapper.py
"""

from __future__ import annotations

import sys


def main() -> None:
    malformed = 0
    emitted = 0
    for raw_line in sys.stdin:
        line = raw_line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 5:
            malformed += 1
            sys.stderr.write(f"MAPPER_SKIP_MALFORMED_LINE\t{line}\n")
            continue
        sys.stdout.write(line + "\n")
        emitted += 1
    sys.stderr.write(f"MAPPER_SUMMARY\temitted={emitted}\tmalformed_skipped={malformed}\n")


if __name__ == "__main__":
    main()
