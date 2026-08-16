"""Backend API layer for RE:Track (RefinedEngine Track).

Exposes backend services through async commands for Tauri IPC.
No business logic — all work delegates to existing services.
"""

from app.api.commands import (
    forget_dataset,
    generate_context,
    get_agent_context,
    get_backend_status,
    health,
    index_repository,
    initialize_backend,
)
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.api.schemas import (
    BackendStatusResponse,
    ContextResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    ForgetDatasetResponse,
    GenerateContextRequest,
    HealthResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
)

__all__ = [
    # Commands
    "health",
    "get_backend_status",
    "index_repository",
    "generate_context",
    "get_agent_context",
    "forget_dataset",
    "initialize_backend",
    # Request schemas
    "IndexRepositoryRequest",
    "GenerateContextRequest",
    "ForgetDatasetRequest",
    "AgentContextRequest",
    # Response schemas
    "HealthResponse",
    "BackendStatusResponse",
    "IndexRepositoryResponse",
    "ContextResponse",
    "AgentContextResponse",
    "ForgetDatasetResponse",
    "ErrorResponse",
]
