"""Comprehensive unit tests for semantic memory generation and cognification (Phase 10D.6 Task 4).

Validates:
1. Model selection order (dedicated memory model -> active inference model fallback -> not_configured).
2. Grounded-only evidence constraints: no hallucinated files, symbols, or unverified framework features.
3. Provenance validation via CogneeSemanticMemoryAdapter and durable persistence via JsonSemanticMemoryRepository.
4. Truthful telemetry, latency tracking, reasoning <think> block stripping, and abstention behavior.
"""

import json
from pathlib import Path
from typing import Any, Optional
from unittest.mock import AsyncMock

import pytest

from app.application.domain.memory import (
    SemanticMemoryGenerationInput,
    SemanticMemoryRecord,
)
from app.models.provider import ProviderType
from app.services.manifest_service import FileFingerprint, RepositoryManifest
from app.services.semantic_memory_generator import (
    SEMANTIC_MEMORY_SYSTEM_PROMPT,
    SemanticMemoryGenerator,
    build_generation_prompt,
    extract_memories_from_response,
)
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository


class MockLLMProvider:
    """Mock LLM provider for deterministic unit testing."""

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


# 1. test_generation_uses_configured_memory_model
@pytest.mark.asyncio
async def test_generation_uses_configured_memory_model(tmp_path: Path):
    manifest = _make_manifest()
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Core processing logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
            "relationship_kind": "behavior_summary",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
        model_config={"memory_model": "dedicated-mem-model:latest"},
    )

    assert result.success is True
    assert mock_provider.last_model == "dedicated-mem-model:latest"
    assert result.telemetry.model_name == "dedicated-mem-model:latest"
    assert result.telemetry.fallback_used is False
    assert result.telemetry.fallback_reason is None


# 2. test_generation_falls_back_to_current_model_only_when_no_memory_model_configured
@pytest.mark.asyncio
async def test_generation_falls_back_to_current_model_only_when_no_memory_model_configured(tmp_path: Path):
    manifest = _make_manifest()
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Core processing logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
            "relationship_kind": "behavior_summary",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="active-inference-model:q6")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
        model_config={},  # No dedicated memory model
    )

    assert result.success is True
    assert mock_provider.last_model == "active-inference-model:q6"
    assert result.telemetry.model_name == "active-inference-model:q6"
    assert result.telemetry.fallback_used is True
    assert "active inference model" in (result.telemetry.fallback_reason or "")


# 3. test_no_model_configured_returns_not_configured
@pytest.mark.asyncio
async def test_no_model_configured_returns_not_configured(tmp_path: Path):
    manifest = _make_manifest()
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    # No provider configured
    generator = SemanticMemoryGenerator(llm_provider=None, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is False
    assert result.status == "not_configured"
    assert result.telemetry.model_invoked is False
    assert result.telemetry.inference_status == "not_configured"
    assert len(result.records) == 0
    assert len(repo.load_all()) == 0


# 4. test_generation_uses_only_verified_repository_evidence
@pytest.mark.asyncio
async def test_generation_uses_only_verified_repository_evidence(tmp_path: Path):
    manifest = _make_manifest()
    mock_provider = MockLLMProvider(response_text="{}", default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
        source_snippets={"src/core.py": "def process_data(): return 42"},
        task_intent="Find login authentication endpoints",
        frameworks=["fastapi"],
    )

    prompt = mock_provider.last_prompt
    assert prompt is not None
    # Verified evidence is present
    assert "src/core.py" in prompt
    assert "process_data" in prompt
    assert "def process_data(): return 42" in prompt
    assert "Detected Frameworks: fastapi" in prompt
    # Intent is marked distinctly as focus only, not repository facts
    assert "--- TASK / QUERY INTENT (FOR FOCUS ONLY, NOT EVIDENCE) ---" in prompt
    assert "Never treat intent description as repository facts or evidence" in prompt


# 5. test_model_cannot_create_unknown_source_file
@pytest.mark.asyncio
async def test_model_cannot_create_unknown_source_file(tmp_path: Path):
    manifest = _make_manifest()
    # LLM hallucinated an unknown file
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Hallucinated auth controller",
            "source_files": ["src/controllers/auth_controller.py"],
            "source_symbols": ["login_user"],
            "relationship_kind": "route_handler",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is False
    assert result.status == "no_valid_memories"
    assert len(result.records) == 0
    assert result.telemetry.candidate_count == 1
    assert result.telemetry.validated_count == 0
    assert result.telemetry.persisted_count == 0
    assert result.telemetry.rejected_count == 1
    assert any("source_file_unknown" in r for r in result.telemetry.rejection_reasons)
    assert len(repo.load_all()) == 0


# 6. test_model_cannot_create_unknown_symbol
@pytest.mark.asyncio
async def test_model_cannot_create_unknown_symbol(tmp_path: Path):
    manifest = _make_manifest()
    # Valid file, but hallucinated symbol not in AST
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Hallucinated payment processing symbol",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_credit_card"],
            "relationship_kind": "payment_flow",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is False
    assert result.status == "no_valid_memories"
    assert len(result.records) == 0
    assert result.telemetry.validated_count == 0
    assert any("source_symbol_unknown" in r for r in result.telemetry.rejection_reasons)
    assert len(repo.load_all()) == 0


