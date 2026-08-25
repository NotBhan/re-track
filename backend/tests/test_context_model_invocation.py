"""Tests for Context Generation LLM Provider Model Invocation (Phase 10D.2).

Validates:
1. End-to-end model-dependent context generation reaches configured provider (LM Studio / Ollama).
2. Configured model name and parameters are forwarded correctly to inference.
3. Provider failure produces truthful failure status and explicit fallback metadata.
4. Exactly one provider generation call occurs per model-dependent synthesis.
5. Deterministic retrieval is explicitly labeled without synthetic AI-generation claims.
"""

import asyncio
from pathlib import Path
import tempfile
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.application.container import ApplicationContainer
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
    ErrorResponse,
    GenerateContextRequest,
)
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.models.provider import ProviderType
from app.services.intent_parser import IntentParserService
from app.services.llm_provider_service import LLMProviderService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


class MockLLMProvider(LLMProviderPort):
    """Deterministic test double for LLM provider."""

    def __init__(
        self,
        provider_type: ProviderType = ProviderType.LM_STUDIO,
        default_model: str = "qwen2.5-coder:7b",
        response_text: str = '{"task_summary": "Fix auth expiration", "category": "bug_fix", "extracted_symbols": ["AuthService"], "relevant_file_hints": ["auth.py"], "is_vague": false}',
        should_fail: bool = False,
        failure_exception: Optional[Exception] = None,
    ) -> None:
        self.provider_type = provider_type
        self.default_model = default_model
        self.response_text = response_text
        self.should_fail = should_fail
        self.failure_exception = failure_exception or ConnectionError("Connection refused to provider at http://127.0.0.1:1234/v1")
        self.call_count = 0
        self.last_prompt = None
        self.last_model = None
        self.last_system_prompt = None

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        self.last_model = model or self.default_model

        if self.should_fail:
            raise self.failure_exception
        return self.response_text

    async def check_health(self) -> Any:
        mock_health = MagicMock()
        mock_health.is_reachable = not self.should_fail
        mock_health.active_model = self.default_model
        mock_health.loaded_models = []
        mock_health.quantization_warning = None
        return mock_health

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        mock_res = MagicMock()
        mock_res.is_reachable = not self.should_fail
        mock_res.models = []
        return mock_res


@pytest.mark.asyncio
async def test_intent_parser_successful_lm_studio_invocation():
    """Verify IntentParser invokes LM Studio with configured model and records telemetry."""
    mock_provider = MockLLMProvider(
        provider_type=ProviderType.LM_STUDIO,
        default_model="qwen2.5-coder:7b",
        response_text='{"task_summary": "Update token auth", "category": "feature_addition", "extracted_symbols": ["TokenManager"], "relevant_file_hints": ["tokens.py"], "is_vague": false}',
    )
    parser = IntentParserService(llm_service=mock_provider)

    result = await parser.parse_intent("Add TokenManager refresh support in tokens.py")

    assert mock_provider.call_count == 1
    assert mock_provider.last_model == "qwen2.5-coder:7b"
    assert result.model_invoked is True
    assert result.provider_identity == "lmstudio"
    assert result.model_name == "qwen2.5-coder:7b"
    assert result.inference_status == "completed"
    assert result.fallback_used is False
    assert result.fallback_reason is None
    assert result.task_summary == "Update token auth"
    assert "TokenManager" in result.extracted_symbols


@pytest.mark.asyncio
async def test_intent_parser_successful_ollama_invocation():
    """Verify IntentParser invokes Ollama with configured model and records telemetry."""
    mock_provider = MockLLMProvider(
        provider_type=ProviderType.OLLAMA,
        default_model="phi4-mini:latest",
        response_text='{"task_summary": "Fix race condition in store", "category": "bug_fix", "extracted_symbols": ["DataStore"], "relevant_file_hints": ["store.py"], "is_vague": false}',
    )
    parser = IntentParserService(llm_service=mock_provider)

    result = await parser.parse_intent("Fix concurrency race in DataStore")

    assert mock_provider.call_count == 1
    assert mock_provider.last_model == "phi4-mini:latest"
    assert result.model_invoked is True
    assert result.provider_identity == "ollama"
    assert result.model_name == "phi4-mini:latest"
    assert result.inference_status == "completed"
    assert result.fallback_used is False


