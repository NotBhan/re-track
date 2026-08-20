"""System, health, settings, and provider use cases for RE:Track.

Coordinates hardware telemetry, service status, settings persistence, and provider updates.
All dependencies are explicitly injected via constructor.
"""

import logging
from pathlib import Path
import time
from typing import Any, Callable, Coroutine, Optional

from app.api.schemas import (
    AppSettingsResponse,
    BackendStatusResponse,
    CogneeSettingsRequest,
    ErrorResponse,
    HealthResponse,
)
from app.config.settings import Settings
from app.models.errors import CogneeServiceError
from app.models.provider import ProviderType
from app.services.cognee_service import CogneeService
from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)


class SystemUseCases:
    """Orchestrates system health telemetry, status, application settings, and provider management."""

    def __init__(
        self,
        settings_getter: Callable[[], Settings],
        cognee_service_getter: Callable[[], Optional[CogneeService]],
        llm_provider_getter: Callable[[], Optional[LLMProviderService]],
        provider_updater_fn: Callable[[str, str, str, str], Coroutine[Any, Any, dict | ErrorResponse]],
        version: str = "0.1.0",
    ) -> None:
        self._get_settings = settings_getter
        self._get_cognee = cognee_service_getter
        self._get_llm_provider = llm_provider_getter
        self._update_provider_fn = provider_updater_fn
        self.version = version

    async def health(self) -> HealthResponse | ErrorResponse:
        """Check system health: Ollama reachability, Cognee status, and hardware telemetry."""
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
                    ollama_ok = p_health.is_reachable
                    active_model = p_health.active_model
                except Exception:
                    ollama_ok = False
            else:
                ollama_ok = settings.ollama.check_connection()
                active_model = settings.ollama.llm_model

            cognee_ok = cognee.is_initialized if cognee else False
            overall_status = "ok" if (ollama_ok and cognee_ok) else "degraded"

            # Telemetry collection (RAM, CPU, GPU)
            ram_total = 0.0
            ram_used = 0.0
            cpu_pct = 0.0
            try:
                import psutil
                mem = psutil.virtual_memory()
                ram_total = round(mem.total / (1024 ** 3), 1)
                ram_used = round(mem.used / (1024 ** 3), 1)
                cpu_pct = round(psutil.cpu_percent(interval=None), 1)
            except Exception:
                pass

            vram_total = 0.0
            vram_used = 0.0
            gpu_name = None

            # 1. Try Linux sysfs DRM mem_info (AMD Radeon / Intel / generic DRM drivers)
            try:
                for card in sorted(Path("/sys/class/drm").glob("card*")):
                    vram_tot_f = card / "device" / "mem_info_vram_total"
                    vram_used_f = card / "device" / "mem_info_vram_used"
                    if vram_tot_f.exists() and vram_used_f.exists():
                        tot = int(vram_tot_f.read_text().strip()) / (1024 ** 3)
                        used = int(vram_used_f.read_text().strip()) / (1024 ** 3)
                        if tot > vram_total:
                            vram_total = round(tot, 1)
                            vram_used = round(used, 1)
                            gpu_name = "AMD Radeon GPU"
            except Exception:
                pass

            # 2. Try NVIDIA SMI if sysfs didn't find dedicated VRAM
            if vram_total == 0.0:
                try:
                    import subprocess
                    out = subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=name,memory.total,memory.used", "--format=csv,noheader,nounits"],
                        stderr=subprocess.DEVNULL,
                        timeout=1,
                    ).decode().strip()
                    if out:
                        parts = [p.strip() for p in out.split(",")]
                        if len(parts) >= 3:
                            gpu_name = parts[0]
                            vram_total = round(float(parts[1]) / 1024.0, 1)
                            vram_used = round(float(parts[2]) / 1024.0, 1)
                except Exception:
                    pass

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
            )

            elapsed = time.monotonic() - start
            logger.info("use_case: health() complete | status=%s | %.2fs", overall_status, elapsed)
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
                    ollama_ok = p_health.is_reachable
                    active_model = p_health.active_model
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
                llm_prov = llm_provider.provider_type.value

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
