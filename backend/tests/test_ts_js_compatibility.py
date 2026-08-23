"""
Polyglot compatibility tests for Python AST and TypeScript Tree-sitter analyzers.

Verifies that Python AST analysis and TypeScript Tree-sitter analysis coexist
in the same repository without interfering with node IDs, edge schemas, or manifest records.
"""

from pathlib import Path
import pytest

from app.services.manifest_service import ManifestService
from app.services.repository_summary import RepositorySummaryGenerator


def test_polyglot_python_and_typescript_coexistence(tmp_path: Path) -> None:
    repo = tmp_path / "polyglot_repo"
    repo.mkdir()
    (repo / "backend" / "app").mkdir(parents=True)
    (repo / "frontend" / "src").mkdir(parents=True)

    # Python backend
    py_file = repo / "backend" / "app" / "main.py"
    py_file.write_text("""
def process_data(payload: dict) -> bool:
    return True

class ServerApp:
    def start(self):
        process_data({})
""", encoding="utf-8")

    # TypeScript frontend
    ts_file = repo / "frontend" / "src" / "api.ts"
    ts_file.write_text("""
export interface ApiResponse {
    success: boolean;
}

export async function fetchStatus(): Promise<ApiResponse> {
    return { success: true };
}
""", encoding="utf-8")

    files = [py_file, ts_file]
    gen = RepositorySummaryGenerator()
    summary = gen.generate(repo, files)

    assert len(summary.call_graph_nodes) >= 4

    nodes_by_id = {n.id: n for n in summary.call_graph_nodes}
    # Python nodes present (module dot notation)
    assert "backend.app.main.process_data" in nodes_by_id
    assert "backend.app.main.ServerApp" in nodes_by_id

    # TypeScript nodes present (path#symbol notation)
    assert "frontend/src/api.ts#ApiResponse" in nodes_by_id
    assert "frontend/src/api.ts#fetchStatus" in nodes_by_id

    # Manifest serialization
    manifest_service = ManifestService(storage_dir=repo / ".manifests")
    manifest_service.update_manifest(
        repo_path=repo,
        dataset_name="polyglot_test",
        indexed_files=files,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )
    manifest = manifest_service.load_manifest(repo)
    assert manifest is not None

    assert "backend/app/main.py" in manifest.files
    assert "frontend/src/api.ts" in manifest.files
    assert manifest.files["backend/app/main.py"].ast_nodes
    assert manifest.files["frontend/src/api.ts"].ast_nodes
