"""Run the theoretical-week MapReduce job: real Hadoop Streaming on the
3-VM VirtualBox cluster (master/worker1/worker2) when reachable over SSH,
otherwise an honestly-labelled LOCAL EMULATION of the same
mapper -> shuffle(sort) -> reducer pipeline on the Windows host.

See docs/decisions/0005-real-hadoop-cluster-execution.md for the full
cluster inspection log, the YARN/MapReduce resource-limit fix applied
(workers only have <1GB RAM/1 vCPU each -- Hadoop's 8GB/8-vcore defaults
were unsafe and have been overridden to 384MB/1 vcore), and exactly what
"real Hadoop execution" means here (still a single-digit-node, ~1GB-per-
node cluster -- not a claim of production-scale hardware).

`--mode auto` (the default) tries the real cluster first (SSH reachability
+ Hadoop/HDFS/YARN health check); if that fails for any reason, it falls
back to `local-emulation` and says so explicitly in stdout and the
returned/written result. Local-emulation mode still exercises the REAL
mapper.py/reducer.py files (as subprocesses reading/writing files, exactly
like Hadoop Streaming's contract), with an external `sort` standing in for
Hadoop's shuffle -- it is NOT a distributed run: no HDFS, no YARN, no
network shuffle, no JVM task-launch overhead.

Usage:
    python scripts/run_hadoop_job.py --input outputs/mapreduce/demo/events.tsv --label demo
    python scripts/run_hadoop_job.py --input data/synthetic/benchmark_scale_2025_2026/hadoop_input/scale_100000.tsv --label scale_100000
    python scripts/run_hadoop_job.py --input ... --mode local-emulation   # force, skip cluster probing
    python scripts/run_hadoop_job.py --input ... --mode real             # force real cluster, error if unreachable
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs import settings
from src.mapreduce import cluster as mrcluster
from src.mapreduce.environment import HadoopEnvironment, detect_hadoop_environment

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MAPPER = _PROJECT_ROOT / "src" / "mapreduce" / "mapper.py"
_REDUCER = _PROJECT_ROOT / "src" / "mapreduce" / "reducer.py"


@dataclass
class JobResult:
    label: str
    mode: str  # "real_hadoop_cluster" | "local_emulation"
    input_path: str
    output_path: str
    n_input_lines: int
    n_output_lines: int
    timings_seconds: dict  # phase -> seconds (None where not applicable)
    environment: dict
    notes: list


def _count_lines(path: Path) -> int:
    n = 0
    with path.open("rb") as fh:
        for _ in fh:
            n += 1
    return n


def run_real_hadoop_cluster(input_path: Path, work_dir: Path, label: str) -> JobResult:
    """Real Hadoop Streaming submission on the 3-VM cluster over SSH. Times
    each phase separately: staging the input file to master, uploading it
    to HDFS, the MapReduce job itself, merging the output on HDFS, and
    fetching it back to this host.
    """
    remote_staging = mrcluster.HADOOP_CLUSTER_REMOTE_STAGING
    hdfs_base = f"{mrcluster.HADOOP_CLUSTER_HDFS_PROJECT_PATH}/{label}"
    hdfs_input = f"{hdfs_base}/input"
    hdfs_output = f"{hdfs_base}/output"
    remote_input_file = f"{remote_staging}/{label}.events.tsv"
    remote_output_file = f"{remote_staging}/{label}.output.tsv"
    remote_mapper = f"{remote_staging}/mapper.py"
    remote_reducer = f"{remote_staging}/reducer.py"

    timings: dict[str, float] = {}
    notes: list[str] = ["Real Hadoop Streaming execution on the 3-VM cluster (master/worker1/worker2)."]

    mrcluster.ensure_remote_staging_dir()
    mrcluster.scp_to_master(_MAPPER, remote_mapper)
    mrcluster.scp_to_master(_REDUCER, remote_reducer)

    t0 = time.perf_counter()
    mrcluster.scp_to_master(input_path, remote_input_file, timeout=600)
    timings["stage_input_to_master"] = time.perf_counter() - t0

    mrcluster.ensure_hdfs_project_dir(label)
    t0 = time.perf_counter()
    mrcluster.ssh_run(f"hdfs dfs -put -f {remote_input_file} {hdfs_input}/", timeout=300)
    timings["hdfs_upload"] = time.perf_counter() - t0

    # This cluster's capacity-scheduler.xml (pre-existing, not created by this
    # project -- see docs/decisions/0005) defines no "default" queue; it has
    # a custom sales/engineering tree left over from an unrelated exercise.
    # "sales" is RUNNING and open to all users (acl_submit_applications=*),
    # so jobs are submitted there rather than editing the scheduler config.
    t0 = time.perf_counter()
    mrcluster.ssh_run(
        f"hadoop jar {mrcluster.HADOOP_CLUSTER_STREAMING_JAR} "
        f"-D stream.num.map.output.key.fields=2 "
        f"-D mapreduce.job.queuename=sales "
        f"-files {remote_mapper},{remote_reducer} "
        f"-input {hdfs_input} -output {hdfs_output} "
        f"-mapper 'python3 mapper.py' -reducer 'python3 reducer.py'",
        timeout=1800,
    )
    timings["mapreduce_job"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    mrcluster.ssh_run(f"hdfs dfs -getmerge {hdfs_output} {remote_output_file}", timeout=300)
    timings["hdfs_download"] = time.perf_counter() - t0

    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = work_dir / f"{label}.hadoop_output.tsv"
    t0 = time.perf_counter()
    mrcluster.scp_from_master(remote_output_file, output_path, timeout=600)
    timings["fetch_output_to_host"] = time.perf_counter() - t0

    timings["hdfs_upload_plus_job_plus_download"] = (
        timings["hdfs_upload"] + timings["mapreduce_job"] + timings["hdfs_download"]
    )

    health = mrcluster.check_cluster_health()
    environment = {
        "execution_mode": "real_multi_node_cluster",
        "hadoop_version": health.hadoop_version,
        "java_version": health.java_version,
        "hdfs_live_datanodes": health.hdfs_live_datanodes,
        "yarn_live_nodes": health.yarn_live_nodes,
        "nodes": ["master (NameNode+SecondaryNameNode+ResourceManager)",
                  "worker1 (DataNode+NodeManager)", "worker2 (DataNode+NodeManager)"],
        "per_node_hardware": "master: 1 vCPU/1.4GiB RAM; worker1/worker2: 1 vCPU/960MiB RAM each",
        "yarn_container_limits": "yarn.nodemanager.resource.memory-mb=384, cpu-vcores=1 "
        "(overridden from the unsafe Hadoop defaults of 8192MB/8 vcores -- see docs/decisions/0005)",
    }

    return JobResult(
        label=label,
        mode="real_hadoop_cluster",
        input_path=str(input_path),
        output_path=str(output_path),
        n_input_lines=_count_lines(input_path),
        n_output_lines=_count_lines(output_path),
        timings_seconds=timings,
        environment=environment,
        notes=notes,
    )


def run_local_emulation(input_path: Path, work_dir: Path, label: str, env: HadoopEnvironment) -> JobResult:
    """Same mapper.py/reducer.py, run as local subprocesses with an external
    `sort` standing in for Hadoop's shuffle. NOT a distributed run -- see
    module docstring and docs/decisions/0004 for exactly what this does and
    does not measure.
    """
    if shutil.which("sort") is None:
        raise SystemExit(
            "No `sort` command found on PATH. On Windows, use Git for Windows' bash "
            "(provides GNU coreutils `sort`) or run from a shell where the built-in "
            "`sort.exe` is available."
        )

    work_dir.mkdir(parents=True, exist_ok=True)
    mapped_path = work_dir / f"{label}.mapped.tsv"
    sorted_path = work_dir / f"{label}.sorted.tsv"
    output_path = work_dir / f"{label}.reduced.tsv"
    mapper_log = work_dir / f"{label}.mapper.log"
    reducer_log = work_dir / f"{label}.reducer.log"

    timings: dict[str, float] = {"hdfs_upload": None, "hdfs_download": None}

    t0 = time.perf_counter()
    with input_path.open("rb") as fin, mapped_path.open("wb") as fout, mapper_log.open("w") as ferr:
        subprocess.run([sys.executable, str(_MAPPER)], stdin=fin, stdout=fout, stderr=ferr, check=True)
    timings["map"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    with mapped_path.open("rb") as fin, sorted_path.open("wb") as fout:
        subprocess.run(["sort"], stdin=fin, stdout=fout, check=True)
    timings["shuffle_sort"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    with sorted_path.open("rb") as fin, output_path.open("wb") as fout, reducer_log.open("w") as ferr:
        subprocess.run([sys.executable, str(_REDUCER)], stdin=fin, stdout=fout, stderr=ferr, check=True)
    timings["reduce"] = time.perf_counter() - t0

    timings["mapreduce_job"] = timings["map"] + timings["shuffle_sort"] + timings["reduce"]

    notes = [
        "LOCAL EMULATION, not real Hadoop/HDFS: mapper.py and reducer.py were run as plain "
        "local subprocesses; an external `sort` stood in for Hadoop's distributed shuffle. "
        "No JVM task-launch overhead, no network shuffle, no HDFS I/O is represented here.",
        f"Reason real Hadoop was not used: {'; '.join(env.notes)}",
    ]

    return JobResult(
        label=label,
        mode="local_emulation",
        input_path=str(input_path),
        output_path=str(output_path),
        n_input_lines=_count_lines(input_path),
        n_output_lines=_count_lines(output_path),
        timings_seconds=timings,
        environment=asdict(env),
        notes=notes,
    )


def run_job(input_path: Path, work_dir: Path, label: str, mode: str = "auto") -> JobResult:
    if mode == "real":
        if not mrcluster.is_cluster_reachable():
            raise SystemExit(
                f"mode=real requested but the cluster ({mrcluster.HADOOP_CLUSTER_SSH_HOST}) is not "
                "reachable over SSH. Check the VMs are running and `ssh tws-master hostname` works. "
                "Use --mode local-emulation or --mode auto."
            )
        return run_real_hadoop_cluster(input_path, work_dir, label)

    env = detect_hadoop_environment()  # local-Windows-host check, used only for local-emulation notes

    if mode == "local-emulation":
        return run_local_emulation(input_path, work_dir, label, env)

    # auto: prefer the real cluster, fall back to local emulation on any failure.
    if mrcluster.is_cluster_reachable():
        try:
            return run_real_hadoop_cluster(input_path, work_dir, label)
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: any cluster failure falls back
            print(
                f"[run_hadoop_job] Real cluster run failed ({exc}) -- falling back to LOCAL EMULATION.",
                file=sys.stderr,
            )
            env.notes = env.notes + [f"Real cluster attempt failed: {exc}"]
            return run_local_emulation(input_path, work_dir, label, env)

    print(
        f"[run_hadoop_job] Cluster ({mrcluster.HADOOP_CLUSTER_SSH_HOST}) not reachable over SSH -- "
        f"falling back to LOCAL EMULATION.",
        file=sys.stderr,
    )
    return run_local_emulation(input_path, work_dir, label, env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--mode", choices=["auto", "real", "local-emulation"], default="auto")
    parser.add_argument("--work-dir", type=Path, default=settings.MAPREDUCE_OUTPUT_DIR)
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"{args.input} not found.")

    result = run_job(args.input, args.work_dir, args.label, args.mode)

    result_path = args.work_dir / f"{args.label}.job_result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(asdict(result), indent=2, default=str), encoding="utf-8")

    print(f"\nMode: {result.mode}")
    print(f"Input lines: {result.n_input_lines:,}  Output lines: {result.n_output_lines:,}")
    print(f"Timings (s): {result.timings_seconds}")
    for note in result.notes:
        print(f"NOTE: {note}")
    print(f"-> {result.output_path}")
    print(f"-> {result_path}")


if __name__ == "__main__":
    main()
