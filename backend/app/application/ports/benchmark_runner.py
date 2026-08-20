"""Abstract benchmark runner port."""

from typing import Any, Optional, Protocol


class BenchmarkRunnerPort(Protocol):
    """Port for executing repository context benchmark suites."""

    async def run_benchmark_suite(
        self,
        questions: Optional[list[str]] = None,
        target_repo_path: Optional[str] = None,
    ) -> Any:
        """Run benchmark evaluation suite across questions and synthesize performance scores."""
        ...
