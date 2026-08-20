"""Benchmark result and suite DTOs."""

from pydantic import BaseModel, Field


class BenchmarkResultItem(BaseModel):
    """A single benchmark query measurement."""

    question: str = Field(description="Benchmark question")
    baseline_tokens: int = Field(default=0, description="Tokens in full eligible repo baseline")
    context_tokens: int = Field(default=0, description="Tokens in generated RE:Track context package")
    compression_ratio: float = Field(default=1.0, description="baseline_tokens / context_tokens")
    token_savings_percent: float = Field(default=0.0, description="Percentage of prompt tokens saved")
    retrieval_time_ms: float = Field(default=0.0, description="Retrieval latency in milliseconds")
    total_time_ms: float = Field(default=0.0, description="Total latency in milliseconds")
    section_count: int = Field(default=0, description="Number of sections generated")
    retrieved_memories: int = Field(default=0, description="Memories retrieved from index")
    accuracy_status: str = Field(default="Not evaluated (requires ground truth set)", description="Context accuracy evaluation status")
    passed: bool = Field(default=False, description="Whether query context met quality criteria")


class BenchmarkSuiteResponse(BaseModel):
    """Response from a benchmark suite run."""

    success: bool = Field(description="Whether the suite completed")
    results: list[BenchmarkResultItem] = Field(default_factory=list)
    avg_retrieval_latency_ms: float = Field(default=0.0, description="Average retrieval latency")
    avg_total_latency_ms: float = Field(default=0.0, description="Average total latency")
    avg_token_savings_percent: float = Field(default=0.0, description="Average token savings percentage")
    avg_compression_ratio: float = Field(default=1.0, description="Average compression ratio")
    accuracy_summary: str = Field(default="Not evaluated (no ground truth set)", description="Accuracy evaluation summary")
    total_questions: int = Field(default=0, description="Total questions tested")
    run_metadata: dict = Field(default_factory=dict, description="Immutable run environment metadata")
