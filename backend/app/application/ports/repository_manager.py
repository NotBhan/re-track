"""Abstract repository manager port."""

from pathlib import Path
from typing import Any, Optional, Protocol


class RepositoryManagerPort(Protocol):
    """Port for managing registered repositories and local directory scanning."""

    def list_repositories(self) -> list[Any]:
        """List all managed repository configurations."""
        ...

    def import_repo(
        self,
        name: str,
        path: str,
        branch: Optional[str] = None,
    ) -> Any:
        """Register/import a local or remote repository."""
        ...

    def delete(self, repo_id: str) -> bool:
        """Delete a managed repository record by its ID."""
        ...

    def scan_local(self, path: Path) -> Any:
        """Scan a local directory to detect languages, frameworks, and file counts."""
        ...

    def get_progress(self, repo_id: str) -> Optional[dict[str, Any]]:
        """Get active indexing or scanning progress for a repository."""
        ...

    def get_by_id(self, repo_id: str) -> Optional[Any]:
        """Retrieve repository details by ID."""
        ...
