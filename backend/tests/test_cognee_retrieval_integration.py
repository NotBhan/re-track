"""Integration tests for Phase 10D.6 Task 8: Actual Cognee Semantic Retrieval Integration.

Validates:
1. test_live_context_query_retrieves_cognee_memory
2. test_cognee_result_is_mapped_to_semantic_memory_record
3. test_cognee_memory_enters_tier4
4. test_tier1_source_outranks_cognee
5. test_tier2_ast_outranks_cognee
6. test_stale_cognee_memory_is_rejected
7. test_deleted_file_cognee_memory_is_rejected
8. test_cross_repository_cognee_memory_is_rejected
9. test_cognee_cannot_create_missing_feature_evidence
10. test_cognee_retrieval_does_not_invoke_memory_llm
11. test_cognee_retrieval_does_not_trigger_cognify
12. test_cognee_outage_preserves_source_ast_retrieval
13. test_empty_cognee_memory_is_valid
14. test_context_retrieval_does_not_recursive_self_feed
15. test_production_get_agent_context_uses_cognee_retrieval
"""

import asyncio
from pathlib import Path
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.container import ApplicationContainer
from app.application.domain.arbitration import AuthorityTier
from app.application.domain.memory import MemoryProvenance, SemanticMemoryRecord
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType
from app.models.responses import RecallResponse, RecallResult
from app.services.cognee_service import CogneeSemanticMemoryAdapter, CogneeService
from app.services.context_service import ContextService
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.manifest_service import ManifestService
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.retrieval_arbitrator import RetrievalArbitrator
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository
from app.services.source_search_service import SourceSearchService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


class MockLLMProvider:
    """Mock LLM provider tracking calls."""

    def __init__(
        self,
        response_text: str = "",
        provider_type: ProviderType = ProviderType.OLLAMA,
        default_model: str = "phi4-mini",
        raise_error: Optional[Exception] = None,
    ) -> None:
        self.response_text = response_text
        self.provider_type = provider_type
        self.default_model = default_model
        self.raise_error = raise_error
        self.call_count: int = 0

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.call_count += 1
        if self.raise_error:
            raise self.raise_error
        return self.response_text

    async def check_health(self) -> Any:
        return MagicMock(is_reachable=True, quantization_warning=None)

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        return AsyncMock()


class MockCogneeRecallService:
    """Mock CogneeService for testing recall and semantic memory retrieval."""

    def __init__(self, recall_results: Optional[list[Any]] = None, should_fail: bool = False) -> None:
        self.recall_results = recall_results or []
        self.should_fail = should_fail
        self._initialized = True
        self.retrieve_call_count = 0
        self.recall_call_count = 0
        self.cognify_call_count = 0
        self.remember_call_count = 0

    async def recall(self, query_text: str, datasets: list[str], top_k: int = 15, **kwargs: Any) -> RecallResponse:
        self.recall_call_count += 1
        if self.should_fail:
            raise CogneeServiceError("Vector database connection timed out")
        return RecallResponse(
            query=query_text,
            dataset=", ".join(datasets),
            results=self.recall_results,
        )

    async def retrieve_semantic_memory(
        self,
        repository_id: str,
        query_text: str,
        manifest: Any,
        top_k: int = 15,
        repository_store: Optional[Any] = None,
        **kwargs: Any,
    ) -> list[SemanticMemoryRecord]:
        self.retrieve_call_count += 1
        if self.should_fail:
            raise CogneeServiceError("Cognee LanceDB retrieval failed")

        candidates = list(self.recall_results)
        if repository_store is not None:
            persisted = repository_store.get_by_repository(
                repository_id=repository_id,
                manifest=manifest,
                include_stale=False,
            )
            for p in persisted:
                if p not in candidates:
                    candidates.append(p)

        return CogneeSemanticMemoryAdapter.map_items(
            items=candidates,
            manifest=manifest,
            repository_id=repository_id,
        )

    async def cognify(self, dataset_name: Optional[str] = None) -> Any:
        self.cognify_call_count += 1
        return MagicMock()

    async def remember(self, data: Any, dataset_name: str = "default", **kwargs: Any) -> Any:
        self.remember_call_count += 1
        return MagicMock()


