"""
Centralized configuration for RE:Track (RefinedEngine Track) backend.

Loads environment variables, validates provider settings,
and performs startup checks. Singleton via get_settings().
"""

import contextvars
import os
import socket
import logging
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.models.errors import ConfigurationError, OllamaConnectionError

logger = logging.getLogger(__name__)

# Default paths relative to backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_ROOT = _BACKEND_ROOT / ".cognee_data"
DEFAULT_SYSTEM_ROOT = _BACKEND_ROOT / ".cognee_system"
DEFAULT_SETTINGS_STORE_PATH = Path.home() / ".retrack" / "settings.json"
DEFAULT_LEGACY_SETTINGS_STORE_PATH = Path.home() / ".andes" / "settings.json"

# The .env file is resolved relative to the backend package, never the current
# working directory. Depending on cwd, a relative ".env" either applied or was
# silently skipped, so identical launches produced different configurations.
DEFAULT_ENV_FILE = _BACKEND_ROOT / ".env"

# Environment variables RE:Track writes for Cognee compatibility via
# Settings.apply_to_environment(). These are tracked so that a value written by
# one Settings instance can never be read back as if it were an operator-supplied
# override by a later Settings instance (process-global contamination).
MANAGED_ENVIRONMENT_KEYS: tuple[str, ...] = (
    "LLM_PROVIDER",
    "LLM_MODEL",
    "SEMANTIC_MEMORY_MODEL",
    "LLM_ENDPOINT",
    "LLM_API_KEY",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL",
    "EMBEDDING_ENDPOINT",
    "EMBEDDING_API_KEY",
    "EMBEDDING_DIMENSIONS",
    "HUGGINGFACE_TOKENIZER",
    "VECTOR_DB_PROVIDER",
    "GRAPH_DB_PROVIDER",
    "RELATIONAL_DB_PROVIDER",
    "DATA_ROOT_DIRECTORY",
    "SYSTEM_ROOT_DIRECTORY",
    "ENABLE_BACKEND_ACCESS_CONTROL",
    "CACHING",
    "COGNEE_SKIP_CONNECTION_TEST",
)

# Environment key -> logical Settings field. The single table driving both the
# environment-override layer and the Cognee-compatibility environment writer.
_ENVIRONMENT_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("LLM_PROVIDER", "llm_provider"),
    ("LLM_MODEL", "llm_model"),
    ("SEMANTIC_MEMORY_MODEL", "memory_model"),
    ("LLM_ENDPOINT", "llm_endpoint"),
    ("LLM_API_KEY", "llm_api_key"),
    ("EMBEDDING_PROVIDER", "embedding_provider"),
    ("EMBEDDING_MODEL", "embedding_model"),
    ("EMBEDDING_ENDPOINT", "embedding_endpoint"),
    ("EMBEDDING_API_KEY", "embedding_api_key"),
    ("EMBEDDING_DIMENSIONS", "embedding_dimensions"),
    ("HUGGINGFACE_TOKENIZER", "hf_tokenizer"),
    ("VECTOR_DB_PROVIDER", "vector_db"),
    ("GRAPH_DB_PROVIDER", "graph_db"),
    ("RELATIONAL_DB_PROVIDER", "relational_db"),
    ("DATA_ROOT_DIRECTORY", "data_root"),
    ("SYSTEM_ROOT_DIRECTORY", "system_root"),
    ("ENABLE_BACKEND_ACCESS_CONTROL", "enable_access_control"),
    ("CACHING", "caching"),
    ("COGNEE_SKIP_CONNECTION_TEST", "skip_connection_test"),
)

_TOP_LEVEL_FIELDS = frozenset(
    {
        "llm_provider",
        "llm_endpoint",
        "llm_api_key",
        "embedding_provider",
        "embedding_endpoint",
        "embedding_api_key",
    }
)
_OLLAMA_FIELDS = frozenset({"llm_model", "memory_model", "embedding_model", "embedding_dimensions", "hf_tokenizer", "host", "port"})
_STORAGE_FIELDS = frozenset({"vector_db", "graph_db", "relational_db", "data_root", "system_root"})
_SERVICE_FIELDS = frozenset({"enable_access_control", "caching", "skip_connection_test"})
_BOOL_FIELDS = frozenset({"enable_access_control", "caching", "skip_connection_test"})
_INT_FIELDS = frozenset({"embedding_dimensions", "port"})
_PATH_FIELDS = frozenset({"data_root", "system_root"})

