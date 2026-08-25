"""Abstract LLM provider port."""

from typing import Any, Optional, Protocol


class LLMProviderPort(Protocol):
    """Port for interacting with local or remote LLM inference providers."""

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """Execute chat completion against the active model provider."""
        ...

    async def check_health(self) -> Any:
        """Check provider reachability and active loaded model."""
        ...

    async def list_models(self) -> list[Any]:
        """List all available models reported by the provider endpoint."""
        ...

    async def discover_models(
        self,
        provider_type: str,
        base_url: str,
        api_key: str = "local",
        timeout: float = 3.0,
    ) -> Any:
        """Probe an endpoint and return discovered models without mutating state."""
        ...

