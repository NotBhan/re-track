"""Benchmark runner for AndesContext.

Executes real benchmark suites against the generate_context endpoint,
measuring latency, token counts, and retrieval quality.
"""

import time
from dataclasses import dataclass, field


@dataclass
class BenchmarkResult:
    question: str
    latency_ms: float
    token_count: int
    section_count: int
    retrieved_memories: int
    compression_ratio: float
    quality_score: float = 0.0
    passed: bool = False


@dataclass
class BenchmarkSuite:
    results: list[BenchmarkResult] = field(default_factory=list)
    avg_latency_ms: float = 0.0
    avg_tokens: float = 0.0
    pass_rate: float = 0.0
    total_questions: int = 0


async def run_benchmark_suite(questions: list[str] | None = None) -> BenchmarkSuite:
    from app.api.commands import _load_repo_store, generate_context, initialize_backend
    from app.api.schemas import GenerateContextRequest

    await initialize_backend()

    if questions is None:
        questions = [
            "How does the authentication middleware work?",
            "What is the project structure?",
            "How do I add a new API endpoint?",
        ]

    store = _load_repo_store()
    datasets = list(store.keys()) if store else ["default"]
    results = []

    for q in questions:
        start = time.monotonic()
        try:
            resp = await generate_context(GenerateContextRequest(
                task=q, datasets=datasets, top_k=20,
            ))
            latency = (time.monotonic() - start) * 1000
            if hasattr(resp, "section_count"):
                results.append(BenchmarkResult(
                    question=q,
                    latency_ms=latency,
                    token_count=resp.token_estimate,
                    section_count=resp.section_count,
                    retrieved_memories=resp.retrieved_memories,
                    compression_ratio=resp.compression_ratio,
                    quality_score=min(100.0, resp.section_count * 15 + resp.compression_ratio * 50),
                    passed=resp.section_count >= 3,
                ))
            else:
                # ErrorResponse — benchmark failed for this question
                latency = (time.monotonic() - start) * 1000
                results.append(BenchmarkResult(
                    question=q, latency_ms=latency, token_count=0,
                    section_count=0, retrieved_memories=0, compression_ratio=0,
                ))
        except Exception:
            latency = (time.monotonic() - start) * 1000
            results.append(BenchmarkResult(
                question=q, latency_ms=latency, token_count=0,
                section_count=0, retrieved_memories=0, compression_ratio=0,
            ))

    n = max(len(results), 1)
    return BenchmarkSuite(
        results=results,
        avg_latency_ms=sum(r.latency_ms for r in results) / n,
        avg_tokens=sum(r.token_count for r in results) / n,
        pass_rate=sum(1 for r in results if r.passed) / n * 100,
        total_questions=len(results),
    )
