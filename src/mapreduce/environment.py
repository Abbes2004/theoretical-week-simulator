"""Detect what Hadoop execution mode is actually available on this machine.

Used by scripts/run_hadoop_job.py so the project never silently claims a
distributed/pseudo-distributed run happened when it did not. See
docs/decisions/0004-hadoop-environment-and-benchmark-design.md for the full
inspection log from this development machine (as of 2026-09-10: no Java,
no Hadoop, no usable general-purpose Linux environment -- WSL only has the
internal `docker-desktop` distribution, which is not a general dev
environment and was left untouched).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class HadoopEnvironment:
    java_available: bool
    java_version: str | None
    hadoop_available: bool
    hadoop_version: str | None
    hadoop_home: str | None
    streaming_jar: str | None
    os_platform: str
    execution_mode: str  # "real_local" | "real_pseudo_distributed" | "real_cluster" | "unavailable"
    notes: list[str] = field(default_factory=list)

    @property
    def can_run_real_hadoop(self) -> bool:
        return self.execution_mode != "unavailable"


def _run(cmd: list[str], timeout: float = 5.0) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        return False, str(exc)


def detect_hadoop_environment() -> HadoopEnvironment:
    notes: list[str] = []

    java_path = shutil.which("java")
    java_ok, java_out = (False, "") if not java_path else _run(["java", "-version"])
    java_version = java_out.splitlines()[0] if java_ok and java_out else None
    if not java_path:
        notes.append("`java` not found on PATH.")

    hadoop_path = shutil.which("hadoop")
    hadoop_ok, hadoop_out = (False, "") if not hadoop_path else _run(["hadoop", "version"])
    hadoop_version = hadoop_out.splitlines()[0] if hadoop_ok and hadoop_out else None
    if not hadoop_path:
        notes.append("`hadoop` not found on PATH.")

    import os

    hadoop_home = os.environ.get("HADOOP_HOME")
    streaming_jar = None
    if hadoop_home:
        import glob

        candidates = glob.glob(f"{hadoop_home}/share/hadoop/tools/lib/hadoop-streaming*.jar")
        streaming_jar = candidates[0] if candidates else None
        if hadoop_path and not streaming_jar:
            notes.append(f"HADOOP_HOME is set ({hadoop_home}) but no hadoop-streaming*.jar found under it.")
    elif hadoop_path:
        notes.append("`hadoop` is on PATH but HADOOP_HOME is not set; cannot locate the streaming jar.")

    if java_path and hadoop_path and streaming_jar:
        # We can locate the binaries; whether HDFS/YARN daemons are
        # actually running (pseudo-distributed) is checked separately by
        # scripts/run_hadoop_job.py immediately before a real run is
        # attempted (`hadoop fs -ls /` success/failure), since that state
        # changes independently of whether the software is installed.
        execution_mode = "real_local"
        notes.append(
            "Java, hadoop, and the streaming jar were all found. Whether HDFS/YARN daemons "
            "are running (enabling pseudo-distributed mode) is checked at run time, not here."
        )
    else:
        execution_mode = "unavailable"
        notes.append(
            "Real Hadoop execution is NOT possible on this machine in its current state. "
            "See docs/decisions/0004-hadoop-environment-and-benchmark-design.md for the exact "
            "prerequisites (JDK, Hadoop binary distribution, winutils.exe for Windows, "
            "HADOOP_HOME/JAVA_HOME, HDFS format+start) that would need to be installed."
        )

    return HadoopEnvironment(
        java_available=java_ok,
        java_version=java_version,
        hadoop_available=hadoop_ok,
        hadoop_version=hadoop_version,
        hadoop_home=hadoop_home,
        streaming_jar=streaming_jar,
        os_platform=f"{platform.system()} {platform.release()} ({platform.version()})",
        execution_mode=execution_mode,
        notes=notes,
    )


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    print(json.dumps(asdict(detect_hadoop_environment()), indent=2))
