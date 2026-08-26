"""Runtime acceptance tests for context evidence gating and abstention."""

import asyncio
from pathlib import Path
import tempfile
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.application.container import ApplicationContainer
from app.application.domain.evidence import EvidenceRecord, EvidenceState
from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import (
    AgentContextRequest,
    AgentContextResponse,
)
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.models.provider import ProviderType
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.source_search_service import SourceSearchService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


class InMemoryMetaStore(RepositoryMetadataPort):
    """In-memory metadata store for runtime tests."""

    def __init__(self) -> None:
        self._records: dict[str, IndexedRepositoryRecord] = {}

    def get_by_path(self, path: Path) -> Optional[IndexedRepositoryRecord]:
        for r in self._records.values():
            if Path(r.path).resolve() == Path(path).resolve():
                return r
        return None

    def get_by_id(self, repo_id: str) -> Optional[IndexedRepositoryRecord]:
        return self._records.get(repo_id)

    def list_all(self) -> list[IndexedRepositoryRecord]:
        return list(self._records.values())

    def upsert(self, record: IndexedRepositoryRecord) -> None:
        self._records[record.id] = record

    def delete(self, repo_id: str) -> bool:
        return self._records.pop(repo_id, None) is not None

    def count(self) -> int:
        return len(self._records)


class RuntimeAcceptanceMockProvider(LLMProviderPort):
    """Test double for LLM provider in runtime acceptance testing."""

    def __init__(
        self,
        provider_type: ProviderType = ProviderType.LM_STUDIO,
        default_model: str = "qwen2.5-coder:7b",
        response_text: str = '{"task_summary": "Parsed task", "category": "feature", "extracted_symbols": [], "relevant_file_hints": [], "is_vague": false}',
        should_fail: bool = False,
    ) -> None:
        self.provider_type = provider_type
        self.default_model = default_model
        self.response_text = response_text
        self.should_fail = should_fail
        self.call_count = 0

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.call_count += 1
        if self.should_fail:
            raise ConnectionError("Provider unreachable at http://127.0.0.1:1234/v1")
        return self.response_text

    async def check_health(self) -> Any:
        mock_h = MagicMock()
        mock_h.is_reachable = not self.should_fail
        mock_h.active_model = self.default_model
        mock_h.loaded_models = [self.default_model] if not self.should_fail else []
        mock_h.quantization_warning = None
        return mock_h

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        mock_res = MagicMock()
        mock_res.is_reachable = not self.should_fail
        mock_res.models = []
        return mock_res


@pytest.mark.asyncio
async def test_runtime_acceptance_negative_case_django_no_auth():
    """Negative Case: Django repository with no auth subsystem must deterministically abstain."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "django_sample_app"
        repo_path.mkdir()
        (repo_path / "manage.py").write_text("#!/usr/bin/env python\n# Django manage script\n")
        (repo_path / "settings.py").write_text("INSTALLED_APPS = ['django.contrib.admin']\nSECRET_KEY = 'test'\n")
        (repo_path / "models.py").write_text("class Product:\n    def __init__(self, name):\n        self.name = name\n")
        (repo_path / "views.py").write_text("def list_products(request):\n    return []\n")

        meta = InMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        mock_provider = RuntimeAcceptanceMockProvider(
            response_text='{"task_summary": "Implement JWT auth endpoint", "category": "feature", "extracted_symbols": ["jwt_auth", "TokenVerifier"], "relevant_file_hints": ["auth.py"], "is_vague": false}'
        )
        container.llm_provider = mock_provider
        container.intent_parser = IntentParserService(llm_service=mock_provider)

        mock_cognee = MagicMock()
        container.cognee_service = mock_cognee
        container.indexing_service = IndexingService(cognee_service=mock_cognee)
        container.summary_generator = RepositorySummaryGenerator()
        container.source_search = SourceSearchService()

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Synthetic Context Package"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        context_uc = container.get_context_use_cases()
        req = AgentContextRequest(
            task_prompt="Implement an API endpoint requiring JWT authentication and token verification",
            repository_path=str(repo_path),
        )

        resp = await context_uc.get_agent_context(req)

        assert isinstance(resp, AgentContextResponse)
        assert resp.success is True
        # 1. Evidence state must be insufficient or none
        assert resp.evidence_state in [EvidenceState.INSUFFICIENT.value, EvidenceState.NONE.value]
        # 2. Must abstain
        assert resp.abstained is True
        # 3. Model claims not allowed
        assert resp.model_claims_allowed is False
        # 4. Model invocation skipped
        assert resp.model_invoked is False
        # 5. Abstention output format check
        assert "# Task Intent" in resp.context_markdown
        assert "# Observed Repository Evidence" in resp.context_markdown
        assert "# Missing Evidence" in resp.context_markdown
        assert "# Insufficient Repository Evidence Notice" in resp.context_markdown
        assert any("authentication" in miss for miss in resp.missing_evidence)
        # 6. Forbidden check: no think blocks, no invented authentication claims
        assert "<think>" not in resp.context_markdown
        assert "</think>" not in resp.context_markdown
        assert "[THINKING]" not in resp.context_markdown
        assert "JWTAuthMiddleware" not in resp.context_markdown


@pytest.mark.asyncio
async def test_runtime_acceptance_positive_case_grounded_symbols():
    """Positive Case: Repository with genuine route and symbol evidence permits grounded synthesis."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "catalog_service"
        repo_path.mkdir()
        (repo_path / "models.py").write_text("class ItemModel:\n    def __init__(self, id, name):\n        self.id = id\n        self.name = name\n")
        (repo_path / "views.py").write_text("from models import ItemModel\n\ndef get_item_by_id(item_id: str) -> ItemModel:\n    return ItemModel(item_id, 'Sample')\n")

        meta = InMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        mock_provider = RuntimeAcceptanceMockProvider(
            response_text='{"task_summary": "Modify get_item_by_id endpoint", "category": "refactoring", "extracted_symbols": ["get_item_by_id", "ItemModel"], "relevant_file_hints": ["views.py", "models.py"], "is_vague": false}'
        )
        container.llm_provider = mock_provider
        container.intent_parser = IntentParserService(llm_service=mock_provider)

        mock_cognee = MagicMock()
        container.cognee_service = mock_cognee
        container.indexing_service = IndexingService(cognee_service=mock_cognee)
        container.summary_generator = RepositorySummaryGenerator()
        container.source_search = SourceSearchService()

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Grounded Synthesized Context Package"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        context_uc = container.get_context_use_cases()
        req = AgentContextRequest(
            task_prompt="Modify the get_item_by_id endpoint in views.py to validate item_id parameter",
            repository_path=str(repo_path),
        )

        resp = await context_uc.get_agent_context(req)

        assert isinstance(resp, AgentContextResponse)
        assert resp.success is True
        # 1. Evidence state must be sufficient or partial
        assert resp.evidence_state in [EvidenceState.SUFFICIENT.value, EvidenceState.PARTIAL.value]
        # 2. Must not abstain
        assert resp.abstained is False
        # 3. Model claims allowed
        assert resp.model_claims_allowed is True
        # 4. Verified symbols and files present
        assert "get_item_by_id" in resp.extracted_symbols or "get_item_by_id" in resp.evidence_symbols
        assert any("views.py" in f for f in resp.related_files)
        # 5. Markdown contains verified symbols
        assert "get_item_by_id" in resp.context_markdown
        assert "<think>" not in resp.context_markdown


