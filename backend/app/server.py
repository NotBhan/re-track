"""
FastAPI HTTP server for RE:Track (RefinedEngine Track) backend.

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
    get_memory_stats,
    index_repository,
    generate_context,
    forget_dataset,
    list_datasets,
    get_repository_summaries,
    run_benchmark,
    initialize_backend,
    list_repositories,
    create_repository,
    scan_repository,
    delete_repository,
    save_context_package,
    list_context_packages,
    get_context_package,
    delete_context_package,
    append_context_package,
    get_repository_progress,
)
from app.api.schemas import (
    ContextPackageAppendRequest,
    ContextPackageSaveRequest,
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    IndexRepositoryRequest,
    RepositoryCreateRequest,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize backend on startup, cleanup on shutdown."""
    logger.info("Starting RE:Track HTTP server")
    try:
        await initialize_backend()
        logger.info("Backend initialized successfully")
    except Exception as e:
        logger.error("Backend initialization failed: %s", e)
    yield
    logger.info("Shutting down RE:Track HTTP server")


app = FastAPI(
    title="RE:Track API",
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


@app.get("/memory/stats")
async def memory_stats_endpoint():
    """Get memory topology statistics."""
    result = await get_memory_stats()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.post("/benchmarks/run")
async def benchmarks_run_endpoint():
    """Run a benchmark suite."""
    result = await run_benchmark()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


# --- Repository Manager Routes ---


@app.get("/repos")
async def repos_list_endpoint():
    """List all managed repositories."""
    result = await list_repositories()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.post("/repos")
async def repos_create_endpoint(request: RepositoryCreateRequest):
    """Create (import) a new repository."""
    result = await create_repository(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result.model_dump()


@app.post("/repos/{repo_id}/scan")
async def repos_scan_endpoint(repo_id: str):
    """Scan a repository for languages, frameworks, and file stats."""
    result = await scan_repository(repo_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result.model_dump()


@app.get("/repos/{repo_id}/progress")
async def repos_progress_endpoint(repo_id: str):
    """Get indexing progress for a repository."""
    result = await get_repository_progress(repo_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@app.delete("/repos/{repo_id}")
async def repos_delete_endpoint(repo_id: str):
    """Delete a managed repository."""
    result = await delete_repository(repo_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


# --- Context Package Routes ---


@app.get("/packages")
async def packages_list_endpoint():
    """List all saved context packages."""
    result = await list_context_packages()
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.post("/packages")
async def packages_save_endpoint(request: ContextPackageSaveRequest):
    """Save a context package."""
    result = await save_context_package(request)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.get("/packages/{package_id}")
async def packages_get_endpoint(package_id: str):
    """Get a single context package by ID."""
    result = await get_context_package(package_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Package not found")
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()


@app.delete("/packages/{package_id}")
async def packages_delete_endpoint(package_id: str):
    """Delete a context package."""
    result = await delete_context_package(package_id)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result


@app.post("/packages/{package_id}/append")
async def packages_append_endpoint(package_id: str, request: ContextPackageAppendRequest):
    """Append content to an existing context package."""
    result = await append_context_package(package_id, request)
    if result is None:
        raise HTTPException(status_code=404, detail="Package not found")
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=500, detail=result.model_dump())
    return result.model_dump()
