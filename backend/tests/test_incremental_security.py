"""Tests for Phase 10A Security Boundaries, Workspace Authorization, and Isolation."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

import asyncio
from app.application.dto import ErrorResponse, IndexRepositoryRequest, IndexRepositoryResponse
from app.application.use_cases.indexing import IndexingUseCases
from app.services.indexing_service import IndexingService
from app.services.manifest_service import ManifestService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService


@pytest.fixture
def auth_service(tmp_path: Path) -> WorkspaceAuthorizationService:
    allowed_dir = tmp_path / "allowed_workspace"
    allowed_dir.mkdir()
    auth = WorkspaceAuthorizationService(workspace_roots=[allowed_dir])
    return auth


@pytest.fixture
def mock_cognee() -> MagicMock:
    mock = MagicMock()
    mock.add = AsyncMock(return_value=None)
    return mock


@pytest.mark.asyncio
async def test_unauthorized_workspace_rejected_before_diff(
    tmp_path: Path, auth_service: WorkspaceAuthorizationService, mock_cognee: MagicMock
):
    """Context and retrieval requests targeting unauthorized paths are rejected at the security boundary."""
    unauthorized = tmp_path / "unauthorized_repo"
    unauthorized.mkdir()
    (unauthorized / "main.py").write_text("print('secret')", encoding="utf-8")

    from app.application.dto import AgentContextRequest
    from app.application.use_cases.context import ContextUseCases
    from app.services.context_cache import ContextCacheEngine

    manifest_svc = ManifestService(storage_dir=tmp_path / "manifests")
    indexing_svc = IndexingService(cognee_service=mock_cognee, manifest_service=manifest_svc)

    ctx_use_case = ContextUseCases(
        context_service=None,
        cognee_service=mock_cognee,
        indexing_service=indexing_svc,
        intent_parser=None,
        llm_provider=None,
        cgc_service=None,
        summary_generator=None,
        context_cache=ContextCacheEngine(),
        context_gen_lock=asyncio.Lock(),
        workspace_auth=auth_service,
    )

    req = AgentContextRequest(
        task_prompt="explain authentication",
        repository_path=str(unauthorized),
    )
    resp = await ctx_use_case.get_agent_context(req)

    assert isinstance(resp, ErrorResponse)
    assert resp.error == "AuthorizationError"
    # Verify no manifest loaded or created for unauthorized repo
    assert manifest_svc.load_manifest(unauthorized) is None


@pytest.mark.asyncio
async def test_symlink_pointing_outside_workspace_is_not_indexed(
    tmp_path: Path, auth_service: WorkspaceAuthorizationService, mock_cognee: MagicMock
):
    """Symlinks escaping the repository boundary are excluded from discovery and manifest."""
    allowed = tmp_path / "allowed_workspace"
    outside_secret = tmp_path / "outside_secret"
    outside_secret.mkdir()
    secret_file = outside_secret / "passwords.txt"
    secret_file.write_text("super_secret_token", encoding="utf-8")

    # Create symlink inside allowed pointing outside
    symlink_file = allowed / "leak_symlink.py"
    try:
        symlink_file.symlink_to(secret_file)
    except OSError:
        pytest.skip("Symlink creation not supported in current environment")

    # Regular valid file
    (allowed / "valid.py").write_text("print('valid')", encoding="utf-8")

    manifest_svc = ManifestService(storage_dir=tmp_path / "manifests")
    indexing_svc = IndexingService(cognee_service=mock_cognee, manifest_service=manifest_svc)

    files = indexing_svc.discover_files(allowed)
    filtered = indexing_svc.filter_files(files, allowed)

    assert any(f.name == "valid.py" for f in filtered)
    # The external symlink must be filtered out
    assert not any(f.name == "leak_symlink.py" for f in filtered)


def test_cross_repository_manifest_isolation(tmp_path: Path):
    """Manifests for different repositories remain strictly isolated and cannot leak state."""
    storage = tmp_path / "manifests"
    service = ManifestService(storage_dir=storage)

    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    repo_a.mkdir()
    repo_b.mkdir()

    file_a = repo_a / "module.py"
    file_b = repo_b / "module.py"
    file_a.write_text("def func_a(): pass", encoding="utf-8")
    file_b.write_text("def func_b(): pass", encoding="utf-8")

    service.update_manifest(repo_a, "dataset_a", indexed_files=[file_a], deleted_rel_paths=[])
    service.update_manifest(repo_b, "dataset_b", indexed_files=[file_b], deleted_rel_paths=[])

    manifest_a = service.load_manifest(repo_a)
    manifest_b = service.load_manifest(repo_b)

    assert manifest_a is not None
    assert manifest_b is not None
    assert manifest_a.repo_path == str(repo_a)
    assert manifest_b.repo_path == str(repo_b)
    assert manifest_a.dataset_name == "dataset_a"
    assert manifest_b.dataset_name == "dataset_b"
    assert "module.py" in manifest_a.files
    assert "module.py" in manifest_b.files
    assert manifest_a.files["module.py"].sha256 != manifest_b.files["module.py"].sha256
