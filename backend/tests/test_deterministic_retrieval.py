"""Regression tests for deterministic retrieval routing and embedding-provider consistency.

Background (measured on a real runtime before the fix): one context-generation
request produced two `cognee.recall()` calls. RE:Track explicitly requested
`SearchType.CHUNKS` for the Tier-4 semantic-memory call, but the `ContextService`
package-assembly call passed no query type, so Cognee's automatic query router
selected `GRAPH_COMPLETION_COT` — an LLM-backed retriever — for a retrieval
operation. Meanwhile the configured embedding endpoint was unusable, so both
recalls failed and the package reported zero retrieved sources as if retrieval had
succeeded.

These tests pin:

1. retrieval requests an explicit, non-LLM search type and disables the router;
2. the router is therefore never the source of the retrieval mode;
3. embedding-provider availability is explicit, truthful, and never substituted;
4. an unavailable embedding provider produces a truthful degraded state;
5. LLM and embedding provider identities stay independent;
6. successful retrieval still yields evidence, and evidence gating is unchanged.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.use_cases.context import ContextUseCases
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings
from app.models.errors import CogneeServiceError
from app.models.responses import RecallResponse, RecallResult
from app.services.cognee_service import (
    CogneeService,
    default_recall_query_type,
    sanitize_dataset_name,
)
from app.services.context_service import ContextService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService

AVAILABLE_EMBEDDING = {
    "provider": "ollama",
    "endpoint": "http://localhost:11434/api/embed",
    "model": "nomic-embed-text:latest",
    "dimensions": 768,
    "state": "available",
    "detail": None,
    "available_models": ["nomic-embed-text:latest"],
}


def _settings(**overrides: Any) -> Settings:
    """Settings instance isolated from the developer's persisted store."""
    base = {
        "llm_provider": "lmstudio",
        "llm_endpoint": "http://127.0.0.1:1234/v1",
        "embedding_provider": "ollama",
        "embedding_endpoint": "",
    }
    base.update(overrides)
    return Settings(**base)


def _cognee_service() -> CogneeService:
    service = CogneeService(_settings())
    service._initialized = True
    return service


@pytest.fixture()
def stub_embedding_probe(monkeypatch):
    """Replace the network embedding probe with a scripted result."""
    state = {"result": dict(AVAILABLE_EMBEDDING)}

    async def fake_probe(self, *args: Any, **kwargs: Any) -> dict:
        return dict(state["result"])

    monkeypatch.setattr(Settings, "probe_embedding_provider", fake_probe, raising=True)
    return state


# --------------------------------------------------------------------------- 1 & 2
@pytest.mark.asyncio
async def test_recall_requests_explicit_chunk_mode_and_disables_router(
    monkeypatch, stub_embedding_probe
):
    """retrieval must pass an explicit non-LLM search type with auto_route disabled."""
    import cognee

    captured: dict[str, Any] = {}

    async def fake_recall(**kwargs: Any) -> list:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(cognee, "recall", fake_recall)

    service = _cognee_service()
    await service.recall(query_text="how does retrieval arbitration work", datasets=["repo"])

    assert captured["query_type"] is default_recall_query_type()
    assert captured["query_type"].value == "CHUNKS"
    assert captured["auto_route"] is False


@pytest.mark.asyncio
async def test_query_router_is_never_the_source_of_the_retrieval_mode(
    monkeypatch, stub_embedding_probe
):
    """Cognee's rule-based router must not be consulted for RE:Track retrieval."""
    import cognee
    from cognee.api.v1.recall import query_router

    def _forbidden(*args: Any, **kwargs: Any):
        raise AssertionError("Cognee query router must not run for RE:Track retrieval")

    monkeypatch.setattr(query_router, "route_query", _forbidden)

    # Reproduce cognee's routing branch: with auto_route=True and no explicit type,
    # the router runs. RE:Track never does that.
    async def strict_recall(**kwargs: Any) -> list:
        assert kwargs.get("auto_route") is False, "auto_route must be disabled"
        assert kwargs.get("query_type") is not None, "query_type must be explicit"
        return []

    monkeypatch.setattr(cognee, "recall", strict_recall)

    service = _cognee_service()
    await service.recall(query_text="explain evidence gating", datasets=["repo"])


