"""Abstract filesystem port for application-level file operations."""

from pathlib import Path
from typing import Protocol, Union


class FileSystemPort(Protocol):
    """Port for filesystem reading and inspection operations."""

    def read_text(self, path: Union[Path, str], errors: str = "replace") -> str:
        """Read full text content from the specified file path."""
        ...

    def get_file_size(self, path: Union[Path, str]) -> int:
        """Get the file size in bytes."""
        ...

    def exists(self, path: Union[Path, str]) -> bool:
        """Check if the given path exists."""
        ...

    def is_dir(self, path: Union[Path, str]) -> bool:
        """Check if the given path is a directory."""
        ...

    def get_mtime(self, path: Union[Path, str]) -> float:
        """Get modification timestamp of the given path."""
        ...
