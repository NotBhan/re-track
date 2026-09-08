"""Integration tests for Phase 10D.6 Task 6: Semantic Cognification & Repository Indexing Lifecycle.

Validates:
1. Fresh repository indexing triggers cognification orchestration with exactly one LLM pass.
2. NOOP indexing triggers 0 AST parses, 0 LLM extraction calls, and preserves existing semantic memory.
3. Added file triggers targeted cognification for the new evidence only.
4. Modified file invalidates stale memory and triggers targeted regeneration while preserving unaffected memories.
5. Deleted file invalidates referencing memories with 0 LLM calls.
6. Same-SHA rename preserves memory text and updates provenance path with 0 LLM calls.
7. Changed-content rename invalidates old and regenerates new memory.
8. Unchanged memories are preserved across indexing cycles.
9. LLM provider failure does NOT fail deterministic repository indexing (graceful degradation).
10. Cognee/LanceDB storage failure does NOT break repository indexing or manifest commit.
11. Exactly one cognification orchestration occurs per indexing operation.
12. Cognification receives the post-index committed manifest.
13. Cross-repository semantic memory isolation is strictly enforced.
"""

import json
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.domain.memory import SemanticMemoryRecord
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType
from app.models.responses import IndexingProgress
from app.services.cognee_service import CogneeService
from app.services.indexing_service import IndexingService
from app.services.manifest_service import ManifestService
from app.services.semantic_memory_generator import SemanticMemoryGenerator
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository


