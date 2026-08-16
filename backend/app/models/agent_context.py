"""
Request and response schemas for Agent Middleware API (/api/v1/context).
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentContextRequest(BaseModel):
    """Request payload sent by external coding agents to get optimized context."""

    task_prompt: str = Field(..., min_length=1, description="Developer request or question")
    repository_path: str = Field(..., min_length=1, description="Path to the repository")
    dataset_name: Optional[str] = Field(
        default=None, description="Optional logical memory dataset name"
    )
    max_tokens: int = Field(
        default=2500, ge=200, le=8000, description="Target token budget for context package"
    )
    include_structural_graph: bool = Field(
        default=True, description="Whether to include CGC call graph and dependency trees"
    )


class AgentContextResponse(BaseModel):
    """Response payload returned to external coding agents."""

    success: bool = True
    context_markdown: str = Field(description="Rendered Markdown context package")
    task_summary: str = Field(description="Parsed objective summary")
    intent_category: str = Field(description="Identified intent category")
    extracted_symbols: list[str] = Field(default_factory=list)
    callers: list[str] = Field(default_factory=list)
    callees: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    quantization_warning: Optional[str] = None
    estimated_tokens: int = 0
    generation_time_ms: int = 0
