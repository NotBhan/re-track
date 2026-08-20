"""Application use cases for RE:Track.

Every use case receives its required dependencies via constructor injection.
"""

from app.application.use_cases.benchmarks import BenchmarkUseCases
from app.application.use_cases.context import ContextUseCases
from app.application.use_cases.context_packages import PackageUseCases
from app.application.use_cases.indexing import IndexingUseCases
from app.application.use_cases.memory import MemoryUseCases
from app.application.use_cases.repositories import RepositoryUseCases
from app.application.use_cases.system import SystemUseCases

__all__ = [
    "BenchmarkUseCases",
    "ContextUseCases",
    "PackageUseCases",
    "IndexingUseCases",
    "MemoryUseCases",
    "RepositoryUseCases",
    "SystemUseCases",
]
