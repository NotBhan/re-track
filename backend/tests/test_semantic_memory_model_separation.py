"""Regression tests for the dedicated semantic-memory extraction model contract.

Pins the third-identity contract introduced for the semantic-memory stage:

1. Interactive inference, embeddings, and semantic-memory extraction are three
   independent identities that are never inferred from one another.
2. A missing extraction model is an explicit unavailable state; the interactive
   model is never substituted and no inference occurs.
3. A configured-but-unserved extraction model reports an explicit unavailable
   state instead of a generic generation failure.
4. Extraction output parses deterministically; malformed or truncated reasoning
   output never produces a persisted record.
5. One cognification cycle performs exactly one extraction call and triggers no
   hidden Cognee ``cognify``/``remember`` LLM pipeline.
6. Retrieval remains vector/chunk retrieval and never invokes the extraction model.
"""

import json
from pathlib import Path
from typing import Any, Optional

import pytest

from app.application.container import ApplicationContainer
from app.config.settings import OllamaConfig, Settings
from app.models.provider import ProviderType
from app.services.cognee_service import CogneeService, default_recall_query_type
from app.services.llm_provider_service import ModelNotAvailableError
from app.services.manifest_service import FileFingerprint, IndexDelta, RepositoryManifest
from app.services.semantic_memory_generator import (
    SemanticMemoryGenerator,
    extract_memories_from_response,
)
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository


class RecordingMemoryProvider:
    """Dedicated semantic-memory provider test double that records every call."""

    def __init__(
        self,
        response_text: str = "",
        provider_type: ProviderType = ProviderType.LM_STUDIO,
        default_model: str = "phi-4-mini-instruct",
        raise_error: Optional[Exception] = None,
        base_url: str = "http://127.0.0.1:1234/v1",
    ) -> None:
        self.response_text = response_text
        self.provider_type = provider_type
        self.default_model = default_model
        self.base_url = base_url
        self.raise_error = raise_error
        self.call_count = 0
        self.last_model: Optional[str] = None
        self.last_prompt: Optional[str] = None

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.call_count += 1
        self.last_model = model
        self.last_prompt = prompt
        if self.raise_error:
            raise self.raise_error
        return self.response_text

    async def check_health(self) -> Any:  # pragma: no cover - unused by generator
        return None

    async def list_models(self) -> list[Any]:  # pragma: no cover
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        return None


class RecordingInteractiveProvider(RecordingMemoryProvider):
    """Interactive inference provider double; must never be used for extraction."""