@pytest.fixture
def test_env(tmp_path: Path):
    """Sets up a test environment with indexed repo, manifest, and memory components."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir(parents=True)
    src_dir = repo_dir / "src"
    src_dir.mkdir(parents=True)

    core_file = src_dir / "core.py"
    core_file.write_text(
        "class CoreEngine:\n    def process_data(self):\n        return 42\n",
        encoding="utf-8",
    )

    utils_file = src_dir / "utils.py"
    utils_file.write_text(
        "def format_output(val):\n    return str(val).strip()\n",
        encoding="utf-8",
    )

    manifest_storage = tmp_path / "manifests"
    manifest_storage.mkdir(parents=True)
    manifest_service = ManifestService(storage_dir=manifest_storage)

    memory_store = tmp_path / "sem_mem.json"
    memory_repo = JsonSemanticMemoryRepository(store_path=memory_store)

    # Index repository deterministically
    summary_gen = RepositorySummaryGenerator()
    files = [core_file, utils_file]
    summary_gen.generate(repo_dir, files)
    manifest = manifest_service.update_manifest(
        repo_path=repo_dir,
        dataset_name="test_repo",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )

    workspace_auth = WorkspaceAuthorizationService(workspace_roots=[tmp_path])

    return {
        "repo_dir": repo_dir,
        "src_dir": src_dir,
        "manifest_service": manifest_service,
        "manifest": manifest,
        "memory_repo": memory_repo,
        "memory_store": memory_store,
        "tmp_path": tmp_path,
        "files": files,
        "workspace_auth": workspace_auth,
    }


def _create_container(
    test_env: dict[str, Any],
    memory_repo: Any = None,
    cognee_service: Any = None,
    llm_provider: Any = None,
) -> ApplicationContainer:
    """Helper to configure ApplicationContainer with test environment services."""
    container = ApplicationContainer()
    container.workspace_auth = test_env["workspace_auth"]
    container.manifest_service = test_env["manifest_service"]
    container.semantic_memory_repository = memory_repo if memory_repo is not None else test_env["memory_repo"]
    
    cognee = cognee_service if cognee_service is not None else MockCogneeRecallService()
    container.cognee_service = cognee
    container.indexing_service = IndexingService(
        cognee_service=cognee,
        manifest_service=test_env["manifest_service"],
    )
    container.summary_generator = RepositorySummaryGenerator()
    container.source_search = SourceSearchService()

    mock_pkg = MagicMock()
    mock_pkg.markdown = "# Synthetic Context Package\n\nContext details"
    mock_pkg.sections = []
    mock_pkg.references = []
    container.context_service = MagicMock()
    container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

    llm = llm_provider if llm_provider is not None else MockLLMProvider()
    container.llm_provider = llm
    container.intent_parser = IntentParserService(llm_service=llm)
    return container


# 1. test_live_context_query_retrieves_cognee_memory
@pytest.mark.asyncio
async def test_live_context_query_retrieves_cognee_memory(test_env):
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]

    # Cognee recall result with valid provenance
    raw_item = {
        "memory_id": "cognee_mem_live_1",
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
        "semantic_text": "CoreEngine handles business data transformation",
        "source_files": ["src/core.py"],
        "source_symbols": ["CoreEngine"],
        "source_sha256": [manifest.files["src/core.py"].sha256],
        "relationship_kind": "domain_logic",
        "score": 0.88,
    }
    recall_item = RecallResult(
        kind="concept",
        search_type="vector",
        text="CoreEngine handles business data transformation",
        score=0.88,
        dataset_name="test_repo",
        raw=raw_item,
    )

    cognee = MockCogneeRecallService(recall_results=[recall_item])
    container = _create_container(test_env, cognee_service=cognee)
    use_cases = container.get_context_use_cases()

    req = AgentContextRequest(
        task_prompt="Explain how CoreEngine processes data",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    assert resp.success is True
    assert resp.abstained is False
    assert cognee.retrieve_call_count == 1


# 2. test_cognee_result_is_mapped_to_semantic_memory_record
def test_cognee_result_is_mapped_to_semantic_memory_record(test_env):
    manifest = test_env["manifest"]
    raw_item = {
        "id": "raw_cognee_1",
        "text": "CoreEngine computation pipeline",
        "source_files": ["src/core.py"],
        "source_symbols": ["CoreEngine"],
        "source_sha256": [manifest.files["src/core.py"].sha256],
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
        "relationship_kind": "pipeline",
    }
    recall_res = RecallResult(
        kind="summary",
        search_type="graph",
        text="CoreEngine computation pipeline",
        score=0.92,
        dataset_name="test_repo",
        raw=raw_item,
    )

    record, reason = CogneeSemanticMemoryAdapter.map_item(
        item=recall_res,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert reason == "valid"
    assert isinstance(record, SemanticMemoryRecord)
    assert record.memory_id == "raw_cognee_1"
    assert record.semantic_text == "CoreEngine computation pipeline"
    assert record.source_files == ["src/core.py"]
    assert record.source_symbols == ["CoreEngine"]
    assert record.is_derived is True
    assert record.is_authoritative is False
    assert record.evidence_status == "derived_projection"
    assert record.generated_by == "cognee_pipeline"


# 3. test_cognee_memory_enters_tier4
def test_cognee_memory_enters_tier4(test_env):
    manifest = test_env["manifest"]
    record = SemanticMemoryRecord(
        memory_id="cognee_t4_mem",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Cognee semantic summary of CoreEngine",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine overview",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        cognee_memories=[record],
    )

    t4 = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(t4) == 1
    assert t4[0].content == "Cognee semantic summary of CoreEngine"
    assert t4[0].source_file == "src/core.py"


# 4. test_tier1_source_outranks_cognee
def test_tier1_source_outranks_cognee(test_env):
    manifest = test_env["manifest"]
    record = SemanticMemoryRecord(
        memory_id="cognee_high_sim",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Super high similarity semantic memory",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )
    setattr(record, "score", 1.0)

    result = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        source_snippets=["class CoreEngine:\n    def process_data(self): return 42"],
        source_matched_files=["src/core.py"],
        cognee_memories=[record],
    )

    assert len(result.candidates) >= 2
    assert result.candidates[0].tier == AuthorityTier.TIER_1_SOURCE
    assert result.candidates[1].tier == AuthorityTier.TIER_4_COGNEE


# 5. test_tier2_ast_outranks_cognee
def test_tier2_ast_outranks_cognee(test_env):
    manifest = test_env["manifest"]
    record = SemanticMemoryRecord(
        memory_id="cognee_mem_ast_cmp",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Cognee derived summary",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        ast_symbols=["CoreEngine"],
        ast_call_edges=["CallerService -> CoreEngine"],
        cognee_memories=[record],
    )

    assert len(result.candidates) >= 2
    assert result.candidates[0].tier == AuthorityTier.TIER_2_MANIFEST_AST
    assert result.candidates[-1].tier == AuthorityTier.TIER_4_COGNEE


# 6. test_stale_cognee_memory_is_rejected
def test_stale_cognee_memory_is_rejected(test_env):
    manifest = test_env["manifest"]
    raw_stale = {
        "id": "stale_cognee_1",
        "text": "Stale logic",
        "source_files": ["src/core.py"],
        "source_symbols": ["CoreEngine"],
        "source_sha256": ["stale_sha256_hash_here_1234567890"],
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(
        item=raw_stale,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert record is None
    assert "source_sha256_stale" in reason


# 7. test_deleted_file_cognee_memory_is_rejected
def test_deleted_file_cognee_memory_is_rejected(test_env):
    manifest = test_env["manifest"]
    raw_deleted = {
        "id": "deleted_file_cognee",
        "text": "Memory for removed file",
        "source_files": ["src/removed_module.py"],
        "source_symbols": ["RemovedClass"],
        "source_sha256": ["sha_deleted"],
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(
        item=raw_deleted,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert record is None
    assert "unknown_source_file" in reason


# 8. test_cross_repository_cognee_memory_is_rejected
def test_cross_repository_cognee_memory_is_rejected(test_env):
    manifest = test_env["manifest"]
    raw_foreign = {
        "id": "foreign_repo_cognee",
        "text": "Memory belonging to repo B",
        "source_files": ["src/core.py"],
        "source_symbols": ["CoreEngine"],
        "source_sha256": [manifest.files["src/core.py"].sha256],
        "repository_id": "other_repo_b",
        "repository_fingerprint": "foreign_fingerprint_xyz",
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(
        item=raw_foreign,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert record is None
    assert "cross_repository" in reason


# 9. test_cognee_cannot_create_missing_feature_evidence
@pytest.mark.asyncio
async def test_cognee_cannot_create_missing_feature_evidence(test_env):
    """Negative hallucination test:
    Repository contains NO authentication code.
    Cognee memory claims JWT authentication exists.
    EvidenceService MUST abstain and NOT allow Cognee to manufacture authoritative evidence.
    """
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]

    # Cognee memory claiming authentication exists in src/core.py
    raw_claim = {
        "id": "jwt_cognee_claim",
        "text": "JWT authentication is handled by AuthenticationMiddleware in core",
        "source_files": ["src/core.py"],
        "source_symbols": ["CoreEngine"],
        "source_sha256": [manifest.files["src/core.py"].sha256],
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
    }
    recall_item = RecallResult(
        kind="concept",
        search_type="vector",
        text="JWT authentication is handled by AuthenticationMiddleware in core",
        score=0.99,
        dataset_name="test_repo",
        raw=raw_claim,
    )

    cognee = MockCogneeRecallService(recall_results=[recall_item])
    container = _create_container(test_env, cognee_service=cognee)
    use_cases = container.get_context_use_cases()

    req = AgentContextRequest(
        task_prompt="Configure JWT token validation and login authentication middleware",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    # Must abstain deterministically!
    assert resp.success is True
    assert resp.abstained is True
    assert resp.model_claims_allowed is False
    assert "authentication" in (resp.abstention_reason or "").lower() or len(resp.missing_evidence) > 0


# 10. test_cognee_retrieval_does_not_invoke_memory_llm
@pytest.mark.asyncio
async def test_cognee_retrieval_does_not_invoke_memory_llm(test_env):
    repo_dir = test_env["repo_dir"]
    mock_llm = MockLLMProvider()
    cognee = MockCogneeRecallService()
    container = _create_container(test_env, cognee_service=cognee, llm_provider=mock_llm)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    await use_cases.get_agent_context(req)

    # Memory extraction LLM was NOT invoked during context retrieval
    assert mock_llm.call_count <= 1  # at most intent parser (1), 0 for memory generation


# 11. test_cognee_retrieval_does_not_trigger_cognify
@pytest.mark.asyncio
async def test_cognee_retrieval_does_not_trigger_cognify(test_env):
    repo_dir = test_env["repo_dir"]
    cognee = MockCogneeRecallService()
    container = _create_container(test_env, cognee_service=cognee)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    await use_cases.get_agent_context(req)

    # Cognification is NOT triggered during context retrieval
    assert cognee.cognify_call_count == 0


# 12. test_cognee_outage_preserves_source_ast_retrieval
@pytest.mark.asyncio
async def test_cognee_outage_preserves_source_ast_retrieval(test_env):
    repo_dir = test_env["repo_dir"]
    broken_cognee = MockCogneeRecallService(should_fail=True)
    container = _create_container(test_env, cognee_service=broken_cognee)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    # Deterministic retrieval succeeds even if Cognee fails
    assert resp.success is True
    assert resp.abstained is False
    assert "CoreEngine" in resp.evidence_symbols


# 13. test_empty_cognee_memory_is_valid
@pytest.mark.asyncio
async def test_empty_cognee_memory_is_valid(test_env):
    repo_dir = test_env["repo_dir"]
    empty_cognee = MockCogneeRecallService(recall_results=[])
    container = _create_container(test_env, cognee_service=empty_cognee)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    assert resp.success is True
    assert resp.abstained is False


# 14. test_context_retrieval_does_not_recursive_self_feed
@pytest.mark.asyncio
async def test_context_retrieval_does_not_recursive_self_feed(test_env):
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]

    raw_item = {
        "id": "recalled_item",
        "text": "CoreEngine processing pipeline",
        "source_files": ["src/core.py"],
        "source_symbols": ["CoreEngine"],
        "source_sha256": [manifest.files["src/core.py"].sha256],
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
    }
    recall_item = RecallResult(
        kind="concept",
        search_type="vector",
        text="CoreEngine processing pipeline",
        score=0.9,
        dataset_name="test_repo",
        raw=raw_item,
    )

    cognee = MockCogneeRecallService(recall_results=[recall_item])
    container = _create_container(test_env, cognee_service=cognee)
    use_cases = container.get_context_use_cases()

    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    for _ in range(3):
        await use_cases.get_agent_context(req)

    # Retrieval did not call remember() or cognify() to re-inject memory
    assert cognee.remember_call_count == 0
    assert cognee.cognify_call_count == 0


# 15. test_production_get_agent_context_uses_cognee_retrieval
@pytest.mark.asyncio
async def test_production_get_agent_context_uses_cognee_retrieval(test_env):
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]

    raw_item = {
        "id": "prod_cognee_mem_1",
        "text": "CoreEngine domain processing logic",
        "source_files": ["src/core.py"],
        "source_symbols": ["CoreEngine"],
        "source_sha256": [manifest.files["src/core.py"].sha256],
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
    }
    recall_item = RecallResult(
        kind="concept",
        search_type="vector",
        text="CoreEngine domain processing logic",
        score=0.91,
        dataset_name="test_repo",
        raw=raw_item,
    )

    cognee = MockCogneeRecallService(recall_results=[recall_item])
    container = _create_container(test_env, cognee_service=cognee)

    # Obtain ContextUseCases directly from the container
    use_cases = container.get_context_use_cases()

    resp = await use_cases.get_agent_context(
        AgentContextRequest(
            task_prompt="How is CoreEngine implemented?",
            repository_path=str(repo_dir),
            dataset_name="test_repo",
        )
    )

    assert isinstance(resp, AgentContextResponse)
    assert resp.success is True
    assert resp.abstained is False
    assert cognee.retrieve_call_count >= 1


# 16. test_raw_chunk_with_explicit_file_path_is_mapped
def test_raw_chunk_with_explicit_file_path_is_mapped(test_env):
    manifest = test_env["manifest"]
    raw_chunk = "- [src/core.py#CoreEngine] CoreEngine computes core deterministic calculations"

    rec, reason = CogneeSemanticMemoryAdapter.map_item(
        item=raw_chunk,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert rec is not None
    assert reason == "valid"
    assert rec.source_files == ["src/core.py"]
    assert rec.source_sha256 == [manifest.files["src/core.py"].sha256]
    assert rec.is_derived is True
    assert rec.is_authoritative is False
    assert rec.evidence_status == "derived_projection"
    assert rec.generated_by == "cognee_pipeline"

    # Verify Tier 4 compatibility in arbitration
    arb = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine calculation",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        cognee_memories=[rec],
    )
    t4 = [c for c in arb.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(t4) == 1
    assert t4[0].source_file == "src/core.py"


# 17. test_raw_chunk_with_unknown_file_is_rejected
def test_raw_chunk_with_unknown_file_is_rejected(test_env):
    manifest = test_env["manifest"]
    raw_chunk = "- [src/unknown_module.py] Fictional module description"

    rec, reason = CogneeSemanticMemoryAdapter.map_item(
        item=raw_chunk,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert rec is None
    assert reason == "unknown_source_file:src/unknown_module.py"


# 18. test_raw_chunk_without_provenance_is_rejected
def test_raw_chunk_without_provenance_is_rejected(test_env):
    manifest = test_env["manifest"]
    raw_chunk = "Generic natural language text mentioning CoreEngine but without file headers or brackets"

    rec, reason = CogneeSemanticMemoryAdapter.map_item(
        item=raw_chunk,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert rec is None
    assert reason == "missing_source_files"


# 19. test_raw_chunk_never_invents_symbol
def test_raw_chunk_never_invents_symbol(test_env):
    manifest = test_env["manifest"]
    # Chunk has explicit file bracket, but no #Symbol token
    raw_chunk = "- [src/core.py] CoreEngine and ExtraWorker perform core data transforms"

    rec, reason = CogneeSemanticMemoryAdapter.map_item(
        item=raw_chunk,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert rec is not None
    assert reason == "valid"
    assert rec.source_files == ["src/core.py"]
    # Missing symbol remains absent: no symbol fabricated from semantic text
    assert rec.source_symbols == []


# 20. test_stale_chunk_is_rejected
def test_stale_chunk_is_rejected(test_env):
    manifest = test_env["manifest"]
    stale_item = {
        "text": "- [src/core.py] CoreEngine old logic",
        "source_files": ["src/core.py"],
        "source_sha256": ["0123456789abcdef" * 4],
        "repository_id": "test_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
    }

    rec, reason = CogneeSemanticMemoryAdapter.map_item(
        item=stale_item,
        manifest=manifest,
        repository_id="test_repo",
    )

    assert rec is None
    assert reason == "source_sha256_stale:src/core.py"


# 21. test_cross_repository_chunk_is_rejected
def test_cross_repository_chunk_is_rejected(test_env):
    manifest = test_env["manifest"]
    # 1. Foreign fingerprint
    cross_fp_item = {
        "text": "- [src/core.py] CoreEngine logic",
        "source_files": ["src/core.py"],
        "repository_id": "test_repo",
        "repository_fingerprint": "foreign_repo_fp_xyz",
    }
    rec1, reason1 = CogneeSemanticMemoryAdapter.map_item(
        item=cross_fp_item,
        manifest=manifest,
        repository_id="test_repo",
    )
    assert rec1 is None
    assert reason1 == "cross_repository_fingerprint_mismatch"

    # 2. Foreign dataset/repository_id
    cross_id_item = {
        "text": "- [src/core.py] CoreEngine logic",
        "source_files": ["src/core.py"],
        "repository_id": "completely_different_repo",
        "repository_fingerprint": manifest.repo_fingerprint,
    }
    rec2, reason2 = CogneeSemanticMemoryAdapter.map_item(
        item=cross_id_item,
        manifest=manifest,
        repository_id="test_repo",
    )
    assert rec2 is None
    assert reason2 == "cross_repository_id_mismatch"


# 22. test_cognee_failure_is_distinguishable_from_empty_recall
@pytest.mark.asyncio
async def test_cognee_failure_is_distinguishable_from_empty_recall(test_env):
    manifest = test_env["manifest"]
    cognee = CogneeService(settings=test_env.get("settings") or MagicMock())

    # 1. Case: Cognee recall throws failure
    with patch.object(cognee, "recall", side_effect=CogneeServiceError("Connection refused")):
        fail_telemetry: dict[str, Any] = {}
        res_fail = await cognee.retrieve_semantic_memory(
            repository_id="test_repo",
            query_text="CoreEngine",
            manifest=manifest,
            repository_store=None,
            telemetry=fail_telemetry,
        )
        assert res_fail == []
        assert fail_telemetry["cognee_recall_attempted"] is True
        assert fail_telemetry["cognee_recall_succeeded"] is False
        assert fail_telemetry["cognee_items_received"] == 0

    # 2. Case: Cognee recall succeeds but returns empty
    with patch.object(cognee, "recall", return_value=RecallResponse(query="CoreEngine", dataset="test_repo", results=[])):
        empty_telemetry: dict[str, Any] = {}
        res_empty = await cognee.retrieve_semantic_memory(
            repository_id="test_repo",
            query_text="CoreEngine",
            manifest=manifest,
            repository_store=None,
            telemetry=empty_telemetry,
        )
        assert res_empty == []
        assert empty_telemetry["cognee_recall_attempted"] is True
        assert empty_telemetry["cognee_recall_succeeded"] is True
        assert empty_telemetry["cognee_items_received"] == 0
        assert empty_telemetry["cognee_items_accepted"] == 0
        assert empty_telemetry["cognee_items_rejected"] == 0

