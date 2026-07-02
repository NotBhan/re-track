"""Source abstraction for importing repositories from various origins."""

from app.services.sources.github import GitHubSource
from app.services.sources.local import LocalSource

__all__ = ["GitHubSource", "LocalSource"]
