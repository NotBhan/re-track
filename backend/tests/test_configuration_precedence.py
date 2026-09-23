"""Regression tests for the deterministic provider-configuration precedence contract.

Background (measured on a real runtime before the fix):

* ``backend/.env`` carried stale embedding/provider endpoint values
  (``EMBEDDING_PROVIDER=openai`` pointing at an unreachable remote host).
* ``Settings.apply_to_environment()`` wrote provider identity into ``os.environ``
  for Cognee compatibility.
* Because ``Settings`` is a ``BaseSettings`` that reads ``os.environ`` on
  construction, a *later* ``Settings`` instance silently inherited the values a
  *previous* instance had written. Embedding availability therefore depended on
  what an earlier component had done at runtime.

These tests pin the single documented precedence model:

    1. explicit constructor arguments
    2. operator environment variables (never values RE:Track wrote itself)
    3. persisted settings (``~/.retrack/settings.json``)
    4. ``backend/.env``
    5. field defaults

and that LLM and embedding provider identities stay independent, that
unavailability is reported truthfully, and that no provider/model substitution
or silent fallback occurs.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import pytest

from app.config.settings import (
    CONFIGURATION_PRECEDENCE,
    MANAGED_ENVIRONMENT_KEYS,
    OllamaConfig,
    Settings,
    dotenv_layer,
    operator_environment,
)
from app.models.errors import CogneeServiceError
from app.services.cognee_service import CogneeService, default_recall_query_type

EMBEDDING_KEYS = ("EMBEDDING_PROVIDER", "EMBEDDING_ENDPOINT", "EMBEDDING_MODEL", "EMBEDDING_API_KEY")


def _identity(settings: Settings) -> dict[str, Any]:
    return settings.embedding_identity()


# --------------------------------------------------------------------- 1. model
def test_precedence_model_is_explicit_and_documented():
    """The precedence order is declared in code, highest priority first."""
    assert Settings.configuration_precedence() == CONFIGURATION_PRECEDENCE
    assert CONFIGURATION_PRECEDENCE[0] == "explicit constructor arguments"
    assert CONFIGURATION_PRECEDENCE[1].startswith("operator environment")
    assert set(MANAGED_ENVIRONMENT_KEYS) >= set(EMBEDDING_KEYS) | {"LLM_PROVIDER", "LLM_ENDPOINT"}


# ------------------------------------------------- 2. no cross-instance leakage
def test_apply_to_environment_does_not_contaminate_later_settings():
    """A Settings instance must not leak its provider config into later instances."""
    baseline = _identity(Settings())
    baseline_llm = (Settings().llm_provider, Settings().llm_endpoint, Settings().ollama.llm_model)

    writer = Settings(
        llm_provider="openai_compatible",
        llm_endpoint="http://10.0.0.9:9999/v1",
        embedding_provider="openai_compatible",
        embedding_endpoint="http://10.0.0.9:9999/v1",
    )
    writer.apply_to_environment()

    # The write really happened (the Cognee compatibility path is intact).
    assert os.environ.get("LLM_PROVIDER") == "openai_compatible"
    assert os.environ.get("EMBEDDING_ENDPOINT") == "http://10.0.0.9:9999/v1"

    # A fresh instance must resolve to the pre-existing configuration, not the write.
    later = Settings()
    assert (later.llm_provider, later.llm_endpoint, later.ollama.llm_model) == baseline_llm
    assert _identity(later) == baseline


def test_operator_value_that_differs_from_write_is_still_an_override(monkeypatch):
    """An operator changing a managed variable after a write keeps override precedence."""
    Settings(embedding_provider="ollama", embedding_endpoint="").apply_to_environment()
    assert operator_environment().get("EMBEDDING_PROVIDER") is None  # our own write

    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compatible")
    assert operator_environment()["EMBEDDING_PROVIDER"] == "openai_compatible"

    assert Settings().embedding_provider_name() == "openai_compatible"


def test_explicit_arguments_beat_operator_environment(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "from-env")
    monkeypatch.setenv("EMBEDDING_MODEL", "env-embed-model")

    settings = Settings(
        llm_provider="explicit",
        ollama=OllamaConfig(embedding_model="explicit-embed-model"),
    )
    assert settings.llm_provider == "explicit"
    assert settings.ollama.embedding_model == "explicit-embed-model"


def test_operator_environment_beats_persisted_settings(monkeypatch, tmp_path: Path):
    """At construction time, an operator variable outranks the persisted store."""
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"llm_endpoint": "http://persisted:1/v1"}), encoding="utf-8")
    monkeypatch.setattr("app.config.settings.DEFAULT_SETTINGS_STORE_PATH", store)

    assert Settings().llm_endpoint == "http://persisted:1/v1"

    monkeypatch.setenv("LLM_ENDPOINT", "http://from-env:2/v1")
    assert Settings().llm_endpoint == "http://from-env:2/v1"


def test_reload_configuration_preserves_operator_override(monkeypatch, tmp_path: Path):
    """Reloading (as ApplicationContainer.initialize does) must not demote an override."""
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"llm_endpoint": "http://persisted:1/v1"}), encoding="utf-8")
    monkeypatch.setattr("app.config.settings.DEFAULT_SETTINGS_STORE_PATH", store)
    monkeypatch.setenv("LLM_ENDPOINT", "http://from-env:2/v1")

    settings = Settings()
    assert settings.llm_endpoint == "http://from-env:2/v1"

    settings.reload_configuration()
    assert settings.llm_endpoint == "http://from-env:2/v1"


def test_persisted_settings_beat_dotenv(monkeypatch, tmp_path: Path):
    """At construction time, the persisted store outranks backend/.env."""
    env_file = tmp_path / "custom.env"
    env_file.write_text(
        "LLM_ENDPOINT=http://dotenv:3/v1\nLLM_PROVIDER=dotenv-provider\n", encoding="utf-8"
    )
    monkeypatch.setattr("app.config.settings.DEFAULT_ENV_FILE", env_file)
    assert dotenv_layer()["LLM_ENDPOINT"] == "http://dotenv:3/v1"

    # .env alone (persisted store empty/missing) is the effective value.
    monkeypatch.setattr("app.config.settings.DEFAULT_SETTINGS_STORE_PATH", tmp_path / "absent.json")
    assert Settings().llm_endpoint == "http://dotenv:3/v1"
    assert Settings().llm_provider == "dotenv-provider"

    # Persisted settings now outrank .env.
    store = tmp_path / "settings.json"
    store.write_text(
        json.dumps({"llm_endpoint": "http://persisted:4/v1", "llm_provider": "persisted-provider"}),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.config.settings.DEFAULT_SETTINGS_STORE_PATH", store)
    resolved = Settings()
    assert resolved.llm_endpoint == "http://persisted:4/v1"
    assert resolved.llm_provider == "persisted-provider"


# ------------------------------------------------------- 3. LLM <-> embedding
def test_llm_and_embedding_configurations_do_not_cross_contaminate():
    """Changing one provider identity must not move the other, even via os.environ."""
    baseline_embedding = _identity(Settings())
    baseline_llm_fields = (Settings().llm_provider, Settings().llm_endpoint, Settings().ollama.llm_model)

    settings = Settings(
        llm_provider="lmstudio",
        llm_endpoint="http://127.0.0.1:1234/v1",
        embedding_provider="ollama",
        embedding_endpoint="",
    )
    embedding_before = _identity(settings)

    # Change the LLM identity -> embedding identity unchanged.
    settings.llm_provider = "openai_compatible"
    settings.llm_endpoint = "http://10.0.0.7:9999/v1"
    assert _identity(settings) == embedding_before

    # Change the embedding identity -> LLM identity unchanged.
    settings.embedding_provider = "openai_compatible"
    settings.embedding_endpoint = "http://10.0.0.8:9999/v1"
    assert (settings.llm_provider, settings.llm_endpoint) == ("openai_compatible", "http://10.0.0.7:9999/v1")

    # A round-trip through the process environment leaves a fresh instance clean.
    settings.apply_to_environment()
    fresh = Settings()
    assert _identity(fresh) == baseline_embedding
    assert (fresh.llm_provider, fresh.llm_endpoint, fresh.ollama.llm_model) == baseline_llm_fields


# -------------------------------------------- 4. truthful unavailability states
def test_embedding_provider_is_never_aligned_with_the_llm_provider():
    settings = Settings(
        llm_provider="lmstudio",
        llm_endpoint="http://127.0.0.1:1234/v1",
        embedding_provider="ollama",
        embedding_endpoint="",
    )
    identity = _identity(settings)
    assert identity["provider"] == "ollama"
    assert "11434" in identity["endpoint"]
    assert identity["endpoint"] != settings.llm_endpoint


def test_non_ollama_provider_without_endpoint_reports_not_configured():
    """No silent endpoint substitution for a non-Ollama embedding provider."""
    settings = Settings(
        llm_endpoint="http://127.0.0.1:1234/v1",
        embedding_provider="openai_compatible",
        embedding_endpoint="",
    )
    assert settings.resolve_embedding_endpoint() == ""

    state = asyncio.run(settings.probe_embedding_provider(max_age_seconds=0))
    assert state["state"] == "not_configured"
    assert state["endpoint"] == ""
    # The LLM endpoint was NOT borrowed.
    assert "1234" not in state["endpoint"]


def test_recall_refuses_when_embedding_not_configured(monkeypatch):
    """An unusable embedding configuration fails explicitly; cognee.recall never runs."""
    import cognee

    async def must_not_run(**kwargs: Any) -> list:
        raise AssertionError("retrieval must not run when embeddings are not configured")

    monkeypatch.setattr(cognee, "recall", must_not_run)

    settings = Settings(
        embedding_provider="openai_compatible",
        embedding_endpoint="",
        ollama=OllamaConfig(embedding_model="text-embedding-nomic-embed-text-v1.5"),
    )
    service = CogneeService(settings)
    service._initialized = True

    with pytest.raises(CogneeServiceError) as exc:
        asyncio.run(service.recall(query_text="q", datasets=["repo"]))

    assert "not_configured" in str(exc.value)


def test_model_missing_is_reported_without_substitution(monkeypatch):
    """A reachable provider lacking the configured model is truthful and non-substituting."""
    settings = Settings(
        embedding_provider="openai_compatible",
        embedding_endpoint="http://127.0.0.1:1234/v1",
        ollama=OllamaConfig(embedding_model="text-embedding-nomic-embed-text-v1.5"),
    )

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "some-other-embed"}]}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a: Any) -> bool:
            return False

        async def get(self, url: str, headers: Any = None):
            return _Resp()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client(), raising=False)

    state = asyncio.run(settings.probe_embedding_provider(max_age_seconds=0))
    assert state["state"] == "model_missing"
    assert state["model"] == "text-embedding-nomic-embed-text-v1.5"  # never swapped
    assert "some-other-embed" in state["available_models"]


def test_probe_cache_is_keyed_on_identity(monkeypatch):
    """A configuration change is never answered from a stale probe."""
    calls: list[str] = []
    settings = Settings(
        embedding_provider="openai_compatible",
        embedding_endpoint="http://127.0.0.1:1234/v1",
    )

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"id": "text-embedding-nomic-embed-text-v1.5"}]}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a: Any) -> bool:
            return False

        async def get(self, url: str, headers: Any = None):
            calls.append(url)
            return _Resp()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Client(), raising=False)

    first = asyncio.run(settings.probe_embedding_provider(max_age_seconds=60))
    assert first["state"] == "available"
    assert len(calls) == 1

    # Same identity within the cache window -> served from cache.
    asyncio.run(settings.probe_embedding_provider(max_age_seconds=60))
    assert len(calls) == 1

    # Different identity -> must re-probe, never reuse the stale answer.
    settings.embedding_endpoint = "http://127.0.0.1:1234/v1/other"
    changed = asyncio.run(settings.probe_embedding_provider(max_age_seconds=60))
    assert len(calls) == 2
    assert changed["endpoint"].endswith("/other")


# ------------------------------------------------ 5. deterministic clean startup
def test_clean_startup_is_deterministic_across_cwd(monkeypatch, tmp_path: Path):
    """.env resolves relative to the backend package, not the process cwd."""
    first = _identity(Settings())
    other_cwd = tmp_path / "elsewhere"
    other_cwd.mkdir()
    monkeypatch.chdir(other_cwd)
    second = _identity(Settings())
    assert first == second


def test_repeated_reads_and_updates_are_stable():
    """Multiple reads and an unrelated update leave provider identity stable."""
    baseline = _identity(Settings())
    baseline_llm = Settings().llm_provider

    for _ in range(3):
        settings = Settings()
        assert _identity(settings) == baseline
        assert settings.llm_provider == baseline_llm
        # An unrelated storage update must not shift provider identity.
        settings.storage.vector_db = "lancedb"
        settings.apply_to_environment()

    assert _identity(Settings()) == baseline


# ------------------------------------------------------ 6. persistence round-trip
def test_persisted_settings_roundtrip_preserves_embedding_identity(tmp_path: Path):
    store = tmp_path / "settings.json"
    original = Settings(
        llm_provider="lmstudio",
        llm_endpoint="http://127.0.0.1:1234/v1",
        embedding_provider="openai_compatible",
        embedding_endpoint="http://127.0.0.1:1234/v1",
        embedding_api_key="lm-studio",
        ollama=OllamaConfig(
            embedding_model="text-embedding-nomic-embed-text-v1.5",
            embedding_dimensions=768,
        ),
    )
    original.save_persisted_settings(store_path=store)

    raw = json.loads(store.read_text(encoding="utf-8"))
    assert raw["embedding_provider"] == "openai_compatible"
    assert raw["embedding_endpoint"] == "http://127.0.0.1:1234/v1"
    assert raw["embedding_dimensions"] == 768

    restored = Settings()
    restored.load_persisted_settings(store_path=store)
    assert _identity(restored) == _identity(original)
    assert restored.ollama.embedding_model == "text-embedding-nomic-embed-text-v1.5"


# ------------------------------------- 6b. dedicated semantic-memory stage model
def test_semantic_memory_model_follows_the_same_precedence(monkeypatch, tmp_path: Path):
    """The semantic-memory stage model is resolved, overridable, and explicit-steerable."""
    store = tmp_path / "settings.json"
    store.write_text(json.dumps({"memory_model": "persisted-memory-model"}), encoding="utf-8")
    monkeypatch.setattr("app.config.settings.DEFAULT_SETTINGS_STORE_PATH", store)

    assert Settings().ollama.memory_model == "persisted-memory-model"

    monkeypatch.setenv("SEMANTIC_MEMORY_MODEL", "env-memory-model")
    assert Settings().ollama.memory_model == "env-memory-model"

    explicit = Settings(ollama=OllamaConfig(memory_model="explicit-memory-model"))
    assert explicit.ollama.memory_model == "explicit-memory-model"


def test_semantic_memory_model_falls_back_to_inference_model_when_unset(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("app.config.settings.DEFAULT_SETTINGS_STORE_PATH", tmp_path / "absent.json")
    monkeypatch.setattr("app.config.settings.DEFAULT_ENV_FILE", tmp_path / "absent.env")

    settings = Settings(ollama=OllamaConfig(llm_model="the-inference-model"))
    assert settings.ollama.memory_model == ""

    from app.services.semantic_memory_generator import SemanticMemoryGenerator

    generator = SemanticMemoryGenerator(llm_provider=None, repository=None, settings=settings)
    model, fallback_used, fallback_reason = generator._select_model(None)
    assert model == "the-inference-model"
    assert fallback_used is True
    assert "dedicated memory model" in (fallback_reason or "")


def test_cognee_provider_mapping_keeps_structured_output_usable():
    """LM Studio maps to litellm's `lm_studio` provider, whose structured output works.

    Routing LM Studio through `openai/` makes Cognee constrain structured output
    with `response_format: json_object`, which LM Studio rejects with HTTP 400.
    """
    from cognee.infrastructure.llm.config import get_llm_config

    try:
        settings = Settings(
            llm_provider="lmstudio",
            llm_endpoint="http://127.0.0.1:1234/v1",
            ollama=OllamaConfig(llm_model="some-served-model"),
        )
        settings.configure_cognee()

        cfg = get_llm_config()
        assert cfg.llm_provider == "lm_studio"
        assert cfg.llm_model == "lm_studio/some-served-model"
        assert cfg.llm_endpoint == "http://127.0.0.1:1234/v1"

        from cognee.infrastructure.llm.structured_output_framework.litellm_native.native_adapter import (
            _supports_native_schema,
        )

        # The schema-native path (json_schema) is selected for this model.
        assert _supports_native_schema(cfg.llm_model) is True
    finally:
        get_llm_config.cache_clear()


# ------------------------------------------------- 7. retrieval contract intact
def test_deterministic_chunks_retrieval_is_unchanged(monkeypatch):
    """Retrieval still requests CHUNKS with auto_route disabled and no router call."""
    import cognee

    captured: dict[str, Any] = {}

    async def fake_recall(**kwargs: Any) -> list:
        captured.update(kwargs)
        return []

    monkeypatch.setattr(cognee, "recall", fake_recall)

    settings = Settings(
        embedding_provider="openai_compatible",
        embedding_endpoint="http://127.0.0.1:1234/v1",
    )

    async def fake_probe(self, *a: Any, **k: Any) -> dict:
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

    service = CogneeService(settings)
    service._initialized = True
    asyncio.run(service.recall(query_text="q", datasets=["repo"]))

    assert captured["query_type"] is default_recall_query_type()
    assert captured["query_type"].value == "CHUNKS"
    assert captured["auto_route"] is False


# ------------------------------------------- 8. health reports embedding alone
def test_health_reports_embedding_independently_of_llm():
    """Embedding availability is reported even when the LLM provider is unreachable."""
    from app.application.ports.llm_provider import LLMProviderPort
    from app.application.use_cases.system import SystemUseCases
    from app.models.provider import DiscoveryStatus, ProviderHealthStatus, ProviderType

    class _DownProvider(LLMProviderPort):
        async def generate_completion(self, *a: Any, **k: Any) -> str:  # pragma: no cover
            return ""

        async def check_health(self):
            return ProviderHealthStatus(
                provider=ProviderType.LM_STUDIO,
                base_url="http://127.0.0.1:1234/v1",
                is_reachable=False,
                active_model=None,
                loaded_models=[],
                quantization_warning=None,
                discovery_status=DiscoveryStatus.UNREACHABLE,
            )

    settings = Settings(
        llm_provider="lmstudio",
        embedding_provider="openai_compatible",
        embedding_endpoint="http://127.0.0.1:1234/v1",
    )

    class _Cognee:
        is_initialized = True

        async def embedding_availability(self) -> dict:
            return {
                "provider": "openai_compatible",
                "endpoint": "http://127.0.0.1:1234/v1",
                "model": "text-embedding-nomic-embed-text-v1.5",
                "dimensions": 768,
                "state": "available",
                "detail": None,
                "available_models": [],
            }

    use_cases = SystemUseCases(
        settings_getter=lambda: settings,
        cognee_service_getter=lambda: _Cognee(),
        llm_provider_getter=lambda: _DownProvider(),
        provider_updater_fn=None,
        telemetry_port=None,
        concurrency_guard=None,
    )

    health = asyncio.run(use_cases.health())
    assert health.provider_reachable is False
    assert health.engine_state == "unavailable"
    # Embedding health is independent and truthful.
    assert health.embedding_state == "available"
    assert health.embedding_provider == "openai_compatible"
