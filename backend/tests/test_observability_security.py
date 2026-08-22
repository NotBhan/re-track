"""Phase 9C — Track 5: Observability & Diagnostics Security Tests.

Adversarial validation ensuring that API keys, bearer tokens, passwords, connection
strings, source code contents, and task prompts NEVER appear in logs or diagnostic exports.
"""

import json
import logging
from pathlib import Path
import tempfile
import pytest

from app.core.logging import StructuredJsonFormatter, sanitize_log_message
from app.services.diagnostics_service import DiagnosticsService, sanitize_dict_secrets


def test_adversarial_secrets_redaction_in_log_formatter():
    """Verify that multiple secret formats are redacted from structured log records."""
    formatter = StructuredJsonFormatter()

    adversarial_payloads = [
        "Authorization header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0",
        "Failed request with api_key: sk-proj-1234567890abcdef1234567890abcdef",
        "Anthropic client api_key=sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456",
        "Database connection error postgres://db_user:SuperSecretP@ssword123@localhost:5432/retrack_db",
        "Client secret: client_secret='very_confidential_secret_string'",
        "Cookie: session_id=session_token_9876543210",
    ]

    for payload in adversarial_payloads:
        record = logging.LogRecord(
            name="app.security",
            level=logging.ERROR,
            pathname=__file__,
            lineno=35,
            msg=payload,
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        log_dict = json.loads(formatted)

        # Raw secret strings must NOT exist in the formatted log JSON
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in formatted
        assert "sk-proj-1234567890abcdef1234567890abcdef" not in formatted
        assert "sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456" not in formatted
        assert "SuperSecretP@ssword123" not in formatted
        assert "very_confidential_secret_string" not in formatted
        assert "session_token_9876543210" not in formatted


def test_adversarial_secrets_redaction_in_diagnostics_service():
    """Verify that nested dictionaries with sensitive key names are recursively redacted."""
    sensitive_dict = {
        "user_settings": {
            "api_key": "sk-real-secret-key-1234567890",
            "token": "ghp_abcdefghijklmnopqrstuvwxyz123456",
            "access_token": "secret_access_token_value",
            "password": "my_master_password_999",
            "safe_field": "public_model_name",
        },
        "connection_strings": [
            {"name": "primary_db", "url": "postgres://user:db_password_xyz@host:5432/mydb"},
            {"name": "safe_endpoint", "url": "http://localhost:11434/v1"},
        ],
    }

    sanitized = sanitize_dict_secrets(sensitive_dict)

    # Validate recursive redactions
    assert sanitized["user_settings"]["api_key"] == "[REDACTED]"
    assert sanitized["user_settings"]["token"] == "[REDACTED]"
    assert sanitized["user_settings"]["access_token"] == "[REDACTED]"
    assert sanitized["user_settings"]["password"] == "[REDACTED]"
    assert sanitized["user_settings"]["safe_field"] == "public_model_name"

    # Validate connection string redaction
    assert "db_password_xyz" not in str(sanitized)


def test_diagnostic_bundle_never_contains_source_code_or_prompts():
    """Verify that diagnostic export bundle contains operational metadata only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = DiagnosticsService()
        report = service.generate_diagnostics(include_logs=True, include_health=True)
        report_str = json.dumps(report)

        # Assure no code snippets or task prompts
        assert "def " not in report_str
        assert "class " not in report_str
        assert "import " not in report_str
        assert "task_prompt" not in report_str
        assert "source_code" not in report_str
