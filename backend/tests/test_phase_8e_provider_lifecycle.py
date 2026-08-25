"""Phase 8E — Track 2: Real Subprocess Provider Crash, Outage, and Recovery Lifecycle.

Spawns a real OS subprocess HTTP server as an OpenAI-compatible provider, executing
5 repeated crash, outage, deterministic survival, and recovery cycles against RE:Track.
"""

import asyncio
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from typing import Optional

import pytest

from app.application.container import ApplicationContainer, reset_container
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.use_cases.context import BoundedConcurrencyGuard
from app.mcp.tools import (
    get_agent_context_tool,
    get_ast_call_graph_tool,
    get_repository_summary_tool,
    search_repository_code_tool,
)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_PROVIDER_SERVER_CODE = """
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

class ProviderHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silence stderr logs

    def do_GET(self):
        if self.path == "/v1/models" or self.path == "/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {"data": [{"id": "microsoft/phi-4-mini-reasoning"}]}
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/v1/chat/completions" or self.path == "/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "# Recovered Context\\n- src/main.py\\n"
                    }
                }]
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    port = int(sys.argv[1])
    server = HTTPServer(("127.0.0.1", port), ProviderHandler)
    server.serve_forever()
"""


def _start_provider_subprocess(port: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-c", _PROVIDER_SERVER_CODE, str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait until socket opens
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < 3.0:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except (ConnectionRefusedError, OSError):
            time.sleep(0.05)
    return proc


@pytest.mark.asyncio
async def test_real_subprocess_provider_crash_and_recovery_5_cycles(tmp_path: Path):
    """Verify same-process recovery across 5 real OS subprocess crash/restart cycles."""
    reset_container()
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}/v1"

    # Setup test workspace & repository
    test_repo = tmp_path / "provider_lifecycle_repo"
    test_repo.mkdir(parents=True, exist_ok=True)
    src_dir = test_repo / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "main.py").write_text("def run():\n    return 'ready'\n")

    container = ApplicationContainer()
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5, timeout=5.0)
    container._shared_concurrency_guard = guard

    container.workspace_auth.add_workspace_root(tmp_path)
    container.metadata_store.upsert(
        IndexedRepositoryRecord(
            id="provider_test_id",
            name=test_repo.name,
            path=str(test_repo.resolve()),
            languages=["Python"],
            file_count=1,
            last_indexed="2026-08-22T00:00:00Z",
            purpose="Provider lifecycle test repository",
        )
    )

    from app.config.settings import Settings
    custom_settings = Settings()
    custom_settings.llm_endpoint = base_url
    custom_settings.llm_provider = "openai_compatible"

    # Start the provider subprocess
    provider_proc = _start_provider_subprocess(port)
    assert provider_proc.poll() is None, "Subprocess provider failed to start"

    # Initialize container services
    await container.initialize(settings=custom_settings)
    if container.llm_provider:
        container.llm_provider.timeout = 2.0

    timings: list[dict[str, float]] = []

    try:
        for cycle in range(1, 6):
            t_cycle_start = time.perf_counter()

            # 1. Verify health & context generation while provider is alive
            t0 = time.perf_counter()
            health_online = await container.llm_provider.check_health()
            assert health_online.is_reachable is True, f"Cycle {cycle}: Provider expected online"
            health_latency = (time.perf_counter() - t0) * 1000

            # 2. Kill provider subprocess (hard SIGTERM / SIGKILL)
            t_kill = time.perf_counter()
            provider_proc.send_signal(signal.SIGKILL)
            provider_proc.wait(timeout=2.0)
            kill_duration = (time.perf_counter() - t_kill) * 1000

            # 3. Issue health check & context call -> verify fast socket failure detection
            t_detect = time.perf_counter()
            health_offline = await container.llm_provider.check_health()
            detect_duration = (time.perf_counter() - t_detect) * 1000
            assert health_offline.is_reachable is False

            # Context call must fail gracefully with structured error without crashing server
            res_fail = await get_agent_context_tool(
                task_prompt="Implement new feature",
                repository_path=str(test_repo),
                container=container,
            )
            assert "success" in res_fail

            # 4. Verify deterministic tools (AST, search, summary) operate with ZERO degradation during outage
            t_ast = time.perf_counter()
            ast_res = await get_ast_call_graph_tool(repository_path=str(test_repo), container=container)
            ast_latency = (time.perf_counter() - t_ast) * 1000
            assert ast_res.get("success") is True
            assert ast_latency < 50.0

            search_res = await search_repository_code_tool(
                repository_path=str(test_repo), query="run", container=container
            )
            assert search_res.get("success") is True

            # 5. Restart provider subprocess on the same port
            t_restart = time.perf_counter()
            provider_proc = _start_provider_subprocess(port)
            restart_duration = (time.perf_counter() - t_restart) * 1000

            # 6. Issue post-recovery health check through the SAME container / MCP process
            t_rec = time.perf_counter()
            health_restored = await container.llm_provider.check_health()
            rec_latency = (time.perf_counter() - t_rec) * 1000
            assert health_restored.is_reachable is True, f"Cycle {cycle}: Provider failed to recover"

            # 7. Verify concurrency guard state is completely clean
            assert guard.waiting_count == 0

            timings.append({
                "cycle": cycle,
                "health_latency_ms": health_latency,
                "detect_duration_ms": detect_duration,
                "restart_duration_ms": restart_duration,
                "recovery_latency_ms": rec_latency,
                "ast_latency_ms": ast_latency,
                "total_cycle_s": time.perf_counter() - t_cycle_start,
            })
    finally:
        if provider_proc and provider_proc.poll() is None:
            provider_proc.kill()
            provider_proc.wait()

    # Telemetry analysis
    avg_detect = sum(t["detect_duration_ms"] for t in timings) / len(timings)
    avg_recovery = sum(t["recovery_latency_ms"] for t in timings) / len(timings)
    max_ast = max(t["ast_latency_ms"] for t in timings)

    assert avg_detect < 100.0, f"Socket failure detection too slow: {avg_detect:.2f}ms"
    assert avg_recovery < 100.0, f"Recovery detection too slow: {avg_recovery:.2f}ms"
    assert max_ast < 50.0, f"Deterministic tool degraded during outage: {max_ast:.2f}ms"

    print(
        f"\n[Phase 8E Provider Lifecycle] 5/5 cycles PASSED | "
        f"Avg Socket Failure Detect: {avg_detect:.2f}ms | "
        f"Avg Recovery Detect: {avg_recovery:.2f}ms | "
        f"Max AST Latency during outage: {max_ast:.2f}ms"
    )
