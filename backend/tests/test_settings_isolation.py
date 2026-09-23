"""Regression tests for settings-store isolation.

Provider configuration is persisted through ``Settings.save_persisted_settings()``,
which defaults to ``~/.retrack/settings.json``. Running the test suite previously
rewrote the live provider/model configuration of the machine executing it
(observed: lmstudio/unsloth-phi-4-mini-reasoning was replaced by
ollama/qwen2.5-coder:7b during a full ``pytest tests/`` run).

These tests pin the isolation guard so that cannot happen again.
"""

from pathlib import Path

import pytest

from app.application.container import ApplicationContainer
from app.config.settings import get_settings
from app.models.provider import DiscoveryStatus, ProviderHealthStatus, ProviderType


def _real_settings_path() -> Path:
    return Path.home() / ".retrack" / "settings.json"


def test_default_settings_store_is_isolated_from_real_home():
    """A default-configured Settings instance must not target the developer's store."""
    settings = get_settings()
    resolved = Path(settings.settings_store_path).resolve()
    real = _real_settings_path().resolve()

    assert resolved != real
    assert Path.home() not in resolved.parents


def test_legacy_settings_store_is_isolated_from_real_home():
    settings = get_settings()
    resolved = Path(settings.legacy_settings_store_path).resolve()

    assert Path.home() not in resolved.parents


@pytest.mark.asyncio
async def test_update_provider_does_not_write_real_settings_store(monkeypatch):
    """Hot-reloading the provider must persist only to the isolated store."""
    import app.services.llm_provider_service as provider_module

    async def fake_check_health(self):  # noqa: ANN001
        return ProviderHealthStatus(
            provider=ProviderType.LM_STUDIO,
            base_url=self.base_url,
            is_reachable=True,
            active_model=self.default_model,
            loaded_models=[],
            quantization_warning=None,
            discovery_status=DiscoveryStatus.AVAILABLE,
        )

    monkeypatch.setattr(provider_module.LLMProviderService, "check_health", fake_check_health)

    real_path = _real_settings_path()
    before = real_path.read_bytes() if real_path.exists() else None

    container = ApplicationContainer()
    await container.update_provider("lmstudio", "http://127.0.0.1:1234/v1", "test-model")

    isolated_path = Path(container.settings.settings_store_path)
    after = real_path.read_bytes() if real_path.exists() else None

    assert isolated_path != real_path
    assert isolated_path.exists(), "the isolated store should receive the update"
    assert after == before, "the developer's real settings store must be untouched"
