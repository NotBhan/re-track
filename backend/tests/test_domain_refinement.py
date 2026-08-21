"""Phase 5 domain model refinement and memory capability port tests for RE:Track.

Verifies:
1. ArchitectureLayerRecord, ComponentRecord, and IndexedRepositoryRecord typing and backward compatibility.
2. ParsedIntentRecord and pure parse_intent_heuristics extraction behavior.
3. Memory capability protocol segregation (Lifecycle, Ingestion, Retrieval, Dataset, Topology).
4. Typed memory domain records (Dataset, DataItem, GraphNode, GraphEdge, Graph, VectorStats).
5. Narrow port substitution in use cases (SystemUseCases with MemoryLifecyclePort, RepositoryUseCases with MemoryDatasetPort).
6. MemoryUseCases polymorphic handling of typed domain records and legacy dictionaries.
7. AST static verification ensuring domain and port purity.
"""

import ast
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.application.domain.intent import ParsedIntentRecord, parse_intent_heuristics
from app.application.domain.memory import (
    MemoryDataItemRecord,
    MemoryDatasetRecord,
    MemoryGraphEdgeRecord,
    MemoryGraphNodeRecord,
    MemoryGraphRecord,
    MemoryVectorStatsRecord,
)
from app.application.domain.repository import (
    ArchitectureLayerRecord,
    ComponentRecord,
    IndexedRepositoryRecord,
)
from app.application.ports.intent_parser import IntentParserPort
from app.application.ports.memory import (
    MemoryDatasetPort,
    MemoryIngestionPort,
    MemoryLifecyclePort,
    MemoryPort,
    MemoryRetrievalPort,
    MemoryTopologyPort,
)
from app.application.use_cases.memory import MemoryUseCases
from app.application.use_cases.repositories import RepositoryUseCases
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings
from app.models.repository import Repository


# --- 1. DEBT-006: Repository Domain Entities Tests ---


class TestRepositoryDomainEntities:
    def test_architecture_layer_record_from_dict_and_str(self):
        # From dict
        layer1 = ArchitectureLayerRecord.from_dict({"icon": "Server", "label": "API Gateway"})
        assert layer1.icon == "Server"
        assert layer1.label == "API Gateway"
        assert layer1.to_dict() == {"icon": "Server", "label": "API Gateway"}

        # From scalar string
        layer2 = ArchitectureLayerRecord.from_dict("Modular Monolith")
        assert layer2.icon == "Layers"
        assert layer2.label == "Modular Monolith"

        # From None
        layer3 = ArchitectureLayerRecord.from_dict(None)
        assert layer3.icon == "Layers"
        assert layer3.label == ""

    def test_component_record_from_dict_and_str(self):
        # From dict
        comp1 = ComponentRecord.from_dict({"path": "app/core", "centrality": "core"})
        assert comp1.path == "app/core"
        assert comp1.centrality == "core"
        assert comp1.to_dict() == {"path": "app/core", "centrality": "core"}

        # From scalar string
        comp2 = ComponentRecord.from_dict("services/auth.py")
        assert comp2.path == "services/auth.py"
        assert comp2.centrality == "core"

        # From None
        comp3 = ComponentRecord.from_dict(None)
        assert comp3.path == ""
        assert comp3.centrality == "core"

    def test_indexed_repository_record_roundtrip_with_typed_substructures(self):
        rec = IndexedRepositoryRecord(
            id="repo-1",
            name="re-track",
            path="/path/to/re-track",
            languages=["Python", "TypeScript"],
            file_count=50,
            memory_size="200 KB",
            last_indexed="2026-08-21T00:00:00Z",
            purpose="Repository intelligence",
            architecture=[
                ArchitectureLayerRecord(icon="Layers", label="Hexagonal Architecture"),
                ArchitectureLayerRecord(icon="Cpu", label="Domain Core"),
            ],
            components=[
                ComponentRecord(path="app/domain", centrality="core"),
                ComponentRecord(path="app/ports", centrality="core"),
            ],
            call_graph_status="ready",
            call_graph_error=None,
            call_graph_nodes=[{"id": "node1"}],
            call_graph_edges=[{"from": "node1", "to": "node2"}],
        )

        d = rec.to_dict()
        assert d["id"] == "repo-1"
        assert d["architecture"] == [
            {"icon": "Layers", "label": "Hexagonal Architecture"},
            {"icon": "Cpu", "label": "Domain Core"},
        ]
        assert d["components"] == [
            {"path": "app/domain", "centrality": "core"},
            {"path": "app/ports", "centrality": "core"},
        ]

        rec2 = IndexedRepositoryRecord.from_dict(d)
        assert rec2.id == rec.id
        assert len(rec2.architecture) == 2
        assert isinstance(rec2.architecture[0], ArchitectureLayerRecord)
        assert rec2.architecture[0].label == "Hexagonal Architecture"
        assert len(rec2.components) == 2
        assert isinstance(rec2.components[0], ComponentRecord)
        assert rec2.components[0].path == "app/domain"

    def test_indexed_repository_record_legacy_compatibility(self):
        # Legacy JSON with string items in architecture and missing components
        legacy_data = {
            "id": "legacy-repo",
            "name": "old-project",
            "path": "/old/path",
            "architecture": ["MVC", "REST API"],
            "extra_custom_field": "legacy-value",
        }

        rec = IndexedRepositoryRecord.from_dict(legacy_data)
        assert rec.id == "legacy-repo"
        assert len(rec.architecture) == 2
        assert rec.architecture[0].label == "MVC"
        assert rec.architecture[0].icon == "Layers"
        assert rec.components == []
        assert rec.extra_metadata.get("extra_custom_field") == "legacy-value"

        # Ensure reserialization produces clean dictionary format
        d = rec.to_dict()
        assert d["id"] == "legacy-repo"
        assert d["architecture"] == [
            {"icon": "Layers", "label": "MVC"},
            {"icon": "Layers", "label": "REST API"},
        ]
        assert d["extra_custom_field"] == "legacy-value"


