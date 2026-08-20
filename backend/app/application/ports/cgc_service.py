"""Abstract CodeGraphContext (CGC) structural context port."""

from pathlib import Path
from typing import Any, Optional, Protocol, Sequence


class CGCServicePort(Protocol):
    """Port for querying AST structural call graphs, caller/callee trees, and hierarchies."""

    async def query_structural_context(
        self,
        repo_path: Path,
        target_symbols: Sequence[str],
    ) -> Optional[Any]:
        """Query CGC graph database for structural relationships of target symbols."""
        ...
