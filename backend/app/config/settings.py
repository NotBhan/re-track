"""
Centralized configuration for RE:Track (RefinedEngine Track) backend.

Loads environment variables, validates provider settings,
and performs startup checks. Singleton via get_settings().
"""

import os
import socket
import logging
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from app.models.errors import ConfigurationError, OllamaConnectionError

logger = logging.getLogger(__name__)

# Default paths relative to backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_ROOT = _BACKEND_ROOT / ".cognee_data"
DEFAULT_SYSTEM_ROOT = _BACKEND_ROOT / ".cognee_system"
DEFAULT_SETTINGS_STORE_PATH = Path.home() / ".retrack" / "settings.json"
DEFAULT_LEGACY_SETTINGS_STORE_PATH = Path.home() / ".andes" / "settings.json"


class OllamaConfig(BaseSettings):
    """Ollama provider configuration."""

    host: str = Field(default="localhost", description="Ollama host")
    port: int = Field(default=11434, description="Ollama port")
    llm_model: str = Field(default="phi3:mini", description="LLM model name")
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
    settings_store_path: Path = Field(default_factory=lambda: DEFAULT_SETTINGS_STORE_PATH)
    legacy_settings_store_path: Path = Field(default_factory=lambda: DEFAULT_LEGACY_SETTINGS_STORE_PATH)

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def load_persisted_settings(
        self,
        store_path: Path | None = None,
        legacy_store_path: Path | None = None,
    ) -> None:
        """Load user-customized settings from persistent JSON file if present (canonical first, then legacy)."""
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

            # Storage overrides
            if "vector_db" in data and data["vector_db"]:
                self.storage.vector_db = str(data["vector_db"])
            if "graph_db" in data and data["graph_db"]:
                self.storage.graph_db = str(data["graph_db"])
            if "relational_db" in data and data["relational_db"]:
                self.storage.relational_db = str(data["relational_db"])
            if "enable_kg_extraction" in data:
                self.storage.enable_kg_extraction = bool(data["enable_kg_extraction"])
            if "auto_link_entities" in data:
                self.storage.auto_link_entities = bool(data["auto_link_entities"])

            # Service overrides
            if "caching" in data:
                self.service.caching = bool(data["caching"])

            # Inference / Ollama overrides
            if "llm_model" in data and data["llm_model"]:
                self.ollama.llm_model = str(data["llm_model"])
            if "embedding_model" in data and data["embedding_model"]:
                self.ollama.embedding_model = str(data["embedding_model"])
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

            logger.info("Loaded persistent settings from %s (vector_db=%s, graph_db=%s, kg=%s)",
                        target_path, self.storage.vector_db, self.storage.graph_db, self.storage.enable_kg_extraction)
        except Exception as e:
            logger.warning("Failed to load persistent settings from %s: %s", target_path, e)

    def save_persisted_settings(self, store_path: Path | None = None) -> None:
        """Save current user-customized settings atomically to canonical persistent JSON file."""
        path = store_path or self.settings_store_path
        try:
            import json
            import os
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "vector_db": self.storage.vector_db,
                "graph_db": self.storage.graph_db,
                "relational_db": self.storage.relational_db,
                "enable_kg_extraction": self.storage.enable_kg_extraction,
                "auto_link_entities": self.storage.auto_link_entities,
                "caching": self.service.caching,
                "llm_model": self.ollama.llm_model,
                "embedding_model": self.ollama.embedding_model,
                "llm_host": self.ollama.host,
                "llm_port": self.ollama.port,
                "log_level": self.logging.level,
                "log_max_bytes": self.logging.max_bytes,
                "log_backup_count": self.logging.backup_count,
                "enable_file_logging": self.logging.enable_file_logging,
            }
            tmp_path = path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp_path.replace(path)
            logger.info("Saved persistent settings atomically to %s", path)
        except Exception as e:
            logger.error("Failed to save persistent settings to %s: %s", path, e)

    @model_validator(mode="after")
    def _apply_env_overrides(self) -> "Settings":
        """Read environment variables, then load persisted user settings."""
        self.ollama.llm_model = os.environ.get("LLM_MODEL", self.ollama.llm_model)
        self.ollama.embedding_model = os.environ.get(
            "EMBEDDING_MODEL", self.ollama.embedding_model
        )
        self.ollama.hf_tokenizer = os.environ.get(
            "HUGGINGFACE_TOKENIZER", self.ollama.hf_tokenizer
        )
        self.storage.vector_db = os.environ.get(
            "VECTOR_DB_PROVIDER", self.storage.vector_db
        )
        self.storage.graph_db = os.environ.get(
            "GRAPH_DB_PROVIDER", self.storage.graph_db
        )
        self.storage.relational_db = os.environ.get(
            "RELATIONAL_DB_PROVIDER", self.storage.relational_db
        )

        data_root = os.environ.get("DATA_ROOT_DIRECTORY")
        if data_root:
            self.storage.data_root = Path(data_root)

        system_root = os.environ.get("SYSTEM_ROOT_DIRECTORY")
        if system_root:
            self.storage.system_root = Path(system_root)

        ac = os.environ.get("ENABLE_BACKEND_ACCESS_CONTROL")
        if ac is not None:
            self.service.enable_access_control = ac.lower() == "true"

        caching = os.environ.get("CACHING")
        if caching is not None:
            self.service.caching = caching.lower() == "true"

        skip = os.environ.get("COGNEE_SKIP_CONNECTION_TEST")
        if skip is not None:
            self.service.skip_connection_test = skip.lower() == "true"

        # Apply persisted user settings (if any exist on disk)
        self.load_persisted_settings()

        return self

    def apply_to_environment(self) -> None:
        """Write current settings into os.environ for Cognee compatibility."""
        llm_endpoint = os.environ.get("LLM_ENDPOINT", self.ollama.llm_endpoint)
        embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT", self.ollama.embedding_endpoint)
        llm_provider = os.environ.get("LLM_PROVIDER", "ollama")
        embedding_provider = os.environ.get("EMBEDDING_PROVIDER", "ollama")
        llm_api_key = os.environ.get("LLM_API_KEY", "ollama")
        embedding_api_key = os.environ.get("EMBEDDING_API_KEY", "ollama")

        env = {
            "LLM_PROVIDER": llm_provider,
            "LLM_MODEL": self.ollama.llm_model,
            "LLM_ENDPOINT": llm_endpoint,
            "LLM_API_KEY": llm_api_key,
            "EMBEDDING_PROVIDER": embedding_provider,
            "EMBEDDING_MODEL": self.ollama.embedding_model,
            "EMBEDDING_ENDPOINT": embedding_endpoint,
            "EMBEDDING_API_KEY": embedding_api_key,
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
        for key, value in env.items():
            os.environ[key] = value

    def configure_cognee(self) -> None:
        """Configure Cognee's internal config object."""
        import cognee
        import litellm

        litellm.drop_params = True

        self.apply_to_environment()

        llm_provider = os.environ.get("LLM_PROVIDER", "ollama")
        embedding_provider = os.environ.get("EMBEDDING_PROVIDER", "ollama")
        llm_endpoint = os.environ.get("LLM_ENDPOINT", self.ollama.llm_endpoint)
        embedding_endpoint = os.environ.get("EMBEDDING_ENDPOINT", self.ollama.embedding_endpoint)
        llm_api_key = os.environ.get("LLM_API_KEY", "ollama")
        embedding_api_key = os.environ.get("EMBEDDING_API_KEY", "ollama")

        llm_model = self.ollama.llm_model
        if llm_provider == "openai" and not (llm_model.startswith("openai/") or llm_model.startswith("lm_studio/")):
            llm_model = f"openai/{llm_model}"

        cognee.config.set_llm_provider(llm_provider)
        cognee.config.set_llm_model(llm_model)
        cognee.config.set_llm_api_key(llm_api_key)
        cognee.config.set_llm_endpoint(llm_endpoint)

        embedding_model = self.ollama.embedding_model
        if embedding_provider == "openai" and not (embedding_model.startswith("openai/") or embedding_model.startswith("lm_studio/")):
            embedding_model = f"openai/{embedding_model}"

        cognee.config.set_embedding_provider(embedding_provider)
        cognee.config.set_embedding_model(embedding_model)
        cognee.config.set_embedding_api_key(embedding_api_key)
        cognee.config.set_embedding_endpoint(embedding_endpoint)
        cognee.config.set_embedding_dimensions(self.ollama.embedding_dimensions)

        cognee.config.set_vector_db_provider(self.storage.vector_db)
        cognee.config.set_graph_database_provider(self.storage.graph_db)

        cognee.config.data_root_directory = str(self.storage.data_root)
        cognee.config.system_root_directory = str(self.storage.system_root)

    def validate_ollama(self) -> None:
        """Check that Ollama is reachable and required models exist."""
        if not self.service.skip_connection_test and not self.ollama.check_connection():
            raise OllamaConnectionError(
                f"Ollama is not reachable at {self.ollama.base_url}. "
                "Start it with: ollama serve"
            )

    def ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self.storage.data_root.mkdir(parents=True, exist_ok=True)
        self.storage.system_root.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    return Settings()
