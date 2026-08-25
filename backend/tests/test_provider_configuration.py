"""Tests for Phase 10D.1: Provider Discovery, Configuration, Persistence, and Security."""

import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.application.container import ApplicationContainer
from app.application.dto import ProviderDiscoveryRequest
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings
from app.models.provider import DiscoveryStatus, ProviderType, QuantizationLevel
from app.services.llm_provider_service import LLMProviderService


class TestProviderServiceDiscovery:
    """Test LLMProviderService model discovery and health checks."""

    @pytest.mark.asyncio
    async def test_discover_models_available(self):
        """Probing an OpenAI-compatible endpoint with models returns AVAILABLE status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "phi4-mini:latest"},
                {"id": "qwen2.5-coder:7b-instruct-q6_k"},
            ]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await LLMProviderService.discover_models_for_endpoint(
                provider_type=ProviderType.LM_STUDIO,
                base_url="http://localhost:1234/v1",
                api_key="local",
            )

            assert result.is_reachable is True
            assert result.status == DiscoveryStatus.AVAILABLE
            assert len(result.models) == 2
            assert result.models[0].model_id == "phi4-mini:latest"
            assert result.models[0].is_phi4_mini is True
            assert result.models[1].is_q6_or_higher is True

    @pytest.mark.asyncio
    async def test_discover_models_reachable_but_empty(self):
        """When server is running but has 0 models loaded, report reachable_but_empty distinctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await LLMProviderService.discover_models_for_endpoint(
                provider_type=ProviderType.LM_STUDIO,
                base_url="http://localhost:1234/v1",
                api_key="local",
            )

            assert result.is_reachable is True
            assert result.status == DiscoveryStatus.REACHABLE_BUT_EMPTY
            assert len(result.models) == 0
            assert "no models are currently loaded" in result.message

    @pytest.mark.asyncio
    async def test_discover_models_unreachable(self):
        """Unreachable host reports UNREACHABLE without throwing exceptions."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            result = await LLMProviderService.discover_models_for_endpoint(
                provider_type=ProviderType.OLLAMA,
                base_url="http://192.0.2.1:11434/v1",
                api_key="local",
            )

            assert result.is_reachable is False
            assert result.status == DiscoveryStatus.UNREACHABLE
            assert "unreachable" in result.message.lower()

    @pytest.mark.asyncio
    async def test_discover_models_auth_failed(self):
        """HTTP 401/403 triggers DISCOVERY_FAILED with authentication error detail."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await LLMProviderService.discover_models_for_endpoint(
                provider_type=ProviderType.OPENAI_COMPATIBLE,
                base_url="https://api.openai.com/v1",
                api_key="invalid-key",
            )

            assert result.is_reachable is True
            assert result.status == DiscoveryStatus.DISCOVERY_FAILED
            assert "Authentication failed" in result.message


