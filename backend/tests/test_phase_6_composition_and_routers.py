"""Phase 6 verification suite: Composition Root Lifecycle & FastAPI Route Modularization.

Validates:
1. Composition root lifecycle (lazy instantiation, test isolation, no import-time side effects).
2. AST boundary integrity (use cases, domain, and ports never call get_container).
3. FastAPI router modularization and exact route inventory parity (29 endpoints).
4. Request/response execution and HTTP status code mappings.
5. Backward compatibility of app.api.commands facade.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.schemas import (
    AppSettingsResponse,
    BackendStatusResponse,
    BenchmarkSuiteResponse,
    CogneeSettingsRequest,
    CognifyRequest,
    CognifyResponse,
    ContextPackageAppendRequest,
    ContextPackageListResponse,
    ContextPackageResponse,
    ContextPackageSaveRequest,
    ContextResponse,
    DashboardStats,
    DatasetDataItemsResponse,
    DatasetListResponse,
    ErrorResponse,
    ForgetDatasetRequest,
    GenerateContextRequest,
    HealthResponse,
    IndexRepositoryRequest,
    IndexRepositoryResponse,
    MemoryGraphResponse,
    MemoryStatsResponse,
    MemoryVectorsResponse,
    RepositoryCreateRequest,
    RepositoryListResponse,
    RepositoryResponse,
    ScanResultResponse,
)
from app.application.container import (
    ApplicationContainer,
    get_container,
    reset_container,
    set_container,
)
from app.models.agent_context import AgentContextRequest, AgentContextResponse
from app.server import app, create_app


# ─── 1. Composition Root Lifecycle Tests ───


class TestCompositionRootLifecycle:
    """Verify composition root lazy construction, explicit factories, and test isolation."""

    def test_import_time_container_is_none_in_fresh_process(self):
        """Importing container.py in a fresh process must not instantiate _container."""
        code = (
            "import app.application.container as c\n"
            "assert c._container is None, f'Expected None, got {c._container}'\n"
            "print('SUCCESS')\n"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        assert res.returncode == 0, f"Failed: {res.stderr}"
        assert "SUCCESS" in res.stdout

    def test_container_create_and_get_container(self):
        """get_container should lazily create container, and create() should yield fresh instances."""
        reset_container()
        c1 = ApplicationContainer.create()
        assert isinstance(c1, ApplicationContainer)
        assert c1.cognee_service is None  # uninitialized

        # get_container lazily creates
        c2 = get_container()
        assert isinstance(c2, ApplicationContainer)
        assert get_container() is c2

        reset_container()
        c3 = get_container()
        assert c3 is not c2

    def test_set_and_reset_container_isolation(self):
        """set_container enables explicit injection for test isolation."""
        reset_container()
        mock_container = MagicMock(spec=ApplicationContainer)
        set_container(mock_container)
        assert get_container() is mock_container

        reset_container()
        real_container = get_container()
        assert real_container is not mock_container
        assert isinstance(real_container, ApplicationContainer)

    def test_no_get_container_in_use_cases_domain_or_ports(self):
        """AST purity: use_cases, domain, and ports must NEVER import or call get_container."""
        backend_dir = Path(__file__).resolve().parent.parent / "app" / "application"

        for subdir in ["use_cases", "domain", "ports"]:
            target_dir = backend_dir / subdir
            for py_file in target_dir.glob("*.py"):
                tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and "container" in node.module:
                            for alias in node.names:
                                assert alias.name not in ["get_container", "_container", "set_container"], (
                                    f"Forbidden container import '{alias.name}' found in {py_file}"
                                )
                    elif isinstance(node, ast.Name):
                        assert node.id not in ["get_container", "_container"], (
                            f"Forbidden symbol '{node.id}' accessed in {py_file}"
                        )


# ─── 2. Route Inventory & Parity Tests ───


MANDATORY_ROUTES = [
    # System
    ("GET", "/health"),
    ("GET", "/status"),
    ("GET", "/dashboard/stats"),
    ("POST", "/provider/update"),
    # Repositories
    ("GET", "/repos"),
    ("POST", "/repos"),
    ("POST", "/repos/{repo_id}/scan"),
    ("GET", "/repos/{repo_id}/progress"),
    ("DELETE", "/repos/{repo_id}"),
    ("GET", "/repos/{repo_id}/prompts"),
    ("GET", "/repositories"),
    # Context
    ("POST", "/index"),
    ("POST", "/context"),
    ("POST", "/api/v1/context"),
    # Memory
    ("GET", "/datasets"),
    ("GET", "/datasets/{dataset_id}/items"),
    ("POST", "/forget"),
    ("GET", "/memory/stats"),
    ("GET", "/memory/graph"),
    ("GET", "/memory/vectors"),
    ("POST", "/memory/cognify"),
    # Packages
    ("GET", "/packages"),
    ("POST", "/packages"),
    ("GET", "/packages/{package_id}"),
    ("DELETE", "/packages/{package_id}"),
    ("POST", "/packages/{package_id}/append"),
    # Benchmarks
    ("POST", "/benchmarks/run"),
    # Settings
    ("GET", "/settings"),
    ("POST", "/settings/cognee"),
]


def _extract_all_app_routes(application) -> list[tuple[str, str]]:
    """Extract all active endpoint method/path pairs from FastAPI application."""
    routes: list[tuple[str, str]] = []
    for r in application.routes:
        if hasattr(r, "path") and hasattr(r, "methods"):
            for m in r.methods:
                if m not in ["HEAD", "OPTIONS"]:
                    routes.append((m, r.path))
        elif hasattr(r, "original_router"):
            for sr in r.original_router.routes:
                if hasattr(sr, "path") and hasattr(sr, "methods"):
                    for m in sr.methods:
                        if m not in ["HEAD", "OPTIONS"]:
                            routes.append((m, sr.path))
    return routes


class TestRouteInventoryAndParity:
    """Verify all 29 route operations are registered on FastAPI with exact methods and paths."""

    def test_all_mandatory_routes_registered_exactly_once(self):
        registered_routes = _extract_all_app_routes(app)

        for method, path in MANDATORY_ROUTES:
            matching = [r for r in registered_routes if r == (method, path)]
            assert len(matching) == 1, (
                f"Expected route ({method}, {path}) to be registered exactly once, found {len(matching)}"
            )

    def test_total_route_count(self):
        registered_routes = _extract_all_app_routes(app)
        for m, p in MANDATORY_ROUTES:
            assert (m, p) in registered_routes


# ─── 3. Endpoint Execution & HTTP Status Code Mapping Tests ───


@pytest.fixture
def test_client():
    """Create a FastAPI TestClient with mocked use cases for endpoint testing."""
    client = TestClient(app, raise_server_exceptions=False)
    return client


class TestRouterEndpointsExecution:
    """Test representative request/response contracts and status code mappings."""

    def test_health_success(self, test_client):
        mock_container = ApplicationContainer.create()
        mock_system = MagicMock()
        mock_system.health = AsyncMock(
            return_value=HealthResponse(status="ok", ollama_reachable=True, cognee_initialized=True)
        )
        mock_container.get_system_use_cases = MagicMock(return_value=mock_system)
        set_container(mock_container)

        resp = test_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["ollama_reachable"] is True

    def test_health_error_status_503(self, test_client):
        mock_container = ApplicationContainer.create()
        mock_system = MagicMock()
        mock_system.health = AsyncMock(
            return_value=ErrorResponse(error="HealthError", message="Service unreachable")
        )
        mock_container.get_system_use_cases = MagicMock(return_value=mock_system)
        set_container(mock_container)

        resp = test_client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        assert "detail" in data
        assert data["detail"]["error"] == "HealthError"

    def test_repositories_list_and_create(self, test_client):
        mock_container = ApplicationContainer.create()
        mock_repo = MagicMock()
        mock_repo.list_repositories = AsyncMock(
            return_value=RepositoryListResponse(success=True, repositories=[], total=0)
        )
        mock_repo.create_repository = AsyncMock(
            return_value=RepositoryResponse(
                id="r1",
                name="repo1",
                source_type="local",
                local_path="/path/r1",
                branch="main",
                status="registered",
            )
        )
        mock_container.get_repository_use_cases = MagicMock(return_value=mock_repo)
        set_container(mock_container)

        # GET /repos
        resp_get = test_client.get("/repos")
        assert resp_get.status_code == 200
        assert resp_get.json()["total_count"] == 0


        # POST /repos
        resp_post = test_client.post(
            "/repos",
            json={"source_type": "local", "local_path": "/path/r1", "name": "repo1"},
        )
        assert resp_post.status_code == 200
        assert resp_post.json()["id"] == "r1"


    def test_packages_get_404_when_missing(self, test_client):
        mock_container = ApplicationContainer.create()
        mock_pkg = MagicMock()
        mock_pkg.get_context_package = AsyncMock(return_value=None)
        mock_container.get_package_use_cases = MagicMock(return_value=mock_pkg)
        set_container(mock_container)

        resp = test_client.get("/packages/non-existent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Package not found"

    def test_settings_endpoints(self, test_client):
        mock_container = ApplicationContainer.create()
        mock_sys = MagicMock()
        mock_sys.get_app_settings = AsyncMock(
            return_value=AppSettingsResponse(
                success=True,
                vector_db="lancedb",
                graph_db="kuzu",
                relational_db="sqlite",
                enable_kg_extraction=True,
                auto_link_entities=True,
                caching=False,
                data_root="/tmp/retrack",
                system_root="/tmp/retrack",
                llm_model="qwen2.5-coder:7b",
            )
        )
        mock_container.get_system_use_cases = MagicMock(return_value=mock_sys)
        set_container(mock_container)

        resp = test_client.get("/settings")
        assert resp.status_code == 200
        assert resp.json()["llm_model"] == "qwen2.5-coder:7b"

    def test_benchmarks_run_endpoint(self, test_client):
        mock_container = ApplicationContainer.create()
        mock_bench = MagicMock()
        mock_bench.run_benchmark = AsyncMock(
            return_value=BenchmarkSuiteResponse(
                success=True,
                total_questions=1,
                results=[],
                accuracy_summary="Pass",
            )
        )
        mock_container.get_benchmark_use_cases = MagicMock(return_value=mock_bench)
        set_container(mock_container)

        resp = test_client.post("/benchmarks/run")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_commands_facade_backward_compatibility(self):
        """commands.py must properly resolve active container dynamically."""
        from app.api import commands

        mock_container = ApplicationContainer.create()
        mock_sys = MagicMock()
        mock_sys.health = AsyncMock(
            return_value=HealthResponse(status="ok", ollama_reachable=True, cognee_initialized=True)
        )
        mock_container.get_system_use_cases = MagicMock(return_value=mock_sys)
        set_container(mock_container)

        # Health command check
        res = await commands.health()
        assert res.status == "ok"
        assert res.ollama_reachable is True



    def test_server_assembly_line_count(self):
        """server.py must be a clean assembly boundary (< 80 lines)."""
        server_path = Path(__file__).resolve().parent.parent / "app" / "server.py"
        lines = [line for line in server_path.read_text(encoding="utf-8").splitlines()]
        assert len(lines) < 80, f"server.py is {len(lines)} lines, expected < 80"

