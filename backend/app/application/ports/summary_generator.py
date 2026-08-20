"""Abstract repository summary generator port."""

from pathlib import Path
from typing import Any, Protocol, Sequence


class SummaryGeneratorPort(Protocol):
    """Port for generating repository-level architectural summaries and components."""

    async def generate(
        self,
        repo_path: Path,
        files: Sequence[Path],
    ) -> Any:
        """Generate architectural summary and component map for the repository."""
        ...
