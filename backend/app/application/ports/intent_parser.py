"""Abstract intent parser port for RE:Track."""

from typing import Protocol

from app.application.domain.intent import ParsedIntentRecord


class IntentParserPort(Protocol):
    """Port for extracting structured intent, symbols, and hints from user prompts."""

    async def parse_intent(self, prompt: str) -> ParsedIntentRecord:
        """Parse natural language task prompt into structured intent extraction."""
        ...
