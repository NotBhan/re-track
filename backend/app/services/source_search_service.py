"""Source file searching and focused code snippet extraction service for RE:Track."""

import logging
from pathlib import Path
from typing import Optional, Sequence

from app.application.ports.filesystem import FileSystemPort
from app.application.ports.source_search import SourceSearchPort
from app.services.local_filesystem import LocalFileSystemAdapter

logger = logging.getLogger(__name__)

STOP_WORDS = frozenset({
    "where", "what", "find", "how", "with", "from", "this", "that",
    "the", "and", "for", "are", "can", "you", "does", "show", "tell",
})


class SourceSearchService(SourceSearchPort):
    """Encapsulates filesystem source scanning, term matching, and snippet extraction."""

    def __init__(self, filesystem: Optional[FileSystemPort] = None) -> None:
        self._fs = filesystem or LocalFileSystemAdapter()

    def build_search_terms(
        self,
        task_prompt: str,
        extracted_symbols: Sequence[str] = (),
        relevant_file_hints: Sequence[str] = (),
    ) -> list[str]:
        """Generate deduplicated search terms from prompt, symbols, and hints."""
        prompt_words = [
            w for w in task_prompt.split()
            if len(w) > 3 and w.lower() not in STOP_WORDS
        ]
        return list(dict.fromkeys(prompt_words + list(extracted_symbols) + list(relevant_file_hints)))

    def extract_relevant_snippets(
        self,
        repo_path: Path,
        indexed_files: Sequence[Path],
        search_terms: Sequence[str],
        max_files: int = 8,
        max_snippets: int = 5,
        max_file_size: int = 256_000,
    ) -> tuple[list[str], list[str]]:
        """Search repository files and extract focused code snippets around matches.

        Args:
            repo_path: Root directory of repository.
            indexed_files: Sequence of eligible file paths.
            search_terms: Terms to search for in filenames and contents.
            max_files: Maximum matching files to consider.
            max_snippets: Maximum formatted Markdown snippets to produce.
            max_file_size: Maximum file size in bytes to inspect for content search.

        Returns:
            tuple of (relevant_snippets_markdown_list, matched_file_relative_paths)
        """
        matched_files: list[tuple[str, Path]] = []
        term_lowers = [t.lower() for t in search_terms[:8]]

        if term_lowers:
            for fpath in indexed_files:
                try:
                    rel = str(fpath.relative_to(repo_path))
                    rel_lower = rel.lower()
                    # 1. Match filename first (zero file I/O)
                    if any(t in rel_lower for t in term_lowers):
                        if (rel, fpath) not in matched_files:
                            matched_files.append((rel, fpath))
                    # 2. Content scan for smaller files
                    elif self._fs.get_file_size(fpath) < max_file_size:
                        content = self._fs.read_text(fpath, errors="replace").lower()
                        if any(t in content for t in term_lowers):
                            if (rel, fpath) not in matched_files:
                                matched_files.append((rel, fpath))

                    if len(matched_files) >= max_files:
                        break
                except Exception as e:
                    logger.debug("SourceSearch skipped file %s: %s", fpath, e)

        relevant_snippets: list[str] = []
        for rel_path, full_path in matched_files[:max_snippets]:
            try:
                text = self._fs.read_text(full_path, errors="replace")
                lines = text.splitlines()
                matching_indices = [
                    i for i, line in enumerate(lines)
                    if any(t.lower() in line.lower() for t in search_terms)
                ]
                if matching_indices:
                    first_idx = max(0, matching_indices[0] - 4)
                    last_idx = min(len(lines), matching_indices[0] + 25)
                    snippet = "\n".join(lines[first_idx:last_idx])
                    relevant_snippets.append(
                        f"### `{rel_path}` (Lines {first_idx+1}-{last_idx})\n```\n{snippet}\n```"
                    )
            except Exception as e:
                logger.debug("SourceSearch snippet error in %s: %s", rel_path, e)

        matched_rel_paths = [rel for rel, _ in matched_files]
        return relevant_snippets, matched_rel_paths