@pytest.mark.asyncio
async def test_intent_parser_provider_failure_returns_explicit_fallback():
    """Verify provider connection failure returns truthful fallback with error details."""
    mock_provider = MockLLMProvider(
        provider_type=ProviderType.LM_STUDIO,
        default_model="qwen2.5-coder:7b",
        should_fail=True,
        failure_exception=ConnectionError("Connection refused to http://127.0.0.1:1234/v1"),
    )
    parser = IntentParserService(llm_service=mock_provider)

    result = await parser.parse_intent("Fix JWT authentication in auth.py")

    assert mock_provider.call_count == 1
    assert result.model_invoked is False
    assert result.provider_identity == "lmstudio"
    assert result.model_name == "qwen2.5-coder:7b"
    assert result.inference_status == "failed"
    assert result.fallback_used is True
    assert "ConnectionError" in str(result.fallback_reason)
    assert result.category == "bug_fix"  # Heuristic fallback extracted


@pytest.mark.asyncio
async def test_intent_parser_malformed_json_fallback():
    """Verify malformed JSON from LLM triggers explicit fallback."""
    mock_provider = MockLLMProvider(
        response_text="I am a chatbot and here is some unstructured text without JSON",
    )
    parser = IntentParserService(llm_service=mock_provider)

    result = await parser.parse_intent("Refactor server routes")

    assert mock_provider.call_count == 1
    assert result.model_invoked is False
    assert result.inference_status == "failed"
    assert result.fallback_used is True
    assert "JSON schema" in str(result.fallback_reason)


@pytest.mark.asyncio
async def test_get_agent_context_end_to_end_telemetry():
    """Verify get_agent_context propagates inference telemetry to AgentContextResponse."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "test_repo"
        repo_path.mkdir()
        (repo_path / "auth.py").write_text("class AuthService:\n    def login(self): pass\n")

        mock_provider = MockLLMProvider(
            provider_type=ProviderType.LM_STUDIO,
            default_model="qwen2.5-coder:7b",
            response_text='{"task_summary": "Auth login refactor", "category": "refactoring", "extracted_symbols": ["AuthService"], "relevant_file_hints": ["auth.py"], "is_vague": false}',
        )

        container = ApplicationContainer.create()
        container.llm_provider = mock_provider
        container.intent_parser = IntentParserService(mock_provider)
        container.cognee_service = MagicMock()
        container.indexing_service = MagicMock()
        container.indexing_service.discover_files.return_value = [repo_path / "auth.py"]
        container.indexing_service.filter_files.return_value = [repo_path / "auth.py"]

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Synthetic Context Package"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        auth_svc = WorkspaceAuthorizationService(workspace_roots=[Path(tmp_dir)])
        container.workspace_auth = auth_svc

        context_uc = container.get_context_use_cases()

        req = AgentContextRequest(
            task_prompt="Refactor AuthService login method in auth.py",
            repository_path=str(repo_path),
            dataset_name="test_repo",
        )

        resp = await context_uc.get_agent_context(req)

        assert isinstance(resp, AgentContextResponse)
        assert resp.success is True
        assert resp.model_invoked is True
        assert resp.provider_identity == "lmstudio"
        assert resp.model_name == "qwen2.5-coder:7b"
        assert resp.inference_status == "completed"
        assert resp.fallback_used is False
        assert mock_provider.call_count == 1


@pytest.mark.asyncio
async def test_generate_context_truthfully_reports_deterministic_mode():
    """Verify generate_context reports deterministic fallback mode without fake model claims."""
    container = ApplicationContainer.create()
    container.cognee_service = MagicMock()
    container.indexing_service = MagicMock()
    mock_pkg = MagicMock()
    mock_pkg.task = "Find database models"
    mock_pkg.objective = "Find database models"
    mock_pkg.dataset = "test_dataset"
    mock_pkg.markdown = "# Recall Package"
    mock_pkg.sections = []
    mock_pkg.references = []
    mock_pkg.metadata = None
    container.context_service = MagicMock()
    container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

    context_uc = container.get_context_use_cases()

    req = GenerateContextRequest(
        task="Find database models",
        datasets=["test_dataset"],
    )

    resp = await context_uc.generate_context(req)

    assert resp.success is True
    assert resp.model_invoked is False
    assert resp.fallback_used is True
    assert resp.inference_status == "not_configured"
    assert "Deterministic retrieval" in str(resp.fallback_reason)
