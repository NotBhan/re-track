"""Local source — imports a repository from a local filesystem path."""

from pathlib import Path


class LocalSource:
    """Import a repository from a local directory."""

    source_type = "local"

    def __init__(self, path: str) -> None:
        self.path = path

    def validate(self) -> bool:
        """Check that the path exists and is a directory."""
        p = Path(self.path)
        return p.exists() and p.is_dir()

    def get_metadata(self) -> dict[str, str | None]:
        """Return source metadata."""
        return {"source_type": self.source_type, "source_url": None}

    def import_to(self) -> Path:
        """Validate the path exists and is a directory, then return it."""
        p = Path(self.path)
        if not p.exists():
            raise FileNotFoundError(f"Path does not exist: {self.path}")
        if not p.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.path}")
        return p
