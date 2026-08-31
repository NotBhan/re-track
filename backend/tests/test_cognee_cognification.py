"""Comprehensive unit tests for Real Cognee Cognification & Persistent Semantic Memory Integration (Phase 10D.6 Task 5).

Validates:
1. End-to-end repository cognification orchestration with exactly-once LLM extraction.
2. Granular incremental lifecycle: selective modification re-extraction, deletion invalidation, and same-SHA rename path preservation with 0 LLM calls.
3. Strict non-recursive self-feeding guarantee (only raw source/AST evidence feeds the generator).
4. Provenance validation, cross-repository rejection, graceful degradation on Cognee/LanceDB outages, and truthful telemetry.
5. Safe entry of validated Cognee semantic memories into Tier-4 retrieval arbitration.
"""

import json
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.domain.arbitration import AuthorityTier
from app.application.domain.memory import (
    SemanticMemoryGenerationInput,
    SemanticMemoryRecord,
)
from app.models.provider import ProviderType
from app.models.responses import RecallResponse, RecallResult
from app.services.cognee_service import CogneeService, sanitize_dataset_name
from app.services.manifest_service import FileFingerprint, IndexDelta, RepositoryManifest
from app.services.retrieval_arbitrator import RetrievalArbitrator
from app.services.semantic_memory_generator import (
    SemanticMemoryGenerator,
    build_generation_prompt,
)
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository


class MockLLMProvider:
    """Mock LLM provider for deterministic unit tests."""

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
        self.last_prompt: Optional[str] = None
        self.last_system_prompt: Optional[str] = None
        self.last_model: Optional[str] = None
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
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        self.last_model = model

        if self.raise_error:
            raise self.raise_error

        return self.response_text

    async def check_health(self) -> Any:
        return AsyncMock()

    async def list_models(self) -> list[Any]:
        return []

    async def discover_models(self, *args: Any, **kwargs: Any) -> Any:
        return AsyncMock()


