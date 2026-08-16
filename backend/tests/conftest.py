"""Pytest configuration for RE:Track backend tests."""

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
