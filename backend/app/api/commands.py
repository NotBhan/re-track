"""Backward-compatibility facade for RE:Track backend commands.

Delegates all execution to application use cases under app.application.use_cases.
Preserves module-level variables, lock objects, and signatures for existing callers and test mocking.
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

from app.api.schemas import (
    AppSettingsResponse,
    BackendStatusResponse,
    BenchmarkSuiteResponse,
    CogneeSettingsRequest,
    CognifyRequest,
    CognifyResponse,
    ContextPackageAppendRequest,
    ContextPackageListResponse,
    ContextPackageResponse,
    ContextPackageSaveRequest,
    ContextResponse,
    DashboardStats,
    DatasetDataItemsResponse,
    DatasetListResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    HealthResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    MemoryGraphResponse,
    MemoryStatsResponse,
    MemoryVectorsResponse,
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryResponse,
    ScanResultResponse,
)
from app.application.container import get_container
from app.application.use_cases.context import ContextUseCases
from app.application.use_cases.context_packages import PackageUseCases
from app.application.use_cases.indexing import IndexingUseCases
from app.application.use_cases.memory import MemoryUseCases
from app.application.use_cases.repositories import RepositoryUseCases
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings, get_settings
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.models.errors import CogneeServiceError
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

from app import __version__ as VERSION

_REPO_STORE_PATH = Path.home() / ".retrack" / "indexed_repos.json"
_LEGACY_REPO_STORE_PATH = Path.home() / ".andes" / "indexed_repos.json"

# Module-level aliases wired to container for test mocking compatibility
_cognee_service: Optional[CogneeService] = None
_indexing_service: Optional[IndexingService] = None
_context_service: Optional[ContextService] = None
_settings: Optional[Settings] = None
_manager: Optional[RepositoryManager] = None
_cgc_service: Optional[CGCService] = None
_llm_provider: Optional[LLMProviderService] = None
_intent_parser: Optional[IntentParserService] = None
_manifest_service: Optional[ManifestService] = None

_indexing_lock: Optional[asyncio.Lock] = None
_context_gen_lock: Optional[asyncio.Lock] = None


def _get_active_container() -> Any:
    """Get the active container and sync any module-level mocks."""
    global _manager, _indexing_lock, _context_gen_lock
    container = get_container()
    if _manager is None:
        _manager = container.repository_manager
    if _indexing_lock is None:
        _indexing_lock = container.indexing_lock
    if _context_gen_lock is None:
        _context_gen_lock = container.context_gen_lock

    _sync_container_services(container)
    return container


def _sync_container_services(container: Optional[Any] = None) -> Any:
    """Sync module-level mock overrides with container if tests patched them."""
    target = container or get_container()
    if _cognee_service is not None or _indexing_service is not None or _context_service is not None:
        target.cognee_service = _cognee_service
        target.indexing_service = _indexing_service
        target.context_service = _context_service
    if _settings is not None:
        target.settings = _settings
    if _manager is not None:
        target.repository_manager = _manager
    if _cgc_service is not None:
        target.cgc_service = _cgc_service
    if _llm_provider is not None:
        target.llm_provider = _llm_provider
    if _intent_parser is not None:
        target.intent_parser = _intent_parser
    if _manifest_service is not None:
        target.manifest_service = _manifest_service
    if _indexing_lock is not None:
        target.indexing_lock = _indexing_lock
    if _context_gen_lock is not None:
        target.context_gen_lock = _context_gen_lock
    return target


def _sync_module_from_container() -> None:
    """Sync module-level variables from container."""
    global _cognee_service, _indexing_service, _context_service, _settings, _manager
    global _cgc_service, _llm_provider, _intent_parser, _manifest_service

    container = get_container()
    _cognee_service = container.cognee_service
    _indexing_service = container.indexing_service
    _context_service = container.context_service
    _settings = container.settings
    _manager = container.repository_manager
    _cgc_service = container.cgc_service
    _llm_provider = container.llm_provider
    _intent_parser = container.intent_parser
    _manifest_service = container.manifest_service


def _ensure_services() -> None:
    """Raise if any service is not initialized."""
    container = _get_active_container()
    if _cognee_service is None or _indexing_service is None or _context_service is None:
        raise CogneeServiceError(
            "Backend services not initialized. Call initialize_backend() first."
        )
    container.ensure_services()


def _load_repo_store() -> dict:
    return _get_active_container().metadata_store.load()


def _save_repo_store(data: dict) -> None:
    _get_active_container().metadata_store.save(data)


async def initialize_backend(settings: Optional[Settings] = None) -> None:
    """Initialize all backend services."""
    container = _get_active_container()
    await container.initialize(settings)
    _sync_module_from_container()



# --- System & Health ---


async def health() -> HealthResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_system_use_cases().health()


async def get_backend_status() -> BackendStatusResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_system_use_cases().get_backend_status()


async def get_app_settings() -> AppSettingsResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_system_use_cases().get_app_settings()


async def update_cognee_settings(
    request: CogneeSettingsRequest,
) -> AppSettingsResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_system_use_cases().update_cognee_settings(request)


async def get_detailed_health() -> Any:
    container = _get_active_container()
    return await container.get_system_use_cases().get_detailed_health()


def export_diagnostics(
    output_path: Optional[Any] = None,
    include_logs: bool = True,
    max_log_lines: int = 50,
    include_config: bool = True,
    include_health: bool = True,
) -> Any:
    container = _get_active_container()
    return container.get_system_use_cases().export_diagnostics(
        output_path=output_path,
        include_logs=include_logs,
        max_log_lines=max_log_lines,
        include_config=include_config,
        include_health=include_health,
    )


def get_recent_logs(max_entries: int = 50) -> list[dict[str, Any]]:
    container = _get_active_container()
    return container.get_system_use_cases().get_recent_logs(max_entries=max_entries)


async def update_provider(
    provider: str,
    base_url: str,
    model: str,
    api_key: str = "local",
) -> dict | ErrorResponse:
    container = _get_active_container()
    res = await container.get_system_use_cases().update_provider(provider, base_url, model, api_key)
    _sync_module_from_container()
    return res


# --- Indexing & Repository Summaries ---


async def index_repository(
    request: IndexRepositoryRequest,
) -> IndexRepositoryResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_indexing_use_cases().index_repository(request)


async def get_repository_summaries() -> RepositoryListResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_indexing_use_cases().get_repository_summaries()


# --- Context Generation ---


async def generate_context(
    request: GenerateContextRequest,
) -> ContextResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_context_use_cases().generate_context(request)


async def get_agent_context(
    request: AgentContextRequest,
) -> AgentContextResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_context_use_cases().get_agent_context(request)


# --- Memory & Datasets ---


async def list_datasets() -> DatasetListResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().list_datasets()


async def get_dataset_items(dataset_id: str) -> DatasetDataItemsResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().get_dataset_items(dataset_id)


async def forget_dataset(
    request: ForgetDatasetRequest,
) -> None | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().forget_dataset(request)


async def cognify_dataset(
    request: CognifyRequest,
) -> CognifyResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().cognify_dataset(request)


async def get_memory_stats() -> MemoryStatsResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().get_memory_stats()


async def get_memory_graph(
    dataset_name: Optional[str] = None,
) -> MemoryGraphResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().get_memory_graph(dataset_name)


async def get_memory_vectors() -> MemoryVectorsResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().get_memory_vectors()


async def get_dashboard_stats() -> DashboardStats | ErrorResponse:
    container = _get_active_container()
    return await container.get_memory_use_cases().get_dashboard_stats()


# --- Repository Management ---


async def list_repositories() -> RepositoryListResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_repository_use_cases().list_repositories()


async def create_repository(
    request: RepositoryCreateRequest,
) -> RepositoryResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_repository_use_cases().create_repository(request)


async def scan_repository(repo_id: str) -> ScanResultResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_repository_use_cases().scan_repository(repo_id)


async def get_repository_progress(repo_id: str) -> dict | ErrorResponse:
    container = _get_active_container()
    return await container.get_repository_use_cases().get_repository_progress(repo_id)


async def delete_repository(repo_id: str) -> dict | ErrorResponse:
    container = _get_active_container()
    return await container.get_repository_use_cases().delete_repository(repo_id)


async def generate_suggested_prompts(repo_id: str) -> dict[str, Any]:
    container = _get_active_container()
    return await container.get_repository_use_cases().generate_suggested_prompts(repo_id)


# --- Context Package Persistence ---


async def save_context_package(
    request: ContextPackageSaveRequest,
) -> ContextPackageResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_package_use_cases().save_context_package(request)


async def list_context_packages() -> ContextPackageListResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_package_use_cases().list_context_packages()


async def get_context_package(package_id: str) -> Optional[ContextPackageResponse] | ErrorResponse:
    container = _get_active_container()
    return await container.get_package_use_cases().get_context_package(package_id)


async def delete_context_package(package_id: str) -> dict | ErrorResponse:
    container = _get_active_container()
    return await container.get_package_use_cases().delete_context_package(package_id)


async def append_context_package(
    package_id: str,
    request: ContextPackageAppendRequest,
) -> Optional[ContextPackageResponse] | ErrorResponse:
    container = _get_active_container()
    return await container.get_package_use_cases().append_context_package(package_id, request)


# --- Benchmarks ---


async def run_benchmark() -> BenchmarkSuiteResponse | ErrorResponse:
    container = _get_active_container()
    return await container.get_benchmark_use_cases().run_benchmark()

