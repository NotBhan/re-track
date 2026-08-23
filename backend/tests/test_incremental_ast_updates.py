"""Tests for Phase 10A Incremental AST Extraction, 0-parse reuse, and relinking."""

from pathlib import Path
import time
import pytest

from app.models.responses import CallNode, CallEdge
from app.services.manifest_service import ManifestService
from app.services.repository_summary import RepositorySummaryGenerator


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test_repo"
    repo.mkdir()
    
    # auth service
    auth_dir = repo / "services"
    auth_dir.mkdir()
    (auth_dir / "auth.py").write_text("""
class AuthService:
    def authenticate(self, token: str) -> bool:
        return True

def verify_token(token: str) -> bool:
    return True
""", encoding="utf-8")

    # login handler
    handlers_dir = repo / "handlers"
    handlers_dir.mkdir()
    (handlers_dir / "login.py").write_text("""
from services.auth import verify_token, AuthService

def handle_login(req):
    verify_token(req.token)
    service = AuthService()
    service.authenticate("token")
""", encoding="utf-8")

    # unrelated utils
    (repo / "utils.py").write_text("""
def helper():
    return 42
""", encoding="utf-8")

    return repo


@pytest.fixture
def manifest_service(tmp_path: Path) -> ManifestService:
    storage = tmp_path / "manifests"
    return ManifestService(storage_dir=storage)


def test_initial_full_parse_and_manifest_recording(temp_repo: Path, manifest_service: ManifestService):
    """Initial indexing parses all files and records their AST metadata into manifest."""
    files = list(temp_repo.rglob("*.py"))
    gen = RepositorySummaryGenerator()

    # Full build without existing manifest
    summary = gen.generate(temp_repo, files)

    assert gen.last_parse_stats["files_parsed"] == 3
    assert gen.last_parse_stats["files_reused"] == 0

    # Save to manifest
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_ds",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )

    manifest = manifest_service.load_manifest(temp_repo)
    assert manifest is not None
    assert "services/auth.py" in manifest.files
    assert len(manifest.files["services/auth.py"].ast_nodes) > 0


def test_noop_zero_ast_parses(temp_repo: Path, manifest_service: ManifestService):
    """Re-indexing an unchanged repository performs zero source file parses."""
    files = list(temp_repo.rglob("*.py"))
    gen = RepositorySummaryGenerator()

    # 1. Initial build & manifest save
    gen.generate(temp_repo, files)
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_ds",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )

    # 2. Compute delta & re-generate
    delta, manifest = manifest_service.compute_delta(temp_repo, files)
    assert not delta.has_changes

    gen_noop = RepositorySummaryGenerator()
    summary_noop = gen_noop.generate(temp_repo, files, existing_manifest=manifest, delta=delta)

    assert gen_noop.last_parse_stats["files_parsed"] == 0
    assert gen_noop.last_parse_stats["files_reused"] == 3
    assert len(summary_noop.call_graph_nodes) > 0
    assert len(summary_noop.call_graph_edges) > 0


def test_single_file_edit_parses_only_changed_file(temp_repo: Path, manifest_service: ManifestService):
    """Modifying a single file parses ONLY that 1 file and reuses all other files from manifest."""
    files = list(temp_repo.rglob("*.py"))
    gen = RepositorySummaryGenerator()

    gen.generate(temp_repo, files)
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_ds",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )

    # Modify utils.py (unrelated file)
    time.sleep(0.01)
    utils_file = temp_repo / "utils.py"
    utils_file.write_text("""
def helper():
    return 100

def new_utility():
    return True
""", encoding="utf-8")

    delta, manifest = manifest_service.compute_delta(temp_repo, files)
    assert delta.has_changes
    assert len(delta.modified) == 1
    assert len(delta.unchanged) == 2

    gen_inc = RepositorySummaryGenerator()
    summary_inc = gen_inc.generate(temp_repo, files, existing_manifest=manifest, delta=delta)

    # Exactly 1 file parsed, 2 files reused
    assert gen_inc.last_parse_stats["files_parsed"] == 1
    assert gen_inc.last_parse_stats["files_reused"] == 2

    node_labels = {n.label for n in summary_inc.call_graph_nodes}
    assert "new_utility" in node_labels
    assert "AuthService" in node_labels


