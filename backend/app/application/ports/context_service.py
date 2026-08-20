"""Abstract context synthesis service port."""

from typing import Any, Optional, Protocol


class ContextServicePort(Protocol):
    """Port for synthesizing context packages from task requirements and memory datasets."""

    async def generate_context_package(
        self,
        task: str,
        datasets: list[str],
        top_k: int = 15,
        repository_summary: Any = None,
        target_tokens: Optional[int] = None,
    ) -> Any:
        """Generate a complete ContextPackage using recall from specified datasets."""
        ...
