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

import hashlib
import logging
import asyncio
import re
import os
import time
from typing import Any, Optional

from app.application.domain.memory import (
    MemoryProvenance,
    SemanticMemoryRecord,
    Tier3ProjectionCandidate,
    Tier3RetrievalResult,
)
from app.config.settings import Settings, get_settings
from app.models.errors import CogneeServiceError
from app.models.responses import RememberResult, RecallResult, RecallResponse, SectionType

logger = logging.getLogger(__name__)


def default_recall_query_type() -> Any:
    """Deterministic retrieval mode for every RE:Track retrieval tier.

    RE:Track retrieval is vector/chunk retrieval: Tier-3 projections (LanceDB/Kùzu)
    and Tier-4 Cognee semantic memory are both derived storage that must be recalled
    without invoking the LLM. `SearchType.CHUNKS` maps to `ChunksRetriever` (no LLM),
    whereas Cognee's automatic router can select LLM-backed strategies such as
    `GRAPH_COMPLETION_COT`.
    """
    from cognee.modules.search.types import SearchType

    return SearchType.CHUNKS


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
        self._last_retrieval_telemetry: dict[str, Any] = {}
        self._last_tier3_telemetry: dict[str, Any] = {}

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def last_retrieval_telemetry(self) -> dict[str, Any]:
        """Telemetry from the most recent retrieve_semantic_memory invocation."""
        return dict(self._last_retrieval_telemetry)

    @property
    def last_tier3_telemetry(self) -> dict[str, Any]:
        """Telemetry from the most recent retrieve_tier3_lancedb_kuzu invocation."""
        return dict(self._last_tier3_telemetry)

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
            import cognee
            self._settings.configure_cognee()
            self._settings.validate_provider()
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

    async def close(self) -> None:
        """Release any underlying database engine handles and flush caches."""
        self._initialized = False
        try:
            from cognee.infrastructure.databases.utils.closing_lru_cache import _DECORATED_CACHES

            for cache in list(_DECORATED_CACHES):
                with cache._lock:
                    keys = list(cache._cache.keys())
                for key in keys:
                    try:
                        cache.evict_and_close(key)
                    except Exception:
                        pass
                try:
                    cache.cache_clear()
                except Exception:
                    pass
                try:
                    await cache.await_pending_closes()
                except Exception:
                    pass
        except Exception as e:
            logger.debug("CogneeService.close error closing engines: %s", e)


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
            import cognee
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
            import cognee
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

    async def embedding_availability(self) -> dict[str, Any]:
        """Report the configured embedding provider identity and availability.

        Never substitutes a provider or model; a failure to probe is itself
        reported as an unavailable state.
        """
        try:
            return await self._settings.probe_embedding_provider()
        except Exception as e:  # pragma: no cover - probe failures are reported, not raised
            identity = self._settings.embedding_identity()
            return {
                "provider": identity["provider"],
                "endpoint": identity["endpoint"],
                "model": identity["model"],
                "dimensions": identity["dimensions"],
                "state": "unreachable",
                "detail": f"Embedding probe failed: {type(e).__name__}: {e}",
                "available_models": [],
            }

    async def recall(
        self,
        query_text: str,
        datasets: list[str],
        top_k: int = 15,
        **kwargs: Any,
    ) -> RecallResponse:
        """Retrieve context from persistent memory using a deterministic retrieval mode.

        The retrieval mode is explicit: RE:Track's retrieval tiers are vector/chunk
        retrieval, so `SearchType.CHUNKS` is requested and Cognee's automatic
        query router is disabled. This prevents a retrieval operation from silently
        selecting an LLM-backed strategy (e.g. GRAPH_COMPLETION_COT) just to pick a
        search mode.

        Args:
            query_text: Natural language query.
            datasets: List of dataset names to search.
            top_k: Maximum number of results.
            **kwargs: Additional arguments passed to cognee.recall(). `query_type`
                (alias `search_type`) and `auto_route` may be overridden explicitly.

        Returns:
            RecallResponse with parsed results.

        Raises:
            CogneeServiceError: If retrieval fails, or if the configured embedding
                provider cannot serve the configured embedding model.
        """
        self._ensure_initialized()
        clean_datasets = [sanitize_dataset_name(d) for d in datasets]
        timeout = float(kwargs.pop("timeout", 3.0))
        # Support search_type -> query_type alias
        if "search_type" in kwargs and "query_type" not in kwargs:
            kwargs["query_type"] = kwargs.pop("search_type")
        query_type = kwargs.pop("query_type", None)
        if query_type is None:
            query_type = default_recall_query_type()
        auto_route = bool(kwargs.pop("auto_route", False))

        embedding_state = await self.embedding_availability()
        if embedding_state.get("state") in ("model_missing", "not_configured"):
            # Deterministically unusable configuration: fail with an explicit reason
            # rather than attempting retrieval and reporting an empty success.
            raise CogneeServiceError(
                f"Embedding provider unusable: {embedding_state.get('detail')} "
                f"(state={embedding_state.get('state')})"
            )

        try:
            import cognee
            logger.info(
                "recall() | mode=%s | auto_route=%s | query=%s | datasets=%s | top_k=%d",
                getattr(query_type, "value", query_type),
                auto_route,
                query_text[:80],
                clean_datasets,
                top_k,
            )
            raw_results = await asyncio.wait_for(
                cognee.recall(
                    query_text=query_text,
                    datasets=clean_datasets,
                    top_k=top_k,
                    query_type=query_type,
                    auto_route=auto_route,
                    **kwargs,
                ),
                timeout=timeout,
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
        except asyncio.TimeoutError as e:
            logger.error(
                "recall() timed out | mode=%s | after=%ss | embedding_state=%s",
                getattr(query_type, "value", query_type),
                timeout,
                embedding_state.get("state"),
            )
            raise CogneeServiceError(
                f"recall() timed out after {timeout}s "
                f"(mode={getattr(query_type, 'value', query_type)}, "
                f"embedding_provider={embedding_state.get('provider')}, "
                f"embedding_state={embedding_state.get('state')})"
            ) from e
        except Exception as e:
            detail = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            logger.error(
                "recall() failed | mode=%s | embedding_state=%s | %s",
                getattr(query_type, "value", query_type),
                embedding_state.get("state"),
                detail,
            )
            embedding_note = (
                ""
                if embedding_state.get("state") == "available"
                else (
                    f" [embedding_provider={embedding_state.get('provider')} "
                    f"state={embedding_state.get('state')}: {embedding_state.get('detail')}]"
                )
            )
            raise CogneeServiceError(
                f"recall() failed ({detail}) "
                f"[mode={getattr(query_type, 'value', query_type)}]{embedding_note}"
            ) from e

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
            import cognee
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
            import cognee
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
            import cognee
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

    async def get_vector_stats(self) -> dict[str, Any]:
        """Query LanceDB vector engine for active tables, rows, and vector metadata.

        Returns:
            Dict with keys: tables, total_vectors, embedding_model, embedding_dimensions.
        """
        self._ensure_initialized()
        try:
            from cognee.infrastructure.databases.vector.get_vector_engine import get_vector_engine
            v_engine = get_vector_engine()
            if asyncio.iscoroutine(v_engine):
                v_engine = await v_engine

            conn = await v_engine.get_connection()
            table_names = await conn.table_names() if hasattr(conn, "table_names") else []
            if asyncio.iscoroutine(table_names):
                table_names = await table_names

            tables_info: list[dict[str, Any]] = []
            total_vectors = 0

            for tname in table_names:
                try:
                    tbl = await conn.open_table(tname)
                    cnt = await tbl.count_rows() if hasattr(tbl, "count_rows") else 0
                    if asyncio.iscoroutine(cnt):
                        cnt = await cnt
                    total_vectors += cnt
                    tables_info.append({"table_name": tname, "row_count": cnt})
                except Exception as e_tbl:
                    logger.warning("Could not query table %s: %s", tname, e_tbl)

            emb_model = (
                getattr(self._settings.ollama, "embedding_model", None)
                or os.getenv("EMBEDDING_MODEL")
                or "nomic-embed-text"
            )
            emb_dim = 768
            try:
                emb_dim = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
            except ValueError:
                emb_dim = 768

            return {
                "tables": tables_info,
                "total_vectors": total_vectors,
                "embedding_model": emb_model,
                "embedding_dimensions": emb_dim,
                "storage_state": "healthy",
            }
        except Exception as e:
            logger.warning("get_vector_stats() failed: %s", e)
            emb_model = (
                getattr(self._settings.ollama, "embedding_model", None)
                or os.getenv("EMBEDDING_MODEL")
                or "nomic-embed-text"
            )
            return {
                "tables": [],
                "total_vectors": 0,
                "embedding_model": emb_model,
                "embedding_dimensions": 768,
                "storage_state": "unavailable",
            }

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

    async def cognify(self, dataset_name: Optional[str] = None) -> dict[str, Any]:
        """Run Cognee cognify pipeline on a dataset (or all datasets) to generate vectors and extract knowledge graph.

        Args:
            dataset_name: Optional dataset name to cognify.

        Returns:
            Dict containing extraction results: total_vectors, total_nodes, total_edges.
        """
        self._ensure_initialized()
        try:
            import cognee
            logger.info("Starting Cognee cognify pipeline | dataset=%s", dataset_name)
            if dataset_name:
                await cognee.cognify(datasets=[dataset_name])
            else:
                await cognee.cognify()

            v_stats = await self.get_vector_stats()
            g_stats = await self.get_graph_stats()

            return {
                "success": True,
                "dataset_name": dataset_name,
                "total_vectors": v_stats.get("total_vectors", 0),
                "total_nodes": g_stats.get("graph_nodes", 0),
                "total_edges": g_stats.get("graph_edges", 0),
                "message": f"Successfully extracted memory index for {dataset_name or 'all datasets'}",
            }
        except Exception as e:
            logger.error("Cognify failed for dataset %s: %s", dataset_name, e)
            raise CogneeServiceError(f"Extraction failed: {e}") from e

    def map_semantic_memory(
        self,
        item: Any,
        manifest: Any,
        repository_id: Optional[str] = None,
        repository_fingerprint: Optional[str] = None,
    ) -> tuple[Optional[SemanticMemoryRecord], str]:
        """Map a single Cognee memory item into a validated SemanticMemoryRecord."""
        return CogneeSemanticMemoryAdapter.map_item(
            item=item,
            manifest=manifest,
            repository_id=repository_id,
            repository_fingerprint=repository_fingerprint,
        )

    def map_semantic_memories(
        self,
        items: list[Any],
        manifest: Any,
        repository_id: Optional[str] = None,
        repository_fingerprint: Optional[str] = None,
    ) -> list[SemanticMemoryRecord]:
        """Map a batch of Cognee memory items into validated SemanticMemoryRecord entities."""
        return CogneeSemanticMemoryAdapter.map_items(
            items=items,
            manifest=manifest,
            repository_id=repository_id,
            repository_fingerprint=repository_fingerprint,
        )

    async def retrieve_semantic_memory(
        self,
        repository_id: str,
        query_text: str,
        manifest: Any,
        top_k: int = 15,
        repository_store: Optional[Any] = None,
        telemetry: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> list[SemanticMemoryRecord]:
        """Retrieve semantic memory for a repository, validating provenance against active manifest."""
        clean_ds = sanitize_dataset_name(repository_id)
        current_telemetry: dict[str, Any] = {
            "cognee_recall_attempted": True,
            "cognee_recall_succeeded": False,
            "cognee_items_received": 0,
            "cognee_items_accepted": 0,
            "cognee_items_rejected": 0,
            "cognee_rejection_reasons": {},
        }
        raw_candidates: list[Any] = []

        # 1. Try recalling from Cognee dataset
        try:
            from cognee.modules.search.types import SearchType
            query_type = kwargs.pop("query_type", kwargs.pop("search_type", SearchType.CHUNKS))
            recall_resp = await self.recall(
                query_text=query_text,
                datasets=[clean_ds],
                top_k=top_k,
                query_type=query_type,
                # Deterministic mode: never let Cognee's query router choose an
                # LLM-backed strategy for a retrieval operation.
                auto_route=False,
                only_context=kwargs.pop("only_context", True),
                **kwargs,
            )
            current_telemetry["cognee_recall_succeeded"] = True
            if recall_resp and recall_resp.results:
                raw_candidates = list(recall_resp.results)
                current_telemetry["cognee_items_received"] = len(raw_candidates)
        except Exception as e:
            logger.warning("Cognee recall failed for dataset %s: %s", clean_ds, e)
            current_telemetry["cognee_recall_succeeded"] = False

        # 2. Map Cognee recall items through adapter and validate against manifest
        cognee_records: list[SemanticMemoryRecord] = []
        for it in raw_candidates:
            rec, reason = self.map_semantic_memory(
                item=it,
                manifest=manifest,
                repository_id=repository_id,
            )
            if rec is not None:
                rec.generated_by = "cognee_pipeline"
                cognee_records.append(rec)
                current_telemetry["cognee_items_accepted"] += 1
            else:
                current_telemetry["cognee_items_rejected"] += 1
                reasons = current_telemetry["cognee_rejection_reasons"]
                reasons[reason] = reasons.get(reason, 0) + 1

        # 3. Persistent store fallback: used only if Cognee recall yielded no accepted memories.
        # Fallback records are explicitly marked so they are distinguishable from genuine Cognee retrieval.
        final_records: list[SemanticMemoryRecord] = []
        if cognee_records:
            final_records = cognee_records
        elif repository_store is not None:
            persisted = repository_store.get_by_repository(
                repository_id=repository_id,
                manifest=manifest,
                include_stale=False,
            )
            import copy
            for p in persisted:
                p_copy = copy.deepcopy(p) if hasattr(p, "__dict__") else p
                if hasattr(p_copy, "generated_by"):
                    p_copy.generated_by = "persistent_store_fallback"
                final_records.append(p_copy)

        self._last_retrieval_telemetry = current_telemetry
        if telemetry is not None and isinstance(telemetry, dict):
            telemetry.update(current_telemetry)

        return final_records

    @classmethod
    def _validate_tier3_candidate(
        cls,
        candidate: Tier3ProjectionCandidate,
        manifest: Any,
    ) -> tuple[bool, str]:
        """Validate candidate provenance against active repository manifest.

        Rejection reasons:
        - "missing_provenance": required provenance fields are empty
        - "cross_repository_mismatch": candidate belongs to a different repository/fingerprint
        - "file_not_in_manifest": source file is not in active manifest
        - "stale_sha256_mismatch": source file SHA256 does not match active manifest
        - "symbol_not_in_manifest": symbol declared but missing from file's symbols
        """
        if not candidate.source_file or not candidate.source_sha256:
            return False, "missing_provenance"

        if manifest is None:
            return False, "manifest_unavailable"

        manifest_fp = (
            getattr(manifest, "fingerprint", None)
            or (manifest.get("fingerprint") if isinstance(manifest, dict) else None)
        )
        manifest_repo_id = (
            getattr(manifest, "repository_id", None)
            or getattr(manifest, "repo_id", None)
            or (manifest.get("repository_id") if isinstance(manifest, dict) else None)
            or (manifest.get("repo_id") if isinstance(manifest, dict) else None)
        )

        # Cross-repository check
        if candidate.repository_fingerprint and manifest_fp:
            if candidate.repository_fingerprint != manifest_fp:
                return False, "cross_repository_mismatch"
        elif candidate.repository_id and manifest_repo_id:
            if candidate.repository_id != manifest_repo_id:
                return False, "cross_repository_mismatch"

        # Manifest files lookup
        manifest_files = (
            getattr(manifest, "files", None)
            or (manifest.get("files") if isinstance(manifest, dict) else None)
        )
        manifest_hashes = (
            getattr(manifest, "file_hashes", None)
            or (manifest.get("file_hashes") if isinstance(manifest, dict) else None)
        )

        file_key = candidate.source_file
        file_key_clean = file_key.lstrip("./")

        file_entry = None
        expected_sha = None

        if isinstance(manifest_files, dict):
            file_entry = (
                manifest_files.get(file_key)
                or manifest_files.get(file_key_clean)
                or manifest_files.get(f"./{file_key_clean}")
                or manifest_files.get(f"/{file_key_clean}")
            )
            if file_entry is not None:
                expected_sha = (
                    getattr(file_entry, "sha256", None)
                    or getattr(file_entry, "hash", None)
                    or (file_entry.get("sha256") if isinstance(file_entry, dict) else None)
                    or (file_entry.get("hash") if isinstance(file_entry, dict) else None)
                )
            elif manifest_hashes is None:
                return False, "file_not_in_manifest"
        elif isinstance(manifest_files, (list, set)):
            found = any(f == file_key or f.lstrip("./") == file_key_clean for f in manifest_files)
            if not found and manifest_hashes is None:
                return False, "file_not_in_manifest"

        if expected_sha is None and isinstance(manifest_hashes, dict):
            expected_sha = (
                manifest_hashes.get(file_key)
                or manifest_hashes.get(file_key_clean)
                or manifest_hashes.get(f"./{file_key_clean}")
            )
            if expected_sha is None and (manifest_files is None or isinstance(manifest_files, dict)):
                return False, "file_not_in_manifest"

        if expected_sha and candidate.source_sha256 != expected_sha:
            return False, "stale_sha256_mismatch"

        if candidate.source_symbol and file_entry is not None:
            symbols = (
                getattr(file_entry, "symbols", None)
                or (file_entry.get("symbols") if isinstance(file_entry, dict) else None)
            )
            if symbols is not None and isinstance(symbols, (list, set)):
                sym_clean = candidate.source_symbol.strip()
                if sym_clean and not any(
                    s == sym_clean
                    or getattr(s, "name", None) == sym_clean
                    or (s.get("name") if isinstance(s, dict) else None) == sym_clean
                    for s in symbols
                ):
                    return False, "symbol_not_in_manifest"

        return True, "valid"

    @classmethod
    def _normalize_lancedb_candidate(
        cls,
        item: Any,
        manifest: Any,
        repository_id: str,
        index: int,
    ) -> Optional[Tier3ProjectionCandidate]:
        """Normalize raw LanceDB record or ScoredResult into canonical Tier3ProjectionCandidate."""
        if isinstance(item, Tier3ProjectionCandidate):
            item.origin = "lancedb"
            return item

        manifest_fp = getattr(manifest, "fingerprint", "") if manifest else ""
        manifest_repo_id = (
            getattr(manifest, "repository_id", None)
            or getattr(manifest, "repo_id", None)
            or repository_id
        )

        if isinstance(item, dict):
            prov = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
            item_id = str(item.get("id") or f"lancedb_{index}")
            text = str(item.get("text") or item.get("content") or item.get("semantic_text") or "")
            if "similarity" in item:
                try:
                    relevance = min(1.0, max(0.1, float(item["similarity"])))
                except (ValueError, TypeError):
                    relevance = 0.75
            elif "relevance" in item:
                try:
                    relevance = min(1.0, max(0.1, float(item["relevance"])))
                except (ValueError, TypeError):
                    relevance = 0.75
            elif "score" in item:
                try:
                    score_f = float(item["score"])
                    relevance = min(1.0, max(0.1, 1.0 - score_f if score_f <= 1.0 else 0.1))
                except (ValueError, TypeError):
                    relevance = 0.75
            else:
                relevance = 0.75

            source_file = str(item.get("source_file") or item.get("file_path") or item.get("path") or prov.get("source_file") or "")
            source_sha = str(item.get("source_sha256") or item.get("file_hash") or item.get("sha256") or prov.get("source_sha256") or "")
            repo_id = str(item.get("repository_id") or prov.get("repository_id") or manifest_repo_id or repository_id)
            repo_fp = str(item.get("repository_fingerprint") or prov.get("repository_fingerprint") or manifest_fp or "")
            source_sym = item.get("source_symbol") or item.get("symbol") or prov.get("source_symbol")
            rel_kind = str(item.get("relationship_kind") or prov.get("relationship_kind") or "vector_projection")

            return Tier3ProjectionCandidate(
                id=item_id,
                origin="lancedb",
                text=text,
                relevance=relevance,
                source_file=source_file,
                source_sha256=source_sha,
                repository_id=repo_id,
                repository_fingerprint=repo_fp,
                source_symbol=source_sym,
                relationship_kind=rel_kind,
                metadata={k: v for k, v in item.items() if k not in ("id", "text", "source_file", "source_sha256", "repository_id", "repository_fingerprint", "source_symbol", "relationship_kind")},
            )

        payload = getattr(item, "payload", None) or {}
        item_id = str(getattr(item, "id", f"lancedb_{index}"))
        score = getattr(item, "score", 0.25)
        try:
            score_f = float(score)
            relevance = min(1.0, max(0.1, 1.0 - score_f if score_f <= 1.0 else 0.1))
        except (ValueError, TypeError):
            relevance = 0.75

        text = str(payload.get("text") or payload.get("content") or "")
        source_file = str(payload.get("source_file") or payload.get("file_path") or payload.get("path") or "")
        source_sha = str(payload.get("source_sha256") or payload.get("file_hash") or payload.get("sha256") or "")
        repo_id = str(payload.get("repository_id") or manifest_repo_id or repository_id)
        repo_fp = str(payload.get("repository_fingerprint") or manifest_fp or "")
        source_sym = payload.get("source_symbol") or payload.get("symbol")
        rel_kind = str(payload.get("relationship_kind") or "vector_projection")

        return Tier3ProjectionCandidate(
            id=item_id,
            origin="lancedb",
            text=text,
            relevance=relevance,
            source_file=source_file,
            source_sha256=source_sha,
            repository_id=repo_id,
            repository_fingerprint=repo_fp,
            source_symbol=source_sym,
            relationship_kind=rel_kind,
            metadata=dict(payload),
        )

    @classmethod
    def _normalize_kuzu_candidate(
        cls,
        item: Any,
        manifest: Any,
        repository_id: str,
        query_text: str,
        index: int,
    ) -> Optional[Tier3ProjectionCandidate]:
        """Normalize raw Kùzu node, edge, or dictionary into canonical Tier3ProjectionCandidate."""
        if isinstance(item, Tier3ProjectionCandidate):
            item.origin = "kuzu"
            return item

        manifest_fp = getattr(manifest, "fingerprint", "") if manifest else ""
        manifest_repo_id = (
            getattr(manifest, "repository_id", None)
            or getattr(manifest, "repo_id", None)
            or repository_id
        )

        query_terms = [t.lower() for t in query_text.split()] if query_text else []

        if isinstance(item, tuple):
            if len(item) == 4:
                src_id, tgt_id, rel_name, edge_props = str(item[0]), str(item[1]), str(item[2]), item[3] if isinstance(item[3], dict) else {}
                text = str(edge_props.get("text") or edge_props.get("description") or f"Relationship: {src_id} -[{rel_name}]-> {tgt_id}")
                sim = edge_props.get("similarity") or edge_props.get("relevance") or edge_props.get("score")
                if sim is not None:
                    try:
                        relevance = min(1.0, max(0.1, float(sim)))
                    except (ValueError, TypeError):
                        relevance = 0.75
                else:
                    relevance = 0.85 if any(t in f"{src_id} {rel_name} {tgt_id}".lower() for t in query_terms) else 0.70

                source_file = str(edge_props.get("source_file") or edge_props.get("file_path") or edge_props.get("path") or "")
                source_sha = str(edge_props.get("source_sha256") or edge_props.get("file_hash") or edge_props.get("sha256") or "")
                repo_id = str(edge_props.get("repository_id") or manifest_repo_id or repository_id)
                repo_fp = str(edge_props.get("repository_fingerprint") or manifest_fp or "")
                source_sym = edge_props.get("source_symbol") or edge_props.get("symbol") or src_id

                return Tier3ProjectionCandidate(
                    id=f"kuzu_edge_{src_id}_{rel_name}_{tgt_id}",
                    origin="kuzu",
                    text=text,
                    relevance=relevance,
                    source_file=source_file,
                    source_sha256=source_sha,
                    repository_id=repo_id,
                    repository_fingerprint=repo_fp,
                    source_symbol=source_sym,
                    relationship_kind=rel_name or "graph_projection",
                    graph_source_node=src_id,
                    graph_target_node=tgt_id,
                    metadata=dict(edge_props),
                )
            elif len(item) == 2:
                node_id, node_props = str(item[0]), item[1] if isinstance(item[1], dict) else {}
                desc = node_props.get("description") or node_props.get("name") or ""
                text = str(node_props.get("text") or (f"Node: {node_id} ({desc})" if desc else f"Node: {node_id}"))
                sim = node_props.get("similarity") or node_props.get("relevance") or node_props.get("score")
                if sim is not None:
                    try:
                        relevance = min(1.0, max(0.1, float(sim)))
                    except (ValueError, TypeError):
                        relevance = 0.70
                else:
                    relevance = 0.80 if any(t in f"{node_id} {desc}".lower() for t in query_terms) else 0.65

                source_file = str(node_props.get("source_file") or node_props.get("file_path") or node_props.get("path") or "")
                source_sha = str(node_props.get("source_sha256") or node_props.get("file_hash") or node_props.get("sha256") or "")
                repo_id = str(node_props.get("repository_id") or manifest_repo_id or repository_id)
                repo_fp = str(node_props.get("repository_fingerprint") or manifest_fp or "")
                source_sym = node_props.get("source_symbol") or node_props.get("symbol") or node_props.get("name") or node_id

                return Tier3ProjectionCandidate(
                    id=f"kuzu_node_{node_id}",
                    origin="kuzu",
                    text=text,
                    relevance=relevance,
                    source_file=source_file,
                    source_sha256=source_sha,
                    repository_id=repo_id,
                    repository_fingerprint=repo_fp,
                    source_symbol=source_sym,
                    relationship_kind=str(node_props.get("relationship_kind") or "graph_node"),
                    graph_source_node=node_id,
                    graph_target_node=None,
                    metadata=dict(node_props),
                )

        if isinstance(item, dict):
            prov = item.get("provenance") if isinstance(item.get("provenance"), dict) else {}
            item_id = str(item.get("id") or f"kuzu_{index}")
            text = str(item.get("text") or item.get("content") or item.get("description") or "")
            score = item.get("score") if item.get("score") is not None else item.get("similarity", item.get("relevance", 0.75))
            try:
                score_f = float(score)
                relevance = min(1.0, max(0.1, score_f))
            except (ValueError, TypeError):
                relevance = 0.75
            source_file = str(item.get("source_file") or item.get("file_path") or item.get("path") or prov.get("source_file") or "")
            source_sha = str(item.get("source_sha256") or item.get("file_hash") or item.get("sha256") or prov.get("source_sha256") or "")
            repo_id = str(item.get("repository_id") or prov.get("repository_id") or manifest_repo_id or repository_id)
            repo_fp = str(item.get("repository_fingerprint") or prov.get("repository_fingerprint") or manifest_fp or "")
            source_sym = item.get("source_symbol") or item.get("symbol") or prov.get("source_symbol")
            rel_kind = str(item.get("relationship_kind") or prov.get("relationship_kind") or "graph_projection")

            return Tier3ProjectionCandidate(
                id=item_id,
                origin="kuzu",
                text=text,
                relevance=relevance,
                source_file=source_file,
                source_sha256=source_sha,
                repository_id=repo_id,
                repository_fingerprint=repo_fp,
                source_symbol=source_sym,
                relationship_kind=rel_kind,
                graph_source_node=item.get("graph_source_node"),
                graph_target_node=item.get("graph_target_node"),
                metadata={k: v for k, v in item.items() if k not in ("id", "text", "source_file", "source_sha256", "repository_id", "repository_fingerprint", "source_symbol", "relationship_kind", "graph_source_node", "graph_target_node")},
            )

        return None

    async def _retrieve_lancedb_projections_internal(
        self,
        repository_id: str,
        query_text: str,
        manifest: Any,
        top_k: int = 15,
        **kwargs: Any,
    ) -> tuple[list[Tier3ProjectionCandidate], str, list[str], dict[str, int], int]:
        """Internal worker retrieving, normalizing, and validating LanceDB vector projections."""
        raw_items: list[Any] = []
        state = "healthy"
        errors: list[str] = []
        rejection_reasons: dict[str, int] = {}

        if "lancedb_records" in kwargs:
            raw_items = list(kwargs["lancedb_records"] or [])
        else:
            clean_ds = sanitize_dataset_name(repository_id)
            try:
                from cognee.infrastructure.databases.vector import get_vector_engine_async, get_vector_engine
                try:
                    ve = await get_vector_engine_async()
                except (TypeError, AttributeError):
                    ve = get_vector_engine()
                conn = await ve.get_connection()
                table_names = await conn.table_names()
            except Exception as e:
                logger.warning("Failed to access LanceDB storage: %s", e)
                return [], "unavailable", [f"LanceDB storage unavailable: {e}"], {}, 0

            if not table_names:
                return [], "empty", [], {}, 0

            matching = [t for t in table_names if clean_ds in t]
            if not matching:
                return [], "empty", [], {}, 0

            for tbl in matching:
                try:
                    search_res = await ve.search(
                        collection_name=tbl,
                        query_text=query_text,
                        limit=top_k,
                        include_payload=True,
                    )
                    if search_res:
                        raw_items.extend(search_res)
                except Exception as e:
                    logger.warning("LanceDB search error on table %s: %s", tbl, e)
                    errors.append(f"Table {tbl} read error: {e}")

            if errors and not raw_items:
                state = "corrupt"

        total_raw = len(raw_items)
        if total_raw == 0 and state != "corrupt":
            state = "empty"

        accepted: list[Tier3ProjectionCandidate] = []
        for i, it in enumerate(raw_items):
            cand = self._normalize_lancedb_candidate(it, manifest, repository_id, i)
            if cand is None:
                rejection_reasons["unparseable_record"] = rejection_reasons.get("unparseable_record", 0) + 1
                continue
            is_valid, reason = self._validate_tier3_candidate(cand, manifest)
            if is_valid:
                accepted.append(cand)
            else:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        return accepted, state, errors, rejection_reasons, total_raw

    async def _retrieve_kuzu_projections_internal(
        self,
        repository_id: str,
        query_text: str,
        manifest: Any,
        top_k: int = 15,
        **kwargs: Any,
    ) -> tuple[list[Tier3ProjectionCandidate], str, list[str], dict[str, int], int]:
        """Internal worker retrieving, normalizing, and validating Kùzu graph projections."""
        raw_items: list[Any] = []
        state = "healthy"
        errors: list[str] = []
        rejection_reasons: dict[str, int] = {}

        if "kuzu_records" in kwargs:
            raw_items = list(kwargs["kuzu_records"] or [])
        else:
            try:
                from cognee.infrastructure.databases.graph import get_graph_engine
                ge = await get_graph_engine()
                is_empty = await ge.is_empty()
                if is_empty:
                    return [], "empty", [], {}, 0
                nodes, edges = await ge.get_graph_data()
                if edges:
                    raw_items.extend(edges)
                if nodes:
                    raw_items.extend(nodes)
            except Exception as e:
                logger.warning("Failed to access Kùzu storage: %s", e)
                return [], "unavailable", [f"Kùzu storage unavailable: {e}"], {}, 0

        total_raw = len(raw_items)
        if total_raw == 0:
            state = "empty"

        accepted: list[Tier3ProjectionCandidate] = []
        for i, it in enumerate(raw_items):
            cand = self._normalize_kuzu_candidate(it, manifest, repository_id, query_text, i)
            if cand is None:
                rejection_reasons["unparseable_record"] = rejection_reasons.get("unparseable_record", 0) + 1
                continue
            is_valid, reason = self._validate_tier3_candidate(cand, manifest)
            if is_valid:
                accepted.append(cand)
            else:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        # Query-awareness & top_k bounding: sort by relevance descending and slice to top_k
        accepted.sort(key=lambda c: c.relevance, reverse=True)
        accepted = accepted[:top_k]

        return accepted, state, errors, rejection_reasons, total_raw

    async def retrieve_lancedb_projections(
        self,
        repository_id: str,
        query_text: str,
        manifest: Any,
        top_k: int = 15,
        **kwargs: Any,
    ) -> list[Tier3ProjectionCandidate]:
        """Retrieve direct vector projections from LanceDB, validating provenance against active manifest."""
        cands, _, _, _, _ = await self._retrieve_lancedb_projections_internal(
            repository_id=repository_id,
            query_text=query_text,
            manifest=manifest,
            top_k=top_k,
            **kwargs,
        )
        return cands

    async def retrieve_kuzu_projections(
        self,
        repository_id: str,
        query_text: str,
        manifest: Any,
        top_k: int = 15,
        **kwargs: Any,
    ) -> list[Tier3ProjectionCandidate]:
        """Retrieve direct graph projections from Kùzu, validating provenance against active manifest."""
        cands, _, _, _, _ = await self._retrieve_kuzu_projections_internal(
            repository_id=repository_id,
            query_text=query_text,
            manifest=manifest,
            top_k=top_k,
            **kwargs,
        )
        return cands

    async def retrieve_tier3_lancedb_kuzu(
        self,
        repository_id: str,
        query_text: str,
        manifest: Any,
        top_k: int = 15,
        telemetry: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Tier3RetrievalResult:
        """Retrieve unified Tier-3 direct projections from LanceDB and Kùzu for arbitration.

        Invariants:
        - LanceDB failure does not suppress Kùzu retrieval.
        - Kùzu failure does not suppress LanceDB retrieval.
        - Provenance is strictly verified against active manifest.
        - Never invokes LLM generation, cognify, or persistence mutation.
        """
        l_res, k_res = await asyncio.gather(
            self._retrieve_lancedb_projections_internal(
                repository_id=repository_id,
                query_text=query_text,
                manifest=manifest,
                top_k=top_k,
                **kwargs,
            ),
            self._retrieve_kuzu_projections_internal(
                repository_id=repository_id,
                query_text=query_text,
                manifest=manifest,
                top_k=top_k,
                **kwargs,
            ),
            return_exceptions=True,
        )

        if isinstance(l_res, Exception):
            l_cands, l_state, l_errors, l_reasons, l_raw = [], "unavailable", [str(l_res)], {}, 0
        else:
            l_cands, l_state, l_errors, l_reasons, l_raw = l_res

        if isinstance(k_res, Exception):
            k_cands, k_state, k_errors, k_reasons, k_raw = [], "unavailable", [str(k_res)], {}, 0
        else:
            k_cands, k_state, k_errors, k_reasons, k_raw = k_res

        combined_reasons: dict[str, int] = {}
        for r_dict in (l_reasons, k_reasons):
            for k, v in r_dict.items():
                combined_reasons[k] = combined_reasons.get(k, 0) + v

        # Combine candidates, sorting by relevance descending
        all_candidates = l_cands + k_cands
        all_candidates.sort(key=lambda c: c.relevance, reverse=True)
        selected_candidates = all_candidates[:top_k]

        result = Tier3RetrievalResult(
            candidates=selected_candidates,
            lancedb_count=l_raw,
            kuzu_count=k_raw,
            accepted_count=len(l_cands) + len(k_cands),
            rejected_count=(l_raw - len(l_cands)) + (k_raw - len(k_cands)),
            rejection_reasons=combined_reasons,
            lancedb_state=l_state,
            kuzu_state=k_state,
            retrieval_errors=l_errors + k_errors,
        )

        self._last_tier3_telemetry = result.to_telemetry()
        if telemetry is not None and isinstance(telemetry, dict):
            telemetry.update(result.to_telemetry())

        return result

    def _ensure_initialized(self) -> None:
        """Raise if service is not initialized."""
        if not self._initialized:
            raise CogneeServiceError(
                "CogneeService not initialized. Call initialize() first."
            )


class CogneeSemanticMemoryAdapter:
    """Dedicated adapter for mapping Cognee-derived memory items into canonical SemanticMemoryRecord entities.

    Invariants:
    - Never fabricates missing files, symbols, hashes, or repository identity.
    - Authoritative file paths, SHA-256 checksums, and symbols are validated against active repository manifest.
    - All mapped records are strictly Tier 4 / derived_projection (is_derived=True, is_authoritative=False).
    - Unanchored or corrupted records are rejected with explicit, observable rejection reasons.
    """

    @classmethod
    def map_item(
        cls,
        item: Any,
        manifest: Any,
        repository_id: Optional[str] = None,
        repository_fingerprint: Optional[str] = None,
    ) -> tuple[Optional[SemanticMemoryRecord], str]:
        """Convert a Cognee memory item into a validated SemanticMemoryRecord.

        Args:
            item: Raw Cognee result, dictionary, or RecallResult object.
            manifest: Active RepositoryManifest instance.
            repository_id: Optional repository identifier override/context.
            repository_fingerprint: Optional repository fingerprint override/context.

        Returns:
            Tuple of (Optional[SemanticMemoryRecord], reason_code).
        """
        if item is None:
            return None, "empty_item"

        if manifest is None or not hasattr(manifest, "files") or manifest.files is None:
            return None, "missing_manifest"

        # 1. Parse JSON item or raw_obj if present
        if isinstance(item, str) and item.strip().startswith("{") and item.strip().endswith("}"):
            try:
                import json
                parsed_item = json.loads(item)
                if isinstance(parsed_item, dict):
                    item = parsed_item
            except Exception:
                pass

        raw_obj = getattr(item, "raw", None) or (item.get("raw") if isinstance(item, dict) else None)
        if isinstance(raw_obj, str) and raw_obj.strip().startswith("{") and raw_obj.strip().endswith("}"):
            try:
                import json
                parsed_raw = json.loads(raw_obj)
                if isinstance(parsed_raw, dict):
                    raw_obj = parsed_raw
            except Exception:
                pass

        prov = (
            getattr(item, "provenance", None)
            or (item.get("provenance") if isinstance(item, dict) else None)
            or (getattr(raw_obj, "provenance", None) if raw_obj is not None else None)
            or (raw_obj.get("provenance") if isinstance(raw_obj, dict) else None)
        )

        # 2. Extract memory_id
        mem_id = (
            getattr(item, "memory_id", None)
            or getattr(item, "id", None)
            or (getattr(raw_obj, "memory_id", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "id", None) if raw_obj is not None else None)
            or (item.get("memory_id") if isinstance(item, dict) else None)
            or (item.get("id") if isinstance(item, dict) else None)
            or (raw_obj.get("memory_id") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("id") if isinstance(raw_obj, dict) else None)
        )

        # 3. Extract semantic_text
        semantic_text = (
            getattr(item, "semantic_text", None)
            or getattr(item, "text", None)
            or getattr(item, "content", None)
            or (getattr(raw_obj, "semantic_text", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "text", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "content", None) if raw_obj is not None else None)
            or (item.get("semantic_text") if isinstance(item, dict) else None)
            or (item.get("text") if isinstance(item, dict) else None)
            or (item.get("content") if isinstance(item, dict) else None)
            or (raw_obj.get("semantic_text") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("text") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("content") if isinstance(raw_obj, dict) else None)
        )
        if semantic_text is None:
            semantic_text = str(item)
        semantic_text = str(semantic_text).strip()
        if not semantic_text:
            return None, "empty_semantic_text"

        if not mem_id:
            mem_id = f"cognee_mem_{hashlib.sha256(semantic_text.encode('utf-8')).hexdigest()[:12]}"
        else:
            mem_id = str(mem_id)

        # 4. Extract repository identity & fingerprint
        manifest_ds = getattr(manifest, "dataset_name", None)
        target_repo_id = repository_id or manifest_ds

        item_repo_id = (
            getattr(item, "repository_id", None)
            or getattr(item, "dataset_name", None)
            or (getattr(prov, "repository_id", None) if prov else None)
            or (prov.get("repository_id") if isinstance(prov, dict) else None)
            or (getattr(raw_obj, "repository_id", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "dataset_name", None) if raw_obj is not None else None)
            or (item.get("repository_id") if isinstance(item, dict) else None)
            or (item.get("dataset_name") if isinstance(item, dict) else None)
            or (raw_obj.get("repository_id") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("dataset_name") if isinstance(raw_obj, dict) else None)
        )

        if item_repo_id and target_repo_id:
            clean_item_id = sanitize_dataset_name(str(item_repo_id))
            clean_target_id = sanitize_dataset_name(str(target_repo_id))
            if clean_item_id != clean_target_id and str(item_repo_id) != str(target_repo_id):
                return None, "cross_repository_id_mismatch"

        repo_id = str(target_repo_id or item_repo_id or getattr(manifest, "repo_path", "") or "")
        if not repo_id:
            return None, "missing_repository_provenance"

        manifest_fp = getattr(manifest, "repo_fingerprint", "") or ""
        target_fp = repository_fingerprint or manifest_fp

        item_fp = (
            getattr(item, "repository_fingerprint", None)
            or (getattr(prov, "repository_fingerprint", None) if prov else None)
            or (prov.get("repository_fingerprint") if isinstance(prov, dict) else None)
            or (getattr(raw_obj, "repository_fingerprint", None) if raw_obj is not None else None)
            or (item.get("repository_fingerprint") if isinstance(item, dict) else None)
            or (raw_obj.get("repository_fingerprint") if isinstance(raw_obj, dict) else None)
        )

        if item_fp and target_fp and str(item_fp) != str(target_fp):
            return None, "cross_repository_fingerprint_mismatch"

        repo_fp = str(target_fp or item_fp or "")
        if not repo_fp:
            return None, "missing_repository_fingerprint"

        # 5. Extract source files (mandatory)
        raw_files = (
            getattr(item, "source_files", None)
            or getattr(item, "source_file", None)
            or getattr(item, "file_paths", None)
            or getattr(item, "file_path", None)
            or (getattr(prov, "source_files", None) if prov else None)
            or (getattr(prov, "source_file", None) if prov else None)
            or (getattr(raw_obj, "source_files", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "source_file", None) if raw_obj is not None else None)
            or (item.get("source_files") if isinstance(item, dict) else None)
            or (item.get("source_file") if isinstance(item, dict) else None)
            or (item.get("file_paths") if isinstance(item, dict) else None)
            or (item.get("file_path") if isinstance(item, dict) else None)
            or (prov.get("source_files") if isinstance(prov, dict) else None)
            or (prov.get("source_file") if isinstance(prov, dict) else None)
            or (raw_obj.get("source_files") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("source_file") if isinstance(raw_obj, dict) else None)
        )

        meta = (
            getattr(item, "metadata", None)
            or (item.get("metadata") if isinstance(item, dict) else None)
            or (getattr(raw_obj, "metadata", None) if raw_obj is not None else None)
            or (raw_obj.get("metadata") if isinstance(raw_obj, dict) else None)
        )
        if isinstance(meta, str) and meta.strip().startswith("{") and meta.strip().endswith("}"):
            try:
                import json
                meta = json.loads(meta)
            except Exception:
                pass

        if not raw_files and isinstance(meta, dict):
            raw_files = (
                meta.get("source_files")
                or meta.get("source_file")
                or meta.get("file_paths")
                or meta.get("file_path")
                or meta.get("filePath")
                or meta.get("file_name")
                or meta.get("fileName")
                or meta.get("doc_path")
                or meta.get("path")
            )

        explicit_symbols_from_chunk: list[str] = []
        if not raw_files and semantic_text:
            text_str = str(semantic_text).strip()
            # Pattern 1: Bracketed files prefix e.g. "- [src/orders.py] ..." or "[src/orders.py, src/models.py]: ..."
            m1 = re.match(r"^[-*]?\s*\[\s*([^\]]+?)\s*\](?:\s*:\s*|\s+)?([\s\S]*)$", text_str)
            if m1:
                chunk_files_raw = m1.group(1).strip()
                remainder_text = m1.group(2).strip()
                tokens = [t.strip() for t in chunk_files_raw.split(",") if t.strip()]
                extracted_files: list[str] = []
                for tok in tokens:
                    sym_match = re.search(r"^(.*?)(?:#|::)([a-zA-Z_][a-zA-Z0-9_]*)$", tok)
                    if sym_match:
                        file_part = sym_match.group(1).strip()
                        sym_part = sym_match.group(2).strip()
                        if sym_part:
                            explicit_symbols_from_chunk.append(sym_part)
                    else:
                        file_part = tok
                    file_part = re.sub(r":\d+(?:-\d+)?$", "", file_part).strip()
                    file_part = file_part.strip("'\"`")
                    if file_part:
                        extracted_files.append(file_part)
                if extracted_files:
                    raw_files = extracted_files
                    if remainder_text:
                        semantic_text = remainder_text

            # Pattern 2: Header prefix e.g. "File: src/orders.py\n..." or "### File: src/orders.py\n..."
            if not raw_files:
                m2 = re.match(r"^(?:###?\s*)?(?:File|Source):\s*([^\n\r]+?)(?:\r?\n|\s*:\s*)([\s\S]*)$", text_str)
                if m2:
                    file_val = m2.group(1).strip().strip("'\"`")
                    remainder_text = m2.group(2).strip()
                    tokens = [t.strip().strip("'\"`") for t in file_val.split(",") if t.strip()]
                    if tokens:
                        raw_files = tokens
                        if remainder_text:
                            semantic_text = remainder_text

            # Pattern 3: Markdown link prefix e.g. "- [orders.py](src/orders.py): ..."
            if not raw_files:
                m3 = re.match(r"^[-*]?\s*\[(?:[^\]]+?)\]\(([^)]+?)\)(?:\s*:\s*|\s+)([\s\S]*)$", text_str)
                if m3:
                    file_val = m3.group(1).strip().strip("'\"`")
                    remainder_text = m3.group(2).strip()
                    if file_val:
                        raw_files = [file_val]
                        if remainder_text:
                            semantic_text = remainder_text

        source_files: list[str] = []
        if isinstance(raw_files, list):
            source_files = [str(f).strip().replace("\\", "/").lstrip("./") for f in raw_files if f and str(f).strip()]
        elif isinstance(raw_files, str) and raw_files.strip():
            source_files = [raw_files.strip().replace("\\", "/").lstrip("./")]

        if not source_files:
            return None, "missing_source_files"

        # 6. Extract source symbols
        raw_symbols = (
            getattr(item, "source_symbols", None)
            or getattr(item, "source_symbol", None)
            or getattr(item, "symbols", None)
            or (getattr(prov, "source_symbols", None) if prov else None)
            or (getattr(prov, "source_symbol", None) if prov else None)
            or (getattr(raw_obj, "source_symbols", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "source_symbol", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "symbols", None) if raw_obj is not None else None)
            or (item.get("source_symbols") if isinstance(item, dict) else None)
            or (item.get("source_symbol") if isinstance(item, dict) else None)
            or (item.get("symbols") if isinstance(item, dict) else None)
            or (prov.get("source_symbols") if isinstance(prov, dict) else None)
            or (prov.get("source_symbol") if isinstance(prov, dict) else None)
            or (raw_obj.get("source_symbols") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("source_symbol") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("symbols") if isinstance(raw_obj, dict) else None)
            or (meta.get("source_symbols") if isinstance(meta, dict) else None)
            or (meta.get("source_symbol") if isinstance(meta, dict) else None)
            or (meta.get("symbols") if isinstance(meta, dict) else None)
        )

        source_symbols: list[str] = []
        if isinstance(raw_symbols, list):
            source_symbols = [str(s).strip() for s in raw_symbols if s and str(s).strip()]
        elif isinstance(raw_symbols, str) and raw_symbols.strip():
            source_symbols = [raw_symbols.strip()]

        for sym in explicit_symbols_from_chunk:
            if sym not in source_symbols:
                source_symbols.append(sym)

        # 7. Extract raw source sha256 if supplied in item
        raw_shas = (
            getattr(item, "source_sha256", None)
            or (getattr(prov, "source_sha256", None) if prov else None)
            or (getattr(raw_obj, "source_sha256", None) if raw_obj is not None else None)
            or (item.get("source_sha256") if isinstance(item, dict) else None)
            or (prov.get("source_sha256") if isinstance(prov, dict) else None)
            or (raw_obj.get("source_sha256") if isinstance(raw_obj, dict) else None)
        )
        item_shas: list[str] = []
        if isinstance(raw_shas, list):
            item_shas = [str(s).strip() for s in raw_shas if s and str(s).strip()]
        elif isinstance(raw_shas, str) and raw_shas.strip():
            item_shas = [raw_shas.strip()]

        # 8. Authoritative Manifest Validation for Files & SHAs
        resolved_files: list[str] = []
        resolved_shas: list[str] = []

        for idx, f_path in enumerate(source_files):
            norm_path = f_path.replace("\\", "/").lstrip("./")
            if norm_path not in manifest.files:
                return None, f"unknown_source_file:{norm_path}"

            file_fp = manifest.files[norm_path]
            actual_sha = getattr(file_fp, "sha256", "") or ""

            if idx < len(item_shas) and item_shas[idx]:
                expected_sha = item_shas[idx]
                if actual_sha and expected_sha != actual_sha:
                    return None, f"source_sha256_stale:{norm_path}"

            resolved_files.append(norm_path)
            resolved_shas.append(actual_sha)

        # 9. Authoritative Manifest Validation for Symbols
        if source_symbols:
            known_symbols: set[str] = set()
            for f_path in resolved_files:
                file_fp = manifest.files.get(f_path)
                if file_fp and getattr(file_fp, "symbols", None):
                    known_symbols.update(file_fp.symbols)

            for sym in source_symbols:
                if sym not in known_symbols:
                    return None, f"unknown_symbol:{sym}"

        # 10. Extract relationship_kind & generated_at
        rel_kind = (
            getattr(item, "relationship_kind", None)
            or (getattr(prov, "relationship_kind", None) if prov else None)
            or (getattr(raw_obj, "relationship_kind", None) if raw_obj is not None else None)
            or (item.get("relationship_kind") if isinstance(item, dict) else None)
            or (prov.get("relationship_kind") if isinstance(prov, dict) else None)
            or (raw_obj.get("relationship_kind") if isinstance(raw_obj, dict) else None)
            or (getattr(prov, "kind", None) if prov else None)
            or (prov.get("kind") if isinstance(prov, dict) else None)
            or getattr(item, "kind", None)
            or (item.get("kind") if isinstance(item, dict) else None)
            or (getattr(raw_obj, "kind", None) if raw_obj is not None else None)
            or (raw_obj.get("kind") if isinstance(raw_obj, dict) else None)
        )

        gen_at = (
            getattr(item, "generated_at", None)
            or getattr(item, "indexed_at", None)
            or (getattr(prov, "indexed_at", None) if prov else None)
            or (getattr(raw_obj, "generated_at", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "indexed_at", None) if raw_obj is not None else None)
            or (item.get("generated_at") if isinstance(item, dict) else None)
            or (item.get("indexed_at") if isinstance(item, dict) else None)
            or (prov.get("indexed_at") if isinstance(prov, dict) else None)
            or (raw_obj.get("generated_at") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("indexed_at") if isinstance(raw_obj, dict) else None)
        )
        try:
            gen_at_float = float(gen_at) if gen_at is not None else time.time()
        except (ValueError, TypeError):
            gen_at_float = time.time()

        # 11. Extract confidence_score
        conf_score = (
            getattr(item, "confidence_score", None)
            or getattr(item, "score", None)
            or (getattr(prov, "confidence_score", None) if prov else None)
            or (getattr(raw_obj, "confidence_score", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "score", None) if raw_obj is not None else None)
            or (item.get("confidence_score") if isinstance(item, dict) else None)
            or (item.get("score") if isinstance(item, dict) else None)
            or (prov.get("confidence_score") if isinstance(prov, dict) else None)
            or (raw_obj.get("confidence_score") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("score") if isinstance(raw_obj, dict) else None)
        )
        try:
            conf_score_float = float(conf_score) if conf_score is not None else 1.0
        except (ValueError, TypeError):
            conf_score_float = 1.0

        # 12. Construct canonical SemanticMemoryRecord
        record = SemanticMemoryRecord(
            memory_id=mem_id,
            repository_id=repo_id,
            repository_fingerprint=manifest_fp or repo_fp,
            semantic_text=semantic_text,
            source_files=resolved_files,
            source_symbols=source_symbols,
            source_sha256=resolved_shas,
            relationship_kind=str(rel_kind) if rel_kind else None,
            generated_by="cognee_pipeline",
            generated_at=gen_at_float,
            evidence_status="derived_projection",
            is_derived=True,
            is_authoritative=False,
            confidence_score=conf_score_float,
        )

        return record, "valid"

    @classmethod
    def map_items(
        cls,
        items: list[Any],
        manifest: Any,
        repository_id: Optional[str] = None,
        repository_fingerprint: Optional[str] = None,
    ) -> list[SemanticMemoryRecord]:
        """Convert a batch of Cognee memory items into validated SemanticMemoryRecord entities.

        Invalid or unanchored items are excluded with observable warnings.
        """
        records: list[SemanticMemoryRecord] = []
        for i, it in enumerate(items):
            rec, reason = cls.map_item(
                item=it,
                manifest=manifest,
                repository_id=repository_id,
                repository_fingerprint=repository_fingerprint,
            )
            if rec is not None:
                records.append(rec)
            else:
                logger.warning(
                    "Cognee semantic memory item %d rejected: reason=%s",
                    i,
                    reason,
                )
        return records
