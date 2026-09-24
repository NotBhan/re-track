"""FastAPI HTTP server and application assembly for RE:Track.

Configures application lifespan, CORS middleware, and mounts domain API routers.
Transport layer only — business logic is encapsulated in application use cases.
"""

import logging
import os
import signal
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import register_routers
from app.application.container import get_container

logger = logging.getLogger(__name__)


def _start_parent_watchdog() -> None:
    """Launch a background thread to terminate backend if parent process dies abruptly."""
    parent_pid_str = os.environ.get("RETRACK_PARENT_PID")
    if not parent_pid_str:
        return
    try:
        parent_pid = int(parent_pid_str)
    except ValueError:
        return

    def _watchdog_loop() -> None:
        while True:
            time.sleep(1.0)
            try:
                current_ppid = os.getppid()
                if current_ppid != parent_pid:
                    logger.warning(
                        "Parent process %d terminated (current ppid=%d). Terminating orphaned backend.",
                        parent_pid,
                        current_ppid,
                    )
                    os.kill(os.getpid(), signal.SIGTERM)
                    break
                # Verify parent process still exists
                os.kill(parent_pid, 0)
            except (ProcessLookupError, PermissionError):
                logger.warning(
                    "Parent process %d is no longer reachable. Terminating orphaned backend.",
                    parent_pid,
                )
                os.kill(os.getpid(), signal.SIGTERM)
                break

    thread = threading.Thread(target=_watchdog_loop, name="retrack-parent-watchdog", daemon=True)
    thread.start()
    logger.info("Parent-death watchdog thread registered for parent PID %d", parent_pid)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application composition-root lifecycle on startup and shutdown."""
    logger.info("Starting RE:Track HTTP server")
    _start_parent_watchdog()
    container = get_container()
    app.state.container = container
    try:
        await container.initialize()
        logger.info("Backend initialized successfully")
    except Exception as e:
        logger.error("Backend initialization failed: %s", e)
    yield
    try:
        await container.shutdown()
    except Exception as e:
        logger.error("Backend shutdown failed to release resources: %s", e)
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
