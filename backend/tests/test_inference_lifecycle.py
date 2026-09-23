"""Regression tests for the local-model inference path.

Covers the defects measured during the real-runtime investigation:

1. One user action must produce exactly one provider inference (no duplication).
2. Optional LLM enrichment (intent parsing) must be bounded and must degrade to the
   deterministic fallback instead of consuming the whole request budget and then
   discarding the model's output.
3. A client disconnect must cancel in-flight provider work rather than let it run to
   completion for nobody.
4. Synchronous repository/AST work must not block the event loop.
5. The shared RepositorySummaryGenerator must stay consistent when invoked from
   worker threads.
"""

import asyncio
import time
from pathlib import Path
import tempfile
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.container import ApplicationContainer
from app.application.dto import AgentContextRequest, AgentContextResponse, ErrorResponse
from app.application.use_cases.context import BoundedConcurrencyGuard
from app.models.provider import DiscoveryStatus, ProviderHealthStatus, ProviderType
from app.services.intent_parser import (
    DEFAULT_INTENT_TIMEOUT_SEC,
    IntentParserService,
    resolve_intent_timeout,
)
from app.services.llm_provider_service import (
    DEFAULT_INFERENCE_TIMEOUT_SEC,
    LLMProviderService,
    resolve_inference_timeout,
)
from app.services.repository_summary import RepositorySummaryGenerator

VALID_INTENT_JSON = (
    '{"task_summary":"Explain budgeting","category":"explanation",'
    '"extracted_symbols":["BudgetManager"],"relevant_file_hints":[],"is_vague":false}'
)


class SpyProvider:
    """Provider double recording every generation request."""

    def __init__(
        self,
        response: str = VALID_INTENT_JSON,
        delay: float = 0.0,
        exc: Optional[BaseException] = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._response = response
        self._delay = delay
        self._exc = exc
        self.provider_type = ProviderType.LM_STUDIO
        self.default_model = "spy-model"
        self.last_invoked_model: Optional[str] = None

    async def check_health(self) -> ProviderHealthStatus:
        return ProviderHealthStatus(
            provider=self.provider_type,
            base_url="http://spy-provider/v1",
            is_reachable=True,
            active_model=self.default_model,
            loaded_models=[],
            quantization_warning=None,
            discovery_status=DiscoveryStatus.AVAILABLE,
        )

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: Optional[float] = None,
    ) -> str:
        self.calls.append({"timeout": timeout, "max_tokens": max_tokens, "model": model})
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._exc is not None:
            raise self._exc
        self.last_invoked_model = model or self.default_model
        return self._response


def _fake_package(markdown: str = "# Synthesized Context\n\nbody"):
    pkg = MagicMock()
    pkg.markdown = markdown
    pkg.task = "task"
    pkg.objective = "objective"
    pkg.section_count = 2
    pkg.source_count = 1
    pkg.token_estimate = 42
    pkg.dataset = "ds"
    pkg.sections = []
    pkg.references = []
    meta = MagicMock()
    meta.retrieved_memory_count = 0
    meta.deduplicated_count = 0
    meta.compressed_count = 0
    meta.compression_ratio = 1.0
    meta.retrieval_time_ms = 1
    meta.total_time_ms = 2
    pkg.metadata = meta
    return pkg


def _build_use_cases(
    repo_path: Path,
    provider: Optional[SpyProvider] = None,
    summary_generator: Any = None,
    guard: Optional[BoundedConcurrencyGuard] = None,
):
    container = ApplicationContainer.create()
    container.workspace_auth = MagicMock()
    container.workspace_auth.is_path_authorized.return_value = (True, None)

    container.cognee_service = MagicMock()
    container.indexing_service = MagicMock()
    container.indexing_service.discover_files.return_value = [repo_path / "main.py"]
    container.indexing_service.filter_files.return_value = [repo_path / "main.py"]

    container.context_service = MagicMock()
    container.context_service.generate_context_package = AsyncMock(return_value=_fake_package())

    if provider is not None:
        container.llm_provider = provider
        container.intent_parser = IntentParserService(provider)
    if summary_generator is not None:
        container.summary_generator = summary_generator
    if guard is not None:
        container.concurrency_guard = guard

    return container, container.get_context_use_cases()


