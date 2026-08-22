"""Application container and composition root for RE:Track.

Manages lifecycle and dependency wiring for domain and infrastructure services.
Instantiates use cases via constructor dependency injection of capability ports.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from app.application.ports.benchmark_runner import BenchmarkRunnerPort
from app.application.ports.cgc_service import CGCServicePort
from app.application.ports.context_cache import ContextCachePort
from app.application.ports.context_package_repository import ContextPackageRepositoryPort
from app.application.ports.context_service import ContextServicePort
from app.application.ports.filesystem import FileSystemPort
from app.application.ports.hardware_telemetry import HardwareTelemetryPort
from app.application.ports.indexing_service import IndexingServicePort
from app.application.ports.intent_parser import IntentParserPort
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.memory import MemoryPort
from app.application.ports.repository_manager import RepositoryManagerPort
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.application.ports.source_search import SourceSearchPort
from app.application.ports.summary_generator import SummaryGeneratorPort
from app.application.ports.workspace_authorization import WorkspaceAuthorizationPort
from app.application.use_cases.benchmarks import BenchmarkUseCases
from app.application.use_cases.context import BoundedConcurrencyGuard, ContextUseCases
from app.application.use_cases.context_packages import PackageUseCases
from app.application.use_cases.indexing import IndexingUseCases
from app.application.use_cases.memory import MemoryUseCases
from app.application.use_cases.repositories import RepositoryUseCases
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings, get_settings
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType
from app.services.benchmark_service import BenchmarkService
from app.services.cgc_service import CGCService
from app.services.cognee_service import CogneeService
from app.services.context_cache import ContextCacheEngine, context_cache
from app.services.context_package_repository import JsonContextPackageRepository
from app.services.context_service import ContextService
from app.services.hardware_telemetry import LocalHardwareTelemetryAdapter
from app.services.indexing_service import IndexingService
from app.services.intent_parser import IntentParserService
from app.services.llm_provider_service import LLMProviderService
from app.services.local_filesystem import LocalFileSystemAdapter
from app.services.manifest_service import ManifestService
from app.services.repository_manager import RepositoryManager
from app.services.repository_metadata_store import (
    JsonRepositoryMetadataStore,
    RepositoryMetadataStore,
)
from app.services.repository_summary import RepositorySummaryGenerator
from app.services.source_search_service import SourceSearchService
from app.services.workspace_authorization_service import WorkspaceAuthorizationService

logger = logging.getLogger(__name__)


class ApplicationContainer:
    """Composition root managing service lifecycles and injecting dependencies into use cases."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings: Optional[Settings] = settings
        self.cognee_service: Optional[CogneeService] = None
        self.indexing_service: Optional[IndexingService] = None
        self.context_service: Optional[ContextService] = None
        self.repository_manager: RepositoryManager = RepositoryManager()
        self.cgc_service: Optional[CGCService] = None
        self.llm_provider: Optional[LLMProviderService] = None
        self.intent_parser: Optional[IntentParserService] = None
        self.manifest_service: Optional[ManifestService] = None
        self.package_repository: JsonContextPackageRepository = JsonContextPackageRepository()
        self.summary_generator: RepositorySummaryGenerator = RepositorySummaryGenerator()
        self.context_cache: ContextCacheEngine = context_cache
        self.metadata_store: RepositoryMetadataStore = JsonRepositoryMetadataStore()
        self.filesystem: FileSystemPort = LocalFileSystemAdapter()
        self.telemetry: HardwareTelemetryPort = LocalHardwareTelemetryAdapter()
        self.source_search: SourceSearchPort = SourceSearchService(filesystem=self.filesystem)
        self.workspace_auth: WorkspaceAuthorizationPort = WorkspaceAuthorizationService(
            metadata_store=self.metadata_store
        )

        # Concurrency locks and guards
        self.indexing_lock: asyncio.Lock = asyncio.Lock()
        self.context_gen_lock: asyncio.Lock = asyncio.Lock()
        self.concurrency_guard: BoundedConcurrencyGuard = BoundedConcurrencyGuard(
            max_concurrent=1,
            max_queue=5,
            timeout=30.0,
        )

    def ensure_services(self) -> None:
        """Raise if core services are not initialized."""
        if (
            self.cognee_service is None
            or self.indexing_service is None
            or self.context_service is None
        ):
            raise CogneeServiceError(
                "Backend services not initialized. Call initialize_backend() first."
            )

    async def initialize(self, settings: Optional[Settings] = None) -> None:
        """Initialize all backend services."""
        self.settings = settings or self.settings or get_settings()
        self.cognee_service = CogneeService(self.settings)
        await self.cognee_service.initialize()

        llm_endpoint = os.environ.get("LLM_ENDPOINT", self.settings.ollama.llm_endpoint)
        llm_model = os.environ.get("LLM_MODEL", self.settings.ollama.llm_model)
        llm_api_key = os.environ.get("LLM_API_KEY", "lm-studio")
        provider_str = os.environ.get("LLM_PROVIDER", "lmstudio").lower()

        if "lm" in provider_str or "studio" in provider_str:
            p_type = ProviderType.LM_STUDIO
            if not os.environ.get("LLM_ENDPOINT"):
                llm_endpoint = "http://localhost:1234/v1"
        elif "ollama" in provider_str:
            p_type = ProviderType.OLLAMA
            if not os.environ.get("LLM_ENDPOINT"):
                llm_endpoint = "http://localhost:11434/v1"
        else:
            p_type = ProviderType.OPENAI_COMPATIBLE

        self.llm_provider = LLMProviderService(
            provider_type=p_type,
            base_url=llm_endpoint,
            api_key=llm_api_key,
            default_model=llm_model,
        )

        self.intent_parser = IntentParserService(self.llm_provider)
        self.cgc_service = CGCService()
        self.manifest_service = ManifestService()
        self.indexing_service = IndexingService(
            cognee_service=self.cognee_service,
            manifest_service=self.manifest_service,
        )
        self.context_service = ContextService(
            cognee_service=self.cognee_service,
        )

        logger.info(
            "ApplicationContainer initialized | provider=%s | endpoint=%s | model=%s",
            p_type.value,
            llm_endpoint,
            llm_model,
        )

    async def update_provider(
        self,
        provider: str,
        base_url: str,
        model: str,
        api_key: str = "local",
    ) -> dict:
        """Hot-reload the active LLM provider."""
        prov_lower = provider.lower()
        if "lm" in prov_lower or "studio" in prov_lower:
            p_type = ProviderType.LM_STUDIO
        elif "ollama" in prov_lower:
            p_type = ProviderType.OLLAMA
        else:
            p_type = ProviderType.OPENAI_COMPATIBLE

        self.llm_provider = LLMProviderService(
            provider_type=p_type,
            base_url=base_url,
            model=model,
            api_key=api_key,
        )
        self.intent_parser = IntentParserService(self.llm_provider)

        health_status = await self.llm_provider.check_health()
        loaded = [m.model_id for m in health_status.loaded_models]

        return {
            "success": True,
            "provider": provider,
            "base_url": base_url,
            "model": model,
            "reachable": health_status.is_reachable,
            "loaded_models": loaded,
            "quantization_warning": health_status.quantization_warning,
        }

    # Factory methods returning explicit use cases with injected dependencies:

    def get_context_use_cases(self) -> ContextUseCases:
        return ContextUseCases(
            context_service=self.context_service,
            cognee_service=self.cognee_service,
            indexing_service=self.indexing_service,
            intent_parser=self.intent_parser,
            llm_provider=self.llm_provider,
            cgc_service=self.cgc_service,
            summary_generator=self.summary_generator,
            context_cache=self.context_cache,
            context_gen_lock=self.context_gen_lock,
            ensure_services_fn=self.ensure_services,
            source_search=self.source_search,
            filesystem=self.filesystem,
            workspace_auth=self.workspace_auth,
            concurrency_guard=self.concurrency_guard,
        )

    def get_indexing_use_cases(self) -> IndexingUseCases:
        return IndexingUseCases(
            indexing_service=self.indexing_service,
            indexing_lock=self.indexing_lock,
            ensure_services_fn=self.ensure_services,
            summary_generator=self.summary_generator,
            metadata_store=self.metadata_store,
            filesystem=self.filesystem,
            workspace_auth=self.workspace_auth,
        )

    def get_repository_use_cases(self) -> RepositoryUseCases:
        return RepositoryUseCases(
            repository_manager=self.repository_manager,
            indexing_service=self.indexing_service,
            llm_provider=self.llm_provider,
            summary_generator=self.summary_generator,
            cognee_service=self.cognee_service,
            metadata_store=self.metadata_store,
            filesystem=self.filesystem,
            workspace_auth=self.workspace_auth,
        )

    def get_memory_use_cases(self) -> MemoryUseCases:
        return MemoryUseCases(
            cognee_service=self.cognee_service,
            settings_getter=lambda: self.settings or get_settings(),
            ensure_services_fn=self.ensure_services,
            package_repository=self.package_repository,
            metadata_store=self.metadata_store,
        )

    def get_package_use_cases(self) -> PackageUseCases:
        return PackageUseCases(
            package_repository=self.package_repository,
        )

    def get_system_use_cases(self) -> SystemUseCases:
        return SystemUseCases(
            settings_getter=lambda: self.settings or get_settings(),
            cognee_service_getter=lambda: self.cognee_service,
            llm_provider_getter=lambda: self.llm_provider,
            provider_updater_fn=self.update_provider,
            telemetry_port=self.telemetry,
        )

    def get_benchmark_use_cases(self) -> BenchmarkUseCases:
        bench_service = BenchmarkService(
            generate_context_fn=lambda req: self.get_context_use_cases().generate_context(req),
            health_fn=lambda: self.get_system_use_cases().health(),
            metadata_store=self.metadata_store,
            settings_getter=lambda: self.settings or get_settings(),
        )
        return BenchmarkUseCases(
            benchmark_runner=bench_service,
        )

    @classmethod
    def create(cls, settings: Optional[Settings] = None) -> "ApplicationContainer":
        """Factory method to construct an uninitialized application container."""
        return cls(settings=settings)


# Composition root container reference (lazy, not instantiated at module import time)
_container: Optional[ApplicationContainer] = None


def get_container(settings: Optional[Settings] = None) -> ApplicationContainer:
    """Get or lazily construct the active application container instance.

    Restricted to composition-root boundaries (FastAPI lifespan, API routers, CLI facade).
    Must NEVER be called inside application use cases, domain entities, or ports.
    """
    global _container
    if _container is None:
        _container = ApplicationContainer.create(settings=settings)
    return _container


def set_container(container: Optional[ApplicationContainer]) -> None:
    """Explicitly set the active application container instance.

    Used by application lifespan handlers and isolated test fixtures.
    """
    global _container
    _container = container


def reset_container() -> None:
    """Reset the active application container reference to None for test isolation."""
    global _container
    _container = None

