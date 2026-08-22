"""Abstract workspace authorization port for RE:Track.

Defines the boundary contract for validating that repository paths reside
within explicitly authorized repositories or configured workspace roots.
"""

from pathlib import Path
from typing import Optional, Protocol


class WorkspaceAuthorizationPort(Protocol):
    """Port for verifying repository and workspace filesystem authorization."""

    def is_path_authorized(self, path: Path | str) -> tuple[bool, Optional[str]]:
        """Determine if a requested path is authorized for analysis.

        Args:
            path: Local repository path (string or Path object).

        Returns:
            A tuple of (is_authorized: bool, rejection_reason: Optional[str]).
            If authorized, is_authorized is True and rejection_reason is None.
            If unauthorized, is_authorized is False and rejection_reason explains why.
        """
        ...

    def get_authorized_roots(self) -> list[Path]:
        """Return the list of configured authorized workspace roots."""
        ...

    def add_workspace_root(self, root_path: Path | str) -> None:
        """Dynamically add an authorized workspace root."""
        ...