class TestProviderHotReloadAndContainer:
    """Test ApplicationContainer hot reload contract and parameter compatibility."""

    @pytest.mark.asyncio
    async def test_provider_hot_reload_regression(self):
        """Ensure ApplicationContainer.update_provider successfully reconfigures without parameter mismatch."""
        container = ApplicationContainer()
        settings = Settings()
        container.settings = settings

        mock_health = MagicMock()
        mock_health.is_reachable = True
        mock_health.loaded_models = []
        mock_health.quantization_warning = None

        with patch.object(LLMProviderService, "check_health", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = mock_health

            # Hot reload to LM Studio
            res_lm = await container.update_provider(
                provider="lmstudio",
                base_url="http://localhost:1234/v1",
                model="phi4-mini",
                api_key="local",
            )
            assert res_lm["success"] is True
            assert res_lm["provider"] == "lmstudio"
            assert res_lm["base_url"] == "http://localhost:1234/v1"
            assert container.llm_provider.provider_type == ProviderType.LM_STUDIO
            assert container.llm_provider.default_model == "phi4-mini"

            # Hot reload to Ollama
            res_ol = await container.update_provider(
                provider="ollama",
                base_url="http://localhost:11434/v1",
                model="qwen2.5-coder:7b",
                api_key="local",
            )
            assert res_ol["success"] is True
            assert res_ol["provider"] == "ollama"
            assert container.llm_provider.provider_type == ProviderType.OLLAMA
            assert container.llm_provider.default_model == "qwen2.5-coder:7b"


class TestSettingsPersistenceAndSecurity:
    """Test settings.json atomic persistence, 0600 file permissions, and 0700 dir permissions."""

    def test_settings_atomic_save_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "sub" / "settings.json"

            settings = Settings()
            settings.llm_provider = "lmstudio"
            settings.llm_endpoint = "http://localhost:1234/v1"
            settings.llm_api_key = "sk-secret-test-key-12345"
            settings.ollama.llm_model = "phi4-mini-q6_k"

            settings.save_persisted_settings(store_path=store_path)

            assert store_path.exists()

            # Verify permissions on POSIX
            if os.name == "posix":
                file_mode = stat.S_IMODE(store_path.stat().st_mode)
                dir_mode = stat.S_IMODE(store_path.parent.stat().st_mode)
                assert file_mode == 0o600, f"Expected 0600, got {oct(file_mode)}"
                assert dir_mode == 0o700, f"Expected 0700, got {oct(dir_mode)}"

            # Load into fresh settings instance
            loaded_settings = Settings()
            loaded_settings.load_persisted_settings(store_path=store_path)

            assert loaded_settings.llm_provider == "lmstudio"
            assert loaded_settings.llm_endpoint == "http://localhost:1234/v1"
            assert loaded_settings.llm_api_key == "sk-secret-test-key-12345"
            assert loaded_settings.ollama.llm_model == "phi4-mini-q6_k"

    @pytest.mark.asyncio
    async def test_secret_masking_in_status_and_settings(self):
        settings = Settings()
        settings.llm_provider = "openai_compatible"
        settings.llm_endpoint = "https://api.openai.com/v1"
        settings.llm_api_key = "sk-test-super-secret-key-12345"

        system_use_cases = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: None,
            llm_provider_getter=lambda: None,
            provider_updater_fn=AsyncMock(),
        )

        app_settings = await system_use_cases.get_app_settings()
        assert app_settings.api_key_configured is True
        assert app_settings.api_key_masked == "sk-...345"
        assert "sk-test-super-secret-key-12345" not in json.dumps(app_settings.model_dump())

        backend_status = await system_use_cases.get_backend_status()
        assert "sk-test-super-secret-key-12345" not in json.dumps(backend_status.model_dump())


