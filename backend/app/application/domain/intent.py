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

    # Regex for potential symbol / function / path patterns:
    # 1. Dotted symbol paths (e.g. app.server, routers.packages)
    # 2. PascalCase / CamelCase (e.g. ApplicationContainer, CGCService, makeKey)
    # 3. snake_case identifiers (e.g. parse_intent_heuristics, context_gen_lock, get_container)
    # 4. ALL_CAPS constants with underscore (e.g. SUPPORTED_EXTENSIONS, IGNORED_DIRS, DEBT_003)
    symbol_candidates = re.findall(
        r"\b[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)+\b"
        r"|\b(?:[A-Z]{2,}[a-z0-9]+[a-zA-Z0-9]*|[A-Z][a-z0-9]+[A-Z][a-zA-Z0-9]*|[a-z0-9]+[A-Z][a-zA-Z0-9]*)\b"
        r"|\b[a-zA-Z_][a-zA-Z0-9_]*_[a-zA-Z0-9_]+\b"
        r"|\b[A-Z][A-Z0-9_]{2,}\b",
        prompt,
    )
    backticked = re.findall(r"`([^`]+)`", prompt)
    
    # File hints (words ending in standard file extensions)
    file_hints = re.findall(
        r"\b[\w\-\/\\]+\.(?:py|ts|tsx|js|jsx|json|md|yaml|yml|toml|rs|go|java|c|cpp|h|css|html)\b",
        prompt,
    )
    file_hints_set = set(file_hints)

    # Clean and deduplicate symbols, excluding full file hints
    cleaned_symbols = []
    for s in backticked + symbol_candidates:
        s_clean = s.strip()
        if s_clean and s_clean not in file_hints_set and s_clean not in cleaned_symbols:
            cleaned_symbols.append(s_clean)

    # Check if prompt is very short or generic (vague)
    is_vague = len(prompt.split()) < 5 or any(
        w in lowered for w in ["everything", "all files", "overview", "project status"]
    )

    return ParsedIntentRecord(
        task_summary=prompt.strip().split("\n")[0][:120],
        category=category,
        extracted_symbols=cleaned_symbols,
        relevant_file_hints=list(dict.fromkeys(file_hints)),
        is_vague=is_vague,
    )
