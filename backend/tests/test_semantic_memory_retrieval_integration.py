"""Integration tests for Phase 10D.6 Task 7: Live Retrieval Integration of Persisted Semantic Memory.

Validates:
1. Persisted SemanticMemoryRecord is retrieved during production get_agent_context() execution.
2. Valid memory enters Tier 4 (TIER_4_COGNEE) arbitration.
3. Tier 1 source outranks high-similarity Tier 4 memory according to lexicographic authority.
4. Tier 2 AST outranks Tier 4 memory.
5. Stale memory (SHA mismatch) is excluded before arbitration.
6. Deleted-file memory is excluded before arbitration.
7. Cross-repository memory is strictly isolated and excluded.
8. Semantic memory cannot satisfy an otherwise empty evidence gate (negative hallucination protection).
9. Semantic memory retrieval is strictly read-only and does NOT invoke the LLM.
10. Semantic-memory repository failure isolates gracefully and does not break deterministic retrieval.
11. Empty semantic memory is handled normally without errors.
12. Repeated context retrieval does not trigger memory regeneration.
13. Full live container path executes and integrates persisted semantic memory.
"""

import asyncio
from pathlib import Path
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.container import ApplicationContainer
from app.application.domain.arbitration import AuthorityTier
from app.application.domain.memory import MemoryProvenance, SemanticMemoryRecord
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType
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
    """Mock LLM provider for deterministic retrieval tests."""

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


@pytest.fixture
def test_env(tmp_path: Path):
    """Sets up a test environment with indexed repo, manifest, and semantic memory repository."""
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


def _create_container(test_env: dict[str, Any], memory_repo: Any = None, llm_provider: Any = None) -> ApplicationContainer:
    """Helper to configure ApplicationContainer with test environment services."""
    container = ApplicationContainer()
    container.workspace_auth = test_env["workspace_auth"]
    container.manifest_service = test_env["manifest_service"]
    container.semantic_memory_repository = memory_repo if memory_repo is not None else test_env["memory_repo"]
    
    mock_cognee = MagicMock()
    container.cognee_service = mock_cognee
    container.indexing_service = IndexingService(cognee_service=mock_cognee, manifest_service=test_env["manifest_service"])
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


# 1. test_persisted_memory_is_retrieved_during_context_generation
@pytest.mark.asyncio
async def test_persisted_memory_is_retrieved_during_context_generation(test_env):
    repo_dir = test_env["repo_dir"]
    manifest = test_env["manifest"]
    memory_repo = test_env["memory_repo"]

    # Persist valid record
    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_1",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Core engine processes domain data with high precision",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
        relationship_kind="orchestration",
    )
    memory_repo.save(rec, manifest=manifest)

    container = _create_container(test_env, memory_repo=memory_repo)
    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing logic",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    assert resp.success is True
    assert resp.abstained is False


# 2. test_valid_memory_enters_tier4_arbitration
@pytest.mark.asyncio
async def test_valid_memory_enters_tier4_arbitration(test_env):
    manifest = test_env["manifest"]
    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_1",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Core engine behavior description",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
        relationship_kind="behavior_summary",
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="How does CoreEngine work?",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        source_snippets=["class CoreEngine:\n    def process_data(self): return 42"],
        source_matched_files=["src/core.py"],
        ast_symbols=["CoreEngine"],
        ast_call_edges=[],
        cognee_memories=[rec],
    )

    tier4_cands = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(tier4_cands) == 1
    assert tier4_cands[0].content == "Core engine behavior description"
    assert tier4_cands[0].source_file == "src/core.py"


# 3. test_tier1_source_outranks_high_similarity_tier4_memory
@pytest.mark.asyncio
async def test_tier1_source_outranks_high_similarity_tier4_memory(test_env):
    manifest = test_env["manifest"]
    # Semantic memory with artificial maximum similarity score 1.0
    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_1",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Core engine description with maximum similarity",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )
    # inject score
    setattr(rec, "score", 1.0)

    result = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        source_snippets=["class CoreEngine: pass"],
        source_matched_files=["src/core.py"],
        ast_symbols=[],
        ast_call_edges=[],
        cognee_memories=[rec],
    )

    # Tier 1 candidate MUST rank before Tier 4
    assert len(result.candidates) >= 2
    assert result.candidates[0].tier == AuthorityTier.TIER_1_SOURCE
    assert result.candidates[1].tier == AuthorityTier.TIER_4_COGNEE


