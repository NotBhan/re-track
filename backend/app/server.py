"""FastAPI HTTP server and application assembly for RE:Track.

Configures application lifespan, CORS middleware, and mounts domain API routers.
Transport layer only — business logic is encapsulated in application use cases.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import register_routers
from app.application.container import get_container

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application composition-root lifecycle on startup and shutdown."""
    logger.info("Starting RE:Track HTTP server")
    container = get_container()
    app.state.container = container
    try:
        await container.initialize()
        logger.info("Backend initialized successfully")
    except Exception as e:
        logger.error("Backend initialization failed: %s", e)
    yield
    logger.info("Shutting down RE:Track HTTP server")


def create_app() -> FastAPI:
    """Construct and configure the RE:Track FastAPI application."""
    application = FastAPI(
        title="RE:Track API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Allow Tauri and frontend clients to call from any origin
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount all domain API routers
    register_routers(application)

    return application


app = create_app()