# 7. test_framework_presence_does_not_create_optional_feature_memory
@pytest.mark.asyncio
async def test_framework_presence_does_not_create_optional_feature_memory(tmp_path: Path):
    manifest = _make_manifest()
    # Model claims OAuth2 endpoint exists just because framework was mentioned, referencing invented files/symbols
    mock_response = json.dumps({
        "memories": [
            {
                "semantic_text": "OAuth2 password bearer authentication and JWT refresh handler",
                "source_files": ["src/auth/jwt.py"],
                "source_symbols": ["create_access_token"],
                "relationship_kind": "auth_flow",
            },
            {
                "semantic_text": "Validated core data processing logic",
                "source_files": ["src/core.py"],
                "source_symbols": ["process_data"],
                "relationship_kind": "behavior_summary",
            },
        ]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
        frameworks=["fastapi"],
    )

    assert result.success is True
    # The hallucinated OAuth2 memory is rejected; only the verified one is accepted
    assert len(result.records) == 1
    assert result.records[0].source_files == ["src/core.py"]
    assert result.telemetry.candidate_count == 2
    assert result.telemetry.validated_count == 1
    assert result.telemetry.rejected_count == 1
    assert result.telemetry.persisted_count == 1


# 8. test_empty_repository_generates_zero_memories
@pytest.mark.asyncio
async def test_empty_repository_generates_zero_memories(tmp_path: Path):
    # Manifest with 0 files
    empty_manifest = RepositoryManifest(repo_path="/empty/repo", dataset_name="empty_repo")
    mock_provider = MockLLMProvider(response_text="{}", default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="empty_repo",
        manifest=empty_manifest,
    )

    assert result.success is False
    assert result.status == "insufficient_evidence"
    assert result.telemetry.model_invoked is False
    assert mock_provider.call_count == 0
    assert len(result.records) == 0
    assert len(repo.load_all()) == 0


# 9. test_provider_failure_generates_zero_persisted_memories
@pytest.mark.asyncio
async def test_provider_failure_generates_zero_persisted_memories(tmp_path: Path):
    manifest = _make_manifest()
    mock_provider = MockLLMProvider(
        raise_error=ConnectionError("Connection refused to inference endpoint"),
        default_model="phi4-mini",
    )
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is False
    assert result.status == "provider_unavailable"
    assert result.telemetry.model_invoked is True
    assert result.telemetry.inference_status == "provider_unavailable"
    assert result.telemetry.persisted_count == 0
    assert len(result.records) == 0
    assert len(repo.load_all()) == 0


# 10. test_generated_memory_passes_through_cognee_adapter
@pytest.mark.asyncio
async def test_generated_memory_passes_through_cognee_adapter(tmp_path: Path):
    manifest = _make_manifest()
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Core processing component",
            "source_files": ["src/core.py"],
            "source_symbols": ["CoreEngine"],
            "relationship_kind": "component_overview",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
    )

    assert result.success is True
    assert len(result.records) == 1
    rec = result.records[0]

    # Invariants enforced by CogneeSemanticMemoryAdapter
    assert rec.generated_by == "cognee_pipeline"
    assert rec.evidence_status == "derived_projection"
    assert rec.is_derived is True
    assert rec.is_authoritative is False
    assert rec.source_sha256 == ["sha_core_1111"]
    assert rec.repository_fingerprint == manifest.repo_fingerprint