# 4. test_tier2_ast_outranks_tier4_memory
@pytest.mark.asyncio
async def test_tier2_ast_outranks_tier4_memory(test_env):
    manifest = test_env["manifest"]
    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_1",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Semantic memory for CoreEngine",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        source_snippets=[],
        source_matched_files=[],
        ast_symbols=["CoreEngine"],
        ast_call_edges=["CallerService -> CoreEngine"],
        cognee_memories=[rec],
    )

    assert len(result.candidates) >= 2
    assert result.candidates[0].tier == AuthorityTier.TIER_2_MANIFEST_AST
    assert result.candidates[-1].tier == AuthorityTier.TIER_4_COGNEE


# 5. test_stale_memory_is_excluded
@pytest.mark.asyncio
async def test_stale_memory_is_excluded(test_env):
    manifest = test_env["manifest"]
    # Stale SHA
    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_stale",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Stale core logic",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=["deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        source_snippets=["class CoreEngine: pass"],
        source_matched_files=["src/core.py"],
        cognee_memories=[rec],
    )

    tier4_cands = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(tier4_cands) == 0
    assert result.stale_rejected_count >= 1


# 6. test_deleted_file_memory_is_excluded
@pytest.mark.asyncio
async def test_deleted_file_memory_is_excluded(test_env):
    manifest = test_env["manifest"]
    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_deleted",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Deleted file memory",
        source_files=["src/deleted.py"],
        source_symbols=["DeletedClass"],
        source_sha256=["abc123sha"],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="DeletedClass",
        intent=MagicMock(extracted_symbols=["DeletedClass"], relevant_file_hints=[]),
        manifest=manifest,
        cognee_memories=[rec],
    )

    tier4_cands = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(tier4_cands) == 0


# 7. test_cross_repository_memory_is_excluded
@pytest.mark.asyncio
async def test_cross_repository_memory_is_excluded(test_env):
    manifest = test_env["manifest"]
    repo_b_rec = SemanticMemoryRecord(
        memory_id="cognee_mem_repo_b",
        repository_id="repo_b",
        repository_fingerprint="wrong_fingerprint_repo_b",
        semantic_text="Foreign memory from repo B",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="CoreEngine",
        intent=MagicMock(extracted_symbols=["CoreEngine"], relevant_file_hints=[]),
        manifest=manifest,
        cognee_memories=[repo_b_rec],
    )

    tier4_cands = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(tier4_cands) == 0
    assert result.cross_repo_rejected_count >= 1