def _request(repo_path: Path, prompt: str = "Explain the token budgeting pipeline"):
    return AgentContextRequest(
        task_prompt=prompt,
        repository_path=str(repo_path),
        dataset_name="test_repo",
        max_tokens=4000,
        include_structural_graph=False,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    (repo_path / "main.py").write_text("def run():\n    return 1\n")
    return repo_path


@pytest.mark.asyncio
async def test_single_request_produces_exactly_one_provider_inference(repo: Path):
    """One context request must invoke the model exactly once."""
    provider = SpyProvider()
    _container, use_cases = _build_use_cases(repo, provider=provider)

    result = await use_cases.get_agent_context(_request(repo))

    assert isinstance(result, AgentContextResponse), result
    # Exactly one provider call, and it is the intent enrichment completing cleanly.
    assert len(provider.calls) == 1
    assert result.inference_status == "completed"


@pytest.mark.asyncio
async def test_identical_repeat_is_served_from_cache_without_second_inference(repo: Path):
    """Repeating the same request must not re-run the model."""
    provider = SpyProvider()
    _container, use_cases = _build_use_cases(repo, provider=provider)

    first = await use_cases.get_agent_context(_request(repo, "Explain the token budgeting pipeline"))
    second = await use_cases.get_agent_context(_request(repo, "Explain the token budgeting pipeline"))

    assert isinstance(first, AgentContextResponse)
    assert isinstance(second, AgentContextResponse)
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_repeated_inference_lifecycle_is_stable(repo: Path):
    """Sequential distinct requests invoke the model once each and never leak the guard."""
    provider = SpyProvider()
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5, timeout=5.0)
    _container, use_cases = _build_use_cases(repo, provider=provider, guard=guard)

    for i in range(5):
        result = await use_cases.get_agent_context(_request(repo, f"Explain budgeting variant {i}"))
        assert isinstance(result, AgentContextResponse), result

    assert len(provider.calls) == 5
    assert guard.waiting_count == 0


@pytest.mark.asyncio
async def test_concurrent_requests_do_not_duplicate_inference(repo: Path):
    """Concurrent requests must produce at most one provider call per admitted request."""
    provider = SpyProvider(delay=0.05)
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5, timeout=5.0)
    _container, use_cases = _build_use_cases(repo, provider=provider, guard=guard)

    results = await asyncio.gather(
        use_cases.get_agent_context(_request(repo, "concurrent task A")),
        use_cases.get_agent_context(_request(repo, "concurrent task B")),
    )

    admitted = [r for r in results if isinstance(r, AgentContextResponse)]
    assert len(provider.calls) == len(admitted)
    assert guard.waiting_count == 0


@pytest.mark.asyncio
async def test_slow_intent_enrichment_is_cancelled_at_its_budget(repo: Path):
    """A hanging enrichment must be cancelled at its budget, not waited on."""
    provider = SpyProvider(delay=10.0)
    parser = IntentParserService(provider, intent_timeout=0.4)

    started = time.perf_counter()
    record = await parser.parse_intent("Explain the token budgeting pipeline")
    elapsed = time.perf_counter() - started

    assert record.inference_status == "timeout"
    assert elapsed < 3.0
    assert DEFAULT_INTENT_TIMEOUT_SEC < DEFAULT_INFERENCE_TIMEOUT_SEC


@pytest.mark.asyncio
async def test_slow_intent_enrichment_does_not_stall_the_request(repo: Path):
    """The full request must complete promptly when enrichment is slow."""
    provider = SpyProvider(delay=10.0)
    _container, use_cases = _build_use_cases(repo, provider=provider)
    use_cases._intent_parser = IntentParserService(provider, intent_timeout=0.4)

    started = time.perf_counter()
    result = await use_cases.get_agent_context(_request(repo, "slow enrichment probe"))
    elapsed = time.perf_counter() - started

    assert isinstance(result, AgentContextResponse), result
    assert result.inference_status == "timeout"
    assert elapsed < 5.0


def test_intent_timeout_is_configurable(monkeypatch):
    """Intent budget honours explicit construction, env override, then default."""
    provider = SpyProvider()
    assert IntentParserService(provider, intent_timeout=7.5)._intent_timeout == 7.5

    monkeypatch.setenv("RETRACK_INTENT_TIMEOUT_SEC", "12")
    assert resolve_intent_timeout() == 12.0

    monkeypatch.setenv("RETRACK_INTENT_TIMEOUT_SEC", "not-a-number")
    assert resolve_intent_timeout() == DEFAULT_INTENT_TIMEOUT_SEC


@pytest.mark.asyncio
async def test_intent_timeout_degrades_to_deterministic_fallback(repo: Path):
    """A timed-out enrichment must fall back deterministically and report the reason."""
    provider = SpyProvider(exc=TimeoutError("exceeded the 20s generation budget"))
    parser = IntentParserService(provider, intent_timeout=20.0)

    record = await parser.parse_intent("Explain the token budgeting pipeline")

    assert record.inference_status == "timeout"
    assert record.fallback_used is True
    assert record.model_invoked is False
    assert record.fallback_reason and "budget" in record.fallback_reason
    assert record.fallback_reason != "Model response was not valid JSON schema"
    assert record.inference_time_ms >= 0


