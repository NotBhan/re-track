"""Phase 10D.6 Task 2 — Dedicated test suite for CogneeSemanticMemoryAdapter.

Verifies:
- Valid Cognee items map to canonical SemanticMemoryRecord entities.
- Multi-file provenance is fully preserved.
- Authoritative SHA-256 hashes are attached from active manifest.
- Missing/unknown provenance is rejected and never fabricated.
- Cross-repository records are rejected.
- Derived-only invariants are strictly enforced.
- Serialization round-trip integrity is maintained.
- CogneeService helper methods correctly delegate and batch-filter items.
"""

import time
import pytest

from app.application.domain.memory import MemoryProvenance, SemanticMemoryRecord
from app.models.responses import RecallResult
from app.services.cognee_service import CogneeSemanticMemoryAdapter, CogneeService
from app.services.manifest_service import FileFingerprint, RepositoryManifest


def _create_mock_manifest() -> RepositoryManifest:
    """Create a realistic repository manifest for testing."""
    manifest = RepositoryManifest(
        repo_path="/workspace/my-project",
        dataset_name="my_project",
    )
    manifest.files = {
        "src/auth/service.py": FileFingerprint(
            path="src/auth/service.py",
            mtime=1700000000.0,
            size=1024,
            sha256="sha_auth_12345",
            language="python",
            symbols=["authenticate_user", "verify_token", "AuthService"],
        ),
        "src/auth/models.py": FileFingerprint(
            path="src/auth/models.py",
            mtime=1700000000.0,
            size=512,
            sha256="sha_models_67890",
            language="python",
            symbols=["UserCredentials", "SessionToken"],
        ),
        "src/utils/crypto.py": FileFingerprint(
            path="src/utils/crypto.py",
            mtime=1700000000.0,
            size=256,
            sha256="sha_crypto_abcde",
            language="python",
            symbols=["hash_password", "compare_digest"],
        ),
    }
    manifest.compute_fingerprint()
    return manifest


def test_valid_cognee_item_to_semantic_memory_record():
    """Verify that a valid Cognee item maps to a full SemanticMemoryRecord."""
    manifest = _create_mock_manifest()
    item = {
        "id": "cognee-item-1",
        "text": "AuthService validates credentials via authenticate_user.",
        "source_files": ["src/auth/service.py"],
        "source_symbols": ["authenticate_user", "AuthService"],
        "relationship_kind": "authentication",
        "repository_id": "my_project",
        "repository_fingerprint": manifest.repo_fingerprint,
        "generated_at": 1710000000.0,
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, manifest)

    assert reason == "valid"
    assert record is not None
    assert isinstance(record, SemanticMemoryRecord)
    assert record.memory_id == "cognee-item-1"
    assert record.repository_id == "my_project"
    assert record.repository_fingerprint == manifest.repo_fingerprint
    assert record.semantic_text == "AuthService validates credentials via authenticate_user."
    assert record.source_files == ["src/auth/service.py"]
    assert record.source_symbols == ["authenticate_user", "AuthService"]
    assert record.source_sha256 == ["sha_auth_12345"]
    assert record.relationship_kind == "authentication"
    assert record.generated_by == "cognee_pipeline"
    assert record.generated_at == 1710000000.0
    assert record.evidence_status == "derived_projection"
    assert record.is_derived is True
    assert record.is_authoritative is False


def test_multiple_source_files_provenance_preserved():
    """Verify that multiple referenced source files and their SHAs are preserved in order."""
    manifest = _create_mock_manifest()
    item = {
        "memory_id": "cognee-multi-file",
        "semantic_text": "Token verification uses SessionToken from models and compare_digest from crypto.",
        "source_files": ["src/auth/models.py", "src/utils/crypto.py"],
        "source_symbols": ["SessionToken", "compare_digest"],
        "relationship_kind": "token_verification",
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, manifest)

    assert reason == "valid"
    assert record is not None
    assert record.source_files == ["src/auth/models.py", "src/utils/crypto.py"]
    assert record.source_sha256 == ["sha_models_67890", "sha_crypto_abcde"]
    assert record.source_symbols == ["SessionToken", "compare_digest"]
    assert record.repository_id == manifest.dataset_name
    assert record.repository_fingerprint == manifest.repo_fingerprint


