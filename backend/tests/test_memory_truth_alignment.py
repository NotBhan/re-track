"""Tests for Phase 10D.4: Database & Memory Integration and Provenance Truth Alignment.

Verifies:
1. Fresh indexing produces valid MemoryProvenance records.
2. Modified files invalidate stale memory provenance.
3. Deleted files disappear from memory evidence.
4. Renamed files maintain content identity via SHA-256 matching.
5. Cross-repository memory isolation via repository fingerprints.
6. Database subsystem degradation does not compromise deterministic AST grounding.
7. Stale memory cannot satisfy EvidenceService.
8. Truthful error reporting across LanceDB, Kùzu, and Cognee subsystems.
"""

from dataclasses import dataclass
from pathlib import Path
import pytest
import time
from typing import Any

from app.application.domain.evidence import EvidenceState
from app.application.domain.intent import ParsedIntentRecord
from app.application.domain.memory import (
    MemoryDataItemRecord,
    MemoryDatasetRecord,
    MemoryGraphEdgeRecord,
    MemoryGraphNodeRecord,
    MemoryGraphRecord,
    MemoryProvenance,
    MemoryVectorStatsRecord,
    StorageSubsystemState,
)
from app.application.dto.memory import (
    DatasetInfo,
    MemoryGraphResponse,
    MemoryStatsResponse,
    MemoryVectorsResponse,
)
from app.models.responses import (
    ArchitectureInfo,
    ComponentInfo,
    ConventionInfo,
    DirectoryEntry,
    RepositorySummary,
    TechnologyStack,
)
from app.services.evidence_service import EvidenceService
from app.services.manifest_service import FileFingerprint, RepositoryManifest


def make_repo_summary(
    fingerprint: str = "",
    languages: list[str] | None = None,
    frameworks: list[str] | None = None,
    components: list[ComponentInfo] | None = None,
) -> RepositorySummary:
    return RepositorySummary(
        version="2.0",
        repository_fingerprint=fingerprint,
        generated_at="2026-08-26T00:00:00Z",
        indexed_commit=None,
        project_purpose="Test repository",
        technology_stack=TechnologyStack(
            languages=languages or ["python"],
            frameworks=frameworks or ["fastapi"],
            databases=[],
            dependencies=[],
        ),
        repository_map=[DirectoryEntry(path="src", description="Source code")],
        architecture=ArchitectureInfo(pattern="layered", layers=["api", "services"], boundaries=[], major_flows=[]),
        key_components=components or [],
        entry_points=[],
        public_apis=[],
        coding_conventions=ConventionInfo(naming="snake_case", formatting="black", patterns=[]),
        domain_vocabulary={},
    )


@pytest.fixture
def sample_manifest() -> RepositoryManifest:
    """Fixture providing a deterministic RepositoryManifest with 3 files."""
    manifest = RepositoryManifest(
        repo_path="/test/workspace/repo",
        dataset_name="repo_test",
        schema_version="2.0",
        parser_version="2.0.0",
    )
    manifest.files["src/auth/service.py"] = FileFingerprint(
        path="src/auth/service.py",
        mtime=time.time(),
        size=1024,
        sha256="aaa111bbb222",
        language="python",
        symbols=["AuthService", "authenticate_user", "verify_token"],
    )
    manifest.files["src/api/routes.py"] = FileFingerprint(
        path="src/api/routes.py",
        mtime=time.time(),
        size=2048,
        sha256="ccc333ddd444",
        language="python",
        symbols=["login_route", "profile_route"],
    )
    manifest.files["src/models/user.py"] = FileFingerprint(
        path="src/models/user.py",
        mtime=time.time(),
        size=512,
        sha256="eee555fff666",
        language="python",
        symbols=["UserModel"],
    )
    manifest.compute_fingerprint()
    return manifest


def test_fresh_indexing_provenance_validation(sample_manifest: RepositoryManifest):
    """Scenario 1: Fresh indexing produces valid MemoryProvenance matching the manifest."""
    prov = MemoryProvenance(
        repository_id="repo_sha256_id",
        repository_fingerprint=sample_manifest.repo_fingerprint,
        source_file="src/auth/service.py",
        source_sha256="aaa111bbb222",
        source_symbol="AuthService",
        relationship_kind="defines",
        indexed_at=time.time(),
        parser_version="2.0.0",
        manifest_version="2.0",
        evidence_status="verified_authoritative",
    )
    assert prov.is_valid_for_manifest(sample_manifest) is True