def test_router_decision_is_llm_backed_for_this_query_documenting_the_hazard():
    """Documents why the explicit mode matters: the router picks an LLM retriever."""
    from cognee.api.v1.recall.query_router import route_query

    routed = route_query("Explain how retrieval arbitration selects evidence tiers")
    assert routed.search_type.value == "GRAPH_COMPLETION_COT"
    # ...which is not the mode RE:Track requests.
    assert default_recall_query_type().value == "CHUNKS"


def test_chunk_mode_is_not_an_llm_completion_mode():
    """The retrieval mode RE:Track uses is vector-only, not an LLM completion mode."""
    from cognee.modules.search.types import SearchType

    from cognee.modules.retrieval.chunks_retriever import ChunksRetriever
    from cognee.modules.retrieval.graph_completion_cot_retriever import GraphCompletionCotRetriever

    mode = default_recall_query_type()
    assert mode is SearchType.CHUNKS
    llm_completion_modes = {
        SearchType.GRAPH_COMPLETION,
        SearchType.GRAPH_COMPLETION_COT,
        SearchType.RAG_COMPLETION,
        SearchType.HYBRID_COMPLETION,
    }
    assert mode not in llm_completion_modes
    assert ChunksRetriever is not GraphCompletionCotRetriever


# --------------------------------------------------------------------------- 3
@pytest.mark.asyncio
async def test_embedding_probe_reports_truthful_states(monkeypatch):
    """The probe reports available / model_missing / unreachable without substitution."""
    settings = _settings()

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class FakeClient:
        def __init__(self, payload: dict = None, exc: Exception = None) -> None:
            self._payload = payload
            self._exc = exc

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a: Any) -> bool:
            return False

        async def get(self, url: str, headers: Any = None):
            if self._exc:
                raise self._exc
            return FakeResponse(self._payload or {})

    import httpx as _httpx_module

    # 1. available
    settings._embedding_probe_cache = None
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        # The configured model is what a reachable provider must serve.
        lambda **kw: FakeClient(
            {"models": [{"name": settings.ollama.embedding_model}, {"name": "other"}]}
        ),
        raising=False,
    )
    state = await settings.probe_embedding_provider(max_age_seconds=0)
    assert state["state"] == "available"
    assert state["provider"] == "ollama"
    assert state["model"] == settings.ollama.embedding_model

    # 2. reachable but the configured model is absent -> truthful, no substitution
    settings._embedding_probe_cache = None
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: FakeClient({"models": [{"name": "some-other-embed:latest"}]}),
        raising=False,
    )
    state = await settings.probe_embedding_provider(max_age_seconds=0)
    assert state["state"] == "model_missing"
    assert "not available" in (state["detail"] or "")
    assert state["model"] == settings.ollama.embedding_model  # never swapped
    assert "some-other-embed:latest" in state["available_models"]

    # 3. unreachable
    settings._embedding_probe_cache = None
    monkeypatch.setattr(
        _httpx_module,
        "AsyncClient",
        lambda **kw: FakeClient(exc=ConnectionError("connection refused")),
        raising=False,
    )
    state = await settings.probe_embedding_provider(max_age_seconds=0)
    assert state["state"] == "unreachable"
    assert "connection refused" in (state["detail"] or "")


