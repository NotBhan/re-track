"""API routers package for RE:Track.

Exports domain routers and provides registration helper for FastAPI application assembly.
"""

from fastapi import FastAPI

from app.api.routers.benchmarks import router as benchmarks_router
from app.api.routers.context import router as context_router
from app.api.routers.memory import router as memory_router
from app.api.routers.packages import router as packages_router
from app.api.routers.repositories import router as repositories_router
from app.api.routers.settings import router as settings_router
from app.api.routers.system import router as system_router

__all__ = [
    "system_router",
    "repositories_router",
    "context_router",
    "memory_router",
    "packages_router",
    "benchmarks_router",
    "settings_router",
    "register_routers",
]


def register_routers(app: FastAPI) -> None:
    """Register all domain routers onto the FastAPI application."""
    app.include_router(system_router)
    app.include_router(repositories_router)
    app.include_router(context_router)
    app.include_router(memory_router)
    app.include_router(packages_router)
    app.include_router(benchmarks_router)
    app.include_router(settings_router)
