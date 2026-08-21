"""Intent Parser and Prompt Analyzer for RE:Track.

Uses structured prompts and Pydantic validation to extract targets,
symbols, intent categories, and specificity scores from developer requests
with strict anti-hallucination guardrails.
"""

import json
import logging
import re
from typing import Optional

from app.application.domain.intent import ParsedIntentRecord, parse_intent_heuristics
from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
ParsedIntent = ParsedIntentRecord


class IntentParserService:
    """Parses developer prompts using local LLM with rule-based fallbacks."""

    def __init__(self, llm_service: Optional[LLMProviderService] = None) -> None:
        self._llm = llm_service

    @staticmethod
    def rule_based_fallback(prompt: str) -> ParsedIntentRecord:
        """Fast, LLM-free rule-based intent parser ensuring zero-hallucination fallback."""
        return parse_intent_heuristics(prompt)

    async def parse_intent(self, prompt: str) -> ParsedIntentRecord:
        """Extract intent, symbols, and specificity score from task prompt."""
        fallback = self.rule_based_fallback(prompt)
        if not self._llm:
            return fallback

        system_prompt = (
            "You are a strict, hallucination-free code query analyzer. "
            "Analyze the developer's request and respond ONLY in valid JSON format matching this schema:\n"
            "{\n"
            '  "task_summary": "One line summary of the goal",\n'
            '  "category": "bug_fix" | "feature_addition" | "refactoring" | "architecture_query" | "explanation",\n'
            '  "extracted_symbols": ["list", "of", "exact", "code_symbols_mentioned"],\n'
            '  "relevant_file_hints": ["mentioned_file_names.py"],\n'
            '  "is_vague": true | false\n'
            "}\n"
            "Do NOT invent code identifiers not present or referenced in the user text."
        )

        try:
            raw = await self._llm.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=250,
            )
            # Find JSON block
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return ParsedIntentRecord(
                    task_summary=str(data.get("task_summary", fallback.task_summary)),
                    category=str(data.get("category", fallback.category)),
                    extracted_symbols=list(dict.fromkeys(data.get("extracted_symbols", []) + fallback.extracted_symbols)),
                    relevant_file_hints=list(dict.fromkeys(data.get("relevant_file_hints", []) + fallback.relevant_file_hints)),
                    is_vague=bool(data.get("is_vague", fallback.is_vague)),
                )
        except Exception as e:
            logger.debug("LLM intent parsing failed, using rule-based fallback: %s", e)

        return fallback
