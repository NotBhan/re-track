"""
Repository indexing pipeline for RE:Track (RefinedEngine Track).

Responsibilities only:
- Discover repository files
- Apply ignore rules
- Filter supported file types
- Batch ingestion
- Report indexing progress
- Call CogneeService.remember()

No Context Package generation. No workspace management.
No filesystem watching. No incremental indexing.
"""

import logging
from pathlib import Path
from typing import Optional

from app.models.errors import CogneeServiceError
from app.models.responses import IndexingProgress
from app.services.cognee_service import CogneeService

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
    }
)

IGNORED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "dist",
        "build",
        "coverage",
        ".venv",
        "venv",
        "__pycache__",
        ".cognee_data",
        ".cognee_system",
        "target",
    }
)

IGNORED_PATTERNS: frozenset[str] = frozenset(
    {
        "*.lock",
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.svg",
        "*.ico",
        "*.pdf",
        "*.zip",
        "*.tar",
        "*.gz",
        "*.mp4",
        "*.mp3",
        "*.wav",
    }
)

DEFAULT_BATCH_SIZE = 10


class IndexingService:
    """Repository indexing pipeline.

    Discovers files in a repository, filters by supported types,
    applies ignore rules, and batches ingestion into Cognee via
    CogneeService.
    """

    def __init__(
        self,
        cognee_service: CogneeService,
        batch_size: int = DEFAULT_BATCH_SIZE,
        supported_extensions: Optional[frozenset[str]] = None,
        ignored_dirs: Optional[frozenset[str]] = None,
        ignored_patterns: Optional[frozenset[str]] = None,
    ) -> None:
        self._cognee = cognee_service
        self._batch_size = batch_size
        self._supported = supported_extensions or SUPPORTED_EXTENSIONS
        self._ignored_dirs = ignored_dirs or IGNORED_DIRS
        self._ignored_patterns = ignored_patterns or IGNORED_PATTERNS

    async def index_repository(
        self,
        repo_path: str | Path,
        dataset_name: str,
    ) -> IndexingProgress:
        """Index a repository into Cognee memory.

        Discovers files, filters by type, applies ignore rules,
        batches them, and calls CogneeService.remember() for each batch.

        Args:
            repo_path: Root directory of the repository.
            dataset_name: Logical memory namespace for Cognee.

        Returns:
            IndexingProgress with counts and failure details.

        Raises:
            CogneeServiceError: If the repository path is invalid.
        """
        repo = Path(repo_path).resolve()
        if not repo.is_dir():
            raise CogneeServiceError(f"Repository path is not a directory: {repo}")

        all_files = self.discover_files(repo)
        filtered = self.filter_files(all_files, repo)
        batches = self.batch_files(filtered)

        progress = IndexingProgress(
            total_files=len(filtered),
            total_batches=len(batches),
        )

        logger.info(
            "index_repository | path=%s | files=%d | batches=%d",
            repo,
            len(filtered),
            len(batches),
        )

        for batch_idx, batch in enumerate(batches, 1):
            progress.current_batch = batch_idx
            try:
                file_paths = [str(f) for f in batch]
                await self._cognee.remember(
                    data=file_paths,
                    dataset_name=dataset_name,
                )
                progress.processed_files += len(batch)
                logger.info(
                    "batch %d/%d complete | files=%d",
                    batch_idx,
                    len(batches),
                    len(batch),
                )
            except CogneeServiceError as e:
                progress.failed_files += len(batch)
                progress.failed_paths.extend(str(f) for f in batch)
                logger.error(
                    "batch %d/%d failed | files=%d | error=%s",
                    batch_idx,
                    len(batches),
                    len(batch),
                    e,
                )

        logger.info("indexing complete | %s", progress.summary())
        return progress

    def discover_files(self, root: Path) -> list[Path]:
        """Recursively discover all files under root.

        Args:
            root: Directory to scan.

        Returns:
            List of file paths found.
        """
        files: list[Path] = []
        for path in root.rglob("*"):
            if path.is_file():
                files.append(path)
        return files

    def filter_files(
        self,
        files: list[Path],
        root: Optional[Path] = None,
    ) -> list[Path]:
        """Filter files by supported extensions and ignore rules.

        Args:
            files: List of file paths to filter.
            root: Repository root for computing relative paths.

        Returns:
            Filtered list of supported, non-ignored files.
        """
        result: list[Path] = []
        for f in files:
            if not self._is_supported(f):
                continue
            if root and self._is_ignored(f, root):
                continue
            result.append(f)
        return result

    def batch_files(self, files: list[Path]) -> list[list[Path]]:
        """Split files into batches for ingestion.

        Args:
            files: List of file paths.

        Returns:
            List of batches, each a list of file paths.
        """
        if not files:
            return []
        return [
            files[i : i + self._batch_size]
            for i in range(0, len(files), self._batch_size)
        ]

    def _is_supported(self, path: Path) -> bool:
        """Return True if the file extension is supported."""
        return path.suffix.lower() in self._supported

    def _is_ignored(self, path: Path, root: Path) -> bool:
        """Return True if the file should be ignored.

        Checks each component of the relative path against ignore dirs
        and the filename against ignored patterns.
        """
        try:
            rel = path.relative_to(root)
        except ValueError:
            return False

        for part in rel.parts:
            if part in self._ignored_dirs:
                return True

        name = path.name
        for pattern in self._ignored_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True

        return False
