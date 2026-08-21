"""Application ports for RE:Track.

Defines abstract capability protocols implemented by infrastructure adapters.
"""

from app.application.ports.benchmark_runner import BenchmarkRunnerPort
from app.application.ports.cgc_service import CGCServicePort
from app.application.ports.context_cache import ContextCachePort
from app.application.ports.context_package_repository import ContextPackageRepositoryPort
from app.application.ports.context_service import ContextServicePort
from app.application.ports.filesystem import FileSystemPort
from app.application.ports.hardware_telemetry import (
    HardwareTelemetry,
    HardwareTelemetryPort,
)
from app.application.ports.indexing_service import IndexingServicePort
from app.application.ports.intent_parser import IntentParserPort
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.memory import (
    MemoryDatasetPort,
    MemoryIngestionPort,
    MemoryLifecyclePort,
    MemoryPort,
    MemoryRetrievalPort,
    MemoryTopologyPort,
)
from app.application.ports.repository_manager import RepositoryManagerPort
from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.application.ports.source_search import SourceSearchPort
from app.application.ports.summary_generator import SummaryGeneratorPort

__all__ = [
    "BenchmarkRunnerPort",
    "CGCServicePort",
    "ContextCachePort",
    "ContextPackageRepositoryPort",
    "ContextServicePort",
    "FileSystemPort",
    "HardwareTelemetry",
    "HardwareTelemetryPort",
    "IndexingServicePort",
    "IntentParserPort",
    "LLMProviderPort",
    "MemoryDatasetPort",
    "MemoryIngestionPort",
    "MemoryLifecyclePort",
    "MemoryPort",
    "MemoryRetrievalPort",
    "MemoryTopologyPort",
    "RepositoryManagerPort",
    "RepositoryMetadataPort",
    "SourceSearchPort",
    "SummaryGeneratorPort",
]
