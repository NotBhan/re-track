"""
Thin wrapper around Cognee for AndesContext memory operations.

Responsibilities only:
- initialize()
- remember()
- recall()
- improve()
- forget()

No business logic. No repository indexing. No batching.
No context generation. No filesystem logic. No UI logic.
"""

import logging
from typing import Any, Optional

import cognee

from app.config.settings import Settings, get_settings
from app.models.errors import CogneeServiceError
from app.models.responses import RecallResult, RecallResponse, RememberResult

logger = logging.getLogger(__name__)


class CogneeService:
    """Thin wrapper providing AndesContext memory operations via Cognee.

    This service delegates all work to the Cognee SDK. It does not
    contain business logic, repository scanning, or context generation.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        """Configure and validate Cognee for local operation.

        Sets environment variables, validates Ollama connectivity,
        and ensures storage directories exist.

        Raises:
            CogneeServiceError: If initialization fails.
        """
        if self._initialized:
            return

        try:
            self._settings.configure_cognee()
            self._settings.validate_ollama()
            self._settings.ensure_directories()
            self._initialized = True
            logger.info(
                "CogneeService initialized | model=%s | embedding=%s",
                self._settings.ollama.llm_model,
                self._settings.ollama.embedding_model,
            )
        except Exception as e:
            logger.error("CogneeService initialization failed: %s", e)
            raise CogneeServiceError(f"Initialization failed: {e}") from e

    async def remember(
        self,
        data: Any,
        dataset_name: str = "default",
        **kwargs: Any,
    ) -> RememberResult:
        """Ingest data into persistent memory.

        Args:
            data: Content to ingest (str, list of str, file paths, etc.).
            dataset_name: Logical memory namespace.
            **kwargs: Additional arguments passed to cognee.remember().

        Returns:
            RememberResult with dataset name and item count.

        Raises:
            CogneeServiceError: If ingestion fails.
        """
        self._ensure_initialized()
        try:
            items = len(data) if isinstance(data, list) else 1
            logger.info(
                "remember() | dataset=%s | items=%d", dataset_name, items
            )
            result = await cognee.remember(
                data=data, dataset_name=dataset_name, **kwargs
            )
            return RememberResult(
                dataset_name=dataset_name,
                items_sent=items,
                raw_result=result,
            )
        except Exception as e:
            logger.error("remember() failed: %s", e)
            raise CogneeServiceError(f"remember() failed: {e}") from e

    async def recall(
        self,
        query_text: str,
        datasets: list[str],
        top_k: int = 15,
        **kwargs: Any,
    ) -> RecallResponse:
        """Retrieve context from persistent memory.

        Args:
            query_text: Natural language query.
            datasets: List of dataset names to search.
            top_k: Maximum number of results.
            **kwargs: Additional arguments passed to cognee.recall().

        Returns:
            RecallResponse with parsed results.

        Raises:
            CogneeServiceError: If retrieval fails.
        """
        self._ensure_initialized()
        try:
            logger.info(
                "recall() | query=%s | datasets=%s | top_k=%d",
                query_text[:80],
                datasets,
                top_k,
            )
            raw_results = await cognee.recall(
                query_text=query_text,
                datasets=datasets,
                top_k=top_k,
                **kwargs,
            )
            results = [
                RecallResult(
                    kind=getattr(r, "kind", "unknown"),
                    search_type=getattr(r, "search_type", "unknown"),
                    text=str(getattr(r, "text", r)),
                    score=float(getattr(r, "score", None) or 0.0),
                    dataset_name=getattr(r, "dataset_name", ""),
                    raw=r,
                )
                for r in raw_results
            ]
            return RecallResponse(
                query=query_text,
                dataset=", ".join(datasets),
                results=results,
            )
        except Exception as e:
            logger.error("recall() failed: %s", e)
            raise CogneeServiceError(f"recall() failed: {e}") from e

    async def improve(
        self,
        dataset: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Enrich and refine existing memory.

        Args:
            dataset: Optional dataset name. If None, improves all datasets.
            **kwargs: Additional arguments passed to cognee.improve().

        Returns:
            Raw result from Cognee.

        Raises:
            CogneeServiceError: If improvement fails.
        """
        self._ensure_initialized()
        try:
            logger.info("improve() | dataset=%s", dataset or "all")
            kwargs["dataset"] = dataset
            result = await cognee.improve(**kwargs)
            logger.info("improve() completed")
            return result
        except Exception as e:
            logger.error("improve() failed: %s", e)
            raise CogneeServiceError(f"improve() failed: {e}") from e

    async def forget(
        self,
        dataset: Optional[str] = None,
        dataset_id: Optional[str] = None,
        data_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Remove information from persistent memory.

        Args:
            dataset: Dataset name to delete.
            dataset_id: UUID of dataset to delete.
            data_id: UUID of specific data item to delete.
            **kwargs: Additional arguments passed to cognee.forget().

        Raises:
            CogneeServiceError: If deletion fails.
        """
        self._ensure_initialized()
        try:
            logger.info(
                "forget() | dataset=%s | dataset_id=%s | data_id=%s",
                dataset,
                dataset_id,
                data_id,
            )
            if dataset is not None:
                kwargs["dataset"] = dataset
            if dataset_id is not None:
                kwargs["dataset_id"] = dataset_id
            if data_id is not None:
                kwargs["data_id"] = data_id
            await cognee.forget(**kwargs)
            logger.info("forget() completed")
        except AttributeError as e:
            # Handle Cognee error when dataset doesn't exist
            if "NoneType" in str(e):
                logger.warning("forget() dataset not found: %s", dataset)
                return
            raise CogneeServiceError(f"forget() failed: {e}") from e
        except Exception as e:
            logger.error("forget() failed: %s", e)
            raise CogneeServiceError(f"forget() failed: {e}") from e

    async def list_datasets(self) -> list[dict[str, Any]]:
        """List all datasets stored in Cognee memory.

        Returns:
            List of dicts with keys: id, name, created_at, file_count.

        Raises:
            CogneeServiceError: If listing fails.
        """
        self._ensure_initialized()
        try:
            logger.info("list_datasets()")
            raw_datasets = await cognee.datasets.list_datasets()

            datasets: list[dict[str, Any]] = []
            for ds in raw_datasets:
                file_count = 0
                try:
                    data_items = await cognee.datasets.list_data(ds.id)
                    file_count = len(data_items)
                except Exception:
                    pass

                created = None
                if ds.created_at:
                    created = ds.created_at.isoformat() if hasattr(ds.created_at, "isoformat") else str(ds.created_at)

                datasets.append({
                    "id": str(ds.id),
                    "name": ds.name or "",
                    "created_at": created,
                    "file_count": file_count,
                })

            logger.info("list_datasets() | count=%d", len(datasets))
            return datasets
        except Exception as e:
            logger.error("list_datasets() failed: %s", e)
            raise CogneeServiceError(f"list_datasets() failed: {e}") from e

    async def get_graph_stats(self) -> dict[str, int]:
        """Get graph engine statistics if available.

        Returns:
            Dict with keys: graph_nodes, graph_edges.
            Returns 0 for both if graph engine is not available.

        Raises:
            CogneeServiceError: If stats retrieval fails unexpectedly.
        """
        self._ensure_initialized()
        try:
            # Try to access graph engine through Cognee's public API
            # Cognee may expose graph_stats or similar methods
            graph_nodes = 0
            graph_edges = 0

            # Attempt to get graph stats through cognee's graph module
            try:
                if hasattr(cognee, "graph"):
                    graph_module = cognee.graph
                    if hasattr(graph_module, "get_node_count"):
                        graph_nodes = await graph_module.get_node_count()
                    if hasattr(graph_module, "get_edge_count"):
                        graph_edges = await graph_module.get_edge_count()
            except Exception:
                # Graph engine not available or doesn't support stats
                pass

            return {"graph_nodes": graph_nodes, "graph_edges": graph_edges}
        except Exception as e:
            # Gracefully return zeros if anything goes wrong
            logger.warning("get_graph_stats() failed, returning zeros: %s", e)
            return {"graph_nodes": 0, "graph_edges": 0}

    def _ensure_initialized(self) -> None:
        """Raise if service is not initialized."""
        if not self._initialized:
            raise CogneeServiceError(
                "CogneeService not initialized. Call initialize() first."
            )