@pytest.mark.asyncio
async def test_intent_timeout_surfaces_in_request_response(repo: Path):
    """The request must complete (via fallback) and expose the timeout status."""
    provider = SpyProvider(exc=TimeoutError("exceeded the 20s generation budget"))
    _container, use_cases = _build_use_cases(repo, provider=provider)

    started = time.perf_counter()
    result = await use_cases.get_agent_context(_request(repo))
    elapsed = time.perf_counter() - started

    assert isinstance(result, AgentContextResponse), result
    assert result.inference_status == "timeout"
    assert result.model_invoked is False
    assert elapsed < 5.0


@pytest.mark.asyncio
async def test_provider_failure_releases_guard_and_reports_status(repo: Path):
    """A failing provider must not leak the concurrency slot or raise."""
    provider = SpyProvider(exc=RuntimeError("provider exploded"))
    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=5, timeout=5.0)
    _container, use_cases = _build_use_cases(repo, provider=provider, guard=guard)

    result = await use_cases.get_agent_context(_request(repo, "first attempt"))

    assert isinstance(result, AgentContextResponse), result
    assert result.inference_status == "failed"
    assert guard.waiting_count == 0

    # The slot must be reusable afterwards.
    ok = SpyProvider()
    _c2, uc2 = _build_use_cases(repo, provider=ok, guard=guard)
    result2 = await uc2.get_agent_context(_request(repo, "second attempt"))
    assert isinstance(result2, AgentContextResponse)
    assert guard.waiting_count == 0


@pytest.mark.asyncio
async def test_client_disconnect_cancels_in_flight_provider_work(repo: Path):
    """Disconnecting must cancel provider work instead of waiting for it."""
    provider = SpyProvider(delay=5.0)
    _container, use_cases = _build_use_cases(repo, provider=provider)

    probe_calls = 0

    async def disconnect_probe() -> bool:
        nonlocal probe_calls
        probe_calls += 1
        return True  # client is already gone

    started = time.perf_counter()
    result = await use_cases.get_agent_context(
        _request(repo, "abandoned request"),
        disconnect_probe=disconnect_probe,
    )
    elapsed = time.perf_counter() - started

    assert isinstance(result, ErrorResponse)
    assert result.error == "ClientDisconnected"
    assert probe_calls >= 1
    # Cancelled well before the 5s provider delay completed.
    assert elapsed < 2.0
    assert use_cases._guard.waiting_count == 0


@pytest.mark.asyncio
async def test_connected_client_is_not_cancelled(repo: Path):
    """A probe reporting a live connection must not disturb a normal request."""
    provider = SpyProvider()
    _container, use_cases = _build_use_cases(repo, provider=provider)

    async def still_connected() -> bool:
        return False

    result = await use_cases.get_agent_context(
        _request(repo, "live request"),
        disconnect_probe=still_connected,
    )

    assert isinstance(result, AgentContextResponse), result
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_event_loop_stays_responsive_during_blocking_summary_work(repo: Path):
    """Synchronous AST work must run off the event loop."""

    class BlockingSummaryGenerator:
        """Emulates CPU-bound AST parsing (0.4s) without any awaits."""

        def generate(self, repo_path, files, *args, **kwargs):
            time.sleep(0.4)
            summary = MagicMock()
            summary.call_graph_nodes = []
            summary.call_graph_edges = []
            summary.technology_stack = None
            summary.architecture = None
            summary.key_components = []
            summary.project_purpose = "test"
            summary.call_graph_status = "zero_edges"
            summary.call_graph_error = None
            return summary

    _container, use_cases = _build_use_cases(repo, summary_generator=BlockingSummaryGenerator())

    ticks = 0
    stop = asyncio.Event()

    async def ticker():
        nonlocal ticks
        while not stop.is_set():
            ticks += 1
            await asyncio.sleep(0.01)

    ticker_task = asyncio.create_task(ticker())
    try:
        result = await use_cases.get_agent_context(_request(repo, "blocking summary probe"))
    finally:
        stop.set()
        await ticker_task

    assert isinstance(result, AgentContextResponse), result
    # 0.4s of blocking work at 10ms ticks would allow ~0 ticks if run on the loop.
    assert ticks >= 8, f"event loop was blocked by synchronous summary work (ticks={ticks})"


