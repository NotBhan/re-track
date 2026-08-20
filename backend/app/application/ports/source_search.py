"""Abstract source search port for file snippet extraction."""

from pathlib import Path
from typing import Protocol, Sequence


class SourceSearchPort(Protocol):
    """Port for search term extraction and relevant source snippet retrieval."""

    def build_search_terms(
        self,
        task_prompt: str,
        extracted_symbols: Sequence[str] = (),
        relevant_file_hints: Sequence[str] = (),
    ) -> list[str]:
        """Generate deduplicated ranked search terms from prompt, symbols, and hints."""
        ...

    def extract_relevant_snippets(
        self,
        repo_path: Path,
        indexed_files: Sequence[Path],
        search_terms: Sequence[str],
        max_files: int = 8,
        max_snippets: int = 5,
        max_file_size: int = 256_000,
    ) -> tuple[list[str], list[str]]:
        """Scan repository files for search terms and return matching relative paths and formatted snippets."""
        ...
