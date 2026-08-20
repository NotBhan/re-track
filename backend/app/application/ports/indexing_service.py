"""Abstract indexing service port."""

from pathlib import Path
from typing import Any, Optional, Protocol, Sequence


class IndexingServicePort(Protocol):
    """Port for discovering, filtering, and indexing repository files."""

    def discover_files(self, repo_path: Path) -> list[Path]:
        """Discover all candidate files within a repository directory."""
        ...

    def filter_files(self, files: Sequence[Path], repo_path: Path) -> list[Path]:
        """Apply ignore rules, size limits, and extension filters."""
        ...

    async def index_repository(
        self,
        repo_path: Path,
        dataset_name: Optional[str] = None,
        force_reindex: bool = False,
        progress_callback: Optional[Any] = None,
    ) -> Any:
        """Execute full indexing pipeline for the repository into persistent memory."""
        ...
