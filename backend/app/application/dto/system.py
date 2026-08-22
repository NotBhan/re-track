"""System health, status, and settings DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health check response."""

    status: str = Field(description="Health status: 'ok' or 'degraded'")
    ollama_reachable: bool = Field(description="Whether Ollama is reachable")
    cognee_initialized: bool = Field(description="Whether CogneeService is initialized")
    version: str = Field(default="0.1.0", description="Backend version")
    ram_total_gb: float = Field(default=0.0, description="Total host RAM in GB")
    ram_used_gb: float = Field(default=0.0, description="Used host RAM in GB")
    ram_percent: float = Field(default=0.0, description="Host RAM usage percentage")
    high_memory_pressure: bool = Field(default=False, description="Whether RAM pressure is above 90%")
    cpu_percent: float = Field(default=0.0, description="Host CPU utilization percent")
    gpu_presence: str = Field(default="None", description="Detected GPU model or family ('AMD', 'NVIDIA', 'None')")
    gpu_name: Optional[str] = Field(default=None, description="GPU device model name")
    vram_total_gb: float = Field(default=0.0, description="Total GPU VRAM in GB")
    vram_used_gb: float = Field(default=0.0, description="Used GPU VRAM in GB")
    execution_device: str = Field(default="CPU", description="Actual runtime execution device ('CPU', 'GPU', 'UNKNOWN')")
    active_model: Optional[str] = Field(default=None, description="Currently active model loaded in memory")
    # Phase 9C Detailed Health & Operational Status Fields
    health_state: str = Field(default="healthy", description="Operational classification: 'healthy', 'degraded', 'unavailable', 'not_configured'")
    storage_canonical_exists: bool = Field(default=True, description="Whether ~/.retrack/ storage directory exists")
    storage_canonical_writable: bool = Field(default=True, description="Whether ~/.retrack/ storage directory is writable")
    legacy_storage_detected: bool = Field(default=False, description="Whether ~/.andes/ legacy storage directory exists")
    repository_count: int = Field(default=0, description="Total number of registered repositories")
    context_package_count: int = Field(default=0, description="Total number of saved context packages")
    cache_files_count: int = Field(default=0, description="Total number of cached AST / context files")
    cache_total_bytes: int = Field(default=0, description="Total size in bytes of cache files")
    concurrency_queue_depth: int = Field(default=0, description="Current waiting request count in concurrency queue")
    concurrency_queue_capacity: int = Field(default=5, description="Maximum concurrency queue capacity")
    concurrency_available_slots: int = Field(default=1, description="Available execution slots in concurrency guard")
    mcp_server_ready: bool = Field(default=True, description="Whether MCP runtime services are operational")
    recent_errors_count: int = Field(default=0, description="Number of recent error log events")


class DetailedHealthResponse(HealthResponse):
    """Detailed operational health and diagnostic status."""

    diagnostics_log_entries: list[dict] = Field(default_factory=list, description="Recent sanitized log records")
    storage_paths: dict[str, str] = Field(default_factory=dict, description="Storage paths summary")


class BackendStatusResponse(BaseModel):
    """Detailed backend status."""

    status: str = Field(description="Health status: 'ok' or 'degraded'")
    ollama_reachable: bool = Field(description="Whether Ollama is reachable")
    ollama_host: str = Field(description="Ollama host")
    ollama_port: int = Field(description="Ollama port")
    llm_model: str = Field(description="Current LLM model name")
    embedding_model: str = Field(description="Current embedding model name")
    vector_db: str = Field(description="Vector database provider")
    graph_db: str = Field(description="Graph database provider")
    relational_db: str = Field(description="Relational database provider")
    data_root: str = Field(description="Data storage root path")
    system_root: str = Field(description="System storage root path")
    cognee_initialized: bool = Field(description="Whether CogneeService is initialized")
    gpu_presence: str = Field(default="None", description="GPU presence")
    execution_device: str = Field(default="CPU", description="Runtime execution device")


class CogneeSettingsRequest(BaseModel):
    """Request to update Cognee configuration."""

    vector_db: Optional[str] = Field(default=None, description="Vector database provider (lancedb, qdrant, milvus)")
    graph_db: Optional[str] = Field(default=None, description="Graph database provider (kuzu, ladybug, networkx)")
    enable_kg_extraction: Optional[bool] = Field(default=None, description="Enable knowledge graph extraction")
    auto_link_entities: Optional[bool] = Field(default=None, description="Auto-link detected symbols & entities")
    caching: Optional[bool] = Field(default=None, description="Enable session memory caching")


class AppSettingsResponse(BaseModel):
    """Current application configuration."""

    success: bool = Field(default=True, description="Whether query succeeded")
    vector_db: str = Field(description="Active vector database provider")
    graph_db: str = Field(description="Active graph database provider")
    relational_db: str = Field(description="Active relational database provider")
    enable_kg_extraction: bool = Field(description="Whether knowledge graph extraction is enabled")
    auto_link_entities: bool = Field(description="Whether auto-linking is enabled")
    caching: bool = Field(description="Whether session memory caching is enabled")
    data_root: str = Field(description="Data root storage directory")
    system_root: str = Field(description="System root storage directory")
    llm_provider: str = Field(default="ollama", description="Active LLM provider")
    llm_host: str = Field(default="localhost", description="LLM host")
    llm_port: int = Field(default=11434, description="LLM port")
    llm_model: str = Field(default="phi4-mini", description="Active LLM model")
    embedding_model: str = Field(default="nomic-embed-text:latest", description="Active embedding model")