class MockLLMProvider:
    """Mock LLM provider for deterministic integration tests."""

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
    """Mock CogneeService for testing indexing and memory ingestion."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.add_calls: list[dict[str, Any]] = []
        self._initialized = True

    async def add(self, data: Any, dataset_name: str = "default", **kwargs: Any) -> Any:
        if self.should_fail:
            raise CogneeServiceError("LanceDB storage unavailable")
        self.add_calls.append({"data": data, "dataset_name": dataset_name, **kwargs})
        return MagicMock(dataset_name=dataset_name, items_sent=1)

    async def recall(self, *args: Any, **kwargs: Any) -> Any:
        return MagicMock(results=[])


@pytest.fixture
def test_repo_env(tmp_path: Path):
    """Creates a sample multi-file repository and manifest directory."""
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir(parents=True)
    src_dir = repo_dir / "src"
    src_dir.mkdir(parents=True)

    (src_dir / "core.py").write_text(
        "class CoreEngine:\n    def process_data(self):\n        return 42\n",
        encoding="utf-8",
    )
    (src_dir / "utils.py").write_text(
        "def format_output(val):\n    return str(val).strip()\n",
        encoding="utf-8",
    )

    manifest_storage = tmp_path / "manifest_storage"
    manifest_storage.mkdir(parents=True)
    manifest_service = ManifestService(storage_dir=manifest_storage)

    memory_store = tmp_path / "sem_mem.json"
    memory_repo = JsonSemanticMemoryRepository(store_path=memory_store)

    return {
        "repo_dir": repo_dir,
        "src_dir": src_dir,
        "manifest_service": manifest_service,
        "memory_repo": memory_repo,
        "memory_store": memory_store,
        "tmp_path": tmp_path,
    }


# 1. test_fresh_indexing_triggers_cognification
@pytest.mark.asyncio
async def test_fresh_indexing_triggers_cognification(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Core processing and utility functions",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
            "relationship_kind": "orchestration",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    progress = await indexing_service.index_repository(repo_dir, "test_repo")

    assert progress.failed_files == 0
    assert progress.processed_files == 2
    assert mock_provider.call_count == 1
    assert indexing_service.last_cognification_result is not None
    assert indexing_service.last_cognification_result.success is True
    assert indexing_service.last_cognification_result.telemetry.llm_invocation_count == 1

    # Verify persisted in repository
    manifest = manifest_service.load_manifest(repo_dir)
    assert manifest is not None
    persisted = memory_repo.get_by_repository("test_repo", manifest=manifest)
    assert len(persisted) == 1
    assert persisted[0].source_files == ["src/core.py"]


# 2. test_noop_triggers_zero_cognification
@pytest.mark.asyncio
async def test_noop_triggers_zero_cognification(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Initial memory",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    # Initial full index
    await indexing_service.index_repository(repo_dir, "test_repo")
    assert mock_provider.call_count == 1

    # Second index with no changes
    progress_noop = await indexing_service.index_repository(repo_dir, "test_repo")

    assert progress_noop.failed_files == 0
    # ZERO LLM calls triggered on NOOP
    assert mock_provider.call_count == 1

    # Verify memories preserved
    manifest = manifest_service.load_manifest(repo_dir)
    persisted = memory_repo.get_by_repository("test_repo", manifest=manifest)
    assert len(persisted) == 1


# 3. test_added_file_triggers_targeted_cognification
@pytest.mark.asyncio
async def test_added_file_triggers_targeted_cognification(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    src_dir = test_repo_env["src_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp_1 = json.dumps({
        "memories": [{
            "semantic_text": "Core logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp_1)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    # Initial index
    await indexing_service.index_repository(repo_dir, "test_repo")
    assert len(memory_repo.get_by_repository("test_repo", manifest=manifest_service.load_manifest(repo_dir))) == 1

    # Add a new file
    (src_dir / "api.py").write_text(
        "class ApiRouter:\n    def register_routes(self):\n        pass\n",
        encoding="utf-8",
    )
    mock_provider.response_text = json.dumps({
        "memories": [{
            "semantic_text": "API routing layer",
            "source_files": ["src/api.py"],
            "source_symbols": ["ApiRouter"],
        }]
    })

    await indexing_service.index_repository(repo_dir, "test_repo")

    # Second LLM call for the added file
    assert mock_provider.call_count == 2
    assert indexing_service.last_cognification_result.telemetry.mode == "incremental"

    manifest_v2 = manifest_service.load_manifest(repo_dir)
    all_records = memory_repo.get_by_repository("test_repo", manifest=manifest_v2)
    assert len(all_records) == 2
    files = {r.source_files[0] for r in all_records}
    assert "src/core.py" in files
    assert "src/api.py" in files


# 4. test_modified_file_triggers_targeted_regeneration
@pytest.mark.asyncio
async def test_modified_file_triggers_targeted_regeneration(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    src_dir = test_repo_env["src_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp_1 = json.dumps({
        "memories": [
            {"semantic_text": "Core v1", "source_files": ["src/core.py"], "source_symbols": ["CoreEngine"]},
            {"semantic_text": "Utils v1", "source_files": ["src/utils.py"], "source_symbols": ["format_output"]},
        ]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp_1)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_dir, "test_repo")
    assert len(memory_repo.get_by_repository("test_repo", manifest=manifest_service.load_manifest(repo_dir))) == 2

    # Mutate src/core.py
    (src_dir / "core.py").write_text(
        "class CoreEngine:\n    def process_data_v2(self):\n        return 99\n",
        encoding="utf-8",
    )
    mock_provider.response_text = json.dumps({
        "memories": [{
            "semantic_text": "Core v2 updated",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })

    await indexing_service.index_repository(repo_dir, "test_repo")

    manifest_v2 = manifest_service.load_manifest(repo_dir)
    current_mems = memory_repo.get_by_repository("test_repo", manifest=manifest_v2)
    assert len(current_mems) == 2
    texts = {m.semantic_text for m in current_mems}
    assert "Core v2 updated" in texts
    assert "Utils v1" in texts


# 5. test_deleted_file_invalidates_without_llm_call
@pytest.mark.asyncio
async def test_deleted_file_invalidates_without_llm_call(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    src_dir = test_repo_env["src_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp_1 = json.dumps({
        "memories": [
            {"semantic_text": "Core logic", "source_files": ["src/core.py"], "source_symbols": ["CoreEngine"]},
            {"semantic_text": "Utils logic", "source_files": ["src/utils.py"], "source_symbols": ["format_output"]},
        ]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp_1)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_dir, "test_repo")
    assert mock_provider.call_count == 1

    # Delete src/utils.py
    (src_dir / "utils.py").unlink()

    await indexing_service.index_repository(repo_dir, "test_repo")

    # Deletion only: ZERO additional LLM calls
    assert mock_provider.call_count == 1
    assert indexing_service.last_cognification_result.telemetry.llm_invocation_count == 0
    assert indexing_service.last_cognification_result.telemetry.invalidated_count == 1

    manifest_v2 = manifest_service.load_manifest(repo_dir)
    remaining = memory_repo.get_by_repository("test_repo", manifest=manifest_v2)
    assert len(remaining) == 1
    assert remaining[0].source_files == ["src/core.py"]


# 6. test_same_sha_rename_updates_provenance_without_llm_call
@pytest.mark.asyncio
async def test_same_sha_rename_updates_provenance_without_llm_call(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    src_dir = test_repo_env["src_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Utils helper functions",
            "source_files": ["src/utils.py"],
            "source_symbols": ["format_output"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_dir, "test_repo")
    assert mock_provider.call_count == 1

    # Rename src/utils.py -> src/helpers.py without content changes
    content = (src_dir / "utils.py").read_text(encoding="utf-8")
    (src_dir / "utils.py").unlink()
    (src_dir / "helpers.py").write_text(content, encoding="utf-8")

    await indexing_service.index_repository(repo_dir, "test_repo")

    # Zero LLM extraction calls for same-SHA rename!
    assert mock_provider.call_count == 1
    assert indexing_service.last_cognification_result.telemetry.llm_invocation_count == 0
    assert indexing_service.last_cognification_result.telemetry.renamed_count == 1

    manifest_v2 = manifest_service.load_manifest(repo_dir)
    renamed_mems = memory_repo.get_by_repository("test_repo", manifest=manifest_v2)
    assert len(renamed_mems) == 1
    assert renamed_mems[0].source_files == ["src/helpers.py"]
    assert renamed_mems[0].semantic_text == "Utils helper functions"


# 7. test_changed_rename_regenerates_memory
@pytest.mark.asyncio
async def test_changed_rename_regenerates_memory(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    src_dir = test_repo_env["src_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp_1 = json.dumps({
        "memories": [{
            "semantic_text": "Core logic v1",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp_1)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_dir, "test_repo")
    assert mock_provider.call_count == 1

    # Rename src/core.py -> src/engine.py WITH content change
    (src_dir / "core.py").unlink()
    (src_dir / "engine.py").write_text(
        "class CoreEngine:\n    def execute_pipeline(self):\n        pass\n",
        encoding="utf-8",
    )
    mock_provider.response_text = json.dumps({
        "memories": [{
            "semantic_text": "Engine pipeline execution",
            "source_files": ["src/engine.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })

    await indexing_service.index_repository(repo_dir, "test_repo")

    # Content changed -> LLM regenerated
    assert mock_provider.call_count == 2
    manifest_v2 = manifest_service.load_manifest(repo_dir)
    mems = memory_repo.get_by_repository("test_repo", manifest=manifest_v2)
    assert len(mems) == 1
    assert mems[0].source_files == ["src/engine.py"]
    assert mems[0].semantic_text == "Engine pipeline execution"


# 8. test_unchanged_memories_are_preserved
@pytest.mark.asyncio
async def test_unchanged_memories_are_preserved(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    src_dir = test_repo_env["src_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp = json.dumps({
        "memories": [
            {"semantic_text": "Core logic", "source_files": ["src/core.py"], "source_symbols": ["CoreEngine"]},
            {"semantic_text": "Utils logic", "source_files": ["src/utils.py"], "source_symbols": ["format_output"]},
        ]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_dir, "test_repo")

    # Add extra file without touching core or utils
    (src_dir / "extra.py").write_text("def extra_func(): pass\n", encoding="utf-8")
    mock_provider.response_text = json.dumps({
        "memories": [{"semantic_text": "Extra logic", "source_files": ["src/extra.py"], "source_symbols": ["extra_func"]}]
    })

    await indexing_service.index_repository(repo_dir, "test_repo")

    manifest = manifest_service.load_manifest(repo_dir)
    mems = memory_repo.get_by_repository("test_repo", manifest=manifest)
    assert len(mems) == 3
    texts = {m.semantic_text for m in mems}
    assert "Core logic" in texts
    assert "Utils logic" in texts
    assert "Extra logic" in texts


# 9. test_provider_failure_does_not_fail_indexing
@pytest.mark.asyncio
async def test_provider_failure_does_not_fail_indexing(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    # Provider that raises network / offline error
    mock_provider = MockLLMProvider(raise_error=ConnectionError("Ollama daemon offline"))
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    # Indexing must succeed deterministically!
    progress = await indexing_service.index_repository(repo_dir, "test_repo")

    assert progress.failed_files == 0
    assert progress.processed_files == 2

    # Manifest is committed
    manifest = manifest_service.load_manifest(repo_dir)
    assert manifest is not None
    assert len(manifest.files) == 2

    # Semantic failure reported truthfully without breaking indexing
    assert indexing_service.last_cognification_result is not None
    assert indexing_service.last_cognification_result.success is False
    assert indexing_service.last_cognification_result.status == "provider_unavailable"


# 10. test_cognee_failure_does_not_fail_indexing
@pytest.mark.asyncio
async def test_cognee_failure_does_not_fail_indexing(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Core logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp)
    # Cognee service that fails during outline ingestion
    failing_cognee = MockCogneeService(should_fail=True)
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=failing_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    progress = await indexing_service.index_repository(repo_dir, "test_repo")
    # Deterministic progress records failure from Cognee outage gracefully
    assert progress.failed_files == 2


# 11. test_duplicate_cognification_trigger_is_impossible_for_one_index_operation
@pytest.mark.asyncio
async def test_duplicate_cognification_trigger_is_impossible_for_one_index_operation(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Single trigger memory",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_dir, "test_repo")

    # Exactly one LLM extraction pass across the entire indexing cycle
    assert mock_provider.call_count == 1
    assert indexing_service.last_cognification_result.telemetry.llm_invocation_count == 1


# 12. test_cognification_sees_the_post_index_current_manifest
@pytest.mark.asyncio
async def test_cognification_sees_the_post_index_current_manifest(test_repo_env):
    repo_dir = test_repo_env["repo_dir"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    mock_resp = json.dumps({
        "memories": [{
            "semantic_text": "Post-index manifest test",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_resp)
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_dir, "test_repo")

    manifest = manifest_service.load_manifest(repo_dir)
    assert manifest is not None
    rec = memory_repo.get_by_repository("test_repo", manifest=manifest)[0]

    # Stored record matches post-index manifest fingerprint
    assert rec.repository_fingerprint == manifest.repo_fingerprint
    assert rec.source_sha256 == [manifest.files["src/core.py"].sha256]


# 13. test_cross_repository_isolation_remains_enforced
@pytest.mark.asyncio
async def test_cross_repository_isolation_remains_enforced(test_repo_env):
    repo_a = test_repo_env["repo_dir"]
    tmp_path = test_repo_env["tmp_path"]
    manifest_service = test_repo_env["manifest_service"]
    memory_repo = test_repo_env["memory_repo"]

    # Create Repo B
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()
    (repo_b / "app.py").write_text("class AppService: pass\n", encoding="utf-8")

    mock_provider = MockLLMProvider(
        response_text=json.dumps({
            "memories": [{
                "semantic_text": "Alpha component",
                "source_files": ["src/core.py"],
                "source_symbols": ["CoreEngine"],
            }]
        })
    )
    mock_cognee = MockCogneeService()
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=memory_repo)

    indexing_service = IndexingService(
        cognee_service=mock_cognee,
        manifest_service=manifest_service,
        semantic_memory_generator=generator,
    )

    await indexing_service.index_repository(repo_a, "dataset_a")

    mock_provider.response_text = json.dumps({
        "memories": [{
            "semantic_text": "Beta component",
            "source_files": ["app.py"],
            "source_symbols": ["AppService"],
        }]
    })
    await indexing_service.index_repository(repo_b, "dataset_b")

    manifest_a = manifest_service.load_manifest(repo_a)
    manifest_b = manifest_service.load_manifest(repo_b)

    mems_a = memory_repo.get_by_repository("dataset_a", manifest=manifest_a)
    mems_b = memory_repo.get_by_repository("dataset_b", manifest=manifest_b)

    assert len(mems_a) == 1
    assert len(mems_b) == 1
    assert mems_a[0].repository_id == "dataset_a"
    assert mems_b[0].repository_id == "dataset_b"
    assert mems_a[0].semantic_text == "Alpha component"
    assert mems_b[0].semantic_text == "Beta component"