# Human-readable precedence contract, surfaced in diagnostics and docs.
CONFIGURATION_PRECEDENCE: tuple[str, ...] = (
    "explicit constructor arguments",
    "operator environment variables (never values RE:Track wrote itself)",
    "persisted settings (~/.retrack/settings.json)",
    "backend/.env",
    "field defaults",
)

# Values RE:Track itself wrote into os.environ, keyed by variable name.
_applied_environment: dict[str, str] = {}

# Fields explicitly supplied to the Settings constructor for the active construction.
_explicit_init_fields: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar(
    "retrack_explicit_settings_fields", default=frozenset()
)


@contextmanager
def _suppress_applied_environment() -> Iterator[None]:
    """Temporarily remove environment variables RE:Track itself wrote.

    Without this, ``Settings()`` instances inherit the provider configuration of
    any earlier ``apply_to_environment()`` call, because pydantic reads os.environ
    on construction. Operator-set values that differ from what we wrote are left
    untouched, so genuine environment overrides keep working.
    """
    removed: dict[str, str] = {}
    for key in MANAGED_ENVIRONMENT_KEYS:
        value = os.environ.get(key)
        if value is None:
            continue
        if _applied_environment.get(key) == value:
            removed[key] = os.environ.pop(key)
    try:
        yield
    finally:
        for key, value in removed.items():
            os.environ[key] = value


def dotenv_layer() -> dict[str, str]:
    """Return the ``backend/.env`` values as the lowest explicit configuration layer.

    Parsed directly so that keys mapping to nested config (model names, storage
    roots) participate in the same precedence as top-level keys, instead of being
    silently ignored because they do not match a top-level field name.
    """
    path = DEFAULT_ENV_FILE
    if not path.exists():
        return {}
    try:
        from dotenv import dotenv_values

        return {key: str(value) for key, value in dotenv_values(str(path)).items() if value is not None}
    except Exception as e:  # pragma: no cover - malformed .env must not break startup
        logger.warning("Failed to read %s: %s", path, e)
        return {}


def operator_environment() -> dict[str, str]:
    """Return managed environment variables that were supplied by the operator.

    Values equal to what RE:Track last wrote itself are excluded, so a previous
    Settings instance cannot masquerade as an explicit environment override.
    """
    result: dict[str, str] = {}
    for key in MANAGED_ENVIRONMENT_KEYS:
        value = os.environ.get(key)
        if value is None:
            continue
        if _applied_environment.get(key) == value:
            continue
        result[key] = value
    return result


def clear_applied_environment() -> None:
    """Forget which environment variables RE:Track wrote.

    Used by diagnostics and test isolation; does not modify os.environ.
    """
    _applied_environment.clear()


class OllamaConfig(BaseSettings):
    """Ollama provider configuration."""

    host: str = Field(default="localhost", description="Ollama host")
    port: int = Field(default=11434, description="Ollama port")
    llm_model: str = Field(default="phi3:mini", description="LLM model name")
    memory_model: str = Field(
        default="",
        description=(
            "Dedicated model for semantic-memory extraction. Empty falls back to the "
            "configured inference model. A reasoning model can consume its whole "
            "generation budget on hidden reasoning and never emit the required JSON, "
            "so a non-reasoning instruct model is recommended for this stage."
        ),
    )
    embedding_model: str = Field(
        default="nomic-embed-text:latest", description="Embedding model name"
    )
    embedding_dimensions: int = Field(
        default=768, description="Embedding vector dimensions"
    )
    hf_tokenizer: str = Field(
        default="nomic-ai/nomic-embed-text-v1",
        description="HuggingFace tokenizer for token counting",
    )

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def llm_endpoint(self) -> str:
        return f"{self.base_url}/v1"

    @property
    def embedding_endpoint(self) -> str:
        return f"{self.base_url}/api/embed"

    def check_connection(self, timeout: float = 3.0) -> bool:
        """Return True if Ollama is reachable."""
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except (ConnectionRefusedError, OSError):
            return False


