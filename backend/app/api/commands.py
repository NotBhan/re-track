"""Async API command handlers for RE:Track."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from app.api.schemas import (
    AppSettingsResponse,
    BackendStatusResponse,
    BenchmarkResultItem,
    BenchmarkSuiteResponse,
    CogneeSettingsRequest,
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
    MemoryGraphNode,
    MemoryGraphEdge,
    MemoryGraphResponse,
    VectorDatasetInfo,
    MemoryVectorsResponse,
    MemoryDataItem,
    DatasetDataItemsResponse,
    RepoArchInfo,
    RepoComponentInfo,
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryResponse,
    RepositorySummaryInfo,
    ScanResultResponse,
)
from app.config.settings import Settings, get_settings
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.models.context_package import SavedContextPackage
from app.models.errors import AndesContextError, CogneeServiceError
from app.models.provider import ProviderType
from app.models.repository import Repository
from app.services.cgc_service import CGCService
from app.services.cognee_service import CogneeService
from app.services.context_cache import context_cache
from app.services.context_package_repository import JsonContextPackageRepository
from app.services.context_service import ContextService
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.llm_provider_service import LLMProviderService
from app.services.manifest_service import ManifestService
from app.services.repository_manager import RepositoryManager
from app.services.repository_summary import RepositorySummaryGenerator

logger = logging.getLogger(__name__)

# Backend version
VERSION = "0.1.0"

# Persistent store for indexed repository metadata
_REPO_STORE_PATH = Path.home() / ".retrack" / "indexed_repos.json"
_LEGACY_REPO_STORE_PATH = Path.home() / ".andes" / "indexed_repos.json"


# --- Repo metadata store ---


def _load_repo_store() -> dict:
    """Load the indexed repos store from disk."""
    if _REPO_STORE_PATH.exists():
        try:
            return json.loads(_REPO_STORE_PATH.read_text())
        except Exception:
            return {}
    if _LEGACY_REPO_STORE_PATH.exists():
        try:
            return json.loads(_LEGACY_REPO_STORE_PATH.read_text())
        except Exception:
            return {}
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

# Concurrency locks for critical asynchronous tasks
_indexing_lock = asyncio.Lock()
_context_gen_lock = asyncio.Lock()


def _ensure_services() -> None:
    """Raise if any service is not initialized."""
    if _cognee_service is None or _indexing_service is None or _context_service is None:
        raise CogneeServiceError(
            "Backend services not initialized. Call initialize_backend() first."
        )


_cgc_service: Optional[CGCService] = None
_llm_provider: Optional[LLMProviderService] = None
_intent_parser: Optional[IntentParserService] = None
_manifest_service: Optional[ManifestService] = None


async def initialize_backend(settings: Optional[Settings] = None) -> None:
    """Initialize all backend services.

    Args:
        settings: Optional settings override. Uses default if None.
    """
    global _cognee_service, _indexing_service, _context_service, _settings
    global _cgc_service, _llm_provider, _intent_parser, _manifest_service

    from app.config.settings import Settings, get_settings
    _settings = settings or get_settings()
    _cognee_service = CogneeService(_settings)
    await _cognee_service.initialize()

    # Determine provider endpoint and type from environment/settings
    llm_endpoint = os.environ.get("LLM_ENDPOINT", _settings.ollama.llm_endpoint)
    llm_model = os.environ.get("LLM_MODEL", _settings.ollama.llm_model)
    llm_api_key = os.environ.get("LLM_API_KEY", "lm-studio")
    provider_str = os.environ.get("LLM_PROVIDER", "lmstudio").lower()

    if "lm" in provider_str or "studio" in provider_str:
        p_type = ProviderType.LM_STUDIO
    elif "openai" in provider_str:
        p_type = ProviderType.OPENAI_COMPATIBLE
    else:
        p_type = ProviderType.OLLAMA

    _llm_provider = LLMProviderService(
        provider_type=p_type,
        base_url=llm_endpoint,
        api_key=llm_api_key,
        default_model=llm_model,
    )
    _intent_parser = IntentParserService(_llm_provider)

    _indexing_service = IndexingService(_cognee_service, manifest_service=_manifest_service)
    _context_service = ContextService(_cognee_service)

    logger.info("Backend services initialized")


async def update_provider(
    provider: str,
    base_url: str,
    model: str,
    api_key: str = "local",
) -> dict | ErrorResponse:
    """Hot-reload the active LLM provider without restarting the backend.

    Args:
        provider: One of 'ollama', 'lmstudio', 'openai_compatible'.
        base_url: Full base URL including /v1 suffix if needed.
        model: Model identifier to use (e.g. 'phi4-mini:q6_k').
        api_key: API key or sentinel string (e.g. 'lm-studio', 'ollama').
    """
    global _llm_provider, _intent_parser

    start = time.monotonic()
    logger.info("command: update_provider() | provider=%s url=%s model=%s", provider, base_url, model)

    try:
        provider_lower = provider.lower()
        if "lm" in provider_lower or "studio" in provider_lower:
            p_type = ProviderType.LM_STUDIO
        elif "openai" in provider_lower:
            p_type = ProviderType.OPENAI_COMPATIBLE
        else:
            p_type = ProviderType.OLLAMA

        _llm_provider = LLMProviderService(
            provider_type=p_type,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            default_model=model,
        )
        _intent_parser = IntentParserService(_llm_provider)

        # Synchronize Cognee's runtime config with the new provider & model
        if _settings:
            cog_provider = "openai" if p_type in (ProviderType.LM_STUDIO, ProviderType.OPENAI_COMPATIBLE) else "ollama"
            os.environ["LLM_PROVIDER"] = cog_provider
            os.environ["LLM_ENDPOINT"] = base_url.rstrip("/")
            os.environ["LLM_MODEL"] = model
            os.environ["LLM_API_KEY"] = api_key
            _settings.ollama.llm_model = model
            try:
                _settings.configure_cognee()
                _settings.save_persisted_settings()
            except Exception as cog_err:
                logger.warning("Could not reconfigure Cognee runtime: %s", cog_err)

        # Verify reachability immediately
        provider_health = await _llm_provider.check_health()

        elapsed = time.monotonic() - start
        logger.info("command: update_provider() complete | reachable=%s | %.2fs", provider_health.is_reachable, elapsed)
        return {
            "success": True,
            "provider": provider,
            "base_url": base_url,
            "model": provider_health.active_model or model,
            "reachable": provider_health.is_reachable,
            "loaded_models": [m.model_id for m in provider_health.loaded_models],
        }

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: update_provider() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Provider update failed: {e}",
        )


# --- Settings Commands ---


async def get_app_settings() -> AppSettingsResponse | ErrorResponse:
    """Return current app configuration and Cognee settings."""
    try:
        settings = _settings or get_settings()
        llm_prov = "ollama"
        if _llm_provider is not None:
            llm_prov = _llm_provider.provider_type.value

        return AppSettingsResponse(
            success=True,
            vector_db=settings.storage.vector_db,
            graph_db=settings.storage.graph_db,
            relational_db=settings.storage.relational_db,
            enable_kg_extraction=settings.storage.enable_kg_extraction,
            auto_link_entities=settings.storage.auto_link_entities,
            caching=settings.service.caching,
            data_root=str(settings.storage.data_root),
            system_root=str(settings.storage.system_root),
            llm_provider=llm_prov,
            llm_host=settings.ollama.host,
            llm_port=settings.ollama.port,
            llm_model=_llm_provider.default_model if _llm_provider else settings.ollama.llm_model,
            embedding_model=settings.ollama.embedding_model,
        )
    except Exception as e:
        logger.error("get_app_settings() failed: %s", e)
        return ErrorResponse(error=type(e).__name__, message=str(e))


async def update_cognee_settings(
    request: CogneeSettingsRequest,
) -> AppSettingsResponse | ErrorResponse:
    """Update and persist Cognee / storage settings to disk and runtime."""
    global _settings
    start = time.monotonic()
    logger.info("command: update_cognee_settings() | %s", request.model_dump())

    try:
        settings = _settings or get_settings()
        if request.vector_db is not None:
            settings.storage.vector_db = request.vector_db.strip().lower()
        if request.graph_db is not None:
            settings.storage.graph_db = request.graph_db.strip().lower()
        if request.enable_kg_extraction is not None:
            settings.storage.enable_kg_extraction = request.enable_kg_extraction
        if request.auto_link_entities is not None:
            settings.storage.auto_link_entities = request.auto_link_entities
        if request.caching is not None:
            settings.service.caching = request.caching

        # Persist to disk (~/.andes/settings.json)
        settings.save_persisted_settings()

        # Reconfigure Cognee runtime
        try:
            settings.configure_cognee()
        except Exception as cog_err:
            logger.warning("Could not reconfigure Cognee runtime: %s", cog_err)

        elapsed = time.monotonic() - start
        logger.info("command: update_cognee_settings() complete | %.2fs", elapsed)
        return await get_app_settings()
    except Exception as e:
        logger.error("update_cognee_settings() failed: %s", e)
        return ErrorResponse(error=type(e).__name__, message=str(e))


# --- Commands ---


async def health() -> HealthResponse | ErrorResponse:
    """Check system health: Cognee, Ollama, and host hardware metrics."""
    start = time.monotonic()
    logger.info("command: health()")

    try:
        settings = _settings or get_settings()
        cognee = _cognee_service

        # Use the active LLM provider to check reachability — this respects
        # whichever provider (Ollama, LM Studio, etc.) was initialized at startup.
        if _llm_provider is not None:
            provider_health = await _llm_provider.check_health()
            ollama_reachable = provider_health.is_reachable
        else:
            # Fallback: probe the configured Ollama socket if provider not ready yet.
            ollama_reachable = settings.ollama.check_connection()
        cognee_ok = cognee is not None and cognee.is_initialized
        status = "ok" if (ollama_reachable and cognee_ok) else "degraded"

        # Hardware metrics (safe fallback if psutil/nvidia-smi unavailable)
        ram_total = 16.0
        ram_used = 0.0
        cpu_pct = 0.0
        try:
            import psutil
            vm = psutil.virtual_memory()
            ram_total = round(vm.total / (1024 ** 3), 1)
            ram_used = round(vm.used / (1024 ** 3), 1)
            cpu_pct = round(psutil.cpu_percent(interval=0.0), 1)
        except Exception:
            pass

        vram_total = 0.0
        vram_used = 0.0
        gpu_name = None

        # 1. Try Linux sysfs DRM mem_info (AMD Radeon / Intel / generic DRM drivers)
        try:
            from pathlib import Path
            for card in sorted(Path("/sys/class/drm").glob("card*")):
                vram_tot_f = card / "device" / "mem_info_vram_total"
                vram_used_f = card / "device" / "mem_info_vram_used"
                if vram_tot_f.exists() and vram_used_f.exists():
                    tot = int(vram_tot_f.read_text().strip()) / (1024 ** 3)
                    used = int(vram_used_f.read_text().strip()) / (1024 ** 3)
                    # Pick dedicated GPU if available
                    if tot > vram_total:
                        vram_total = round(tot, 1)
                        vram_used = round(used, 1)
                        gpu_name = "AMD Radeon GPU"
        except Exception:
            pass

        # 2. Try NVIDIA SMI if sysfs didn't find dedicated VRAM
        if vram_total == 0.0:
            try:
                import subprocess
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
                    stderr=subprocess.DEVNULL,
                    timeout=1,
                ).decode().strip()
                if out:
                    parts = [p.strip() for p in out.split(",")]
                    if len(parts) >= 3:
                        gpu_name = parts[0]
                        vram_total = round(float(parts[1]) / 1024.0, 1)
                        vram_used = round(float(parts[2]) / 1024.0, 1)
            except Exception:
                pass

        ram_pct = round((ram_used / ram_total) * 100, 1) if ram_total > 0 else 0.0
        high_mem_pressure = ram_pct >= 90.0

        gpu_presence = "None"
        if gpu_name:
            if "AMD" in gpu_name:
                gpu_presence = "AMD"
            elif "NVIDIA" in gpu_name or "GeForce" in gpu_name or "RTX" in gpu_name:
                gpu_presence = "NVIDIA"
            else:
                gpu_presence = "Generic"

        # Runtime execution device: only declare GPU if VRAM usage is strictly > 0
        exec_device = "GPU" if vram_used > 0.2 else "CPU"
        active_model = settings.ollama.llm_model if settings else None

        response = HealthResponse(
            status=status,
            ollama_reachable=ollama_reachable,
            cognee_initialized=cognee_ok,
            version=VERSION,
            ram_total_gb=ram_total,
            ram_used_gb=ram_used,
            ram_percent=ram_pct,
            high_memory_pressure=high_mem_pressure,
            cpu_percent=cpu_pct,
            gpu_presence=gpu_presence,
            gpu_name=gpu_name,
            vram_total_gb=vram_total,
            vram_used_gb=vram_used,
            execution_device=exec_device,
            active_model=active_model,
        )

        elapsed = time.monotonic() - start
        logger.info("command: health() | status=%s | device=%s | ram=%s%% | %.2fs", response.status, exec_device, ram_pct, elapsed)
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

        # Use the active LLM provider for reachability and model info so that
        # switching from Ollama to LM Studio is reflected here immediately.
        if _llm_provider is not None:
            provider_health = await _llm_provider.check_health()
            ollama_reachable = provider_health.is_reachable
            # Parse host/port from the provider's base_url
            from urllib.parse import urlparse
            parsed = urlparse(_llm_provider.base_url)
            active_host = parsed.hostname or settings.ollama.host
            active_port = parsed.port or settings.ollama.port
            # Use the actual loaded model name when available, fall back to configured default.
            active_llm_model = provider_health.active_model or _llm_provider.default_model
        else:
            ollama_reachable = settings.ollama.check_connection()
            active_host = settings.ollama.host
            active_port = settings.ollama.port
            active_llm_model = settings.ollama.llm_model
        cognee_ok = cognee is not None and cognee.is_initialized
        status = "ok" if (ollama_reachable and cognee_ok) else "degraded"

        response = BackendStatusResponse(
            status=status,
            ollama_reachable=ollama_reachable,
            ollama_host=active_host,
            ollama_port=active_port,
            llm_model=active_llm_model,
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

        if _indexing_lock.locked():
            logger.warning("command: index_repository() rejected | indexing already in progress")
            return ErrorResponse(
                error="ConcurrencyError",
                message="An indexing job is already in progress. Please wait for it to complete.",
            )

        async with _indexing_lock:
            repo_path = Path(request.repository_path).resolve()
            if not repo_path.exists():
                raise ValueError(f"Repository path does not exist: {request.repository_path}")
            if not repo_path.is_dir():
                raise ValueError(f"Path is not a directory: {request.repository_path}")

            # Find matching repository id if any
            matching_repo = None
            matching_repo_id = None
            for r in _manager.list_repositories():
                if (
                    str(Path(r.local_path).resolve()) == str(repo_path)
                    or r.id == request.dataset_name
                    or r.name == request.dataset_name
                    or Path(r.local_path).name == repo_path.name
                ):
                    matching_repo = r
                    matching_repo_id = r.id
                    break

            def on_progress(stage_name: str, step: int, total_steps: int):
                if matching_repo_id:
                    total_f = matching_repo.file_count or 1
                    proc_f = int((step / total_steps) * total_f) if step < total_steps else total_f
                    _manager.set_indexing_progress(matching_repo_id, {
                        "status": "indexed" if step >= total_steps else "indexing",
                        "stage": stage_name,
                        "processed_files": proc_f,
                        "total_files": total_f,
                        "elapsed_ms": int((time.monotonic() - start) * 1000),
                        "languages": matching_repo.languages if matching_repo else [],
                        "frameworks": matching_repo.frameworks if matching_repo else [],
                        "error": None,
                        "file_count": total_f,
                        "size_bytes": matching_repo.size_bytes if matching_repo else 0,
                    })

            on_progress("Scanning & discovering repository files...", 1, 5)

            progress = await _indexing_service.index_repository(
                repo_path=repo_path,
                dataset_name=request.dataset_name,
                force_reindex=request.force_reindex,
                progress_callback=on_progress,
            )

            # Persist repository metadata and invalidate cache after successful indexing
            if progress.failed_files == 0:
                context_cache.invalidate_repo(str(repo_path))
                _persist_repo_metadata(repo_path, progress.processed_files)
                if matching_repo_id:
                    _manager.set_indexing_progress(matching_repo_id, {
                        "status": "indexed",
                        "stage": "Indexing Completed",
                        "processed_files": progress.processed_files,
                        "total_files": progress.total_files,
                        "elapsed_ms": int((time.monotonic() - start) * 1000),
                        "languages": matching_repo.languages if matching_repo else [],
                        "frameworks": matching_repo.frameworks if matching_repo else [],
                        "error": None,
                        "file_count": progress.total_files,
                        "size_bytes": matching_repo.size_bytes if matching_repo else 0,
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                    })
            elif matching_repo_id:
                _manager.set_indexing_progress(matching_repo_id, {
                    "status": "error",
                    "stage": "Indexing Failed",
                    "processed_files": progress.processed_files,
                    "total_files": progress.total_files,
                    "elapsed_ms": int((time.monotonic() - start) * 1000),
                    "languages": matching_repo.languages if matching_repo else [],
                    "frameworks": matching_repo.frameworks if matching_repo else [],
                    "error": "Failed files during indexing",
                    "file_count": progress.total_files,
                    "size_bytes": 0,
                })

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
        if _indexing_service is not None:
            indexed_files = _indexing_service.filter_files(_indexing_service.discover_files(repo_path), repo_path)
        else:
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
            "frameworks": summary.technology_stack.frameworks,
            "file_count": file_count,
            "memory_size": f"{len(indexed_files)} files",
            "last_indexed": summary.generated_at,
            "purpose": summary.project_purpose,
            "architecture": [a.model_dump() for a in architecture] if architecture else None,
            "components": [c.model_dump() for c in components] if components else None,
            "call_graph_nodes": [
                {"id": n.id, "label": n.label, "file": n.file, "kind": n.kind, "line": n.line}
                for n in summary.call_graph_nodes
            ],
            "call_graph_edges": [
                {"source": e.source, "target": e.target, "kind": e.kind}
                for e in summary.call_graph_edges
            ],
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

        # Update matching repository in manager
        try:
            for m_repo in _manager.list_repositories():
                if str(Path(m_repo.local_path).resolve()) == str(repo_path.resolve()) or m_repo.id == repo_id or m_repo.name == repo_path.name:
                    _manager.update_repository(
                        m_repo.id,
                        status="indexed",
                        indexed_at=datetime.now(timezone.utc).isoformat(),
                        error_message=None,
                        summary=summary.project_purpose or m_repo.summary,
                        architecture=summary.architecture.pattern if summary.architecture else m_repo.architecture,
                        components=[c.name for c in summary.key_components] if summary.key_components else m_repo.components,
                        entry_points=[e.path for e in summary.entry_points] if summary.entry_points else m_repo.entry_points,
                        metadata={
                            **(m_repo.metadata or {}),
                            "call_graph_nodes": entry["call_graph_nodes"],
                            "call_graph_edges": entry["call_graph_edges"],
                        },
                    )
        except Exception as sync_err:
            logger.debug("Non-fatal: could not sync to manager: %s", sync_err)
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


async def generate_suggested_prompts(repo_id: str) -> dict[str, Any]:
    """Generate repository-tailored developer prompts grounded strictly in AST metadata and real symbols."""
    start = time.monotonic()
    logger.info("command: generate_suggested_prompts() | repo_id=%s", repo_id)

    repo = None
    for r in _manager.list_repositories():
        if r.id == repo_id or r.name == repo_id or Path(r.local_path).name == repo_id:
            repo = r
            break

    name = repo.name if repo else "this repository"
    langs = ", ".join(repo.languages) if (repo and repo.languages) else "code"
    frameworks = ", ".join(repo.frameworks) if (repo and repo.frameworks) else ""
    components = repo.components if (repo and repo.components) else []

    # Extract actual verified AST symbols (classes, functions, components)
    real_symbols = []
    if repo and repo.metadata and isinstance(repo.metadata.get("call_graph_nodes"), list):
        real_symbols = [
            n["label"] for n in repo.metadata["call_graph_nodes"]
            if isinstance(n, dict) and n.get("label") and not n.get("label", "").startswith(".")
        ]
    if not real_symbols and components:
        real_symbols = components[:15]

    symbols_str = ", ".join(real_symbols[:15]) if real_symbols else ""

    heuristic_prompts = []
    if real_symbols:
        s1 = real_symbols[0]
        heuristic_prompts.append({
            "label": f"{s1[:20]} Architecture",
            "prompt": f"Explain the implementation, callers, and lifecycle of `{s1}` in {name}."
        })
        if len(real_symbols) > 1:
            s2 = real_symbols[1]
            heuristic_prompts.append({
                "label": f"{s2[:20]} Flow",
                "prompt": f"Trace how `{s2}` interacts with related components and handles state in {name}."
            })
    if frameworks:
        heuristic_prompts.append({
            "label": f"{frameworks.split(',')[0]} Routing & Auth",
            "prompt": f"Find where {frameworks} configuration, routing, and middleware pipelines are initialized in {name}."
        })
    heuristic_prompts.extend([
        {
            "label": "Call Graph Traversal",
            "prompt": f"Trace the critical function call graph and data dependencies across {name}."
        },
        {
            "label": "Data Schemas",
            "prompt": f"Show the key data models, schemas, and API definitions present in {name}."
        },
    ])

    if _llm_provider:
        try:
            health = await _llm_provider.check_health()
            if health.is_reachable:
                system_prompt = (
                    "You are a strict, hallucination-free software engineer. "
                    "You must base your task questions SOLELY and STRICTLY on the actual verified classes, "
                    "symbols, and modules present in this repository. DO NOT invent external features, models, "
                    "or endpoints not present in the provided symbols.\n"
                    "Return STRICTLY a valid JSON array of objects with keys 'label' (2-4 words) "
                    "and 'prompt' (a single clear developer question/task). Do not include markdown formatting or backticks."
                )
                user_prompt = (
                    f"Repository: {name}\n"
                    f"Frameworks: {frameworks or 'Standard'}\n"
                    f"Languages: {langs}\n"
                    f"Discovered Classes & Symbols: {symbols_str or 'Core codebase'}\n\n"
                    "Generate 4-5 focused developer questions or implementation tasks referencing these exact symbols."
                )
                raw_text = await _llm_provider.generate_completion(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.1,
                    max_tokens=600,
                )
                clean_json = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
                if "```" in clean_json:
                    clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                    clean_json = re.sub(r"\s*```$", "", clean_json)
                parsed = json.loads(clean_json)
                if isinstance(parsed, list) and len(parsed) >= 2:
                    valid_prompts = [
                        {"label": str(item.get("label", "Task"))[:30], "prompt": str(item.get("prompt", ""))}
                        for item in parsed
                        if item.get("label") and item.get("prompt")
                    ]
                    if valid_prompts:
                        elapsed = time.monotonic() - start
                        logger.info("Generated %d strictly grounded AI prompts in %.2fs", len(valid_prompts), elapsed)
                        return {"success": True, "prompts": valid_prompts, "source": "ai"}
        except Exception as e:
            logger.debug("LLM prompt generation failed, falling back to heuristics: %s", e)

    return {"success": True, "prompts": heuristic_prompts[:5], "source": "heuristic"}


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
        graph_nodes = None
        graph_edges = None
        knowledge_graph_status = "not_extracted"

        if _cognee_service and _cognee_service.is_initialized:
            try:
                graph_stats = await _cognee_service.get_graph_stats()
                raw_nodes = graph_stats.get("graph_nodes", 0)
                raw_edges = graph_stats.get("graph_edges", 0)
                if raw_nodes > 0:
                    knowledge_graph_status = "extracted"
                    graph_nodes = raw_nodes
                    graph_edges = raw_edges
                else:
                    knowledge_graph_status = "not_extracted"
            except Exception as e:
                logger.warning("Failed to get graph stats: %s", e)
                knowledge_graph_status = "failed"

        response = MemoryStatsResponse(
            success=True,
            total_size_display=total_size_display,
            dataset_count=dataset_count,
            knowledge_graph_status=knowledge_graph_status,
            graph_nodes=graph_nodes,
            graph_edges=graph_edges,
        )

        elapsed = time.monotonic() - start
        logger.info(
            "command: get_memory_stats() complete | datasets=%d | status=%s | nodes=%s | edges=%s | %.2fs",
            dataset_count,
            knowledge_graph_status,
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


async def get_memory_graph(dataset_name: Optional[str] = None) -> MemoryGraphResponse | ErrorResponse:
    """Return authoritative Knowledge Graph nodes and edges from Cognee memory engine."""
    start = time.monotonic()
    logger.info("command: get_memory_graph() | dataset=%s", dataset_name)

    try:
        if not _cognee_service or not _cognee_service.is_initialized:
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

        raw_nodes, raw_edges = await _cognee_service.get_graph_data()
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
        logger.info("command: get_memory_graph() complete | nodes=%d | edges=%d | %.2fs", len(nodes), len(edges), elapsed)
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_memory_graph() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to get memory graph: {e}",
        )


async def get_memory_vectors() -> MemoryVectorsResponse | ErrorResponse:
    """Return authoritative Vector Space and embedding index statistics."""
    start = time.monotonic()
    logger.info("command: get_memory_vectors()")

    try:
        settings = _settings or get_settings()
        cognee = _cognee_service

        datasets_list: list[VectorDatasetInfo] = []
        total_files = 0

        if cognee and cognee.is_initialized:
            raw_datasets = await cognee.list_datasets()
            for ds in raw_datasets:
                fc = ds.get("file_count", 0)
                sz = ds.get("size_bytes", 0)
                total_files += fc
                v_status = "ready" if fc > 0 else "empty"
                # Estimate chunks based on file count / size
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

        response = MemoryVectorsResponse(
            success=True,
            vector_db_provider=settings.storage.vector_db,
            embedding_model=settings.ollama.embedding_model,
            embedding_dimensions=768,
            total_datasets=len(datasets_list),
            total_files=total_files,
            datasets=datasets_list,
        )

        elapsed = time.monotonic() - start
        logger.info("command: get_memory_vectors() complete | datasets=%d | files=%d | %.2fs", len(datasets_list), total_files, elapsed)
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_memory_vectors() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to get vector records: {e}",
        )


async def get_dataset_items(dataset_id: str) -> DatasetDataItemsResponse | ErrorResponse:
    """Return authoritative data items (stored files) for a specific dataset."""
    start = time.monotonic()
    logger.info("command: get_dataset_items() | dataset_id=%s", dataset_id)

    try:
        cognee = _cognee_service
        items: list[MemoryDataItem] = []
        dataset_name = dataset_id

        if cognee and cognee.is_initialized:
            raw_items = await cognee.get_dataset_data_items(dataset_id)
            for it in raw_items:
                items.append(MemoryDataItem(
                    id=it.get("id", ""),
                    name=it.get("name", ""),
                    mime_type=it.get("mime_type", "text/plain"),
                    data_size=it.get("data_size", 0),
                    created_at=it.get("created_at"),
                    extension=it.get("extension", ""),
                    content_hash=it.get("content_hash", ""),
                    pipeline_status=it.get("pipeline_status", {}),
                ))

        response = DatasetDataItemsResponse(
            success=True,
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            items=items,
            total_count=len(items),
        )

        elapsed = time.monotonic() - start
        logger.info("command: get_dataset_items() complete | count=%d | %.2fs", len(items), elapsed)
        return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_dataset_items() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to get dataset items: {e}",
        )


async def run_benchmark() -> BenchmarkSuiteResponse | ErrorResponse:
    """Run a benchmark suite against the generate_context endpoint."""
    start = time.monotonic()
    logger.info("command: run_benchmark()")

    try:
        from app.api.benchmarks import run_benchmark_suite

        _ensure_services()
        response = await run_benchmark_suite()

        elapsed = time.monotonic() - start
        logger.info(
            "command: run_benchmark() complete | questions=%d | compression=%.2fx | savings=%.1f%% | %.2fs",
            response.total_questions,
            response.avg_compression_ratio,
            response.avg_token_savings_percent,
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
    """Convert a Repository dataclass to a Pydantic response model with full AST and metadata."""
    call_graph_nodes = None
    call_graph_edges = None
    call_graph_status = "not_analyzed"
    call_graph_error = None
    summary = repo.summary or ""
    entry_points = repo.entry_points or []
    architecture = repo.architecture or ""
    components = repo.components or []
    dependencies = repo.dependencies or []

    # Check repo metadata
    if repo.metadata:
        if "call_graph_nodes" in repo.metadata:
            call_graph_nodes = repo.metadata["call_graph_nodes"]
        if "call_graph_edges" in repo.metadata:
            call_graph_edges = repo.metadata["call_graph_edges"]
        if "call_graph_status" in repo.metadata:
            call_graph_status = repo.metadata["call_graph_status"]
        if "call_graph_error" in repo.metadata:
            call_graph_error = repo.metadata["call_graph_error"]

    # Fallback to indexed repo store if not in repo.metadata
    if not call_graph_nodes:
        try:
            store = _load_repo_store()
            for r in store.get("repositories", []):
                if r.get("path") == repo.local_path or r.get("name") == repo.name or r.get("id") == repo.id:
                    if r.get("call_graph_nodes"):
                        call_graph_nodes = r.get("call_graph_nodes")
                    if r.get("call_graph_edges"):
                        call_graph_edges = r.get("call_graph_edges")
                    if r.get("call_graph_status"):
                        call_graph_status = r.get("call_graph_status")
                    if r.get("call_graph_error"):
                        call_graph_error = r.get("call_graph_error")
                    if not summary and r.get("purpose"):
                        summary = r.get("purpose")
                    break
        except Exception:
            pass

    # Infer status if not explicitly recorded
    if call_graph_status == "not_analyzed":
        if call_graph_edges and len(call_graph_edges) > 0:
            call_graph_status = "analyzed"
        elif call_graph_nodes and len(call_graph_nodes) > 0:
            call_graph_status = "zero_edges"
        elif repo.status == "indexed":
            call_graph_status = "zero_edges"

    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        source_type=repo.source_type,
        source_url=repo.source_url,
        local_path=repo.local_path,
        branch=repo.branch,
        commit_hash=repo.commit_hash,
        status=repo.status,
        languages=repo.languages or [],
        frameworks=repo.frameworks or [],
        file_count=repo.file_count or 0,
        size_bytes=repo.size_bytes or 0,
        indexed_at=repo.indexed_at,
        error_message=repo.error_message,
        summary=summary,
        entry_points=entry_points,
        architecture=architecture,
        components=components,
        dependencies=dependencies,
        metadata=repo.metadata or {},
        call_graph_status=call_graph_status,
        call_graph_error=call_graph_error,
        call_graph_nodes=call_graph_nodes,
        call_graph_edges=call_graph_edges,
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


async def get_repository_progress(repo_id: str) -> dict | ErrorResponse:
    """Get indexing progress for a repository."""
    start = time.monotonic()
    logger.info("command: get_repository_progress() | repo_id=%s", repo_id)

    try:
        progress = _manager.get_indexing_progress(repo_id)
        elapsed = time.monotonic() - start
        logger.info(
            "command: get_repository_progress() complete | status=%s | %.2fs",
            progress["status"],
            elapsed,
        )
        return progress

    except KeyError as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_repository_progress() error | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=str(e),
        )
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_repository_progress() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to get progress: {e}",
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


async def get_agent_context(
    request: AgentContextRequest,
) -> AgentContextResponse | ErrorResponse:
    """Generate an optimized context package for an external coding agent.

    Parses intent, retrieves structural code graphs via CGC, fetches semantic
    memory via Cognee, and builds a compact Markdown Context Package.
    """
    start = time.monotonic()
    logger.info("command: get_agent_context() | prompt=%s", request.task_prompt[:80])

    try:
        _ensure_services()

        if _context_gen_lock.locked():
            logger.warning("command: get_agent_context() rejected | synthesis already in progress")
            return ErrorResponse(
                error="ConcurrencyError",
                message="Context synthesis is already running for a task. Please wait a moment.",
            )

        async with _context_gen_lock:
            repo_path = Path(request.repository_path).resolve()
            dataset_name = request.dataset_name or repo_path.name
            target_tokens = request.max_tokens or 8000

            # 0. Check in-memory context synthesis cache (< 5ms hit)
            manifest_hash = ""
            manifest_file = repo_path / ".andes" / "manifest.json"
            if manifest_file.exists():
                try:
                    manifest_hash = str(manifest_file.stat().st_mtime)
                except Exception:
                    pass

            cache_key = context_cache.make_key(
                repo_path=str(repo_path),
                manifest_hash=manifest_hash,
                task_prompt=request.task_prompt,
                max_tokens=target_tokens,
            )
            cached_resp = context_cache.get(cache_key)
            if cached_resp is not None and isinstance(cached_resp, AgentContextResponse):
                logger.info(
                    "command: get_agent_context() [CACHE HIT] | prompt=%s | %.1fms",
                    request.task_prompt[:50],
                    (time.monotonic() - start) * 1000,
                )
                return cached_resp

            # 1. Parallel Step: Parse intent + generate repo summary + check provider health
            generator = RepositorySummaryGenerator()

            async def _get_intent():
                return await _intent_parser.parse_intent(request.task_prompt)

            async def _get_repo_summary():
                raw_files = _indexing_service.discover_files(repo_path)
                indexed = _indexing_service.filter_files(raw_files, repo_path)
                summary = generator.generate(repo_path, indexed)
                return indexed, summary

            async def _get_provider_health():
                if _llm_provider:
                    try:
                        return await _llm_provider.check_health()
                    except Exception:
                        return None
                return None

            intent, (indexed_files, repo_summary), health_status = await asyncio.gather(
                _get_intent(),
                _get_repo_summary(),
                _get_provider_health(),
            )

            # 2. Parallel Step: CGC Structural Query + Cognee Context Synthesis (Retrieval Stage)
            t_retrieval_start = time.perf_counter()

            async def _query_cgc():
                if request.include_structural_graph and _cgc_service:
                    try:
                        return await _cgc_service.query_structural_context(
                            repo_path=repo_path,
                            target_symbols=intent.extracted_symbols,
                        )
                    except Exception as e:
                        logger.warning("CGC query warning: %s", e)
                        return None
                return None

            async def _generate_package():
                ctx_svc = ContextService(
                    cognee_service=_cognee_service,
                    repository_summary=repo_summary,
                    target_tokens=target_tokens,
                )
                return await ctx_svc.generate_context_package(
                    task=request.task_prompt,
                    datasets=[dataset_name],
                    top_k=15,
                )

            structural_res, package = await asyncio.gather(
                _query_cgc(),
                _generate_package(),
            )
            retrieval_time_ms = int((time.perf_counter() - t_retrieval_start) * 1000)

            # 3. Direct AST & symbol relevance search across repository files (Ranking Stage)
            t_rank_start = time.perf_counter()
            relevant_snippets = []
            search_terms = list(set(
                [w for w in request.task_prompt.split() if len(w) > 3 and w.lower() not in ("where", "what", "find", "how", "with", "from", "this", "that")]
                + intent.extracted_symbols
                + intent.relevant_file_hints
            ))

            matched_files = set()
            term_lowers = [t.lower() for t in search_terms[:8]]
            if term_lowers:
                for fpath in indexed_files:
                    try:
                        rel = str(fpath.relative_to(repo_path))
                        rel_lower = rel.lower()
                        # Match filename first (zero I/O)
                        if any(t in rel_lower for t in term_lowers):
                            matched_files.add((rel, fpath))
                        elif fpath.stat().st_size < 256_000:
                            content = fpath.read_text(errors="replace").lower()
                            if any(t in content for t in term_lowers):
                                matched_files.add((rel, fpath))
                        if len(matched_files) >= 8:
                            break
                    except Exception:
                        pass

            # Extract focused code snippets for matched files
            for rel_path, full_path in list(matched_files)[:5]:
                try:
                    text = full_path.read_text(errors="replace")
                    lines = text.splitlines()
                    matching_indices = [
                        i for i, line in enumerate(lines)
                        if any(t.lower() in line.lower() for t in search_terms)
                    ]
                    if matching_indices:
                        first_idx = max(0, matching_indices[0] - 4)
                        last_idx = min(len(lines), matching_indices[0] + 25)
                        snippet = "\n".join(lines[first_idx:last_idx])
                        relevant_snippets.append(
                            f"### `{rel_path}` (Lines {first_idx+1}-{last_idx})\n```\n{snippet}\n```"
                        )
                except Exception:
                    pass

            ranking_time_ms = int((time.perf_counter() - t_rank_start) * 1000)

            # 4. Merge snippets and structural graph into Markdown output (Synthesis Stage)
            t_synth_start = time.perf_counter()
            quant_warning = health_status.quantization_warning if health_status else None

            final_markdown = package.markdown
            if relevant_snippets:
                final_markdown += "\n\n---\n\n# Relevant Code Snippets & Target Implementations\n\n" + "\n\n".join(relevant_snippets)

            if structural_res and structural_res.symbols_found:
                struct_md = structural_res.to_markdown()
                if struct_md:
                    final_markdown += f"\n\n---\n\n# Structural Code Relationships\n\n{struct_md}\n"

            synthesis_time_ms = int((time.perf_counter() - t_synth_start) * 1000)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            all_related = list(dict.fromkeys(
                [r[0] for r in matched_files] + (structural_res.related_files if structural_res else [])
            ))

            response = AgentContextResponse(
                success=True,
                context_markdown=final_markdown,
                task_summary=intent.task_summary,
                intent_category=intent.category,
                extracted_symbols=intent.extracted_symbols,
                callers=structural_res.callers if structural_res else [],
                callees=structural_res.callees if structural_res else [],
                related_files=all_related,
                quantization_warning=quant_warning,
                estimated_tokens=len(final_markdown) // 4,
                generation_time_ms=elapsed_ms,
                retrieval_time_ms=retrieval_time_ms,
                ranking_time_ms=ranking_time_ms,
                synthesis_time_ms=synthesis_time_ms,
                total_time_ms=elapsed_ms,
            )

            # Store in high-speed synthesis cache
            context_cache.set(cache_key, response, repo_path=str(repo_path))
            return response

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("command: get_agent_context() failed | %.2fs | %s", elapsed, e)
        return ErrorResponse(
            error=type(e).__name__,
            message=f"Failed to generate agent context: {e}",
        )
