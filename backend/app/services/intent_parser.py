"""
Intent Parser and Prompt Analyzer for RE:Track.

Uses structured prompts and Pydantic validation to extract targets,
symbols, intent categories, and specificity scores from developer requests
with strict anti-hallucination guardrails.
"""

import json
import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)


class ParsedIntent(BaseModel):
    """Structured extraction of developer task intent."""

    task_summary: str = Field(description="One line summary of the objective")
    category: str = Field(
        default="general",
        description="Intent category: bug_fix, feature_addition, refactoring, architecture_query, explanation",
    )
    extracted_symbols: list[str] = Field(
        default_factory=list,
        description="Code symbols explicitly mentioned or directly implied (functions, classes, variables)",
    )
    relevant_file_hints: list[str] = Field(
        default_factory=list,
        description="File path substrings or module names mentioned in the prompt",
    )
    is_vague: bool = Field(
        default=False,
        description="True if prompt is broad/abstract and requires adaptive compression",
    )


class IntentParserService:
    """Parses developer prompts using local LLM with rule-based fallbacks."""

    def __init__(self, llm_service: Optional[LLMProviderService] = None) -> None:
        self._llm = llm_service

    @staticmethod
    def rule_based_fallback(prompt: str) -> ParsedIntent:
        """Fast, LLM-free rule-based intent parser to guarantee zero-hallucination fallback."""
        lowered = prompt.lower()

        category = "general"
        if any(w in lowered for w in ["fix", "bug", "error", "issue", "fail", "crash"]):
            category = "bug_fix"
        elif any(w in lowered for w in ["add", "create", "implement", "build", "new"]):
            category = "feature_addition"
        elif any(w in lowered for w in ["refactor", "clean", "structure", "rename", "move"]):
            category = "refactoring"
        elif any(w in lowered for w in ["how", "why", "what", "where", "explain"]):
            category = "explanation"

        # Regex for potential symbol / function / path patterns (words with dots, underscores, camelCase)
        symbol_candidates = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+\b|\b[a-z]+[A-Z][a-zA-Z0-9]*\b|\b[a-zA-Z_][a-zA-Z0-9_]*_[a-zA-Z0-9_]+\b", prompt)
        
        # File hints (words ending in .py, .ts, .tsx, .json, .md, etc.)
        file_hints = re.findall(r"\b[\w\-\/\\]+\.(?:py|ts|tsx|js|jsx|json|md|yaml|toml|rs)\b", prompt)

        # Check if prompt is very short or generic (vague)
        is_vague = len(prompt.split()) < 5 or any(w in lowered for w in ["everything", "all files", "overview", "project status"])

        return ParsedIntent(
            task_summary=prompt.strip()[:100],
            category=category,
            extracted_symbols=list(set(symbol_candidates)),
            relevant_file_hints=list(set(file_hints)),
            is_vague=is_vague,
        )

    async def parse_intent(self, prompt: str) -> ParsedIntent:
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
                return ParsedIntent(
                    task_summary=data.get("task_summary", fallback.task_summary),
                    category=data.get("category", fallback.category),
                    extracted_symbols=list(set(data.get("extracted_symbols", []) + fallback.extracted_symbols)),
                    relevant_file_hints=list(set(data.get("relevant_file_hints", []) + fallback.relevant_file_hints)),
                    is_vague=data.get("is_vague", fallback.is_vague),
                )
        except Exception as e:
            logger.debug("LLM intent parsing failed, using rule-based fallback: %s", e)

        return fallback