# --- 2. DEBT-007: Intent Domain & Heuristic Extraction Tests ---


class TestIntentDomainAndHeuristics:
    def test_parse_intent_heuristics_categories(self):
        fix_intent = parse_intent_heuristics("Fix the race condition in indexing lock")
        assert fix_intent.category == "bug_fix"
        assert fix_intent.is_vague is False

        feat_intent = parse_intent_heuristics("Add new capability ports for memory decomposition")
        assert feat_intent.category == "feature_addition"

        refactor_intent = parse_intent_heuristics("Refactor memory use cases to depend on narrow ports")
        assert refactor_intent.category == "refactoring"

        explain_intent = parse_intent_heuristics("How does the dual storage resolution fallback work?")
        assert explain_intent.category == "explanation"

    def test_parse_intent_heuristics_symbol_and_file_extraction(self):
        prompt = "Fix bug in `MemoryLifecyclePort` inside `backend/app/application/ports/memory.py`"
        intent = parse_intent_heuristics(prompt)

        assert "MemoryLifecyclePort" in intent.extracted_symbols
        assert any("memory.py" in f for f in intent.relevant_file_hints)

    def test_parse_intent_heuristics_determinism_and_side_effects(self):
        prompt = "Investigate error in ContextPackageRepository"
        res1 = parse_intent_heuristics(prompt)
        res2 = parse_intent_heuristics(prompt)

        assert res1 == res2
        assert res1.to_dict() == res2.to_dict()

    def test_parse_intent_heuristics_empty_or_vague(self):
        empty_intent = parse_intent_heuristics("")
        assert empty_intent.task_summary == ""
        assert empty_intent.is_vague is True

        vague_intent = parse_intent_heuristics("help me")
        assert vague_intent.is_vague is True

    def test_intent_parser_port_protocol_purity(self):
        # Protocol must have parse_intent and must NOT have rule_based_fallback
        assert hasattr(IntentParserPort, "parse_intent")
        assert not hasattr(IntentParserPort, "rule_based_fallback")