def test_file_addition_incrementally_incorporated(temp_repo: Path, manifest_service: ManifestService):
    """Adding a new source file parses ONLY the new file and updates call graph."""
    files = list(temp_repo.rglob("*.py"))
    gen = RepositorySummaryGenerator()
    gen.generate(temp_repo, files)
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_ds",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )

    # Add a new file
    payment_file = temp_repo / "services" / "payment.py"
    payment_file.write_text("""
class PaymentGateway:
    def process_payment(self, amount: float) -> bool:
        return True
""", encoding="utf-8")

    all_files = list(temp_repo.rglob("*.py"))
    delta, manifest = manifest_service.compute_delta(temp_repo, all_files)
    assert len(delta.added) == 1

    gen_add = RepositorySummaryGenerator()
    summary_add = gen_add.generate(temp_repo, all_files, existing_manifest=manifest, delta=delta)

    assert gen_add.last_parse_stats["files_parsed"] == 1
    assert gen_add.last_parse_stats["files_reused"] == 3

    node_labels = {n.label for n in summary_add.call_graph_nodes}
    assert "PaymentGateway" in node_labels


def test_file_deletion_removes_stale_nodes_and_dangling_edges(temp_repo: Path, manifest_service: ManifestService):
    """Deleting a file removes its nodes and purges any dangling call edges."""
    files = list(temp_repo.rglob("*.py"))
    gen = RepositorySummaryGenerator()
    summary = gen.generate(temp_repo, files)
    manifest_service.update_manifest(
        repo_path=temp_repo,
        dataset_name="test_ds",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )

    # Delete services/auth.py
    auth_file = temp_repo / "services" / "auth.py"
    auth_file.unlink()

    remaining_files = [f for f in temp_repo.rglob("*.py") if f.exists()]
    delta, manifest = manifest_service.compute_delta(temp_repo, remaining_files)
    assert "services/auth.py" in delta.deleted

    gen_del = RepositorySummaryGenerator()
    summary_del = gen_del.generate(temp_repo, remaining_files, existing_manifest=manifest, delta=delta)

    node_ids = {n.id for n in summary_del.call_graph_nodes}
    assert not any("services.auth" in nid for nid in node_ids)

    # Verify no dangling edges exist
    for edge in summary_del.call_graph_edges:
        assert edge.source in node_ids
        assert edge.target in node_ids


def test_typescript_jsx_render_resolution_incremental(tmp_path: Path, manifest_service: ManifestService):
    """TypeScript/React JSX component discovery and incremental render resolution."""
    repo = tmp_path / "ts_repo"
    repo.mkdir()

    comp_dir = repo / "src" / "components"
    comp_dir.mkdir(parents=True)
    btn_file = comp_dir / "Button.tsx"
    btn_file.write_text("""
export function Button() {
    return <button>Click</button>;
}
""", encoding="utf-8")

    app_dir = repo / "src" / "app"
    app_dir.mkdir(parents=True)
    page_file = app_dir / "page.tsx"
    page_file.write_text("""
import { Button } from '@/components/Button';

export default function Home() {
    return (
        <div>
            <Button />
        </div>
    );
}
""", encoding="utf-8")

    files = [btn_file, page_file]
    gen = RepositorySummaryGenerator()
    summary = gen.generate(repo, files)
    manifest_service.update_manifest(
        repo_path=repo,
        dataset_name="ts_ds",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )

    assert len(summary.call_graph_nodes) >= 2
    render_edges = [e for e in summary.call_graph_edges if e.kind == "renders"]
    assert any("Button" in e.target for e in render_edges)

    # Re-indexing without changes: 0 parses, render edges preserved
    delta, manifest = manifest_service.compute_delta(repo, files)
    gen_noop = RepositorySummaryGenerator()
    summary_noop = gen_noop.generate(repo, files, existing_manifest=manifest, delta=delta)

    assert gen_noop.last_parse_stats["files_parsed"] == 0
    assert gen_noop.last_parse_stats["files_reused"] == 2
    render_edges_noop = [e for e in summary_noop.call_graph_edges if e.kind == "renders"]
    assert len(render_edges_noop) == len(render_edges)
