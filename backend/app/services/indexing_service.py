"""
Repository indexing pipeline for RE:Track (RefinedEngine Track).

Responsibilities only:
- Discover repository files with directory pruning
- Apply ignore rules (.gitignore, IGNORED_DIRS)
- Filter supported file types
- Batch ingestion
- Report indexing progress
- Call CogneeService.remember()
"""

import logging
from pathlib import Path
from typing import Callable, Optional

from app.models.errors import CogneeServiceError
from app.models.responses import IndexingProgress
from app.services.cognee_service import CogneeService
from app.services.manifest_service import ManifestService, IndexDelta

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
        ".rs",
        ".go",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".cs",
        ".html",
        ".css",
        ".sql",
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
        ".cache",
        ".next",
        ".nuxt",
        ".output",
        ".turbo",
        ".idea",
        ".vscode",
        "tmp",
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
        manifest_service: Optional[ManifestService] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        supported_extensions: Optional[frozenset[str]] = None,
        ignored_dirs: Optional[frozenset[str]] = None,
        ignored_patterns: Optional[frozenset[str]] = None,
    ) -> None:
        self._cognee = cognee_service
        self._manifest_service = manifest_service or ManifestService()
        self._batch_size = batch_size
        self._supported = supported_extensions or SUPPORTED_EXTENSIONS
        self._ignored_dirs = ignored_dirs or IGNORED_DIRS
        self._ignored_patterns = ignored_patterns or IGNORED_PATTERNS

    async def index_repository(
        self,
        repo_path: str | Path,
        dataset_name: str,
        force_reindex: bool = False,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> IndexingProgress:
        """Index a repository into Cognee memory with incremental delta support.

        Discovers files, computes delta against last manifest, filters by type,
        applies ignore rules, batches new/modified files, and calls CogneeService.remember().

        Args:
            repo_path: Root directory of the repository.
            dataset_name: Logical memory namespace for Cognee.
            force_reindex: If True, bypasses manifest diff and re-indexes all files.
            progress_callback: Optional callback receiving (stage_name, current_step, total_steps).

        Returns:
            IndexingProgress with counts and failure details.

        Raises:
            CogneeServiceError: If the repository path is invalid.
        """
        repo = Path(repo_path).resolve()
        if not repo.is_dir():
            raise CogneeServiceError(f"Repository path is not a directory: {repo}")

        if progress_callback:
            progress_callback("Scanning & discovering repository files...", 1, 5)

        all_files = self.discover_files(repo)
        filtered = self.filter_files(all_files, repo)

        if force_reindex:
            target_files = filtered
            existing_manifest = None
            deleted_rel_paths: list[str] = []
            logger.info("force_reindex=True | indexing all %d files", len(filtered))
        else:
            delta, existing_manifest = self._manifest_service.compute_delta(repo, filtered)
            if not delta.has_changes and existing_manifest is not None:
                logger.info(
                    "Repository unchanged (0 modifications, %d files cached) | skipping indexing",
                    len(filtered),
                )
                if progress_callback:
                    progress_callback("Indexing Completed", 5, 5)
                return IndexingProgress(
                    total_files=len(filtered),
                    processed_files=len(filtered),
                    skipped_files=len(filtered),
                    failed_files=0,
                    current_batch=1,
                    total_batches=1,
                )

            target_files = delta.added + delta.modified
            deleted_rel_paths = delta.deleted
            logger.info(
                "Incremental scan | added=%d | modified=%d | deleted=%d | unchanged=%d",
                len(delta.added),
                len(delta.modified),
                len(delta.deleted),
                len(delta.unchanged),
            )

        progress = IndexingProgress(
            total_files=len(filtered),
            total_batches=1,
            current_batch=1,
            skipped_files=len(filtered) - len(target_files),
        )

        if progress_callback:
            progress_callback("Extracting AST call graphs and symbols...", 2, 5)

        # Fast outline generation for cold start (LLM-free)
        from app.services.repository_summary import RepositorySummaryGenerator
        from app.services.renderer import MarkdownRenderer
        summary_gen = RepositorySummaryGenerator()
        repo_summary = summary_gen.generate(repo, filtered)

        if progress_callback:
            progress_callback("Generating repository architecture outline...", 3, 5)

        outline_markdown = MarkdownRenderer()._render_summary(repo_summary)

        if progress_callback:
            progress_callback("Ingesting knowledge into Cognee memory graph...", 4, 5)

        successfully_indexed: list[Path] = []
        # Ingest the clean folder structure & architecture outline into Cognee
        try:
            logger.info("Ingesting repository outline into memory | dataset=%s", dataset_name)
            await self._cognee.add(
                data=outline_markdown,
                dataset_name=dataset_name,
            )
            progress.processed_files = len(filtered)
            successfully_indexed = list(filtered)
            logger.info("Repository outline successfully indexed into memory")
        except CogneeServiceError as e:
            logger.error("Failed to index repository outline into memory: %s", e)
            progress.failed_files = len(filtered)

        # Update and save manifest
        self._manifest_service.update_manifest(
            repo_path=repo,
            dataset_name=dataset_name,
            indexed_files=successfully_indexed,
            deleted_rel_paths=deleted_rel_paths,
            existing_manifest=existing_manifest,
        )

        if progress_callback:
            progress_callback("Indexing Completed", 5, 5)

        logger.info("indexing complete | %s", progress.summary())
        return progress

    def discover_files(self, root: Path) -> list[Path]:
        """Recursively discover all files under root with aggressive directory pruning.

        Args:
            root: Directory to scan.

        Returns:
            List of file paths found.
        """
        files: list[Path] = []
        gitignore_patterns: set[str] = set()
        gi_file = root / ".gitignore"
        if gi_file.exists():
            try:
                for line in gi_file.read_text(errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pattern = line.rstrip("/").lstrip("/")
                        if pattern:
                            gitignore_patterns.add(pattern)
            except Exception:
                pass

        for cur_root, dirs, filenames in Path(root).walk():
            # In-place directory pruning: do not traverse into ignored directories
            dirs[:] = [
                d for d in dirs
                if d not in self._ignored_dirs
                and not d.startswith(".agents")
                and not d.startswith("__")
                and d not in gitignore_patterns
                and not any(pat == d or pat.rstrip("/") == d for pat in gitignore_patterns)
            ]

            for f in filenames:
                p = Path(cur_root) / f
                rel_p = str(p.relative_to(root)) if p.is_relative_to(root) else f
                if any(pat in rel_p or pat == f for pat in gitignore_patterns):
                    continue
                files.append(p)

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