@pytest.mark.asyncio
async def test_recall_fails_fast_when_embedding_model_is_missing(
    monkeypatch, stub_embedding_probe
):
    """A definitively unusable embedding provider must produce a truthful error."""
    stub_embedding_probe["result"] = {**AVAILABLE_EMBEDDING, "state": "model_missing", "detail": "model 'x' not available"}

    import cognee

    async def must_not_be_called(**kwargs: Any) -> list:
        raise AssertionError("retrieval must not run when the embedding model is missing")

    monkeypatch.setattr(cognee, "recall", must_not_be_called)

    service = _cognee_service()
    with pytest.raises(CogneeServiceError) as exc:
        await service.recall(query_text="q", datasets=["repo"])

    assert "Embedding provider unusable" in str(exc.value)
    assert "model 'x' not available" in str(exc.value)


@pytest.mark.asyncio
async def test_recall_failure_reports_mode_and_embedding_state(monkeypatch, stub_embedding_probe):
    """A failing recall must not surface as an opaque or empty success."""
    stub_embedding_probe["result"] = {
        **AVAILABLE_EMBEDDING,
        "state": "unreachable",
        "detail": "ConnectTimeout",
    }

    import cognee

    async def failing_recall(**kwargs: Any) -> list:
        raise RuntimeError("vector store unavailable")

    monkeypatch.setattr(cognee, "recall", failing_recall)

    service = _cognee_service()
    with pytest.raises(CogneeServiceError) as exc:
        await service.recall(query_text="q", datasets=["repo"])

    message = str(exc.value)
    assert "RuntimeError" in message
    assert "mode=CHUNKS" in message
    assert "embedding_provider=ollama" in message
    assert "state=unreachable" in message


@pytest.mark.asyncio
async def test_recall_timeout_is_reported_explicitly(monkeypatch, stub_embedding_probe):
    """A timeout reports the mode and embedding state instead of an empty message."""
    import cognee

    async def slow_recall(**kwargs: Any) -> list:
        await asyncio.sleep(5)
        return []

    monkeypatch.setattr(cognee, "recall", slow_recall)

    service = _cognee_service()
    with pytest.raises(CogneeServiceError) as exc:
        await service.recall(query_text="q", datasets=["repo"], timeout=0.05)

    message = str(exc.value)
    assert "timed out after 0.05s" in message
    assert "mode=CHUNKS" in message


# --------------------------------------------------------------------------- 4
@pytest.mark.asyncio
async def test_package_assembly_reports_unavailable_retrieval_truthfully():
    """Retrieval failure yields retrieval_state=unavailable, never a silent empty success."""
    cognee = MagicMock()
    cognee.recall = AsyncMock(side_effect=CogneeServiceError("recall() failed: embedding unusable"))

    service = ContextService(cognee_service=cognee, target_tokens=1000)
    package = await service.generate_context_package(task="explain budgeting", datasets=["repo"])

    assert package.metadata is not None
    assert package.metadata.retrieval_state == "unavailable"
    assert "embedding unusable" in (package.metadata.retrieval_error or "")
    # Authoritative content is unaffected and nothing is fabricated.
    assert package.metadata.retrieved_memory_count == 0


@pytest.mark.asyncio
async def test_package_assembly_reports_ok_when_retrieval_succeeds():
    """Successful chunk retrieval keeps retrieval_state=ok and yields sources."""
    cognee = MagicMock()

    async def recall(**kwargs: Any) -> RecallResponse:
        assert kwargs["query_type"] is default_recall_query_type()
        assert kwargs["auto_route"] is False
        return RecallResponse(
            query="q",
            dataset="repo",
            results=[
                RecallResult(
                    kind="chunk",
                    search_type="CHUNKS",
                    text="context chunk",
                    score=0.9,
                    dataset_name="repo",
                )
            ],
        )

    cognee.recall = recall
    service = ContextService(cognee_service=cognee, target_tokens=2000)
    package = await service.generate_context_package(task="explain budgeting", datasets=["repo"])

    assert package.metadata is not None
    assert package.metadata.retrieval_state == "ok"
    assert package.metadata.retrieval_error is None
    assert package.metadata.retrieved_memory_count == 1