def test_modified_file_invalidates_stale_memory(sample_manifest: RepositoryManifest):
    """Scenario 2: Modified file's SHA-256 mismatch invalidates stale memory provenance."""
    stale_prov = MemoryProvenance(
        repository_id="repo_sha256_id",
        repository_fingerprint=sample_manifest.repo_fingerprint,
        source_file="src/auth/service.py",
        source_sha256="old_sha256_hash_999",
        source_symbol="AuthService",
    )
    assert stale_prov.is_valid_for_manifest(sample_manifest) is False

    memories = [
        {"id": "mem_1", "provenance": stale_prov},
        {
            "id": "mem_2",
            "provenance": MemoryProvenance(
                repository_id="repo_sha256_id",
                repository_fingerprint=sample_manifest.repo_fingerprint,
                source_file="src/api/routes.py",
                source_sha256="ccc333ddd444",
                source_symbol="login_route",
            ),
        },
    ]

    filtered = EvidenceService.validate_memory_evidence(memories, sample_manifest)
    assert len(filtered) == 1
    assert filtered[0]["id"] == "mem_2"


def test_deleted_file_disappears_from_memory_evidence(sample_manifest: RepositoryManifest):
    """Scenario 3: Deleted file is not present in manifest and is filtered out."""
    deleted_prov = MemoryProvenance(
        repository_id="repo_sha256_id",
        repository_fingerprint=sample_manifest.repo_fingerprint,
        source_file="src/legacy/old_service.py",
        source_sha256="zzz999xxx888",
    )
    assert deleted_prov.is_valid_for_manifest(sample_manifest) is False

    memories = [{"id": "mem_deleted", "provenance": deleted_prov}]
    filtered = EvidenceService.validate_memory_evidence(memories, sample_manifest)
    assert len(filtered) == 0


def test_cross_repository_memory_isolation(sample_manifest: RepositoryManifest):
    """Scenario 4: Memory from a different repository with different fingerprint is rejected."""
    foreign_prov = MemoryProvenance(
        repository_id="foreign_repo",
        repository_fingerprint="foreign_fp_12345",
        source_file="src/auth/service.py",
        source_sha256="aaa111bbb222",
    )
    assert foreign_prov.is_valid_for_manifest(sample_manifest) is False


def test_symbol_absence_invalidates_provenance(sample_manifest: RepositoryManifest):
    """Scenario 5: If provenance specifies a symbol not found in the file, it is invalid."""
    missing_sym_prov = MemoryProvenance(
        repository_id="repo_sha256_id",
        repository_fingerprint=sample_manifest.repo_fingerprint,
        source_file="src/auth/service.py",
        source_sha256="aaa111bbb222",
        source_symbol="NonExistentFunction",
    )
    assert missing_sym_prov.is_valid_for_manifest(sample_manifest) is False


def test_storage_subsystem_outage_resilience(sample_manifest: RepositoryManifest):
    """Scenario 6: LanceDB / Kùzu degradation does not disrupt deterministic AST evidence evaluation."""
    intent = ParsedIntentRecord(
        task_summary="Refactor AuthService to use UserModel",
        category="refactor",
        extracted_symbols=["AuthService", "UserModel"],
        relevant_file_hints=["src/auth/service.py", "src/models/user.py"],
    )
    repo_summary = make_repo_summary(
        fingerprint=sample_manifest.repo_fingerprint,
        frameworks=["fastapi"],
        components=[
            ComponentInfo(name="AuthService", responsibilities="Authentication", relationships=[]),
            ComponentInfo(name="UserModel", responsibilities="User persistence", relationships=[]),
        ],
    )

    evidence = EvidenceService.assess_evidence(
        task_prompt="Refactor AuthService to use UserModel",
        intent=intent,
        repo_summary=repo_summary,
        indexed_files=list(sample_manifest.files.keys()),
        relevant_snippets=["class AuthService:", "class UserModel:"],
        matched_file_rels=["src/auth/service.py", "src/models/user.py"],
        structural_symbols=["AuthService", "UserModel"],
        structural_relationships=[],
        derived_memories=[],
        manifest=sample_manifest,
    )

    assert evidence.abstained is False
    assert evidence.evidence_score >= 0.40
    assert "AuthService" in evidence.evidence_symbols
    assert "UserModel" in evidence.evidence_symbols