class StorageConfig(BaseSettings):
    """Storage provider configuration."""

    vector_db: str = Field(default="lancedb", description="Vector database provider")
    graph_db: str = Field(default="kuzu", description="Graph database provider")
    relational_db: str = Field(default="sqlite", description="Relational database provider")
    enable_kg_extraction: bool = Field(default=True, description="Enable knowledge graph extraction")
    auto_link_entities: bool = Field(default=False, description="Auto-link detected symbols & entities")
    data_root: Path = Field(default=DEFAULT_DATA_ROOT, description="Data storage root")
    system_root: Path = Field(default=DEFAULT_SYSTEM_ROOT, description="System storage root")


class LoggingConfig(BaseSettings):
    """Logging subsystem configuration."""

    level: str = Field(default="INFO", description="Minimum log level (DEBUG, INFO, WARNING, ERROR)")
    log_dir: Path = Field(default_factory=lambda: Path.home() / ".retrack" / "logs", description="Persistent log directory")
    log_file_name: str = Field(default="app.jsonl", description="Log file name")
    max_bytes: int = Field(default=10 * 1024 * 1024, description="Maximum size per log file in bytes (default: 10MB)")
    backup_count: int = Field(default=5, description="Number of rotated backup log files to retain")
    enable_file_logging: bool = Field(default=True, description="Enable structured file logging")
    enable_stderr_logging: bool = Field(default=True, description="Enable human-readable stderr logging")


class ServiceConfig(BaseSettings):
    """Service behavior configuration."""

    enable_access_control: bool = Field(
        default=False, description="Enable multi-user access control"
    )
    caching: bool = Field(default=False, description="Enable session memory caching")
    skip_connection_test: bool = Field(
        default=True, description="Skip startup connection tests"
    )