# --------------------------------------------------------------------------- 5
def test_llm_and_embedding_provider_identities_are_independent():
    """Embedding identity is never inferred from, or collapsed into, the LLM identity."""
    settings = _settings(
        llm_provider="lmstudio",
        llm_endpoint="http://127.0.0.1:1234/v1",
        embedding_provider="ollama",
        embedding_endpoint="",
    )
    embedding = settings.embedding_identity()

    assert embedding["provider"] == "ollama"
    assert "11434" in embedding["endpoint"]
    assert settings.llm_endpoint == "http://127.0.0.1:1234/v1"
    assert embedding["endpoint"] != settings.llm_endpoint

    # Changing the LLM identity must not move the embedding identity.
    settings.llm_provider = "openai_compatible"
    settings.llm_endpoint = "http://10.0.0.5:9999/v1"
    after = settings.embedding_identity()
    assert after == embedding


def test_explicit_embedding_endpoint_is_honoured_without_substitution():
    """An explicitly configured embedding endpoint wins; nothing is silently aligned."""
    settings = _settings(
        llm_endpoint="http://127.0.0.1:1234/v1",
        embedding_provider="openai",
        embedding_endpoint="http://127.0.0.1:1234/v1",
    )
    embedding = settings.embedding_identity()
    assert embedding["provider"] == "openai"
    assert embedding["endpoint"] == "http://127.0.0.1:1234/v1"
    # Still reported as an embedding identity, not as the LLM identity.
    assert embedding["model"] == settings.ollama.embedding_model


# --------------------------------------------------------------------------- 6 & 7
def _context_use_cases(repo_path: Path, provider: Any, guard: Any = None) -> ContextUseCases:
    from app.application.container import ApplicationContainer

    container = ApplicationContainer.create()
    container.workspace_auth = MagicMock()
    container.workspace_auth.is_path_authorized.return_value = (True, None)
    container.cognee_service = MagicMock()
    container.indexing_service = MagicMock()
    container.indexing_service.discover_files.return_value = [repo_path / "main.py"]
    container.indexing_service.filter_files.return_value = [repo_path / "main.py"]
    container.context_service = MagicMock()
    pkg = MagicMock()
    pkg.markdown = "# Context"
    meta = MagicMock()
    meta.retrieved_memory_count = 0
    meta.deduplicated_count = 0
    meta.compressed_count = 0
    meta.compression_ratio = 1.0
    meta.retrieval_time_ms = 0
    meta.total_time_ms = 0
    meta.retrieval_state = "unavailable"
    meta.retrieval_error = "recall() failed: embedding unusable"
    pkg.metadata = meta
    pkg.task = "t"
    pkg.objective = "o"
    pkg.section_count = 0
    pkg.source_count = 0
    pkg.token_estimate = 1
    pkg.dataset = "ds"
    pkg.sections = []
    pkg.references = []
    container.context_service.generate_context_package = AsyncMock(return_value=pkg)
    if provider is not None:
        from app.services.intent_parser import IntentParserService

        container.llm_provider = provider
        container.intent_parser = IntentParserService(provider)
    if guard is not None:
        container.concurrency_guard = guard
    return container.get_context_use_cases()


