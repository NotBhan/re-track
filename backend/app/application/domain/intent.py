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
    actions: list[str] = field(default_factory=list)
    target_entities: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    uncertainty: str | None = None
    is_vague: bool = False
    model_invoked: bool = False
    provider_identity: str | None = None
    model_name: str | None = None
    inference_status: str = "not_configured"
    fallback_used: bool = False
    fallback_reason: str | None = None
    inference_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize intent record to dictionary format."""
        return {
            "task_summary": self.task_summary,
            "category": self.category,
            "extracted_symbols": self.extracted_symbols,
            "relevant_file_hints": self.relevant_file_hints,
            "actions": self.actions,
            "target_entities": self.target_entities,
            "constraints": self.constraints,
            "uncertainty": self.uncertainty,
            "is_vague": self.is_vague,
            "model_invoked": self.model_invoked,
            "provider_identity": self.provider_identity,
            "model_name": self.model_name,
            "inference_status": self.inference_status,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "inference_time_ms": self.inference_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParsedIntentRecord":
        """Construct intent record from dictionary format."""
        return cls(
            task_summary=str(data.get("task_summary", "")),
            category=str(data.get("category", "general")),
            extracted_symbols=list(data.get("extracted_symbols", [])),
            relevant_file_hints=list(data.get("relevant_file_hints", [])),
            actions=list(data.get("actions", [])),
            target_entities=list(data.get("target_entities", [])),
            constraints=list(data.get("constraints", [])),
            uncertainty=data.get("uncertainty"),
            is_vague=bool(data.get("is_vague", False)),
            model_invoked=bool(data.get("model_invoked", False)),
            provider_identity=data.get("provider_identity"),
            model_name=data.get("model_name"),
            inference_status=str(data.get("inference_status", "not_configured")),
            fallback_used=bool(data.get("fallback_used", False)),
            fallback_reason=data.get("fallback_reason"),
            inference_time_ms=int(data.get("inference_time_ms", 0)),
        )


def parse_intent_heuristics(prompt: str) -> ParsedIntentRecord:
    """Pure, deterministic, LLM-free rule-based intent parser.

    Guarantees zero-hallucination intent extraction without external I/O or framework dependencies.
    Extracts semantic actions, entities, symbols, and file hints regardless of category taxonomy.
    """
    if not prompt or not prompt.strip():
        return ParsedIntentRecord(
            task_summary="",
            category="general",
            extracted_symbols=[],
            relevant_file_hints=[],
            actions=[],
            target_entities=[],
            constraints=[],
            is_vague=True,
        )

    clean_prompt = prompt.strip()
    lowered = clean_prompt.lower()

    # Extract actions (verbs)
    action_words = [
        "add", "create", "implement", "build", "integrate",
        "fix", "resolve", "patch", "repair", "debug",
        "refactor", "clean", "structure", "rename", "move", "reorganize",
        "explain", "find", "locate", "trace", "inspect", "investigate", "show", "where", "why",
        "change", "modify", "update", "retry", "delete", "remove",
    ]
    detected_actions = [
        a for a in action_words
        if re.search(r"\b" + re.escape(a) + r"\b", lowered)
    ]

    # Category is a flexible descriptor, NOT a gate
    category = "general"
    if any(w in lowered for w in ["fix", "bug", "error", "issue", "fail", "crash"]):
        category = "bug_fix"
    elif any(w in lowered for w in ["why", "how", "what", "where", "trace", "explain", "find", "inspect"]):
        category = "explanation"
    elif any(w in lowered for w in ["add", "create", "implement", "build", "new", "integrate"]):
        category = "feature_addition"
    elif any(w in lowered for w in ["refactor", "clean", "structure", "rename", "move"]):
        category = "refactoring"
    elif any(w in lowered for w in ["change", "modify", "update"]):
        category = "modification"

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
        clean_prompt,
    )
    backticked = re.findall(r"`([^`]+)`", clean_prompt)

    # File hints (words ending in standard file extensions)
    file_hints = re.findall(
        r"\b[\w\-\/\\]+\.(?:py|ts|tsx|js|jsx|json|md|yaml|yml|toml|rs|go|java|c|cpp|h|css|html)\b",
        clean_prompt,
    )
    file_hints_set = set(file_hints)

    # Clean and deduplicate symbols, excluding full file hints
    cleaned_symbols = []
    for s in backticked + symbol_candidates:
        s_clean = s.strip()
        if s_clean and s_clean not in file_hints_set and s_clean not in cleaned_symbols:
            cleaned_symbols.append(s_clean)

    # Extract target entities/phrases (noun chunks or meaningful phrases)
    # Filter common stop phrases
    stop_phrases = {"the", "a", "an", "this", "that", "to", "for", "in", "on", "at", "by", "from", "with", "into"}
    candidate_entities: list[str] = []
    
    # Check for multi-word technical concepts like "retry handling", "payment webhook", "database write", "jwt middleware"
    concept_matches = re.findall(r"\b[a-z]{3,}\s+[a-z]{3,}(?:\s+[a-z]{3,})?\b", lowered)
    for c in concept_matches:
        parts = c.split()
        if not all(p in stop_phrases for p in parts) and len(c) > 6:
            candidate_entities.append(c)

    # Vague only if very short and lacking concrete action or entity
    is_vague = (len(clean_prompt.split()) < 3 and not cleaned_symbols and not file_hints) or any(
        w == lowered for w in ["everything", "all files", "overview", "project status"]
    )

    return ParsedIntentRecord(
        task_summary=clean_prompt.split("\n")[0][:120],
        category=category,
        extracted_symbols=cleaned_symbols,
        relevant_file_hints=list(dict.fromkeys(file_hints)),
        actions=detected_actions,
        target_entities=list(dict.fromkeys(candidate_entities))[:6],
        constraints=[],
        is_vague=is_vague,
    )
