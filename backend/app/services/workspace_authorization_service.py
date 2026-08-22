"""Workspace and repository authorization service for RE:Track.

Implements WorkspaceAuthorizationPort to establish a defensible security boundary
preventing external MCP clients from accessing arbitrary host directories.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from app.application.ports.repository_metadata import RepositoryMetadataPort
from app.application.ports.workspace_authorization import WorkspaceAuthorizationPort

logger = logging.getLogger(__name__)

# Defense-in-depth: sensitive host directories that are always rejected
FORBIDDEN_SYSTEM_PATHS: frozenset[Path] = frozenset(
    {
        Path("/etc"),
        Path("/proc"),
        Path("/sys"),
        Path("/dev"),
        Path("/run"),
        Path("/boot"),
        Path("/root"),
        Path("/var"),
        Path.home() / ".ssh",
        Path.home() / ".gnupg",
    }
)


class WorkspaceAuthorizationService(WorkspaceAuthorizationPort):
    """Concrete service verifying repository and workspace authorization."""

    def __init__(
        self,
        metadata_store: Optional[RepositoryMetadataPort] = None,
        workspace_roots: Optional[list[Path]] = None,
    ) -> None:
        self._metadata_store = metadata_store
        self._workspace_roots: list[Path] = []

        if workspace_roots is not None:
            for r in workspace_roots:
                self.add_workspace_root(r)
        else:
            # Read from environment variable RETRACK_WORKSPACE_ROOTS
            env_roots = os.environ.get("RETRACK_WORKSPACE_ROOTS", "").strip()
            if env_roots:
                delim = ";" if os.name == "nt" else ":"
                for r_str in env_roots.split(delim):
                    if r_str.strip():
                        self.add_workspace_root(r_str.strip())

    def get_authorized_roots(self) -> list[Path]:
        """Return the list of configured authorized workspace roots."""
        return list(self._workspace_roots)

    def add_workspace_root(self, root_path: Path | str) -> None:
        """Dynamically add an authorized workspace root."""
        try:
            resolved = Path(root_path).resolve()
            if resolved not in self._workspace_roots:
                self._workspace_roots.append(resolved)
        except Exception as e:
            logger.warning("Failed to add workspace root %s: %s", root_path, e)

    def is_path_authorized(self, path: Path | str) -> tuple[bool, Optional[str]]:
        """Determine if a requested path is authorized for analysis.

        Enforces:
        1. Non-empty string and valid path syntax.
        2. Canonicalization via Path.resolve().
        3. Existence and directory validation.
        4. Defense-in-depth block on filesystem roots and sensitive host directories.
        5. Primary Authorization:
           - Matches an explicitly registered repository in metadata_store, OR
           - Resides within an explicitly configured workspace root.
        """
        if path is None:
            return False, "Repository path must not be null"

        p_str = str(path).strip()
        if not p_str:
            return False, "Repository path must not be empty"

        try:
            resolved = Path(p_str).resolve()
        except Exception as e:
            return False, f"Invalid path syntax: {e}"

        if not resolved.exists():
            return False, f"Repository path does not exist: {p_str}"
        if not resolved.is_dir():
            return False, f"Repository path is not a directory: {p_str}"

        # Defense-in-depth: Root directory rejection
        if str(resolved) in ("/", "\\", "C:\\", "C:/"):
            return False, "Scanning the filesystem root directory is prohibited"

        # Defense-in-depth: Sensitive system directories
        for forbidden in FORBIDDEN_SYSTEM_PATHS:
            try:
                if resolved == forbidden or (forbidden.exists() and resolved.is_relative_to(forbidden)):
                    return False, f"Access to system directory {p_str} is prohibited"
            except Exception:
                if resolved == forbidden:
                    return False, f"Access to system directory {p_str} is prohibited"

        # Primary Authorization 1: Check configured workspace roots
        for root in self._workspace_roots:
            try:
                if resolved == root or resolved.is_relative_to(root):
                    return True, None
            except Exception:
                if resolved == root:
                    return True, None

        # Primary Authorization 2: Check registered repositories in metadata store
        if self._metadata_store is not None:
            try:
                for repo in self._metadata_store.load_all():
                    if not repo.path:
                        continue
                    try:
                        registered_path = Path(repo.path).resolve()
                        if resolved == registered_path:
                            return True, None
                    except Exception:
                        if str(resolved) == repo.path:
                            return True, None
            except Exception as e:
                logger.warning("Error checking metadata store for authorization: %s", e)

        return (
            False,
            f"Access denied: Path '{resolved}' is not an authorized repository or within a configured workspace root. "
            "Please register the repository with RE:Track or configure RETRACK_WORKSPACE_ROOTS.",
        )
