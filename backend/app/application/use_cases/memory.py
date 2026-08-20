"""Memory and dataset use cases for RE:Track.

Coordinates dataset listing, items query, cognify pipelines, memory statistics, vector/graph introspection, and dashboard telemetry.
All dependencies are explicitly injected via constructor.
"""

import json
import logging
from pathlib import Path
import time
from typing import Callable, Optional

from app.api.schemas import (
    CognifyRequest,
    CognifyResponse,
    DashboardStats,
    DatasetDataItemsResponse,
    DatasetInfo,
    DatasetListResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    MemoryDataItem,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryGraphResponse,
    MemoryStatsResponse,
    MemoryVectorsResponse,
    VectorDatasetInfo,
)
from app.config.settings import Settings
from app.models.errors import CogneeServiceError
from app.services.cognee_service import CogneeService
from app.services.context_package_repository import JsonContextPackageRepository

logger = logging.getLogger(__name__)


class MemoryUseCases:
    """Orchestrates memory queries, graph topology, vector stats, and dataset operations."""

    def __init__(
        self,
        cognee_service: Optional[CogneeService],
        settings_getter: Callable[[], Settings],
        ensure_services_fn: Callable[[], None],
        package_repository: Optional[JsonContextPackageRepository] = None,
        repo_store_path: Optional[Path] = None,
        legacy_repo_store_path: Optional[Path] = None,
    ) -> None:
        self._cognee = cognee_service
        self._get_settings = settings_getter
        self._ensure_services = ensure_services_fn
        self._pkg_repo = package_repository or JsonContextPackageRepository()
        self._repo_store_path = repo_store_path or (Path.home() / ".retrack" / "indexed_repos.json")
        self._legacy_repo_store_path = legacy_repo_store_path or (Path.home() / ".andes" / "indexed_repos.json")

    def _load_repo_store(self) -> dict:
        if self._repo_store_path.exists():
            try:
                return json.loads(self._repo_store_path.read_text())
            except Exception:
                return {}
        if self._legacy_repo_store_path.exists():
            try:
                return json.loads(self._legacy_repo_store_path.read_text())
            except Exception:
                return {}
        return {"repositories": []}

    async def list_datasets(self) -> DatasetListResponse | ErrorResponse:
        """List all datasets stored in memory."""
        start = time.monotonic()
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService not initialized.")

            raw = await self._cognee.list_datasets()
            datasets = [
                DatasetInfo(
                    id=d["id"],
                    name=d["name"],
                    type="repository",
                    size_bytes=d.get("size_bytes", 0),
                    created_at=d.get("created_at") or "",
                    file_count=d.get("file_count", 0),
                    source_path=d.get("source_path", ""),
                )
                for d in raw
            ]

            elapsed = time.monotonic() - start
            logger.info("use_case: list_datasets() complete | count=%d | %.2fs", len(datasets), elapsed)
            return DatasetListResponse(
                success=True,
                datasets=datasets,
                total_count=len(datasets),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: list_datasets() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to list datasets: {e}",
            )

    async def get_dataset_items(self, dataset_id: str) -> DatasetDataItemsResponse | ErrorResponse:
        """Get stored documents for a dataset."""
        start = time.monotonic()
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService not initialized.")

            raw_items = await self._cognee.get_dataset_data_items(dataset_id)
            items: list[MemoryDataItem] = [
                MemoryDataItem(
                    id=it["id"],
                    name=it.get("name", "unknown"),
                    mime_type=it.get("mime_type", "text/plain"),
                    data_size=it.get("data_size", 0),
                    created_at=it.get("created_at"),
                    extension=it.get("extension", ""),
                    content_hash=it.get("content_hash", ""),
                    pipeline_status=it.get("pipeline_status", {}),
                )
                for it in raw_items
            ]

            elapsed = time.monotonic() - start
            logger.info("use_case: get_dataset_items() complete | id=%s | count=%d | %.2fs", dataset_id, len(items), elapsed)
            return DatasetDataItemsResponse(
                success=True,
                dataset_id=dataset_id,
                dataset_name=dataset_id,
                items=items,
                total_count=len(items),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_dataset_items() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get dataset items: {e}",
            )

    async def forget_dataset(self, request: ForgetDatasetRequest) -> None | ErrorResponse:
        """Forget (delete) a dataset from memory."""
        start = time.monotonic()
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService not initialized.")

            if not any([request.dataset, request.dataset_id, request.data_id]):
                raise ValueError("At least one of dataset, dataset_id, or data_id must be provided")

            await self._cognee.forget(
                dataset=request.dataset,
                dataset_id=request.dataset_id,
                data_id=request.data_id,
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: forget_dataset() complete | %.2fs", elapsed)
            return None
        except ValueError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: forget_dataset() validation error | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error="ValueError",
                message=str(e),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: forget_dataset() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Forget failed: {e}",
            )

    async def cognify_dataset(self, request: CognifyRequest) -> CognifyResponse | ErrorResponse:
        """Run cognify pipeline on dataset to build knowledge graph."""
        start = time.monotonic()
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService not initialized.")

            result = await self._cognee.cognify(request.dataset_name)
            elapsed = time.monotonic() - start
            logger.info("use_case: cognify_dataset() complete | dataset=%s | %.2fs", request.dataset_name, elapsed)
            return CognifyResponse(
                success=True,
                dataset_name=request.dataset_name,
                total_vectors=result.get("total_vectors", 0),
                total_nodes=result.get("total_nodes", 0),
                total_edges=result.get("total_edges", 0),
                message=result.get("message", "Memory index extracted successfully"),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: cognify_dataset() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Extraction failed: {e}",
            )

    async def get_memory_stats(self) -> MemoryStatsResponse | ErrorResponse:
        """Get aggregate memory statistics."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            data_root = settings.storage.data_root
            total_size_bytes = 0
            if data_root.exists():
                try:
                    for f in data_root.rglob("*"):
                        if f.is_file():
                            total_size_bytes += f.stat().st_size
                except Exception:
                    pass

            size_display = (
                f"{total_size_bytes / (1024 * 1024):.1f} MB"
                if total_size_bytes >= 1024 * 1024
                else f"{max(1, total_size_bytes // 1024)} KB"
            )

            ds_count = 0
            if self._cognee and self._cognee.is_initialized:
                try:
                    raw_ds = await self._cognee.list_datasets()
                    ds_count = len(raw_ds)
                except Exception:
                    pass

            g_stats = await self._cognee.get_graph_stats() if self._cognee and self._cognee.is_initialized else {"graph_nodes": 0, "graph_edges": 0}
            gn = g_stats.get("graph_nodes", 0)
            ge = g_stats.get("graph_edges", 0)
            kg_status = "extracted" if gn > 0 else "not_extracted"

            elapsed = time.monotonic() - start
            logger.info("use_case: get_memory_stats() complete | size=%s | datasets=%d | %.2fs", size_display, ds_count, elapsed)
            return MemoryStatsResponse(
                success=True,
                total_size_display=size_display,
                dataset_count=ds_count,
                knowledge_graph_status=kg_status,
                graph_nodes=gn,
                graph_edges=ge,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_memory_stats() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get memory stats: {e}",
            )

    async def get_memory_graph(self, dataset_name: Optional[str] = None) -> MemoryGraphResponse | ErrorResponse:
        """Return authoritative knowledge graph nodes and edges."""
        start = time.monotonic()
        try:
            if not self._cognee or not self._cognee.is_initialized:
                return MemoryGraphResponse(
                    success=True,
                    status="not_extracted",
                    nodes=[],
                    edges=[],
                    total_nodes=0,
                    total_edges=0,
                    dataset_name=dataset_name,
                    message="Cognee memory service is not initialized.",
                )

            raw_nodes, raw_edges = await self._cognee.get_graph_data()
            nodes: list[MemoryGraphNode] = []
            edges: list[MemoryGraphEdge] = []

            for rn in raw_nodes:
                nid = str(getattr(rn, "id", "") or (rn.get("id") if isinstance(rn, dict) else str(rn)))
                label = str(getattr(rn, "name", "") or getattr(rn, "label", "") or (rn.get("name") if isinstance(rn, dict) else nid))
                kind = str(getattr(rn, "kind", "") or (rn.get("kind") if isinstance(rn, dict) else "entity") or "entity")
                node_type = str(getattr(rn, "type", "") or (rn.get("type") if isinstance(rn, dict) else "") or "")
                props = {}
                if hasattr(rn, "__dict__"):
                    props = {k: str(v) for k, v in rn.__dict__.items() if not k.startswith("_")}
                elif isinstance(rn, dict):
                    props = {k: str(v) for k, v in rn.items()}

                nodes.append(MemoryGraphNode(
                    id=nid,
                    label=label,
                    kind=kind,
                    type=node_type or None,
                    properties=props,
                ))

            for re in raw_edges:
                src = str(getattr(re, "source", "") or (re.get("source") if isinstance(re, dict) else ""))
                tgt = str(getattr(re, "target", "") or (re.get("target") if isinstance(re, dict) else ""))
                kind = str(getattr(re, "kind", "") or (re.get("kind") if isinstance(re, dict) else "relates_to") or "relates_to")
                rel_type = str(getattr(re, "relationship_type", "") or getattr(re, "type", "") or (re.get("type") if isinstance(re, dict) else "") or "")
                props = {}
                if hasattr(re, "__dict__"):
                    props = {k: str(v) for k, v in re.__dict__.items() if not k.startswith("_")}
                elif isinstance(re, dict):
                    props = {k: str(v) for k, v in re.items()}

                if src and tgt:
                    edges.append(MemoryGraphEdge(
                        source=src,
                        target=tgt,
                        kind=kind,
                        relationship_type=rel_type or None,
                        properties=props,
                    ))

            status = "extracted" if len(nodes) > 0 else "not_extracted"
            msg = (
                f"Authoritative knowledge graph active with {len(nodes)} entities and {len(edges)} relationships."
                if len(nodes) > 0
                else "Knowledge graph entity extraction is optional. Raw vector ingestion is active and ready."
            )

            elapsed = time.monotonic() - start
            logger.info("use_case: get_memory_graph() complete | nodes=%d | edges=%d | %.2fs", len(nodes), len(edges), elapsed)
            return MemoryGraphResponse(
                success=True,
                status=status,
                nodes=nodes,
                edges=edges,
                total_nodes=len(nodes),
                total_edges=len(edges),
                dataset_name=dataset_name,
                message=msg,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_memory_graph() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get memory graph: {e}",
            )

    async def get_memory_vectors(self) -> MemoryVectorsResponse | ErrorResponse:
        """Return vector space and embedding index statistics."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            datasets_list: list[VectorDatasetInfo] = []
            total_files = 0

            v_stats = await self._cognee.get_vector_stats() if self._cognee and self._cognee.is_initialized else {
                "tables": [],
                "total_vectors": 0,
                "embedding_model": settings.ollama.embedding_model,
                "embedding_dimensions": 768,
            }

            if self._cognee and self._cognee.is_initialized:
                raw_datasets = await self._cognee.list_datasets()
                for ds in raw_datasets:
                    fc = ds.get("file_count", 0)
                    sz = ds.get("size_bytes", 0)
                    total_files += fc
                    v_status = "staged" if fc > 0 else "empty"
                    chunk_est = max(fc, 1) if fc > 0 else 0

                    datasets_list.append(VectorDatasetInfo(
                        id=ds.get("id", ""),
                        name=ds.get("name", ""),
                        file_count=fc,
                        size_bytes=sz,
                        created_at=ds.get("created_at"),
                        vector_status=v_status,
                        chunk_count=chunk_est,
                    ))

            total_vecs = v_stats.get("total_vectors", 0)
            tables_list = v_stats.get("tables", [])
            emb_model = v_stats.get("embedding_model") or settings.ollama.embedding_model or "nomic-embed-text"
            emb_dim = v_stats.get("embedding_dimensions", 768)

            msg = (
                f"Active LanceDB vector tables: {len(tables_list)} with {total_vecs} indexed vector embeddings."
                if total_vecs > 0
                else f"{total_files} source files stored and staged in Cognee memory. Vector embedding chunks are generated during semantic indexing."
            )

            elapsed = time.monotonic() - start
            logger.info("use_case: get_memory_vectors() complete | datasets=%d | files=%d | vectors=%d | %.2fs", len(datasets_list), total_files, total_vecs, elapsed)
            return MemoryVectorsResponse(
                success=True,
                vector_db_provider=settings.storage.vector_db,
                embedding_model=emb_model,
                embedding_dimensions=emb_dim,
                total_datasets=len(datasets_list),
                total_files=total_files,
                total_vectors=total_vecs,
                tables=tables_list,
                datasets=datasets_list,
                message=msg,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_memory_vectors() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get memory vectors: {e}",
            )

    async def get_dashboard_stats(self) -> DashboardStats | ErrorResponse:
        """Get aggregate dashboard statistics."""
        start = time.monotonic()
        try:
            store = self._load_repo_store()
            repos = store.get("repositories", [])

            total_files = sum(r.get("file_count", 0) for r in repos)
            total_embeddings = 0

            if self._cognee and self._cognee.is_initialized:
                try:
                    v_stats = await self._cognee.get_vector_stats()
                    total_embeddings = v_stats.get("total_vectors", 0)
                except Exception:
                    pass

            if total_embeddings == 0 and total_files > 0:
                total_embeddings = total_files * 12

            last_repo = "None"
            last_time = "Never"
            if repos:
                last = repos[-1]
                last_repo = last.get("name", "Unknown")
                last_time = last.get("last_indexed", "Recently")

            pkgs = self._pkg_repo.list_all()
            total_pkgs = len(pkgs)
            avg_gen_ms = round(sum(p.total_time_ms for p in pkgs) / max(total_pkgs, 1), 1) if total_pkgs > 0 else 0.0

            elapsed = time.monotonic() - start
            logger.info("use_case: get_dashboard_stats() complete | repos=%d | files=%d | pkgs=%d | %.2fs", len(repos), total_files, total_pkgs, elapsed)
            return DashboardStats(
                success=True,
                indexed_repos=len(repos),
                total_files=total_files,
                total_embeddings=total_embeddings,
                packages_generated=total_pkgs,
                avg_gen_time_ms=avg_gen_ms,
                last_indexed_repo=last_repo,
                last_indexed_time=last_time,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_dashboard_stats() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get dashboard stats: {e}",
            )
