"""Tests for Workspace Authorization Service and Trust Boundary Enforcement."""

from pathlib import Path
import pytest

from app.application.domain.repository import IndexedRepositoryRecord
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


class InMemoryMetadataStore(RepositoryMetadataPort):
    def __init__(self, records: list[IndexedRepositoryRecord] | None = None) -> None:
        self._records = {r.id: r for r in (records or [])}

    def load_all(self) -> list[IndexedRepositoryRecord]:
        return list(self._records.values())

    def get_by_id(self, repo_id: str) -> IndexedRepositoryRecord | None:
        return self._records.get(repo_id)

    def get_by_path(self, path: str) -> IndexedRepositoryRecord | None:
        norm = str(Path(path).resolve())
        for r in self._records.values():
            if str(Path(r.path).resolve()) == norm:
                return r
        return None

    def upsert(self, record: IndexedRepositoryRecord) -> None:
        self._records[record.id] = record

    def delete(self, repo_id: str) -> bool:
        return self._records.pop(repo_id, None) is not None

    def count(self) -> int:
        return len(self._records)


@pytest.fixture
def temp_workspace(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    repo_a = ws / "repo_a"
    repo_a.mkdir()
    (repo_a / "main.py").write_text("print('hello a')")

    repo_b = ws / "repo_b"
    repo_b.mkdir()
    (repo_b / "main.py").write_text("print('hello b')")

    external = tmp_path / "external"
    external.mkdir()
    (external / "secret.txt").write_text("sensitive")

    return {
        "root": ws,
        "repo_a": repo_a,
        "repo_b": repo_b,
        "external": external,
    }


def test_unregistered_unauthorized_path_rejected(temp_workspace):
    store = InMemoryMetadataStore([])
    auth_service = WorkspaceAuthorizationService(metadata_store=store, workspace_roots=[])

    is_auth, reason = auth_service.is_path_authorized(str(temp_workspace["repo_a"]))
    assert not is_auth
    assert "not an authorized repository" in reason.lower()


def test_registered_repository_path_authorized(temp_workspace):
    record = IndexedRepositoryRecord(
        id="1",
        name="repo_a",
        path=str(temp_workspace["repo_a"]),
        languages=["Python"],
        file_count=1,
        memory_size="4 KB",
        last_indexed="2026-08-21T00:00:00Z",
    )
    store = InMemoryMetadataStore([record])
    auth_service = WorkspaceAuthorizationService(metadata_store=store, workspace_roots=[])

    is_auth, reason = auth_service.is_path_authorized(str(temp_workspace["repo_a"]))
    assert is_auth
    assert reason is None


def test_workspace_root_child_authorized(temp_workspace):
    store = InMemoryMetadataStore([])
    auth_service = WorkspaceAuthorizationService(
        metadata_store=store,
        workspace_roots=[str(temp_workspace["root"])],
    )

    is_auth_a, _ = auth_service.is_path_authorized(str(temp_workspace["repo_a"]))
    is_auth_b, _ = auth_service.is_path_authorized(str(temp_workspace["repo_b"]))
    is_auth_ext, reason_ext = auth_service.is_path_authorized(str(temp_workspace["external"]))

    assert is_auth_a
    assert is_auth_b
    assert not is_auth_ext
    assert "not an authorized repository" in reason_ext.lower()


def test_sensitive_system_paths_rejected():
    store = InMemoryMetadataStore([])
    auth_service = WorkspaceAuthorizationService(metadata_store=store, workspace_roots=["/"])

    for sensitive_path in ["/etc", "/proc", "/sys", "/dev", "/root", "/var"]:
        if Path(sensitive_path).exists():
            is_auth, reason = auth_service.is_path_authorized(sensitive_path)
            assert not is_auth, f"Sensitive path {sensitive_path} should be rejected"
            assert "prohibited" in reason.lower() or "denied" in reason.lower()


def test_tmp_directory_rejected_when_not_in_workspace_roots():
    store = InMemoryMetadataStore([])
    auth_service = WorkspaceAuthorizationService(metadata_store=store, workspace_roots=[])

    is_auth, reason = auth_service.is_path_authorized("/tmp")
    assert not is_auth
    assert "not an authorized repository" in reason.lower()


def test_root_filesystem_rejected():
    store = InMemoryMetadataStore([])
    auth_service = WorkspaceAuthorizationService(metadata_store=store, workspace_roots=["/"])

    is_auth, reason = auth_service.is_path_authorized("/")
    assert not is_auth
    assert "root" in reason.lower() or "prohibited" in reason.lower()


def test_symlink_escape_rejected(temp_workspace):
    # Symlink pointing outside workspace root
    escape_link = temp_workspace["repo_a"] / "escape_symlink"
    escape_link.symlink_to(temp_workspace["external"], target_is_directory=True)

    store = InMemoryMetadataStore([])
    auth_service = WorkspaceAuthorizationService(
        metadata_store=store,
        workspace_roots=[str(temp_workspace["repo_a"])],
    )

    is_auth, reason = auth_service.is_path_authorized(str(escape_link))
    assert not is_auth
    assert "not an authorized repository" in reason.lower()


def test_dynamic_add_workspace_root(temp_workspace):
    store = InMemoryMetadataStore([])
    auth_service = WorkspaceAuthorizationService(metadata_store=store, workspace_roots=[])

    is_auth_before, _ = auth_service.is_path_authorized(str(temp_workspace["repo_a"]))
    assert not is_auth_before

    auth_service.add_workspace_root(str(temp_workspace["repo_a"]))
    is_auth_after, _ = auth_service.is_path_authorized(str(temp_workspace["repo_a"]))
    assert is_auth_after
