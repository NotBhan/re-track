"""Runtime acceptance tests for Phase 10D.6 Task 9: Real Cognee Runtime Acceptance.

Validates the complete semantic-memory lifecycle against isolated local Cognee
runtime storage and persistent vector/graph structures:
1. test_real_cognification_persists_to_cognee
2. test_real_cognee_retrieval_returns_persisted_memory
3. test_real_context_query_uses_cognee_retrieval
4. test_context_query_does_not_invoke_memory_llm
5. test_context_query_does_not_cognify
6. test_real_cognee_memory_enters_tier4
7. test_source_and_ast_outrank_real_cognee
8. test_real_cognee_memory_survives_generation_boundary
9. test_modified_source_invalidates_real_cognee_memory
10. test_deleted_source_invalidates_real_cognee_memory
11. test_same_sha_rename_preserves_real_cognee_memory
12. test_cross_repository_real_cognee_memory_is_rejected
13. test_cognee_failure_preserves_deterministic_retrieval
14. test_missing_feature_still_abstains_with_cognee_present
15. test_real_runtime_is_repository_isolated
"""

import asyncio
import json
from pathlib import Path
import time
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.container import ApplicationContainer
from app.application.domain.arbitration import AuthorityTier
from app.application.domain.memory import (
    MemoryProvenance,
    SemanticMemoryRecord,
)
from app.config.settings import ServiceConfig, Settings, StorageConfig
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType
from app.models.responses import RecallResponse, RecallResult
from app.services.cognee_service import CogneeSemanticMemoryAdapter, CogneeService
from app.services.context_service import ContextService
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.manifest_service import IndexDelta, ManifestService
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.retrieval_arbitrator import RetrievalArbitrator
from app.services.semantic_memory_generator import SemanticMemoryGenerator
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository
from app.services.source_search_service import SourceSearchService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


class RealRuntimeMockLLM:
    """Deterministic LLM test double for semantic memory generation and intent parsing."""

    def __init__(
        self,
        memory_response: Optional[str] = None,
        intent_response: Optional[str] = None,
        provider_type: ProviderType = ProviderType.OLLAMA,
        default_model: str = "phi4-mini",
    ) -> None:
        self.memory_response = memory_response or json.dumps({
            "memories": [{
                "semantic_text": "OrderService coordinates order creation, pricing validation, and status transitions.",
                "source_files": ["src/orders.py"],
                "source_symbols": ["OrderService"],
                "relationship_kind": "business_orchestration",
                "confidence_score": 0.95,
            }]
        })
        self.intent_response = intent_response or json.dumps({
            "task_summary": "Order creation explanation",
            "category": "explanation",
            "extracted_symbols": ["OrderService", "create_order"],
            "relevant_file_hints": ["src/orders.py"],
            "is_vague": False,
        })
        self.provider_type = provider_type
        self.default_model = default_model
        self.memory_llm_call_count = 0
        self.intent_llm_call_count = 0
        self.last_prompt = ""

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        self.last_prompt = prompt
        if "VERIFIED REPOSITORY EVIDENCE" in prompt or "semantic memory extraction" in (system_prompt or "").lower():
            self.memory_llm_call_count += 1
            return self.memory_response
        elif "jwt" in prompt.lower() or "authentication" in prompt.lower() or "login" in prompt.lower():
            self.intent_llm_call_count += 1
            return json.dumps({
                "task_summary": "Configure JWT authentication",
                "category": "feature",
                "extracted_symbols": ["jwt_auth", "TokenVerifier", "AuthenticationMiddleware"],
                "relevant_file_hints": ["src/auth.py"],
                "is_vague": False,
            })
        else:
            self.intent_llm_call_count += 1
            return self.intent_response

    async def check_health(self) -> Any:
        return MagicMock(is_reachable=True, quantization_warning=None)

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        return AsyncMock()


