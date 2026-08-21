"""Services package for RE:Track.

Uses lazy attribute resolution to prevent eager loading of heavyweight
vendor SDKs (Cognee, FastAPI, Starlette) during package import.
"""

from typing import Any

__all__ = ["CogneeService", "ContextService", "IndexingService", "ManifestService"]


def __getattr__(name: str) -> Any:
    if name == "CogneeService":
        from app.services.cognee_service import CogneeService
        return CogneeService
    elif name == "ContextService":
        from app.services.context_service import ContextService
        return ContextService
    elif name == "IndexingService":
        from app.services.indexing_service import IndexingService
        return IndexingService
    elif name == "ManifestService":
        from app.services.manifest_service import ManifestService
        return ManifestService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
