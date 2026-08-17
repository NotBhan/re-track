import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

import pytest


@pytest.fixture(autouse=True)
def _reset_command_singletons():
    """Reset command singletons before each test."""
    import app.api.commands as cmds

    cmds._cognee_service = None
    cmds._indexing_service = None
    cmds._context_service = None
    yield
    cmds._cognee_service = None
    cmds._indexing_service = None
    cmds._context_service = None