# 11. test_generated_memory_is_persisted_only_after_provenance_validation
@pytest.mark.asyncio
async def test_generated_memory_is_persisted_only_after_provenance_validation(tmp_path: Path):
    manifest = _make_manifest()
    mock_response = json.dumps({
        "memories": [
            {
                "semantic_text": "Valid utility functions",
                "source_files": ["src/utils.py"],
                "source_symbols": ["format_output"],
            },
            {
                "semantic_text": "Invalid unanchored memory",
                "source_files": ["unknown/path.py"],
            },
        ]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory(
        repository_id="test_repo",
        manifest=manifest,
        persist=True,
    )

    assert result.success is True
    assert len(result.records) == 1
    persisted = repo.get_by_repository("test_repo", manifest=manifest)
    assert len(persisted) == 1
    assert persisted[0].source_files == ["src/utils.py"]


# 12. test_repeated_generation_does_not_duplicate_memory
@pytest.mark.asyncio
async def test_repeated_generation_does_not_duplicate_memory(tmp_path: Path):
    manifest = _make_manifest()
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Deterministic core logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Run 1
    res1 = await generator.generate_semantic_memory("test_repo", manifest)
    assert res1.success is True
    assert len(repo.get_by_repository("test_repo", manifest=manifest)) == 1

    # Run 2 with identical content
    res2 = await generator.generate_semantic_memory("test_repo", manifest)
    assert res2.success is True
    # Count remains 1 due to upsert deduplication on deterministic memory_id
    assert len(repo.get_by_repository("test_repo", manifest=manifest)) == 1


# 13. test_modified_source_invalidates_previous_memory
@pytest.mark.asyncio
async def test_modified_source_invalidates_previous_memory(tmp_path: Path):
    manifest_v1 = _make_manifest(files={"src/core.py": ("sha_v1", ["process_data"])})
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Version 1 logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Generate v1
    await generator.generate_semantic_memory("test_repo", manifest_v1)
    assert len(repo.get_by_repository("test_repo", manifest=manifest_v1)) == 1

    # Mutate source file SHA in manifest v2
    manifest_v2 = _make_manifest(files={"src/core.py": ("sha_v2_mutated", ["process_data"])})

    # Active reload against v2 manifest excludes stale record
    active_mems = repo.get_by_repository("test_repo", manifest=manifest_v2, include_stale=False)
    assert len(active_mems) == 0

    # Including stale entries returns marked as stale
    stale_mems = repo.get_by_repository("test_repo", manifest=manifest_v2, include_stale=True)
    assert len(stale_mems) == 1
    assert stale_mems[0].evidence_status == "stale"


# 14. test_deleted_source_invalidates_previous_memory
@pytest.mark.asyncio
async def test_deleted_source_invalidates_previous_memory(tmp_path: Path):
    manifest_v1 = _make_manifest(files={"src/core.py": ("sha_v1", ["process_data"])})
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Version 1 logic",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    # Generate v1
    await generator.generate_semantic_memory("test_repo", manifest_v1)
    assert len(repo.get_by_repository("test_repo", manifest=manifest_v1)) == 1

    # Remove src/core.py from manifest v2 (file deleted)
    manifest_v2 = _make_manifest(files={"src/other.py": ("sha_other", ["other_fn"])})

    # Reload against v2 manifest marks previous memory as stale / excludes from active
    assert len(repo.get_by_repository("test_repo", manifest=manifest_v2, include_stale=False)) == 0


# 15. test_generation_telemetry_is_truthful
@pytest.mark.asyncio
async def test_generation_telemetry_is_truthful(tmp_path: Path):
    manifest = _make_manifest()
    mock_response = json.dumps({
        "memories": [
            {
                "semantic_text": "Valid item",
                "source_files": ["src/core.py"],
                "source_symbols": ["process_data"],
            },
            {
                "semantic_text": "Invalid item",
                "source_files": ["src/does_not_exist.py"],
            },
        ]
    })
    mock_provider = MockLLMProvider(
        response_text=mock_response,
        provider_type=ProviderType.LM_STUDIO,
        default_model="lm-phi4-mini",
    )
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory("test_repo", manifest)

    telemetry = result.telemetry
    assert telemetry.model_invoked is True
    assert telemetry.provider_identity == ProviderType.LM_STUDIO.value
    assert telemetry.model_name == "lm-phi4-mini"
    assert telemetry.inference_status == "success"
    assert telemetry.inference_time_ms >= 0.0
    assert telemetry.candidate_count == 2
    assert telemetry.validated_count == 1
    assert telemetry.persisted_count == 1
    assert telemetry.rejected_count == 1
    assert len(telemetry.rejection_reasons) >= 1

    # Verify serialization
    d = telemetry.to_dict()
    assert d["candidate_count"] == 2
    assert d["validated_count"] == 1


# 16. test_reasoning_think_blocks_are_not_persisted
@pytest.mark.asyncio
async def test_reasoning_think_blocks_are_not_persisted(tmp_path: Path):
    manifest = _make_manifest()
    # Response containing <think> reasoning trace
    mock_response = (
        "<think>\n"
        "Let me analyze the provided files.\n"
        "src/core.py has process_data.\n"
        "I will now form the JSON output.\n"
        "</think>\n"
        "```json\n"
        "{\n"
        '  "memories": [\n'
        "    {\n"
        '      "semantic_text": "<think>inner thought</think>Process data coordinates execution pipeline.",\n'
        '      "source_files": ["src/core.py"],\n'
        '      "source_symbols": ["process_data"]\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```"
    )
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory("test_repo", manifest)

    assert result.success is True
    assert len(result.records) == 1
    text = result.records[0].semantic_text
    assert "<think>" not in text
    assert "</think>" not in text
    assert "inner thought" not in text
    assert text == "Process data coordinates execution pipeline."


# 17. test_model_output_cannot_override_repository_truth
@pytest.mark.asyncio
async def test_model_output_cannot_override_repository_truth(tmp_path: Path):
    manifest = _make_manifest()
    # Adversarial model response trying to claim authoritative status
    mock_response = json.dumps({
        "memories": [{
            "semantic_text": "Adversarial claim of authority",
            "source_files": ["src/core.py"],
            "source_symbols": ["process_data"],
            "is_authoritative": True,
            "is_derived": False,
            "evidence_status": "verified_authoritative",
            "generated_by": "human_developer",
        }]
    })
    mock_provider = MockLLMProvider(response_text=mock_response, default_model="phi4-mini")
    repo = JsonSemanticMemoryRepository(store_path=tmp_path / "sem_mem.json")
    generator = SemanticMemoryGenerator(llm_provider=mock_provider, repository=repo)

    result = await generator.generate_semantic_memory("test_repo", manifest)

    assert result.success is True
    assert len(result.records) == 1
    rec = result.records[0]

    # Invariants must remain strictly derived / Tier 4
    assert rec.is_authoritative is False
    assert rec.is_derived is True
    assert rec.evidence_status == "derived_projection"
    assert rec.generated_by == "cognee_pipeline"
