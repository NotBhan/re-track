"""Domain-level contract tests for SemanticMemoryRecord (Phase 10D.6 Task 1).

Verifies invariants:
- Mandatory repository provenance and non-empty source_files.
- Complete serialization/deserialization roundtrip.
- Valid manifest acceptance.
- Cross-repository isolation (fingerprint & repo_id rejection).
- Stale detection upon source SHA mutation.
- Invalidation upon deleted source file.
- Invalidation upon missing/renamed symbol.
- Strictly derived invariant: is_derived=True, is_authoritative=False.
- Semantic memory cannot satisfy Tier-1/Tier-2 authority checks.
"""

from typing import Any
import pytest

from app.application.domain.arbitration import AuthorityTier
from app.application.domain.memory import MemoryProvenance, SemanticMemoryRecord
from app.services.manifest_service import FileFingerprint, RepositoryManifest


def _create_test_manifest() -> RepositoryManifest:
    """Create a standardized repository manifest for contract testing."""
    manifest = RepositoryManifest(
        repo_path="/test/sample_repo",
        dataset_name="sample_repo",
        schema_version="2.0",
        parser_version="2.0.0",
        repo_fingerprint="sample_repo_fp_2026_abc123",
    )
    manifest.files["src/auth/jwt.py"] = FileFingerprint(
        path="src/auth/jwt.py",
        mtime=1700000000.0,
        size=1024,
        sha256="sha256_jwt_valid_hash_111",
        language="python",
        symbols=["issue_jwt_token", "verify_jwt_token", "JWTClaimsValidator"],
    )
    manifest.files["src/models/user.py"] = FileFingerprint(
        path="src/models/user.py",
        mtime=1700000000.0,
        size=2048,
        sha256="sha256_user_valid_hash_222",
        language="python",
        symbols=["User", "UserRole", "PermissionSet"],
    )
    return manifest


def test_semantic_memory_serialization_roundtrip():
    """Verify complete lossless roundtrip serialization and deserialization."""
    original = SemanticMemoryRecord(
        memory_id="mem_jwt_auth_001",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="JWT authentication issues tokens with standard claims and validates signature using HMAC.",
        source_files=["src/auth/jwt.py", "src/models/user.py"],
        source_symbols=["issue_jwt_token", "User"],
        source_sha256=["sha256_jwt_valid_hash_111", "sha256_user_valid_hash_222"],
        relationship_kind="validates_identity",
        generated_by="cognee_pipeline",
        generated_at=1700000100.0,
        evidence_status="derived_projection",
    )

    data = original.to_dict()
    assert isinstance(data, dict)
    assert data["memory_id"] == "mem_jwt_auth_001"
    assert data["repository_id"] == "sample_repo"
    assert data["repository_fingerprint"] == "sample_repo_fp_2026_abc123"
    assert data["source_files"] == ["src/auth/jwt.py", "src/models/user.py"]
    assert data["source_symbols"] == ["issue_jwt_token", "User"]
    assert data["source_sha256"] == ["sha256_jwt_valid_hash_111", "sha256_user_valid_hash_222"]
    assert data["relationship_kind"] == "validates_identity"
    assert data["is_derived"] is True
    assert data["is_authoritative"] is False

    restored = SemanticMemoryRecord.from_dict(data)
    assert restored.memory_id == original.memory_id
    assert restored.repository_id == original.repository_id
    assert restored.repository_fingerprint == original.repository_fingerprint
    assert restored.semantic_text == original.semantic_text
    assert restored.source_files == original.source_files
    assert restored.source_symbols == original.source_symbols
    assert restored.source_sha256 == original.source_sha256
    assert restored.relationship_kind == original.relationship_kind
    assert restored.generated_by == original.generated_by
    assert restored.generated_at == original.generated_at
    assert restored.evidence_status == original.evidence_status
    assert restored.is_derived is True
    assert restored.is_authoritative is False


def test_semantic_memory_requires_provenance_and_source_files():
    """Verify that records with missing repository provenance or empty source_files fail validation."""
    manifest = _create_test_manifest()

    # Missing repository_id
    rec_no_repo = SemanticMemoryRecord(
        memory_id="mem_invalid_01",
        repository_id="",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="Some text",
        source_files=["src/auth/jwt.py"],
    )
    valid, reason = rec_no_repo.validate_against_manifest(manifest)
    assert valid is False
    assert reason == "missing_repository_provenance"
    assert rec_no_repo.is_valid_for_manifest(manifest) is False

    # Missing repository_fingerprint
    rec_no_fp = SemanticMemoryRecord(
        memory_id="mem_invalid_02",
        repository_id="sample_repo",
        repository_fingerprint="",
        semantic_text="Some text",
        source_files=["src/auth/jwt.py"],
    )
    valid, reason = rec_no_fp.validate_against_manifest(manifest)
    assert valid is False
    assert reason == "missing_repository_provenance"

    # Missing source_files
    rec_no_files = SemanticMemoryRecord(
        memory_id="mem_invalid_03",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="Floating hallucinated summary without source file.",
        source_files=[],
    )
    valid, reason = rec_no_files.validate_against_manifest(manifest)
    assert valid is False
    assert reason == "missing_source_files"


