"""Repository metadata persistence store adapter for RE:Track.

Encapsulates reading and writing indexed repository metadata from JSON storage on disk,
abstracting filesystem details away from application use cases and implementing RepositoryMetadataPort.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.application.domain.repository import IndexedRepositoryRecord
from app.application.ports.repository_metadata import RepositoryMetadataPort

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
RepositoryMetadataStore = RepositoryMetadataPort


class JsonRepositoryMetadataStore:
    """Concrete filesystem JSON implementation of RepositoryMetadataPort."""

    def __init__(
        self,
        store_path: Optional[Path] = None,
        legacy_store_path: Optional[Path] = None,
    ) -> None:
        if store_path is None:
            self._store_path = Path.home() / ".retrack" / "indexed_repos.json"
            self._legacy_store_path = legacy_store_path or (Path.home() / ".andes" / "indexed_repos.json")
        else:
            self._store_path = store_path
            self._legacy_store_path = legacy_store_path

    @property
    def store_path(self) -> Path:
        return self._store_path

    def load(self) -> dict[str, Any]:
        """Load the raw indexed repos store dict from disk with legacy fallback."""
        if self._store_path.exists():
            try:
                return json.loads(self._store_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load repo store from %s: %s", self._store_path, e)
                return {"repositories": []}

        if self._legacy_store_path is not None and self._legacy_store_path.exists():
            try:
                return json.loads(self._legacy_store_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load legacy repo store from %s: %s", self._legacy_store_path, e)
                return {"repositories": []}

        return {"repositories": []}

    def save(self, data: dict[str, Any]) -> None:
        """Persist the raw indexed repos store dict to disk atomically."""
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._store_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                import os
                os.fsync(f.fileno())
            tmp_path.replace(self._store_path)
        except Exception as e:
            logger.error("Failed to save repo store to %s: %s", self._store_path, e)
            raise

    def load_all(self) -> list[IndexedRepositoryRecord]:
        """Load all indexed repository records as typed domain entities."""
        raw = self.load()
        raw_repos = raw.get("repositories", [])
        return [IndexedRepositoryRecord.from_dict(r) for r in raw_repos if isinstance(r, dict)]

    def get_by_path(self, path: str) -> Optional[IndexedRepositoryRecord]:
        """Find an indexed repository record matching the given path."""
        norm_target = str(Path(path).resolve())
        for r in self.load_all():
            try:
                if str(Path(r.path).resolve()) == norm_target or r.path == path:
                    return r
            except Exception:
                if r.path == path:
                    return r
        return None

    def get_by_id(self, repo_id: str) -> Optional[IndexedRepositoryRecord]:
        """Find an indexed repository record matching the given ID."""
        for r in self.load_all():
            if r.id == repo_id:
                return r
        return None

    def save_all(self, records: list[IndexedRepositoryRecord]) -> None:
        """Persist a full list of typed domain records."""
        data = {"repositories": [r.to_dict() for r in records]}
        self.save(data)

    def upsert(self, record: IndexedRepositoryRecord) -> None:
        """Add or update an indexed repository record in persistent store."""
        records = self.load_all()
        updated = False
        for i, existing in enumerate(records):
            if existing.id == record.id or existing.path == record.path:
                records[i] = record
                updated = True
                break
        if not updated:
            records.append(record)
        self.save_all(records)

    def delete(self, identifier: str) -> bool:
        """Delete an indexed repository record by ID or path."""
        records = self.load_all()
        filtered = [r for r in records if r.id != identifier and r.path != identifier]
        if len(filtered) < len(records):
            self.save_all(filtered)
            return True
        return False