@pytest.mark.asyncio
async def test_runtime_acceptance_partial_case_missing_service_layer():
    """Partial Case: Route exists but service layer is absent -> partial evidence state with missing items."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "orders_app"
        repo_path.mkdir()
        (repo_path / "routes.py").write_text("def create_order(req):\n    return {'status': 'created'}\n")

        meta = InMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        mock_provider = RuntimeAcceptanceMockProvider(
            response_text='{"task_summary": "Connect create_order to database", "category": "feature", "extracted_symbols": ["create_order", "DatabaseOrderService"], "relevant_file_hints": ["routes.py"], "is_vague": false}'
        )
        container.llm_provider = mock_provider
        container.intent_parser = IntentParserService(llm_service=mock_provider)

        mock_cognee = MagicMock()
        container.cognee_service = mock_cognee
        container.indexing_service = IndexingService(cognee_service=mock_cognee)
        container.summary_generator = RepositorySummaryGenerator()
        container.source_search = SourceSearchService()

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Partial Synthesis Package"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        context_uc = container.get_context_use_cases()
        req = AgentContextRequest(
            task_prompt="Connect create_order route in routes.py to a new persistent database repository",
            repository_path=str(repo_path),
        )

        resp = await context_uc.get_agent_context(req)

        assert isinstance(resp, AgentContextResponse)
        assert resp.success is True
        # Partial evidence state because route exists but database models are not yet in codebase
        assert resp.evidence_state == EvidenceState.PARTIAL.value
        assert resp.abstained is False
        assert resp.model_claims_allowed is True
        assert "create_order" in resp.extracted_symbols or "create_order" in resp.evidence_symbols


@pytest.mark.asyncio
async def test_runtime_acceptance_provider_failure_case():
    """Provider Failure Case: Unreachable provider must NOT be conflated with absent evidence."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "user_service"
        repo_path.mkdir()
        (repo_path / "routes.py").write_text("def get_user_profile(user_id):\n    return {'id': user_id}\n")

        meta = InMemoryMetaStore()
        auth = WorkspaceAuthorizationService(metadata_store=meta, workspace_roots=[Path(tmp_dir)])
        container = ApplicationContainer.create()
        container.metadata_store = meta
        container.workspace_auth = auth

        # Provider fails on network invocation
        mock_provider = RuntimeAcceptanceMockProvider(should_fail=True)
        container.llm_provider = mock_provider
        container.intent_parser = IntentParserService(llm_service=mock_provider)

        mock_cognee = MagicMock()
        container.cognee_service = mock_cognee
        container.indexing_service = IndexingService(cognee_service=mock_cognee)
        container.summary_generator = RepositorySummaryGenerator()
        container.source_search = SourceSearchService()

        mock_pkg = MagicMock()
        mock_pkg.markdown = "# Deterministic Package"
        mock_pkg.sections = []
        mock_pkg.references = []
        container.context_service = MagicMock()
        container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

        context_uc = container.get_context_use_cases()
        req = AgentContextRequest(
            task_prompt="Modify get_user_profile route in routes.py",
            repository_path=str(repo_path),
        )

        resp = await context_uc.get_agent_context(req)

        assert isinstance(resp, AgentContextResponse)
        assert resp.success is True
        # Evidence in repository WAS found!
        assert resp.evidence_state in [EvidenceState.SUFFICIENT.value, EvidenceState.PARTIAL.value]
        # Provider invocation failed, so fallback used
        assert resp.model_invoked is False
        assert resp.fallback_used is True
        assert resp.inference_status in ["failed", "not_configured", "fallback"]
        # Must NOT claim successful model synthesis
        assert resp.model_invoked is False
        # Markdown must contain deterministic AST context
        assert "get_user_profile" in resp.context_markdown