class MockCogneeService:
    """Mock CogneeService for testing vector/graph indexing delegation."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.add_calls: list[dict[str, Any]] = []
        self.cognify_calls: list[str] = []
        self.recall_calls: list[dict[str, Any]] = []
        self._initialized = True

    async def add(self, data: Any, dataset_name: str = "default", **kwargs: Any) -> Any:
        if self.should_fail:
            raise RuntimeError("LanceDB storage unavailable")
        self.add_calls.append({"data": data, "dataset_name": dataset_name, **kwargs})
        return MagicMock(dataset_name=dataset_name, items_sent=1)

    async def cognify(self, dataset_name: Optional[str] = None) -> dict[str, Any]:
        self.cognify_calls.append(dataset_name or "all")
        return {"success": True, "dataset_name": dataset_name}

    async def recall(self, query_text: str, datasets: list[str], top_k: int = 15, **kwargs: Any) -> RecallResponse:
        self.recall_calls.append({"query": query_text, "datasets": datasets, "top_k": top_k})
        return RecallResponse(query=query_text, dataset=",".join(datasets), results=[])


def _make_manifest(
    dataset_name: str = "test_repo",
    repo_path: str = "/workspace/test_repo",
    files: Optional[dict[str, tuple[str, list[str]]]] = None,
) -> RepositoryManifest:
    """Helper to construct a valid RepositoryManifest with FileFingerprints."""
    manifest = RepositoryManifest(
        repo_path=repo_path,
        dataset_name=dataset_name,
    )
    file_specs = files or {
        "src/core.py": ("sha_core_1111", ["process_data", "CoreEngine"]),
        "src/utils.py": ("sha_utils_2222", ["format_output", "validate_input"]),
        "src/api.py": ("sha_api_3333", ["create_app", "register_routes"]),
    }
    for path, (sha, symbols) in file_specs.items():
        manifest.files[path] = FileFingerprint(
            path=path,
            mtime=1000.0,
            size=500,
            sha256=sha,
            language="python",
            symbols=list(symbols),
        )
    manifest.compute_fingerprint()
    return manifest


# 1. test_cognee_uses_configured_memory_model
@pytest.mark.asyncio
async def test_cognee_uses_configured_memory_model(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Core engine orchestration",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
            "relationship_kind": "component_overview",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
        model_config={"memory_model": "dedicated-qwen-mem:latest"},
    )

    assert result.success is True
    assert mock_provider.last_model == "dedicated-qwen-mem:latest"
    assert result.telemetry.model_name == "dedicated-qwen-mem:latest"
    assert result.telemetry.fallback_used is False
    assert result.telemetry.llm_invocation_count == 1


# 2. test_cognee_falls_back_to_active_inference_model
@pytest.mark.asyncio
async def test_cognee_falls_back_to_active_inference_model(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Core engine orchestration",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="qwen2.5-coder:7b")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
        model_config={},  # No dedicated memory model
    )

    assert result.success is True
    assert mock_provider.last_model == "qwen2.5-coder:7b"
    assert result.telemetry.fallback_used is True
    assert "active inference model" in (result.telemetry.fallback_reason or "")
    assert result.telemetry.llm_invocation_count == 1


# 3. test_cognee_without_model_returns_not_configured
@pytest.mark.asyncio
async def test_cognee_without_model_returns_not_configured(tmp_path: Path):
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=None, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is False
    assert result.status == "not_configured"
    assert result.telemetry.model_invoked is False
    assert result.telemetry.llm_invocation_count == 0
    assert len(result.records) == 0


# 4. test_cognee_receives_only_verified_repository_evidence
@pytest.mark.asyncio
async def test_cognee_receives_only_verified_repository_evidence(tmp_path: Path):
    manifest = _make_manifest()
    mock_provider = MockLLMProvider(response_text="{}", default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
        source_snippets={"src/core.py": "def process_data(): return 42"},
        frameworks=["fastapi"],
        task_intent="Refactor authentication layer",
    )

    prompt = mock_provider.last_prompt
    assert prompt is not None
    assert "--- VERIFIED REPOSITORY EVIDENCE ---" in prompt
    assert "src/core.py" in prompt
    assert "def process_data(): return 42" in prompt
    assert "--- TASK / QUERY INTENT (FOR FOCUS ONLY, NOT EVIDENCE) ---" in prompt
    assert "Never treat intent description as repository facts or evidence" in prompt


# 5. test_cognee_cognification_persists_repository_scoped_memory
@pytest.mark.asyncio
async def test_cognee_cognification_persists_repository_scoped_memory(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "API setup and routing",
            "source_files": ["src/api.py"],
            "source_symbols": ["create_app", "register_routes"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
        cognee_service=mock_cognee,
    )

    assert result.success is True
    assert len(result.records) == 1
    assert result.vector_indexed is True
    assert len(mock_cognee.add_calls) == 1
    assert mock_cognee.add_calls[0]["dataset_name"] == "test_repo"

    # Verify persisted in repository
    persisted = repo.get_by_repository("test_repo", manifest=manifest)
    assert len(persisted) == 1
    assert persisted[0].source_files == ["src/api.py"]


# 6. test_cognee_output_is_mapped_through_semantic_memory_adapter
@pytest.mark.asyncio
async def test_cognee_output_is_mapped_through_semantic_memory_adapter(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Utility formatting logic",
            "source_files": ["src/utils.py"],
            "source_symbols": ["format_output"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is True
    rec = result.records[0]
    assert rec.generated_by == "cognee_pipeline"
    assert rec.evidence_status == "derived_projection"
    assert rec.is_derived is True
    assert rec.is_authoritative is False
    assert rec.source_sha256 == ["sha_utils_2222"]


# 7. test_cognee_cannot_create_unknown_files
@pytest.mark.asyncio
async def test_cognee_cannot_create_unknown_files(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Hallucinated database migration",
            "source_files": ["alembic/versions/001_init.py"],
            "source_symbols": ["upgrade"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is False
    assert result.status == "no_valid_memories"
    assert len(result.records) == 0
    assert result.telemetry.rejected_count == 1
    assert any("source_file_unknown" in r for r in result.telemetry.rejection_reasons)


# 8. test_cognee_cannot_create_unknown_symbols
@pytest.mark.asyncio
async def test_cognee_cannot_create_unknown_symbols(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Hallucinated GraphQL resolver",
            "source_files": ["src/api.py"],
            "source_symbols": ["resolve_graphql_query"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is False
    assert result.status == "no_valid_memories"
    assert len(result.records) == 0
    assert any("source_symbol_unknown" in r for r in result.telemetry.rejection_reasons)


# 9. test_cognee_output_cannot_become_authoritative
@pytest.mark.asyncio
async def test_cognee_output_cannot_become_authoritative(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Claiming Tier 1 authority",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
            "is_authoritative": True,
            "is_derived": False,
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is True
    rec = result.records[0]
    assert rec.is_authoritative is False
    assert rec.is_derived is True
    assert rec.evidence_status == "derived_projection"


# 10. test_cross_repository_cognee_memory_is_rejected
@pytest.mark.asyncio
async def test_cross_repository_cognee_memory_is_rejected(tmp_path: Path):
    manifest_a = _make_manifest(dataset_name="repo_a", repo_path="/workspace/repo_a")
    manifest_b = _make_manifest(dataset_name="repo_b", repo_path="/workspace/repo_b")

    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Repo A component",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Cognify Repo A
    await generator.cognify_repository("repo_a", manifest=manifest_a)

    # Repo B attempts to retrieve memories from repository
    mems_b = repo.get_by_repository("repo_b", manifest=manifest_b)
    assert len(mems_b) == 0

    # Cross-repo candidate in adapter is rejected
    rec, status = generator.repository.save(
        SemanticMemoryRecord(
            memory_id="foreign_mem",
            repository_id="repo_a",
            repository_fingerprint=manifest_a.repo_fingerprint,
            semantic_text="foreign text",
            source_files=["src/core.py"],
            source_symbols=["process_data"],
            source_sha256=["sha_core_1111"],
            relationship_kind="summary",
            generated_by="cognee_pipeline",
            generated_at=1700000000.0,
            evidence_status="derived_projection",
        ),
        manifest=manifest_b,
    )
    assert rec is False
    assert "cross_repository" in status


# 11. test_stale_cognee_memory_is_rejected_after_source_mutation
@pytest.mark.asyncio
async def test_stale_cognee_memory_is_rejected_after_source_mutation(tmp_path: Path):
    manifest_v1 = _make_manifest(files={"src/core.py": ("sha_v1", ["process_data"])})
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Core logic v1",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    await generator.cognify_repository("test_repo", manifest=manifest_v1)
    assert len(repo.get_by_repository("test_repo", manifest=manifest_v1)) == 1

    # Source mutated in v2
    manifest_v2 = _make_manifest(files={"src/core.py": ("sha_v2_mutated", ["process_data"])})
    active_mems = repo.get_by_repository("test_repo", manifest=manifest_v2, include_stale=False)
    assert len(active_mems) == 0


# 12. test_deleted_file_cognee_memory_is_invalidated
@pytest.mark.asyncio
async def test_deleted_file_cognee_memory_is_invalidated(tmp_path: Path):
    manifest_v1 = _make_manifest(files={
        "src/core.py": ("sha_core", ["process_data"]),
        "src/old_feature.py": ("sha_old", ["legacy_func"]),
    })
    mock_resp = json.dumps({
        "memories": [
            {
                "semantic_text": "Core logic",
                "source_files": ["src/core.py"],
                "source_symbols": ["process_data"],
            },
            {
                "semantic_text": "Legacy feature",
                "source_files": ["src/old_feature.py"],
                "source_symbols": ["legacy_func"],
            },
        ]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Initial cognify
    await generator.cognify_repository("test_repo", manifest=manifest_v1)
    assert len(repo.get_by_repository("test_repo", manifest=manifest_v1)) == 2

    # In v2: src/old_feature.py is deleted
    manifest_v2 = _make_manifest(files={"src/core.py": ("sha_core", ["process_data"])})
    delta = IndexDelta(
        added=[],
        modified=[],
        deleted=["src/old_feature.py"],
        unchanged=[Path("/workspace/test_repo/src/core.py")],
        renamed=[],
    )

    # Cognify with deletion delta
    del_result = await generator.cognify_repository(
        "test_repo",
        manifest=manifest_v2,
        delta=delta,
        existing_manifest=manifest_v1,
    )

    assert del_result.success is True
    assert del_result.telemetry.llm_invocation_count == 0  # No LLM calls for deletion-only
    assert del_result.telemetry.invalidated_count == 1
    assert len(del_result.records) == 1
    assert del_result.records[0].source_files == ["src/core.py"]


# 13. test_cognee_failure_does_not_break_deterministic_retrieval
@pytest.mark.asyncio
async def test_cognee_failure_does_not_break_deterministic_retrieval(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Core logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    # Cognee service that fails on add()
    failing_cognee = MockCogneeService(should_fail=True)
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        "test_repo",
        manifest=manifest,
        cognee_service=failing_cognee,
    )

    # The operation still succeeds for persistent RE:Track semantic records
    assert result.success is True
    assert result.vector_indexed is False  # Degraded vector state recorded
    assert len(result.records) == 1
    assert len(repo.get_by_repository("test_repo", manifest=manifest)) == 1


# 14. test_cognification_is_repository_scoped
@pytest.mark.asyncio
async def test_cognification_is_repository_scoped(tmp_path: Path):
    manifest_1 = _make_manifest(dataset_name="repo_alpha", repo_path="/workspace/alpha")
    manifest_2 = _make_manifest(dataset_name="repo_beta", repo_path="/workspace/beta")

    mock_provider = MockLLMProvider(
        response_text=json.dumps({"memories": [{
            "semantic_text": "Alpha component",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]}),
        default_model="phi4-mini",
    )
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    res1 = await generator.cognify_repository("repo_alpha", manifest=manifest_1)
    assert res1.success is True

    # Check store separation
    assert len(repo.get_by_repository("repo_alpha", manifest=manifest_1)) == 1
    assert len(repo.get_by_repository("repo_beta", manifest=manifest_2)) == 0


# 15. test_repeated_cognification_is_idempotent
@pytest.mark.asyncio
async def test_repeated_cognification_is_idempotent(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Idempotent component summary",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # First pass
    r1 = await generator.cognify_repository("test_repo", manifest=manifest)
    assert r1.success is True
    assert len(repo.get_by_repository("test_repo", manifest=manifest)) == 1

    # Second pass with no-change delta
    delta = IndexDelta(added=[], modified=[], deleted=[], unchanged=[Path("src/core.py")], renamed=[])
    r2 = await generator.cognify_repository(
        "test_repo",
        manifest=manifest,
        delta=delta,
        existing_manifest=manifest,
    )
    assert r2.success is True
    assert r2.status == "noop"
    assert r2.telemetry.llm_invocation_count == 0
    assert len(repo.get_by_repository("test_repo", manifest=manifest)) == 1


# 16. test_modified_file_triggers_targeted_re_cognification
@pytest.mark.asyncio
async def test_modified_file_triggers_targeted_re_cognification(tmp_path: Path):
    manifest_v1 = _make_manifest(files={
        "src/core.py": ("sha_core_v1", ["process_data"]),
        "src/utils.py": ("sha_utils_v1", ["format_output"]),
    })
    mock_resp_v1 = json.dumps({
        "memories": [
            {"semantic_text": "Core v1", "source_files": ["src/core.py"], "source_symbols": ["process_data"]},
            {"semantic_text": "Utils v1", "source_files": ["src/utils.py"], "source_symbols": ["format_output"]},
        ]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp_v1, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Initial build
    await generator.cognify_repository("test_repo", manifest=manifest_v1)
    assert len(repo.get_by_repository("test_repo", manifest=manifest_v1)) == 2

    # Manifest v2: only src/core.py was modified
    manifest_v2 = _make_manifest(files={
        "src/core.py": ("sha_core_v2_mutated", ["process_data"]),
        "src/utils.py": ("sha_utils_v1", ["format_output"]),
    })
    delta = IndexDelta(
        added=[],
        modified=[Path("/workspace/test_repo/src/core.py")],
        deleted=[],
        unchanged=[Path("/workspace/test_repo/src/utils.py")],
        renamed=[],
    )

    mock_provider.response_text = json.dumps({
        "memories": [
            {"semantic_text": "Core v2 mutated", "source_files": ["src/core.py"], "source_symbols": ["process_data"]}
        ]
    })

    r2 = await generator.cognify_repository(
        "test_repo",
        manifest=manifest_v2,
        delta=delta,
        existing_manifest=manifest_v1,
    )

    assert r2.success is True
    assert r2.telemetry.llm_invocation_count == 1
    assert r2.telemetry.invalidated_count == 1  # only old core.py invalidated
    assert r2.telemetry.preserved_count == 1    # utils.py preserved

    # Total in store is 2 (new core + preserved utils)
    all_current = repo.get_by_repository("test_repo", manifest=manifest_v2)
    assert len(all_current) == 2
    texts = [m.semantic_text for m in all_current]
    assert "Core v2 mutated" in texts
    assert "Utils v1" in texts


# 17. test_renamed_file_preserves_same_sha_memory
@pytest.mark.asyncio
async def test_renamed_file_preserves_same_sha_memory(tmp_path: Path):
    manifest_v1 = _make_manifest(files={"src/old_path.py": ("sha_identical", ["my_fn"])})
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Identical logic preserved",
            "source_files": ["src/old_path.py"],
            "source_symbols": ["my_fn"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Initial build
    await generator.cognify_repository("test_repo", manifest=manifest_v1)
    assert len(repo.get_by_repository("test_repo", manifest=manifest_v1)) == 1

    # Manifest v2: file renamed from src/old_path.py to src/new_path.py with identical SHA
    manifest_v2 = _make_manifest(files={"src/new_path.py": ("sha_identical", ["my_fn"])})
    delta = IndexDelta(
        added=[],
        modified=[],
        deleted=[],
        unchanged=[],
        renamed=[("src/old_path.py", Path("/workspace/test_repo/src/new_path.py"))],
    )

    r_rename = await generator.cognify_repository(
        "test_repo",
        manifest=manifest_v2,
        delta=delta,
        existing_manifest=manifest_v1,
    )

    assert r_rename.success is True
    # Zero LLM extraction calls for same-SHA rename!
    assert r_rename.telemetry.llm_invocation_count == 0
    assert r_rename.telemetry.renamed_count == 1
    assert len(r_rename.records) == 1
    assert r_rename.records[0].source_files == ["src/new_path.py"]
    assert r_rename.records[0].semantic_text == "Identical logic preserved"


# 18. test_cognee_telemetry_reports_actual_model
@pytest.mark.asyncio
async def test_cognee_telemetry_reports_actual_model(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Telemetry model reporting",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(
        response_text=mock_resp,
        provider_type=ProviderType.LM_STUDIO,
        default_model="lmstudio-custom-mem:q8",
    )
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository("test_repo", manifest=manifest)
    tel = result.telemetry

    assert tel.model_invoked is True
    assert tel.provider_identity == ProviderType.LM_STUDIO.value
    assert tel.model_name == "lmstudio-custom-mem:q8"
    assert tel.inference_status == "success"
    assert tel.llm_invocation_count == 1


# 19. test_cognee_failure_is_not_reported_as_missing_repository_evidence
@pytest.mark.asyncio
async def test_cognee_failure_is_not_reported_as_missing_repository_evidence(tmp_path: Path):
    manifest = _make_manifest()
    mock_provider = MockLLMProvider(
        raise_error=ConnectionError("Endpoint refused connection"),
        default_model="phi4-mini",
    )
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository("test_repo", manifest=manifest)

    assert result.success is False
    assert result.status == "provider_unavailable"
    # Explicit distinction: NOT "insufficient_evidence"
    assert result.status != "insufficient_evidence"
    assert result.telemetry.inference_status == "provider_unavailable"


# 20. test_cognee_results_enter_tier4_arbitration_only_after_validation
@pytest.mark.asyncio
async def test_cognee_results_enter_tier4_arbitration_only_after_validation(tmp_path: Path):
    manifest = _make_manifest()
    # 1 valid record, 1 cross-repo record, 1 stale record (mutated SHA)
    valid_rec = SemanticMemoryRecord(
        memory_id="valid_mem",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Valid core memory",
        source_files=["src/core.py"],
        source_symbols=["process_data"],
        source_sha256=["sha_core_1111"],
        relationship_kind="summary",
        generated_by="cognee_pipeline",
        generated_at=1700000000.0,
        evidence_status="derived_projection",
    )
    cross_repo_rec = SemanticMemoryRecord(
        memory_id="cross_mem",
        repository_id="other_repo",
        repository_fingerprint="foreign_fp",
        semantic_text="Foreign memory",
        source_files=["src/core.py"],
        source_symbols=["process_data"],
        source_sha256=["sha_core_1111"],
        relationship_kind="summary",
        generated_by="cognee_pipeline",
        generated_at=1700000000.0,
        evidence_status="derived_projection",
    )
    stale_rec = SemanticMemoryRecord(
        memory_id="stale_mem",
        repository_id="test_repo",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Stale memory",
        source_files=["src/core.py"],
        source_symbols=["process_data"],
        source_sha256=["old_sha_mutated"],
        relationship_kind="summary",
        generated_by="cognee_pipeline",
        generated_at=1700000000.0,
        evidence_status="derived_projection",
    )

    from app.application.domain.intent import ParsedIntentRecord
    intent = ParsedIntentRecord(task_summary="query valid memory", category="feature")

    arbitrated = RetrievalArbitrator.arbitrate(
        task_prompt="find core logic",
        intent=intent,
        manifest=manifest,
        cognee_memories=[valid_rec, cross_repo_rec, stale_rec],
    )

    # Only the validated record enters Tier 4
    tier4_candidates = [c for c in arbitrated.candidates if c.tier == AuthorityTier.TIER_4_COGNEE]
    assert len(tier4_candidates) == 1
    assert tier4_candidates[0].content == "Valid core memory"
    assert arbitrated.stale_rejected_count == 1
    assert arbitrated.cross_repo_rejected_count == 1


# 21. Acceptance Constraint 1: Exactly-once semantic extraction
@pytest.mark.asyncio
async def test_acceptance_constraint_exactly_once_semantic_extraction(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Single pass extraction",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    mock_cognee = MockCogneeService()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.cognify_repository(
        "test_repo",
        manifest=manifest,
        cognee_service=mock_cognee,
    )

    assert result.success is True
    # Exactly one LLM call
    assert mock_provider.call_count == 1
    assert result.telemetry.llm_invocation_count == 1
    # Cognee add() called without second cognify() LLM extraction
    assert len(mock_cognee.add_calls) == 1
    assert len(mock_cognee.cognify_calls) == 0


# 22. Acceptance Constraint 3: No recursive semantic self-feeding
@pytest.mark.asyncio
async def test_acceptance_constraint_no_recursive_self_feeding(tmp_path: Path):
    manifest = _make_manifest()
    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Initial memory record",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Pass 1
    await generator.cognify_repository("test_repo", manifest=manifest)
    assert len(repo.get_by_repository("test_repo", manifest=manifest)) == 1

    # Pass 2 (full re-build or incremental)
    # The generation input MUST NOT contain existing SemanticMemoryRecord texts as source evidence
    delta = IndexDelta(
        added=[],
        modified=[Path("/workspace/test_repo/src/api.py")],
        deleted=[],
        unchanged=[Path("/workspace/test_repo/src/core.py")],
        renamed=[],
    )
    mock_provider.response_text = json.dumps({
        "memories": [{
            "semantic_text": "API memory",
            "source_files": ["src/api.py"],
            "source_symbols": ["create_app"],
        }]
    })

    await generator.cognify_repository(
        "test_repo",
        manifest=manifest,
        delta=delta,
        existing_manifest=manifest,
    )

    prompt = mock_provider.last_prompt
    assert prompt is not None
    # Generated semantic memory text from Pass 1 does NOT appear as source evidence in Pass 2
    assert "Initial memory record" not in prompt
    assert "src/api.py" in prompt