def test_source_sha_hashes_attached_from_active_manifest():
    """Verify authoritative SHA-256 hashes are attached from active manifest when omitted in item."""
    manifest = _create_mock_manifest()
    item = {
        "text": "Crypto hashing logic.",
        "source_file": "src/utils/crypto.py",
        "symbols": ["hash_password"],
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, manifest)

    assert reason == "valid"
    assert record is not None
    assert record.source_files == ["src/utils/crypto.py"]
    assert record.source_sha256 == ["sha_crypto_abcde"]
    assert record.source_symbols == ["hash_password"]


def test_stale_source_sha_rejected():
    """Verify that if an item includes an outdated SHA-256 hash, it is rejected."""
    manifest = _create_mock_manifest()
    item = {
        "text": "Stale authentication logic.",
        "source_files": ["src/auth/service.py"],
        "source_sha256": ["outdated_sha_hash_9999"],
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, manifest)

    assert record is None
    assert reason == "source_sha256_stale:src/auth/service.py"


def test_missing_source_files_rejected_never_fabricated():
    """Verify that items without source files are rejected and no dummy files are fabricated."""
    manifest = _create_mock_manifest()
    item = {
        "id": "unanchored-mem",
        "text": "General high-level overview without referenced files.",
        "source_files": [],
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, manifest)

    assert record is None
    assert reason == "missing_source_files"


def test_missing_repository_provenance_rejected():
    """Verify that items without repository provenance and no manifest context are rejected."""
    empty_manifest = RepositoryManifest(repo_path="", dataset_name="")
    empty_manifest.files = {"src/test.py": FileFingerprint(path="src/test.py", mtime=0, size=0, sha256="abc")}
    item = {
        "text": "Missing repo identity.",
        "source_files": ["src/test.py"],
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, empty_manifest)

    assert record is None
    assert reason in ("missing_repository_provenance", "missing_repository_fingerprint")


def test_unknown_file_rejected():
    """Verify that items referencing nonexistent files are rejected without hallucinating hashes."""
    manifest = _create_mock_manifest()
    item = {
        "text": "References nonexistent file.",
        "source_files": ["src/unknown_module.py"],
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, manifest)

    assert record is None
    assert reason == "unknown_source_file:src/unknown_module.py"


