"""Unit tests for src/mapreduce/cluster.py helpers that don't require a live
cluster connection: the scp path-escaping workaround (the actual bug that
broke every scp call until found -- see docs/decisions/0005) and the retry
wrapper's give-up behavior.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.mapreduce.cluster import ClusterUnreachable, _run_with_retry, _scp_local_arg  # noqa: E402


def test_scp_local_arg_converts_absolute_path_under_cwd_to_relative():
    target = Path.cwd() / "src" / "mapreduce" / "reducer.py"
    result = _scp_local_arg(target)
    assert result == str(Path("src") / "mapreduce" / "reducer.py")
    assert "(" not in result and ")" not in result


def test_scp_local_arg_falls_back_to_absolute_for_paths_outside_cwd(tmp_path):
    # pytest's tmp_path is never under this project's cwd, so relative_to()
    # raises (ValueError, or on Windows possibly a different-drive error)
    # and the function should fall back to returning the path as-is.
    outside = Path(tmp_path).resolve() / "somefile.txt"
    result = _scp_local_arg(outside)
    assert result == str(outside)


def test_run_with_retry_gives_up_after_max_attempts():
    calls = []

    def fake_run(cmd, capture_output, text, timeout):
        calls.append(1)
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="boom")

    with patch("src.mapreduce.cluster.subprocess.run", side_effect=fake_run), \
         patch("src.mapreduce.cluster.time.sleep"):
        proc = _run_with_retry(["ssh", "tws-master", "true"], timeout=5, error_label="test")

    assert len(calls) == 3  # _MAX_ATTEMPTS
    assert proc.returncode == 1


def test_run_with_retry_succeeds_after_transient_failure():
    attempts = {"n": 0}

    def fake_run(cmd, capture_output, text, timeout):
        attempts["n"] += 1
        if attempts["n"] < 2:
            return subprocess.CompletedProcess(cmd, returncode=255, stdout="", stderr="connection reset")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="ok", stderr="")

    with patch("src.mapreduce.cluster.subprocess.run", side_effect=fake_run), \
         patch("src.mapreduce.cluster.time.sleep"):
        proc = _run_with_retry(["ssh", "tws-master", "true"], timeout=5, error_label="test")

    assert attempts["n"] == 2
    assert proc.returncode == 0


def test_run_with_retry_raises_cluster_unreachable_on_repeated_timeout():
    def fake_run(cmd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    with patch("src.mapreduce.cluster.subprocess.run", side_effect=fake_run), \
         patch("src.mapreduce.cluster.time.sleep"):
        try:
            _run_with_retry(["ssh", "tws-master", "true"], timeout=5, error_label="test")
            assert False, "expected ClusterUnreachable"
        except ClusterUnreachable:
            pass