def test_semantic_memory_valid_manifest_acceptance():
    """Verify that a well-formed record matching manifest passes validation."""
    manifest = _create_test_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_valid_001",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="JWT authentication implementation.",
        source_files=["src/auth/jwt.py"],
        source_symbols=["issue_jwt_token", "verify_jwt_token"],
        source_sha256=["sha256_jwt_valid_hash_111"],
    )

    valid, reason = record.validate_against_manifest(manifest)
    assert valid is True
    assert reason == "valid"
    assert record.is_valid_for_manifest(manifest) is True


def test_semantic_memory_cross_repository_rejection():
    """Verify that records from different repositories or fingerprints are rejected."""
    manifest = _create_test_manifest()

    # Fingerprint mismatch
    rec_wrong_fp = SemanticMemoryRecord(
        memory_id="mem_cross_01",
        repository_id="sample_repo",
        repository_fingerprint="other_repo_fp_9999",
        semantic_text="JWT auth from foreign branch.",
        source_files=["src/auth/jwt.py"],
    )
    valid, reason = rec_wrong_fp.validate_against_manifest(manifest)
    assert valid is False
    assert reason == "cross_repository_fingerprint_mismatch"

    # Repository ID mismatch
    rec_wrong_id = SemanticMemoryRecord(
        memory_id="mem_cross_02",
        repository_id="unrelated_project_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="Cross project contamination.",
        source_files=["src/auth/jwt.py"],
    )
    valid, reason = rec_wrong_id.validate_against_manifest(manifest)
    assert valid is False
    assert reason == "cross_repository_id_mismatch"


def test_semantic_memory_stale_on_file_sha_mutation():
    """Verify that a modified file SHA immediately invalidates the record as stale."""
    manifest = _create_test_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_stale_01",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="JWT authentication before refactoring.",
        source_files=["src/auth/jwt.py"],
        source_sha256=["sha256_outdated_old_sha_000"],
    )

    valid, reason = record.validate_against_manifest(manifest)
    assert valid is False
    assert "source_sha256_stale" in reason
    assert "src/auth/jwt.py" in reason
    assert record.is_valid_for_manifest(manifest) is False


def test_semantic_memory_invalid_on_deleted_source_file():
    """Verify that referencing a deleted or non-existent file invalidates the record."""
    manifest = _create_test_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_deleted_01",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="Summary of deleted legacy auth service.",
        source_files=["src/auth/legacy_auth.py"],
    )

    valid, reason = record.validate_against_manifest(manifest)
    assert valid is False
    assert "source_file_deleted" in reason
    assert "src/auth/legacy_auth.py" in reason


def test_semantic_memory_invalid_on_missing_symbol():
    """Verify that a renamed or removed symbol invalidates the record."""
    manifest = _create_test_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_missing_sym_01",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="Summary of non-existent helper function.",
        source_files=["src/auth/jwt.py"],
        source_symbols=["non_existent_auth_helper_function"],
        source_sha256=["sha256_jwt_valid_hash_111"],
    )

    valid, reason = record.validate_against_manifest(manifest)
    assert valid is False
    assert reason == "source_symbol_missing:non_existent_auth_helper_function"


def test_semantic_memory_invariant_always_derived_never_authoritative():
    """Verify domain invariant: semantic memory is always derived and never authoritative."""
    record = SemanticMemoryRecord(
        memory_id="mem_inv_01",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="Semantic summary description.",
        source_files=["src/auth/jwt.py"],
    )

    assert record.is_derived is True
    assert record.is_authoritative is False

    # Invariant holds even if dictionary attempts to tamper
    tampered_data = record.to_dict()
    tampered_data["is_authoritative"] = True  # Attempted forgery
    tampered_data["is_derived"] = False

    reconstructed = SemanticMemoryRecord.from_dict(tampered_data)
    # The domain model enforces derived status and forbids authoritative flag
    assert reconstructed.is_derived is True
    assert reconstructed.is_authoritative is False


def test_semantic_memory_cannot_satisfy_tier1_tier2_authority_check():
    """Verify that SemanticMemoryRecord maps to MemoryProvenance for Tier 4, not Tier 1 or Tier 2."""
    record = SemanticMemoryRecord(
        memory_id="mem_tier_01",
        repository_id="sample_repo",
        repository_fingerprint="sample_repo_fp_2026_abc123",
        semantic_text="JWT authentication explanation.",
        source_files=["src/auth/jwt.py"],
        source_symbols=["issue_jwt_token"],
        source_sha256=["sha256_jwt_valid_hash_111"],
        relationship_kind="auth_mechanism",
        generated_at=1700000200.0,
    )

    prov = record.to_provenance()
    assert isinstance(prov, MemoryProvenance)
    assert prov.repository_id == "sample_repo"
    assert prov.repository_fingerprint == "sample_repo_fp_2026_abc123"
    assert prov.source_file == "src/auth/jwt.py"
    assert prov.source_symbol == "issue_jwt_token"
    assert prov.source_sha256 == "sha256_jwt_valid_hash_111"
    assert prov.relationship_kind == "auth_mechanism"
    assert prov.indexed_at == 1700000200.0
    assert record.is_authoritative is False
    assert record.is_derived is True

    # Must be categorized as derived Tier 4, subordinated to Tier 1 and Tier 2 in sorting
    assert AuthorityTier.TIER_4_COGNEE.label == "validated_cognee"
    assert AuthorityTier.TIER_4_COGNEE.value < AuthorityTier.TIER_1_SOURCE.value
    assert AuthorityTier.TIER_4_COGNEE.value < AuthorityTier.TIER_2_MANIFEST_AST.value
