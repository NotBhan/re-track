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

import cognee

from app.application.domain.memory import MemoryProvenance, SemanticMemoryRecord
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

        # 1. Extract memory_id
        mem_id = (
            getattr(item, "memory_id", None)
            or getattr(item, "id", None)
            or (item.get("memory_id") if isinstance(item, dict) else None)
            or (item.get("id") if isinstance(item, dict) else None)
        )

        # 2. Extract semantic_text
        semantic_text = (
            getattr(item, "semantic_text", None)
            or getattr(item, "text", None)
            or getattr(item, "content", None)
            or (item.get("semantic_text") if isinstance(item, dict) else None)
            or (item.get("text") if isinstance(item, dict) else None)
            or (item.get("content") if isinstance(item, dict) else None)
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

        # 3. Extract raw container and provenance container if present
        raw_obj = getattr(item, "raw", None) or (item.get("raw") if isinstance(item, dict) else None)
        prov = (
            getattr(item, "provenance", None)
            or (item.get("provenance") if isinstance(item, dict) else None)
            or (getattr(raw_obj, "provenance", None) if raw_obj is not None else None)
            or (raw_obj.get("provenance") if isinstance(raw_obj, dict) else None)
        )

        # 4. Extract repository identity & fingerprint
        repo_id = (
            repository_id
            or getattr(item, "repository_id", None)
            or getattr(item, "dataset_name", None)
            or (getattr(prov, "repository_id", None) if prov else None)
            or (prov.get("repository_id") if isinstance(prov, dict) else None)
            or (getattr(raw_obj, "repository_id", None) if raw_obj is not None else None)
            or (getattr(raw_obj, "dataset_name", None) if raw_obj is not None else None)
            or (item.get("repository_id") if isinstance(item, dict) else None)
            or (item.get("dataset_name") if isinstance(item, dict) else None)
            or (raw_obj.get("repository_id") if isinstance(raw_obj, dict) else None)
            or (raw_obj.get("dataset_name") if isinstance(raw_obj, dict) else None)
            or getattr(manifest, "dataset_name", None)
            or getattr(manifest, "repo_path", None)
        )
        if not repo_id:
            return None, "missing_repository_provenance"
        repo_id = str(repo_id)

        manifest_fp = getattr(manifest, "repo_fingerprint", "") or ""
        repo_fp = (
            repository_fingerprint
            or getattr(item, "repository_fingerprint", None)
            or (getattr(prov, "repository_fingerprint", None) if prov else None)
            or (prov.get("repository_fingerprint") if isinstance(prov, dict) else None)
            or (getattr(raw_obj, "repository_fingerprint", None) if raw_obj is not None else None)
            or (item.get("repository_fingerprint") if isinstance(item, dict) else None)
            or (raw_obj.get("repository_fingerprint") if isinstance(raw_obj, dict) else None)
            or manifest_fp
        )
        if not repo_fp:
            return None, "missing_repository_fingerprint"
        repo_fp = str(repo_fp)

        # Check repository fingerprint match against manifest
        if manifest_fp and repo_fp != manifest_fp:
            return None, "cross_repository_fingerprint_mismatch"

        # Check repository ID match against manifest if manifest specifies dataset_name
        manifest_ds = getattr(manifest, "dataset_name", None)
        if manifest_ds and repo_id:
            if manifest_ds != repo_id and manifest_ds != repo_id.replace("/", "_"):
                return None, "cross_repository_id_mismatch"

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

        source_files: list[str] = []
        if isinstance(raw_files, list):
            source_files = [str(f).strip() for f in raw_files if f and str(f).strip()]
        elif isinstance(raw_files, str) and raw_files.strip():
            source_files = [raw_files.strip()]

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
        )

        source_symbols: list[str] = []
        if isinstance(raw_symbols, list):
            source_symbols = [str(s).strip() for s in raw_symbols if s and str(s).strip()]
        elif isinstance(raw_symbols, str) and raw_symbols.strip():
            source_symbols = [raw_symbols.strip()]

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

        # 11. Construct canonical SemanticMemoryRecord
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
