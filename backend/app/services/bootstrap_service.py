"""Bootstrap and first-run initialization service for RE:Track.

Ensures canonical storage directories (~/.retrack/), configuration, and data stores
are safely, idempotently created without mutating existing data or touching legacy storage.
"""

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import socket
from typing import Optional

from app import __version__
from app.config.settings import Settings, DEFAULT_SETTINGS_STORE_PATH, DEFAULT_LEGACY_SETTINGS_STORE_PATH

logger = logging.getLogger(__name__)


@dataclass
class BootstrapResult:
    """Detailed summary of the bootstrap initialization execution."""

    success: bool
    version: str
    retrack_dir: str
    created_directories: list[str] = field(default_factory=list)
    existing_directories: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    preserved_files: list[str] = field(default_factory=list)
    provider_reachable: bool = False
    provider_host: str = "localhost"
    provider_port: int = 11434
    legacy_data_detected: bool = False
    legacy_dir: Optional[str] = None
    legacy_item_count: int = 0
    message: str = ""


class BootstrapService:
    """Service responsible for first-run bootstrap and directory initialization."""

    def __init__(
        self,
        retrack_dir: Optional[Path | str] = None,
        legacy_dir: Optional[Path | str] = None,
    ):
        self._retrack_dir = Path(retrack_dir) if retrack_dir is not None else Path.home() / ".retrack"
        self._legacy_dir = Path(legacy_dir) if legacy_dir is not None else Path.home() / ".andes"

    def initialize(self, check_provider: bool = True) -> BootstrapResult:
        """Initialize the RE:Track environment idempotently.

        Args:
            check_provider: Whether to test connectivity to the configured local provider.

        Returns:
            BootstrapResult with structured details on all created or verified paths.
        """
        created_dirs: list[str] = []
        existing_dirs: list[str] = []
        created_files: list[str] = []
        preserved_files: list[str] = []

        # 1. Ensure required directory tree exists
        required_dirs = [
            self._retrack_dir,
            self._retrack_dir / "manifests",
            self._retrack_dir / "cache",
            self._retrack_dir / "backups",
            self._retrack_dir / "logs",
        ]

        for d in required_dirs:
            if d.exists() and d.is_dir():
                existing_dirs.append(str(d))
            else:
                d.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(d))

        # 2. Ensure canonical configuration file exists
        settings_file = self._retrack_dir / "settings.json"
        if settings_file.exists():
            preserved_files.append(str(settings_file))
        else:
            default_settings = {
                "version": __version__,
                "ollama": {
                    "host": "localhost",
                    "port": 11434,
                    "llm_model": "phi3:mini",
                    "embedding_model": "nomic-embed-text:latest",
                    "embedding_dimensions": 768,
                },
                "storage": {
                    "vector_db": "lancedb",
                    "graph_db": "kuzu",
                    "relational_db": "sqlite",
                },
            }
            settings_file.write_text(json.dumps(default_settings, indent=2))
            created_files.append(str(settings_file))

        # 3. Ensure canonical repositories metadata file exists
        repos_file = self._retrack_dir / "indexed_repos.json"
        if repos_file.exists():
            preserved_files.append(str(repos_file))
        else:
            repos_file.write_text("[]")
            created_files.append(str(repos_file))

        # Also support repositories.json alias
        repos_alias = self._retrack_dir / "repositories.json"
        if repos_alias.exists():
            preserved_files.append(str(repos_alias))
        else:
            repos_alias.write_text("[]")
            created_files.append(str(repos_alias))

        # 4. Ensure context packages file exists
        packages_file = self._retrack_dir / "context_packages.json"
        if packages_file.exists():
            preserved_files.append(str(packages_file))
        else:
            packages_file.write_text("{}")
            created_files.append(str(packages_file))

        # 5. Check local provider reachability (non-blocking)
        provider_ok = False
        host = "localhost"
        port = 11434
        if check_provider:
            try:
                # Load configured host/port if present
                if settings_file.exists():
                    try:
                        data = json.loads(settings_file.read_text())
                        host = data.get("ollama", {}).get("host", "localhost")
                        port = int(data.get("ollama", {}).get("port", 11434))
                    except Exception:
                        pass
                with socket.create_connection((host, port), timeout=1.0):
                    provider_ok = True
            except Exception:
                provider_ok = False

        # 6. Check for legacy ~/.andes data
        legacy_detected = False
        legacy_count = 0
        if self._legacy_dir.exists() and self._legacy_dir.is_dir():
            for p in self._legacy_dir.glob("*"):
                legacy_count += 1
            if legacy_count > 0:
                legacy_detected = True

        msg = (
            f"RE:Track v{__version__} environment initialized successfully at {self._retrack_dir}."
        )
        if legacy_detected:
            msg += f" Found {legacy_count} legacy item(s) in {self._legacy_dir}. Run 'retrack migrate' to copy."

        return BootstrapResult(
            success=True,
            version=__version__,
            retrack_dir=str(self._retrack_dir),
            created_directories=created_dirs,
            existing_directories=existing_dirs,
            created_files=created_files,
            preserved_files=preserved_files,
            provider_reachable=provider_ok,
            provider_host=host,
            provider_port=port,
            legacy_data_detected=legacy_detected,
            legacy_dir=str(self._legacy_dir) if legacy_detected else None,
            legacy_item_count=legacy_count,
            message=msg,
        )
