"""Benchmark runner compatibility facade for RE:Track.

Delegates execution to app.services.benchmark_service.
"""

from typing import Optional
from app.application.dto import BenchmarkResultItem, BenchmarkSuiteResponse
from app.services.benchmark_service import (
    BenchmarkService,
    compute_baseline_tokens,
    get_git_revision,
    ELIGIBLE_EXTENSIONS,
    IGNORED_DIRS,
    IGNORED_FILES,
)

# Compatibility aliases
_compute_baseline_tokens = compute_baseline_tokens
_get_git_revision = get_git_revision


async def run_benchmark_suite(
    questions: Optional[list[str]] = None,
    target_repo_path: Optional[str] = None,
) -> BenchmarkSuiteResponse:
    """Compatibility forwarder: run benchmark suite via application container."""
    from app.application.container import get_container
    container = get_container()
    return await container.get_benchmark_use_cases().run_benchmark(
        questions=questions,
        target_repo_path=target_repo_path,
    )
