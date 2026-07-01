"""
FastAPI HTTP server for AndesContext backend.

Exposes backend commands as HTTP endpoints for Tauri IPC bridge.
This is a thin transport layer — all business logic stays in commands.py.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.commands import (
    health,
    get_backend_status,
    get_dashboard_stats,
    index_repository,
    generate_context,
    forget_dataset,
    list_datasets,
    get_repository_summaries,
    initialize_backend,
)
from app.api.schemas import (
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    IndexRepositoryRequest,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize backend on startup, cleanup on shutdown."""
    logger.info("Starting AndesContext HTTP server")
    try:
        await initialize_backend()
        logger.info("Backend initialized successfully")
    except Exception as e:
        logger.error("Backend initialization failed: %s", e)
    yield
    logger.info("Shutting down AndesContext HTTP server")


app = FastAPI(
    title="AndesContext API",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow Tauri to call from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_endpoint():
    """Check system health."""
    result = await health()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result.model_dump()


@app.get("/datasets")
async def datasets_endpoint():
    """List all stored datasets."""
    result = await list_datasets()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.get("/status")
async def status_endpoint():
    """Get backend status."""
    result = await get_backend_status()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=503, detail=result.model_dump())
    return result.model_dump()


@app.post("/index")
async def index_endpoint(request: IndexRepositoryRequest):
    """Index a repository."""
    result = await index_repository(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.post("/context")
async def context_endpoint(request: GenerateContextRequest):
    """Generate a Context Package."""
    result = await generate_context(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.post("/forget")
async def forget_endpoint(request: ForgetDatasetRequest):
    """Forget a dataset."""
    result = await forget_dataset(request)
    if result is None:
        return {"success": True, "message": "Dataset forgotten successfully"}
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.get("/repositories")
async def repositories_endpoint():
    """List all indexed repositories with metadata."""
    result = await get_repository_summaries()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.get("/dashboard/stats")
async def dashboard_stats_endpoint():
    """Get aggregate dashboard statistics."""
    result = await get_dashboard_stats()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