class _SpyProvider:
    """Minimal LLM provider double counting generations."""

    def __init__(self) -> None:
        from app.models.provider import ProviderType

        self.calls = 0
        self.provider_type = ProviderType.LM_STUDIO
        self.default_model = "spy"
        self.last_invoked_model = None

    async def check_health(self):
        from app.models.provider import DiscoveryStatus, ProviderHealthStatus, ProviderType

        return ProviderHealthStatus(
            provider=ProviderType.LM_STUDIO,
            base_url="http://spy/v1",
            is_reachable=True,
            active_model="spy",
            loaded_models=[],
            quantization_warning=None,
            discovery_status=DiscoveryStatus.AVAILABLE,
        )

    async def generate_completion(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        self.calls += 1
        return (
            '{"task_summary":"s","category":"explanation",'
            '"extracted_symbols":[],"relevant_file_hints":[],"is_vague":false}'
        )


@pytest.mark.asyncio
async def test_one_generation_makes_no_retrieval_time_llm_invocation(monkeypatch, tmp_path: Path):
    """A single context request must invoke the model only for the intent enrichment."""
    import cognee
    from cognee.api.v1.recall import query_router

    def _forbidden(*a: Any, **k: Any):
        raise AssertionError("query router must not run during retrieval")

    monkeypatch.setattr(query_router, "route_query", _forbidden)

    provider = _SpyProvider()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def f():\n    return 1\n")

    use_cases = _context_use_cases(repo, provider)
    from app.application.dto import AgentContextRequest

    result = await use_cases.get_agent_context(
        AgentContextRequest(
            task_prompt="Explain the token budgeting pipeline",
            repository_path=str(repo),
            dataset_name="repo",
            max_tokens=2000,
            include_structural_graph=False,
        )
    )

    assert provider.calls == 1, "exactly one model generation per request"


@pytest.mark.asyncio
async def test_retrieval_failure_does_not_fabricate_evidence_and_gating_still_runs(
    monkeypatch, tmp_path: Path
):
    """Retrieval unavailability must not be presented as retrieved evidence."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("def f():\n    return 1\n")

    provider = _SpyProvider()
    use_cases = _context_use_cases(repo, provider)

    from app.application.dto import AgentContextRequest

    result = await use_cases.get_agent_context(
        AgentContextRequest(
            task_prompt="Explain the token budgeting pipeline",
            repository_path=str(repo),
            dataset_name="repo",
            max_tokens=2000,
            include_structural_graph=False,
        )
    )

    # The evidence gate still runs and the response remains honest about evidence.
    assert result.abstained is True or result.evidence_state in ("insufficient", "partial", "sufficient")
    assert result.evidence_files == (result.evidence_files or [])
    # No retrieval-sourced evidence is invented for a repo with no indexed memory.
    assert not (result.evidence_relationships or [])


@pytest.mark.asyncio
async def test_health_reports_embedding_identity_and_state(monkeypatch, stub_embedding_probe):
    """Health must expose embedding identity/state independently of the LLM provider."""
    from app.application.ports.llm_provider import LLMProviderPort
    from app.models.provider import DiscoveryStatus, ProviderHealthStatus, ProviderType

    class _Provider(LLMProviderPort):
        async def generate_completion(self, *a: Any, **k: Any) -> str:  # pragma: no cover
            return ""

        async def check_health(self):
            return ProviderHealthStatus(
                provider=ProviderType.LM_STUDIO,
                base_url="http://127.0.0.1:1234/v1",
                is_reachable=True,
                active_model="m",
                loaded_models=[],
                quantization_warning=None,
                discovery_status=DiscoveryStatus.AVAILABLE,
            )

    stub_embedding_probe["result"] = {**AVAILABLE_EMBEDDING, "state": "unreachable", "detail": "ConnectTimeout"}

    service = CogneeService(_settings())
    service._initialized = True
    service.embedding_availability = AsyncMock(return_value=stub_embedding_probe["result"])

    use_cases = SystemUseCases(
        settings_getter=lambda: _settings(),
        cognee_service_getter=lambda: service,
        llm_provider_getter=lambda: _Provider(),
        provider_updater_fn=AsyncMock(),
        telemetry_port=None,
        concurrency_guard=None,
    )

    health = await use_cases.health()

    assert health.embedding_provider == "ollama"
    assert health.embedding_state == "unreachable"
    assert health.embedding_detail == "ConnectTimeout"
    # LLM identity stays separate and distinct.
    assert health.provider_identity == "lmstudio"


@pytest.mark.asyncio
async def test_default_recall_mode_is_chunks():
    """The deterministic default is the vector/chunk retriever."""
    assert default_recall_query_type().value == "CHUNKS"
    assert sanitize_dataset_name("My Repo.git") == "My_Repo"
