"""Diagnostics and supportability service for RE:Track.

Generates sanitized diagnostic bundles, operational reports, and support exports
while strictly enforcing privacy guarantees: no source code, no credentials,
no task prompts, and no arbitrary secrets.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import platform
import re
import sys
import tempfile
from typing import Any, Optional

from app import __version__ as RETRACK_VERSION
from app.config.settings import Settings, get_settings
from app.core.logging import read_recent_logs, sanitize_log_message

logger = logging.getLogger(__name__)

# Sensitive key names to redact automatically in configs and dictionaries
_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "client_secret",
    "authorization",
    "auth",
    "cookie",
    "session_id",
    "private_key",
    "task_prompt",
    "source_code",
}


def sanitize_dict_secrets(data: Any) -> Any:
    """Recursively redact sensitive keys and strings in nested dicts/lists."""
    if isinstance(data, dict):
        sanitized: dict[str, Any] = {}
        for k, v in data.items():
            key_lower = str(k).lower().replace("-", "_")
            if any(sensitive in key_lower for sensitive in _SENSITIVE_KEYS):
                clean_k = re.sub(r"(?i)task_prompt|source_code", "redacted_field", str(k))
                sanitized[clean_k] = "[REDACTED]"
            elif isinstance(v, str):
                sanitized[k] = sanitize_log_message(v)
            elif isinstance(v, (dict, list)):
                sanitized[k] = sanitize_dict_secrets(v)
            else:
                sanitized[k] = v
        return sanitized
    elif isinstance(data, list):
        return [sanitize_dict_secrets(item) for item in data]
    elif isinstance(data, str):
        return sanitize_log_message(data)
    else:
        return data


class DiagnosticsService:
    """Collects, sanitizes, and exports operational diagnostic bundles."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()

    def generate_diagnostics(
        self,
        include_logs: bool = True,
        max_log_lines: int = 50,
        include_config: bool = True,
        include_health: bool = True,
        container: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Generate a complete, sanitized operational diagnostic report."""
        timestamp = datetime.now(timezone.utc).isoformat()

        bundle: dict[str, Any] = {
            "metadata": {
                "product": "RE:Track",
                "version": RETRACK_VERSION,
                "generated_at": timestamp,
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "os_name": os.name,
                "process_id": os.getpid(),
            }
        }

        # 1. Sanitized Configuration Summary
        if include_config:
            raw_config = {
                "storage": {
                    "vector_db": self._settings.storage.vector_db,
                    "graph_db": self._settings.storage.graph_db,
                    "relational_db": self._settings.storage.relational_db,
                    "enable_kg_extraction": self._settings.storage.enable_kg_extraction,
                    "auto_link_entities": self._settings.storage.auto_link_entities,
                },
                "service": {
                    "caching": self._settings.service.caching,
                    "enable_access_control": self._settings.service.enable_access_control,
                    "skip_connection_test": self._settings.service.skip_connection_test,
                },
                "ollama": {
                    "host": self._settings.ollama.host,
                    "port": self._settings.ollama.port,
                    "llm_model": self._settings.ollama.llm_model,
                    "embedding_model": self._settings.ollama.embedding_model,
                },
                "logging": {
                    "level": self._settings.logging.level,
                    "max_bytes": self._settings.logging.max_bytes,
                    "backup_count": self._settings.logging.backup_count,
                    "enable_file_logging": self._settings.logging.enable_file_logging,
                    "enable_stderr_logging": self._settings.logging.enable_stderr_logging,
                },
                "environment_flags": {
                    "RETRACK_WORKSPACE_ROOTS_COUNT": len(
                        os.environ.get("RETRACK_WORKSPACE_ROOTS", "").split(",")
                    ) if os.environ.get("RETRACK_WORKSPACE_ROOTS") else 0,
                    "LLM_MODEL_ENV_SET": bool(os.environ.get("LLM_MODEL")),
                },
            }
            bundle["configuration"] = sanitize_dict_secrets(raw_config)

        # 2. Health & Operational Storage Metrics
        if include_health:
            canonical_root = Path.home() / ".retrack"
            legacy_root = Path.home() / ".andes"
            cache_dir = canonical_root / "cache"

            # Check cache statistics
            cache_file_count = 0
            cache_total_bytes = 0
            if cache_dir.exists() and cache_dir.is_dir():
                for f in cache_dir.glob("*"):
                    if f.is_file():
                        cache_file_count += 1
                        try:
                            cache_total_bytes += f.stat().st_size
                        except OSError:
                            pass

            # Check canonical storage health
            canonical_exists = canonical_root.exists()
            canonical_writable = False
            canonical_free_mb = 0
            if canonical_exists:
                try:
                    test_file = canonical_root / ".write_test"
                    test_file.write_text("ok")
                    test_file.unlink(missing_ok=True)
                    canonical_writable = True
                    # Check disk free
                    statvfs = os.statvfs(canonical_root)
                    canonical_free_mb = int((statvfs.f_bavail * statvfs.f_frsize) / (1024 * 1024))
                except Exception:
                    canonical_writable = False

            # Check repository and package counts
            repo_count = 0
            package_count = 0
            repos_summary: list[dict[str, Any]] = []

            repo_file = canonical_root / "indexed_repos.json"
            if not repo_file.exists():
                repo_file = canonical_root / "repositories.json"
            if not repo_file.exists() and legacy_root.exists():
                repo_file = legacy_root / "indexed_repos.json"

            if repo_file.exists():
                try:
                    repo_data = json.loads(repo_file.read_text(encoding="utf-8"))
                    if isinstance(repo_data, list):
                        repo_count = len(repo_data)
                        for r in repo_data:
                            if isinstance(r, dict):
                                repos_summary.append({
                                    "name": r.get("name", "unnamed"),
                                    "status": r.get("status", "unknown"),
                                    "languages": r.get("languages", []),
                                    "file_count": r.get("file_count", 0),
                                })
                except Exception:
                    pass

            pkg_file = canonical_root / "context_packages.json"
            if not pkg_file.exists() and legacy_root.exists():
                pkg_file = legacy_root / "context_packages.json"
            if pkg_file.exists():
                try:
                    pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
                    if isinstance(pkg_data, list):
                        package_count = len(pkg_data)
                except Exception:
                    pass

            # Check provider connectivity
            provider_reachable = self._settings.ollama.check_connection(timeout=1.0)
            overall_health = "healthy" if (provider_reachable and canonical_writable) else (
                "degraded" if canonical_writable else "unavailable"
            )

            # Check concurrency state if container provided
            concurrency_depth = 0
            concurrency_capacity = 5
            concurrency_available = 1
            if container is not None and hasattr(container, "concurrency_guard"):
                guard = container.concurrency_guard
                concurrency_depth = getattr(guard, "waiting_count", 0)
                concurrency_capacity = getattr(guard, "_max_queue", 5)
                sem = getattr(guard, "_semaphore", None)
                if sem is not None:
                    concurrency_available = getattr(sem, "_value", 1)

            bundle["health"] = {
                "overall_status": overall_health,
                "provider": {
                    "type": "ollama",
                    "reachable": provider_reachable,
                    "host": self._settings.ollama.host,
                    "port": self._settings.ollama.port,
                    "active_model": self._settings.ollama.llm_model,
                    "offline_fallback_ready": True,
                },
                "storage": {
                    "canonical_root_exists": canonical_exists,
                    "canonical_root_writable": canonical_writable,
                    "canonical_free_space_mb": canonical_free_mb,
                    "legacy_root_detected": legacy_root.exists(),
                    "cache_file_count": cache_file_count,
                    "cache_total_bytes": cache_total_bytes,
                },
                "workspaces": {
                    "repository_count": repo_count,
                    "context_package_count": package_count,
                    "repositories": repos_summary,
                },
                "concurrency": {
                    "queue_depth": concurrency_depth,
                    "queue_capacity": concurrency_capacity,
                    "available_slots": concurrency_available,
                },
                "mcp_runtime": {
                    "stdio_ready": True,
                    "tools_count": 5,
                },
            }

        # 3. Recent Sanitized Structured Logs
        if include_logs:
            raw_logs = read_recent_logs(
                max_entries=max_log_lines,
                log_dir=self._settings.logging.log_dir,
                log_file_name=self._settings.logging.log_file_name,
            )
            bundle["recent_logs"] = sanitize_dict_secrets(raw_logs)

        return sanitize_dict_secrets(bundle)

    def export_bundle(
        self,
        output_path: Optional[Path | str] = None,
        include_logs: bool = True,
        max_log_lines: int = 50,
        include_config: bool = True,
        include_health: bool = True,
        container: Optional[Any] = None,
    ) -> Path:
        """Generate and write a sanitized diagnostic bundle JSON file."""
        diagnostics = self.generate_diagnostics(
            include_logs=include_logs,
            max_log_lines=max_log_lines,
            include_config=include_config,
            include_health=include_health,
            container=container,
        )

        if output_path is not None:
            target_path = Path(output_path).resolve()
            if target_path.is_dir():
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = target_path / f"diagnostic_bundle_{timestamp_str}.json"
        else:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            diag_dir = Path.home() / ".retrack" / "diagnostics"
            diag_dir.mkdir(parents=True, exist_ok=True)
            target_path = diag_dir / f"diagnostic_bundle_{timestamp_str}.json"

        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        tmp_fd, tmp_file = tempfile.mkstemp(
            prefix="diag_tmp_", suffix=".json", dir=str(target_path.parent)
        )
        try:
            with open(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(diagnostics, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, target_path)
            logger.info("Successfully exported diagnostic bundle to %s", target_path)
            return target_path
        except Exception:
            if os.path.exists(tmp_file):
                try:
                    os.unlink(tmp_file)
                except OSError:
                    pass
            raise
