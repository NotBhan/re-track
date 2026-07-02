"""Async API commands for AndesContext.

Thin command layer that validates input, delegates to services,
and returns serializable responses. No business logic lives here.

Every command:
- Validates request parameters
- Logs the request with timing
- Delegates to the appropriate service
- Returns a Pydantic response model
- Catches and wraps errors in ErrorResponse
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from app.api.schemas import (
    BackendStatusResponse,
    BenchmarkResultItem,
    BenchmarkSuiteResponse,
    ContextPackageAppendRequest,
    ContextPackageListResponse,
    ContextPackageResponse,
    ContextPackageSaveRequest,
    ContextResponse,
    DashboardStats,
    DatasetInfo,
    DatasetListResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    HealthResponse,
    IndexedRepositoryListResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    MemoryStatsResponse,
    RepoArchInfo,
    RepoComponentInfo,
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryResponse,
    RepositorySummaryInfo,
    ScanResultResponse,
)
from app.config.settings import Settings, get_settings
from app.models.errors import AndesContextError, CogneeServiceError
from app.models.repository import Repository
from app.services.context_service import ContextService
from app.services.context_package_repository import JsonContextPackageRepository
from app.services.cognee_service import CogneeService
from app.services.indexing_service import IndexingService
from app.models.context_package import SavedContextPackage
from app.services.repository_manager import RepositoryManager
from app.services.repository_summary import RepositorySummaryGenerator

logger = logging.getLogger(__name__)

# Backend version
VERSION = "0.1.0"

# Persistent store for indexed repository metadata
_REPO_STORE_PATH = Path.home() / ".andes" / "indexed_repos.json"


# --- Repo metadata store ---


def _load_repo_store() -> dict:
    """Load the indexed repos store from disk."""
    if _REPO_STORE_PATH.exists():
        try:
            return json.loads(_REPO_STORE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return {"repositories": []}
    return {"repositories": []}


def _save_repo_store(data: dict) -> None:
    """Persist the indexed repos store to disk."""
    _REPO_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPO_STORE_PATH.write_text(json.dumps(data, indent=2))


# --- Service singletons (lazy-initialized) ---

_cognee_service: Optional[CogneeService] = None
_indexing_service: Optional[IndexingService] = None
_context_service: Optional[ContextService] = None
_settings: Optional[Settings] = None
_manager = RepositoryManager()


def _ensure_services() -> None:
    """Raise if any service is not initialized."""
    if _cognee_service is None or _indexing_service is None or _context_service is None:
        raise CogneeServiceError(
            "Backend services not initialized. Call initialize_backend() first."
        )


async def initialize_backend(settings: Optional[Settings] = None) -> None:
    """Initialize all backend services.

    Args:
        settings: Optional settings override. Uses default if None.
    """
    global _cognee_service, _indexing_service, _context_service, _settings

    _settings = settings or get_settings()
    _cognee_service = CogneeService(_settings)
    await _cognee_service.initialize()

    _indexing_service = IndexingService(_cognee_service)
    _context_service = ContextService(_cognee_service)

    logger.info("Backend services initialized")


# --- Commands ---


async def health() -> HealthResponse | ErrorResponse:
    """Check system health: Cognee, Ollama, and storage."""
    start = time.monotonic()
    logger.info("command: health()")

    try:
        settings = _settings or get_settings()
        cognee = _cognee_service

        ollama_reachable = settings.ollama.check_connection()
        cognee_ok = cognee is not None and cognee.is_initialized

        status = "ok" if (ollama_reachable and cognee_ok) else "degraded"

        response = HealthResponse(
            status=status,
            ollama_reachable=ollama_reachable,
            cognee_initialized=cognee_ok,
            version=VERSION,
        )

        elapsed = time.monotonic() - start
        logger.info("command: health() | status=%s | %.2fs", response.status, elapsed)
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: health() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Health check failed: {e}",
        )


async def list_datasets() -> DatasetListResponse | ErrorResponse:
    """List all datasets stored in Cognee memory.

    Returns an empty list gracefully if Cognee is not initialized.
    """
    start = time.monotonic()
    logger.info("command: list_datasets()")

    try:
        cognee = _cognee_service
        if cognee is None or not cognee.is_initialized:
            logger.info("command: list_datasets() | cognee not initialized, returning empty")
            return DatasetListResponse(success=True, datasets=[], total_count=0)

        raw_datasets = await cognee.list_datasets()

        datasets = [
            DatasetInfo(
                id=ds["id"],
                name=ds["name"],
                created_at=ds["created_at"],
                file_count=ds["file_count"],
            )
            for ds in raw_datasets
        ]

        response = DatasetListResponse(
            success=True,
            datasets=datasets,
            total_count=len(datasets),
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: list_datasets() complete | count=%d | %.2fs",
            len(datasets),
            elapsed,
        )
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: list_datasets() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to list datasets: {e}",
        )


async def get_backend_status() -> BackendStatusResponse | ErrorResponse:
    """Return detailed backend status including configuration and datasets."""
    start = time.monotonic()
    logger.info("command: get_backend_status()")

    try:
        settings = _settings or get_settings()
        cognee = _cognee_service

        ollama_reachable = settings.ollama.check_connection()
        cognee_ok = cognee is not None and cognee.is_initialized
        status = "ok" if (ollama_reachable and cognee_ok) else "degraded"

        response = BackendStatusResponse(
            status=status,
            ollama_reachable=ollama_reachable,
            ollama_host=settings.ollama.host,
            ollama_port=settings.ollama.port,
            llm_model=settings.ollama.llm_model,
            embedding_model=settings.ollama.embedding_model,
            vector_db=settings.storage.vector_db,
            graph_db=settings.storage.graph_db,
            relational_db=settings.storage.relational_db,
            data_root=str(settings.storage.data_root),
            system_root=str(settings.storage.system_root),
            cognee_initialized=cognee_ok,
        )

        elapsed = time.monotonic() - start
        logger.info("command: get_backend_status() complete | %.2fs", elapsed)
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_backend_status() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Status check failed: {e}",
        )


async def index_repository(
    request: IndexRepositoryRequest,
) -> IndexRepositoryResponse | ErrorResponse:
    """Index a repository into Cognee memory.

    Validates the repository path exists and is a directory,
    then delegates to IndexingService.
    """
    start = time.monotonic()
    logger.info(
        "command: index_repository() | repo=%s | dataset=%s",
        request.repository_path,
        request.dataset_name,
    )

    try:
        _ensure_services()

        repo_path = Path(request.repository_path).resolve()
        if not repo_path.exists():
            raise ValueError(f"Repository path does not exist: {request.repository_path}")
        if not repo_path.is_dir():
            raise ValueError(f"Path is not a directory: {request.repository_path}")

        progress = await _indexing_service.index_repository(
            repo_path=repo_path,
            dataset_name=request.dataset_name,
        )

        # Persist repository metadata after successful indexing
        if progress.failed_files == 0:
            _persist_repo_metadata(repo_path, progress.processed_files)

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
            "command: index_repository() complete | files=%d | %.2fs",
            progress.processed_files,
            elapsed,
        )
        return response

    except ValueError as e:
        elapsed = time.monotonic() - start
        logger.error("command: index_repository() validation error | %.2fs | %s", elapsed, e)
        raise
    except CogneeServiceError as e:
        elapsed = time.monotonic() - start
        logger.error("command: index_repository() service error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Indexing failed: {e}",
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: index_repository() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Indexing failed: {e}",
        )


async def generate_context(
    request: GenerateContextRequest,
) -> ContextResponse | ErrorResponse:
    """Generate a Context Package for a developer task.

    Validates query is non-empty, datasets are provided,
    then delegates to ContextService.
    """
    start = time.monotonic()
    logger.info(
        "command: generate_context() | task=%s | datasets=%s | top_k=%d",
        request.task[:80],
        request.datasets,
        request.top_k,
    )

    try:
        _ensure_services()

        if not request.task.strip():
            raise ValueError("Task must not be empty")
        if not request.datasets:
            raise ValueError("at least one dataset must be provided")

        package = await _context_service.generate_context_package(
            task=request.task,
            datasets=request.datasets,
            top_k=request.top_k,
        )

        response = ContextResponse(
            success=True,
            task=package.task,
            objective=package.objective,
            markdown=package.markdown,
            section_count=package.section_count,
            source_count=package.source_count,
            token_estimate=package.token_estimate,
            dataset=package.dataset,
            retrieved_memories=package.metadata.retrieved_memory_count if package.metadata else 0,
            deduplicated_memories=package.metadata.deduplicated_count if package.metadata else 0,
            compressed_memories=package.metadata.compressed_count if package.metadata else 0,
            compression_ratio=package.metadata.compression_ratio if package.metadata else 1.0,
            retrieval_time_ms=package.metadata.retrieval_time_ms if package.metadata else 0,
            total_time_ms=package.metadata.total_time_ms if package.metadata else 0,
            reference_count=len(package.references),
            section_headings=[s.heading for s in package.sections],
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: generate_context() complete | sources=%d | ~%d tokens | %.2fs",
            package.source_count,
            package.token_estimate,
            elapsed,
        )
        return response

    except ValueError as e:
        elapsed = time.monotonic() - start
        logger.error("command: generate_context() validation error | %.2fs | %s", elapsed, e)
        raise
    except CogneeServiceError as e:
        elapsed = time.monotonic() - start
        logger.error("command: generate_context() service error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Context generation failed: {e}",
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: generate_context() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Context generation failed: {e}",
        )


async def forget_dataset(
    request: ForgetDatasetRequest,
) -> None | ErrorResponse:
    """Forget (delete) a dataset or specific data item from Cognee memory.

    Validates that at least one identifier is provided,
    then delegates to CogneeService.

    Returns None on success, ErrorResponse on failure.
    """
    start = time.monotonic()
    logger.info(
        "command: forget_dataset() | dataset=%s | dataset_id=%s | data_id=%s",
        request.dataset,
        request.dataset_id,
        request.data_id,
    )

    try:
        _ensure_services()

        if not any([request.dataset, request.dataset_id, request.data_id]):
            raise ValueError("At least one of dataset, dataset_id, or data_id must be provided")

        await _cognee_service.forget(
            dataset=request.dataset,
            dataset_id=request.dataset_id,
            data_id=request.data_id,
        )

        elapsed = time.monotonic() - start
        logger.info("command: forget_dataset() complete | %.2fs", elapsed)
        return None

    except ValueError as e:
        elapsed = time.monotonic() - start
        logger.error("command: forget_dataset() validation error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=str(e),
        )
    except CogneeServiceError as e:
        elapsed = time.monotonic() - start
        logger.error("command: forget_dataset() service error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Forget operation failed: {e}",
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: forget_dataset() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Forget operation failed: {e}",
        )


def _persist_repo_metadata(repo_path: Path, file_count: int) -> None:
    """Persist repository metadata to the indexed repos store after indexing."""
    try:
        generator = RepositorySummaryGenerator()
        # Collect indexed files by scanning the repo path
        indexed_files = [
            f for f in repo_path.rglob("*")
            if f.is_file() and not f.name.startswith(".")
        ]
        summary = generator.generate(repo_path, indexed_files)

        repo_id = str(repo_path).replace("/", "_").replace("\\", "_").replace(":", "_")

        architecture = None
        if summary.architecture.pattern:
            arch_icons = {
                "layered": "layers",
                "microservice": "cloud",
                "monolith": "box",
            }
            architecture = [
                RepoArchInfo(
                    icon=arch_icons.get(summary.architecture.pattern, "code"),
                    label=summary.architecture.pattern.title(),
                )
            ]

        components = None
        if summary.key_components:
            components = [
                RepoComponentInfo(
                    path=comp.name,
                    centrality="core" if i < 3 else "peripheral",
                )
                for i, comp in enumerate(summary.key_components)
            ]

        entry = {
            "id": repo_id,
            "name": repo_path.name,
            "path": str(repo_path),
            "languages": summary.technology_stack.languages,
            "file_count": file_count,
            "memory_size": f"{len(indexed_files)} files",
            "last_indexed": summary.generated_at,
            "purpose": summary.project_purpose,
            "architecture": [a.model_dump() for a in architecture] if architecture else None,
            "components": [c.model_dump() for c in components] if components else None,
        }

        store = _load_repo_store()
        # Update existing entry or add new one
        repos = store.get("repositories", [])
        for i, r in enumerate(repos):
            if r.get("id") == repo_id:
                repos[i] = entry
                break
        else:
            repos.append(entry)
        store["repositories"] = repos
        _save_repo_store(store)
        logger.info("Persisted repo metadata for %s", repo_path)
    except Exception as e:
        logger.warning("Failed to persist repo metadata: %s", e)


async def get_repository_summaries() -> RepositoryListResponse | ErrorResponse:
    """List all indexed repositories with metadata."""
    start = time.monotonic()
    logger.info("command: get_repository_summaries()")

    try:
        store = _load_repo_store()
        repos_data = store.get("repositories", [])

        repositories = [
            RepositorySummaryInfo(
                id=r["id"],
                name=r["name"],
                path=r["path"],
                languages=r.get("languages", []),
                file_count=r.get("file_count", 0),
                memory_size=r.get("memory_size", "0 B"),
                last_indexed=r["last_indexed"],
                purpose=r.get("purpose"),
                architecture=[RepoArchInfo(**a) for a in r["architecture"]] if r.get("architecture") else None,
                components=[RepoComponentInfo(**c) for c in r["components"]] if r.get("components") else None,
            )
            for r in repos_data
        ]

        response = IndexedRepositoryListResponse(
            success=True,
            repositories=repositories,
            total_count=len(repositories),
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: get_repository_summaries() complete | count=%d | %.2fs",
            len(repositories),
            elapsed,
        )
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_repository_summaries() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to list repositories: {e}",
        )


async def get_dashboard_stats() -> DashboardStats | ErrorResponse:
    """Return aggregate dashboard statistics from the indexed repos store."""
    start = time.monotonic()
    logger.info("command: get_dashboard_stats()")

    try:
        store = _load_repo_store()
        repos = store.get("repositories", [])

        indexed_repos = len(repos)
        total_files = sum(r.get("file_count", 0) for r in repos)
        total_embeddings = total_files * 5

        last_repo = ""
        last_time = ""
        if repos:
            latest = max(repos, key=lambda r: r.get("last_indexed", ""))
            last_repo = latest.get("name", "")
            last_time = latest.get("last_indexed", "")

        response = DashboardStats(
            success=True,
            indexed_repos=indexed_repos,
            total_files=total_files,
            total_embeddings=total_embeddings,
            packages_generated=0,
            avg_gen_time_ms=0.0,
            last_indexed_repo=last_repo,
            last_indexed_time=last_time,
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: get_dashboard_stats() complete | repos=%d | files=%d | %.2fs",
            indexed_repos,
            total_files,
            elapsed,
        )
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_dashboard_stats() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to get dashboard stats: {e}",
        )


async def get_memory_stats() -> MemoryStatsResponse | ErrorResponse:
    """Return memory topology statistics for the memory page sidebar.

    Aggregates total size from indexed repos, counts datasets,
    and queries graph engine for node/edge counts.
    """
    start = time.monotonic()
    logger.info("command: get_memory_stats()")

    try:
        store = _load_repo_store()
        repos = store.get("repositories", [])

        # Count datasets from indexed repos
        dataset_count = len(repos)

        # Calculate total size display from memory_size values
        total_size_display = "N/A"
        if repos:
            # Sum up file counts from memory_size strings (e.g., "42 files")
            total_files = 0
            for repo in repos:
                memory_size = repo.get("memory_size", "0 files")
                try:
                    # Extract number from "X files" format
                    count = int(memory_size.split()[0])
                    total_files += count
                except (ValueError, IndexError):
                    # If parsing fails, try to get file_count directly
                    total_files += repo.get("file_count", 0)
            if total_files > 0:
                total_size_display = f"{total_files} files"

        # Get graph stats from CogneeService
        graph_nodes = 0
        graph_edges = 0
        if _cognee_service and _cognee_service.is_initialized:
            try:
                graph_stats = await _cognee_service.get_graph_stats()
                graph_nodes = graph_stats.get("graph_nodes", 0)
                graph_edges = graph_stats.get("graph_edges", 0)
            except Exception as e:
                logger.warning("Failed to get graph stats: %s", e)

        response = MemoryStatsResponse(
            success=True,
            total_size_display=total_size_display,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
            dataset_count=dataset_count,
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: get_memory_stats() complete | datasets=%d | nodes=%d | edges=%d | %.2fs",
            dataset_count,
            graph_nodes,
            graph_edges,
            elapsed,
        )
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_memory_stats() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to get memory stats: {e}",
        )


async def run_benchmark() -> BenchmarkSuiteResponse | ErrorResponse:
    """Run a benchmark suite against the generate_context endpoint."""
    start = time.monotonic()
    logger.info("command: run_benchmark()")

    try:
        from app.api.benchmarks import run_benchmark_suite

        _ensure_services()
        suite = await run_benchmark_suite()

        response = BenchmarkSuiteResponse(
            success=True,
            results=[
                BenchmarkResultItem(
                    question=r.question,
                    latency_ms=r.latency_ms,
                    token_count=r.token_count,
                    section_count=r.section_count,
                    retrieved_memories=r.retrieved_memories,
                    compression_ratio=r.compression_ratio,
                    quality_score=r.quality_score,
                    passed=r.passed,
                )
                for r in suite.results
            ],
            avg_latency_ms=suite.avg_latency_ms,
            avg_tokens=suite.avg_tokens,
            pass_rate=suite.pass_rate,
            total_questions=suite.total_questions,
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: run_benchmark() complete | questions=%d | pass_rate=%.1f%% | %.2fs",
            suite.total_questions,
            suite.pass_rate,
            elapsed,
        )
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: run_benchmark() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Benchmark failed: {e}",
        )


# --- Repository Manager Commands ---


def _repo_to_response(repo: Repository) -> RepositoryResponse:
    """Convert a Repository dataclass to a Pydantic response model."""
    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        source_type=repo.source_type,
        source_url=repo.source_url,
        local_path=repo.local_path,
        branch=repo.branch,
        commit_hash=repo.commit_hash,
        status=repo.status,
        languages=repo.languages,
        frameworks=repo.frameworks,
        file_count=repo.file_count,
        size_bytes=repo.size_bytes,
        indexed_at=repo.indexed_at,
        error_message=repo.error_message,
    )


async def list_repositories() -> RepositoryListResponse | ErrorResponse:
    """List all managed repositories."""
    start = time.monotonic()
    logger.info("command: list_repositories()")

    try:
        repos = _manager.list_repositories()
        response = RepositoryListResponse(
            success=True,
            repositories=[_repo_to_response(r) for r in repos],
            total_count=len(repos),
        )
        elapsed = time.monotonic() - start
        logger.info(
            "command: list_repositories() complete | count=%d | %.2fs",
            len(repos),
            elapsed,
        )
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: list_repositories() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to list repositories: {e}",
        )


async def create_repository(
    request: RepositoryCreateRequest,
) -> RepositoryResponse | ErrorResponse:
    """Import a new repository from GitHub or a local path."""
    start = time.monotonic()
    logger.info(
        "command: create_repository() | source_type=%s | url=%s | path=%s",
        request.source_type,
        request.source_url,
        request.local_path,
    )

    try:
        repo = _manager.import_repository(
            source_type=request.source_type,
            source_url=request.source_url,
            local_path=request.local_path,
            name=request.name,
        )
        response = _repo_to_response(repo)
        elapsed = time.monotonic() - start
        logger.info(
            "command: create_repository() complete | id=%s | %.2fs",
            repo.id,
            elapsed,
        )
        return response

    except (ValueError, KeyError) as e:
        elapsed = time.monotonic() - start
        logger.error("command: create_repository() validation error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=str(e),
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: create_repository() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to create repository: {e}",
        )


async def scan_repository(repo_id: str) -> ScanResultResponse | ErrorResponse:
    """Scan a repository for languages, frameworks, and file statistics."""
    start = time.monotonic()
    logger.info("command: scan_repository() | repo_id=%s", repo_id)

    try:
        result = _manager.scan_repository(repo_id)
        response = ScanResultResponse(
            success=True,
            languages=result.languages,
            frameworks=result.frameworks,
            file_count=result.file_count,
            size_bytes=result.size_bytes,
            ignored_dirs=result.ignored_dirs,
            estimated_index_time_ms=float(result.estimated_index_time_ms),
        )
        elapsed = time.monotonic() - start
        logger.info(
            "command: scan_repository() complete | files=%d | %.2fs",
            result.file_count,
            elapsed,
        )
        return response

    except (KeyError, FileNotFoundError) as e:
        elapsed = time.monotonic() - start
        logger.error("command: scan_repository() error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=str(e),
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: scan_repository() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Scan failed: {e}",
        )


async def delete_repository(repo_id: str) -> dict | ErrorResponse:
    """Delete a managed repository."""
    start = time.monotonic()
    logger.info("command: delete_repository() | repo_id=%s", repo_id)

    try:
        _manager.delete_repository(repo_id)
        elapsed = time.monotonic() - start
        logger.info("command: delete_repository() complete | %.2fs", elapsed)
        return {"success": True, "message": f"Repository {repo_id} deleted"}

    except KeyError as e:
        elapsed = time.monotonic() - start
        logger.error("command: delete_repository() error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=str(e),
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: delete_repository() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to delete repository: {e}",
        )


# --- Context Package Commands ---

_pkg_repo = JsonContextPackageRepository()


def _pkg_to_response(pkg: SavedContextPackage) -> ContextPackageResponse:
    """Convert a SavedContextPackage dataclass to a Pydantic response model."""
    return ContextPackageResponse(
        id=pkg.id,
        name=pkg.name,
        task=pkg.task,
        objective=pkg.objective,
        repository_id=pkg.repository_id,
        repository_name=pkg.repository_name,
        repository_branch=pkg.repository_branch,
        repository_commit=pkg.repository_commit,
        indexing_version=pkg.indexing_version,
        markdown=pkg.markdown,
        section_count=pkg.section_count,
        token_estimate=pkg.token_estimate,
        retrieved_memories=pkg.retrieved_memories,
        deduplicated_memories=pkg.deduplicated_memories,
        compression_ratio=pkg.compression_ratio,
        total_time_ms=pkg.total_time_ms,
        created_at=pkg.created_at,
        updated_at=pkg.updated_at,
        tags=pkg.tags,
    )


async def save_context_package(
    request: ContextPackageSaveRequest,
) -> ContextPackageResponse | ErrorResponse:
    """Save a context package."""
    import uuid
    from datetime import datetime, timezone

    start = time.monotonic()
    logger.info("command: save_context_package() | name=%s", request.name)

    try:
        now = datetime.now(timezone.utc).isoformat()
        pkg_id = str(uuid.uuid4())

        pkg = SavedContextPackage(
            id=pkg_id,
            name=request.name,
            task=request.task,
            objective=request.objective,
            repository_id=request.repository_id,
            repository_name=request.repository_name,
            repository_branch=request.repository_branch,
            repository_commit=request.repository_commit,
            indexing_version=request.indexing_version,
            markdown=request.markdown,
            section_count=request.section_count,
            token_estimate=request.token_estimate,
            retrieved_memories=request.retrieved_memories,
            deduplicated_memories=request.deduplicated_memories,
            compression_ratio=request.compression_ratio,
            total_time_ms=int(request.total_time_ms),
            created_at=now,
            updated_at=now,
            tags=request.tags,
        )

        saved = await _pkg_repo.save(pkg)
        elapsed = time.monotonic() - start
        logger.info("command: save_context_package() complete | id=%s | %.2fs", saved.id, elapsed)
        return _pkg_to_response(saved)

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: save_context_package() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to save context package: {e}",
        )


async def list_context_packages() -> ContextPackageListResponse | ErrorResponse:
    """List all saved context packages."""
    start = time.monotonic()
    logger.info("command: list_context_packages()")

    try:
        packages = await _pkg_repo.list_all()
        packages.sort(key=lambda p: p.created_at, reverse=True)

        elapsed = time.monotonic() - start
        logger.info(
            "command: list_context_packages() complete | count=%d | %.2fs",
            len(packages),
            elapsed,
        )
        return ContextPackageListResponse(
            success=True,
            packages=[_pkg_to_response(p) for p in packages],
            total_count=len(packages),
        )

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: list_context_packages() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to list context packages: {e}",
        )


async def get_context_package(
    package_id: str,
) -> ContextPackageResponse | ErrorResponse | None:
    """Get a single context package by ID."""
    start = time.monotonic()
    logger.info("command: get_context_package() | id=%s", package_id)

    try:
        pkg = await _pkg_repo.get(package_id)
        if pkg is None:
            return None

        elapsed = time.monotonic() - start
        logger.info("command: get_context_package() complete | %.2fs", elapsed)
        return _pkg_to_response(pkg)

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_context_package() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to get context package: {e}",
        )


async def delete_context_package(package_id: str) -> dict | ErrorResponse:
    """Delete a context package."""
    start = time.monotonic()
    logger.info("command: delete_context_package() | id=%s", package_id)

    try:
        deleted = await _pkg_repo.delete(package_id)
        elapsed = time.monotonic() - start
        if deleted:
            logger.info("command: delete_context_package() complete | %.2fs", elapsed)
            return {"success": True, "message": f"Package {package_id} deleted"}
        else:
            return ErrorResponse(
                error="NotFoundError",
                message=f"Package {package_id} not found",
            )

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: delete_context_package() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to delete context package: {e}",
        )


async def append_context_package(
    package_id: str,
    request: ContextPackageAppendRequest,
) -> ContextPackageResponse | ErrorResponse | None:
    """Append content to an existing context package."""
    start = time.monotonic()
    logger.info("command: append_context_package() | id=%s", package_id)

    try:
        pkg = await _pkg_repo.append(
            package_id=package_id,
            additional_task=request.additional_task,
            additional_markdown=request.additional_markdown,
            additional_objective=request.additional_objective,
        )

        if pkg is None:
            return None

        elapsed = time.monotonic() - start
        logger.info("command: append_context_package() complete | %.2fs", elapsed)
        return _pkg_to_response(pkg)

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: append_context_package() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to append to context package: {e}",
        )
