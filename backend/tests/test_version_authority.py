"""Automated tests verifying single-source version authority and synchronization.

Invariants:
1. `backend/app/__init__.py` is the single authoritative source of truth for runtime version.
2. `pyproject.toml` derives dynamic versioning from `app/__init__.py`.
3. CLI `--version` outputs the authoritative runtime version.
4. MCP server metadata reports the authoritative runtime version.
5. Frontend package metadata (`package.json`, `src-tauri/tauri.conf.json`) strictly matches `app.__version__`.
"""

import json
from pathlib import Path
import re
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from app import __version__
from app.cli.main import app as cli_app
from app.mcp.server import create_mcp_server

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"


def test_single_authoritative_version():
    """Verify app.__version__ is a non-empty, valid SemVer string (X.Y.Z)."""
    assert isinstance(__version__, str)
    assert __version__.strip() != ""
    semver_pattern = r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$"
    assert re.match(semver_pattern, __version__), f"__version__ '{__version__}' is not valid SemVer"


def test_package_metadata_matches_runtime_version():
    """Verify pyproject.toml defines dynamic versioning pointing to app/__init__.py."""
    pyproject_path = BACKEND_ROOT / "pyproject.toml"
    assert pyproject_path.exists(), "backend/pyproject.toml not found"

    content = pyproject_path.read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in content or "dynamic = ['version']" in content
    assert 'path = "app/__init__.py"' in content or "path = 'app/__init__.py'" in content


def test_cli_version_matches_runtime_version():
    """Verify Typer CLI --version flag outputs the exact authoritative runtime version."""
    runner = CliRunner()
    result = runner.invoke(cli_app, ["--version"])
    assert result.exit_code == 0
    assert f"RE:Track v{__version__}" in result.stdout


def test_mcp_server_version_matches_runtime_version():
    """Verify FastMCP/MCPServer instance metadata matches the authoritative runtime version."""
    server = create_mcp_server()
    assert server.version == __version__
    assert server.name == "retrack-mcp"


def test_artifact_version_consistency():
    """Verify frontend package.json and tauri.conf.json match the authoritative runtime version."""
    # 1. Check package.json
    pkg_json_path = REPO_ROOT / "package.json"
    assert pkg_json_path.exists(), "package.json not found"
    pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
    assert pkg_data.get("version") == __version__, (
        f"package.json version ({pkg_data.get('version')}) does not match authoritative backend version ({__version__})"
    )

    # 2. Check src-tauri/tauri.conf.json
    tauri_conf_path = REPO_ROOT / "src-tauri" / "tauri.conf.json"
    if tauri_conf_path.exists():
        tauri_data = json.loads(tauri_conf_path.read_text(encoding="utf-8"))
        assert tauri_data.get("version") == __version__, (
            f"tauri.conf.json version ({tauri_data.get('version')}) does not match authoritative backend version ({__version__})"
        )