class RecordingCogneeService:
    """CogneeService double recording ingestion without performing extraction."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.add_calls: list[dict[str, Any]] = []
        self.cognify_calls: list[Any] = []
        self.remember_calls: list[Any] = []
        self.recall_calls: list[dict[str, Any]] = []
        self._initialized = True

    async def add(self, data: Any, dataset_name: str = "default", **kwargs: Any) -> Any:
        if self.should_fail:
            raise RuntimeError("storage unavailable")
        self.add_calls.append({"data": data, "dataset_name": dataset_name})
        return {"dataset_name": dataset_name, "items_sent": 1}

    async def cognify(self, dataset_name: Optional[str] = None) -> dict[str, Any]:
        self.cognify_calls.append(dataset_name)
        return {"success": True}

    async def remember(self, *args: Any, **kwargs: Any) -> Any:
        self.remember_calls.append(kwargs)
        return {"items_sent": 1}

    async def recall(self, *args: Any, **kwargs: Any) -> Any:
        self.recall_calls.append(kwargs)
        raise AssertionError("retrieval must not run in this test")


def _make_manifest(
    dataset_name: str = "test_repo",
    repo_path: str = "/workspace/test_repo",
    files: Optional[dict[str, tuple[str, list[str]]]] = None,
) -> RepositoryManifest:
    manifest = RepositoryManifest(repo_path=repo_path, dataset_name=dataset_name)
    file_specs = files or {
        "src/core.py": ("sha_core_1111", ["process_event", "CoreEngine"]),
        "src/utils.py": ("sha_utils_2222", ["format_output"]),
    }
    for path, (sha, symbols) in file_specs.items():
        manifest.files[path] = FileFingerprint(
            path=path,
            mtime=1000.0,
            size=500,
            sha256=sha,
            language="python",
            symbols=list(symbols),
        )
    manifest.compute_fingerprint()
    return manifest


def _settings(**overrides: Any) -> Settings:
    """Hermetic Settings with the semantic-memory identity fully explicit."""
    base: dict[str, Any] = {
        "semantic_memory_provider": "lmstudio",
        "semantic_memory_endpoint": "http://127.0.0.1:1234/v1",
        "semantic_memory_api_key": "lm-studio",
        "ollama": OllamaConfig(
            llm_model="unsloth/phi-4-mini-reasoning",
            memory_model="phi-4-mini-instruct",
        ),
    }
    base.update(overrides)
    return Settings(**base)


# ---------------------------------------------------------------- 1. model config
def test_extraction_model_precedence_is_dedicated_and_never_inferred():
    """Resolution order: explicit arg > model_config > configured model > dedicated provider model."""
    settings = _settings(ollama=OllamaConfig(llm_model="interactive-model", memory_model="configured-extractor"))
    provider = RecordingMemoryProvider(default_model="provider-extractor")

    generator = SemanticMemoryGenerator(memory_provider=provider, settings=settings)
    # Configured extraction model wins over the provider's own model.
    assert generator._resolve_memory_identity(None) == ("configured-extractor", None)
    # A per-call model_config outranks the configured default.
    assert generator._resolve_memory_identity({"memory_model": "call-extractor"}) == ("call-extractor", None)

    explicit = SemanticMemoryGenerator(
        memory_provider=provider, settings=settings, memory_model="explicit-extractor"
    )
    assert explicit._resolve_memory_identity({"memory_model": "call-extractor"}) == ("explicit-extractor", None)

    # The provider's own model is only used when nothing else is configured.
    bare = _settings(ollama=OllamaConfig(llm_model="interactive-model", memory_model=""))
    assert SemanticMemoryGenerator(memory_provider=provider, settings=bare)._resolve_memory_identity(None) == (
        "provider-extractor",
        None,
    )

    # Nothing configured anywhere -> explicit unavailable, interactive model ignored.
    none_provider = RecordingMemoryProvider(default_model="")
    assert SemanticMemoryGenerator(
        memory_provider=none_provider, settings=bare
    )._resolve_memory_identity(None) == (None, "no_semantic_memory_model_configured")


def test_extraction_uses_the_dedicated_model_not_the_interactive_model():
    provider = RecordingMemoryProvider(default_model="provider-extractor")
    interactive = RecordingInteractiveProvider(default_model="unsloth/phi-4-mini-reasoning")
    settings = _settings()
    generator = SemanticMemoryGenerator(memory_provider=provider, settings=settings)

    model, _ = generator._resolve_memory_identity(None)
    assert model == "phi-4-mini-instruct"
    assert model != interactive.default_model
    assert model != settings.ollama.llm_model


# --------------------------------------------------------- 2. container identity
def test_container_builds_a_dedicated_memory_provider_for_the_configured_identity():
    container = ApplicationContainer(settings=_settings())
    provider = container._build_memory_provider()

    assert provider is not None
    assert provider.default_model == "phi-4-mini-instruct"
    assert provider.base_url == "http://127.0.0.1:1234/v1"
    assert provider.provider_type == ProviderType.LM_STUDIO
    # Independent of the interactive identity.
    assert provider.default_model != "unsloth/phi-4-mini-reasoning"


def test_container_reports_unavailable_when_the_extraction_identity_is_incomplete():
    """A missing endpoint or a missing model yields no provider: never a borrowed one."""
    no_model = ApplicationContainer(
        settings=_settings(ollama=OllamaConfig(llm_model="interactive", memory_model=""))
    )
    assert no_model._build_memory_provider() is None

    no_endpoint = ApplicationContainer(
        settings=_settings(semantic_memory_provider="", semantic_memory_endpoint="")
    )
    assert no_endpoint._build_memory_provider() is None


def test_identities_do_not_cross_contaminate():
    settings = _settings(
        llm_provider="lmstudio",
        llm_endpoint="http://127.0.0.1:1234/v1",
        embedding_provider="openai_compatible",
        embedding_endpoint="http://127.0.0.1:1234/v1",
        semantic_memory_provider="openai_compatible",
        semantic_memory_endpoint="http://127.0.0.1:9999/v1",
    )
    # Changing the semantic-memory endpoint moves neither the LLM nor the embedding identity.
    assert settings.llm_endpoint == "http://127.0.0.1:1234/v1"
    assert settings.embedding_identity()["endpoint"] == "http://127.0.0.1:1234/v1"
    assert settings.semantic_memory_identity()["endpoint"] == "http://127.0.0.1:9999/v1"

    # And the reverse: changing the LLM identity does not move the extraction identity.
    settings.llm_endpoint = "http://127.0.0.1:4321/v1"
    assert settings.semantic_memory_identity()["endpoint"] == "http://127.0.0.1:9999/v1"


# --------------------------------------------------- 3. explicit unavailable state
@pytest.mark.asyncio
async def test_missing_extraction_model_is_explicitly_unavailable_with_zero_inference(tmp_path: Path):
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem.json")
    interactive = RecordingInteractiveProvider(
        response_text='{"memories": []}', default_model="unsloth/phi-4-mini-reasoning"
    )
    settings = _settings(ollama=OllamaConfig(llm_model="unsloth/phi-4-mini-reasoning", memory_model=""))

    generator = SemanticMemoryGenerator(
        memory_provider=None, repository=repo, settings=settings
    )
    result = await generator.generate_semantic_memory("test_repo", manifest=manifest)

    assert result.success is False
    assert result.status == "not_configured"
    assert result.telemetry.inference_status == "not_configured"
    assert result.telemetry.model_invoked is False
    assert result.telemetry.fallback_used is False
    assert interactive.call_count == 0
    assert repo.load_all() == []


@pytest.mark.asyncio
async def test_unserved_extraction_model_is_reported_as_model_unavailable(tmp_path: Path):
    """A configured but unserved extraction model is unavailable, not a generation failure."""
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem.json")
    provider = RecordingMemoryProvider(
        raise_error=ModelNotAvailableError("model 'phi-4-mini-instruct' is not available"),
        default_model="phi-4-mini-instruct",
    )
    generator = SemanticMemoryGenerator(memory_provider=provider, repository=repo, settings=_settings())

    result = await generator.generate_semantic_memory("test_repo", manifest=manifest)

    assert result.success is False
    assert result.status == "model_unavailable"
    assert result.status != "generation_failed"
    assert result.telemetry.inference_status == "model_unavailable"
    assert result.telemetry.model_name == "phi-4-mini-instruct"
    assert result.telemetry.provider_endpoint == "http://127.0.0.1:1234/v1"
    assert any("memory_model_unavailable" in r for r in result.telemetry.rejection_reasons)
    assert repo.load_all() == []


# -------------------------------------------------- 4. deterministic extraction output
def test_malformed_and_truncated_output_parses_to_no_memories():
    assert extract_memories_from_response("") == []
    assert extract_memories_from_response("   ") == []
    assert extract_memories_from_response("not json at all") == []
    assert extract_memories_from_response('{"memories": "not-a-list"}') == []
    assert extract_memories_from_response('{"memories": [1, 2, "x"]}') == []
    # A reasoning model that ran out of budget mid-reasoning.
    assert extract_memories_from_response("<think>Let me consider src/core.py and") == []
    # An unclosed reasoning block followed by no JSON.
    assert extract_memories_from_response("<think>reasoning...\nstill reasoning") == []
    # A truncated JSON object is rejected rather than repaired.
    assert extract_memories_from_response('{"memories": [{"semantic_text": "x"') == []


def test_valid_output_parses_from_json_fence_and_bare_object():
    payload = {"memories": [{"semantic_text": "t", "source_files": ["src/core.py"], "source_symbols": ["process_event"]}]}
    assert extract_memories_from_response(json.dumps(payload)) == payload["memories"]
    assert extract_memories_from_response(f"```json\n{json.dumps(payload)}\n```") == payload["memories"]
    assert extract_memories_from_response(
        f"<think>internal</think>\n{json.dumps(payload)}"
    ) == payload["memories"]
    assert extract_memories_from_response(json.dumps(payload["memories"])) == payload["memories"]


@pytest.mark.asyncio
async def test_invalid_extraction_output_produces_no_persisted_records(tmp_path: Path):
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem.json")
    provider = RecordingMemoryProvider(response_text="<think>truncated reasoning only")
    generator = SemanticMemoryGenerator(memory_provider=provider, repository=repo, settings=_settings())

    result = await generator.generate_semantic_memory("test_repo", manifest=manifest)

    assert result.success is False
    assert result.status == "no_valid_memories"
    assert result.telemetry.model_invoked is True
    assert result.telemetry.llm_invocation_count == 1
    assert "empty_or_malformed_llm_json" in result.telemetry.rejection_reasons
    assert repo.load_all() == []


# ------------------------------------------- 5. successful extraction + provenance
@pytest.mark.asyncio
async def test_successful_extraction_persists_records_with_full_provenance(tmp_path: Path):
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem.json")
    provider = RecordingMemoryProvider(
        response_text=json.dumps(
            {
                "memories": [
                    {
                        "semantic_text": "CoreEngine processes events through process_event.",
                        "source_files": ["src/core.py"],
                        "source_symbols": ["CoreEngine", "process_event"],
                        "relationship_kind": "behavior_summary",
                    }
                ]
            }
        )
    )
    generator = SemanticMemoryGenerator(memory_provider=provider, repository=repo, settings=_settings())

    result = await generator.generate_semantic_memory("test_repo", manifest=manifest)

    assert result.success is True
    assert result.status == "success"
    assert provider.last_model == "phi-4-mini-instruct"
    assert result.telemetry.persisted_count == 1

    persisted = repo.get_by_repository("test_repo", manifest=manifest)
    assert len(persisted) == 1
    rec = persisted[0]
    assert rec.source_files == ["src/core.py"]
    assert rec.source_symbols == ["CoreEngine", "process_event"]
    # SHA-256 provenance is authoritative, taken from the manifest, not the model.
    assert rec.source_sha256 == ["sha_core_1111"]
    assert rec.repository_fingerprint == manifest.repo_fingerprint
    assert rec.is_derived is True
    assert rec.is_authoritative is False
    assert rec.evidence_status == "derived_projection"
    assert rec.generated_by == "cognee_pipeline"


@pytest.mark.asyncio
async def test_semantic_records_remain_repository_isolated(tmp_path: Path):
    store = tmp_path / "sem.json"
    repo = JsonSemanticMemoryRepository(store_path=store)
    manifest_a = _make_manifest(dataset_name="repo_a", repo_path="/workspace/a")
    manifest_b = _make_manifest(dataset_name="repo_b", repo_path="/workspace/b")

    provider = RecordingMemoryProvider(
        response_text=json.dumps(
            {
                "memories": [
                    {
                        "semantic_text": "Repo A behaviour",
                        "source_files": ["src/core.py"],
                        "source_symbols": ["process_event"],
                    }
                ]
            }
        )
    )
    generator = SemanticMemoryGenerator(memory_provider=provider, repository=repo, settings=_settings())
    await generator.generate_semantic_memory("repo_a", manifest=manifest_a)

    assert len(repo.get_by_repository("repo_a", manifest=manifest_a)) == 1
    assert repo.get_by_repository("repo_b", manifest=manifest_b) == []


# ---------------------------------------------- 6. exactly one extraction, no hidden LLM
@pytest.mark.asyncio
async def test_cognification_cycle_makes_exactly_one_extraction_call(tmp_path: Path):
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem.json")
    provider = RecordingMemoryProvider(
        response_text=json.dumps(
            {
                "memories": [
                    {
                        "semantic_text": "Core behaviour",
                        "source_files": ["src/core.py"],
                        "source_symbols": ["process_event"],
                    }
                ]
            }
        )
    )
    cognee = RecordingCogneeService()
    generator = SemanticMemoryGenerator(memory_provider=provider, repository=repo, settings=_settings())

    result = await generator.cognify_repository(
        "test_repo", manifest=manifest, cognee_service=cognee
    )

    assert result.success is True
    assert provider.call_count == 1
    assert result.telemetry.llm_invocation_count == 1
    # Ingestion happens through add() only; no second extraction pipeline is triggered.
    assert len(cognee.add_calls) == 1
    assert cognee.cognify_calls == []
    assert cognee.remember_calls == []


@pytest.mark.asyncio
async def test_noop_and_deletion_only_cycles_never_invoke_the_extraction_model(tmp_path: Path):
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem.json")
    provider = RecordingMemoryProvider(response_text='{"memories": []}')
    generator = SemanticMemoryGenerator(memory_provider=provider, repository=repo, settings=_settings())

    noop_delta = IndexDelta(added=[], modified=[], deleted=[], unchanged=[], renamed=[])
    noop = await generator.cognify_repository(
        "test_repo", manifest=manifest, delta=noop_delta, existing_manifest=manifest
    )
    assert noop.status == "noop"
    assert noop.telemetry.llm_invocation_count == 0
    assert provider.call_count == 0

    deletion_delta = IndexDelta(added=[], modified=[], deleted=["src/utils.py"], unchanged=[], renamed=[])
    deletion_manifest = _make_manifest(files={"src/core.py": ("sha_core_1111", ["process_event", "CoreEngine"])})
    deletion = await generator.cognify_repository(
        "test_repo",
        manifest=deletion_manifest,
        delta=deletion_delta,
        existing_manifest=manifest,
    )
    assert deletion.success is True
    assert deletion.telemetry.llm_invocation_count == 0
    assert provider.call_count == 0


def test_cognee_add_never_triggers_a_cognify_or_remember_llm_pipeline(monkeypatch):
    """`add()` must ingest only; a hidden cognify/remember pass would be an extra LLM call."""
    import cognee

    calls: list[str] = []

    async def fake_add(**kwargs: Any) -> Any:
        calls.append("add")
        return {"ok": True}

    async def fake_cognify(**kwargs: Any) -> Any:
        calls.append("cognify")
        raise AssertionError("add() must not trigger a cognify extraction pass")

    async def fake_remember(**kwargs: Any) -> Any:
        calls.append("remember")
        raise AssertionError("add() must not trigger a remember extraction pass")

    monkeypatch.setattr(cognee, "add", fake_add, raising=False)
    monkeypatch.setattr(cognee, "cognify", fake_cognify, raising=False)
    monkeypatch.setattr(cognee, "remember", fake_remember, raising=False)

    service = CogneeService(settings=_settings())
    service._initialized = True

    import asyncio

    asyncio.run(service.add(data="- [src/core.py] summary", dataset_name="test_repo"))
    assert calls == ["add"]


@pytest.mark.asyncio
async def test_retrieval_remains_chunks_and_never_invokes_the_extraction_model(monkeypatch, tmp_path: Path):
    """Retrieval is vector/chunk retrieval: no auto-routing, no additional extraction call."""
    import cognee

    captured: dict[str, Any] = {}

    async def fake_recall(**kwargs: Any) -> list:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(cognee, "recall", fake_recall)

    settings = _settings()
    service = CogneeService(settings=settings)
    service._initialized = True

    async def fake_probe(*args: Any, **kwargs: Any) -> dict:
        return {
            "provider": "openai_compatible",
            "endpoint": "http://127.0.0.1:1234/v1",
            "model": "text-embedding-nomic-embed-text-v1.5",
            "dimensions": 768,
            "state": "available",
            "detail": None,
            "available_models": [],
        }

    monkeypatch.setattr(Settings, "probe_embedding_provider", fake_probe, raising=True)

    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem.json")
    provider = RecordingMemoryProvider(
        response_text=json.dumps(
            {
                "memories": [
                    {
                        "semantic_text": "Core behaviour",
                        "source_files": ["src/core.py"],
                        "source_symbols": ["process_event"],
                    }
                ]
            }
        )
    )
    generator = SemanticMemoryGenerator(memory_provider=provider, repository=repo, settings=settings)
    await generator.cognify_repository("test_repo", manifest=manifest)
    assert provider.call_count == 1

    # Retrieval afterwards must not perform a second extraction pass.
    await service.retrieve_semantic_memory(
        repository_id="test_repo",
        query_text="how does core work",
        manifest=manifest,
        repository_store=repo,
    )

    assert captured["query_type"] is default_recall_query_type()
    assert captured["query_type"].value == "CHUNKS"
    assert captured["auto_route"] is False
    assert provider.call_count == 1