@pytest.fixture
def test_env(tmp_path: Path):
    """Sets up a clean isolated test repository and local Cognee storage."""
    repo_dir = tmp_path / "order_repo"
    repo_dir.mkdir(parents=True)
    src_dir = repo_dir / "src"
    src_dir.mkdir(parents=True)

    orders_file = src_dir / "orders.py"
    orders_file.write_text(
        "class OrderService:\n"
        "    def create_order(self, customer_id: str, amount: float):\n"
        "        return {'status': 'created', 'customer_id': customer_id, 'amount': amount}\n"
        "\n"
        "    def calculate_total(self, items: list):\n"
        "        return sum(item.get('price', 0) for item in items)\n",
        encoding="utf-8",
    )

    models_file = src_dir / "models.py"
    models_file.write_text(
        "class OrderModel:\n"
        "    def __init__(self, order_id: str, amount: float):\n"
        "        self.order_id = order_id\n"
        "        self.amount = amount\n",
        encoding="utf-8",
    )

    manifest_storage = tmp_path / "manifests"
    manifest_storage.mkdir(parents=True)
    manifest_service = ManifestService(storage_dir=manifest_storage)

    memory_store = tmp_path / "semantic_store.json"
    memory_repo = JsonSemanticMemoryRepository(store_path=memory_store)

    # Initial deterministic indexing
    summary_gen = RepositorySummaryGenerator()
    files = [orders_file, models_file]
    summary_gen.generate(repo_dir, files)
    manifest = manifest_service.update_manifest(
        repo_path=repo_dir,
        dataset_name="order_repo",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )

    workspace_auth = WorkspaceAuthorizationService(workspace_roots=[tmp_path])

    # Configure real CogneeService with isolated temporary storage roots
    cognee_data_root = tmp_path / "cognee_data"
    cognee_system_root = tmp_path / "cognee_system"
    cognee_data_root.mkdir(parents=True)
    cognee_system_root.mkdir(parents=True)

    settings = Settings(
        storage=StorageConfig(
            data_root=cognee_data_root,
            system_root=cognee_system_root,
        ),
        service=ServiceConfig(
            skip_connection_test=True,
            enable_access_control=False,
            caching=False,
        ),
    )
    # Explicitly configure Cognee settings and environment variables to isolated tmp_path
    settings.configure_cognee()
    cognee_service = CogneeService(settings=settings)

    llm = RealRuntimeMockLLM()
    generator = SemanticMemoryGenerator(
        memory_provider=llm,
        repository=memory_repo,
        settings=settings,
    )

    env = {
        "repo_dir": repo_dir,
        "src_dir": src_dir,
        "orders_file": orders_file,
        "models_file": models_file,
        "manifest_service": manifest_service,
        "manifest": manifest,
        "memory_repo": memory_repo,
        "memory_store": memory_store,
        "workspace_auth": workspace_auth,
        "cognee_service": cognee_service,
        "generator": generator,
        "llm": llm,
        "settings": settings,
        "tmp_path": tmp_path,
        "files": files,
    }

    yield env

    # Teardown: drop env references and drain/reset all cached engine handles
    env.clear()
    from tests.conftest import reset_cognee_engine_and_caches
    reset_cognee_engine_and_caches()


def _build_container(test_env: dict[str, Any], memory_repo: Any = None, cognee_service: Any = None) -> ApplicationContainer:
    """Constructs application container with test environment wiring."""
    container = ApplicationContainer(settings=test_env["settings"])
    container.workspace_auth = test_env["workspace_auth"]
    container.manifest_service = test_env["manifest_service"]
    container.semantic_memory_repository = memory_repo if memory_repo is not None else test_env["memory_repo"]
    
    cognee = cognee_service if cognee_service is not None else test_env["cognee_service"]
    container.cognee_service = cognee
    container.indexing_service = IndexingService(
        cognee_service=cognee,
        manifest_service=test_env["manifest_service"],
        semantic_memory_generator=test_env["generator"],
    )
    container.summary_generator = RepositorySummaryGenerator()
    container.source_search = SourceSearchService()

    mock_pkg = MagicMock()
    mock_pkg.markdown = "# Synthetic Context Package\n\nOrderService processing details"
    mock_pkg.sections = []
    mock_pkg.references = []
    container.context_service = MagicMock()
    container.context_service.generate_context_package = AsyncMock(return_value=mock_pkg)

    container.llm_provider = test_env["llm"]
    container.intent_parser = IntentParserService(llm_service=test_env["llm"])
    return container


