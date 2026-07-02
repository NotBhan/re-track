"""Tests for RepositoryManager service."""

import json
from pathlib import Path

import pytest

from app.models.repository import ScanResult
from app.services.repository_manager import RepositoryManager


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "repositories.json"


@pytest.fixture
def manager(store_path: Path) -> RepositoryManager:
    return RepositoryManager(store_path=store_path)


def _create_sample_repo(base: Path, name: str = "test-repo") -> Path:
    repo = base / name
    repo.mkdir(parents=True)
    (repo / "main.py").write_text("print('hello')")
    (repo / "utils.py").write_text("def helper(): pass")
    (repo / "app.js").write_text("console.log('hi')")
    (repo / "styles.css").write_text("body { color: red; }")
    (repo / "package.json").write_text("{}")
    return repo


# ── Import tests ─────────────────────────────────────────────────


def test_import_local_repository(tmp_path: Path, manager: RepositoryManager) -> None:
    repo_path = _create_sample_repo(tmp_path)
    result = manager.import_repository(source_type="local", local_path=str(repo_path))

    assert result.source_type == "local"
    assert result.local_path == str(repo_path)
    assert result.status == "registered"
    assert result.name == "test-repo"
    assert result.id is not None

    stored = manager.get_repository(result.id)
    assert stored.id == result.id
    assert stored.local_path == str(repo_path)


def test_import_nonexistent_path(manager: RepositoryManager) -> None:
    with pytest.raises(FileNotFoundError):
        manager.import_repository(source_type="local", local_path="/nonexistent/path/xyz")


def test_import_missing_local_path(manager: RepositoryManager) -> None:
    with pytest.raises(ValueError):
        manager.import_repository(source_type="local")


def test_import_unknown_source_type(manager: RepositoryManager) -> None:
    with pytest.raises(ValueError, match="Unknown source type"):
        manager.import_repository(source_type="unknown")


# ── Scan tests ───────────────────────────────────────────────────


def test_scan_repository(tmp_path: Path, manager: RepositoryManager) -> None:
    repo_path = _create_sample_repo(tmp_path)
    repo = manager.import_repository(source_type="local", local_path=str(repo_path))
    scan = manager.scan_repository(repo.id)

    assert isinstance(scan, ScanResult)
    assert "Python" in scan.languages
    assert "JavaScript" in scan.languages
    assert "Node.js" in scan.frameworks
    assert scan.file_count == 5  # main.py, utils.py, app.js, styles.css, package.json
    assert scan.size_bytes > 0
    assert scan.estimated_index_time_ms > 0

    updated = manager.get_repository(repo.id)
    assert updated.languages == scan.languages
    assert updated.frameworks == scan.frameworks
    assert updated.file_count == scan.file_count


def test_scan_nonexistent_repo(manager: RepositoryManager) -> None:
    with pytest.raises(KeyError):
        manager.scan_repository("nonexistent-id")


def test_scan_with_ignored_dirs(tmp_path: Path, manager: RepositoryManager) -> None:
    repo = _create_sample_repo(tmp_path)
    # Create files inside ignored directories that should be skipped
    (repo / "node_modules" / "pkg").mkdir(parents=True)
    (repo / "node_modules" / "pkg" / "index.js").write_text("// ignored")
    (repo / "__pycache__").mkdir(parents=True)
    (repo / "__pycache__" / "cache.pyc").write_text("cached")

    result = manager.import_repository(source_type="local", local_path=str(repo))
    scan = manager.scan_repository(result.id)

    # The ignored files should NOT be counted
    assert scan.file_count == 5  # Same 5 files from _create_sample_repo
    assert ".git" in scan.ignored_dirs
    assert "node_modules" in scan.ignored_dirs


# ── CRUD tests ───────────────────────────────────────────────────


def test_list_repositories(tmp_path: Path, manager: RepositoryManager) -> None:
    assert manager.list_repositories() == []

    repo_path = _create_sample_repo(tmp_path, "repo-a")
    manager.import_repository(source_type="local", local_path=str(repo_path))
    repo_path2 = _create_sample_repo(tmp_path, "repo-b")
    manager.import_repository(source_type="local", local_path=str(repo_path2))

    repos = manager.list_repositories()
    assert len(repos) == 2
    names = {r.name for r in repos}
    assert names == {"repo-a", "repo-b"}


def test_delete_repository(tmp_path: Path, manager: RepositoryManager) -> None:
    repo_path = _create_sample_repo(tmp_path)
    repo = manager.import_repository(source_type="local", local_path=str(repo_path))
    assert len(manager.list_repositories()) == 1

    manager.delete_repository(repo.id)
    assert len(manager.list_repositories()) == 0
    with pytest.raises(KeyError):
        manager.get_repository(repo.id)


def test_delete_nonexistent(manager: RepositoryManager) -> None:
    with pytest.raises(KeyError):
        manager.delete_repository("nonexistent-id")


def test_update_repository(tmp_path: Path, manager: RepositoryManager) -> None:
    repo_path = _create_sample_repo(tmp_path)
    repo = manager.import_repository(source_type="local", local_path=str(repo_path))

    updated = manager.update_repository(repo.id, name="renamed-repo", status="indexing")
    assert updated.name == "renamed-repo"
    assert updated.status == "indexing"


def test_update_nonexistent(manager: RepositoryManager) -> None:
    with pytest.raises(KeyError):
        manager.update_repository("nonexistent-id", name="x")


# ── Persistence tests ────────────────────────────────────────────


def test_persistence_across_instances(tmp_path: Path) -> None:
    store_path = tmp_path / "repositories.json"
    repo_path = _create_sample_repo(tmp_path)

    m1 = RepositoryManager(store_path=store_path)
    repo = m1.import_repository(source_type="local", local_path=str(repo_path))

    m2 = RepositoryManager(store_path=store_path)
    repos = m2.list_repositories()
    assert len(repos) == 1
    assert repos[0].id == repo.id


# ── Git info tests ───────────────────────────────────────────────


def test_scan_with_git_info(tmp_path: Path, manager: RepositoryManager) -> None:
    import subprocess

    repo_path = _create_sample_repo(tmp_path, "git-repo")
    subprocess.run(["git", "init"], cwd=str(repo_path), capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo_path), "add", "."], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(repo_path), "commit", "-m", "init", "--allow-empty"],
        capture_output=True, check=True,
    )

    repo = manager.import_repository(source_type="local", local_path=str(repo_path))
    assert repo.branch is not None
    assert repo.commit_hash is not None
    assert len(repo.commit_hash) == 40  # Full SHA-1 hash
