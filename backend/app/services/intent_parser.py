"""Intent Parser and Prompt Analyzer for RE:Track.

Uses structured prompts and Pydantic validation to extract targets,
symbols, intent categories, and specificity scores from developer requests
with strict anti-hallucination guardrails.
"""

import json
import logging
import re
import time
from typing import Optional

from app.application.domain.intent import ParsedIntentRecord, parse_intent_heuristics
from app.application.ports.llm_provider import LLMProviderPort
from app.core.logging import log_event

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
ParsedIntent = ParsedIntentRecord


class IntentParserService:
    """Parses developer prompts using local LLM with rule-based fallbacks."""

    def __init__(self, llm_service: Optional[LLMProviderPort] = None) -> None:
        self._llm = llm_service

    @staticmethod
    def rule_based_fallback(prompt: str) -> ParsedIntentRecord:
        """Fast, LLM-free rule-based intent parser ensuring zero-hallucination fallback."""
        return parse_intent_heuristics(prompt)

    async def parse_intent(self, prompt: str) -> ParsedIntentRecord:
        """Extract intent, symbols, and specificity score from task prompt."""
        fallback = self.rule_based_fallback(prompt)
        if not self._llm:
            fallback.model_invoked = False
            fallback.provider_identity = None
            fallback.model_name = None
            fallback.inference_status = "not_configured"
            fallback.fallback_used = True
            fallback.fallback_reason = "No LLM provider configured"
            fallback.inference_time_ms = 0
            return fallback

        p_type = getattr(self._llm, "provider_type", None)
        p_name = p_type.value if hasattr(p_type, "value") else str(p_type or "llm_provider")
        model_name = getattr(self._llm, "default_model", None)

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

        t_start = time.perf_counter()
        log_event(
            logger,
            logging.INFO,
            "context_model_invocation_started",
            component="intent_parser",
            operation="parse_intent",
            provider_identity=p_name,
            model_name=model_name,
        )

        try:
            raw = await self._llm.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model_name,
                temperature=0.0,
                max_tokens=250,
            )
            elapsed_ms = int((time.perf_counter() - t_start) * 1000)

            # Find JSON block
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                log_event(
                    logger,
                    logging.INFO,
                    "context_model_invocation_completed",
                    component="intent_parser",
                    operation="parse_intent",
                    duration_ms=elapsed_ms,
                    provider_identity=p_name,
                    model_name=model_name,
                )
                return ParsedIntentRecord(
                    task_summary=str(data.get("task_summary", fallback.task_summary)),
                    category=str(data.get("category", fallback.category)),
                    extracted_symbols=list(dict.fromkeys(data.get("extracted_symbols", []) + fallback.extracted_symbols)),
                    relevant_file_hints=list(dict.fromkeys(data.get("relevant_file_hints", []) + fallback.relevant_file_hints)),
                    is_vague=bool(data.get("is_vague", fallback.is_vague)),
                    model_invoked=True,
                    provider_identity=p_name,
                    model_name=model_name,
                    inference_status="completed",
                    fallback_used=False,
                    fallback_reason=None,
                    inference_time_ms=elapsed_ms,
                )
            else:
                log_event(
                    logger,
                    logging.WARNING,
                    "context_model_invocation_failed",
                    component="intent_parser",
                    operation="parse_intent",
                    duration_ms=elapsed_ms,
                    provider_identity=p_name,
                    model_name=model_name,
                    error_class="MalformedJSON",
                )
                log_event(
                    logger,
                    logging.INFO,
                    "context_deterministic_fallback",
                    component="intent_parser",
                    operation="parse_intent",
                    fallback_reason="Model response was not valid JSON schema",
                )
                fallback.model_invoked = False
                fallback.provider_identity = p_name
                fallback.model_name = model_name
                fallback.inference_status = "failed"
                fallback.fallback_used = True
                fallback.fallback_reason = "Model response was not valid JSON schema"
                fallback.inference_time_ms = elapsed_ms
                return fallback
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - t_start) * 1000)
            logger.warning("LLM intent parsing failed, using rule-based fallback: %s", e)
            log_event(
                logger,
                logging.WARNING,
                "context_model_invocation_failed",
                component="intent_parser",
                operation="parse_intent",
                duration_ms=elapsed_ms,
                provider_identity=p_name,
                model_name=model_name,
                error_class=type(e).__name__,
            )
            log_event(
                logger,
                logging.INFO,
                "context_deterministic_fallback",
                component="intent_parser",
                operation="parse_intent",
                fallback_reason=f"{type(e).__name__}: {e}",
            )
            fallback.model_invoked = False
            fallback.provider_identity = p_name
            fallback.model_name = model_name
            fallback.inference_status = "failed"
            fallback.fallback_used = True
            fallback.fallback_reason = f"{type(e).__name__}: {e}"
            fallback.inference_time_ms = elapsed_ms
            return fallback

