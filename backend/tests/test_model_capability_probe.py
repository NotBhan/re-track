"""
Unit tests for runtime model capability probe and store.

Verifies:
- Chat, tool calling, and JSON mode are probed against the endpoint.
- Reasoning capability remains strictly 'unknown' unless verified through metadata.
- Models producing <think> text do NOT claim verified reasoning capability.
- Separate embedding model is tested through /embeddings and not assumed from chat.
- Context window is obtained from trusted metadata or configuration, never guessed.
- Capabilities are stored and refreshed per model and provider.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from app.models.provider import ProviderType
from app.services.capability_probe import (
    CapabilityStore,
    async_detect_model_capabilities,
    detect_model_capabilities,
    fetch_trusted_model_metadata,
)
from app.services.llm_provider_service import LLMProviderService


class TestModelCapabilityProbe:
    """Test runtime capability detection and truth invariants."""

    def test_detect_chat_unavailable_returns_early(self):
        """When chat completion fails, chat is marked unavailable and probe returns early."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            result = detect_model_capabilities("http://localhost:1234/v1", "test-model")

            assert result["model"] == "test-model"
            assert result["chat"] == "unavailable"
            assert result["tool_calling"] == "unknown"
            assert result["json_mode"] == "unknown"
            assert result["reasoning"] == "unknown"
            assert result["embeddings"] == "not_tested"
            assert mock_post.call_count == 1

    def test_detect_tool_calling_supported(self):
        """When endpoint returns tool_calls, tool_calling is marked supported."""
        with patch("requests.post") as mock_post, patch(
            "app.services.capability_probe.fetch_trusted_model_metadata", return_value={}
        ):
            def mock_response(*args, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                resp.raise_for_status.return_value = None
                json_data = kwargs.get("json", {})
                if "tools" in json_data:
                    resp.json.return_value = {
                        "choices": [{"message": {"tool_calls": [{"id": "call_1", "function": {"name": "capability_test"}}]}}]
                    }
                elif "response_format" in json_data:
                    resp.json.return_value = {"choices": [{"message": {"content": '{"ok": true}'}}]}
                else:
                    resp.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
                return resp

            mock_post.side_effect = mock_response

            result = detect_model_capabilities("http://localhost:1234/v1", "test-model")
            assert result["chat"] == "supported"
            assert result["tool_calling"] == "supported"
            assert result["json_mode"] == "supported"
            assert result["reasoning"] == "unknown"
            assert result["embeddings"] == "not_tested"
            assert result["context_window"] is None

    def test_detect_tool_calling_unsupported_when_no_calls(self):
        """When endpoint accepts tools but returns normal message, tool_calling is unsupported."""
        with patch("requests.post") as mock_post, patch(
            "app.services.capability_probe.fetch_trusted_model_metadata", return_value={}
        ):
            def mock_response(*args, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                resp.raise_for_status.return_value = None
                resp.json.return_value = {"choices": [{"message": {"content": "I cannot call tools."}}]}
                return resp

            mock_post.side_effect = mock_response

            result = detect_model_capabilities("http://localhost:1234/v1", "test-model")
            assert result["chat"] == "supported"
            assert result["tool_calling"] == "unsupported"

    def test_detect_tool_calling_unknown_on_error(self):
        """When tool calling payload causes 400 Bad Request, tool_calling is unknown."""
        with patch("requests.post") as mock_post, patch(
            "app.services.capability_probe.fetch_trusted_model_metadata", return_value={}
        ):
            def mock_response(*args, **kwargs):
                json_data = kwargs.get("json", {})
                resp = MagicMock()
                if "tools" in json_data:
                    resp.status_code = 400
                    resp.raise_for_status.side_effect = Exception("400 Client Error: Bad Request")
                    return resp
                resp.status_code = 200
                resp.raise_for_status.return_value = None
                resp.json.return_value = {"choices": [{"message": {"content": '{"ok": true}'}}]}
                return resp

            mock_post.side_effect = mock_response

            result = detect_model_capabilities("http://localhost:1234/v1", "test-model")
            assert result["chat"] == "supported"
            assert result["tool_calling"] == "unknown"

    def test_reasoning_remains_unknown_even_with_think_tags(self):
        """A model producing <think> text does NOT establish verified reasoning capability."""
        with patch("requests.post") as mock_post, patch(
            "app.services.capability_probe.fetch_trusted_model_metadata", return_value={}
        ):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            resp.json.return_value = {
                "choices": [{"message": {"content": "<think>Let me think...</think>OK"}}]
            }
            mock_post.return_value = resp

            result = detect_model_capabilities("http://localhost:1234/v1", "phi-4-mini-reasoning")
            assert result["chat"] == "supported"
            # Invariant: reasoning must remain unknown unless verified through metadata or dedicated eval
            assert result["reasoning"] == "unknown"

    def test_embeddings_tested_separately_when_configured(self):
        """Embedding model is tested via /embeddings and not assumed from chat model."""
        with patch("requests.post") as mock_post, patch(
            "app.services.capability_probe.fetch_trusted_model_metadata", return_value={}
        ):
            def mock_response(*args, **kwargs):
                url = args[0] if args else kwargs.get("url", "")
                resp = MagicMock()
                resp.status_code = 200
                resp.raise_for_status.return_value = None
                if "/embeddings" in url:
                    resp.json.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
                else:
                    resp.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
                return resp

            mock_post.side_effect = mock_response

            # When embedding model is provided
            result = detect_model_capabilities(
                "http://localhost:1234/v1",
                "phi-4-mini",
                embedding_model="text-embedding-nomic",
            )
            assert result["embeddings"] == "supported"
            assert result["embedding_model"] == "text-embedding-nomic"

    def test_context_window_from_trusted_metadata_not_guessed(self):
        """Context window is retrieved from trusted metadata and not a guessed default."""
        with patch("requests.post") as mock_post, patch(
            "app.services.capability_probe.fetch_trusted_model_metadata"
        ) as mock_meta:
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
            mock_post.return_value = resp

            # Metadata provides trusted context window
            mock_meta.return_value = {"context_window": 131072, "source": "lmstudio_api_v0"}

            result = detect_model_capabilities("http://localhost:1234/v1", "phi-4-mini")
            assert result["context_window"] == 131072

            # When metadata has no context window, it must remain None, not a guessed number
            mock_meta.return_value = {}
            result_no_meta = detect_model_capabilities("http://localhost:1234/v1", "phi-4-mini")
            assert result_no_meta["context_window"] is None

    def test_capability_store_persistence(self, tmp_path):
        """CapabilityStore saves and retrieves capabilities per model and provider."""
        store_file = tmp_path / "test_capabilities.json"
        store = CapabilityStore(store_path=store_file)

        caps = {
            "model": "model-a",
            "chat": "supported",
            "tool_calling": "unsupported",
            "json_mode": "supported",
            "reasoning": "unknown",
            "embeddings": "not_tested",
            "context_window": 32768,
        }
        store.set("ollama", "http://localhost:11434/v1", "model-a", caps)

        # Retrieve from same store
        cached = store.get("ollama", "http://localhost:11434/v1", "model-a")
        assert cached is not None
        assert cached["context_window"] == 32768
        assert cached["provider"] == "ollama"

        # Verify persisted to disk and reloadable in new store instance
        store2 = CapabilityStore(store_path=store_file)
        reloaded = store2.get("ollama", "http://localhost:11434/v1", "model-a")
        assert reloaded is not None
        assert reloaded["chat"] == "supported"
        assert reloaded["context_window"] == 32768

    @pytest.mark.asyncio
    async def test_llm_provider_service_probe_capabilities_integration(self):
        """LLMProviderService.probe_capabilities updates service state and check_health."""
        service = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://localhost:1234/v1",
            default_model="phi4-mini",
        )

        dummy_caps = {
            "model": "phi4-mini",
            "chat": "supported",
            "tool_calling": "unknown",
            "json_mode": "unknown",
            "reasoning": "unknown",
            "embeddings": "not_tested",
            "context_window": 56064,
        }

        with patch(
            "app.services.capability_probe.async_detect_model_capabilities",
            return_value=dummy_caps,
        ), patch.object(service, "discover_models_for_endpoint") as mock_disc:
            from app.models.provider import DiscoveryStatus, ProviderDiscoveryResult

            mock_disc.return_value = ProviderDiscoveryResult(
                provider=ProviderType.LM_STUDIO,
                base_url="http://localhost:1234/v1",
                is_reachable=True,
                status=DiscoveryStatus.AVAILABLE,
                models=[],
            )

            probed = await service.probe_capabilities(force_refresh=True)
            assert probed["chat"] == "supported"
            assert probed["context_window"] == 56064

            # Verify check_health attaches the probed capabilities
            health = await service.check_health()
            assert health.capabilities is not None
            assert health.capabilities["model"] == "phi4-mini"
            assert health.capabilities["context_window"] == 56064
