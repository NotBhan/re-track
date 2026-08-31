"""Phase 10D.6 Task 3 — Dedicated test suite for SemanticMemoryRepository persistence.

Verifies:
1. Valid record persists and can be loaded.
2. Serialization is lossless.
3. Invalid/unanchored record is rejected before persistence.
4. Cross-repository record is rejected.
5. Deleted source becomes stale on reload.
6. Modified source SHA becomes stale on reload.
7. Missing symbol becomes stale/invalid on reload.
8. Repository isolation prevents cross-repo retrieval.
9. Repeated writes do not create duplicate records (upsert deduplication).
10. Derived-only invariant survives persistence round-trip.
11. Persisted records remain usable by Cognee semantic-memory mapping.
12. Atomic persistence does not leave partial/corrupt committed records.
"""

import json
from pathlib import Path
import pytest

from app.application.domain.memory import MemoryProvenance, SemanticMemoryRecord
from app.services.cognee_service import CogneeSemanticMemoryAdapter
from app.services.manifest_service import FileFingerprint, RepositoryManifest
from app.services.semantic_memory_repository import JsonSemanticMemoryRepository


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


def test_valid_record_persists_and_can_be_loaded(tmp_path: Path):
    """Verify that a valid SemanticMemoryRecord persists to disk and can be retrieved."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)
    manifest = _create_mock_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_auth_001",
        repository_id=manifest.dataset_name,
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="AuthService validates user session tokens.",
        source_files=["src/auth/service.py"],
        source_symbols=["AuthService", "verify_token"],
        source_sha256=["sha_auth_12345"],
        relationship_kind="auth_pipeline",
        generated_by="cognee_pipeline",
        generated_at=1710000000.0,
        evidence_status="derived_projection",
        is_derived=True,
        is_authoritative=False,
        confidence_score=0.95,
    )

    success, reason = repo.save(record, manifest=manifest)
    assert success is True
    assert reason == "valid"

    # Reload by ID
    loaded = repo.get("mem_auth_001", repository_id=manifest.dataset_name, manifest=manifest)
    assert loaded is not None
    assert loaded.memory_id == "mem_auth_001"
    assert loaded.repository_id == manifest.dataset_name
    assert loaded.repository_fingerprint == manifest.repo_fingerprint
    assert loaded.semantic_text == "AuthService validates user session tokens."
    assert loaded.source_files == ["src/auth/service.py"]
    assert loaded.source_symbols == ["AuthService", "verify_token"]
    assert loaded.source_sha256 == ["sha_auth_12345"]
    assert loaded.relationship_kind == "auth_pipeline"
    assert loaded.generated_by == "cognee_pipeline"
    assert loaded.generated_at == 1710000000.0
    assert loaded.evidence_status == "derived_projection"
    assert loaded.is_derived is True
    assert loaded.is_authoritative is False
    assert loaded.confidence_score == 0.95


def test_serialization_is_lossless(tmp_path: Path):
    """Verify that serialization to disk retains all 12 contract fields losslessly."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)
    manifest = _create_mock_manifest()

    original = SemanticMemoryRecord(
        memory_id="mem_lossless_002",
        repository_id="my_project",
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Lossless roundtrip serialization test.",
        source_files=["src/auth/models.py", "src/utils/crypto.py"],
        source_symbols=["SessionToken", "compare_digest"],
        source_sha256=["sha_models_67890", "sha_crypto_abcde"],
        relationship_kind="token_verification",
        generated_by="cognee_pipeline",
        generated_at=1710500000.0,
        evidence_status="derived_projection",
        is_derived=True,
        is_authoritative=False,
        confidence_score=0.88,
    )

    success, _ = repo.save(original)
    assert success is True

    records = repo.get_by_repository("my_project")
    assert len(records) == 1
    loaded = records[0]

    assert loaded.to_dict() == original.to_dict()


