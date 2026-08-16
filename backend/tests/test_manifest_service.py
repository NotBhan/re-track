"""Unit tests for ManifestService and incremental delta indexing."""

from pathlib import Path
import time

import pytest

from app.services.manifest_service import (
    FileFingerprint,
    IndexDelta,
    ManifestService,
    RepositoryManifest,
)


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / "file1.py").write_text("print('hello')", encoding="utf-8")
    (repo / "file2.ts").write_text("const x = 1;", encoding="utf-8")
    return repo


@pytest.fixture
def manifest_service(tmp_path: Path) -> ManifestService:
    storage = tmp_path / "manifests"
    return ManifestService(storage_dir=storage)


def test_compute_sha256(temp_repo: Path):
    f1 = temp_repo / "file1.py"
    sha1 = ManifestService.compute_sha256(f1)
    assert len(sha1) == 64

    # Change content -> hash must change
    f1.write_text("print('hello world')", encoding="utf-8")
    sha2 = ManifestService.compute_sha256(f1)
    assert sha1 != sha2


def test_delta_first_run(manifest_service: ManifestService, temp_repo: Path):
    files = [temp_repo / "file1.py", temp_repo / "file2.ts"]
    delta, manifest = manifest_service.compute_delta(temp_repo, files)

    assert manifest is None
    assert delta.has_changes is True
    assert set(delta.added) == set(files)
    assert len(delta.modified) == 0
    assert len(delta.deleted) == 0
    assert len(delta.unchanged) == 0


def test_delta_after_initial_index(
    manifest_service: ManifestService, temp_repo: Path
):
    files = [temp_repo / "file1.py", temp_repo / "file2.ts"]
    
    # Save initial manifest
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
    )

    # Re-compute delta without modifying files
    delta, manifest = manifest_service.compute_delta(temp_repo, files)
    assert manifest is not None
    assert delta.has_changes is False
    assert len(delta.added) == 0
    assert len(delta.modified) == 0
    assert len(delta.deleted) == 0
    assert len(delta.unchanged) == 2


def test_delta_with_added_modified_deleted(
    manifest_service: ManifestService, temp_repo: Path
):
    f1 = temp_repo / "file1.py"
    f2 = temp_repo / "file2.ts"
    files = [f1, f2]

    # Initial index
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
    )

    # 1. Modify file1.py
    time.sleep(0.01)
    f1.write_text("print('modified')", encoding="utf-8")

    # 2. Add file3.md
    f3 = temp_repo / "file3.md"
    f3.write_text("# Readme", encoding="utf-8")

    # 3. Delete file2.ts from discovered list
    discovered = [f1, f3]

    delta, manifest = manifest_service.compute_delta(temp_repo, discovered)
    assert manifest is not None
    assert delta.has_changes is True
    assert delta.added == [f3]
    assert delta.modified == [f1]
    assert delta.deleted == ["file2.ts"]
    assert len(delta.unchanged) == 0
