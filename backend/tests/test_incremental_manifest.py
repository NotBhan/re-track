"""Tests for Phase 10A Incremental Manifest & State Model."""

import json
from pathlib import Path
import time

import pytest

from app.services.manifest_service import (
    FileFingerprint,
    IndexDelta,
    MANIFEST_SCHEMA_VERSION,
    ManifestService,
    PARSER_VERSION,
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


def test_manifest_serialization_roundtrip(manifest_service: ManifestService, temp_repo: Path):
    f1 = temp_repo / "file1.py"
    f2 = temp_repo / "file2.ts"
    files = [f1, f2]

    file_meta = {
        "file1.py": {
            "language": "Python",
            "symbols": ["hello_func"],
            "imports": ["sys"],
            "ast_nodes": [{"id": "file1.hello_func", "label": "hello_func", "file": "file1.py", "kind": "function", "line": 1}],
            "ast_edges": [],
        },
        "file2.ts": {
            "language": "TypeScript",
            "symbols": ["x"],
            "imports": [],
            "ast_nodes": [],
            "ast_edges": [],
        },
    }

    manifest = manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=file_meta,
    )

    loaded = manifest_service.load_manifest(temp_repo)
    assert loaded is not None
    assert loaded.repo_path == str(temp_repo.resolve())
    assert loaded.dataset_name == "test_dataset"
    assert loaded.schema_version == MANIFEST_SCHEMA_VERSION
    assert loaded.parser_version == PARSER_VERSION
    assert loaded.repo_fingerprint == manifest.repo_fingerprint
    assert len(loaded.files) == 2

    fp1 = loaded.files["file1.py"]
    assert fp1.language == "Python"
    assert fp1.symbols == ["hello_func"]
    assert fp1.imports == ["sys"]
    assert len(fp1.ast_nodes) == 1
    assert fp1.ast_nodes[0]["id"] == "file1.hello_func"


def test_deterministic_fingerprint(manifest_service: ManifestService, temp_repo: Path):
    f1 = temp_repo / "file1.py"
    files = [f1]

    m1 = manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
    )
    fp1 = m1.repo_fingerprint

    # Save same files again -> fingerprint must be identical
    m2 = manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
        existing_manifest=m1,
    )
    assert m2.repo_fingerprint == fp1

    # Modify content -> fingerprint must change
    time.sleep(0.01)
    f1.write_text("print('modified content')", encoding="utf-8")
    m3 = manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
        existing_manifest=m2,
    )
    assert m3.repo_fingerprint != fp1


def test_mtime_only_change_detected_as_unchanged(manifest_service: ManifestService, temp_repo: Path):
    """If mtime changes but content hash is identical, file must be classified as unchanged."""
    f1 = temp_repo / "file1.py"
    files = [f1]

    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
    )

    # Touch file (change mtime without modifying content)
    import os
    st = f1.stat()
    os.utime(f1, (st.st_atime + 100, st.st_mtime + 100))

    delta, manifest = manifest_service.compute_delta(temp_repo, files)
    assert manifest is not None
    assert delta.has_changes is False
    assert len(delta.unchanged) == 1
    assert len(delta.modified) == 0


def test_rename_detection_unambiguous(manifest_service: ManifestService, temp_repo: Path):
    """Renaming a file with identical content is detected as a rename."""
    f1 = temp_repo / "file1.py"
    content = f1.read_text(encoding="utf-8")
    files = [f1]

    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
    )

    # Delete file1.py and create renamed_file1.py with identical content
    f1.unlink()
    f1_renamed = temp_repo / "renamed_file1.py"
    f1_renamed.write_text(content, encoding="utf-8")

    discovered = [f1_renamed]
    delta, manifest = manifest_service.compute_delta(temp_repo, discovered)

    assert delta.has_changes is True
    assert len(delta.renamed) == 1
    assert delta.renamed[0] == ("file1.py", f1_renamed)
    assert len(delta.deleted) == 0
    assert len(delta.added) == 0


def test_ambiguous_rename_fallback(manifest_service: ManifestService, temp_repo: Path):
    """If multiple added files have the same hash as a deleted file, fall back conservatively to delete + add."""
    f1 = temp_repo / "file1.py"
    content = "identical content in multiple files"
    f1.write_text(content, encoding="utf-8")
    files = [f1]

    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
    )

    # Delete file1.py and create two new files with the same content
    f1.unlink()
    copy_a = temp_repo / "copy_a.py"
    copy_b = temp_repo / "copy_b.py"
    copy_a.write_text(content, encoding="utf-8")
    copy_b.write_text(content, encoding="utf-8")

    discovered = [copy_a, copy_b]
    delta, manifest = manifest_service.compute_delta(temp_repo, discovered)

    assert delta.has_changes is True
    assert len(delta.renamed) == 0
    assert delta.deleted == ["file1.py"]
    assert set(delta.added) == {copy_a, copy_b}


def test_corrupted_manifest_triggers_full_rebuild(manifest_service: ManifestService, temp_repo: Path):
    """Corrupted JSON in manifest returns None, triggering a full rebuild."""
    f1 = temp_repo / "file1.py"
    files = [f1]

    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=files,
        deleted_rel_paths=[],
    )

    manifest_path = manifest_service._get_manifest_path(temp_repo)
    assert manifest_path.exists()
    # Corrupt JSON
    manifest_path.write_text("CORRUPTED_JSON_NOT_VALID", encoding="utf-8")

    loaded = manifest_service.load_manifest(temp_repo)
    assert loaded is None

    delta, manifest = manifest_service.compute_delta(temp_repo, files)
    assert manifest is None
    assert delta.has_changes is True
    assert delta.added == files


def test_schema_or_parser_version_mismatch_triggers_rebuild(manifest_service: ManifestService, temp_repo: Path):
    """Manifest with outdated schema or parser version triggers full rebuild."""
    f1 = temp_repo / "file1.py"
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=[f1],
        deleted_rel_paths=[],
    )

    manifest_path = manifest_service._get_manifest_path(temp_repo)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Modify schema_version to 999.0
    data["schema_version"] = "999.0"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    loaded = manifest_service.load_manifest(temp_repo)
    assert loaded is None


def test_repo_identity_mismatch_triggers_rebuild(manifest_service: ManifestService, temp_repo: Path):
    """Manifest containing different repo_path triggers full rebuild."""
    f1 = temp_repo / "file1.py"
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_dataset",
        indexed_files=[f1],
        deleted_rel_paths=[],
    )

    manifest_path = manifest_service._get_manifest_path(temp_repo)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["repo_path"] = "/nonexistent/other/repo"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    loaded = manifest_service.load_manifest(temp_repo)
    assert loaded is None
