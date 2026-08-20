"""Repository indexing and summary use cases for RE:Track.

Coordinates incremental indexing, file filtering, manifest updates, and repository summaries.
All dependencies are explicitly injected via constructor.
"""

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Callable, Optional

from app.application.dto import (
    ErrorResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexedRepositoryListResponse,
    RepoArchInfo,
    RepoComponentInfo,
    RepositorySummaryInfo,
)
from app.models.errors import CogneeServiceError
from app.services.indexing_service import IndexingService
from app.services.repository_metadata_store import (
    JsonRepositoryMetadataStore,
    RepositoryMetadataStore,
)
from app.services.repository_summary import RepositorySummaryGenerator

logger = logging.getLogger(__name__)


class IndexingUseCases:
    """Orchestrates repository indexing and summary queries."""

    def __init__(
        self,
        indexing_service: Optional[IndexingService],
        indexing_lock: asyncio.Lock,
        ensure_services_fn: Callable[[], None],
        summary_generator: RepositorySummaryGenerator,
        metadata_store: Optional[RepositoryMetadataStore] = None,
    ) -> None:
        self._indexing_service = indexing_service
        self._lock = indexing_lock
        self._ensure_services = ensure_services_fn
        self._summary_generator = summary_generator
        self._metadata_store = metadata_store or JsonRepositoryMetadataStore()

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

                # Persist repository metadata using abstracted metadata store
                store = self._metadata_store.load()
                repos = store.get("repositories", [])

                # Extract languages, purpose, architecture, and components from summary generator
                languages: list[str] = []
                purpose = "Software Repository"
                arch_list: list[dict] = []
                comp_list: list[dict] = []
                call_graph_status = "not_analyzed"
                call_graph_error = None

                try:
                    all_files = self._indexing_service.discover_files(repo_path)
                    filtered = self._indexing_service.filter_files(all_files, repo_path)
                    summary = self._summary_generator.generate(repo_path, filtered)
                    languages = [lang.name for lang in summary.technology_stack.languages]
                    if summary.technology_stack.frameworks:
                        languages.extend(summary.technology_stack.frameworks)
                    purpose = summary.project_purpose
                    arch_list = [{"icon": a.icon, "label": a.label} for a in summary.architecture]
                    comp_list = [{"path": c.path, "centrality": c.centrality} for c in summary.key_components]
                    call_graph_status = summary.call_graph_status
                    call_graph_error = summary.call_graph_error
                except Exception as e:
                    logger.warning("Failed to extract repository summary: %s", e)

                # Calculate memory size representation
                mem_size = f"{max(1, progress.processed_files * 4)} KB"

                # Update or append repo entry
                existing = next(
                    (r for r in repos if r.get("path") == str(repo_path)),
                    None,
                )
                repo_entry = {
                    "id": existing["id"] if existing else str(len(repos) + 1),
                    "name": request.dataset_name or repo_path.name,
                    "path": str(repo_path),
                    "languages": languages or ["Code"],
                    "file_count": progress.processed_files,
                    "memory_size": mem_size,
                    "last_indexed": datetime.now(timezone.utc).isoformat(),
                    "purpose": purpose,
                    "architecture": arch_list,
                    "components": comp_list,
                    "call_graph_status": call_graph_status,
                    "call_graph_error": call_graph_error,
                }

                if existing:
                    repos[repos.index(existing)] = repo_entry
                else:
                    repos.append(repo_entry)

                store["repositories"] = repos
                self._metadata_store.save(store)

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
            store = self._metadata_store.load()
            repos_data = store.get("repositories", [])
            repos: list[RepositorySummaryInfo] = []

            for r in repos_data:
                arch_objs = [
                    RepoArchInfo(icon=a.get("icon", "Layers"), label=a.get("label", ""))
                    for a in r.get("architecture", [])
                ]
                comp_objs = [
                    RepoComponentInfo(path=c.get("path", ""), centrality=c.get("centrality", "core"))
                    for c in r.get("components", [])
                ]

                repos.append(
                    RepositorySummaryInfo(
                        id=str(r.get("id", "")),
                        name=r.get("name", ""),
                        path=r.get("path", ""),
                        languages=r.get("languages", ["Code"]),
                        file_count=r.get("file_count", 0),
                        memory_size=r.get("memory_size", "0 KB"),
                        last_indexed=r.get("last_indexed", ""),
                        purpose=r.get("purpose", ""),
                        architecture=arch_objs,
                        components=comp_objs,
                        call_graph_status=r.get("call_graph_status", "not_analyzed"),
                        call_graph_error=r.get("call_graph_error"),
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
