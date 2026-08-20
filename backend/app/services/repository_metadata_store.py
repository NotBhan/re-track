"""Repository metadata persistence store for RE:Track.

Encapsulates reading and writing indexed repository metadata from JSON storage on disk,
abstracting filesystem details away from application use cases.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class RepositoryMetadataStore(Protocol):
    """Protocol for indexed repository metadata storage."""

    def load(self) -> dict:
        """Load the indexed repository store from persistent storage."""
        ...

    def save(self, data: dict) -> None:
        """Persist repository metadata store to disk."""
        ...


class JsonRepositoryMetadataStore:
    """Concrete filesystem JSON implementation of RepositoryMetadataStore."""

    def __init__(
        self,
        store_path: Optional[Path] = None,
        legacy_store_path: Optional[Path] = None,
    ) -> None:
        self._store_path = store_path or (Path.home() / ".retrack" / "indexed_repos.json")
        self._legacy_store_path = legacy_store_path or (Path.home() / ".andes" / "indexed_repos.json")

    @property
    def store_path(self) -> Path:
        return self._store_path

    def load(self) -> dict:
        """Load the indexed repos store from disk with legacy fallback."""
        if self._store_path.exists():
            try:
                return json.loads(self._store_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load repo store from %s: %s", self._store_path, e)
                return {"repositories": []}

        if self._legacy_store_path.exists():
            try:
                return json.loads(self._legacy_store_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load legacy repo store from %s: %s", self._legacy_store_path, e)
                return {"repositories": []}

        return {"repositories": []}

    def save(self, data: dict) -> None:
        """Persist the indexed repos store to disk atomically."""
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            self._store_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save repo store to %s: %s", self._store_path, e)
            raise
