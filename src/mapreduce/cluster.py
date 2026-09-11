"""SSH/SCP helpers for the real 3-VM Hadoop cluster (master/worker1/worker2).

See docs/decisions/0005-real-hadoop-cluster-execution.md for the full
cluster inspection log (topology, versions, resource limits applied) and
docs/decisions/0004-hadoop-environment-and-benchmark-design.md for why no
Hadoop runs on the Windows host itself.

Connectivity relies on the `tws-master` alias in the Windows user's
`~/.ssh/config` (passwordless ED25519 key auth, set up interactively with
the user -- this module never handles or stores a password). All remote
operations are confined to project-scoped paths:
  - local filesystem staging on master: configs.settings.HADOOP_CLUSTER_REMOTE_STAGING
  - HDFS: configs.settings.HADOOP_CLUSTER_HDFS_PROJECT_PATH
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from configs.settings import (  # noqa: E402
    HADOOP_CLUSTER_HADOOP_HOME,
    HADOOP_CLUSTER_HDFS_PROJECT_PATH,
    HADOOP_CLUSTER_REMOTE_STAGING,
    HADOOP_CLUSTER_SSH_HOST,
    HADOOP_CLUSTER_STREAMING_JAR,
)

_HADOOP_ENV_PREFIX = (
    "export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64; "
    f"export HADOOP_HOME={HADOOP_CLUSTER_HADOOP_HOME}; "
    "export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop; "
    "export PATH=$JAVA_HOME/bin:$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin; "
)


class ClusterUnreachable(RuntimeError):
    pass


# This cluster's nodes are extremely resource-constrained (1 vCPU each,
# shared with HDFS/YARN daemons -- see docs/decisions/0005). SSH key
# exchange is CPU-bound, and rapid successive connections occasionally fail
# outright (observed in this session: an isolated `scp` succeeding when
# retried seconds later with no other change). A small bounded retry is a
# documented operational accommodation for this specific hardware, not a
# blanket "retry until it works": it gives up and raises after 3 attempts.
_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 3.0


def _run_with_retry(cmd: list[str], timeout: float, error_label: str) -> subprocess.CompletedProcess:
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if proc.returncode == 0 or attempt == _MAX_ATTEMPTS:
                return proc
            last_exc = RuntimeError(f"{error_label} exit {proc.returncode}: {proc.stderr.strip()}")
        except subprocess.TimeoutExpired as exc:
            last_exc = exc
            if attempt == _MAX_ATTEMPTS:
                raise ClusterUnreachable(f"{error_label} timed out after {_MAX_ATTEMPTS} attempts: {exc}") from exc
        except FileNotFoundError as exc:
            raise ClusterUnreachable(f"{error_label} failed: {exc}") from exc
        time.sleep(_RETRY_DELAY_SECONDS)
    raise ClusterUnreachable(f"{error_label} failed after {_MAX_ATTEMPTS} attempts: {last_exc}")


def ssh_run(remote_cmd: str, timeout: float = 60.0, check: bool = True) -> subprocess.CompletedProcess:
    """Run `remote_cmd` on the cluster's master node over SSH (with the
    Hadoop environment sourced first, since non-interactive SSH sessions do
    not source ~/.bashrc). Retries up to 3 times on connection failure
    (not on the remote command's own exit code, unless it's a nonzero exit
    from the ssh transport itself alongside empty output, which usually
    indicates a dropped connection rather than a real remote error)."""
    full_cmd = _HADOOP_ENV_PREFIX + remote_cmd
    proc = _run_with_retry(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HADOOP_CLUSTER_SSH_HOST, full_cmd],
        timeout,
        f"ssh {HADOOP_CLUSTER_SSH_HOST}",
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Remote command failed (exit {proc.returncode}) on {HADOOP_CLUSTER_SSH_HOST}:\n"
            f"cmd: {remote_cmd}\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return proc


def _scp_local_arg(local_path: Path) -> str:
    """Windows' scp.exe (OpenSSH-for-Windows) mis-parses absolute paths
    containing parentheses -- and this project's own directory name
    happens to contain one (`theoretical-week-simulator(1)`), which broke
    every scp call with 'stat local "": No such file or directory' until
    this was found. Passing a path relative to the current working
    directory (this project's scripts are always run from the project
    root) sidesteps the parenthesized directory component entirely."""
    try:
        return str(Path(local_path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(local_path)  # not under cwd; best effort, may hit the same bug


def scp_to_master(local_path: Path, remote_path: str, timeout: float = 300.0) -> None:
    local_arg = _scp_local_arg(local_path)
    proc = _run_with_retry(
        ["scp", "-o", "BatchMode=yes", local_arg, f"{HADOOP_CLUSTER_SSH_HOST}:{remote_path}"],
        timeout,
        f"scp {local_arg} -> {HADOOP_CLUSTER_SSH_HOST}:{remote_path}",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"scp to master failed: {proc.stderr}")


def scp_from_master(remote_path: str, local_path: Path, timeout: float = 300.0) -> None:
    local_arg = _scp_local_arg(local_path)
    proc = _run_with_retry(
        ["scp", "-o", "BatchMode=yes", f"{HADOOP_CLUSTER_SSH_HOST}:{remote_path}", local_arg],
        timeout,
        f"scp {HADOOP_CLUSTER_SSH_HOST}:{remote_path} -> {local_arg}",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"scp from master failed: {proc.stderr}")


def is_cluster_reachable() -> bool:
    try:
        proc = ssh_run("hostname", timeout=8, check=False)
        return proc.returncode == 0
    except ClusterUnreachable:
        return False


@dataclass
class ClusterHealth:
    reachable: bool
    hadoop_version: str | None = None
    java_version: str | None = None
    hdfs_live_datanodes: int | None = None
    yarn_live_nodes: int | None = None
    notes: list | None = None


def check_cluster_health() -> ClusterHealth:
    """Read-only health check: versions + live DataNode/NodeManager counts.
    Never formats, deletes, or reconfigures anything."""
    notes = []
    if not is_cluster_reachable():
        return ClusterHealth(reachable=False, notes=["SSH to master failed or timed out."])

    hadoop_version = ssh_run("hadoop version 2>&1 | head -1", timeout=30, check=False).stdout.strip()
    java_version = ssh_run("java -version 2>&1 | head -1", timeout=30, check=False).stdout.strip()

    # These two spin up a client JVM and talk to the NameNode/ResourceManager
    # over the network; on this ~1-vCPU cluster that routinely takes 20-45s.
    hdfs_report = ssh_run("hdfs dfsadmin -report 2>&1", timeout=90, check=False).stdout
    live_dn = hdfs_report.count("Hostname:")

    yarn_nodes = ssh_run("yarn node -list 2>&1", timeout=90, check=False).stdout
    live_nm = sum(1 for line in yarn_nodes.splitlines() if "RUNNING" in line)

    return ClusterHealth(
        reachable=True,
        hadoop_version=hadoop_version,
        java_version=java_version,
        hdfs_live_datanodes=live_dn,
        yarn_live_nodes=live_nm,
        notes=notes,
    )


def ensure_remote_staging_dir() -> None:
    ssh_run(f"mkdir -p {HADOOP_CLUSTER_REMOTE_STAGING}")


def ensure_hdfs_project_dir(label: str) -> None:
    ssh_run(
        f"hdfs dfs -mkdir -p {HADOOP_CLUSTER_HDFS_PROJECT_PATH}/{label}/input && "
        f"hdfs dfs -rm -r -f -skipTrash {HADOOP_CLUSTER_HDFS_PROJECT_PATH}/{label}/output"
    )


__all__ = [
    "ClusterUnreachable",
    "ClusterHealth",
    "ssh_run",
    "scp_to_master",
    "scp_from_master",
    "is_cluster_reachable",
    "check_cluster_health",
    "ensure_remote_staging_dir",
    "ensure_hdfs_project_dir",
    "HADOOP_CLUSTER_STREAMING_JAR",
    "HADOOP_CLUSTER_REMOTE_STAGING",
    "HADOOP_CLUSTER_HDFS_PROJECT_PATH",
]
