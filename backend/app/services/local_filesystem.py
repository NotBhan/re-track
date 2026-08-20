"""Local filesystem adapter implementing FileSystemPort."""

from pathlib import Path
from typing import Union


class LocalFileSystemAdapter:
    """Standard-library filesystem adapter implementing FileSystemPort."""

    def read_text(self, path: Union[Path, str], errors: str = "replace") -> str:
        """Read full text content from file using utf-8 encoding with fallback."""
        return Path(path).read_text(encoding="utf-8", errors=errors)

    def get_file_size(self, path: Union[Path, str]) -> int:
        """Get file size in bytes via stat."""
        return Path(path).stat().st_size

    def exists(self, path: Union[Path, str]) -> bool:
        """Check if path exists on disk."""
        return Path(path).exists()

    def is_dir(self, path: Union[Path, str]) -> bool:
        """Check if path is a directory."""
        return Path(path).is_dir()

    def get_mtime(self, path: Union[Path, str]) -> float:
        """Get file modification time."""
        return Path(path).stat().st_mtime
