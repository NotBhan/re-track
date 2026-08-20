"""Repository indexing and summary use cases for RE:Track.

Coordinates incremental indexing, file filtering, manifest updates, and repository summaries.
All dependencies are explicitly injected via constructor capability ports.
"""

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Callable, Optional

from app.application.domain.repository import IndexedRepositoryRecord
from app.application.dto import (
    ErrorResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexedRepositoryListResponse,
    RepoArchInfo,
    RepoComponentInfo,
    RepositorySummaryInfo,
)
from app.application.ports.filesystem import FileSystemPort
from app.application.ports.indexing_service import IndexingServicePort
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.application.ports.summary_generator import SummaryGeneratorPort
from app.models.errors import CogneeServiceError

logger = logging.getLogger(__name__)


class IndexingUseCases:
    """Orchestrates repository indexing and summary queries."""

    def __init__(
        self,
        indexing_service: Optional[IndexingServicePort],
        indexing_lock: asyncio.Lock,
        ensure_services_fn: Callable[[], None],
        summary_generator: SummaryGeneratorPort,
        metadata_store: Optional[RepositoryMetadataPort] = None,
        filesystem: Optional[FileSystemPort] = None,
    ) -> None:
        self._indexing_service = indexing_service
        self._lock = indexing_lock
        self._ensure_services = ensure_services_fn
        self._summary_generator = summary_generator
        self._metadata_store = metadata_store
        self._fs = filesystem

    async def index_repository(
        self,
        request: IndexRepositoryRequest,
    ) -> IndexRepositoryResponse | ErrorResponse:
        """Index a repository into Cognee memory.

        Validates repository path exists, acquires indexing lock to prevent
        concurrent ingestion collisions, and delegates to IndexingService.
        """
        start = time.monotonic()
        logger.info(
            "use_case: index_repository() | path=%s | dataset=%s | batch=%d",
            request.repository_path,
            request.dataset_name,
            request.batch_size,
        )

        try:
            self._ensure_services()
            if self._indexing_service is None:
                raise CogneeServiceError("IndexingService is not initialized.")

            repo_path = Path(request.repository_path).resolve()
            if self._fs:
                if not self._fs.exists(repo_path):
                    raise ValueError(f"Repository path does not exist: {request.repository_path}")
                if not self._fs.is_dir(repo_path):
                    raise ValueError(f"Repository path is not a directory: {request.repository_path}")
            else:
                if not repo_path.exists():
                    raise ValueError(f"Repository path does not exist: {request.repository_path}")
                if not repo_path.is_dir():
                    raise ValueError(f"Repository path is not a directory: {request.repository_path}")

            if self._lock.locked():
                logger.warning("use_case: index_repository() rejected | another indexing job is in progress")
                return ErrorResponse(
                    error="ConcurrencyError",
                    message="Another repository is currently being indexed. Please wait for it to complete.",
                )

            async with self._lock:
                progress = await self._indexing_service.index_repository(
                    repo_path=repo_path,
                    dataset_name=request.dataset_name,
                    force_reindex=request.force_reindex,
                )

                # Extract languages, purpose, architecture, and components from summary generator
                languages: list[str] = []
                purpose = "Software Repository"
                arch_list: list[dict] = []
                comp_list: list[dict] = []
                call_graph_status = "not_analyzed"
                call_graph_error = None

                try:
                    all_files: list[Path] = []
                    if hasattr(self._indexing_service, "discover_files"):
                        res = self._indexing_service.discover_files(repo_path)
                        if isinstance(res, (list, tuple, set)):
                            all_files = list(res)
                    filtered: list[Path] = all_files
                    if hasattr(self._indexing_service, "filter_files"):
                        res_f = self._indexing_service.filter_files(all_files, repo_path)
                        if isinstance(res_f, (list, tuple, set)):
                            filtered = list(res_f)

                    if self._summary_generator and hasattr(self._summary_generator, "generate"):
                        summary = await self._summary_generator.generate(repo_path, filtered) if asyncio.iscoroutinefunction(self._summary_generator.generate) else self._summary_generator.generate(repo_path, filtered)

                        if summary and hasattr(summary, "technology_stack") and summary.technology_stack:
                            languages = [lang.name if hasattr(lang, "name") else str(lang) for lang in getattr(summary.technology_stack, "languages", [])]
                            if getattr(summary.technology_stack, "frameworks", None):
                                languages.extend([f.name if hasattr(f, "name") else str(f) for f in summary.technology_stack.frameworks])

                        purpose = getattr(summary, "project_purpose", "Software Repository")

                        if summary and hasattr(summary, "architecture") and summary.architecture:
                            arch = summary.architecture
                            if hasattr(arch, "layers") and arch.layers:
                                arch_list = [{"icon": "Layers", "label": layer} for layer in arch.layers]
                            elif isinstance(arch, list):
                                arch_list = [{"icon": a.get("icon", "Layers") if isinstance(a, dict) else getattr(a, "icon", "Layers"), "label": a.get("label", str(a)) if isinstance(a, dict) else getattr(a, "label", str(a))} for a in arch]
                            elif hasattr(arch, "pattern") and arch.pattern:
                                arch_list = [{"icon": "Layers", "label": arch.pattern}]

                        if summary and hasattr(summary, "key_components") and summary.key_components:
                            for c in summary.key_components:
                                c_path = c.name if hasattr(c, "name") else c.path if hasattr(c, "path") else c.get("path", str(c)) if isinstance(c, dict) else str(c)
                                comp_list.append({"path": c_path, "centrality": "core"})

                        call_graph_status = getattr(summary, "call_graph_status", "not_analyzed")
                        call_graph_error = getattr(summary, "call_graph_error", None)
                except Exception as e:
                    logger.warning("Failed to extract repository summary: %s", e)

                # Calculate memory size representation
                mem_size = f"{max(1, progress.processed_files * 4)} KB"

                # Persist repository metadata using typed domain record
                if self._metadata_store:
                    try:
                        existing_record = self._metadata_store.get_by_path(str(repo_path))
                        all_records = self._metadata_store.load_all()
                        record_id = existing_record.id if existing_record else str(len(all_records) + 1)

                        record = IndexedRepositoryRecord(
                            id=record_id,
                            name=request.dataset_name or repo_path.name,
                            path=str(repo_path),
                            languages=languages or ["Code"],
                            file_count=progress.processed_files,
                            memory_size=mem_size,
                            last_indexed=datetime.now(timezone.utc).isoformat(),
                            purpose=purpose,
                            architecture=arch_list,
                            components=comp_list,
                            call_graph_status=call_graph_status,
                            call_graph_error=call_graph_error,
                        )
                        self._metadata_store.upsert(record)
                    except Exception as em:
                        logger.warning("Failed to persist metadata record: %s", em)

                response = IndexRepositoryResponse(
                    success=progress.failed_files == 0,
                    repository_path=str(repo_path),
                    dataset_name=request.dataset_name,
                    total_files=progress.total_files,
                    processed_files=progress.processed_files,
                    failed_files=progress.failed_files,
                    total_batches=progress.total_batches,
                    failed_paths=progress.failed_paths,
                    summary=progress.summary(),
                )

                elapsed = time.monotonic() - start
                logger.info(
                    "use_case: index_repository() complete | %s | %.2fs",
                    progress.summary(),
                    elapsed,
                )
                return response

        except ValueError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: index_repository() validation error | %.2fs | %s", elapsed, e)
            raise
        except CogneeServiceError as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: index_repository() service error | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Indexing failed: {e}",
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: index_repository() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Indexing failed: {e}",
            )

    async def get_repository_summaries(self) -> IndexedRepositoryListResponse | ErrorResponse:
        """Return list of all indexed repositories with metadata for UI cards."""
        start = time.monotonic()
        logger.info("use_case: get_repository_summaries()")

        try:
            records = self._metadata_store.load_all() if self._metadata_store else []
            repos: list[RepositorySummaryInfo] = []

            for r in records:
                arch_objs = [
                    RepoArchInfo(icon=a.get("icon", "Layers"), label=a.get("label", ""))
                    for a in r.architecture
                ]
                comp_objs = [
                    RepoComponentInfo(path=c.get("path", ""), centrality=c.get("centrality", "core"))
                    for c in r.components
                ]

                repos.append(
                    RepositorySummaryInfo(
                        id=str(r.id),
                        name=r.name,
                        path=r.path,
                        languages=r.languages,
                        file_count=r.file_count,
                        memory_size=r.memory_size,
                        last_indexed=r.last_indexed,
                        purpose=r.purpose,
                        architecture=arch_objs,
                        components=comp_objs,
                        call_graph_status=r.call_graph_status,
                        call_graph_error=r.call_graph_error,
                    )
                )

            response = IndexedRepositoryListResponse(
                success=True,
                repositories=repos,
                total_count=len(repos),
            )

            elapsed = time.monotonic() - start
            logger.info("use_case: get_repository_summaries() complete | count=%d | %.2fs", len(repos), elapsed)
            return response

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_repository_summaries() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get repository summaries: {e}",
            )
