"""Phase 9C — Track 4: In-Application Health & Operational Status Tests.

Verifies health state classifications (healthy, degraded, unavailable),
provider online/offline behavior, concurrency metrics, and CLI output.
"""

import asyncio
from pathlib import Path
import tempfile
import pytest
from typer.testing import CliRunner

from app.application.dto import HealthResponse, DetailedHealthResponse
from app.application.use_cases.context import BoundedConcurrencyGuard
from app.application.use_cases.system import SystemUseCases
from app.cli.main import app
from app.config.settings import Settings

runner = CliRunner()


class DummyProviderHealth:
    def __init__(self, reachable: bool = True, model: str = "phi4-mini"):
        self.is_reachable = reachable
        self.active_model = model


class DummyLLMProvider:
    def __init__(self, reachable: bool = True):
        self._reachable = reachable

    async def check_health(self):
        return DummyProviderHealth(reachable=self._reachable, model="phi4-mini")


class DummyCognee:
    is_initialized = True


@pytest.mark.asyncio
async def test_health_when_healthy(monkeypatch):
    """Verify health returns healthy when provider and storage are functional."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        settings = Settings()

        guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5)
        use_cases = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: DummyCognee(),
            llm_provider_getter=lambda: DummyLLMProvider(reachable=True),
            provider_updater_fn=lambda *args: asyncio.sleep(0),
            concurrency_guard=guard,
        )

        res = await use_cases.health()
        assert isinstance(res, HealthResponse)
        assert res.status == "ok"
        assert res.health_state == "healthy"
        assert res.ollama_reachable is True
        assert res.concurrency_queue_depth == 0
        assert res.concurrency_queue_capacity == 5


@pytest.mark.asyncio
async def test_health_when_provider_offline(monkeypatch):
    """Verify health degrades to 'degraded' when provider is unreachable on configured system."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        (Path(tmpdir) / ".retrack").mkdir(parents=True, exist_ok=True)
        settings = Settings()

        use_cases = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: DummyCognee(),
            llm_provider_getter=lambda: DummyLLMProvider(reachable=False),
            provider_updater_fn=lambda *args: asyncio.sleep(0),
        )

        res = await use_cases.health()
        assert isinstance(res, HealthResponse)
        assert res.status == "degraded"
        assert res.health_state == "degraded"
        assert res.ollama_reachable is False


@pytest.mark.asyncio
async def test_health_when_not_configured(monkeypatch):
    """Verify health returns 'not_configured' when ~/.retrack has not been initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        settings = Settings()

        use_cases = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: DummyCognee(),
            llm_provider_getter=lambda: DummyLLMProvider(reachable=False),
            provider_updater_fn=lambda *args: asyncio.sleep(0),
        )

        res = await use_cases.health()
        assert isinstance(res, HealthResponse)
        assert res.health_state == "not_configured"


@pytest.mark.asyncio
async def test_detailed_health_structure(monkeypatch):
    """Verify get_detailed_health provides storage paths and recent log records."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        settings = Settings()
        settings.logging.log_dir = Path(tmpdir) / ".retrack" / "logs"

        use_cases = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: DummyCognee(),
            llm_provider_getter=lambda: DummyLLMProvider(reachable=True),
            provider_updater_fn=lambda *args: asyncio.sleep(0),
        )

        res = await use_cases.get_detailed_health()
        assert isinstance(res, DetailedHealthResponse)
        assert res.health_state == "healthy"
        assert "canonical_root" in res.storage_paths
        assert "logs_directory" in res.storage_paths
        assert isinstance(res.diagnostics_log_entries, list)


def test_cli_health_command(monkeypatch):
    """Verify `retrack health` CLI output renders the operational table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        res = runner.invoke(app, ["health"])
        assert res.exit_code == 0
        assert "System Health & Operational Status" in res.stdout
        assert "Overall Health" in res.stdout
        assert "Memory Engine (Cognee)" in res.stdout
