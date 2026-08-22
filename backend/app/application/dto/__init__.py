"""Application DTOs (Data Transfer Objects) for RE:Track.

This package defines transport-independent request and response data contracts
owned by the application layer.
"""

from app.application.dto.common import ErrorResponse
from app.application.dto.context import (
    AgentContextRequest,
    AgentContextResponse,
    ContextResponse,
    GenerateContextRequest,
)
from app.application.dto.indexing import (
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    IndexedRepositoryListResponse,
    RepoArchInfo,
    RepoComponentInfo,
    RepositorySummaryInfo,
)
from app.application.dto.repositories import (
    ASTCallGraphResponse,
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryResponse,
    RepositorySummaryResponse,
    ScanResultResponse,
    SourceSearchResponse,
    SourceSearchResultItem,
)
from app.application.dto.memory import (
    CognifyRequest,
    CognifyResponse,
    DashboardStats,
    DatasetDataItemsResponse,
    DatasetInfo,
    DatasetListResponse,
    ForgetDatasetRequest,
    ForgetDatasetResponse,
    MemoryDataItem,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryGraphResponse,
    MemoryStatsResponse,
    MemoryVectorsResponse,
    VectorDatasetInfo,
)
from app.application.dto.packages import (
    ContextPackageAppendRequest,
    ContextPackageListResponse,
    ContextPackageResponse,
    ContextPackageSaveRequest,
)
from app.application.dto.system import (
    AppSettingsResponse,
    BackendStatusResponse,
    CogneeSettingsRequest,
    DetailedHealthResponse,
    HealthResponse,
)
from app.application.dto.benchmarks import (
    BenchmarkResultItem,
    BenchmarkSuiteResponse,
)

__all__ = [
    # Common
    "ErrorResponse",
    # Context
    "GenerateContextRequest",
    "ContextResponse",
    "AgentContextRequest",
    "AgentContextResponse",
    # Indexing
    "IndexRepositoryRequest",
    "IndexRepositoryResponse",
    "RepoArchInfo",
    "RepoComponentInfo",
    "RepositorySummaryInfo",
    "IndexedRepositoryListResponse",
    # Repositories
    "RepositoryCreateRequest",
    "RepositoryResponse",
    "RepositoryListResponse",
    "ScanResultResponse",
    "RepositorySummaryResponse",
    "ASTCallGraphResponse",
    "SourceSearchResultItem",
    "SourceSearchResponse",
    # Memory
    "ForgetDatasetRequest",
    "ForgetDatasetResponse",
    "DatasetInfo",
    "DatasetListResponse",
    "MemoryGraphNode",
    "MemoryGraphEdge",
    "MemoryGraphResponse",
    "VectorDatasetInfo",
    "MemoryVectorsResponse",
    "MemoryDataItem",
    "DatasetDataItemsResponse",
    "CognifyRequest",
    "CognifyResponse",
    "MemoryStatsResponse",
    "DashboardStats",
    # Packages
    "ContextPackageSaveRequest",
    "ContextPackageResponse",
    "ContextPackageListResponse",
    "ContextPackageAppendRequest",
    # System
    "HealthResponse",
    "DetailedHealthResponse",
    "BackendStatusResponse",
    "CogneeSettingsRequest",
    "AppSettingsResponse",
    # Benchmarks
    "BenchmarkResultItem",
    "BenchmarkSuiteResponse",
]
