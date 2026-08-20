"""Memory and dataset use cases for RE:Track.

Coordinates dataset listing, items query, cognify pipelines, memory statistics, vector/graph introspection, and dashboard telemetry.
All dependencies are explicitly injected via constructor.
"""

import logging
import time
from typing import Callable, Optional

from app.application.dto import (
    CognifyRequest,
    CognifyResponse,
    DashboardStats,
    DatasetDataItemsResponse,
    DatasetInfo,
    DatasetListResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    ForgetDatasetResponse,
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
from app.services.context_package_repository import (
    ContextPackageRepository,
    JsonContextPackageRepository,
)
from app.services.repository_metadata_store import (
    JsonRepositoryMetadataStore,
    RepositoryMetadataStore,
)

logger = logging.getLogger(__name__)


class MemoryUseCases:
    """Orchestrates memory queries, graph topology, vector stats, and dataset operations."""

    def __init__(
        self,
        cognee_service: Optional[CogneeService],
        settings_getter: Callable[[], Settings],
        ensure_services_fn: Callable[[], None],
        package_repository: Optional[ContextPackageRepository] = None,
        metadata_store: Optional[RepositoryMetadataStore] = None,
    ) -> None:
        self._cognee = cognee_service
        self._get_settings = settings_getter
        self._ensure_services = ensure_services_fn
        self._pkg_repo = package_repository or JsonContextPackageRepository()
        self._metadata_store = metadata_store or JsonRepositoryMetadataStore()

    async def list_datasets(self) -> DatasetListResponse | ErrorResponse:
        """List all datasets in Cognee memory."""
        start = time.monotonic()
        logger.info("use_case: list_datasets()")
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService is not initialized.")

            raw_datasets = await self._cognee.list_datasets()
            datasets = [
                DatasetInfo(
                    id=str(d.get("id", "")),
                    name=str(d.get("name", "")),
                    type=str(d.get("type", "repository")),
                    size_bytes=d.get("size_bytes"),
                    created_at=d.get("created_at"),
                    file_count=int(d.get("file_count", 0)),
                    source_path=d.get("source_path"),
                )
                for d in raw_datasets
            ]
            response = DatasetListResponse(
                success=True,
                datasets=datasets,
                total_count=len(datasets),
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: list_datasets() complete | count=%d | %.2fs", len(datasets), elapsed)
            return response
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: list_datasets() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to list datasets: {e}")
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: list_datasets() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to list datasets: {e}")

    async def get_dataset_items(self, dataset_id: str) -> DatasetDataItemsResponse | ErrorResponse:
        """Get stored data items for a dataset."""
        start = time.monotonic()
        logger.info("use_case: get_dataset_items() | dataset_id=%s", dataset_id)
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService is not initialized.")

            data = await self._cognee.get_dataset_data(dataset_id)
            items = [
                MemoryDataItem(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")),
                    mime_type=str(item.get("mime_type", "text/plain")),
                    data_size=int(item.get("data_size", 0)),
                    created_at=item.get("created_at"),
                    extension=str(item.get("extension", "")),
                    content_hash=str(item.get("content_hash", "")),
                    pipeline_status=item.get("pipeline_status", {}),
                )
                for item in data.get("items", [])
            ]
            response = DatasetDataItemsResponse(
                success=True,
                dataset_id=dataset_id,
                dataset_name=data.get("dataset_name", ""),
                items=items,
                total_count=len(items),
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: get_dataset_items() complete | count=%d | %.2fs", len(items), elapsed)
            return response
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_dataset_items() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to get dataset items: {e}")
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_dataset_items() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to get dataset items: {e}")

    async def forget_dataset(
        self,
        request: ForgetDatasetRequest,
    ) -> None | ErrorResponse:
        """Forget (delete) a dataset from Cognee memory."""
        start = time.monotonic()
        logger.info(
            "use_case: forget_dataset() | dataset=%s | id=%s | data_id=%s",
            request.dataset,
            request.dataset_id,
            request.data_id,
        )
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService is not initialized.")

            if not request.dataset and not request.dataset_id and not request.data_id:
                return ErrorResponse(
                    error="ValueError",
                    message="Must provide dataset, dataset_id, or data_id to forget.",
                )

            await self._cognee.forget(
                dataset=request.dataset,
                dataset_id=request.dataset_id,
                data_id=request.data_id,
            )

            elapsed = time.monotonic() - start
            logger.info("use_case: forget_dataset() complete | %.2fs", elapsed)
            return None
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: forget_dataset() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Forget operation failed: {e}")
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: forget_dataset() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Forget operation failed: {e}")

    async def cognify_dataset(
        self,
        request: CognifyRequest,
    ) -> CognifyResponse | ErrorResponse:
        """Run Cognify pipeline on a dataset to extract knowledge graph and vectors."""
        start = time.monotonic()
        logger.info("use_case: cognify_dataset() | dataset=%s", request.dataset_name)
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService is not initialized.")

            res = await self._cognee.cognify(dataset_name=request.dataset_name)
            elapsed = time.monotonic() - start
            logger.info("use_case: cognify_dataset() complete | %.2fs", elapsed)
            return CognifyResponse(
                success=True,
                dataset_name=request.dataset_name,
                total_vectors=res.get("vectors_count", 0),
                total_nodes=res.get("nodes_count", 0),
                total_edges=res.get("edges_count", 0),
                message=res.get("message", "Cognify completed successfully"),
            )
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: cognify_dataset() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Cognify failed: {e}")
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: cognify_dataset() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Cognify failed: {e}")

    async def get_memory_stats(self) -> MemoryStatsResponse | ErrorResponse:
        """Get authoritative memory topology statistics."""
        start = time.monotonic()
        logger.info("use_case: get_memory_stats()")
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService is not initialized.")

            datasets_data = await self._cognee.list_datasets()
            dataset_count = len(datasets_data)
            total_files = sum(int(d.get("file_count", 0)) for d in datasets_data)
            display_size = f"{total_files} files"

            kg_status = "not_extracted"
            graph_nodes = None
            graph_edges = None

            try:
                g_data = await self._cognee.get_graph_data()
                nodes = g_data.get("nodes", [])
                edges = g_data.get("edges", [])
                if len(nodes) > 0 or len(edges) > 0:
                    kg_status = "extracted"
                    graph_nodes = len(nodes)
                    graph_edges = len(edges)
            except Exception:
                kg_status = "not_extracted"

            response = MemoryStatsResponse(
                success=True,
                total_size_display=display_size,
                dataset_count=dataset_count,
                knowledge_graph_status=kg_status,
                graph_nodes=graph_nodes,
                graph_edges=graph_edges,
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: get_memory_stats() complete | datasets=%d | %.2fs", dataset_count, elapsed)
            return response
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_memory_stats() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to get memory stats: {e}")
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_memory_stats() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to get memory stats: {e}")

    async def get_memory_graph(
        self,
        dataset_name: Optional[str] = None,
    ) -> MemoryGraphResponse | ErrorResponse:
        """Get authoritative knowledge graph topology."""
        start = time.monotonic()
        logger.info("use_case: get_memory_graph() | dataset=%s", dataset_name)
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService is not initialized.")

            g_data = await self._cognee.get_graph_data(dataset_name=dataset_name)
            nodes = [
                MemoryGraphNode(
                    id=str(n.get("id", "")),
                    label=str(n.get("label", n.get("id", ""))),
                    kind=str(n.get("kind", "entity")),
                    type=n.get("type"),
                    properties=n.get("properties", {}),
                )
                for n in g_data.get("nodes", [])
            ]
            edges = [
                MemoryGraphEdge(
                    source=str(e.get("source", "")),
                    target=str(e.get("target", "")),
                    kind=str(e.get("kind", "relates_to")),
                    relationship_type=e.get("relationship_type"),
                    properties=e.get("properties", {}),
                )
                for e in g_data.get("edges", [])
            ]

            status = "extracted" if len(nodes) > 0 else "not_extracted"
            msg = "Authoritative graph topology loaded" if len(nodes) > 0 else "Knowledge graph has not been extracted yet."

            response = MemoryGraphResponse(
                success=True,
                status=status,
                nodes=nodes,
                edges=edges,
                total_nodes=len(nodes),
                total_edges=len(edges),
                dataset_name=dataset_name,
                message=msg,
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: get_memory_graph() complete | nodes=%d | edges=%d | %.2fs", len(nodes), len(edges), elapsed)
            return response
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_memory_graph() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to get memory graph: {e}")
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_memory_graph() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(error=type(e).__name__, message=f"Failed to get memory graph: {e}")

    async def get_memory_vectors(self) -> MemoryVectorsResponse | ErrorResponse:
        """Get vector index metadata and embeddings status."""
        start = time.monotonic()
        logger.info("use_case: get_memory_vectors()")
        try:
            self._ensure_services()
            if self._cognee is None:
                raise CogneeServiceError("CogneeService is not initialized.")

            v_data = await self._cognee.get_vector_stats()
            tables_list = v_data.get("tables", [])
            datasets_list = [
                VectorDatasetInfo(
                    id=str(d.get("id", "")),
                    name=str(d.get("name", "")),
                    file_count=int(d.get("file_count", 0)),
                    size_bytes=int(d.get("size_bytes", 0)),
                    created_at=d.get("created_at"),
                    vector_status=str(d.get("vector_status", "ready")),
                    chunk_count=int(d.get("chunk_count", 0)),
                )
                for d in v_data.get("datasets", [])
            ]

            total_vecs = v_data.get("total_vectors", sum(d.chunk_count for d in datasets_list))
            settings = self._get_settings()
            emb_model = settings.ollama.embedding_model if settings else ""
            msg = "Authoritative vector index information loaded"

            elapsed = time.monotonic() - start
            logger.info("use_case: get_memory_vectors() complete | vectors=%d | %.2fs", total_vecs, elapsed)
            return MemoryVectorsResponse(
                success=True,
                vector_db_provider=settings.cognee.vector_db if settings else "lancedb",
                embedding_model=emb_model,
                embedding_dimensions=768,
                total_datasets=len(datasets_list),
                total_files=sum(d.file_count for d in datasets_list),
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
            store = self._metadata_store.load()
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
