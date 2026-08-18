"""GitHub source — clones or pulls a repository from a GitHub URL."""

from pathlib import Path
from urllib.parse import urlparse

import subprocess


class GitHubSource:
    """Import a repository from GitHub by cloning or pulling."""

    source_type = "github"

    def __init__(self, url: str, workspace: Path) -> None:
        self.url = url
        self.workspace = workspace

    def validate(self) -> bool:
        """Check that the URL is a valid GitHub HTTPS URL."""
        parsed = urlparse(self.url)
        if parsed.scheme not in ("https", "http"):
            return False
        if not parsed.netloc:
            return False
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) < 2:
            return False
        return True

    def get_repo_name(self) -> str:
        """Extract the repository name from the URL (repo name without .git)."""
        parsed = urlparse(self.url)
        name = parsed.path.strip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name

    def get_metadata(self) -> dict[str, str | None]:
        """Return source metadata."""
        return {"source_type": self.source_type, "source_url": self.url}

    def import_to(self) -> Path:
        """Clone the repository, or pull if it already exists. Returns the repo path."""
        if not self.validate():
            raise ValueError(f"Invalid GitHub URL: {self.url}")

        repo_name = self.get_repo_name()
        repo_dir = self.workspace / repo_name.replace("/", "_")

        if repo_dir.exists():
            subprocess.run(
                ["git", "-C", str(repo_dir), "pull", "--ff-only"],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            self.workspace.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["git", "clone", self.url, str(repo_dir)],
                check=True,
                capture_output=True,
                text=True,
            )

        return repo_dir