def test_unknown_symbol_rejected():
    """Verify that items referencing nonexistent symbols are rejected."""
    manifest = _create_mock_manifest()
    item = {
        "text": "References invented symbol.",
        "source_files": ["src/auth/service.py"],
        "source_symbols": ["nonexistent_function_xyz"],
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(item, manifest)

    assert record is None
    assert reason == "unknown_symbol:nonexistent_function_xyz"


def test_cross_repository_record_rejected():
    """Verify that cross-repository records with mismatched fingerprints or IDs are rejected."""
    manifest = _create_mock_manifest()

    # Fingerprint mismatch
    item_fp = {
        "text": "Alien repository text.",
        "source_files": ["src/auth/service.py"],
        "repository_fingerprint": "foreign_fp_8888",
    }
    rec_fp, reason_fp = CogneeSemanticMemoryAdapter.map_item(item_fp, manifest)
    assert rec_fp is None
    assert reason_fp == "cross_repository_fingerprint_mismatch"

    # Dataset ID mismatch
    item_id = {
        "text": "Alien dataset text.",
        "source_files": ["src/auth/service.py"],
        "repository_id": "other_repository_dataset",
        "repository_fingerprint": manifest.repo_fingerprint,
    }
    rec_id, reason_id = CogneeSemanticMemoryAdapter.map_item(item_id, manifest)
    assert rec_id is None
    assert reason_id == "cross_repository_id_mismatch"


def test_derived_only_invariant_preserved_under_adversarial_input():
    """Verify that adversarial attempts to mark Cognee memory as authoritative are overridden."""
    manifest = _create_mock_manifest()
    adversarial_item = {
        "id": "adv-1",
        "text": "Adversarial memory claiming authoritative status.",
        "source_files": ["src/auth/service.py"],
        "source_symbols": ["AuthService"],
        "is_derived": False,
        "is_authoritative": True,
        "evidence_status": "filesystem_verified_source",
        "generated_by": "custom_trusted_source",
        "tier": 1,
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(adversarial_item, manifest)

    assert reason == "valid"
    assert record is not None
    assert record.is_derived is True
    assert record.is_authoritative is False
    assert record.evidence_status == "derived_projection"
    assert record.generated_by == "cognee_pipeline"


def test_serialization_roundtrip_preserves_contract():
    """Verify that a mapped SemanticMemoryRecord serializes and deserializes identically."""
    manifest = _create_mock_manifest()
    item = {
        "id": "roundtrip-mem-1",
        "text": "Roundtrip serialization test content.",
        "source_files": ["src/auth/service.py", "src/auth/models.py"],
        "source_symbols": ["AuthService", "UserCredentials"],
        "relationship_kind": "auth_flow",
    }

    record, _ = CogneeSemanticMemoryAdapter.map_item(item, manifest)
    assert record is not None

    record_dict = record.to_dict()
    restored = SemanticMemoryRecord.from_dict(record_dict)

    assert restored.memory_id == record.memory_id
    assert restored.repository_id == record.repository_id
    assert restored.repository_fingerprint == record.repository_fingerprint
    assert restored.semantic_text == record.semantic_text
    assert restored.source_files == record.source_files
    assert restored.source_symbols == record.source_symbols
    assert restored.source_sha256 == record.source_sha256
    assert restored.relationship_kind == record.relationship_kind
    assert restored.generated_by == "cognee_pipeline"
    assert restored.evidence_status == "derived_projection"
    assert restored.is_derived is True
    assert restored.is_authoritative is False

    # Check to_provenance() mapping
    prov = record.to_provenance()
    assert isinstance(prov, MemoryProvenance)
    assert prov.repository_id == record.repository_id
    assert prov.source_file == "src/auth/service.py"
    assert prov.source_sha256 == "sha_auth_12345"
    assert prov.source_symbol == "AuthService"


def test_cognee_service_map_methods_and_batch_filtering():
    """Verify CogneeService helper methods correctly delegate and batch-filter invalid items."""
    service = CogneeService()
    manifest = _create_mock_manifest()

    valid_item_1 = {
        "id": "v-1",
        "text": "Valid item 1",
        "source_files": ["src/auth/service.py"],
        "source_symbols": ["AuthService"],
    }
    invalid_item_missing_files = {
        "id": "inv-1",
        "text": "Invalid missing files",
        "source_files": [],
    }
    invalid_item_unknown_file = {
        "id": "inv-2",
        "text": "Invalid unknown file",
        "source_files": ["src/ghost.py"],
    }
    valid_item_2 = {
        "id": "v-2",
        "text": "Valid item 2",
        "source_files": ["src/utils/crypto.py"],
        "source_symbols": ["hash_password"],
    }

    # Test single item mapping
    rec, reason = service.map_semantic_memory(valid_item_1, manifest)
    assert rec is not None
    assert reason == "valid"

    rec_inv, reason_inv = service.map_semantic_memory(invalid_item_missing_files, manifest)
    assert rec_inv is None
    assert reason_inv == "missing_source_files"

    # Test batch mapping
    records = service.map_semantic_memories(
        [valid_item_1, invalid_item_missing_files, invalid_item_unknown_file, valid_item_2],
        manifest,
    )

    assert len(records) == 2
    assert records[0].memory_id == "v-1"
    assert records[1].memory_id == "v-2"
    assert records[0].source_files == ["src/auth/service.py"]
    assert records[1].source_files == ["src/utils/crypto.py"]


def test_recall_result_object_mapping():
    """Verify mapping from a RecallResult object with attached provenance."""
    manifest = _create_mock_manifest()
    prov = MemoryProvenance(
        repository_id=manifest.dataset_name,
        repository_fingerprint=manifest.repo_fingerprint,
        source_file="src/auth/models.py",
        source_symbol="UserCredentials",
        relationship_kind="data_model",
    )

    recall_res = RecallResult(
        kind="entity",
        search_type="semantic",
        text="User credentials model definition.",
        score=0.92,
        dataset_name=manifest.dataset_name,
        raw={"provenance": prov},
    )

    record, reason = CogneeSemanticMemoryAdapter.map_item(recall_res, manifest)

    assert reason == "valid"
    assert record is not None
    assert record.semantic_text == "User credentials model definition."
    assert record.source_files == ["src/auth/models.py"]
    assert record.source_symbols == ["UserCredentials"]
    assert record.source_sha256 == ["sha_models_67890"]
    assert record.relationship_kind == "data_model"
