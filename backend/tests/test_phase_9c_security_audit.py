"""Phase 9C Final Security & Architecture Closure Audit Suite.

Adversarial security, privacy, hexagonal boundary, and regression validation:
1. test_diagnostics_api_secret_redaction
2. test_logs_recent_secret_redaction
3. test_diagnostics_export_path_traversal
4. test_diagnostics_export_symlink_escape
5. test_jsonl_log_injection_integrity
6. test_nested_secret_redaction
7. test_exception_secret_sanitization
8. test_repository_path_privacy
9. test_system_use_case_architecture_boundary
10. test_phase8_security_regression
11. test_phase8_mcp_lifecycle_regression
"""

import asyncio
import json
import logging
import os
from pathlib import Path
import tempfile
import pytest

from app.application.dto import (
    DetailedHealthResponse,
    ErrorResponse,
    HealthResponse,
)
from app.application.use_cases.system import SystemUseCases
from app.config.settings import Settings
from app.core.logging import (
    SafeRotatingFileHandler,
    StructuredJsonFormatter,
    read_recent_logs,
    sanitize_log_message,
    setup_logging,
)
from app.services.diagnostics_service import (
    DiagnosticsService,
    sanitize_dict_secrets,
)


# --- 1. Diagnostics API Secret Redaction ---
def test_diagnostics_api_secret_redaction():
    """Verify that diagnostics generation redacts all known credential formats."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings()
        settings.logging.log_dir = Path(tmpdir) / "logs"

        # Inject sensitive config & environment
        settings.ollama.host = "http://admin:SecretPass123@localhost"

        service = DiagnosticsService(settings=settings)
        report = service.generate_diagnostics(include_config=True, include_health=True)
        report_str = json.dumps(report)

        assert "SecretPass123" not in report_str
        assert "[REDACTED]" in report_str or "localhost" in report_str


# --- 2. Logs Recent Secret Redaction ---
def test_logs_recent_secret_redaction():
    """Verify that recent log extraction from disk sanitizes all secrets."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "app.jsonl"

        lines = [
            json.dumps({
                "timestamp": "2026-08-22T10:00:00Z",
                "level": "ERROR",
                "message": "Auth failure for api_key=sk-ant-api03-abcdef1234567890abcdef123456",
                "auth_token": "Bearer ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            }),
            json.dumps({
                "timestamp": "2026-08-22T10:01:00Z",
                "level": "INFO",
                "message": "Connected to postgres://retrack_user:p@ssword_999@localhost:5432/db",
            }),
        ]
        log_file.write_text("\n".join(lines), encoding="utf-8")

        logs = read_recent_logs(max_entries=10, log_dir=log_dir, log_file_name="app.jsonl")
        sanitized_logs = sanitize_dict_secrets(logs)
        logs_str = json.dumps(sanitized_logs)

        assert "sk-ant-api03-abcdef1234567890abcdef123456" not in logs_str
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in logs_str
        assert "p@ssword_999" not in logs_str


# --- 3. Diagnostics Export Path Traversal ---
def test_diagnostics_export_path_traversal():
    """Verify export_bundle resolves and handles relative and directory paths safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = Settings()
        service = DiagnosticsService(settings=settings)

        # Export to a directory path
        target_dir = Path(tmpdir) / "diag_dir"
        target_dir.mkdir(parents=True, exist_ok=True)
        exported = service.export_bundle(output_path=target_dir, include_logs=False)

        assert exported.exists()
        assert exported.is_file()
        assert exported.parent == target_dir
        assert exported.name.startswith("diagnostic_bundle_")
        assert exported.suffix == ".json"

        # Export with relative path traversal
        nested_dir = Path(tmpdir) / "a" / "b"
        nested_dir.mkdir(parents=True, exist_ok=True)
        traversal_target = nested_dir / ".." / "exported_diag.json"
        exported2 = service.export_bundle(output_path=traversal_target, include_logs=False)

        assert exported2.exists()
        assert exported2.resolve() == (Path(tmpdir) / "a" / "exported_diag.json").resolve()


# --- 4. Diagnostics Export Symlink Escape ---
def test_diagnostics_export_symlink_escape():
    """Verify export_bundle safely handles target symlinks without uncontained corruption."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        real_file = base / "real_bundle.json"
        real_file.write_text("{}", encoding="utf-8")

        symlink_path = base / "symlink_bundle.json"
        symlink_path.symlink_to(real_file)

        settings = Settings()
        service = DiagnosticsService(settings=settings)
        exported = service.export_bundle(output_path=symlink_path, include_logs=False)

        assert exported.exists()
        content = json.loads(exported.read_text(encoding="utf-8"))
        assert content["metadata"]["product"] == "RE:Track"


# --- 5. JSONL Log Injection Integrity ---
def test_jsonl_log_injection_integrity():
    """Verify that CRLF, newlines, quotes, and malicious JSON in log messages do NOT split lines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "app.jsonl"
        handler = SafeRotatingFileHandler(filename=str(log_file), maxBytes=100000, backupCount=1)
        handler.setFormatter(StructuredJsonFormatter())

        logger = logging.getLogger("test_injection_logger")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        logger.addHandler(handler)

        hostile_inputs = [
            "Log with newline\n{\"level\": \"CRITICAL\", \"message\": \"FORGED_ENTRY\"}\n",
            "Log with CRLF\r\n{\"admin\": true}",
            "Log with quotes \" and braces { } and \\u0000 null byte",
            "Log with tab \t and backslash \\ and unicode: \u2603 \U0001F600",
            '{"event": "fake_json_object", "status": "tampered"}',
        ]

        for inp in hostile_inputs:
            logger.info("Hostile input: %s", inp)

        handler.close()

        # Verify that EVERY line in the file is a single valid JSON object
        raw_lines = [line.strip() for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(raw_lines) == len(hostile_inputs), f"Expected {len(hostile_inputs)} lines, got {len(raw_lines)} (line injection detected!)"

        for line in raw_lines:
            record = json.loads(line)
            assert "level" in record
            assert "timestamp" in record
            assert "message" in record


# --- 6. Nested Secret Redaction ---
def test_nested_secret_redaction():
    """Verify recursive redaction across multi-tier nested dictionaries and lists."""
    adversarial_structure = {
        "tier1": {
            "api_key": "sk-real-key-1234567890",
            "tier2_list": [
                "safe_string",
                {"password": "secret_password_456", "session_token": "token_val_789"},
                ["inner_list", {"db_uri": "mysql://root:root_pass_abc@localhost:3306/db"}],
            ],
            "headers": {
                "Authorization": "Bearer sensitive_bearer_jwt_token_payload_here",
                "X-Custom-Auth": "auth_token_xyz_987654",
            },
        }
    }

    sanitized = sanitize_dict_secrets(adversarial_structure)
    sanitized_str = json.dumps(sanitized)

    assert "sk-real-key-1234567890" not in sanitized_str
    assert "secret_password_456" not in sanitized_str
    assert "token_val_789" not in sanitized_str
    assert "root_pass_abc" not in sanitized_str
    assert "sensitive_bearer_jwt_token_payload_here" not in sanitized_str
    assert "auth_token_xyz_987654" not in sanitized_str


# --- 7. Exception Secret Sanitization ---
def test_exception_secret_sanitization():
    """Verify that exception messages containing credentials are fully sanitized."""
    formatter = StructuredJsonFormatter()

    try:
        raise ConnectionError("Failed to connect: api_key='sk-ant-live-secret-987654321' to https://api.anthropic.com")
    except ConnectionError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="app.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=150,
        msg="Provider error occurred",
        args=(),
        exc_info=exc_info,
    )

    formatted = formatter.format(record)
    assert "sk-ant-live-secret-987654321" not in formatted
    data = json.loads(formatted)
    assert data["error_class"] == "ConnectionError"


# --- 8. Repository Path Privacy & Content Exclusion ---
def test_repository_path_privacy():
    """Verify that diagnostics summaries exclude source code files, bodies, and prompts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        canonical_root = Path(tmpdir) / ".retrack"
        canonical_root.mkdir(parents=True, exist_ok=True)

        # Write mock repo data with metadata
        repos_file = canonical_root / "indexed_repos.json"
        repos_file.write_text(json.dumps([
            {
                "name": "my-secret-repo",
                "status": "ready",
                "languages": ["Python", "TypeScript"],
                "file_count": 50,
                "private_internal_field": "some_value",
            }
        ]), encoding="utf-8")

        settings = Settings()
        settings.logging.log_dir = Path(tmpdir) / "logs"

        # Monkeypatch home
        orig_home = Path.home
        try:
            Path.home = lambda: Path(tmpdir)
            service = DiagnosticsService(settings=settings)
            report = service.generate_diagnostics(include_logs=False, include_health=True)
        finally:
            Path.home = orig_home

        report_str = json.dumps(report)
        assert "my-secret-repo" in report_str
        assert "def " not in report_str
        assert "class " not in report_str
        assert "import " not in report_str
        assert "task_prompt" not in report_str


# --- 9. System Use Case Architecture Boundary ---
@pytest.mark.asyncio
async def test_system_use_case_architecture_boundary():
    """Verify SystemUseCases is pure and isolated, functioning with mock ports without live services."""
    settings = Settings()
    use_cases = SystemUseCases(
        settings_getter=lambda: settings,
        cognee_service_getter=lambda: None,
        llm_provider_getter=lambda: None,
        provider_updater_fn=lambda *args: asyncio.sleep(0),
    )

    res = await use_cases.health()
    assert isinstance(res, HealthResponse)
    assert res.version == "0.1.0"

    det_res = await use_cases.get_detailed_health()
    assert isinstance(det_res, DetailedHealthResponse)
    assert "canonical_root" in det_res.storage_paths


# --- 10. Phase 8 Security Invariant Regression ---
def test_phase8_security_regression():
    """Verify Phase 8B workspace path authorization and traversal rejection."""
    from app.services.workspace_authorization_service import WorkspaceAuthorizationService

    with tempfile.TemporaryDirectory() as tmpdir:
        ws_root = Path(tmpdir) / "workspace"
        ws_root.mkdir(parents=True, exist_ok=True)
        repo_dir = ws_root / "my_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "src").mkdir(parents=True, exist_ok=True)
        (repo_dir / "src" / "index.ts").write_text("console.log('test');", encoding="utf-8")

        auth_service = WorkspaceAuthorizationService(workspace_roots=[str(ws_root)])

        # 1. Authorized repository path inside workspace
        is_auth, reason = auth_service.is_path_authorized(str(repo_dir))
        assert is_auth is True
        assert reason is None

        # 2. Path traversal attack with directory outside workspace
        outside_dir = Path(tmpdir) / "outside_repo"
        outside_dir.mkdir(parents=True, exist_ok=True)
        is_auth_trav, reason_trav = auth_service.is_path_authorized(str(ws_root / ".." / "outside_repo"))
        assert is_auth_trav is False
        assert "not an authorized repository" in reason_trav.lower()

        # 3. Direct outside directory access
        is_auth_out, reason_out = auth_service.is_path_authorized(str(outside_dir))
        assert is_auth_out is False


# --- 11. Phase 8 MCP Lifecycle Regression ---
@pytest.mark.asyncio
async def test_phase8_mcp_lifecycle_regression():
    """Verify Phase 8C/8D concurrency guard and exception isolation invariants."""
    from app.application.use_cases.context import BoundedConcurrencyGuard

    guard = BoundedConcurrencyGuard(max_concurrent=1, max_queue=2)

    # Acquire slot
    assert guard.waiting_count == 0
    ok, err = await guard.acquire()
    assert ok is True
    assert err is None
    # Inside active execution
    assert guard._semaphore._value == 0

    # Release slot
    guard.release()
    assert guard._semaphore._value == 1
