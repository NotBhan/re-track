"""Integration and unit test suite for AST Call Graph end-to-end data flow.

Validates:
1. Domain serialization / deserialization (IndexedRepositoryRecord, RepositorySummaryInfo).
2. JsonRepositoryMetadataStore persistence across simulated process restarts.
3. Backward compatibility for legacy repository records lacking call graph fields.
4. End-to-end indexing -> metadata store -> GET /repositories & GET /repos AST graph data flow.
5. Invariant: Graph node/edge counts match exactly across all pipeline boundaries.
6. Mutation behavior: fresh index, NOOP re-index, file edit, file delete, and file rename.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.application.container import ApplicationContainer, reset_container, set_container
from app.application.domain.repository import (
    ArchitectureLayerRecord,
    ComponentRecord,
    IndexedRepositoryRecord,
)
from app.application.dto.indexing import (
    IndexRepositoryRequest,
    RepositorySummaryInfo,
)
from app.application.use_cases.indexing import IndexingUseCases
from app.application.use_cases.repositories import RepositoryUseCases
from app.models.repository import Repository
from app.server import app
from app.models.responses import IndexingProgress
from app.services.repository_metadata_store import JsonRepositoryMetadataStore
from app.services.repository_summary import RepositorySummaryGenerator


# =============================================================================
# 1. Backend Unit Tests: Serialization & Backward Compatibility
# =============================================================================

def test_indexed_repository_record_graph_serialization():
    """Verify IndexedRepositoryRecord serializes and deserializes call graph nodes and edges."""
    sample_nodes = [
        {"id": "mod.func_a", "label": "func_a", "file": "mod.py", "kind": "function", "line": 10},
        {"id": "mod.func_b", "label": "func_b", "file": "mod.py", "kind": "function", "line": 20},
    ]
    sample_edges = [
        {"source": "mod.func_a", "target": "mod.func_b", "kind": "calls"},
    ]

    record = IndexedRepositoryRecord(
        id="repo-1",
        name="test-repo",
        path="/path/to/test-repo",
        languages=["Python"],
        file_count=2,
        memory_size="8 KB",
        last_indexed="2026-09-05T00:00:00Z",
        purpose="Test Repository",
        call_graph_status="analyzed",
        call_graph_error=None,
        call_graph_nodes=sample_nodes,
        call_graph_edges=sample_edges,
    )

    data = record.to_dict()
    assert data["call_graph_status"] == "analyzed"
    assert data["call_graph_nodes"] == sample_nodes
    assert data["call_graph_edges"] == sample_edges

    reconstructed = IndexedRepositoryRecord.from_dict(data)
    assert reconstructed.id == "repo-1"
    assert reconstructed.call_graph_status == "analyzed"
    assert reconstructed.call_graph_nodes == sample_nodes
    assert reconstructed.call_graph_edges == sample_edges


def test_indexed_repository_record_empty_graph_preserved():
    """Empty list for call graph nodes/edges must be preserved as [] and not converted to None."""
    record = IndexedRepositoryRecord(
        id="repo-empty",
        name="empty-repo",
        path="/path/to/empty",
        call_graph_status="zero_edges",
        call_graph_nodes=[],
        call_graph_edges=[],
    )
    data = record.to_dict()
    assert data["call_graph_nodes"] == []
    assert data["call_graph_edges"] == []

    loaded = IndexedRepositoryRecord.from_dict(data)
    assert loaded.call_graph_nodes == []
    assert loaded.call_graph_edges == []


def test_legacy_repository_record_backward_compatibility():
    """Historical records saved without graph fields must load safely with truthful defaults."""
    legacy_json = {
        "id": "legacy-repo",
        "name": "historical",
        "path": "/path/to/legacy",
        "languages": ["Python"],
        "file_count": 5,
        "memory_size": "20 KB",
        "last_indexed": "2025-01-01T00:00:00Z",
        "purpose": "Legacy test",
    }
    record = IndexedRepositoryRecord.from_dict(legacy_json)
    assert record.id == "legacy-repo"
    assert record.call_graph_status == "not_analyzed"
    assert record.call_graph_error is None
    assert record.call_graph_nodes is None
    assert record.call_graph_edges is None


def test_repository_metadata_store_persistence_roundtrip(tmp_path: Path):
    """JsonRepositoryMetadataStore must preserve graph nodes and edges across disk reloads."""
    store_file = tmp_path / "indexed_repos.json"
    store = JsonRepositoryMetadataStore(store_path=store_file)

    nodes = [{"id": "a.py.run", "label": "run", "file": "a.py", "kind": "function", "line": 5}]
    edges = [{"source": "a.py.run", "target": "a.py.worker", "kind": "calls"}]

    rec = IndexedRepositoryRecord(
        id="1",
        name="persisted-repo",
        path=str(tmp_path / "persisted"),
        call_graph_status="analyzed",
        call_graph_nodes=nodes,
        call_graph_edges=edges,
    )
    store.upsert(rec)

    # Simulate process restart by instantiating new store pointing to same file
    new_store = JsonRepositoryMetadataStore(store_path=store_file)
    loaded = new_store.get_by_id("1")
    assert loaded is not None
    assert loaded.call_graph_status == "analyzed"
    assert loaded.call_graph_nodes == nodes
    assert loaded.call_graph_edges == edges


def test_repository_summary_info_dto():
    """RepositorySummaryInfo DTO must serialize graph fields."""
    dto = RepositorySummaryInfo(
        id="repo-dto",
        name="test",
        path="/test",
        languages=["Python"],
        file_count=1,
        memory_size="4 KB",
        last_indexed="2026-09-05T00:00:00Z",
        call_graph_status="analyzed",
        call_graph_error=None,
        call_graph_nodes=[{"id": "n1", "label": "n1", "file": "a.py", "kind": "function", "line": 1}],
        call_graph_edges=[{"source": "n1", "target": "n2", "kind": "calls"}],
    )
    dumped = dto.model_dump()
    assert dumped["call_graph_status"] == "analyzed"
    assert len(dumped["call_graph_nodes"]) == 1
    assert len(dumped["call_graph_edges"]) == 1


# =============================================================================
# 2. Integration & End-to-End Tests: A -> B -> C Call Graph Pipeline Flow
# =============================================================================

@pytest.mark.asyncio
async def test_end_to_end_ast_graph_pipeline(tmp_path: Path):
    """End-to-End scenario:

    1. Create repository with A -> B -> C call chain.
    2. Run AST generation and index_repository().
    3. Verify node/edge count before persistence, after persistence, and in get_repository_summaries().
    4. Verify GET /repositories API returns exact matching graph topology.
    5. Verify GET /repos API returns exact matching graph topology.
    """
    repo_root = tmp_path / "repo_abc"
    pkg = repo_root / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)

    # c.py: callee
    (pkg / "c.py").write_text("def func_c():\n    return 42\n")

    # b.py: caller of c
    (pkg / "b.py").write_text("from pkg.c import func_c\n\ndef func_b():\n    return func_c()\n")

    # a.py: caller of b
    (pkg / "a.py").write_text("from pkg.b import func_b\n\ndef func_a():\n    return func_b()\n")

    # 1. Direct AST extraction: authoritative ground truth
    summary_gen = RepositorySummaryGenerator()
    files = [pkg / "a.py", pkg / "b.py", pkg / "c.py"]
    ast_summary = summary_gen.generate(repo_root, files)

    raw_nodes = ast_summary.call_graph_nodes
    raw_edges = ast_summary.call_graph_edges
    assert len(raw_nodes) == 3, f"Expected 3 nodes (func_a, func_b, func_c), got {len(raw_nodes)}"
    assert len(raw_edges) >= 2, f"Expected at least 2 call edges, got {len(raw_edges)}"

    node_ids = {n.id for n in raw_nodes}
    assert any("func_a" in nid for nid in node_ids)
    assert any("func_b" in nid for nid in node_ids)
    assert any("func_c" in nid for nid in node_ids)

    # 2. Setup isolated container and metadata store
    store_file = tmp_path / "test_store.json"
    metadata_store = JsonRepositoryMetadataStore(store_path=store_file)

    mock_indexing_service = MagicMock()
    mock_indexing_service.last_summary = ast_summary
    mock_indexing_service.discover_files.return_value = files
    mock_indexing_service.filter_files.return_value = files
    mock_indexing_service.index_repository = AsyncMock(return_value=IndexingProgress(
        total_files=3,
        processed_files=3,
        failed_files=0,
        total_batches=1,
        current_batch=1,
    ))

    import asyncio
    indexing_uc = IndexingUseCases(
        indexing_service=mock_indexing_service,
        indexing_lock=asyncio.Lock(),
        ensure_services_fn=lambda: None,
        summary_generator=summary_gen,
        metadata_store=metadata_store,
        filesystem=MagicMock(),
        workspace_auth=MagicMock(),
    )

    # 3. Execute index_repository use case
    index_res = await indexing_uc.index_repository(IndexRepositoryRequest(
        repository_path=str(repo_root),
        dataset_name="repo_abc",
        force_reindex=True,
    ))
    assert index_res.success is True

    # 4. Verification boundary 1: Metadata store persistence
    persisted = metadata_store.get_by_path(str(repo_root))
    assert persisted is not None, "Repository record must exist in metadata store"
    assert persisted.call_graph_status == "analyzed"
    assert persisted.call_graph_nodes is not None
    assert persisted.call_graph_edges is not None
    assert len(persisted.call_graph_nodes) == len(raw_nodes)
    assert len(persisted.call_graph_edges) == len(raw_edges)

    # 5. Verification boundary 2: get_repository_summaries()
    summaries_res = await indexing_uc.get_repository_summaries()
    assert summaries_res.success is True
    assert len(summaries_res.repositories) == 1
    summary_dto = summaries_res.repositories[0]
    assert summary_dto.call_graph_status == "analyzed"
    assert summary_dto.call_graph_nodes is not None
    assert summary_dto.call_graph_edges is not None
    assert len(summary_dto.call_graph_nodes) == len(raw_nodes)
    assert len(summary_dto.call_graph_edges) == len(raw_edges)

    # 6. Verification boundary 3: FastAPI GET /repositories via TestClient
    container = ApplicationContainer()
    container.metadata_store = metadata_store
    container.indexing_service = mock_indexing_service
    set_container(container)

    try:
        client = TestClient(app)
        api_res = client.get("/repositories")
        assert api_res.status_code == 200
        body = api_res.json()
        assert body["success"] is True
        assert len(body["repositories"]) == 1
        repo_data = body["repositories"][0]

        # Invariant checks
        assert repo_data["call_graph_status"] == "analyzed"
        assert len(repo_data["call_graph_nodes"]) == len(raw_nodes)
        assert len(repo_data["call_graph_edges"]) == len(raw_edges)

        # Confirm A -> B -> C nodes and edges survived
        retrieved_ids = {n["id"] for n in repo_data["call_graph_nodes"]}
        assert retrieved_ids == node_ids

        retrieved_edge_pairs = {(e["source"], e["target"]) for e in repo_data["call_graph_edges"]}
        raw_edge_pairs = {(e.source, e.target) for e in raw_edges}
        assert retrieved_edge_pairs == raw_edge_pairs

        # 7. Verification boundary 4: GET /repos via TestClient
        # Register repo in manager so /repos returns it
        container.repository_manager._repositories[persisted.id] = {
            "id": persisted.id,
            "name": "repo_abc",
            "source_type": "local",
            "local_path": str(repo_root),
            "status": "indexed",
        }

        repos_res = client.get("/repos")
        assert repos_res.status_code == 200
        repos_body = repos_res.json()
        assert repos_body["success"] is True
        assert len(repos_body["repositories"]) >= 1
        target_repo = next(r for r in repos_body["repositories"] if r["id"] == persisted.id)
        assert target_repo["call_graph_status"] == "analyzed"
        assert len(target_repo["call_graph_nodes"]) == len(raw_nodes)
        assert len(target_repo["call_graph_edges"]) == len(raw_edges)

    finally:
        reset_container()


# =============================================================================
# 3. Mutation Behavior Tests: NOOP, Modification, Deletion, Rename
# =============================================================================

def test_mutation_behavior_ast_call_graph(tmp_path: Path):
    """Verify AST call graph behavior under code mutation:

    - Fresh indexing produces graph.
    - NOOP indexing preserves graph data.
    - File modification updates graph data.
    - File deletion removes affected nodes/edges.
    """
    repo_root = tmp_path / "repo_mutations"
    repo_root.mkdir()
    gen = RepositorySummaryGenerator()

    # Initial state: a.py calls b.py
    f_b = repo_root / "b.py"
    f_b.write_text("def helper(): pass\n")
    f_a = repo_root / "a.py"
    f_a.write_text("from b import helper\ndef main(): helper()\n")

    files = [f_a, f_b]
    s1 = gen.generate(repo_root, files)
    assert len(s1.call_graph_nodes) == 2
    assert len(s1.call_graph_edges) >= 1

    # NOOP: same files
    s_noop = gen.generate(repo_root, files)
    assert len(s_noop.call_graph_nodes) == len(s1.call_graph_nodes)
    assert len(s_noop.call_graph_edges) == len(s1.call_graph_edges)

    # Modification: add func2 to b.py
    f_b.write_text("def helper(): pass\ndef helper2(): pass\n")
    s_mod = gen.generate(repo_root, files)
    assert len(s_mod.call_graph_nodes) == 3
    assert any("helper2" in n.id for n in s_mod.call_graph_nodes)

    # Deletion: remove b.py
    f_b.unlink()
    s_del = gen.generate(repo_root, [f_a])
    del_node_ids = {n.id for n in s_del.call_graph_nodes}
    assert not any("helper" in nid for nid in del_node_ids)

    # Same-SHA rename: rename a.py -> entry.py
    f_entry = repo_root / "entry.py"
    f_entry.write_text(f_a.read_text())
    f_a.unlink()
    s_rename = gen.generate(repo_root, [f_entry])
    assert len(s_rename.call_graph_nodes) >= 1
    entry_node = next(n for n in s_rename.call_graph_nodes if n.label == "main")
    assert entry_node.file == "entry.py"
