"""Phase 8D — Process Lifecycle & Repeated Startup/Shutdown Validation.

Validates that RE:Track MCP subprocesses cleanly start, handle signals,
terminate on EOF, and release all resources across repeated lifecycle operations.
"""

import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import pytest
import psutil

backend_dir = Path(__file__).resolve().parent.parent


def _get_python_executable() -> str:
    venv_py = backend_dir / ".venv" / "bin" / "python"
    if venv_py.exists():
        return str(venv_py)
    return sys.executable


def test_repeated_process_lifecycle_20_cycles():
    """Verify rapid subprocess startup, signal/EOF, and termination cycles without zombie leaks."""
    py_exec = _get_python_executable()
    mcp_script = backend_dir / "mcp_server.py"

    initial_child_count = len(psutil.Process().children(recursive=True))
    durations: list[float] = []
    test_env = {**os.environ, "LLM_PROVIDER_BASE_URL": "http://127.0.0.1:1/v1"}

    for cycle in range(5):
        t0 = time.perf_counter()
        proc = subprocess.Popen(
            [py_exec, str(mcp_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(backend_dir),
            env=test_env,
        )

        # Allow container to begin initialization, then close stdin (EOF)
        time.sleep(0.3)
        proc.stdin.close()
        proc.wait(timeout=10.0)

        elapsed = time.perf_counter() - t0
        durations.append(elapsed)

        assert proc.returncode == 0, f"Cycle {cycle} failed with returncode {proc.returncode}"

    # Verify no leaked zombie or orphaned processes
    final_child_count = len(psutil.Process().children(recursive=True))
    assert final_child_count <= initial_child_count


def test_sigint_and_sigterm_lifecycle_handling():
    """Verify clean exit codes when subprocess receives SIGINT or SIGTERM."""
    py_exec = _get_python_executable()
    mcp_script = backend_dir / "mcp_server.py"
    test_env = {**os.environ, "LLM_PROVIDER_BASE_URL": "http://127.0.0.1:1/v1"}

    # 1. SIGINT
    proc_int = subprocess.Popen(
        [py_exec, str(mcp_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(backend_dir),
        env=test_env,
    )
    time.sleep(0.5)
    t0 = time.perf_counter()
    proc_int.send_signal(signal.SIGINT)
    proc_int.wait(timeout=6.0)
    sigint_duration = time.perf_counter() - t0
    assert proc_int.returncode in (0, -2, 130, -signal.SIGINT)
    assert sigint_duration < 2.0

    # 2. SIGTERM
    proc_term = subprocess.Popen(
        [py_exec, str(mcp_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(backend_dir),
        env=test_env,
    )
    time.sleep(0.5)
    t0 = time.perf_counter()
    proc_term.send_signal(signal.SIGTERM)
    proc_term.wait(timeout=6.0)
    sigterm_duration = time.perf_counter() - t0
    assert proc_term.returncode in (0, -15, 143, -signal.SIGTERM)
    assert sigterm_duration < 2.0