def test_offload_pool_is_bounded():
    """The offload pool must stay small; asyncio.to_thread would grow to cpu_count+4."""
    from app.application.use_cases.context import (
        _OFFLOAD_MAX_WORKERS,
        get_offload_executor,
        shutdown_offload_executor,
    )

    try:
        executor = get_offload_executor()
        assert executor._max_workers == _OFFLOAD_MAX_WORKERS
        assert _OFFLOAD_MAX_WORKERS <= 2
        # Lazily created: no worker threads before any submission.
        assert len(getattr(executor, "_threads", ())) <= _OFFLOAD_MAX_WORKERS
    finally:
        shutdown_offload_executor()
    # Shutdown must actually release the pool so it can be recreated.
    assert get_offload_executor() is not executor
    shutdown_offload_executor()


def test_shared_summary_generator_is_thread_safe(tmp_path: Path):
    """Concurrent worker-thread calls on one shared instance must stay consistent."""
    repo_path = tmp_path / "summary_repo"
    repo_path.mkdir()
    for i in range(6):
        (repo_path / f"mod_{i}.py").write_text(
            f"def handler_{i}():\n    return {i}\n\nclass Service{i}:\n    def run(self):\n        return handler_{i}()\n"
        )
    files = sorted(repo_path.glob("*.py"))

    reference = RepositorySummaryGenerator().generate(repo_path, files)
    expected_nodes = len(reference.call_graph_nodes)

    from app.application.use_cases.context import run_offloaded, shutdown_offload_executor

    shared = RepositorySummaryGenerator()

    async def run_concurrently():
        try:
            return await asyncio.gather(
                *[run_offloaded(shared.generate, repo_path, files) for _ in range(4)]
            )
        finally:
            shutdown_offload_executor()

    summaries = asyncio.run(run_concurrently())

    assert expected_nodes > 0
    for summary in summaries:
        assert len(summary.call_graph_nodes) == expected_nodes
        assert summary.repository_fingerprint == reference.repository_fingerprint


def test_agent_context_endpoint_wires_disconnect_probe():
    """The HTTP route must supply a disconnect probe (and still route correctly)."""
    from fastapi.testclient import TestClient

    import app.api.routers.context as context_router
    from app.server import create_app

    app = create_app()
    recorded: dict[str, Any] = {}

    class FakeUseCases:
        async def get_agent_context(self, request, disconnect_probe=None):
            recorded["probe"] = disconnect_probe
            return AgentContextResponse(
                success=True,
                context_markdown="# ok",
                task_summary="summary",
                intent_category="explanation",
                extracted_symbols=[],
                callers=[],
                callees=[],
                related_files=[],
                estimated_tokens=1,
                generation_time_ms=1,
            )

    app.dependency_overrides[context_router.get_context_use_cases] = lambda: FakeUseCases()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/context",
        json={"task_prompt": "explain", "repository_path": "/tmp"},
    )

    assert response.status_code == 200, response.text
    assert callable(recorded.get("probe"))


def test_inference_timeout_is_configurable_and_overridable(monkeypatch):
    """Generation budget resolution order: explicit, env, default."""
    assert resolve_inference_timeout(42.0) == 42.0
    assert resolve_inference_timeout() == DEFAULT_INFERENCE_TIMEOUT_SEC
    assert DEFAULT_INFERENCE_TIMEOUT_SEC > 60.0  # old hard-coded cap is gone

    monkeypatch.setenv("RETRACK_INFERENCE_TIMEOUT_SEC", "240")
    assert resolve_inference_timeout() == 240.0
    assert resolve_inference_timeout(99.0) == 99.0

    monkeypatch.setenv("RETRACK_INFERENCE_TIMEOUT_SEC", "garbage")
    assert resolve_inference_timeout() == DEFAULT_INFERENCE_TIMEOUT_SEC


@pytest.mark.asyncio
async def test_generate_completion_applies_resolved_budget(monkeypatch):
    """The provider must hand the resolved budget to the HTTP client."""
    import app.services.llm_provider_service as provider_module

    captured: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "ok"}}], "model": "phi4-mini"}

    class FakeAsyncClient:
        def __init__(self, timeout: float | None = None, **kwargs: Any) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *exc: Any) -> bool:
            return False

        async def post(self, url: str, headers: Any = None, json: Any = None) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(provider_module.httpx, "AsyncClient", FakeAsyncClient)

    service = LLMProviderService(
        provider_type=ProviderType.LM_STUDIO,
        base_url="http://127.0.0.1:1234/v1",
        default_model="phi4-mini",
    )
    service._health_checked = True
    service.discovered_models = ["phi4-mini"]
    service.verified_active_model = "phi4-mini"

    await service.generate_completion("hello", timeout=77.0)
    assert captured["timeout"] == 77.0

    await service.generate_completion("hello")
    assert captured["timeout"] == DEFAULT_INFERENCE_TIMEOUT_SEC