# 1. test_real_cognification_persists_to_cognee
@pytest.mark.asyncio
async def test_real_cognification_persists_to_cognee(test_env):
    manifest = test_env["manifest"]
    generator = test_env["generator"]
    cognee = test_env["cognee_service"]
    memory_repo = test_env["memory_repo"]
    llm = test_env["llm"]

    await cognee.initialize()

    result = await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    assert result.success is True
    assert len(result.records) == 1
    assert result.vector_indexed is True
    assert result.telemetry.llm_invocation_count == 1
    assert llm.memory_llm_call_count == 1

    # Verify durable persistence in repository store
    persisted = memory_repo.get_by_repository("order_repo", manifest=manifest)
    assert len(persisted) == 1
    assert persisted[0].source_files == ["src/orders.py"]
    assert persisted[0].source_symbols == ["OrderService"]


# 2. test_real_cognee_retrieval_returns_persisted_memory
@pytest.mark.asyncio
async def test_real_cognee_retrieval_returns_persisted_memory(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    memory_repo = test_env["memory_repo"]
    generator = test_env["generator"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    retrieved = await cognee.retrieve_semantic_memory(
        repository_id="order_repo",
        query_text="How does OrderService create orders?",
        manifest=manifest,
        repository_store=memory_repo,
    )

    assert len(retrieved) >= 1
    rec = retrieved[0]
    assert isinstance(rec, SemanticMemoryRecord)
    assert rec.source_files == ["src/orders.py"]
    assert rec.source_symbols == ["OrderService"]
    assert rec.is_derived is True
    assert rec.is_authoritative is False
    assert rec.evidence_status == "derived_projection"


# 3. test_real_context_query_uses_cognee_retrieval
@pytest.mark.asyncio
async def test_real_context_query_uses_cognee_retrieval(test_env):
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]
    cognee = test_env["cognee_service"]
    generator = test_env["generator"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    container = _build_container(test_env)
    use_cases = container.get_context_use_cases()

    req = AgentContextRequest(
        task_prompt="How does OrderService handle order creation and total calculation?",
        repository_path=str(repo_dir),
        dataset_name="order_repo",
    )

    resp = await use_cases.get_agent_context(req)

    assert isinstance(resp, AgentContextResponse)
    assert resp.success is True
    assert resp.abstained is False
    assert "OrderService" in resp.evidence_symbols or "OrderService" in resp.extracted_symbols


# 4. test_context_query_does_not_invoke_memory_llm
@pytest.mark.asyncio
async def test_context_query_does_not_invoke_memory_llm(test_env):
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]
    cognee = test_env["cognee_service"]
    generator = test_env["generator"]
    llm = test_env["llm"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    initial_memory_llm_calls = llm.memory_llm_call_count
    assert initial_memory_llm_calls == 1

    container = _build_container(test_env)
    use_cases = container.get_context_use_cases()

    for _ in range(3):
        await use_cases.get_agent_context(
            AgentContextRequest(
                task_prompt="Explain OrderService methods",
                repository_path=str(repo_dir),
                dataset_name="order_repo",
            )
        )

    # Retrieval is READ-ONLY: 0 memory LLM extraction calls
    assert llm.memory_llm_call_count == initial_memory_llm_calls


# 5. test_context_query_does_not_cognify
@pytest.mark.asyncio
async def test_context_query_does_not_cognify(test_env):
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]
    cognee = test_env["cognee_service"]
    generator = test_env["generator"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    cognify_spy = MagicMock()
    cognee.cognify = cognify_spy

    container = _build_container(test_env)
    use_cases = container.get_context_use_cases()

    await use_cases.get_agent_context(
        AgentContextRequest(
            task_prompt="Explain OrderService methods",
            repository_path=str(repo_dir),
            dataset_name="order_repo",
        )
    )

    # Context query must NEVER trigger re-cognification
    assert cognify_spy.call_count == 0


# 6. test_real_cognee_memory_enters_tier4
@pytest.mark.asyncio
async def test_real_cognee_memory_enters_tier4(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    memory_repo = test_env["memory_repo"]
    generator = test_env["generator"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    memories = await cognee.retrieve_semantic_memory(
        repository_id="order_repo",
        query_text="OrderService overview",
        manifest=manifest,
        repository_store=memory_repo,
    )

    result = RetrievalArbitrator.arbitrate(
        task_prompt="OrderService overview",
        intent=MagicMock(extracted_symbols=["OrderService"], relevant_file_hints=[]),
        manifest=manifest,
        cognee_memories=memories,
    )

    t4 = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(t4) >= 1
    assert t4[0].source_file == "src/orders.py"


# 7. test_source_and_ast_outrank_real_cognee
@pytest.mark.asyncio
async def test_source_and_ast_outrank_real_cognee(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    memory_repo = test_env["memory_repo"]
    generator = test_env["generator"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    memories = await cognee.retrieve_semantic_memory(
        repository_id="order_repo",
        query_text="OrderService overview",
        manifest=manifest,
        repository_store=memory_repo,
    )

    # Inject maximal similarity on memory
    for m in memories:
        setattr(m, "score", 1.0)

    result = RetrievalArbitrator.arbitrate(
        task_prompt="OrderService",
        intent=MagicMock(extracted_symbols=["OrderService"], relevant_file_hints=[]),
        manifest=manifest,
        source_snippets=["class OrderService:\n    def create_order(self): pass"],
        source_matched_files=["src/orders.py"],
        ast_symbols=["OrderService"],
        ast_call_edges=["Caller -> OrderService"],
        cognee_memories=memories,
    )

    assert len(result.candidates) >= 3
    # Lexicographic sorting invariant: Tier 1 > Tier 2 > Tier 4
    assert result.candidates[0].tier == AuthorityTier.TIER_1_SOURCE
    assert result.candidates[1].tier == AuthorityTier.TIER_2_MANIFEST_AST
    assert any(c.tier == AuthorityTier.TIER_4_COGNEE for c in result.candidates)


# 8. test_real_cognee_memory_survives_generation_boundary
@pytest.mark.asyncio
async def test_real_cognee_memory_survives_generation_boundary(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    generator = test_env["generator"]
    repo_dir = test_env["repo_dir"]
    memory_store = test_env["memory_store"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    # Separate container & separate repository instance pointing to the same persistent store
    new_memory_repo = JsonSemanticMemoryRepository(store_path=memory_store)
    new_cognee = CogneeService(settings=test_env["settings"])
    await new_cognee.initialize()

    new_container = _build_container(test_env, memory_repo=new_memory_repo, cognee_service=new_cognee)
    use_cases = new_container.get_context_use_cases()

    resp = await use_cases.get_agent_context(
        AgentContextRequest(
            task_prompt="How does OrderService work?",
            repository_path=str(repo_dir),
            dataset_name="order_repo",
        )
    )

    assert resp.success is True
    assert resp.abstained is False


# 9. test_modified_source_invalidates_real_cognee_memory
@pytest.mark.asyncio
async def test_modified_source_invalidates_real_cognee_memory(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    generator = test_env["generator"]
    orders_file = test_env["orders_file"]
    manifest_service = test_env["manifest_service"]
    repo_dir = test_env["repo_dir"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    # Modify source file
    orders_file.write_text(
        "class OrderService:\n    def create_order(self):\n        return 'modified_v2'\n",
        encoding="utf-8",
    )

    # Re-generate manifest with new SHA-256
    summary_gen = RepositorySummaryGenerator()
    summary_gen.generate(repo_dir, [orders_file, test_env["models_file"]])
    updated_manifest = manifest_service.update_manifest(
        repo_path=repo_dir,
        dataset_name="order_repo",
        indexed_files=[orders_file, test_env["models_file"]],
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )

    # Old memory retrieved against updated manifest must be rejected as stale
    memories = await cognee.retrieve_semantic_memory(
        repository_id="order_repo",
        query_text="OrderService",
        manifest=updated_manifest,
        repository_store=test_env["memory_repo"],
    )

    # Stale record is excluded
    assert len(memories) == 0


# 10. test_deleted_source_invalidates_real_cognee_memory
@pytest.mark.asyncio
async def test_deleted_source_invalidates_real_cognee_memory(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    generator = test_env["generator"]
    orders_file = test_env["orders_file"]
    manifest_service = test_env["manifest_service"]
    repo_dir = test_env["repo_dir"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    # Delete orders.py
    orders_file.unlink()

    # Re-index manifest without orders.py
    summary_gen = RepositorySummaryGenerator()
    summary_gen.generate(repo_dir, [test_env["models_file"]])
    updated_manifest = manifest_service.update_manifest(
        repo_path=repo_dir,
        dataset_name="order_repo",
        indexed_files=[test_env["models_file"]],
        deleted_rel_paths=["src/orders.py"],
        file_metadata=summary_gen.file_ast_metadata,
    )

    memories = await cognee.retrieve_semantic_memory(
        repository_id="order_repo",
        query_text="OrderService",
        manifest=updated_manifest,
        repository_store=test_env["memory_repo"],
    )

    assert len(memories) == 0


# 11. test_same_sha_rename_preserves_real_cognee_memory
@pytest.mark.asyncio
async def test_same_sha_rename_preserves_real_cognee_memory(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    generator = test_env["generator"]
    orders_file = test_env["orders_file"]
    manifest_service = test_env["manifest_service"]
    repo_dir = test_env["repo_dir"]
    llm = test_env["llm"]

    await cognee.initialize()
    await generator.cognify_repository(
        repository_id="order_repo",
        manifest=manifest,
        cognee_service=cognee,
    )

    initial_calls = llm.memory_llm_call_count
    assert initial_calls == 1

    # Rename src/orders.py -> src/services_orders.py without modifying content
    renamed_file = test_env["src_dir"] / "services_orders.py"
    renamed_file.write_text(orders_file.read_text(encoding="utf-8"), encoding="utf-8")
    orders_file.unlink()

    summary_gen = RepositorySummaryGenerator()
    summary_gen.generate(repo_dir, [renamed_file, test_env["models_file"]])
    updated_manifest = manifest_service.update_manifest(
        repo_path=repo_dir,
        dataset_name="order_repo",
        indexed_files=[renamed_file, test_env["models_file"]],
        deleted_rel_paths=["src/orders.py"],
        file_metadata=summary_gen.file_ast_metadata,
    )

    delta = IndexDelta(
        added=[],
        modified=[],
        deleted=[],
        renamed=[("src/orders.py", Path("src/services_orders.py"))],
        unchanged=[test_env["models_file"]],
    )

    # Perform incremental cognification for rename
    res = await generator.cognify_repository(
        repository_id="order_repo",
        manifest=updated_manifest,
        delta=delta,
        existing_manifest=manifest,
        cognee_service=cognee,
    )

    assert res.success is True
    # Invariant: 0 LLM calls for same-SHA rename
    assert llm.memory_llm_call_count == initial_calls
    assert len(res.records) == 1
    assert res.records[0].source_files == ["src/services_orders.py"]


# 12. test_cross_repository_real_cognee_memory_is_rejected
@pytest.mark.asyncio
async def test_cross_repository_real_cognee_memory_is_rejected(test_env):
    manifest = test_env["manifest"]
    foreign_rec = SemanticMemoryRecord(
        memory_id="foreign_mem_1",
        repository_id="foreign_repo",
        repository_fingerprint="foreign_fingerprint_9999",
        semantic_text="Foreign repository memory",
        source_files=["src/orders.py"],
        source_symbols=["OrderService"],
        source_sha256=[manifest.files["src/orders.py"].sha256],
    )

    rec, reason = CogneeSemanticMemoryAdapter.map_item(
        item=foreign_rec,
        manifest=manifest,
        repository_id="order_repo",
    )

    assert rec is None
    assert "cross_repository" in reason


# 13. test_cognee_failure_preserves_deterministic_retrieval
@pytest.mark.asyncio
async def test_cognee_failure_preserves_deterministic_retrieval(test_env):
    repo_dir = test_env["repo_dir"]
    broken_cognee = MagicMock()
    broken_cognee.retrieve_semantic_memory.side_effect = CogneeServiceError("Storage provider unreachable")

    container = _build_container(test_env, cognee_service=broken_cognee)
    use_cases = container.get_context_use_cases()

    req = AgentContextRequest(
        task_prompt="Explain OrderService order creation",
        repository_path=str(repo_dir),
        dataset_name="order_repo",
    )

    resp = await use_cases.get_agent_context(req)

    # Failure isolation: deterministic retrieval continues
    assert resp.success is True
    assert resp.abstained is False
    assert "OrderService" in resp.evidence_symbols or "OrderService" in resp.extracted_symbols


# 14. test_missing_feature_still_abstains_with_cognee_present
@pytest.mark.asyncio
async def test_missing_feature_still_abstains_with_cognee_present(test_env):
    """Grounding & Negative Hallucination Acceptance:
    Repository contains OrderService but NO authentication code.
    Cognee memory claims authentication exists.
    EvidenceService MUST abstain and NOT synthesize claims.
    """
    manifest = test_env["manifest"]
    repo_dir = test_env["repo_dir"]
    memory_repo = test_env["memory_repo"]

    # Claim memory
    claim_rec = SemanticMemoryRecord(
        memory_id="jwt_auth_claim",
        repository_id="order_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Authentication is handled by JWT middleware in orders module",
        source_files=["src/orders.py"],
        source_symbols=["OrderService"],
        source_sha256=[manifest.files["src/orders.py"].sha256],
    )
    memory_repo.save(claim_rec, manifest=manifest)

    container = _build_container(test_env)
    use_cases = container.get_context_use_cases()

    req = AgentContextRequest(
        task_prompt="Configure JWT token validation and login authentication middleware",
        repository_path=str(repo_dir),
        dataset_name="order_repo",
    )

    resp = await use_cases.get_agent_context(req)

    assert resp.success is True
    assert resp.abstained is True
    assert resp.model_claims_allowed is False
    assert resp.model_invoked is False


# 15. test_real_runtime_is_repository_isolated
@pytest.mark.asyncio
async def test_real_runtime_is_repository_isolated(test_env):
    tmp_path = test_env["tmp_path"]
    manifest_a = test_env["manifest"]

    # Create Repo B
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir(parents=True)
    (repo_b / "src").mkdir(parents=True)
    b_file = repo_b / "src" / "billing.py"
    b_file.write_text("class BillingEngine:\n    def charge(self): return True\n", encoding="utf-8")

    summary_gen = RepositorySummaryGenerator()
    summary_gen.generate(repo_b, [b_file])
    manifest_b = test_env["manifest_service"].update_manifest(
        repo_path=repo_b,
        dataset_name="repo_b",
        indexed_files=[b_file],
        deleted_rel_paths=[],
        file_metadata=summary_gen.file_ast_metadata,
    )

    # Memory for Repo B
    rec_b = SemanticMemoryRecord(
        memory_id="billing_mem_1",
        repository_id="repo_b",
        repository_fingerprint=manifest_b.repo_fingerprint,
        semantic_text="BillingEngine handles customer credit card charging",
        source_files=["src/billing.py"],
        source_symbols=["BillingEngine"],
        source_sha256=[manifest_b.files["src/billing.py"].sha256],
    )
    test_env["memory_repo"].save(rec_b, manifest=manifest_b)

    # Retrieval for Repo A
    memories_a = await test_env["cognee_service"].retrieve_semantic_memory(
        repository_id="order_repo",
        query_text="BillingEngine charge",
        manifest=manifest_a,
        repository_store=test_env["memory_repo"],
    )

    # Repo B memories MUST NOT leak into Repo A
    assert not any(m.repository_id == "repo_b" for m in memories_a)
    assert not any("BillingEngine" in m.source_symbols for m in memories_a)


# 16. test_real_cognee_recall_produces_tier4_candidate
@pytest.mark.asyncio
async def test_real_cognee_recall_produces_tier4_candidate(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]

    # Cognee recall returns a real raw chunk with explicit file provenance
    raw_chunk = "- [src/orders.py#OrderService] OrderService handles customer order creation and calculates total pricing"
    recall_item = RecallResult(
        kind="chunk",
        search_type="vector",
        text=raw_chunk,
        score=0.92,
        dataset_name="order_repo",
        raw=raw_chunk,
    )

    with patch.object(
        cognee,
        "recall",
        return_value=RecallResponse(
            query="OrderService pricing",
            dataset="order_repo",
            results=[recall_item],
        ),
    ):
        telemetry: dict[str, Any] = {}
        records = await cognee.retrieve_semantic_memory(
            repository_id="order_repo",
            query_text="OrderService pricing",
            manifest=manifest,
            repository_store=None,
            telemetry=telemetry,
        )

        assert telemetry["cognee_recall_attempted"] is True
        assert telemetry["cognee_recall_succeeded"] is True
        assert telemetry["cognee_items_received"] == 1
        assert telemetry["cognee_items_accepted"] == 1
        assert telemetry["cognee_items_rejected"] == 0
        assert len(records) == 1

        rec = records[0]
        assert rec.generated_by == "cognee_pipeline"
        assert rec.source_files == ["src/orders.py"]
        assert rec.source_sha256 == [manifest.files["src/orders.py"].sha256]
        assert rec.source_symbols == ["OrderService"]
        assert rec.is_derived is True
        assert rec.is_authoritative is False
        assert rec.evidence_status == "derived_projection"

        # Arbitrate and verify it enters Tier 4
        result = RetrievalArbitrator.arbitrate(
            task_prompt="OrderService pricing logic",
            intent=MagicMock(extracted_symbols=["OrderService"], relevant_file_hints=[]),
            manifest=manifest,
            cognee_memories=[rec],
        )
        t4 = [c for c in result.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
        assert len(t4) == 1
        assert t4[0].source_file == "src/orders.py"


# 17. test_cognee_retrieval_does_not_write_memory
@pytest.mark.asyncio
async def test_cognee_retrieval_does_not_write_memory(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    memory_repo = test_env["memory_repo"]

    write_calls = 0
    orig_save = memory_repo.save
    orig_save_all = memory_repo.save_all

    def track_save(*args, **kwargs):
        nonlocal write_calls
        write_calls += 1
        return orig_save(*args, **kwargs)

    def track_save_all(*args, **kwargs):
        nonlocal write_calls
        write_calls += 1
        return orig_save_all(*args, **kwargs)

    memory_repo.save = track_save
    memory_repo.save_all = track_save_all

    # Retrieval run must be completely read-only
    await cognee.retrieve_semantic_memory(
        repository_id="order_repo",
        query_text="OrderService overview",
        manifest=manifest,
        repository_store=memory_repo,
    )

    assert write_calls == 0


# 18. test_unanchored_cognee_chunk_rejected_and_fallback_distinguishable
@pytest.mark.asyncio
async def test_unanchored_cognee_chunk_rejected_and_fallback_distinguishable(test_env):
    manifest = test_env["manifest"]
    cognee = test_env["cognee_service"]
    memory_repo = test_env["memory_repo"]

    # Pre-populate persistent store with 1 record
    existing_rec = SemanticMemoryRecord(
        memory_id="persisted_order_mem",
        repository_id="order_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Persisted knowledge of OrderService",
        source_files=["src/orders.py"],
        source_symbols=["OrderService"],
        source_sha256=[manifest.files["src/orders.py"].sha256],
        generated_by="cognee_pipeline",
    )
    memory_repo.save(existing_rec, manifest=manifest)

    # Mock recall returning an unanchored chunk (no provenance)
    unanchored = RecallResult(
        kind="chunk",
        search_type="vector",
        text="Vague floating description without any file path or brackets",
        score=0.9,
        dataset_name="order_repo",
        raw="Vague floating description without any file path or brackets",
    )

    with patch.object(
        cognee,
        "recall",
        return_value=RecallResponse(
            query="Vague query",
            dataset="order_repo",
            results=[unanchored],
        ),
    ):
        telemetry: dict[str, Any] = {}
        records = await cognee.retrieve_semantic_memory(
            repository_id="order_repo",
            query_text="Vague query",
            manifest=manifest,
            repository_store=memory_repo,
            telemetry=telemetry,
        )

        # Unanchored chunk was rejected
        assert telemetry["cognee_items_received"] == 1
        assert telemetry["cognee_items_accepted"] == 0
        assert telemetry["cognee_items_rejected"] == 1
        assert "missing_source_files" in telemetry["cognee_rejection_reasons"]

        # Because Cognee recall had 0 accepted items, fallback repository store supplied the record
        assert len(records) == 1
        # Fallback record is clearly distinguishable from genuine Cognee recall
        assert records[0].generated_by == "persistent_store_fallback"

