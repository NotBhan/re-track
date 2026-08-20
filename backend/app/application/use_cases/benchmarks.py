"""Benchmark use cases for RE:Track.

Coordinates execution of reproducible benchmark suites measuring tokens, latency, and compression.
All dependencies are explicitly injected via constructor capability ports.
"""

import logging
import time
from typing import Any, Callable, Coroutine, Optional, Union

from app.application.dto import BenchmarkSuiteResponse, ErrorResponse
from app.application.ports.benchmark_runner import BenchmarkRunnerPort

logger = logging.getLogger(__name__)


class BenchmarkUseCases:
    """Orchestrates benchmark suite executions."""

    def __init__(
        self,
        benchmark_runner: Optional[Union[BenchmarkRunnerPort, Callable[..., Coroutine[Any, Any, BenchmarkSuiteResponse]]]] = None,
    ) -> None:
        self._runner = benchmark_runner

    async def run_benchmark(
        self,
        questions: Optional[list[str]] = None,
        target_repo_path: Optional[str] = None,
    ) -> BenchmarkSuiteResponse | ErrorResponse:
        """Run an authoritative benchmark suite measuring compression and latency."""
        start = time.monotonic()
        logger.info("use_case: run_benchmark()")
        try:
            if not self._runner:
                raise ValueError("Benchmark runner is not configured")

            if hasattr(self._runner, "run_benchmark_suite"):
                result = await self._runner.run_benchmark_suite(questions=questions, target_repo_path=target_repo_path)
            else:
                result = await self._runner(questions=questions, target_repo_path=target_repo_path)

            elapsed = time.monotonic() - start
            logger.info("use_case: run_benchmark() complete | %.2fs", elapsed)
            return result
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: run_benchmark() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Benchmark run failed: {e}",
            )
