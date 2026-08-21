"""Benchmark execution API router.

Exposes context synthesis and retrieval benchmark runs.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import ErrorResponse
from app.application.container import get_container
from app.application.use_cases.benchmarks import BenchmarkUseCases

router = APIRouter(tags=["benchmarks"])


def get_benchmark_use_cases() -> BenchmarkUseCases:
    return get_container().get_benchmark_use_cases()


@router.post("/benchmarks/run")
async def benchmarks_run_endpoint(
    bench_use_cases: BenchmarkUseCases = Depends(get_benchmark_use_cases),
) -> dict[str, Any]:
    """Run a benchmark suite."""
    result = await bench_use_cases.run_benchmark()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
