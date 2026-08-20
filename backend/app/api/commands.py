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

VERSION = "0.1.0"

_REPO_STORE_PATH = Path.home() / ".retrack" / "indexed_repos.json"
_LEGACY_REPO_STORE_PATH = Path.home() / ".andes" / "indexed_repos.json"

# Module-level aliases wired to container for test mocking compatibility
_container = get_container()

_cognee_service: Optional[CogneeService] = None
_indexing_service: Optional[IndexingService] = None
_context_service: Optional[ContextService] = None
_settings: Optional[Settings] = None
_manager: RepositoryManager = _container.repository_manager
_cgc_service: Optional[CGCService] = None
_llm_provider: Optional[LLMProviderService] = None
_intent_parser: Optional[IntentParserService] = None
_manifest_service: Optional[ManifestService] = None

_indexing_lock: asyncio.Lock = _container.indexing_lock
_context_gen_lock: asyncio.Lock = _container.context_gen_lock


def _sync_container_services() -> None:
    """Sync module-level mock overrides with container if tests patched them."""
    _container.cognee_service = _cognee_service
    _container.indexing_service = _indexing_service
    _container.context_service = _context_service
    if _settings is not None:
        _container.settings = _settings
    if _manager is not None:
        _container.repository_manager = _manager
    if _cgc_service is not None:
        _container.cgc_service = _cgc_service
    if _llm_provider is not None:
        _container.llm_provider = _llm_provider
    if _intent_parser is not None:
        _container.intent_parser = _intent_parser
    if _manifest_service is not None:
        _container.manifest_service = _manifest_service


def _sync_module_from_container() -> None:
    """Sync module-level variables from container."""
    global _cognee_service, _indexing_service, _context_service, _settings, _manager
    global _cgc_service, _llm_provider, _intent_parser, _manifest_service

    _cognee_service = _container.cognee_service
    _indexing_service = _container.indexing_service
    _context_service = _container.context_service
    _settings = _container.settings
    _manager = _container.repository_manager
    _cgc_service = _container.cgc_service
    _llm_provider = _container.llm_provider
    _intent_parser = _container.intent_parser
    _manifest_service = _container.manifest_service


def _ensure_services() -> None:
    """Raise if any service is not initialized."""
    if _cognee_service is None or _indexing_service is None or _context_service is None:
        raise CogneeServiceError(
            "Backend services not initialized. Call initialize_backend() first."
        )
    _sync_container_services()
    _container.ensure_services()


def _load_repo_store() -> dict:
    indexer = _container.get_indexing_use_cases()
    return indexer._load_repo_store()


def _save_repo_store(data: dict) -> None:
    indexer = _container.get_indexing_use_cases()
    indexer._save_repo_store(data)


async def initialize_backend(settings: Optional[Settings] = None) -> None:
    """Initialize all backend services."""
    await _container.initialize(settings)
    _sync_module_from_container()


# --- System & Health ---


async def health() -> HealthResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_system_use_cases().health()


async def get_backend_status() -> BackendStatusResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_system_use_cases().get_backend_status()


async def get_app_settings() -> AppSettingsResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_system_use_cases().get_app_settings()


async def update_cognee_settings(
    request: CogneeSettingsRequest,
) -> AppSettingsResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_system_use_cases().update_cognee_settings(request)


async def update_provider(
    provider: str,
    base_url: str,
    model: str,
    api_key: str = "local",
) -> dict | ErrorResponse:
    _sync_container_services()
    res = await _container.get_system_use_cases().update_provider(provider, base_url, model, api_key)
    _sync_module_from_container()
    return res


# --- Indexing & Repository Summaries ---


async def index_repository(
    request: IndexRepositoryRequest,
) -> IndexRepositoryResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_indexing_use_cases().index_repository(request)


async def get_repository_summaries() -> RepositoryListResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_indexing_use_cases().get_repository_summaries()


# --- Context Generation ---


async def generate_context(
    request: GenerateContextRequest,
) -> ContextResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_context_use_cases().generate_context(request)


async def get_agent_context(
    request: AgentContextRequest,
) -> AgentContextResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_context_use_cases().get_agent_context(request)


# --- Memory & Datasets ---


async def list_datasets() -> DatasetListResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().list_datasets()


async def get_dataset_items(dataset_id: str) -> DatasetDataItemsResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().get_dataset_items(dataset_id)


async def forget_dataset(
    request: ForgetDatasetRequest,
) -> None | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().forget_dataset(request)


async def cognify_dataset(
    request: CognifyRequest,
) -> CognifyResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().cognify_dataset(request)


async def get_memory_stats() -> MemoryStatsResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().get_memory_stats()


async def get_memory_graph(
    dataset_name: Optional[str] = None,
) -> MemoryGraphResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().get_memory_graph(dataset_name)


async def get_memory_vectors() -> MemoryVectorsResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().get_memory_vectors()


async def get_dashboard_stats() -> DashboardStats | ErrorResponse:
    _sync_container_services()
    return await _container.get_memory_use_cases().get_dashboard_stats()


# --- Repository Management ---


async def list_repositories() -> RepositoryListResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_repository_use_cases().list_repositories()


async def create_repository(
    request: RepositoryCreateRequest,
) -> RepositoryResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_repository_use_cases().create_repository(request)


async def scan_repository(repo_id: str) -> ScanResultResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_repository_use_cases().scan_repository(repo_id)


async def get_repository_progress(repo_id: str) -> dict | ErrorResponse:
    _sync_container_services()
    return await _container.get_repository_use_cases().get_repository_progress(repo_id)


async def delete_repository(repo_id: str) -> dict | ErrorResponse:
    _sync_container_services()
    return await _container.get_repository_use_cases().delete_repository(repo_id)


async def generate_suggested_prompts(repo_id: str) -> dict[str, Any]:
    _sync_container_services()
    return await _container.get_repository_use_cases().generate_suggested_prompts(repo_id)


# --- Context Package Persistence ---


async def save_context_package(
    request: ContextPackageSaveRequest,
) -> ContextPackageResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_package_use_cases().save_context_package(request)


async def list_context_packages() -> ContextPackageListResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_package_use_cases().list_context_packages()


async def get_context_package(package_id: str) -> Optional[ContextPackageResponse] | ErrorResponse:
    _sync_container_services()
    return await _container.get_package_use_cases().get_context_package(package_id)


async def delete_context_package(package_id: str) -> dict | ErrorResponse:
    _sync_container_services()
    return await _container.get_package_use_cases().delete_context_package(package_id)


async def append_context_package(
    package_id: str,
    request: ContextPackageAppendRequest,
) -> Optional[ContextPackageResponse] | ErrorResponse:
    _sync_container_services()
    return await _container.get_package_use_cases().append_context_package(package_id, request)


# --- Benchmarks ---


async def run_benchmark() -> BenchmarkSuiteResponse | ErrorResponse:
    _sync_container_services()
    return await _container.get_benchmark_use_cases().run_benchmark()
