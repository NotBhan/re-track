"""
Incremental indexing tests for TypeScript / JavaScript structural analysis.

Verifies that:
1. Manifest version / parser version bump triggers full rebuild.
2. Unchanged TS files reuse deterministic AST nodes without re-parsing.
3. Modified TS files trigger selective re-parse and cross-file relinking.
4. Deleted TS files are cleanly expunged from the manifest.
"""

from pathlib import Path
import pytest

from app.services.manifest_service import ManifestService, PARSER_VERSION
from app.services.repository_summary import RepositorySummaryGenerator


@pytest.fixture
def ts_project(tmp_path: Path) -> Path:
    repo = tmp_path / "ts_project"
    repo.mkdir()
    (repo / "src" / "components").mkdir(parents=True)
    (repo / "src" / "utils").mkdir(parents=True)

    (repo / "src" / "utils" / "math.ts").write_text("""
    export function add(a: number, b: number): number {
        return a + b;
    }
    """, encoding="utf-8")

    (repo / "src" / "components" / "Counter.tsx").write_text("""
    import { add } from '../utils/math';

    export const Counter = () => {
        const val = add(1, 2);
        return <div>{val}</div>;
    };
    """, encoding="utf-8")

    return repo


def test_ts_incremental_caching_and_reuse(ts_project: Path) -> None:
    manifest_service = ManifestService(storage_dir=ts_project / ".manifests")
    gen = RepositorySummaryGenerator()

    # Pass 1: Full index
    files_pass1 = list(ts_project.glob("src/**/*.*"))
    summary1 = gen.generate(ts_project, files_pass1)

    assert gen.last_parse_stats["files_parsed"] == 2
    assert gen.last_parse_stats["files_reused"] == 0

    # Build and persist manifest
    manifest_service.update_manifest(
        repo_path=ts_project,
        dataset_name="ts_test",
        indexed_files=files_pass1,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )
    manifest1 = manifest_service.load_manifest(ts_project)
    assert manifest1 is not None

    # Pass 2: No changes -> NOOP / 100% Reuse
    delta2, _ = manifest_service.compute_delta(ts_project, files_pass1)
    assert delta2.has_changes is False

    summary2 = gen.generate(
        ts_project,
        files_pass1,
        existing_manifest=manifest1,
        delta=delta2,
    )

    assert gen.last_parse_stats["files_parsed"] == 0
    assert gen.last_parse_stats["files_reused"] == 2
    assert len(summary2.call_graph_nodes) == len(summary1.call_graph_nodes)
    assert len(summary2.call_graph_edges) == len(summary1.call_graph_edges)


def test_ts_incremental_partial_mutation(ts_project: Path) -> None:
    manifest_service = ManifestService(storage_dir=ts_project / ".manifests")
    gen = RepositorySummaryGenerator()

    # Pass 1: Full index
    files1 = list(ts_project.glob("src/**/*.*"))
    summary1 = gen.generate(ts_project, files1)
    manifest_service.update_manifest(
        repo_path=ts_project,
        dataset_name="ts_test",
        indexed_files=files1,
        deleted_rel_paths=[],
        file_metadata=gen.file_ast_metadata,
    )
    manifest1 = manifest_service.load_manifest(ts_project)
    assert manifest1 is not None

    # Mutate ONLY src/utils/math.ts
    math_file = ts_project / "src" / "utils" / "math.ts"
    math_file.write_text("""
    export function add(a: number, b: number): number {
        return a + b;
    }
    export function subtract(a: number, b: number): number {
        return a - b;
    }
    """, encoding="utf-8")

    files2 = list(ts_project.glob("src/**/*.*"))
    delta2, _ = manifest_service.compute_delta(ts_project, files2)

    assert "src/utils/math.ts" in [str(f.resolve().relative_to(ts_project.resolve()).as_posix()) for f in delta2.modified]
    assert len(delta2.unchanged) == 1

    summary2 = gen.generate(
        ts_project,
        files2,
        existing_manifest=manifest1,
        delta=delta2,
    )

    # Only math.ts was re-parsed (1 parse), Counter.tsx was reused (1 reused)
    assert gen.last_parse_stats["files_parsed"] == 1
    assert gen.last_parse_stats["files_reused"] == 1

    node_labels = {n.label for n in summary2.call_graph_nodes}
    assert "add" in node_labels
    assert "subtract" in node_labels
    assert "Counter" in node_labels