def test_invalid_unanchored_record_is_rejected_before_persistence(tmp_path: Path):
    """Verify that records missing files, SHAs, or IDs are rejected before write."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)

    unanchored = SemanticMemoryRecord(
        memory_id="unanchored_001",
        repository_id="my_project",
        repository_fingerprint="fp_123",
        semantic_text="Unanchored text without files.",
        source_files=[],
        source_symbols=[],
        source_sha256=[],
    )

    success, reason = repo.save(unanchored)
    assert success is False
    assert reason == "missing_source_files"
    assert not store_file.exists() or len(repo.load_all()) == 0


def test_cross_repository_record_is_rejected_on_save(tmp_path: Path):
    """Verify that records with mismatched repository fingerprints or IDs are rejected when saved with manifest."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)
    manifest = _create_mock_manifest()

    cross_repo_record = SemanticMemoryRecord(
        memory_id="cross_repo_001",
        repository_id=manifest.dataset_name,
        repository_fingerprint="alien_repository_fingerprint_999",
        semantic_text="Cross-repository test record.",
        source_files=["src/auth/service.py"],
        source_symbols=["AuthService"],
        source_sha256=["sha_auth_12345"],
    )

    success, reason = repo.save(cross_repo_record, manifest=manifest)
    assert success is False
    assert reason == "cross_repository_fingerprint_mismatch"
    assert len(repo.load_all()) == 0


def test_deleted_source_becomes_stale_on_reload(tmp_path: Path):
    """Verify that deleting a source file causes the record to become stale upon reload."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)
    manifest = _create_mock_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_delete_target",
        repository_id=manifest.dataset_name,
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Target for file deletion test.",
        source_files=["src/auth/models.py"],
        source_symbols=["SessionToken"],
        source_sha256=["sha_models_67890"],
    )
    repo.save(record)

    # Mutate manifest to simulate deleting src/auth/models.py
    del manifest.files["src/auth/models.py"]

    # Active query without include_stale should exclude it
    active_records = repo.get_by_repository(manifest.dataset_name, manifest=manifest, include_stale=False)
    assert len(active_records) == 0

    # Inspection query with include_stale should return marked as stale
    stale_records = repo.get_by_repository(manifest.dataset_name, manifest=manifest, include_stale=True)
    assert len(stale_records) == 1
    assert stale_records[0].evidence_status == "stale"
    assert stale_records[0].is_derived is True
    assert stale_records[0].is_authoritative is False


def test_modified_source_sha_becomes_stale_on_reload(tmp_path: Path):
    """Verify that modifying a source file SHA causes the record to become stale upon reload."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)
    manifest = _create_mock_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_sha_target",
        repository_id=manifest.dataset_name,
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Target for SHA modification test.",
        source_files=["src/auth/service.py"],
        source_symbols=["AuthService"],
        source_sha256=["sha_auth_12345"],
    )
    repo.save(record)

    # Mutate manifest to simulate file edit with new SHA
    manifest.files["src/auth/service.py"].sha256 = "new_mutated_sha_99999"

    # Active query excludes it
    active_records = repo.get_by_repository(manifest.dataset_name, manifest=manifest, include_stale=False)
    assert len(active_records) == 0

    # Stale query returns it marked as stale
    stale_records = repo.get_by_repository(manifest.dataset_name, manifest=manifest, include_stale=True)
    assert len(stale_records) == 1
    assert stale_records[0].evidence_status == "stale"


def test_missing_symbol_becomes_stale_on_reload(tmp_path: Path):
    """Verify that removing a referenced symbol causes the record to become stale upon reload."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)
    manifest = _create_mock_manifest()

    record = SemanticMemoryRecord(
        memory_id="mem_symbol_target",
        repository_id=manifest.dataset_name,
        repository_fingerprint=manifest.repo_fingerprint,
        semantic_text="Target for symbol removal test.",
        source_files=["src/auth/service.py"],
        source_symbols=["authenticate_user"],
        source_sha256=["sha_auth_12345"],
    )
    repo.save(record)

    # Mutate manifest to remove authenticate_user from AST symbols
    manifest.files["src/auth/service.py"].symbols = ["AuthService", "verify_token"]

    # Active query excludes it
    active_records = repo.get_by_repository(manifest.dataset_name, manifest=manifest, include_stale=False)
    assert len(active_records) == 0

    # Stale query returns it marked as stale
    stale_records = repo.get_by_repository(manifest.dataset_name, manifest=manifest, include_stale=True)
    assert len(stale_records) == 1
    assert stale_records[0].evidence_status == "stale"


def test_repository_isolation_prevents_cross_repo_retrieval(tmp_path: Path):
    """Verify that records for repository A are never returned when querying repository B."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)

    rec_a = SemanticMemoryRecord(
        memory_id="mem_repo_a",
        repository_id="repo_alpha",
        repository_fingerprint="fp_alpha",
        semantic_text="Alpha repository memory.",
        source_files=["src/a.py"],
        source_sha256=["sha_a"],
    )
    rec_b = SemanticMemoryRecord(
        memory_id="mem_repo_b",
        repository_id="repo_beta",
        repository_fingerprint="fp_beta",
        semantic_text="Beta repository memory.",
        source_files=["src/b.py"],
        source_sha256=["sha_b"],
    )

    repo.save(rec_a)
    repo.save(rec_b)

    alpha_records = repo.get_by_repository("repo_alpha")
    assert len(alpha_records) == 1
    assert alpha_records[0].memory_id == "mem_repo_a"

    beta_records = repo.get_by_repository("repo_beta")
    assert len(beta_records) == 1
    assert beta_records[0].memory_id == "mem_repo_b"


