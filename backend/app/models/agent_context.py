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
        default=8000, ge=100, description="Target token budget for context package (default: 8000)"
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
    retrieval_time_ms: int = 0
    ranking_time_ms: int = 0
    synthesis_time_ms: int = 0
    total_time_ms: int = 0
    # Inference telemetry
    model_invoked: bool = Field(default=False, description="Whether LLM inference was executed")
    provider_identity: Optional[str] = Field(default=None, description="Active LLM provider identifier")
    model_name: Optional[str] = Field(default=None, description="Active model name")
    inference_status: str = Field(default="not_configured", description="Inference status")
    fallback_used: bool = Field(default=False, description="Whether fallback was used")
    fallback_reason: Optional[str] = Field(default=None, description="Reason fallback was used")
    inference_time_ms: int = Field(default=0, description="Inference latency in milliseconds")
    # Evidence evaluation
    evidence_state: str = Field(default="sufficient", description="Evidence state")
    evidence_score: float = Field(default=1.0, description="Evidence score between 0.0 and 1.0")
    evidence_confidence: float = Field(default=1.0, description="Evidence confidence between 0.0 and 1.0")
    evidence_files: list[str] = Field(default_factory=list, description="Files containing direct code evidence")
    evidence_symbols: list[str] = Field(default_factory=list, description="Verified AST symbols supporting evidence")
    evidence_relationships: list[str] = Field(default_factory=list, description="Verified AST relationships")
    observed_evidence: list[str] = Field(default_factory=list, description="Observed repository facts")
    missing_evidence: list[str] = Field(default_factory=list, description="Missing evidence items")
    abstained: bool = Field(default=False, description="Whether generation abstained")
    abstention_reason: Optional[str] = Field(default=None, description="Abstention reason")
    model_claims_allowed: bool = Field(default=True, description="Whether model claims are allowed")


