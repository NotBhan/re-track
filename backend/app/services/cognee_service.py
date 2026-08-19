"""
Thin wrapper around Cognee for RE:Track (RefinedEngine Track) memory operations.

Responsibilities only:
- remember(data, dataset_name) -> remember_result
- recall(search_type, query, datasets) -> recall_result
- improve()
- forget(dataset_id)
- configure_engine(custom_config)

Never imports from other services.
All Cognee imports stay inside this module.
"""

import logging
import asyncio
import re
from typing import Any, Optional

import cognee

from app.config.settings import Settings, get_settings
from app.models.errors import CogneeServiceError
from app.models.responses import RememberResult, RecallResult, RecallResponse, SectionType

logger = logging.getLogger(__name__)


def sanitize_dataset_name(name: str | None) -> str:
    """Sanitize a dataset name for Cognee and vector databases.
    Removes .git suffix, and replaces dots, spaces, slashes, and non-alphanumerics with underscores.
    """
    if not name:
        return "default"
    clean = str(name).strip()
    if clean.endswith(".git"):
        clean = clean[:-4]
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", clean)
    clean = re.sub(r"_+", "_", clean).strip("-_")
    return clean or "default"


class CogneeService:
    """Thin wrapper providing RE:Track memory operations via Cognee.

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

    async def add(
        self,
        data: Any,
        dataset_name: str = "default",
        **kwargs: Any,
    ) -> RememberResult:
        """Add data to memory without LLM graph extraction.

        Args:
            data: Content to ingest (str, list of str, file paths, etc.).
            dataset_name: Logical memory namespace.
            **kwargs: Additional arguments passed to cognee.add().

        Returns:
            RememberResult with dataset name and item count.

        Raises:
            CogneeServiceError: If ingestion fails.
        """
        self._ensure_initialized()
        dataset_name = sanitize_dataset_name(dataset_name)
        try:
            items = len(data) if isinstance(data, list) else 1
            logger.info("add() | dataset=%s | items=%d", dataset_name, items)
            result = await cognee.add(
                data=data, dataset_name=dataset_name, **kwargs
            )
            return RememberResult(
                dataset_name=dataset_name,
                items_sent=items,
                raw_result=result,
            )
        except Exception as e:
            logger.error("add() failed: %s", e)
            raise CogneeServiceError(f"add() failed: {e}") from e

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
        dataset_name = sanitize_dataset_name(dataset_name)
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
        clean_datasets = [sanitize_dataset_name(d) for d in datasets]
        try:
            logger.info(
                "recall() | query=%s | datasets=%s | top_k=%d",
                query_text[:80],
                clean_datasets,
                top_k,
            )
            raw_results = await cognee.recall(
                query_text=query_text,
                datasets=clean_datasets,
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
                dataset=", ".join(clean_datasets),
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
        clean_dataset = sanitize_dataset_name(dataset) if dataset else None
        try:
            logger.info("improve() | dataset=%s", clean_dataset or "all")
            kwargs["dataset"] = clean_dataset
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
        clean_dataset = sanitize_dataset_name(dataset) if dataset else None
        try:
            logger.info(
                "forget() | dataset=%s | dataset_id=%s | data_id=%s",
                clean_dataset,
                dataset_id,
                data_id,
            )
            if clean_dataset is not None:
                kwargs["dataset"] = clean_dataset
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
            from cognee.modules.data.methods import get_dataset_data

            datasets: list[dict[str, Any]] = []
            for ds in raw_datasets:
                file_count = 0
                size_bytes = 0
                try:
                    data_items = await get_dataset_data(ds.id)
                    file_count = len(data_items)
                    size_bytes = sum(getattr(it, "data_size", 0) or 0 for it in data_items)
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
                    "size_bytes": size_bytes,
                })

            logger.info("list_datasets() | count=%d", len(datasets))
            return datasets
        except Exception as e:
            logger.error("list_datasets() failed: %s", e)
            raise CogneeServiceError(f"list_datasets() failed: {e}") from e

    async def get_dataset_data_items(self, dataset_id_or_name: str) -> list[dict[str, Any]]:
        """Get all stored/ingested files and documents for a dataset.

        Args:
            dataset_id_or_name: UUID string or name of the dataset.

        Returns:
            List of data item dicts with authoritative fields.
        """
        self._ensure_initialized()
        try:
            from uuid import UUID
            from cognee.modules.data.methods import get_dataset_data

            target_id = None
            try:
                target_id = UUID(dataset_id_or_name)
            except ValueError:
                # Resolve name to ID
                raw_datasets = await cognee.datasets.list_datasets()
                for ds in raw_datasets:
                    if ds.name == dataset_id_or_name:
                        target_id = ds.id
                        break

            if target_id is None:
                return []

            data_items = await get_dataset_data(target_id)
            results: list[dict[str, Any]] = []
            for it in data_items:
                created = None
                if hasattr(it, "created_at") and it.created_at:
                    created = it.created_at.isoformat() if hasattr(it.created_at, "isoformat") else str(it.created_at)

                results.append({
                    "id": str(it.id),
                    "name": getattr(it, "name", "unknown"),
                    "mime_type": getattr(it, "mime_type", "text/plain"),
                    "data_size": getattr(it, "data_size", 0) or 0,
                    "created_at": created,
                    "extension": getattr(it, "extension", "") or "",
                    "content_hash": getattr(it, "content_hash", "") or "",
                    "pipeline_status": getattr(it, "pipeline_status", {}) or {},
                })

            return results
        except Exception as e:
            logger.warning("get_dataset_data_items failed: %s", e)
            return []

    async def get_graph_stats(self) -> dict[str, int]:
        """Get graph engine statistics from Cognee graph engine.

        Returns:
            Dict with keys: graph_nodes, graph_edges.
        """
        self._ensure_initialized()
        try:
            from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
            ge = await get_graph_engine()
            nodes, edges = await ge.get_graph_data()
            return {"graph_nodes": len(nodes), "graph_edges": len(edges)}
        except Exception as e:
            logger.warning("get_graph_stats() failed, returning zeros: %s", e)
            return {"graph_nodes": 0, "graph_edges": 0}

    async def get_graph_data(self) -> tuple[list[Any], list[Any]]:
        """Get authoritative nodes and edges directly from the Cognee graph engine.

        Returns:
            Tuple of (nodes, edges).
        """
        self._ensure_initialized()
        try:
            from cognee.infrastructure.databases.graph.get_graph_engine import get_graph_engine
            ge = await get_graph_engine()
            nodes, edges = await ge.get_graph_data()
            return nodes, edges
        except Exception as e:
            logger.warning("get_graph_data() failed: %s", e)
            return [], []

    def _ensure_initialized(self) -> None:
        """Raise if service is not initialized."""
        if not self._initialized:
            raise CogneeServiceError(
                "CogneeService not initialized. Call initialize() first."
            )
