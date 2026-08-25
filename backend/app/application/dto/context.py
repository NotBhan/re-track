"""Context generation and synthesis DTOs."""

from typing import Optional
from pydantic import BaseModel, Field

from app.models.agent_context import AgentContextRequest, AgentContextResponse


class GenerateContextRequest(BaseModel):
    """Request to generate a Context Package for a developer task."""

    task: str = Field(
        ..., min_length=1, description="Developer request or question"
    )
    datasets: list[str] = Field(
        default_factory=list, description="Datasets to search"
    )
    top_k: Optional[int] = Field(default=20, ge=1, le=100, description="Maximum memories to retrieve")


class ContextResponse(BaseModel):
    """Response containing a generated Context Package."""

    success: bool = Field(description="Whether generation succeeded")
    task: str = Field(description="Original developer request")
    objective: str = Field(description="Derived objective from the task")
    markdown: str = Field(description="Generated Markdown context")
    section_count: int = Field(description="Number of sections")
    source_count: int = Field(description="Number of memory sources used")
    token_estimate: int = Field(description="Estimated token count")
    dataset: str = Field(description="Datasets searched")
    # Metadata fields
    retrieved_memories: int = Field(default=0, description="Total memories retrieved")
    deduplicated_memories: int = Field(default=0, description="Memories after dedup")
    compressed_memories: int = Field(default=0, description="Memories after compression")
    compression_ratio: float = Field(default=1.0, description="Input/output token ratio")
    retrieval_time_ms: int = Field(default=0, description="Time spent in Cognee recall")
    total_time_ms: int = Field(default=0, description="Total generation time")
    # Reference fields
    reference_count: int = Field(default=0, description="Number of traceable references")
    section_headings: list[str] = Field(default_factory=list, description="Headings of generated sections")
    # Model invocation telemetry
    model_invoked: bool = Field(default=False, description="Whether LLM inference was executed")
    provider_identity: Optional[str] = Field(default=None, description="Active LLM provider identifier")
    model_name: Optional[str] = Field(default=None, description="Active LLM model used")
    inference_status: str = Field(default="not_configured", description="Status of inference (completed, failed, not_configured, fallback)")
    fallback_used: bool = Field(default=False, description="Whether deterministic fallback was used")
    fallback_reason: Optional[str] = Field(default=None, description="Reason deterministic fallback was used")
    inference_time_ms: int = Field(default=0, description="Time spent in LLM inference")

