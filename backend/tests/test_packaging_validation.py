"""Automated tests validating release package artifacts, clean installation, and entrypoints outside repository.

Invariants:
1. Wheel and sdist are built from single source of truth.
2. Wheel contains positive required modules and zero forbidden files (tests, databases, env, logs).
3. Exact wheel installs cleanly into an isolated virtual environment outside the repository.
4. CLI and FastMCP entrypoints function seamlessly from the installed package.
5. MCP stdio framing remains 100% reserved for JSON-RPC in production package installation.
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

import pytest

from app import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"


@pytest.fixture(scope="module")
def built_artifacts():
    """Build wheel and sdist into a temporary directory once for the module."""
    build_dir = Path(tempfile.mkdtemp(prefix="retrack_build_"))
    try:
        # Run uv build targeting temporary dist directory
        build_proc = subprocess.run(
            ["uv", "build", "--out-dir", str(build_dir)],
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
        )
        assert build_proc.returncode == 0, f"Build failed: {build_proc.stderr}"

        wheels = list(build_dir.glob("*.whl"))
        sdists = list(build_dir.glob("*.tar.gz"))

        assert len(wheels) == 1, f"Expected 1 wheel, found {len(wheels)} in {build_dir}"
        assert len(sdists) == 1, f"Expected 1 sdist, found {len(sdists)} in {build_dir}"

        yield {"wheel": wheels[0], "sdist": sdists[0], "dir": build_dir}
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


def test_wheel_positive_file_allowlist(built_artifacts):
    """Verify built wheel contains all required runtime application modules."""
    wheel_path = built_artifacts["wheel"]
    with zipfile.ZipFile(wheel_path, "r") as zf:
        namelist = zf.namelist()

        required_prefixes = [
            "app/__init__.py",
            "app/application/",
            "app/services/",
            "app/api/",
            "app/cli/",
            "app/mcp/",
            "app/core/",
            "app/config/",
            "app/evaluation/",
            "app/models/",
        ]

        for req in required_prefixes:
            if req.endswith("/"):
                assert any(name.startswith(req) for name in namelist), f"Missing required directory in wheel: {req}"
            else:
                assert req in namelist, f"Missing required file in wheel: {req}"

        # Verify entrypoints exist in dist-info
        dist_info_entries = [name for name in namelist if "entry_points.txt" in name]
        assert len(dist_info_entries) > 0, "Missing entry_points.txt in wheel metadata"


def test_wheel_negative_file_allowlist(built_artifacts):
    """Verify built wheel strictly excludes forbidden files (tests, databases, secrets, logs, frontend)."""
    wheel_path = built_artifacts["wheel"]
    with zipfile.ZipFile(wheel_path, "r") as zf:
        namelist = zf.namelist()

        forbidden_patterns = [
            "tests/",
            "test_",
            ".git",
            ".github",
            ".pytest_cache",
            ".venv",
            "node_modules",
            "src/",
            "src-tauri/",
            ".env",
            ".log",
            ".jsonl",
            ".sqlite",
            ".db",
            "diagnostics/",
            "diagnostic_bundle_",
        ]

        for name in namelist:
            for forb in forbidden_patterns:
                assert forb not in name, f"Forbidden file/directory '{name}' detected in release wheel!"


def test_sdist_build(built_artifacts):
    """Verify sdist contains project structure, metadata, and core application code."""
    sdist_path = built_artifacts["sdist"]
    assert sdist_path.exists()

    with tarfile.open(sdist_path, "r:gz") as tf:
        names = tf.getnames()
        # Should contain root folder like retrack_ai-0.1.0/
        root_prefix = f"retrack_ai-{__version__}"
        assert any(n.startswith(root_prefix) for n in names)
        assert any(n.endswith("pyproject.toml") for n in names)
        assert any(n.endswith("README.md") for n in names)
        assert any("app/__init__.py" in n for n in names)


@pytest.fixture(scope="module")
def clean_installed_environment(built_artifacts):
    """Create an isolated virtual environment and install the exact built wheel."""
    env_dir = Path(tempfile.mkdtemp(prefix="retrack_clean_env_"))
    try:
        # Create virtual environment with uv
        subprocess.run(["uv", "venv", str(env_dir), "--seed"], check=True, capture_output=True)

        bin_dir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
        python_exe = bin_dir / ("python.exe" if sys.platform == "win32" else "python")
        retrack_exe = bin_dir / ("retrack.exe" if sys.platform == "win32" else "retrack")
        retrack_mcp_exe = bin_dir / ("retrack-mcp.exe" if sys.platform == "win32" else "retrack-mcp")

        # Install wheel with uv pip (fast & uses local wheel cache if needed)
        wheel_path = built_artifacts["wheel"]
        install_proc = subprocess.run(
            ["uv", "pip", "install", "--python", str(python_exe), str(wheel_path)],
            capture_output=True,
            text=True,
        )
        assert install_proc.returncode == 0, f"Wheel installation failed: {install_proc.stderr}"

        yield {
            "env_dir": env_dir,
            "python": python_exe,
            "retrack": retrack_exe,
            "retrack_mcp": retrack_mcp_exe,
        }
    finally:
        shutil.rmtree(env_dir, ignore_errors=True)


def test_clean_install_outside_repository(clean_installed_environment):
    """Verify package imports correctly in an isolated subprocess with no repository on PYTHONPATH."""
    python_exe = clean_installed_environment["python"]

    # Run in a completely separate temp directory with empty PYTHONPATH
    with tempfile.TemporaryDirectory() as tmpdir:
        test_script = "import app; print('IMPORTED_VERSION=' + app.__version__)"
        proc = subprocess.run(
            [str(python_exe), "-c", test_script],
            cwd=tmpdir,
            env={"PATH": str(clean_installed_environment["env_dir"] / "bin"), "PYTHONPATH": ""},
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, f"Import failed in clean environment: {proc.stderr}"
        assert f"IMPORTED_VERSION={__version__}" in proc.stdout


def test_installed_cli_entrypoint(clean_installed_environment):
    """Verify installed retrack executable runs --version, --help, and init with isolated HOME."""
    retrack_exe = clean_installed_environment["retrack"]

    with tempfile.TemporaryDirectory() as isolated_home:
        env = {
            "HOME": isolated_home,
            "USERPROFILE": isolated_home,
            "PATH": str(clean_installed_environment["env_dir"] / "bin") + ":" + str(Path(sys.executable).parent),
            "PYTHONPATH": "",
        }

        # 1. retrack --version
        proc_ver = subprocess.run([str(retrack_exe), "--version"], cwd=isolated_home, env=env, capture_output=True, text=True)
        assert proc_ver.returncode == 0
        assert f"RE:Track v{__version__}" in proc_ver.stdout

        # 2. retrack --help
        proc_help = subprocess.run([str(retrack_exe), "--help"], cwd=isolated_home, env=env, capture_output=True, text=True)
        assert proc_help.returncode == 0
        assert "RE:Track CLI" in proc_help.stdout or "Usage:" in proc_help.stdout

        # 3. retrack init
        proc_init = subprocess.run([str(retrack_exe), "init"], cwd=isolated_home, env=env, capture_output=True, text=True)
        assert proc_init.returncode == 0
        retrack_data_dir = Path(isolated_home) / ".retrack"
        assert retrack_data_dir.exists(), "retrack init did not create ~/.retrack/"


def test_installed_mcp_entrypoint(clean_installed_environment):
    """Verify installed retrack-mcp entrypoint starts and handles JSON-RPC initialization."""
    retrack_mcp_exe = clean_installed_environment["retrack_mcp"]

    with tempfile.TemporaryDirectory() as isolated_home:
        env = {
            "HOME": isolated_home,
            "USERPROFILE": isolated_home,
            "PATH": str(clean_installed_environment["env_dir"] / "bin") + ":" + str(Path(sys.executable).parent),
            "PYTHONPATH": "",
        }

        init_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }) + "\n"

        proc = subprocess.run(
            [str(retrack_mcp_exe)],
            input=init_request,
            cwd=isolated_home,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        assert proc.returncode == 0 or proc.stdout != ""
        # Stdio stdout must contain valid JSON-RPC response
        assert "jsonrpc" in proc.stdout
        assert "retrack-mcp" in proc.stdout or "serverInfo" in proc.stdout


def test_installed_module_entrypoint(clean_installed_environment):
    """Verify python -m app.mcp starts the MCP stdio server."""
    python_exe = clean_installed_environment["python"]

    with tempfile.TemporaryDirectory() as isolated_home:
        env = {
            "HOME": isolated_home,
            "USERPROFILE": isolated_home,
            "PATH": str(clean_installed_environment["env_dir"] / "bin") + ":" + str(Path(sys.executable).parent),
            "PYTHONPATH": "",
        }

        init_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }) + "\n"

        proc = subprocess.run(
            [str(python_exe), "-m", "app.mcp"],
            input=init_request,
            cwd=isolated_home,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        assert proc.returncode == 0 or proc.stdout != ""
        assert "jsonrpc" in proc.stdout


def test_installed_mcp_stdio_integrity(clean_installed_environment):
    """Verify stdout from installed retrack-mcp is strictly valid JSON-RPC frames with zero banner leaks."""
    retrack_mcp_exe = clean_installed_environment["retrack_mcp"]

    with tempfile.TemporaryDirectory() as isolated_home:
        env = {
            "HOME": isolated_home,
            "USERPROFILE": isolated_home,
            "PATH": str(clean_installed_environment["env_dir"] / "bin") + ":" + str(Path(sys.executable).parent),
            "PYTHONPATH": "",
        }

        init_request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }) + "\n"

        proc = subprocess.run(
            [str(retrack_mcp_exe)],
            input=init_request,
            cwd=isolated_home,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        # Parse every non-empty line on stdout as valid JSON
        stdout_lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        assert len(stdout_lines) > 0, "No stdout received from MCP server"

        for line in stdout_lines:
            try:
                frame = json.loads(line)
                assert "jsonrpc" in frame, f"Non-JSONRPC frame leaked to stdout: {line}"
            except json.JSONDecodeError as exc:
                pytest.fail(f"Non-JSON string leaked to MCP stdout: {line} (error: {exc})")
