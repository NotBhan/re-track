"""Tests for RE:Track packaging, wheel build artifacts, and package metadata."""

import importlib
from pathlib import Path
import pytest

from app import __version__


def test_package_metadata_consistency():
    """Verify package metadata version is consistent across app and pyproject.toml."""
    backend_dir = Path(__file__).resolve().parent.parent
    pyproject_file = backend_dir / "pyproject.toml"

    assert pyproject_file.exists()
    content = pyproject_file.read_text()
    assert 'name = "retrack-ai"' in content
    assert f'version = "{__version__}"' in content
    assert 'retrack = "app.cli.main:app"' in content
    assert 'retrack-mcp = "app.mcp.server:main"' in content


def test_wheel_build_artifacts():
    """Verify that wheel and source distribution artifacts build and exist."""
    backend_dir = Path(__file__).resolve().parent.parent
    dist_dir = backend_dir / "dist"

    assert dist_dir.exists()
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))

    assert len(wheels) >= 1
    assert any(f"retrack_ai-{__version__}" in w.name for w in wheels)
    assert len(sdists) >= 1
    assert any(f"retrack_ai-{__version__}" in s.name for s in sdists)


def test_core_package_imports():
    """Verify that all core driving and driven modules can be imported cleanly."""
    cli_module = importlib.import_module("app.cli.main")
    assert hasattr(cli_module, "app")

    mcp_module = importlib.import_module("app.mcp.server")
    assert hasattr(mcp_module, "create_mcp_server")
    assert hasattr(mcp_module, "run_mcp_stdio")
    assert hasattr(mcp_module, "main")

    bootstrap_module = importlib.import_module("app.services.bootstrap_service")
    assert hasattr(bootstrap_module, "BootstrapService")

    maintenance_module = importlib.import_module("app.services.maintenance_service")
    assert hasattr(maintenance_module, "MaintenanceService")
