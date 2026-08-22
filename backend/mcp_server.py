#!/usr/bin/env python3.12
"""RE:Track Model Context Protocol (MCP) Server CLI entry point.

Usage:
    python -m app.mcp
    python mcp_server.py
    retrack mcp
"""

import asyncio
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_logging
from app.mcp.server import run_mcp_stdio


def main() -> None:
    """Run MCP stdio server."""
    # Ensure MCP logs to stderr exclusively
    setup_logging(stream=sys.stderr)
    try:
        asyncio.run(run_mcp_stdio())
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[RE:Track MCP Fatal] {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