# --- 3. DEBT-005: Memory Domain Records & Port Segregation Tests ---


class TestMemoryDomainAndCapabilityPorts:
    def test_memory_domain_records_roundtrip(self):
        ds = MemoryDatasetRecord(
            id="ds-1",
            name="re-track",
            size_bytes=1024,
            created_at="2026-08-21T10:00:00Z",
            file_count=12,
        )
        assert ds.to_dict()["id"] == "ds-1"
        assert MemoryDatasetRecord.from_dict(ds.to_dict()).name == "re-track"

        item = MemoryDataItemRecord(
            id="item-1",
            name="main.py",
            data_size=512,
            extension=".py",
        )
        assert item.to_dict()["id"] == "item-1"
        assert MemoryDataItemRecord.from_dict(item.to_dict()).extension == ".py"

        graph = MemoryGraphRecord(
            nodes=[MemoryGraphNodeRecord(id="n1", label="User", kind="entity")],
            edges=[MemoryGraphEdgeRecord(source="n1", target="n2", kind="relates_to")],
        )
        assert len(graph.to_dict()["nodes"]) == 1
        graph2 = MemoryGraphRecord.from_dict(graph.to_dict())
        assert len(graph2.nodes) == 1
        assert graph2.nodes[0].label == "User"

        v_stats = MemoryVectorStatsRecord(
            tables=["default_vectors"],
            total_vectors=42,
            embedding_model="nomic-embed-text",
            embedding_dimensions=768,
        )
        assert v_stats.to_dict()["total_vectors"] == 42
        assert MemoryVectorStatsRecord.from_dict(v_stats.to_dict()).embedding_model == "nomic-embed-text"

    @pytest.mark.asyncio
    async def test_system_use_cases_with_memory_lifecycle_port_only(self, tmp_path):
        """Verify SystemUseCases works when injected only with MemoryLifecyclePort."""
        class FakeLifecycleAdapter:
            @property
            def is_initialized(self) -> bool:
                return True

            async def initialize(self) -> None:
                pass

        settings = Settings(settings_store_path=tmp_path / "settings.json")
        lifecycle_adapter: MemoryLifecyclePort = FakeLifecycleAdapter()
        mock_provider = AsyncMock()
        mock_provider.check_health.return_value = MagicMock(is_reachable=True, active_model="phi4-mini")

        use_case = SystemUseCases(
            settings_getter=lambda: settings,
            cognee_service_getter=lambda: lifecycle_adapter,
            llm_provider_getter=lambda: mock_provider,
            provider_updater_fn=AsyncMock(return_value={"success": True}),
        )

        health = await use_case.health()
        assert health.status == "ok"
        assert health.cognee_initialized is True

    @pytest.mark.asyncio
    async def test_repository_use_cases_with_memory_dataset_port_only(self):
        """Verify RepositoryUseCases works when injected only with MemoryDatasetPort."""
        class FakeDatasetAdapter:
            def __init__(self):
                self.forgotten = []

            @property
            def is_initialized(self) -> bool:
                return True

            async def list_datasets(self):
                return []

            async def get_dataset_data(self, dataset_id: str):
                return []

            async def forget(self, dataset=None, dataset_id=None, data_id=None, **kwargs):
                self.forgotten.append(dataset)

            async def forget_data_item(self, data_id: str):
                pass

        dataset_adapter: MemoryDatasetPort = FakeDatasetAdapter()
        mock_manager = MagicMock()
        mock_repo = Repository(id="repo-1", name="my-repo", source_type="local", local_path="/path/to/repo")
        mock_manager.get.return_value = mock_repo
        mock_manager.delete.return_value = True

        mock_meta_store = MagicMock()

        use_case = RepositoryUseCases(
            repository_manager=mock_manager,
            indexing_service=None,
            llm_provider=None,
            summary_generator=MagicMock(),
            cognee_service=dataset_adapter,
            metadata_store=mock_meta_store,
        )

        res = await use_case.delete_repository("repo-1")
        assert res is not None
        assert "my-repo" in dataset_adapter.forgotten

    @pytest.mark.asyncio
    async def test_memory_use_cases_polymorphic_responses(self, tmp_path):
        """Verify MemoryUseCases seamlessly handles typed domain records."""
        class FakeTypedMemoryAdapter:
            @property
            def is_initialized(self) -> bool:
                return True

            async def initialize(self) -> None:
                pass

            async def list_datasets(self):
                return [
                    MemoryDatasetRecord(id="ds-1", name="re-track", file_count=5, size_bytes=1000)
                ]

            async def get_dataset_data(self, dataset_id: str):
                return [
                    MemoryDataItemRecord(id="item-1", name="main.py", data_size=200)
                ]

            async def get_graph(self, dataset_name=None):
                return MemoryGraphRecord(
                    nodes=[MemoryGraphNodeRecord(id="n1", label="Core")],
                    edges=[MemoryGraphEdgeRecord(source="n1", target="n2")],
                )

            async def get_vectors(self):
                return MemoryVectorStatsRecord(
                    tables=["re-track-vecs"],
                    total_vectors=15,
                )

            async def forget(self, **kwargs):
                pass

            async def forget_data_item(self, data_id: str):
                pass

            async def cognify(self, dataset_name=None):
                pass

            async def get_stats(self):
                return {}

            async def add(self, data, dataset_name="default", **kwargs):
                pass

            async def remember(self, data, dataset_name="default", **kwargs):
                pass

            async def recall(self, query_text, datasets, top_k=15, **kwargs):
                pass

        typed_adapter: MemoryPort = FakeTypedMemoryAdapter()
        settings = Settings(settings_store_path=tmp_path / "settings.json")

        use_case = MemoryUseCases(
            cognee_service=typed_adapter,
            settings_getter=lambda: settings,
            ensure_services_fn=lambda: None,
        )

        # 1. list_datasets
        ds_res = await use_case.list_datasets()
        assert ds_res.success is True
        assert ds_res.total_count == 1
        assert ds_res.datasets[0].name == "re-track"
        assert ds_res.datasets[0].file_count == 5

        # 2. get_dataset_items
        items_res = await use_case.get_dataset_items("ds-1")
        assert items_res.success is True
        assert len(items_res.items) == 1
        assert items_res.items[0].name == "main.py"

        # 3. get_memory_graph
        graph_res = await use_case.get_memory_graph()
        assert graph_res.success is True
        assert graph_res.total_nodes == 1
        assert graph_res.total_edges == 1

        # 4. get_memory_vectors
        vec_res = await use_case.get_memory_vectors()
        assert vec_res.success is True
        assert vec_res.total_vectors == 15


