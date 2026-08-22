"""System, health, settings, and provider use cases for RE:Track.

Coordinates hardware telemetry, service status, settings persistence, and provider updates.
All dependencies are explicitly injected via constructor capability ports.
"""

import logging
import time
from typing import Any, Callable, Coroutine, Optional

from app.application.dto import (
    AppSettingsResponse,
    BackendStatusResponse,
    CogneeSettingsRequest,
    DetailedHealthResponse,
    ErrorResponse,
    HealthResponse,
)
from app.application.ports.hardware_telemetry import (
    HardwareTelemetry,
    HardwareTelemetryPort,
)
from app.application.ports.llm_provider import LLMProviderPort
from app.application.ports.memory import MemoryLifecyclePort
from app.config.settings import Settings
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType

logger = logging.getLogger(__name__)


class SystemUseCases:
    """Orchestrates system health telemetry, status, application settings, and provider management."""

    def __init__(
        self,
        settings_getter: Callable[[], Settings],
        cognee_service_getter: Callable[[], Optional[MemoryLifecyclePort]],
        llm_provider_getter: Callable[[], Optional[LLMProviderPort]],
        provider_updater_fn: Callable[[str, str, str, str], Coroutine[Any, Any, dict | ErrorResponse]],
        telemetry_port: Optional[HardwareTelemetryPort] = None,
        concurrency_guard: Optional[Any] = None,
        version: Optional[str] = None,
    ) -> None:
        from app import __version__
        self._get_settings = settings_getter
        self._get_cognee = cognee_service_getter
        self._get_llm_provider = llm_provider_getter
        self._update_provider_fn = provider_updater_fn
        self._telemetry = telemetry_port
        self._concurrency_guard = concurrency_guard
        self.version = version or __version__

    async def health(self) -> HealthResponse | ErrorResponse:
        """Check system health: Ollama reachability, Cognee status, storage metrics, and hardware telemetry."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            cognee = self._get_cognee()
            llm_provider = self._get_llm_provider()

            ollama_ok = False
            active_model = None

            if llm_provider:
                try:
                    p_health = await llm_provider.check_health()
                    ollama_ok = getattr(p_health, "is_reachable", False)
                    active_model = getattr(p_health, "active_model", None)
                except Exception:
                    ollama_ok = False
            else:
                ollama_ok = settings.ollama.check_connection()
                active_model = settings.ollama.llm_model

            cognee_ok = cognee.is_initialized if cognee else False
            overall_status = "ok" if (ollama_ok and cognee_ok) else "degraded"

            # Phase 9C storage and cache checks
            from pathlib import Path
            import os
            import json

            canonical_root = Path.home() / ".retrack"
            legacy_root = Path.home() / ".andes"
            canonical_exists = canonical_root.exists()
            canonical_writable = canonical_exists and os.access(canonical_root, os.W_OK)

            # Cache stats
            cache_files = 0
            cache_bytes = 0
            cache_dir = canonical_root / "cache"
            if cache_dir.exists() and cache_dir.is_dir():
                for f in cache_dir.glob("*"):
                    if f.is_file():
                        cache_files += 1
                        try:
                            cache_bytes += f.stat().st_size
                        except OSError:
                            pass

            # Repo count
            repo_count = 0
            repo_file = canonical_root / "indexed_repos.json"
            if not repo_file.exists():
                repo_file = canonical_root / "repositories.json"
            if not repo_file.exists() and legacy_root.exists():
                repo_file = legacy_root / "indexed_repos.json"
            if repo_file.exists():
                try:
                    r_data = json.loads(repo_file.read_text(encoding="utf-8"))
                    if isinstance(r_data, list):
                        repo_count = len(r_data)
                except Exception:
                    pass

            # Package count
            pkg_count = 0
            pkg_file = canonical_root / "context_packages.json"
            if not pkg_file.exists() and legacy_root.exists():
                pkg_file = legacy_root / "context_packages.json"
            if pkg_file.exists():
                try:
                    p_data = json.loads(pkg_file.read_text(encoding="utf-8"))
                    if isinstance(p_data, list):
                        pkg_count = len(p_data)
                except Exception:
                    pass

            # Concurrency metrics
            c_queue_depth = 0
            c_queue_cap = 5
            c_avail_slots = 1
            if self._concurrency_guard is not None:
                c_queue_depth = getattr(self._concurrency_guard, "waiting_count", 0)
                c_queue_cap = getattr(self._concurrency_guard, "_max_queue", 5)
                sem = getattr(self._concurrency_guard, "_semaphore", None)
                if sem is not None:
                    c_avail_slots = getattr(sem, "_value", 1)

            # Health classification
            if not canonical_writable and canonical_exists:
                health_class = "unavailable"
            elif ollama_ok and cognee_ok:
                health_class = "healthy"
            elif canonical_writable:
                health_class = "degraded"
            else:
                health_class = "not_configured"

            # Telemetry collection via HardwareTelemetryPort
            if self._telemetry:
                telem = self._telemetry.get_telemetry()
                ram_total = telem.ram_total_gb
                ram_used = telem.ram_used_gb
                cpu_pct = telem.cpu_percent
                vram_total = telem.vram_total_gb
                vram_used = telem.vram_used_gb
                gpu_name = telem.gpu_name
            else:
                ram_total = 16.0
                ram_used = 8.0
                cpu_pct = 10.0
                vram_total = 0.0
                vram_used = 0.0
                gpu_name = None

            ram_pct = round((ram_used / ram_total) * 100, 1) if ram_total > 0 else 0.0
            high_mem_pressure = ram_pct >= 90.0

            gpu_presence = "None"
            if gpu_name:
                if "AMD" in gpu_name:
                    gpu_presence = "AMD"
                elif "NVIDIA" in gpu_name or "GeForce" in gpu_name or "RTX" in gpu_name:
                    gpu_presence = "NVIDIA"
                else:
                    gpu_presence = "Generic"

            exec_device = "GPU" if (gpu_presence != "None" and (vram_used > 0.1 or vram_total > 0)) else "CPU"

            response = HealthResponse(
                status=overall_status,
                ollama_reachable=ollama_ok,
                cognee_initialized=cognee_ok,
                version=self.version,
                ram_total_gb=ram_total,
                ram_used_gb=ram_used,
                ram_percent=ram_pct,
                high_memory_pressure=high_mem_pressure,
                cpu_percent=cpu_pct,
                gpu_presence=gpu_presence,
                gpu_name=gpu_name,
                vram_total_gb=vram_total,
                vram_used_gb=vram_used,
                execution_device=exec_device,
                active_model=active_model,
                health_state=health_class,
                storage_canonical_exists=canonical_exists,
                storage_canonical_writable=canonical_writable,
                legacy_storage_detected=legacy_root.exists(),
                repository_count=repo_count,
                context_package_count=pkg_count,
                cache_files_count=cache_files,
                cache_total_bytes=cache_bytes,
                concurrency_queue_depth=c_queue_depth,
                concurrency_queue_capacity=c_queue_cap,
                concurrency_available_slots=c_avail_slots,
                mcp_server_ready=True,
                recent_errors_count=0,
            )

            elapsed = time.monotonic() - start
            logger.info("use_case: health() complete | status=%s | health_state=%s | %.2fs", overall_status, health_class, elapsed)
            return response

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: health() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Health check failed: {e}",
            )

    async def get_backend_status(self) -> BackendStatusResponse | ErrorResponse:
        """Get detailed backend status and configuration."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            cognee = self._get_cognee()
            llm_provider = self._get_llm_provider()

            ollama_ok = False
            active_model = settings.ollama.llm_model
            if llm_provider:
                try:
                    p_health = await llm_provider.check_health()
                    ollama_ok = getattr(p_health, "is_reachable", False)
                    active_model = getattr(p_health, "active_model", None)
                except Exception:
                    ollama_ok = False
            else:
                ollama_ok = settings.ollama.check_connection()

            cognee_ok = cognee.is_initialized if cognee else False
            overall_status = "ok" if (ollama_ok and cognee_ok) else "degraded"

            response = BackendStatusResponse(
                status=overall_status,
                ollama_reachable=ollama_ok,
                ollama_host=settings.ollama.host,
                ollama_port=settings.ollama.port,
                llm_model=active_model,
                embedding_model=settings.ollama.embedding_model,
                vector_db=settings.storage.vector_db,
                graph_db=settings.storage.graph_db,
                relational_db=settings.storage.relational_db,
                data_root=str(settings.storage.data_root),
                system_root=str(settings.storage.system_root),
                cognee_initialized=cognee_ok,
                gpu_presence="None",
                execution_device="CPU",
            )

            elapsed = time.monotonic() - start
            logger.info("use_case: get_backend_status() complete | %.2fs", elapsed)
            return response

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_backend_status() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Status check failed: {e}",
            )

    async def get_app_settings(self) -> AppSettingsResponse | ErrorResponse:
        """Get current persistent settings."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            settings.load_persisted_settings()

            response = AppSettingsResponse(
                success=True,
                vector_db=settings.storage.vector_db,
                graph_db=settings.storage.graph_db,
                relational_db=settings.storage.relational_db,
                enable_kg_extraction=settings.storage.enable_kg_extraction,
                auto_link_entities=settings.storage.auto_link_entities,
                caching=settings.service.caching,
                llm_model=settings.ollama.llm_model,
                embedding_model=settings.ollama.embedding_model,
                llm_host=settings.ollama.host,
                llm_port=settings.ollama.port,
                data_root=str(settings.storage.data_root),
                system_root=str(settings.storage.system_root),
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: get_app_settings() complete | %.2fs", elapsed)
            return response
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_app_settings() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get app settings: {e}",
            )

    async def update_cognee_settings(
        self,
        request: CogneeSettingsRequest,
    ) -> AppSettingsResponse | ErrorResponse:
        """Update and persist Cognee runtime and storage configuration."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            if getattr(request, "vector_db", None) is not None:
                settings.storage.vector_db = request.vector_db.strip().lower()
            if getattr(request, "graph_db", None) is not None:
                settings.storage.graph_db = request.graph_db.strip().lower()
            if getattr(request, "enable_kg_extraction", None) is not None:
                settings.storage.enable_kg_extraction = request.enable_kg_extraction
            if getattr(request, "auto_link_entities", None) is not None:
                settings.storage.auto_link_entities = request.auto_link_entities
            if getattr(request, "caching", None) is not None:
                settings.service.caching = request.caching

            settings.save_persisted_settings()

            llm_prov = "ollama"
            llm_provider = self._get_llm_provider()
            if llm_provider is not None:
                provider_type = getattr(llm_provider, "provider_type", None)
                if hasattr(provider_type, "value"):
                    llm_prov = provider_type.value
                elif isinstance(provider_type, str):
                    llm_prov = provider_type

            response = AppSettingsResponse(
                success=True,
                vector_db=settings.storage.vector_db,
                graph_db=settings.storage.graph_db,
                relational_db=settings.storage.relational_db,
                enable_kg_extraction=settings.storage.enable_kg_extraction,
                auto_link_entities=settings.storage.auto_link_entities,
                caching=settings.service.caching,
                data_root=str(settings.storage.data_root),
                system_root=str(settings.storage.system_root),
                llm_provider=llm_prov,
                llm_host=settings.ollama.host,
                llm_port=settings.ollama.port,
                llm_model=settings.ollama.llm_model,
                embedding_model=settings.ollama.embedding_model,
            )
            elapsed = time.monotonic() - start
            logger.info("use_case: update_cognee_settings() complete | %.2fs", elapsed)
            return response
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: update_cognee_settings() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to update settings: {e}",
            )

    async def update_provider(
        self,
        provider: str,
        base_url: str,
        model: str,
        api_key: str = "local",
    ) -> dict | ErrorResponse:
        """Hot-reload the active LLM inference provider."""
        return await self._update_provider_fn(provider, base_url, model, api_key)

    async def get_detailed_health(self) -> DetailedHealthResponse | ErrorResponse:
        """Get enriched system health with storage paths and recent sanitized log entries."""
        base_health = await self.health()
        if isinstance(base_health, ErrorResponse):
            return base_health

        from pathlib import Path
        from app.core.logging import read_recent_logs

        settings = self._get_settings()
        recent_logs = read_recent_logs(
            max_entries=20,
            log_dir=settings.logging.log_dir,
            log_file_name=settings.logging.log_file_name,
        )

        canonical_root = str(Path.home() / ".retrack")
        legacy_root = str(Path.home() / ".andes")

        return DetailedHealthResponse(
            **base_health.model_dump(),
            diagnostics_log_entries=recent_logs,
            storage_paths={
                "canonical_root": canonical_root,
                "legacy_root": legacy_root,
                "logs_directory": str(settings.logging.log_dir),
                "cache_directory": str(Path.home() / ".retrack" / "cache"),
            },
        )

    def export_diagnostics(
        self,
        output_path: Optional[Any] = None,
        include_logs: bool = True,
        max_log_lines: int = 50,
        include_config: bool = True,
        include_health: bool = True,
    ) -> dict[str, Any] | str:
        """Export sanitized operational diagnostics bundle."""
        from app.services.diagnostics_service import DiagnosticsService

        diag_service = DiagnosticsService(settings=self._get_settings())
        if output_path:
            exported_path = diag_service.export_bundle(
                output_path=output_path,
                include_logs=include_logs,
                max_log_lines=max_log_lines,
                include_config=include_config,
                include_health=include_health,
            )
            return str(exported_path)
        else:
            return diag_service.generate_diagnostics(
                include_logs=include_logs,
                max_log_lines=max_log_lines,
                include_config=include_config,
                include_health=include_health,
            )

    def get_recent_logs(self, max_entries: int = 50) -> list[dict[str, Any]]:
        """Get recent sanitized log entries."""
        from app.core.logging import read_recent_logs

        settings = self._get_settings()
        return read_recent_logs(
            max_entries=max_entries,
            log_dir=settings.logging.log_dir,
            log_file_name=settings.logging.log_file_name,
        )