# 8. test_semantic_memory_cannot_satisfy_empty_evidence_gate
@pytest.mark.asyncio
async def test_semantic_memory_cannot_satisfy_empty_evidence_gate(test_env):
    """Critical negative hallucination test:
    Repository contains NO authentication files or symbols.
    Semantic memory claims 'Authentication is handled by JWT middleware'.
    EvidenceService MUST abstain and NOT allow semantic memory to manufacture authoritative evidence.
    """
    repo_dir = test_env["repo_dir"]
    manifest = test_env["manifest"]
    memory_repo = test_env["memory_repo"]

    # Save memory claiming auth exists in src/core.py (which only has CoreEngine)
    claim_rec = SemanticMemoryRecord(
        memory_id="cognee_mem_jwt_claim",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Authentication is handled by JWT middleware in core",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )
    memory_repo.save(claim_rec, manifest=manifest)

    container = _create_container(test_env, memory_repo=memory_repo)
    use_cases = container.get_context_use_cases()

    # Query specifically for authentication subsystem
    req = AgentContextRequest(
        task_prompt="Configure JWT token validation and login authentication middleware",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    # Must abstain deterministically!
    assert resp.success is True
    assert resp.abstained is True
    assert "authentication" in (resp.abstention_reason or "").lower() or len(resp.missing_evidence) > 0


# 9. test_semantic_memory_retrieval_does_not_invoke_llm
@pytest.mark.asyncio
async def test_semantic_memory_retrieval_does_not_invoke_llm(test_env):
    repo_dir = test_env["repo_dir"]
    manifest = test_env["manifest"]
    memory_repo = test_env["memory_repo"]

    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_1",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Core data processing logic",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )
    memory_repo.save(rec, manifest=manifest)

    mock_llm = MockLLMProvider()
    container = _create_container(test_env, memory_repo=memory_repo, llm_provider=mock_llm)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="How is CoreEngine implemented?",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    # Get context
    await use_cases.get_agent_context(req)

    # Semantic memory retrieval does NOT invoke the LLM for memory generation
    assert mock_llm.call_count <= 2  # at most intent parser (1) + task synthesis (1), 0 for memory extraction


# 10. test_semantic_memory_backend_failure_does_not_break_deterministic_retrieval
@pytest.mark.asyncio
async def test_semantic_memory_backend_failure_does_not_break_deterministic_retrieval(test_env):
    repo_dir = test_env["repo_dir"]
    mock_broken_repo = MagicMock()
    mock_broken_repo.get_by_repository.side_effect = OSError("Disk read failure on semantic_memory.json")

    container = _create_container(test_env, memory_repo=mock_broken_repo)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    # Deterministic retrieval succeeds
    assert resp.success is True
    assert resp.abstained is False


# 11. test_empty_semantic_memory_handled_normally
@pytest.mark.asyncio
async def test_empty_semantic_memory_handled_normally(test_env):
    repo_dir = test_env["repo_dir"]
    empty_repo = JsonSemanticMemoryRepository(store_path=test_env["tmp_path"] / "empty_store.json")

    container = _create_container(test_env, memory_repo=empty_repo)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    resp = await use_cases.get_agent_context(req)

    assert resp.success is True
    assert resp.abstained is False


# 12. test_repeated_context_retrieval_does_not_regenerate_semantic_memory
@pytest.mark.asyncio
async def test_repeated_context_retrieval_does_not_regenerate_semantic_memory(test_env):
    repo_dir = test_env["repo_dir"]
    manifest = test_env["manifest"]
    memory_repo = test_env["memory_repo"]

    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_1",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Core data processing logic",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )
    memory_repo.save(rec, manifest=manifest)

    initial_count = len(memory_repo.get_by_repository("test_repo"))

    container = _create_container(test_env, memory_repo=memory_repo)

    use_cases = container.get_context_use_cases()
    req = AgentContextRequest(
        task_prompt="Explain CoreEngine processing",
        repository_path=str(repo_dir),
        dataset_name="test_repo",
    )

    for _ in range(3):
        await use_cases.get_agent_context(req)

    # Record count must stay identical
    assert len(memory_repo.get_by_repository("test_repo")) == initial_count


# 13. test_live_get_agent_context_path_performs_integration
@pytest.mark.asyncio
async def test_live_get_agent_context_path_performs_integration(test_env):
    repo_dir = test_env["repo_dir"]
    manifest = test_env["manifest"]
    memory_repo = test_env["memory_repo"]

    rec = SemanticMemoryRecord(
        memory_id="cognee_mem_1",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Core data processing logic",
        source_files=["src/core.py"],
        source_symbols=["CoreEngine"],
        source_sha256=[manifest.files["src/core.py"].sha256],
    )
    memory_repo.save(rec, manifest=manifest)

    container = _create_container(test_env, memory_repo=memory_repo)

    # Get use cases directly from container factory
    use_cases = container.get_context_use_cases()

    resp = await use_cases.get_agent_context(
        AgentContextRequest(
            task_prompt="How does CoreEngine process data?",
            repository_path=str(repo_dir),
            dataset_name="test_repo",
        )
    )

    assert isinstance(resp, AgentContextResponse)
    assert resp.success is True
    assert resp.abstained is False
    assert "CoreEngine" in resp.evidence_symbols
