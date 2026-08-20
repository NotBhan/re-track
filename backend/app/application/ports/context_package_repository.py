"""Abstract context package persistence repository port."""

from typing import Any, Optional, Protocol


class ContextPackageRepositoryPort(Protocol):
    """Port for persisting and retrieving synthesized context packages."""

    async def save(self, package: Any) -> Any:
        """Save a context package to persistent storage."""
        ...

    async def get(self, package_id: str) -> Optional[Any]:
        """Retrieve a context package by unique ID."""
        ...

    async def list_all(self) -> list[Any]:
        """List all stored context packages."""
        ...

    async def delete(self, package_id: str) -> bool:
        """Delete a context package by ID."""
        ...

    async def append(
        self,
        package_id: str,
        additional_task: str,
        additional_markdown: str,
        additional_objective: str = "",
    ) -> Optional[Any]:
        """Append an iterative follow-up query to an existing context package."""
        ...