class Settings(BaseSettings):
    """Top-level configuration combining all sub-configs."""

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    llm_provider: str = Field(default="ollama", description="Active LLM provider: ollama, lmstudio, openai_compatible")
    llm_endpoint: str = Field(default="http://localhost:11434/v1", description="Active LLM endpoint base URL")
    llm_api_key: str = Field(default="local", description="Active LLM API key")

    # Embedding provider identity is intentionally independent from the LLM provider.
    # These are explicit so the retrieval tier can report the provider/model it is
    # actually configured to use, instead of assuming it matches the LLM.
    embedding_provider: str = Field(
        default="ollama",
        description="Embedding provider: ollama or openai-compatible (openai/lmstudio)",
    )
    embedding_endpoint: str = Field(
        default="",
        description="Embedding endpoint. Empty resolves to the Ollama /api/embed endpoint.",
    )
    embedding_api_key: str = Field(default="ollama", description="Embedding provider API key")

    settings_store_path: Path = Field(default_factory=lambda: DEFAULT_SETTINGS_STORE_PATH)
    legacy_settings_store_path: Path = Field(default_factory=lambda: DEFAULT_LEGACY_SETTINGS_STORE_PATH)

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **values: Any) -> None:
        # Record which fields the caller supplied explicitly, then construct with
        # any environment variables RE:Track wrote itself removed. This makes the
        # documented precedence deterministic and prevents cross-instance
        # contamination through the process environment.
        token = _explicit_init_fields.set(frozenset(values.keys()))
        try:
            with _suppress_applied_environment():
                super().__init__(**values)
        finally:
            _explicit_init_fields.reset(token)

    @staticmethod
    def configuration_precedence() -> tuple[str, ...]:
        """Return the documented configuration precedence, highest priority first."""
        return CONFIGURATION_PRECEDENCE

    def load_persisted_settings(
        self,
        store_path: Path | None = None,
        legacy_store_path: Path | None = None,
        exclude: frozenset[str] = frozenset(),
    ) -> None:
        """Load user-customized settings from persistent JSON file if present (canonical first, then legacy).

        ``exclude`` lists logical field names (and the group names ``ollama``,
        ``storage``, ``service``) that must not be overwritten — used to honour
        explicit constructor arguments, which outrank persisted settings.
        """
        exclude_ollama = "ollama" in exclude
        exclude_storage = "storage" in exclude
        exclude_service = "service" in exclude
        path = store_path or self.settings_store_path
        legacy_path = legacy_store_path or self.legacy_settings_store_path

        target_path: Optional[Path] = None
        if path.exists():
            target_path = path
        elif legacy_path.exists():
            target_path = legacy_path

        if not target_path:
            return

        try:
            import json
            data = json.loads(target_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return

            # Provider overrides (LLM and embedding identities are independent).
            if "llm_provider" in data and data["llm_provider"] and "llm_provider" not in exclude:
                self.llm_provider = str(data["llm_provider"])
            if "llm_endpoint" in data and data["llm_endpoint"] and "llm_endpoint" not in exclude:
                self.llm_endpoint = str(data["llm_endpoint"])
            if "llm_api_key" in data and data["llm_api_key"] is not None and "llm_api_key" not in exclude:
                self.llm_api_key = str(data["llm_api_key"])
            if "embedding_provider" in data and data["embedding_provider"] and "embedding_provider" not in exclude:
                self.embedding_provider = str(data["embedding_provider"])
            if "embedding_endpoint" in data and data["embedding_endpoint"] and "embedding_endpoint" not in exclude:
                self.embedding_endpoint = str(data["embedding_endpoint"])
            if "embedding_api_key" in data and data["embedding_api_key"] is not None and "embedding_api_key" not in exclude:
                self.embedding_api_key = str(data["embedding_api_key"])

            # Storage overrides
            if not exclude_storage:
                if "vector_db" in data and data["vector_db"]:
                    self.storage.vector_db = str(data["vector_db"])
                if "graph_db" in data and data["graph_db"]:
                    self.storage.graph_db = str(data["graph_db"])
                if "relational_db" in data and data["relational_db"]:
                    self.storage.relational_db = str(data["relational_db"])
            if "enable_kg_extraction" in data and "enable_kg_extraction" not in exclude:
                self.storage.enable_kg_extraction = bool(data["enable_kg_extraction"])
            if "auto_link_entities" in data and "auto_link_entities" not in exclude:
                self.storage.auto_link_entities = bool(data["auto_link_entities"])

            # Service overrides
            if not exclude_service and "caching" in data:
                self.service.caching = bool(data["caching"])

            # Inference / Ollama overrides
            if not exclude_ollama:
                if "llm_model" in data and data["llm_model"]:
                    self.ollama.llm_model = str(data["llm_model"])
                if "memory_model" in data and data["memory_model"]:
                    self.ollama.memory_model = str(data["memory_model"])
                if "embedding_model" in data and data["embedding_model"]:
                    self.ollama.embedding_model = str(data["embedding_model"])
                if "embedding_dimensions" in data and data["embedding_dimensions"]:
                    self.ollama.embedding_dimensions = int(data["embedding_dimensions"])
                if "llm_host" in data and data["llm_host"]:
                    self.ollama.host = str(data["llm_host"])
                if "llm_port" in data and data["llm_port"]:
                    self.ollama.port = int(data["llm_port"])

            # Logging overrides
            if "log_level" in data and data["log_level"]:
                self.logging.level = str(data["log_level"]).upper()
            if "log_max_bytes" in data and data["log_max_bytes"]:
                self.logging.max_bytes = int(data["log_max_bytes"])
            if "log_backup_count" in data and data["log_backup_count"]:
                self.logging.backup_count = int(data["log_backup_count"])
            if "enable_file_logging" in data:
                self.logging.enable_file_logging = bool(data["enable_file_logging"])

            logger.info("Loaded persistent settings from %s (provider=%s, endpoint=%s, model=%s)",
                        target_path, self.llm_provider, self.llm_endpoint, self.ollama.llm_model)
        except Exception as e:
            logger.warning("Failed to load persistent settings from %s: %s", target_path, e)

    def save_persisted_settings(self, store_path: Path | None = None) -> None:
        """Save current user-customized settings atomically to canonical persistent JSON file with 0600 permissions."""
        path = store_path or self.settings_store_path
        try:
            import json
            import os
            parent = path.parent
            parent.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(parent, 0o700)
            except OSError:
                pass

            data = {
                "llm_provider": self.llm_provider,
                "llm_endpoint": self.llm_endpoint,
                "llm_api_key": self.llm_api_key,
                "embedding_provider": self.embedding_provider,
                "embedding_endpoint": self.embedding_endpoint,
                "embedding_api_key": self.embedding_api_key,
                "embedding_dimensions": self.ollama.embedding_dimensions,
                "vector_db": self.storage.vector_db,
                "graph_db": self.storage.graph_db,
                "relational_db": self.storage.relational_db,
                "enable_kg_extraction": self.storage.enable_kg_extraction,
                "auto_link_entities": self.storage.auto_link_entities,
                "caching": self.service.caching,
                "llm_model": self.ollama.llm_model,
                "memory_model": self.ollama.memory_model,
                "embedding_model": self.ollama.embedding_model,
                "llm_host": self.ollama.host,
                "llm_port": self.ollama.port,
                "log_level": self.logging.level,
                "log_max_bytes": self.logging.max_bytes,
                "log_backup_count": self.logging.backup_count,
                "enable_file_logging": self.logging.enable_file_logging,
            }
            tmp_path = path.with_suffix(".tmp")
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            fd = os.open(tmp_path, flags, 0o600)
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            try:
                os.chmod(tmp_path, 0o600)
            except OSError:
                pass
            tmp_path.replace(path)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            logger.info("Saved persistent settings atomically to %s (0600 permissions)", path)
        except Exception as e:
            logger.error("Failed to save persistent settings to %s: %s", path, e)

    @model_validator(mode="after")
    def _resolve_configuration_precedence(self) -> "Settings":
        """Resolve every managed field against the single documented precedence.

        Highest priority wins, per field:

        1. explicit constructor arguments
        2. operator environment variables (never values RE:Track wrote itself)
        3. persisted settings (``~/.retrack/settings.json``)
        4. ``backend/.env``
        5. field defaults

        Layers 4 and 5 were already applied by pydantic during construction, and
        environment variables RE:Track wrote itself were removed for the duration
        of construction, so a prior Settings instance cannot contaminate this one.
        """
        explicit = _explicit_init_fields.get()
        skip: set[str] = set(explicit)
        if "ollama" in explicit:
            skip.update(_OLLAMA_FIELDS)
        if "storage" in explicit:
            skip.update(_STORAGE_FIELDS)
        if "service" in explicit:
            skip.update(_SERVICE_FIELDS)

        self._apply_configuration_layers(exclude=frozenset(skip))
        return self

    def _apply_configuration_layers(self, exclude: frozenset[str]) -> None:
        """Apply the .env -> persisted -> operator-environment layers in order.

        Layer 1 (explicit constructor arguments) and layer 5 (defaults) are applied
        elsewhere; ``exclude`` lists the fields that layer 1 owns.
        """
        # 4. backend/.env above defaults, for every managed field (including the
        #    nested model/storage keys a top-level-only dotenv source would miss).
        env_layer = dotenv_layer()
        for env_key, field in _ENVIRONMENT_FIELD_MAP:
            if field in exclude or env_key not in env_layer:
                continue
            self._assign_configuration_field(field, env_layer[env_key])

        # 3. Persisted user settings override .env and defaults.
        self.load_persisted_settings(exclude=exclude)

        # 2. Operator environment variables override persisted settings.
        operator_env = operator_environment()
        for env_key, field in _ENVIRONMENT_FIELD_MAP:
            if field in exclude or env_key not in operator_env:
                continue
            self._assign_configuration_field(field, operator_env[env_key])

    def reload_configuration(self) -> None:
        """Re-resolve configuration from .env, persisted settings, and the operator
        environment.

        Used to pick up external settings changes without restarting. Operator
        environment variables keep their documented precedence over persisted
        settings, so a reload can never demote an explicit override.
        """
        self._apply_configuration_layers(exclude=frozenset())

    def _assign_configuration_field(self, field: str, raw: Any) -> None:
        """Assign a managed field from a raw (string) configuration value."""
        if field in _BOOL_FIELDS:
            value: Any = str(raw).strip().lower() == "true"
        elif field in _INT_FIELDS:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                return
        elif field in _PATH_FIELDS:
            value = Path(str(raw))
        else:
            value = str(raw)

        if field in _TOP_LEVEL_FIELDS:
            setattr(self, field, value)
        elif field in _OLLAMA_FIELDS:
            setattr(self.ollama, field, value)
        elif field in _STORAGE_FIELDS:
            setattr(self.storage, field, value)
        elif field in _SERVICE_FIELDS:
            setattr(self.service, field, value)

    def resolve_embedding_endpoint(self) -> str:
        """Resolve the embedding endpoint without substituting another provider.

        An explicitly configured endpoint always wins. Only the Ollama provider
        has a derived default (``http://<host>:<port>/api/embed``); every other
        provider reports an empty endpoint so an unconfigured embedding provider
        surfaces as ``not_configured`` rather than being silently pointed at
        another service.
        """
        explicit = (self.embedding_endpoint or "").strip()
        if explicit:
            return explicit
        if self.embedding_provider_name() == "ollama":
            return self.ollama.embedding_endpoint
        return ""

    def embedding_provider_name(self) -> str:
        """Return the configured embedding provider exactly as configured (lowercased)."""
        return (self.embedding_provider or "ollama").strip().lower()

    def embedding_engine_provider(self) -> str:
        """Return the Cognee embedding engine name for the configured provider.

        This maps RE:Track provider aliases onto the engines Cognee actually
        exposes. It is a fixed, documented mapping — never a fallback to a
        different provider when the configured one is unavailable.
        """
        provider = self.embedding_provider_name()
        return {
            "lmstudio": "openai_compatible",
            "lm_studio": "openai_compatible",
            "lm-studio": "openai_compatible",
            "openai-compatible": "openai_compatible",
        }.get(provider, provider)

    def embedding_identity(self) -> dict[str, Any]:
        """Return the authoritative embedding provider identity (never inferred from the LLM)."""
        return {
            "provider": self.embedding_provider_name(),
            "endpoint": self.resolve_embedding_endpoint(),
            "model": self.ollama.embedding_model,
            "dimensions": self.ollama.embedding_dimensions,
            "api_key": self.embedding_api_key or "ollama",
        }

    def apply_to_environment(self, env: Optional[dict[str, str]] = None) -> None:
        """Write provider configuration into os.environ for Cognee compatibility.

        The written values are recorded so that later ``Settings`` instances do
        not treat them as operator-supplied environment overrides.
        """
        if env is None:
            env = self.configuration_environment()
        for key, value in env.items():
            os.environ[key] = str(value)
        _applied_environment.update({key: str(value) for key, value in env.items()})

    def configuration_environment(self) -> dict[str, str]:
        """Return the environment mapping Cognee expects for the active configuration."""
        embedding = self.embedding_identity()
        return {
            "LLM_PROVIDER": self.llm_provider or "ollama",
            "LLM_MODEL": self.ollama.llm_model,
            "SEMANTIC_MEMORY_MODEL": self.ollama.memory_model,
            "LLM_ENDPOINT": self.llm_endpoint or self.ollama.llm_endpoint,
            "LLM_API_KEY": self.llm_api_key or "local",
            "EMBEDDING_PROVIDER": embedding["provider"],
            "EMBEDDING_MODEL": self.ollama.embedding_model,
            "EMBEDDING_ENDPOINT": embedding["endpoint"],
            "EMBEDDING_API_KEY": embedding["api_key"],
            "EMBEDDING_DIMENSIONS": str(self.ollama.embedding_dimensions),
            "HUGGINGFACE_TOKENIZER": self.ollama.hf_tokenizer,
            "VECTOR_DB_PROVIDER": self.storage.vector_db,
            "GRAPH_DB_PROVIDER": self.storage.graph_db,
            "RELATIONAL_DB_PROVIDER": self.storage.relational_db,
            "DATA_ROOT_DIRECTORY": str(self.storage.data_root),
            "SYSTEM_ROOT_DIRECTORY": str(self.storage.system_root),
            "ENABLE_BACKEND_ACCESS_CONTROL": str(self.service.enable_access_control).lower(),
            "CACHING": str(self.service.caching).lower(),
            "COGNEE_SKIP_CONNECTION_TEST": str(self.service.skip_connection_test).lower(),
        }

    def configure_cognee(self) -> None:
        """Configure Cognee's internal config object with active provider and endpoint."""
        import cognee
        import litellm

        litellm.drop_params = True
        litellm.num_retries = 0
        os.environ["LITELLM_NUM_RETRIES"] = "0"

        self.apply_to_environment()

        # Map RE:Track's provider identity onto the litellm/Cognee provider used to
        # reach it. LM Studio is a first-class litellm provider: litellm reports
        # `supports_response_schema=True` for it, so Cognee constrains structured
        # output with `response_format: json_schema` — which LM Studio accepts —
        # instead of `json_object`, which LM Studio rejects with HTTP 400.
        prov_lower = (self.llm_provider or "ollama").lower()
        if "lm" in prov_lower or "studio" in prov_lower:
            cognee_llm_provider = "lm_studio"
        elif "openai" in prov_lower:
            cognee_llm_provider = "openai"
        else:
            cognee_llm_provider = "ollama"

        llm_endpoint = self.llm_endpoint or self.ollama.llm_endpoint
        llm_api_key = self.llm_api_key or "local"
        llm_model = self.ollama.llm_model

        cognee_model_prefix = {"lm_studio": "lm_studio/", "openai": "openai/"}.get(cognee_llm_provider)
        if cognee_model_prefix and not llm_model.startswith(cognee_model_prefix):
            llm_model = f"{cognee_model_prefix}{llm_model}"

        cognee.config.set_llm_provider(cognee_llm_provider)
        cognee.config.set_llm_model(llm_model)
        cognee.config.set_llm_api_key(llm_api_key)
        cognee.config.set_llm_endpoint(llm_endpoint)

        embedding = self.embedding_identity()
        # The embedding identity is independent from the LLM identity; the engine
        # name is an explicit, fixed mapping of the configured provider.
        embedding_provider = self.embedding_engine_provider()
        embedding_endpoint = embedding["endpoint"]
        embedding_api_key = embedding["api_key"]
        embedding_model = embedding["model"]

        if embedding_provider == "openai" and not (embedding_model.startswith("openai/") or embedding_model.startswith("lm_studio/")):
            embedding_model = f"openai/{embedding_model}"

        cognee.config.set_embedding_provider(embedding_provider)
        cognee.config.set_embedding_model(embedding_model)
        cognee.config.set_embedding_api_key(embedding_api_key)
        cognee.config.set_embedding_endpoint(embedding_endpoint)
        cognee.config.set_embedding_dimensions(self.ollama.embedding_dimensions)

        cognee.config.set_vector_db_provider(self.storage.vector_db)
        cognee.config.set_graph_database_provider(self.storage.graph_db)

        # Restore staticmethods if previously clobbered and invoke them with target paths
        try:
            from cognee.api.v1.config.config import config as cognee_config_cls
            cognee.config.system_root_directory = cognee_config_cls.system_root_directory
            cognee.config.data_root_directory = cognee_config_cls.data_root_directory
            cognee.config.system_root_directory(str(self.storage.system_root))
            cognee.config.data_root_directory(str(self.storage.data_root))
        except Exception:
            pass

        # Invalidate Cognee internal memoized configs so changes take effect immediately
        try:
            from cognee.base_config import get_base_config
            get_base_config.cache_clear()
        except (ImportError, AttributeError):
            pass
        try:
            from cognee.infrastructure.databases.graph.config import get_graph_config
            get_graph_config.cache_clear()
        except (ImportError, AttributeError):
            pass
        try:
            from cognee.infrastructure.databases.vector.config import get_vectordb_config
            get_vectordb_config.cache_clear()
        except (ImportError, AttributeError):
            pass
        try:
            from cognee.infrastructure.databases.relational.config import (
                get_migration_config,
                get_relational_config,
            )
            get_relational_config.cache_clear()
            get_migration_config.cache_clear()
        except (ImportError, AttributeError):
            pass
        try:
            from cognee.infrastructure.databases.relational.create_relational_engine import (
                create_relational_engine,
            )
            create_relational_engine.cache_clear()
        except (ImportError, AttributeError):
            pass
        try:
            from cognee.context_global_variables import (
                graph_db_config,
                vector_db_config,
                current_dataset_id,
            )
            graph_db_config.set(None)
            vector_db_config.set(None)
            current_dataset_id.set(None)
        except (ImportError, AttributeError):
            pass

    async def probe_embedding_provider(self, timeout: float = 3.0, max_age_seconds: float = 20.0) -> dict[str, Any]:
        """Explicitly verify the configured embedding provider and model are usable.

        Reports one truthful state and never substitutes another provider, endpoint,
        or model:

            available       - endpoint reachable and the configured model is listed
            model_missing   - endpoint reachable but the configured model is absent
            unreachable     - endpoint could not be reached
            not_configured  - endpoint or model is not configured

        Results are cached briefly so health polling does not add an outbound
        request on every call.
        """
        now = time.monotonic()
        identity = self.embedding_identity()
        provider = identity["provider"]
        endpoint = (identity["endpoint"] or "").rstrip("/")
        model = identity["model"]
        # The cache is keyed on the identity so a configuration change can never be
        # answered from a stale probe of a different provider/endpoint/model.
        cache_key = (provider, endpoint, str(model), str(identity["dimensions"]))

        cached = getattr(self, "_embedding_probe_cache", None)
        if cached is not None and cached[0] == cache_key and (now - cached[1]) < max_age_seconds:
            return cached[2]

        def _remember(payload: dict[str, Any]) -> dict[str, Any]:
            self._embedding_probe_cache = (cache_key, now, payload)
            return payload

        result: dict[str, Any] = {
            "provider": provider,
            "endpoint": endpoint,
            "model": model,
            "dimensions": identity["dimensions"],
            "state": "not_configured",
            "detail": None,
            "available_models": [],
        }

        if not endpoint or not model:
            result["detail"] = "Embedding endpoint or embedding model is not configured."
            return _remember(result)

        engine = self.embedding_engine_provider()
        try:
            import httpx

            async with httpx.AsyncClient(timeout=timeout) as client:
                if engine == "ollama":
                    base = endpoint[: -len("/api/embed")] if endpoint.endswith("/api/embed") else endpoint
                    resp = await client.get(f"{base}/api/tags")
                    resp.raise_for_status()
                    payload = resp.json()
                    names = [str(m.get("name", "")) for m in (payload.get("models") or [])]
                else:
                    models_url = endpoint if endpoint.endswith("/models") else f"{endpoint}/models"
                    resp = await client.get(
                        models_url,
                        headers={"Authorization": f"Bearer {identity['api_key']}"},
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    names = [str(m.get("id", "")) for m in (payload.get("data") or [])]
        except Exception as e:
            result["state"] = "unreachable"
            result["detail"] = f"Embedding provider '{provider}' unreachable at {endpoint}: {type(e).__name__}: {e}"
            return _remember(result)

        available = [n for n in names if n]
        result["available_models"] = available[:10]
        if not available:
            result["state"] = "model_missing"
            result["detail"] = (
                f"Embedding provider '{provider}' is reachable at {endpoint} but reports no models, "
                f"so '{model}' cannot be used."
            )
            return _remember(result)

        target = model
        for prefix in ("openai/", "lm_studio/", "lmstudio/", "ollama/"):
            if target.startswith(prefix):
                target = target[len(prefix):]

        def _matches(candidate: str, wanted: str) -> bool:
            cand, want = candidate.strip(), wanted.strip()
            return cand == want or cand.split(":")[0] == want.split(":")[0]

        if any(_matches(name, target) for name in available):
            result["state"] = "available"
        else:
            result["state"] = "model_missing"
            result["detail"] = (
                f"Embedding model '{model}' is not available at {endpoint}. "
                f"Available embeddings: {', '.join(available[:5])}. "
                "RE:Track will not substitute a different embedding model."
            )
        return _remember(result)

    def clear_embedding_probe_cache(self) -> None:
        """Invalidate the cached embedding availability probe."""
        self._embedding_probe_cache = None

    def validate_provider(self) -> None:
        """Check provider reachability if connection test is not skipped."""
        if self.service.skip_connection_test:
            return
        prov_lower = (self.llm_provider or "ollama").lower()
        if "ollama" in prov_lower:
            if not self.ollama.check_connection():
                raise OllamaConnectionError(
                    f"Ollama is not reachable at {self.ollama.base_url}. "
                    "Start it with: ollama serve"
                )

    def validate_ollama(self) -> None:
        """Check that Ollama is reachable and required models exist (backwards compatibility)."""
        self.validate_provider()

    def ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self.storage.data_root.mkdir(parents=True, exist_ok=True)
        self.storage.system_root.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