class TestRuntimeEngineStateReconciliation:
    """Test Phase 10D.1.1 Runtime Engine State Reconciliation contracts."""

    @pytest.mark.asyncio
    async def test_runtime_health_follows_active_provider(self):
        """Runtime health follows LM Studio rather than Ollama."""
        settings = Settings()
        settings.llm_provider = "lmstudio"
        settings.llm_endpoint = "http://localhost:1234/v1"
        settings.ollama.llm_model = "qwen2.5-coder:7b"

        mock_provider = MagicMock(spec=LLMProviderService)
        mock_provider.provider_type = ProviderType.LM_STUDIO
        mock_provider.base_url = "http://localhost:1234/v1"
        mock_provider.default_model = "qwen2.5-coder:7b"

        from app.models.provider import LoadedModelInfo, ProviderHealthStatus
        mock_provider.check_health = AsyncMock(return_value=ProviderHealthStatus(
            provider=ProviderType.LM_STUDIO,
            base_url="http://localhost:1234/v1",
            is_reachable=True,
            active_model="qwen2.5-coder:7b",
            loaded_models=[LoadedModelInfo(model_id="qwen2.5-coder:7b", name="qwen2.5-coder")],
            discovery_status=DiscoveryStatus.AVAILABLE,
        ))

        mock_cognee = MagicMock()
        mock_cognee.is_initialized = True

        system_use_cases = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: mock_cognee,
            llm_provider_getter=lambda: mock_provider,
            provider_updater_fn=AsyncMock(),
        )

        h = await system_use_cases.health()
        assert h.provider == "lmstudio"
        assert h.provider_identity == "lmstudio"
        assert h.provider_reachable is True
        assert h.engine_state == "healthy"
        assert h.active_model == "qwen2.5-coder:7b"
        assert h.cognee_state == "healthy"

        s = await system_use_cases.get_backend_status()
        assert s.provider_identity == "lmstudio"
        assert s.provider_reachable is True
        assert s.engine_state == "healthy"
        assert s.llm_model == "qwen2.5-coder:7b"

    @pytest.mark.asyncio
    async def test_lm_studio_health_not_evaluated_through_ollama(self):
        """LM Studio health is not evaluated through Ollama connection tests."""
        settings = Settings()
        settings.llm_provider = "lmstudio"
        settings.llm_endpoint = "http://localhost:1234/v1"

        mock_provider = MagicMock(spec=LLMProviderService)
        mock_provider.provider_type = ProviderType.LM_STUDIO
        mock_provider.base_url = "http://localhost:1234/v1"
        mock_provider.default_model = "phi4-mini"

        from app.models.provider import ProviderHealthStatus
        mock_provider.check_health = AsyncMock(return_value=ProviderHealthStatus(
            provider=ProviderType.LM_STUDIO,
            base_url="http://localhost:1234/v1",
            is_reachable=True,
            active_model="phi4-mini",
            loaded_models=[],
            discovery_status=DiscoveryStatus.AVAILABLE,
        ))

        # Ollama check connection is explicitly broken
        with patch("app.config.settings.OllamaConfig.check_connection", return_value=False):
            system_use_cases = SystemUseCases(
                settings_getter=lambda: settings,
                cognee_service_getter=lambda: None,
                llm_provider_getter=lambda: mock_provider,
                provider_updater_fn=AsyncMock(),
            )

            h = await system_use_cases.health()
            assert h.provider_reachable is True
            assert h.engine_state == "healthy"
            assert h.provider == "lmstudio"

    @pytest.mark.asyncio
    async def test_provider_state_and_cognee_state_are_independent(self):
        """A healthy LM Studio provider with uninitialized Cognee must report engine healthy and cognee unavailable."""
        settings = Settings()
        settings.llm_provider = "lmstudio"
        settings.llm_endpoint = "http://localhost:1234/v1"

        mock_provider = MagicMock(spec=LLMProviderService)
        mock_provider.provider_type = ProviderType.LM_STUDIO
        mock_provider.base_url = "http://localhost:1234/v1"
        mock_provider.default_model = "phi4-mini"

        from app.models.provider import ProviderHealthStatus
        mock_provider.check_health = AsyncMock(return_value=ProviderHealthStatus(
            provider=ProviderType.LM_STUDIO,
            base_url="http://localhost:1234/v1",
            is_reachable=True,
            active_model="phi4-mini",
            loaded_models=[],
            discovery_status=DiscoveryStatus.AVAILABLE,
        ))

        # Cognee is uninitialized
        mock_cognee = MagicMock()
        mock_cognee.is_initialized = False

        system_use_cases = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: mock_cognee,
            llm_provider_getter=lambda: mock_provider,
            provider_updater_fn=AsyncMock(),
        )

        h = await system_use_cases.health()
        assert h.provider_reachable is True
        assert h.engine_state == "healthy"
        assert h.cognee_initialized is False
        assert h.cognee_state == "unavailable"
        assert h.cognee_reason is not None

    @pytest.mark.asyncio
    async def test_discovered_models_do_not_become_active_model_automatically(self):
        """Probing models does not invent an active_model when no default_model is specified."""
        service = LLMProviderService(
            provider_type=ProviderType.LM_STUDIO,
            base_url="http://localhost:1234/v1",
            default_model=None,
        )

        from app.models.provider import LoadedModelInfo, ProviderDiscoveryResult
        with patch.object(LLMProviderService, "discover_models_for_endpoint", new_callable=AsyncMock) as mock_disc:
            mock_disc.return_value = ProviderDiscoveryResult(
                provider=ProviderType.LM_STUDIO,
                base_url="http://localhost:1234/v1",
                is_reachable=True,
                status=DiscoveryStatus.AVAILABLE,
                models=[
                    LoadedModelInfo(model_id="qwen2.5-coder:7b", name="qwen2.5-coder"),
                    LoadedModelInfo(model_id="phi4-mini:latest", name="phi4-mini"),
                ],
            )

            status = await service.check_health()
            assert status.is_reachable is True
            assert status.active_model is None
            assert len(status.loaded_models) == 2

    @pytest.mark.asyncio
    async def test_persisted_lm_studio_configuration_survives_restart(self):
        """Persisted LM Studio configuration correctly hydrates ApplicationContainer on startup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = Path(tmpdir) / "settings.json"

            # Save LM Studio settings
            s1 = Settings()
            s1.llm_provider = "lmstudio"
            s1.llm_endpoint = "http://127.0.0.1:1234/v1"
            s1.ollama.llm_model = "qwen2.5-coder:7b"
            s1.save_persisted_settings(store_path=store_path)

            # Fresh container instance initializing with store_path
            s2 = Settings()
            s2.settings_store_path = store_path
            container = ApplicationContainer.create(settings=s2)

            mock_health = MagicMock()
            mock_health.is_reachable = True
            mock_health.loaded_models = []
            mock_health.quantization_warning = None

            with patch.object(LLMProviderService, "check_health", new_callable=AsyncMock) as mock_check:
                mock_check.return_value = mock_health
                await container.initialize()

                assert container.llm_provider is not None
                assert container.llm_provider.provider_type == ProviderType.LM_STUDIO
                assert container.llm_provider.base_url == "http://127.0.0.1:1234/v1"
                assert container.llm_provider.default_model == "qwen2.5-coder:7b"
