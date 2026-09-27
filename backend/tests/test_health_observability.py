"""Phase 9C — Track 4: In-Application Health & Operational Status Tests.

Verifies health state classifications (healthy, degraded, unavailable),
provider online/offline behavior, concurrency metrics, and CLI output.
"""

import asyncio
import json
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


def _health_use_cases(settings, *, reachable=True):
    return SystemUseCases(
        settings_getter=lambda: settings,
        cognee_service_getter=lambda: DummyCognee(),
        llm_provider_getter=lambda: DummyLLMProvider(reachable=reachable),
        provider_updater_fn=lambda *args: asyncio.sleep(0),
    )


@pytest.mark.asyncio
async def test_health_counts_match_the_registered_stores(monkeypatch):
    """Health counts what /repos and /packages read.

    Both canonical stores are JSON objects keyed by id, and the registered
    catalog (repositories.json) is authoritative over the indexed-metadata
    store (indexed_repos.json), which only holds indexed records.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        root = Path(tmpdir) / ".retrack"
        root.mkdir(parents=True, exist_ok=True)
        (root / "repositories.json").write_text(
            json.dumps({f"repo-{i}": {"id": f"repo-{i}", "name": f"repo-{i}"} for i in range(3)}),
            encoding="utf-8",
        )
        # Fewer indexed records than registered repositories: this store must not shadow the catalog.
        (root / "indexed_repos.json").write_text(json.dumps({"repo-0": {"id": "repo-0"}}), encoding="utf-8")
        (root / "context_packages.json").write_text(
            json.dumps({f"pkg-{i}": {"id": f"pkg-{i}"} for i in range(2)}),
            encoding="utf-8",
        )

        settings = Settings()
        res = await _health_use_cases(settings).health()

        assert isinstance(res, HealthResponse)
        assert res.repository_count == 3, "the registered repository catalog is authoritative"
        assert res.context_package_count == 2

        # A fresh instance — a restarted backend — reads the same persisted state.
        restarted = await _health_use_cases(settings).health()
        assert isinstance(restarted, HealthResponse)
        assert restarted.repository_count == 3
        assert restarted.context_package_count == 2


@pytest.mark.asyncio
async def test_health_counts_legacy_list_stores_and_skips_unreadable_ones(monkeypatch):
    """List-shaped legacy stores still count; an unreadable store falls through."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("HOME", tmpdir)
        root = Path(tmpdir) / ".retrack"
        root.mkdir(parents=True, exist_ok=True)
        (root / "repositories.json").write_text("{not json", encoding="utf-8")
        (root / "indexed_repos.json").write_text(json.dumps([{"id": "a"}, {"id": "b"}]), encoding="utf-8")
        (root / "context_packages.json").write_text(json.dumps([{"id": "p"}]), encoding="utf-8")

        res = await _health_use_cases(Settings()).health()

        assert isinstance(res, HealthResponse)
        assert res.repository_count == 2, "an unreadable store falls through to the next candidate"
        assert res.context_package_count == 1


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
