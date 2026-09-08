"""Tests for provider runtime state, active model verification, and invocation truth.

Ensures:
- Settings configuration matches runtime provider and endpoint.
- Active model matches actual invocation model.
- Unverified configured model does not become active model.
- Persisted configurations survive restart without resetting to Ollama defaults.
- Failing model responses report actual provider and model.
- Invalid structured output is distinguished from provider unreachable failure.
- Zero HTTP inference requests sent when active model is null/unverified.
- Provider cannot silently substitute another model.
- Model mismatch is reported truthfully as model_mismatch.
- LM Studio reproduction scenario correctly yields degraded state and zero HTTP inference requests.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.application.container import ApplicationContainer
from app.application.dto.context import AgentContextRequest
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings
from app.models.provider import ProviderType
from app.services.intent_parser import IntentParserService
from app.services.llm_provider_service import (
    LLMProviderService,
    ModelNotAvailableError,
    ModelMismatchError,
)


class TestProviderRuntimeTruth:
    """Test backend-authoritative provider and model runtime truth."""

    @pytest.mark.asyncio
    async def test_provider_configuration_matches_runtime_provider(self):
        """Updating provider reloads LLMProviderService with authoritative runtime values."""
        container = ApplicationContainer()
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "settings.json"
            settings = Settings()
            settings.settings_store_path = store_path
            container.settings = settings

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": [{"id": "phi-4-mini"}]
            }

            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_resp
                res = await container.update_provider(
                    provider="lmstudio",
                    base_url="http://127.0.0.1:1234/v1",
                    model="phi-4-mini",
                    api_key="local",
                )
                assert res["success"] is True
                assert container.llm_provider.provider_type == ProviderType.LM_STUDIO
                assert container.llm_provider.base_url == "http://127.0.0.1:1234/v1"
                assert container.llm_provider.default_model == "phi-4-mini"
                assert container.settings.llm_provider == "lmstudio"
                assert container.settings.llm_endpoint == "http://127.0.0.1:1234/v1"
                assert container.settings.ollama.llm_model == "phi-4-mini"

    @pytest.mark.asyncio
    async def test_active_model_matches_actual_invocation_model(self):
        """When provider executes completion, last_invoked_model records the actual returned model."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="microsoft/phi-4-mini-reasoning",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning"]
        provider.verified_active_model = "microsoft/phi-4-mini-reasoning"
        provider._health_checked = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "microsoft/phi-4-mini-reasoning",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{"category": "feature", "intent": "add test", "confidence": 0.95, "target_files": [], "keywords": ["test"]}',
                    },
                    "finish_reason": "stop",
                }
            ],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            content = await provider.generate_completion(
                prompt="test prompt",
                model="microsoft/phi-4-mini-reasoning",
            )
            assert content is not None
            assert provider.last_invoked_model == "microsoft/phi-4-mini-reasoning"

            # Verify IntentParserService picks up the actual invoked model
            parser = IntentParserService(provider)
            record = await parser.parse_intent("implement feature X")
            assert record.model_invoked is True
            assert record.model_name == "microsoft/phi-4-mini-reasoning"
            assert record.provider_identity == "lmstudio"

    @pytest.mark.asyncio
    async def test_unverified_configured_model_does_not_become_active_model(self):
        """Configured model not found on reachable provider must NOT become active_model."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="qwen2.5-coder:7b",
        )

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"id": "microsoft/phi-4-mini-reasoning"},
            ]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            health = await provider.check_health()
            assert health.is_reachable is True
            # Configured model is qwen2.5-coder:7b, but provider only has phi-4-mini-reasoning
            assert health.active_model is None
            assert health.quantization_warning is not None
            assert "qwen2.5-coder:7b" in health.quantization_warning

            # Check system health representation
            settings = Settings()
            settings.llm_provider = "lmstudio"
            settings.llm_endpoint = "http://127.0.0.1:1234/v1"
            settings.ollama.llm_model = "qwen2.5-coder:7b"

            sys_use_cases = SystemUseCases(
                settings_getter=lambda: settings,
                cognee_service_getter=lambda: MagicMock(is_initialized=True),
                llm_provider_getter=lambda: provider,
                provider_updater_fn=AsyncMock(),
            )
            h = await sys_use_cases.health()
            assert h.configured_model == "qwen2.5-coder:7b"
            assert h.active_model is None
            assert h.active_model_state == "model_not_found"
            assert h.engine_state == "degraded"

            s = await sys_use_cases.get_backend_status()
            assert s.configured_model == "qwen2.5-coder:7b"
            assert s.active_model is None
            assert s.active_model_state == "model_not_found"
            assert s.engine_state == "degraded"

    @pytest.mark.asyncio
    async def test_failing_model_response_reports_actual_provider_and_model(self):
        """When model output fails schema validation, report actual provider and model in telemetry."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="microsoft/phi-4-mini-reasoning",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning"]
        provider.verified_active_model = "microsoft/phi-4-mini-reasoning"
        provider._health_checked = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "microsoft/phi-4-mini-reasoning",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "<think>Thinking about code...",  # Truncated reasoning token stream
                    },
                    "finish_reason": "length",
                }
            ],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            parser = IntentParserService(provider)
            record = await parser.parse_intent("some prompt")

            assert record.model_invoked is False
            assert record.provider_identity == "lmstudio"
            assert record.model_name == "microsoft/phi-4-mini-reasoning"
            assert record.inference_status == "failed"
            assert record.fallback_used is True
            assert record.fallback_reason == "Model response was not valid JSON schema"

    @pytest.mark.asyncio
    async def test_invalid_structured_output_is_distinguished_from_provider_failure(self):
        """Provider connection failure is clearly distinguished from schema validation failure."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="microsoft/phi-4-mini-reasoning",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning"]
        provider.verified_active_model = "microsoft/phi-4-mini-reasoning"
        provider._health_checked = True

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")
            parser = IntentParserService(provider)
            record = await parser.parse_intent("some prompt")

            assert record.model_invoked is False
            assert record.provider_identity == "lmstudio"
            assert record.inference_status == "failed"
            assert record.fallback_used is True
            assert "ConnectError" in (record.fallback_reason or "") or "Connection" in (record.fallback_reason or "")
            assert record.fallback_reason != "Model response was not valid JSON schema"

    def test_persisted_lmstudio_configuration_survives_restart(self):
        """LM Studio settings saved to disk survive process restart without reset to Ollama defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "settings.json"
            s1 = Settings()
            s1.settings_store_path = store_path
            s1.llm_provider = "lmstudio"
            s1.llm_endpoint = "http://127.0.0.1:1234/v1"
            s1.ollama.llm_model = "microsoft/phi-4-mini-reasoning"
            s1.save_persisted_settings(store_path=store_path)

            # Fresh instance simulating backend restart
            s2 = Settings()
            s2.settings_store_path = store_path
            s2.load_persisted_settings(store_path=store_path)

            assert s2.llm_provider == "lmstudio"
            assert s2.llm_endpoint == "http://127.0.0.1:1234/v1"
            assert s2.ollama.llm_model == "microsoft/phi-4-mini-reasoning"

    def test_persisted_ollama_configuration_survives_restart(self):
        """Ollama settings saved to disk survive restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "settings.json"
            s1 = Settings()
            s1.settings_store_path = store_path
            s1.llm_provider = "ollama"
            s1.llm_endpoint = "http://127.0.0.1:11434/v1"
            s1.ollama.llm_model = "qwen2.5-coder:7b"
            s1.save_persisted_settings(store_path=store_path)

            s2 = Settings()
            s2.settings_store_path = store_path
            s2.load_persisted_settings(store_path=store_path)

            assert s2.llm_provider == "ollama"
            assert s2.llm_endpoint == "http://127.0.0.1:11434/v1"
            assert s2.ollama.llm_model == "qwen2.5-coder:7b"

    # --- New Invariant Tests ---

    @pytest.mark.asyncio
    async def test_unverified_configured_model_cannot_be_invoked(self):
        """If active_model is null/unverified, calling generate_completion raises ModelNotAvailableError without HTTP call."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="qwen2.5-coder:7b",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning"]
        provider.verified_active_model = None
        provider._health_checked = True

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            with pytest.raises(ModelNotAvailableError) as exc_info:
                await provider.generate_completion(prompt="hello", model="qwen2.5-coder:7b")
            assert "qwen2.5-coder:7b" in str(exc_info.value)
            assert mock_post.call_count == 0

    @pytest.mark.asyncio
    async def test_model_not_found_produces_zero_http_inference_requests(self):
        """When configured model is unverified/unavailable, IntentParser produces zero HTTP inference requests."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="qwen2.5-coder:7b",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning"]
        provider.verified_active_model = None
        provider._health_checked = True

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            parser = IntentParserService(provider)
            record = await parser.parse_intent("any prompt")
            assert mock_post.call_count == 0
            assert record.model_invoked is False
            assert record.inference_status == "model_not_available"
            assert record.fallback_used is True
            assert record.model_name is None

    @pytest.mark.asyncio
    async def test_provider_cannot_silently_substitute_model(self):
        """Provider cannot silently execute a different model than requested."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="microsoft/phi-4-mini-reasoning",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning", "different-model"]
        provider.verified_active_model = "microsoft/phi-4-mini-reasoning"
        provider._health_checked = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "different-model",
            "choices": [{"message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            with pytest.raises(ModelMismatchError) as exc_info:
                await provider.generate_completion(prompt="hi", model="microsoft/phi-4-mini-reasoning")
            assert "different-model" in str(exc_info.value)
            assert provider.last_invoked_model == "different-model"

    @pytest.mark.asyncio
    async def test_requested_model_matches_response_model(self):
        """When response model matches requested model, completion succeeds and records last_invoked_model."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="microsoft/phi-4-mini-reasoning",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning"]
        provider.verified_active_model = "microsoft/phi-4-mini-reasoning"
        provider._health_checked = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "microsoft/phi-4-mini-reasoning",
            "choices": [{"message": {"role": "assistant", "content": '{"intent": "test"}'}, "finish_reason": "stop"}],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            content = await provider.generate_completion(prompt="hi", model="microsoft/phi-4-mini-reasoning")
            assert content == '{"intent": "test"}'
            assert provider.last_invoked_model == "microsoft/phi-4-mini-reasoning"

    @pytest.mark.asyncio
    async def test_model_mismatch_is_reported_truthfully(self):
        """IntentParser reports inference_status='model_mismatch' and preserves the substituted model name."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="microsoft/phi-4-mini-reasoning",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning", "substituted-model"]
        provider.verified_active_model = "microsoft/phi-4-mini-reasoning"
        provider._health_checked = True

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "substituted-model",
            "choices": [{"message": {"role": "assistant", "content": "{}"}, "finish_reason": "stop"}],
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_resp
            parser = IntentParserService(provider)
            record = await parser.parse_intent("any prompt")
            assert record.model_invoked is False
            assert record.inference_status == "model_mismatch"
            assert record.model_name == "substituted-model"
            assert record.fallback_used is True
            assert "substituted-model" in record.fallback_reason

    @pytest.mark.asyncio
    async def test_active_model_is_only_set_after_verification(self):
        """active_model remains None until health check confirms model is present in discovered models."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="qwen2.5-coder:7b",
        )
        assert provider.verified_active_model is None

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"id": "microsoft/phi-4-mini-reasoning"}]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            health = await provider.check_health()
            assert health.active_model is None
            assert provider.verified_active_model is None

        # Now discover the matching model
        mock_resp.json.return_value = {
            "data": [{"id": "qwen2.5-coder:7b"}]
        }
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            health = await provider.check_health()
            assert health.active_model == "qwen2.5-coder:7b"
            assert provider.verified_active_model == "qwen2.5-coder:7b"

    @pytest.mark.asyncio
    async def test_repository_switch_does_not_change_active_model(self):
        """Changing repository/workspace never modifies provider identity or active model state."""
        container = ApplicationContainer()
        settings = Settings()
        settings.llm_provider = "lmstudio"
        settings.llm_endpoint = "http://127.0.0.1:1234/v1"
        settings.ollama.llm_model = "microsoft/phi-4-mini-reasoning"
        container.settings = settings

        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="microsoft/phi-4-mini-reasoning",
        )
        provider.discovered_models = ["microsoft/phi-4-mini-reasoning"]
        provider.verified_active_model = "microsoft/phi-4-mini-reasoning"
        provider._health_checked = True
        container.llm_provider = provider

        repo_cases = container.get_repository_use_cases()
        with tempfile.TemporaryDirectory() as tmp_repo1, tempfile.TemporaryDirectory() as tmp_repo2:
            from app.application.dto import RepositoryCreateRequest
            r1 = await repo_cases.create_repository(RepositoryCreateRequest(name="Repo1", path=tmp_repo1, source_type="local"))
            r2 = await repo_cases.create_repository(RepositoryCreateRequest(name="Repo2", path=tmp_repo2, source_type="local"))

            assert container.llm_provider.provider_type == ProviderType.LM_STUDIO
            assert container.llm_provider.verified_active_model == "microsoft/phi-4-mini-reasoning"
            assert container.settings.llm_provider == "lmstudio"

            # Query repositories and verify provider state remains intact
            res = await repo_cases.list_repositories()
            assert res.success is True
            assert container.llm_provider.provider_type == ProviderType.LM_STUDIO
            assert container.llm_provider.verified_active_model == "microsoft/phi-4-mini-reasoning"
            assert container.settings.llm_provider == "lmstudio"

    @pytest.mark.asyncio
    async def test_lmstudio_loaded_model_mismatch_is_not_reported_as_success(self):
        """Full reproduction scenario: configured LM Studio with qwen2.5-coder:7b when phi-4-mini is loaded.
        Verifies active_model is null, engine is degraded, zero HTTP inference requests sent,
        and inference_status is model_not_available."""
        provider = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://127.0.0.1:1234/v1",
            api_key="local",
            default_model="qwen2.5-coder:7b",
        )

        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.json.return_value = {
            "data": [{"id": "microsoft/phi-4-mini-reasoning"}]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_get_resp
            health = await provider.check_health()
            assert health.is_reachable is True
            assert health.active_model is None
            assert provider.verified_active_model is None

            settings = Settings()
            settings.llm_provider = "lmstudio"
            settings.llm_endpoint = "http://127.0.0.1:1234/v1"
            settings.ollama.llm_model = "qwen2.5-coder:7b"

            sys_use_cases = SystemUseCases(
                settings_getter=lambda: settings,
                cognee_service_getter=lambda: MagicMock(is_initialized=True),
                llm_provider_getter=lambda: provider,
                provider_updater_fn=AsyncMock(),
            )
            h = await sys_use_cases.health()
            assert h.provider_reachable is True
            assert h.configured_model == "qwen2.5-coder:7b"
            assert h.active_model is None
            assert h.engine_state == "degraded"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            parser = IntentParserService(provider)
            intent = await parser.parse_intent("any prompt")
            assert mock_post.call_count == 0
            assert intent.inference_status == "model_not_available"
            assert intent.model_invoked is False
            assert intent.fallback_used is True
            assert intent.model_name is None
