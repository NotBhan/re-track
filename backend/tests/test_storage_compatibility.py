"""Comprehensive storage compatibility and legacy fallback regression tests for RE:Track.

Validates the Phase 4 non-negotiable compatibility contract:
1. ~/.retrack/ is canonical writable storage.
2. ~/.andes/ is strictly read-only legacy compatibility storage.
3. Canonical data takes precedence over legacy data when both exist.
4. Reads from legacy data never mutate, delete, rename, or write back to legacy files.
5. All new writes/mutations target canonical storage exclusively.
6. Existing legacy clones remain usable and are never mutated.
7. DEBT-004 packaging isolation is enforced.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest

from app.application.domain.repository import IndexedRepositoryRecord
from app.config.settings import Settings
from app.models.context_package import SavedContextPackage
from app.models.repository import Repository
from app.services.context_package_repository import JsonContextPackageRepository
from app.services.manifest_service import ManifestService, RepositoryManifest
from app.services.repository_manager import RepositoryManager
from app.services.repository_metadata_store import JsonRepositoryMetadataStore


def compute_file_sha256(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestRepositoryMetadataStoreCompatibility:
    """Tests for JsonRepositoryMetadataStore dual-path compatibility."""

    def test_scenario_a_canonical_only(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "indexed_repos.json"
        legacy = tmp_path / ".andes" / "indexed_repos.json"

        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(json.dumps({"repositories": [{"id": "c1", "name": "canonical_repo", "path": "/path/c1"}]}))

        store = JsonRepositoryMetadataStore(store_path=canonical, legacy_store_path=legacy)
        records = store.load_all()
        assert len(records) == 1
        assert records[0].id == "c1"
        assert records[0].name == "canonical_repo"
        assert not legacy.exists()

    def test_scenario_b_legacy_only_and_immutability(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "indexed_repos.json"
        legacy = tmp_path / ".andes" / "indexed_repos.json"

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy_data = {"repositories": [{"id": "leg1", "name": "legacy_repo", "path": "/path/leg1"}]}
        legacy.write_text(json.dumps(legacy_data))
        legacy_sha_before = compute_file_sha256(legacy)

        store = JsonRepositoryMetadataStore(store_path=canonical, legacy_store_path=legacy)
        records = store.load_all()
        assert len(records) == 1
        assert records[0].id == "leg1"
        assert records[0].name == "legacy_repo"

        # Verify legacy file is byte-for-byte untouched
        assert compute_file_sha256(legacy) == legacy_sha_before
        assert not canonical.exists()

    def test_scenario_c_both_exist_canonical_precedence(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "indexed_repos.json"
        legacy = tmp_path / ".andes" / "indexed_repos.json"

        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(json.dumps({"repositories": [{"id": "c1", "name": "canonical_repo", "path": "/path/c1"}]}))

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"repositories": [{"id": "leg1", "name": "legacy_repo", "path": "/path/leg1"}]}))
        legacy_sha_before = compute_file_sha256(legacy)

        store = JsonRepositoryMetadataStore(store_path=canonical, legacy_store_path=legacy)
        records = store.load_all()
        assert len(records) == 1
        assert records[0].id == "c1"  # Canonical wins
        assert compute_file_sha256(legacy) == legacy_sha_before

    def test_scenario_d_neither_exists(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "indexed_repos.json"
        legacy = tmp_path / ".andes" / "indexed_repos.json"

        store = JsonRepositoryMetadataStore(store_path=canonical, legacy_store_path=legacy)
        records = store.load_all()
        assert records == []

    def test_scenario_e_legacy_read_then_mutation(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "indexed_repos.json"
        legacy = tmp_path / ".andes" / "indexed_repos.json"

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"repositories": [{"id": "leg1", "name": "legacy_repo", "path": "/path/leg1"}]}))
        legacy_sha_before = compute_file_sha256(legacy)

        store = JsonRepositoryMetadataStore(store_path=canonical, legacy_store_path=legacy)
        # Load legacy record, then mutate by upserting a new record
        store.upsert(IndexedRepositoryRecord(id="new2", name="new_repo", path="/path/new2"))

        # Legacy file MUST remain byte-for-byte identical
        assert compute_file_sha256(legacy) == legacy_sha_before

        # Canonical store MUST be created with both the existing in-memory records + new record
        assert canonical.exists()
        reloaded = JsonRepositoryMetadataStore(store_path=canonical, legacy_store_path=legacy).load_all()
        ids = {r.id for r in reloaded}
        assert "leg1" in ids
        assert "new2" in ids

    def test_scenario_h_malformed_legacy_data(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "indexed_repos.json"
        legacy = tmp_path / ".andes" / "indexed_repos.json"

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text("{ corrupt json invalid }")
        legacy_sha_before = compute_file_sha256(legacy)

        store = JsonRepositoryMetadataStore(store_path=canonical, legacy_store_path=legacy)
        records = store.load_all()
        assert records == []
        assert compute_file_sha256(legacy) == legacy_sha_before


class TestRepositoryManagerCompatibility:
    """Tests for RepositoryManager dual-path and clone safety compatibility."""

    def test_scenario_b_legacy_only_and_immutability(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "repositories.json"
        legacy = tmp_path / ".andes" / "repositories.json"

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({
            "repo1": {
                "id": "repo1",
                "name": "legacy_app",
                "source_type": "local",
                "local_path": str(tmp_path / "legacy_app"),
                "status": "ready",
            }
        }))
        legacy_sha_before = compute_file_sha256(legacy)

        mgr = RepositoryManager(store_path=canonical, legacy_store_path=legacy)
        repos = mgr.list_repositories()
        assert len(repos) == 1
        assert repos[0].id == "repo1"
        assert repos[0].name == "legacy_app"
        assert compute_file_sha256(legacy) == legacy_sha_before
        assert not canonical.exists()

    def test_scenario_c_canonical_precedence(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "repositories.json"
        legacy = tmp_path / ".andes" / "repositories.json"

        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text(json.dumps({"c1": {"id": "c1", "name": "canonical", "source_type": "local", "local_path": "/c1"}}))

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"leg1": {"id": "leg1", "name": "legacy", "source_type": "local", "local_path": "/leg1"}}))
        legacy_sha_before = compute_file_sha256(legacy)

        mgr = RepositoryManager(store_path=canonical, legacy_store_path=legacy)
        repos = mgr.list_repositories()
        assert len(repos) == 1
        assert repos[0].id == "c1"
        assert compute_file_sha256(legacy) == legacy_sha_before

    def test_scenario_e_mutation_writes_to_canonical_only(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "repositories.json"
        legacy = tmp_path / ".andes" / "repositories.json"

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"leg1": {"id": "leg1", "name": "legacy", "source_type": "local", "local_path": "/leg1"}}))
        legacy_sha_before = compute_file_sha256(legacy)

        mgr = RepositoryManager(store_path=canonical, legacy_store_path=legacy)
        mgr.update_repository("leg1", status="indexed")

        assert compute_file_sha256(legacy) == legacy_sha_before
        assert canonical.exists()
        assert "leg1" in json.loads(canonical.read_text())

    def test_scenario_g_clone_safety_and_deletion(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "repositories.json"
        legacy = tmp_path / ".andes" / "repositories.json"
        legacy_clone_dir = tmp_path / ".andes" / "repos" / "test_repo"
        legacy_clone_dir.mkdir(parents=True, exist_ok=True)
        (legacy_clone_dir / "main.py").write_text("print('hello')")
        file_sha_before = compute_file_sha256(legacy_clone_dir / "main.py")

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"r1": {"id": "r1", "name": "test_repo", "source_type": "local", "local_path": str(legacy_clone_dir)}}))

        mgr = RepositoryManager(
            store_path=canonical,
            legacy_store_path=legacy,
            repos_dir=tmp_path / ".retrack" / "repos",
            legacy_repos_dir=tmp_path / ".andes" / "repos",
        )

        # Scanning legacy clone must not mutate files in it
        scan = mgr.scan_repository("r1")
        assert scan.file_count == 1
        assert compute_file_sha256(legacy_clone_dir / "main.py") == file_sha_before

        # Deletion from RepositoryManager deletes metadata registration, never deleting directory
        mgr.delete_repository("r1")
        assert (legacy_clone_dir / "main.py").exists()
        assert compute_file_sha256(legacy_clone_dir / "main.py") == file_sha_before


class TestContextPackageRepositoryCompatibility:
    """Tests for JsonContextPackageRepository dual-path persistence."""

    def test_scenario_b_legacy_read_and_mutation(self, tmp_path: Path) -> None:
        import asyncio
        canonical = tmp_path / ".retrack" / "context_packages.json"
        legacy = tmp_path / ".andes" / "context_packages.json"

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({
            "pkg1": {
                "id": "pkg1",
                "name": "legacy_pkg",
                "task": "task1",
                "markdown": "# Legacy",
                "created_at": "2026-01-01T00:00:00Z",
            }
        }))
        legacy_sha_before = compute_file_sha256(legacy)

        repo = JsonContextPackageRepository(store_path=canonical, legacy_store_path=legacy)
        packages = asyncio.run(repo.list_all())
        assert len(packages) == 1
        assert packages[0].id == "pkg1"
        assert compute_file_sha256(legacy) == legacy_sha_before
        assert not canonical.exists()

        # Save new package -> writes to canonical only
        new_pkg = SavedContextPackage(id="pkg2", name="new_pkg", task="t2", markdown="# New")
        asyncio.run(repo.save(new_pkg))

        assert compute_file_sha256(legacy) == legacy_sha_before
        assert canonical.exists()
        data = json.loads(canonical.read_text())
        assert "pkg2" in data


class TestSettingsCompatibility:
    """Tests for Settings dual-path configuration persistence."""

    def test_scenario_b_legacy_settings_load_and_save(self, tmp_path: Path) -> None:
        canonical = tmp_path / ".retrack" / "settings.json"
        legacy = tmp_path / ".andes" / "settings.json"

        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(json.dumps({"vector_db": "legacy_vector", "llm_model": "legacy_model"}))
        legacy_sha_before = compute_file_sha256(legacy)

        settings = Settings(settings_store_path=canonical, legacy_settings_store_path=legacy)
        settings.load_persisted_settings()

        assert settings.storage.vector_db == "legacy_vector"
        assert settings.ollama.llm_model == "legacy_model"
        assert compute_file_sha256(legacy) == legacy_sha_before
        assert not canonical.exists()

        # Save settings -> writes to canonical only
        settings.storage.vector_db = "updated_vector"
        settings.save_persisted_settings()

        assert compute_file_sha256(legacy) == legacy_sha_before
        assert canonical.exists()
        saved_data = json.loads(canonical.read_text())
        assert saved_data["vector_db"] == "updated_vector"


class TestManifestServiceCompatibility:
    """Tests for ManifestService dual-path manifest management."""

    def test_scenario_b_legacy_manifest_load_and_save(self, tmp_path: Path) -> None:
        canonical_dir = tmp_path / ".retrack" / "manifests"
        legacy_dir = tmp_path / ".andes" / "manifests"
        repo_dir = tmp_path / "my_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)

        service = ManifestService(storage_dir=canonical_dir, legacy_storage_dir=legacy_dir)
        legacy_file = service._get_legacy_manifest_path(repo_dir)
        legacy_file.parent.mkdir(parents=True, exist_ok=True)

        manifest = RepositoryManifest(
            repo_path=str(repo_dir.resolve()),
            dataset_name="legacy_ds",
            created_at=100.0,
            updated_at=100.0,
        )
        legacy_file.write_text(json.dumps(manifest.to_dict()))
        legacy_sha_before = compute_file_sha256(legacy_file)

        loaded = service.load_manifest(repo_dir)
        assert loaded is not None
        assert loaded.dataset_name == "legacy_ds"
        assert compute_file_sha256(legacy_file) == legacy_sha_before

        # Saving updated manifest writes to canonical only
        loaded.dataset_name = "updated_ds"
        service.save_manifest(loaded)

        assert compute_file_sha256(legacy_file) == legacy_sha_before
        canonical_file = service._get_manifest_path(repo_dir)
        assert canonical_file.exists()
        assert json.loads(canonical_file.read_text())["dataset_name"] == "updated_ds"


def test_scenario_i_debt_004_isolation() -> None:
    """Test DEBT-004 resolution: importing app.services does not load FastAPI or heavy frameworks."""
    cmd = [
        sys.executable,
        "-c",
        """
import sys
import app.services
import app.services.local_filesystem
import app.services.hardware_telemetry
import app.services.repository_metadata_store
import app.services.repository_manager
import app.services.context_package_repository
import app.services.manifest_service

forbidden = ['fastapi', 'starlette', 'uvicorn', 'cognee.api.v1']
loaded = [m for m in sys.modules if any(m.startswith(f) for f in forbidden)]
assert len(loaded) == 0, f"Forbidden modules loaded: {loaded}"
print("DEBT-004 isolation passed")
""",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "DEBT-004 isolation passed" in res.stdout
