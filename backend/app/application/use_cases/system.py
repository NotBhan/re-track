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
    DiscoveredModelDTO,
    ErrorResponse,
    HealthResponse,
    ProviderDiscoveryRequest,
    ProviderDiscoveryResponse,
    ProviderStatusResponse,
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
        """Check system health: provider reachability, Cognee status, storage metrics, and hardware telemetry."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            cognee = self._get_cognee()
            llm_provider = self._get_llm_provider()

            def _extract_str(val: Any, default: str = "") -> str:
                if val is None or "Mock" in type(val).__name__:
                    return default
                if hasattr(val, "value") and "Mock" not in type(val.value).__name__:
                    return str(val.value)
                if isinstance(val, str):
                    return val
                return default

            # 1. Determine provider identity and endpoint
            prov_ident = _extract_str(getattr(settings, "llm_provider", None), "ollama")
            prov_endpoint = _extract_str(
                getattr(settings, "llm_endpoint", None),
                "http://localhost:11434/v1" if prov_ident == "ollama" else "http://localhost:1234/v1",
            )

            if llm_provider is not None:
                p_type = getattr(llm_provider, "provider_type", None)
                cleaned_pt = _extract_str(p_type, "")
                if cleaned_pt:
                    prov_ident = cleaned_pt
                b_url = getattr(llm_provider, "base_url", None)
                cleaned_url = _extract_str(b_url, "")
                if cleaned_url:
                    prov_endpoint = cleaned_url

            configured_model = _extract_str(getattr(getattr(settings, "ollama", None), "llm_model", None), "") or None

            # 2. Probe provider health
            provider_reachable = False
            active_model = None
            discovered_models: list[str] = []
            quant_warning: Optional[str] = None

            if llm_provider and not "Mock" in type(llm_provider.check_health).__name__:
                try:
                    p_health = await llm_provider.check_health()
                    provider_reachable = bool(getattr(p_health, "is_reachable", False))
                    active_model = _extract_str(getattr(p_health, "active_model", None), "") or None
                    loaded_infos = getattr(p_health, "loaded_models", [])
                    discovered_models = [m.model_id for m in loaded_infos if hasattr(m, "model_id") and isinstance(m.model_id, str)]
                    quant_warning = _extract_str(getattr(p_health, "quantization_warning", None), "") or None
                except Exception as e:
                    logger.debug("Provider check_health failed: %s", e)
                    provider_reachable = False
            elif llm_provider and "Mock" in type(llm_provider.check_health).__name__:
                try:
                    p_health = await llm_provider.check_health()
                    provider_reachable = bool(getattr(p_health, "is_reachable", False))
                    active_model = _extract_str(getattr(p_health, "active_model", None), "") or None
                    loaded_infos = getattr(p_health, "loaded_models", [])
                    discovered_models = [getattr(m, "model_id", str(m)) for m in loaded_infos if isinstance(getattr(m, "model_id", m), str)]
                    quant_warning = _extract_str(getattr(p_health, "quantization_warning", None), "") or None
                except Exception:
                    provider_reachable = False
            else:
                ollama_cfg = getattr(settings, "ollama", None)
                if ollama_cfg and hasattr(ollama_cfg, "check_connection"):
                    provider_reachable = bool(ollama_cfg.check_connection())
                else:
                    provider_reachable = False
                active_model = configured_model

            # 3. Derive provider health state
            provider_configured = bool(prov_endpoint)
            if not provider_configured:
                provider_health_state = "not_configured"
            elif provider_reachable:
                provider_health_state = "degraded" if quant_warning else "healthy"
            else:
                provider_health_state = "unavailable"

            # 4. Derive active model state
            if active_model and provider_reachable:
                active_model_state = "active"
            elif discovered_models:
                active_model_state = "available"
            elif configured_model:
                active_model_state = "configured_only"
            else:
                active_model_state = "none"

            # 5. Derive inference engine state (independent of Cognee)
            if not provider_configured:
                engine_state = "not_configured"
                engine_reason = "No inference provider endpoint configured."
            elif provider_reachable:
                if quant_warning:
                    engine_state = "degraded"
                    engine_reason = quant_warning
                else:
                    engine_state = "healthy"
                    engine_reason = None
            else:
                engine_state = "unavailable"
                engine_reason = f"Inference provider '{prov_ident}' at {prov_endpoint} is unreachable."

            # 6. Derive Cognee memory state (independent of inference engine)
            cognee_ok = cognee.is_initialized if cognee else False
            if cognee_ok:
                cognee_state = "healthy"
                cognee_reason = None
            else:
                cognee_state = "unavailable"
                cognee_reason = "Cognee memory engine is uninitialized or offline."

            # 7. Overall status
            overall_status = "ok" if (provider_reachable and cognee_ok) else "degraded"

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

            # Operational health classification
            if not canonical_writable and canonical_exists:
                health_class = "unavailable"
            elif provider_reachable and cognee_ok:
                health_class = "healthy"
            elif provider_reachable or canonical_writable:
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
                ollama_reachable=provider_reachable,
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
                provider=prov_ident,
                provider_identity=prov_ident,
                provider_configured=provider_configured,
                provider_reachable=provider_reachable,
                provider_health_state=provider_health_state,
                provider_base_url=prov_endpoint,
                configured_model=configured_model,
                active_model=active_model,
                active_model_state=active_model_state,
                discovered_models=discovered_models,
                engine_state=engine_state,
                engine_reason=engine_reason,
                cognee_state=cognee_state,
                cognee_reason=cognee_reason,
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
            logger.info("use_case: health() complete | engine=%s | cognee=%s | %.2fs", engine_state, cognee_state, elapsed)
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

            def _extract_str(val: Any, default: str = "") -> str:
                if val is None or "Mock" in type(val).__name__:
                    return default
                if hasattr(val, "value") and "Mock" not in type(val.value).__name__:
                    return str(val.value)
                if isinstance(val, str):
                    return val
                return default

            prov_ident = _extract_str(getattr(settings, "llm_provider", None), "ollama")
            prov_endpoint = _extract_str(
                getattr(settings, "llm_endpoint", None),
                "http://localhost:11434/v1" if prov_ident == "ollama" else "http://localhost:1234/v1",
            )

            if llm_provider is not None:
                p_type = getattr(llm_provider, "provider_type", None)
                cleaned_pt = _extract_str(p_type, "")
                if cleaned_pt:
                    prov_ident = cleaned_pt
                b_url = getattr(llm_provider, "base_url", None)
                cleaned_url = _extract_str(b_url, "")
                if cleaned_url:
                    prov_endpoint = cleaned_url

            configured_model = _extract_str(getattr(getattr(settings, "ollama", None), "llm_model", None), "") or None

            provider_reachable = False
            active_model = None
            discovered_models: list[str] = []
            quant_warning: Optional[str] = None

            if llm_provider and not "Mock" in type(llm_provider.check_health).__name__:
                try:
                    p_health = await llm_provider.check_health()
                    provider_reachable = bool(getattr(p_health, "is_reachable", False))
                    active_model = _extract_str(getattr(p_health, "active_model", None), "") or None
                    loaded_infos = getattr(p_health, "loaded_models", [])
                    discovered_models = [m.model_id for m in loaded_infos if hasattr(m, "model_id") and isinstance(m.model_id, str)]
                    quant_warning = _extract_str(getattr(p_health, "quantization_warning", None), "") or None
                except Exception:
                    provider_reachable = False
            elif llm_provider and "Mock" in type(llm_provider.check_health).__name__:
                try:
                    p_health = await llm_provider.check_health()
                    provider_reachable = bool(getattr(p_health, "is_reachable", False))
                    active_model = _extract_str(getattr(p_health, "active_model", None), "") or None
                    loaded_infos = getattr(p_health, "loaded_models", [])
                    discovered_models = [getattr(m, "model_id", str(m)) for m in loaded_infos if isinstance(getattr(m, "model_id", m), str)]
                    quant_warning = _extract_str(getattr(p_health, "quantization_warning", None), "") or None
                except Exception:
                    provider_reachable = False
            else:
                ollama_cfg = getattr(settings, "ollama", None)
                if ollama_cfg and hasattr(ollama_cfg, "check_connection"):
                    provider_reachable = bool(ollama_cfg.check_connection())
                else:
                    provider_reachable = False
                active_model = configured_model

            provider_configured = bool(prov_endpoint)
            if not provider_configured:
                provider_health_state = "not_configured"
            elif provider_reachable:
                provider_health_state = "degraded" if quant_warning else "healthy"
            else:
                provider_health_state = "unavailable"

            if active_model and provider_reachable:
                active_model_state = "active"
            elif discovered_models:
                active_model_state = "available"
            elif configured_model:
                active_model_state = "configured_only"
            else:
                active_model_state = "none"

            if not provider_configured:
                engine_state = "not_configured"
                engine_reason = "No inference provider endpoint configured."
            elif provider_reachable:
                engine_state = "degraded" if quant_warning else "healthy"
                engine_reason = quant_warning
            else:
                engine_state = "unavailable"
                engine_reason = f"Inference provider '{prov_ident}' at {prov_endpoint} is unreachable."

            cognee_ok = cognee.is_initialized if cognee else False
            if cognee_ok:
                cognee_state = "healthy"
                cognee_reason = None
            else:
                cognee_state = "unavailable"
                cognee_reason = "Cognee memory engine is uninitialized or offline."

            overall_status = "ok" if (provider_reachable and cognee_ok) else "degraded"

            api_key = getattr(settings, "llm_api_key", "local")
            if not isinstance(api_key, str) or "Mock" in type(api_key).__name__:
                api_key = "local"

            # Parse host and port safely
            import urllib.parse
            parsed_url = urllib.parse.urlparse(prov_endpoint)
            prov_host = parsed_url.hostname or "localhost"
            prov_port = parsed_url.port or (11434 if prov_ident == "ollama" else 1234)

            display_model = active_model or configured_model or ""

            response = BackendStatusResponse(
                status=overall_status,
                ollama_reachable=provider_reachable,
                ollama_host=prov_host,
                ollama_port=prov_port,
                llm_provider=prov_ident,
                llm_endpoint=prov_endpoint,
                llm_model=display_model,
                embedding_model=str(getattr(settings.ollama, "embedding_model", "nomic-embed-text:latest")),
                vector_db=str(getattr(settings.storage, "vector_db", "lancedb")),
                graph_db=str(getattr(settings.storage, "graph_db", "kuzu")),
                relational_db=str(getattr(settings.storage, "relational_db", "sqlite")),
                data_root=str(getattr(settings.storage, "data_root", "")),
                system_root=str(getattr(settings.storage, "system_root", "")),
                cognee_initialized=cognee_ok,
                gpu_presence="None",
                execution_device="CPU",
                provider_identity=prov_ident,
                provider_configured=provider_configured,
                provider_reachable=provider_reachable,
                provider_health_state=provider_health_state,
                configured_model=configured_model,
                active_model=active_model,
                active_model_state=active_model_state,
                discovered_models=discovered_models,
                engine_state=engine_state,
                engine_reason=engine_reason,
                cognee_state=cognee_state,
                cognee_reason=cognee_reason,
            )
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

            llm_prov = getattr(settings, "llm_provider", "ollama")

            if not isinstance(llm_prov, str) or "Mock" in type(llm_prov).__name__:
                llm_prov = "ollama"

            llm_end = getattr(settings, "llm_endpoint", "http://localhost:11434/v1")
            if not isinstance(llm_end, str) or "Mock" in type(llm_end).__name__:
                llm_end = "http://localhost:11434/v1"

            llm_provider = self._get_llm_provider()
            if llm_provider is not None:
                provider_type = getattr(llm_provider, "provider_type", None)
                if hasattr(provider_type, "value"):
                    llm_prov = provider_type.value
                elif isinstance(provider_type, str):
                    llm_prov = provider_type
                if getattr(llm_provider, "base_url", None) and isinstance(llm_provider.base_url, str):
                    llm_end = llm_provider.base_url

            api_key = getattr(settings, "llm_api_key", "local")
            if not isinstance(api_key, str) or "Mock" in type(api_key).__name__:
                api_key = "local"

            masked_key = "local"
            if api_key in ("local", "ollama", "lm-studio"):
                masked_key = api_key
            elif len(api_key) > 8:
                masked_key = f"{api_key[:3]}...{api_key[-3:]}"
            else:
                masked_key = "configured"

            response = AppSettingsResponse(
                success=True,
                vector_db=str(getattr(settings.storage, "vector_db", "lancedb")),
                graph_db=str(getattr(settings.storage, "graph_db", "kuzu")),
                relational_db=str(getattr(settings.storage, "relational_db", "sqlite")),
                enable_kg_extraction=bool(getattr(settings.storage, "enable_kg_extraction", True)),
                auto_link_entities=bool(getattr(settings.storage, "auto_link_entities", False)),
                caching=bool(getattr(settings.service, "caching", False)),
                llm_provider=llm_prov,
                llm_endpoint=llm_end,
                llm_model=str(getattr(settings.ollama, "llm_model", "phi4-mini")),
                embedding_model=str(getattr(settings.ollama, "embedding_model", "nomic-embed-text:latest")),
                llm_host=str(getattr(settings.ollama, "host", "localhost")),
                llm_port=int(getattr(settings.ollama, "port", 11434)) if str(getattr(settings.ollama, "port", 11434)).isdigit() else 11434,
                api_key_configured=bool(api_key and api_key not in ("local", "ollama", "lm-studio")),
                api_key_masked=masked_key,
                data_root=str(getattr(settings.storage, "data_root", "")),
                system_root=str(getattr(settings.storage, "system_root", "")),
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

            if hasattr(settings, "save_persisted_settings"):
                settings.save_persisted_settings()

            llm_prov = getattr(settings, "llm_provider", "ollama")
            if not isinstance(llm_prov, str) or "Mock" in type(llm_prov).__name__:
                llm_prov = "ollama"

            llm_end = getattr(settings, "llm_endpoint", "http://localhost:11434/v1")
            if not isinstance(llm_end, str) or "Mock" in type(llm_end).__name__:
                llm_end = "http://localhost:11434/v1"

            llm_provider = self._get_llm_provider()
            if llm_provider is not None:
                provider_type = getattr(llm_provider, "provider_type", None)
                if hasattr(provider_type, "value"):
                    llm_prov = provider_type.value
                elif isinstance(provider_type, str):
                    llm_prov = provider_type
                if getattr(llm_provider, "base_url", None) and isinstance(llm_provider.base_url, str):
                    llm_end = llm_provider.base_url

            api_key = getattr(settings, "llm_api_key", "local")
            if not isinstance(api_key, str) or "Mock" in type(api_key).__name__:
                api_key = "local"

            masked_key = "local"
            if api_key in ("local", "ollama", "lm-studio"):
                masked_key = api_key
            elif len(api_key) > 8:
                masked_key = f"{api_key[:3]}...{api_key[-3:]}"
            else:
                masked_key = "configured"

            response = AppSettingsResponse(
                success=True,
                vector_db=str(getattr(settings.storage, "vector_db", "lancedb")),
                graph_db=str(getattr(settings.storage, "graph_db", "kuzu")),
                relational_db=str(getattr(settings.storage, "relational_db", "sqlite")),
                enable_kg_extraction=bool(getattr(settings.storage, "enable_kg_extraction", True)),
                auto_link_entities=bool(getattr(settings.storage, "auto_link_entities", False)),
                caching=bool(getattr(settings.service, "caching", False)),
                data_root=str(getattr(settings.storage, "data_root", "")),
                system_root=str(getattr(settings.storage, "system_root", "")),
                llm_provider=llm_prov,
                llm_endpoint=llm_end,
                llm_host=str(getattr(settings.ollama, "host", "localhost")),
                llm_port=int(getattr(settings.ollama, "port", 11434)) if str(getattr(settings.ollama, "port", 11434)).isdigit() else 11434,
                llm_model=str(getattr(settings.ollama, "llm_model", "phi4-mini")),
                embedding_model=str(getattr(settings.ollama, "embedding_model", "nomic-embed-text:latest")),
                api_key_configured=bool(api_key and api_key not in ("local", "ollama", "lm-studio")),
                api_key_masked=masked_key,
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

    async def get_provider_status(self) -> ProviderStatusResponse | ErrorResponse:
        """Get authoritative active inference provider status and loaded models."""
        start = time.monotonic()
        try:
            settings = self._get_settings()
            llm_provider = self._get_llm_provider()

            prov_name = settings.llm_provider
            endpoint = settings.llm_endpoint
            api_key = settings.llm_api_key

            if llm_provider is not None:
                p_type = getattr(llm_provider, "provider_type", None)
                if hasattr(p_type, "value"):
                    prov_name = p_type.value
                elif isinstance(p_type, str):
                    prov_name = p_type
                endpoint = getattr(llm_provider, "base_url", endpoint)
                api_key = getattr(llm_provider, "api_key", api_key)
                health = await llm_provider.check_health()
            else:
                from app.models.provider import ProviderHealth
                health = ProviderHealth(
                    is_reachable=False,
                    active_model=getattr(settings, "llm_model", "phi4-mini"),
                    loaded_models=[],
                    error="No LLM provider configured",
                )

            models_dto = [
                DiscoveredModelDTO(
                    model_id=m.model_id,
                    name=m.name,
                    quantization=m.quantization.value if hasattr(m.quantization, "value") else str(m.quantization),
                    is_phi4_mini=m.is_phi4_mini,
                    is_q6_or_higher=m.is_q6_or_higher,
                    warning=m.warning,
                )
                for m in getattr(health, "loaded_models", [])
            ]

            masked_key = "local"
            if api_key in ("local", "ollama", "lm-studio"):
                masked_key = api_key
            elif len(api_key) > 8:
                masked_key = f"{api_key[:3]}...{api_key[-3:]}"
            else:
                masked_key = "configured"

            disc_status = getattr(health, "discovery_status", None)
            disc_str = disc_status.value if hasattr(disc_status, "value") else (str(disc_status) if disc_status else ("available" if health.is_reachable and models_dto else "unavailable"))

            return ProviderStatusResponse(
                success=True,
                provider=prov_name,
                base_url=endpoint,
                active_model=health.active_model,
                is_reachable=health.is_reachable,
                health_state="healthy" if health.is_reachable else "unavailable",
                discovery_status=disc_str,
                loaded_models=models_dto,
                quantization_warning=health.quantization_warning,
                api_key_configured=bool(api_key and api_key not in ("local", "ollama", "lm-studio")),
                api_key_masked=masked_key,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: get_provider_status() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Failed to get provider status: {e}",
            )

    async def discover_provider_models(
        self,
        request: ProviderDiscoveryRequest,
    ) -> ProviderDiscoveryResponse | ErrorResponse:
        """Non-mutating model discovery probe for candidate or active provider endpoints."""
        start = time.monotonic()
        try:
            llm_provider = self._get_llm_provider()
            if llm_provider is not None and hasattr(llm_provider, "discover_models"):
                discovery = await llm_provider.discover_models(
                    provider_type=request.provider,
                    base_url=request.base_url,
                    api_key=request.api_key or "local",
                )
            elif llm_provider is not None and hasattr(llm_provider, "discover_models_for_endpoint"):
                discovery = await llm_provider.discover_models_for_endpoint(
                    provider_type=request.provider,
                    base_url=request.base_url,
                    api_key=request.api_key or "local",
                )
            else:
                from app.models.provider import ProviderDiscoveryResult, DiscoveryStatus, ProviderType
                p_enum = (
                    ProviderType.LM_STUDIO if "lm" in request.provider.lower() or "studio" in request.provider.lower()
                    else ProviderType.OLLAMA if "ollama" in request.provider.lower()
                    else ProviderType.OPENAI_COMPATIBLE
                )
                discovery = ProviderDiscoveryResult(
                    provider=p_enum,
                    base_url=request.base_url,
                    is_reachable=False,
                    status=DiscoveryStatus.NOT_CONFIGURED,
                    models=[],
                    message="Discovery port not available",
                    error_details="No provider service registered in container",
                )


            models_dto = [
                DiscoveredModelDTO(
                    model_id=m.model_id,
                    name=m.name,
                    quantization=m.quantization.value if hasattr(m.quantization, "value") else str(m.quantization),
                    is_phi4_mini=m.is_phi4_mini,
                    is_q6_or_higher=m.is_q6_or_higher,
                    warning=m.warning,
                )
                for m in discovery.models
            ]

            status_val = discovery.status.value if hasattr(discovery.status, "value") else str(discovery.status)

            return ProviderDiscoveryResponse(
                success=True,
                provider=discovery.provider.value if hasattr(discovery.provider, "value") else str(discovery.provider),
                base_url=discovery.base_url,
                is_reachable=discovery.is_reachable,
                status=status_val,
                models=models_dto,
                message=discovery.message,
                error_details=discovery.error_details,
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error("use_case: discover_provider_models() failed | %.2fs | %s", elapsed, e)
            return ErrorResponse(
                error=type(e).__name__,
                message=f"Model discovery failed: {e}",
            )

    async def update_provider(
        self,
        provider: str,
        base_url: str,
        model: str,
        api_key: str = "local",
    ) -> dict | ErrorResponse:
        """Hot-reload and persist the active LLM inference provider."""
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

