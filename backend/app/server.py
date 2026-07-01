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
    index_repository,
    generate_context,
    forget_dataset,
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
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