def test_repeated_writes_do_not_create_duplicate_records(tmp_path: Path):
    """Verify upsert behavior: repeated writes of the same memory_id update the record without duplicates."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)

    record_v1 = SemanticMemoryRecord(
        memory_id="mem_dedup_001",
        repository_id="my_project",
        repository_fingerprint="fp_001",
        semantic_text="Initial version.",
        source_files=["src/auth/service.py"],
        source_sha256=["sha_auth_12345"],
        confidence_score=0.70,
    )
    repo.save(record_v1)

    record_v2 = SemanticMemoryRecord(
        memory_id="mem_dedup_001",
        repository_id="my_project",
        repository_fingerprint="fp_001",
        semantic_text="Updated version with higher confidence.",
        source_files=["src/auth/service.py"],
        source_sha256=["sha_auth_12345"],
        confidence_score=0.98,
    )
    repo.save(record_v2)

    records = repo.get_by_repository("my_project")
    assert len(records) == 1
    assert records[0].memory_id == "mem_dedup_001"
    assert records[0].semantic_text == "Updated version with higher confidence."
    assert records[0].confidence_score == 0.98


def test_derived_only_invariant_survives_persistence_roundtrip(tmp_path: Path):
    """Verify that stored records strictly preserve derived-only invariants and reject authoritative claims."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)

    adversarial_record = SemanticMemoryRecord(
        memory_id="adv_mem_001",
        repository_id="my_project",
        repository_fingerprint="fp_001",
        semantic_text="Adversarial attempt.",
        source_files=["src/auth/service.py"],
        source_sha256=["sha_auth_12345"],
        is_derived=False,
        is_authoritative=True,
    )

    success, reason = repo.save(adversarial_record)
    assert success is False
    assert reason == "authoritative_status_forbidden"


def test_persisted_records_remain_usable_by_cognee_semantic_memory_mapping(tmp_path: Path):
    """Verify that Cognee adapter outputs persist cleanly and convert to MemoryProvenance."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)
    manifest = _create_mock_manifest()

    raw_cognee_item = {
        "id": "cognee_mapped_001",
        "text": "Mapped from Cognee recall result.",
        "source_files": ["src/auth/service.py"],
        "source_symbols": ["AuthService"],
        "relationship_kind": "authentication",
        "score": 0.94,
    }

    record, reason = CogneeSemanticMemoryAdapter.map_item(raw_cognee_item, manifest)
    assert reason == "valid"
    assert record is not None

    # Persist
    saved, save_reason = repo.save(record, manifest=manifest)
    assert saved is True
    assert save_reason == "valid"

    # Reload and test provenance conversion
    loaded = repo.get("cognee_mapped_001", repository_id=manifest.dataset_name, manifest=manifest)
    assert loaded is not None
    prov = loaded.to_provenance()
    assert isinstance(prov, MemoryProvenance)
    assert prov.repository_id == manifest.dataset_name
    assert prov.source_file == "src/auth/service.py"
    assert prov.source_sha256 == "sha_auth_12345"
    assert prov.source_symbol == "AuthService"


def test_atomic_persistence_does_not_leave_partial_or_corrupt_committed_records(tmp_path: Path):
    """Verify that persistence writes atomically and handles file recovery gracefully."""
    store_file = tmp_path / "semantic_memory.json"
    repo = JsonSemanticMemoryRepository(store_path=store_file)

    record = SemanticMemoryRecord(
        memory_id="mem_atomic_001",
        repository_id="my_project",
        repository_fingerprint="fp_001",
        semantic_text="Atomic persistence test.",
        source_files=["src/auth/service.py"],
        source_sha256=["sha_auth_12345"],
    )

    repo.save(record)
    assert store_file.exists()
    assert not store_file.with_suffix(".tmp").exists()

    # Corrupt store file intentionally to test error resilience
    store_file.write_text("corrupted invalid json {{{")
    fallback_records = repo.load_all()
    assert fallback_records == []
