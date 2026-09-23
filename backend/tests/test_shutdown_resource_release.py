"""Regression tests for shutdown-time resource release.

Verifies that long-lived composition-root resources (Cognee memory engines:
LanceDB vector engine and Kùzu graph engine) are released deterministically on
shutdown instead of being reclaimed by process exit.

Regression guard for: CogneeService.close() being unreachable from every
production lifecycle path (HTTP lifespan, MCP stdio, CLI).
"""

from types import SimpleNamespace

import pytest

from app.application.container import ApplicationContainer, reset_container
from app.services.cognee_service import CogneeService


class _RecordingCogneeService(CogneeService):
    """CogneeService stub recording close() invocations without touching databases."""

    def __init__(self) -> None:
        self.close_calls = 0

    async def close(self) -> None:
        self.close_calls += 1

    async def initialize(self) -> None:  # pragma: no cover - unused
        return None


@pytest.mark.asyncio
async def test_container_shutdown_releases_cognee_engines():
    """Container.shutdown() must invoke CogneeService.close() exactly once."""
    container = ApplicationContainer()
    stub = _RecordingCogneeService()
    container.cognee_service = stub

    await container.shutdown()

    assert stub.close_calls == 1


@pytest.mark.asyncio
async def test_container_shutdown_is_safe_before_initialization():
    """Shutdown before initialize() must not raise."""
    container = ApplicationContainer()
    assert container.cognee_service is None

    await container.shutdown()

    assert container.cognee_service is None


@pytest.mark.asyncio
async def test_container_shutdown_survives_engine_close_failure():
    """A failing engine close must not propagate and break shutdown."""

    class _ExplodingCogneeService(_RecordingCogneeService):
        async def close(self) -> None:
            raise RuntimeError("lancedb unavailable")

    container = ApplicationContainer()
    container.cognee_service = _ExplodingCogneeService()

    await container.shutdown()  # must not raise


@pytest.mark.asyncio
async def test_http_lifespan_releases_resources_on_shutdown(monkeypatch):
    """FastAPI lifespan must call container.shutdown() after the app stops serving."""
    from app import server

    shutdown_calls = 0

    class _LifecycleContainer:
        async def initialize(self) -> None:
            return None

        async def shutdown(self) -> None:
            nonlocal shutdown_calls
            shutdown_calls += 1

    lifecycle_container = _LifecycleContainer()
    monkeypatch.setattr(server, "get_container", lambda *args, **kwargs: lifecycle_container)

    fake_app = SimpleNamespace(state=SimpleNamespace())

    async with server.lifespan(fake_app):
        assert shutdown_calls == 0
        assert fake_app.state.container is lifecycle_container

    assert shutdown_calls == 1


@pytest.mark.asyncio
async def test_cognee_close_resets_initialized_state():
    """After close(), the service must report uninitialized and be re-initializable."""
    service = CogneeService.__new__(CogneeService)
    service._initialized = True
    service._last_retrieval_telemetry = {}
    service._last_tier3_telemetry = {}

    await service.close()

    assert service.is_initialized is False


def test_reset_container_clears_singleton():
    """Explicit container reset must not retain the previous composition root."""
    from app.application import container as container_module

    sentinel = ApplicationContainer()
    container_module.set_container(sentinel)
    assert container_module.get_container() is sentinel

    reset_container()
    assert container_module._container is None
