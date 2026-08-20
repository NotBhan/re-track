"""Abstract repository metadata persistence port."""

from typing import Any, Optional, Protocol

from app.application.domain.repository import IndexedRepositoryRecord


class RepositoryMetadataPort(Protocol):
    """Port for persistent storage of indexed repository records."""

    def load_all(self) -> list[IndexedRepositoryRecord]:
        """Load all indexed repository records from persistent store."""
        ...

    def get_by_path(self, path: str) -> Optional[IndexedRepositoryRecord]:
        """Find an indexed repository record matching the given local path."""
        ...

    def get_by_id(self, repo_id: str) -> Optional[IndexedRepositoryRecord]:
        """Find an indexed repository record matching the given unique repository ID."""
        ...

    def save_all(self, records: list[IndexedRepositoryRecord]) -> None:
        """Save full list of indexed repository records to persistent store."""
        ...

    def upsert(self, record: IndexedRepositoryRecord) -> None:
        """Add or update an indexed repository record by path or ID."""
        ...

    def delete(self, identifier: str) -> bool:
        """Delete an indexed repository record by ID or path. Returns True if deleted."""
        ...

    # Backward compatibility for raw dictionary access
    def load(self) -> dict[str, Any]:
        """Load raw dictionary persistence structure for backward compatibility."""
        ...

    def save(self, data: dict[str, Any]) -> None:
        """Save raw dictionary persistence structure for backward compatibility."""
        ...