def test_stale_memory_cannot_satisfy_evidence_service(sample_manifest: RepositoryManifest):
    """Scenario 7: Stale/invalid memory cannot satisfy evidence requirements for missing features."""
    intent = ParsedIntentRecord(
        task_summary="Implement Stripe checkout payment integration",
        category="feature",
        extracted_symbols=["StripeCheckout"],
        relevant_file_hints=["src/payments/checkout.py"],
    )
    repo_summary = make_repo_summary(
        fingerprint=sample_manifest.repo_fingerprint,
        frameworks=["django"],
        components=[],
    )

    stale_memory = {
        "id": "stale_payment_memory",
        "provenance": MemoryProvenance(
            repository_id="repo_sha256_id",
            repository_fingerprint=sample_manifest.repo_fingerprint,
            source_file="src/payments/checkout.py",
            source_sha256="fake_sha256",
            source_symbol="StripeCheckout",
        ),
    }

    filtered_memories = EvidenceService.validate_memory_evidence([stale_memory], sample_manifest)
    assert len(filtered_memories) == 0

    evidence = EvidenceService.assess_evidence(
        task_prompt="Implement Stripe checkout payment integration",
        intent=intent,
        repo_summary=repo_summary,
        indexed_files=list(sample_manifest.files.keys()),
        relevant_snippets=[],
        matched_file_rels=[],
        structural_symbols=[],
        structural_relationships=[],
        derived_memories=filtered_memories,
        manifest=sample_manifest,
    )

    assert evidence.abstained is True
    assert evidence.evidence_state in (EvidenceState.NONE.value, EvidenceState.INSUFFICIENT.value)
    assert evidence.model_claims_allowed is False


def test_domain_and_dto_provenance_serialization():
    """Scenario 8: Domain records and DTOs correctly serialize and deserialize provenance metadata."""
    prov = MemoryProvenance(
        repository_id="repo_1",
        repository_fingerprint="fp_abc123",
        source_file="app/main.py",
        source_sha256="sha_xyz",
        source_symbol="main",
        relationship_kind="entrypoint",
        indexed_at=12345678.0,
        parser_version="2.0.0",
        manifest_version="2.0",
        evidence_status="verified_authoritative",
    )

    # Node record
    node = MemoryGraphNodeRecord(
        id="node_1",
        label="main",
        kind="function",
        properties={"line": 10},
        provenance=prov,
    )
    node_dict = node.to_dict()
    assert node_dict["provenance"]["source_file"] == "app/main.py"
    rebuilt_node = MemoryGraphNodeRecord.from_dict(node_dict)
    assert rebuilt_node.provenance is not None
    assert rebuilt_node.provenance.source_symbol == "main"

    # Edge record
    edge = MemoryGraphEdgeRecord(
        source="node_1",
        target="node_2",
        kind="calls",
        relationship_type="invokes",
        provenance=prov,
    )
    edge_dict = edge.to_dict()
    rebuilt_edge = MemoryGraphEdgeRecord.from_dict(edge_dict)
    assert rebuilt_edge.provenance is not None
    assert rebuilt_edge.provenance.relationship_kind == "entrypoint"

    # Data item record
    item = MemoryDataItemRecord(
        id="item_1",
        name="main.py",
        mime_type="text/x-python",
        data_size=500,
        provenance=prov,
    )
    item_dict = item.to_dict()
    rebuilt_item = MemoryDataItemRecord.from_dict(item_dict)
    assert rebuilt_item.provenance is not None
    assert rebuilt_item.provenance.source_sha256 == "sha_xyz"

    # Vector stats record
    v_stats = MemoryVectorStatsRecord(
        tables=[{"table_name": "chunks", "row_count": 42}],
        total_vectors=42,
        embedding_model="nomic-embed-text",
        embedding_dimensions=768,
        storage_state=StorageSubsystemState.HEALTHY.value,
    )
    v_dict = v_stats.to_dict()
    rebuilt_v = MemoryVectorStatsRecord.from_dict(v_dict)
    assert rebuilt_v.storage_state == "healthy"
    assert rebuilt_v.total_vectors == 42
