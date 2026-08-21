"""Domain entity and pure heuristic extraction for prompt intent in RE:Track."""

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass
class ParsedIntentRecord:
    """Domain model representing structured developer task intent."""

    task_summary: str
    category: str = "general"
    extracted_symbols: list[str] = field(default_factory=list)
    relevant_file_hints: list[str] = field(default_factory=list)
    is_vague: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize intent record to dictionary format."""
        return {
            "task_summary": self.task_summary,
            "category": self.category,
            "extracted_symbols": self.extracted_symbols,
            "relevant_file_hints": self.relevant_file_hints,
            "is_vague": self.is_vague,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParsedIntentRecord":
        """Construct intent record from dictionary format."""
        return cls(
            task_summary=str(data.get("task_summary", "")),
            category=str(data.get("category", "general")),
            extracted_symbols=list(data.get("extracted_symbols", [])),
            relevant_file_hints=list(data.get("relevant_file_hints", [])),
            is_vague=bool(data.get("is_vague", False)),
        )


def parse_intent_heuristics(prompt: str) -> ParsedIntentRecord:
    """Pure, deterministic, LLM-free rule-based intent parser.

    Guarantees zero-hallucination intent extraction without external I/O or framework dependencies.
    """
    if not prompt:
        return ParsedIntentRecord(
            task_summary="",
            category="general",
            extracted_symbols=[],
            relevant_file_hints=[],
            is_vague=True,
        )

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
    symbol_candidates = re.findall(
        r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+\b|\b[a-z]+[A-Z][a-zA-Z0-9]*\b|\b[a-zA-Z_][a-zA-Z0-9_]*_[a-zA-Z0-9_]+\b",
        prompt,
    )
    backticked = re.findall(r"`([a-zA-Z_][a-zA-Z0-9_\.]*)`", prompt)
    all_symbols = list(dict.fromkeys(backticked + symbol_candidates))

    # File hints (words ending in standard file extensions)
    file_hints = re.findall(
        r"\b[\w\-\/\\]+\.(?:py|ts|tsx|js|jsx|json|md|yaml|toml|rs|go|java|c|cpp|h)\b",
        prompt,
    )

    # Check if prompt is very short or generic (vague)
    is_vague = len(prompt.split()) < 5 or any(
        w in lowered for w in ["everything", "all files", "overview", "project status"]
    )

    return ParsedIntentRecord(
        task_summary=prompt.strip().split("\n")[0][:120],
        category=category,
        extracted_symbols=all_symbols,
        relevant_file_hints=list(dict.fromkeys(file_hints)),
        is_vague=is_vague,
    )
