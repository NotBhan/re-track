"""Abstract intent parser port."""

from typing import Any, Protocol


class IntentParserPort(Protocol):
    """Port for extracting structured intent, symbols, and hints from user prompts."""

    async def parse_intent(self, prompt: str) -> Any:
        """Parse natural language task prompt into structured intent extraction."""
        ...

    @staticmethod
    def rule_based_fallback(prompt: str) -> Any:
        """Fast, rule-based extraction fallback without LLM inference."""
        ...