# --- 4. AST Architectural Invariant Tests ---


class TestDomainAndPortsASTPurity:
    def test_domain_directory_ast_purity(self):
        """Verify no file under app/application/domain imports from app.services, cognee, or web frameworks."""
        domain_dir = Path(__file__).resolve().parent.parent / "app" / "application" / "domain"
        forbidden = {"app.services", "cognee", "fastapi", "starlette", "uvicorn", "kuzu", "lancedb"}

        for py_file in domain_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for f in forbidden:
                            assert not alias.name.startswith(f), f"Domain violation in {py_file.name}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for f in forbidden:
                        assert not mod.startswith(f), f"Domain violation in {py_file.name}: from {mod} import ..."

    def test_ports_directory_ast_purity(self):
        """Verify no file under app/application/ports imports concrete services or frameworks."""
        ports_dir = Path(__file__).resolve().parent.parent / "app" / "application" / "ports"
        forbidden = {"app.services", "cognee", "fastapi", "starlette", "uvicorn", "kuzu", "lancedb"}

        for py_file in ports_dir.glob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for f in forbidden:
                            assert not alias.name.startswith(f), f"Port violation in {py_file.name}: imports {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for f in forbidden:
                        assert not mod.startswith(f), f"Port violation in {py_file.name}: from {mod} import ..."
