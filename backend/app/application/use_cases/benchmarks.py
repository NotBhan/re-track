"""Benchmark use cases for RE:Track.

Coordinates execution of reproducible benchmark suites measuring tokens, latency, and compression.
All dependencies are explicitly injected via constructor.
"""

import logging
import time
from typing import Any, Callable, Coroutine, Optional

from app.application.dto import BenchmarkSuiteResponse, ErrorResponse

logger = logging.getLogger(__name__)


class BenchmarkUseCases:
    """Orchestrates benchmark suite executions."""

    def __init__(
        self,
        benchmark_runner_fn: Callable[..., Coroutine[Any, Any, BenchmarkSuiteResponse]],
    ) -> None:
        self._runner = benchmark_runner_fn

    async def run_benchmark(
        self,
        questions: Optional[list[str]] = None,
        target_repo_path: Optional[str] = None,
    ) -> BenchmarkSuiteResponse | ErrorResponse:
        """Run an authoritative benchmark suite measuring compression and latency."""
        start = time.monotonic()
        logger.info("use_case: run_benchmark()")
        try:
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
