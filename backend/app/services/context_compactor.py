"""Deterministic, evidence-aware context packing and compaction.

This module replaces tail truncation for the agent-context path. Given ranked
multi-modal evidence candidates (the existing arbitration output), it packs them
into an explicit evidence budget while preserving the project's truth hierarchy:

    source truth > deterministic AST > derived retrieval > semantic memory

Design rules enforced here:

- **Deterministic**: the same candidates, task and budget always produce byte
  identical output. Every ordering has an explicit string tie-break; nothing is
  random, sampled, time-dependent or category-gated.
- **Priority driven**: high-authority evidence is never sacrificed so that
  low-authority evidence can fit. Under pressure the lowest-value evidence is
  reduced, then dropped, first.
- **No tail truncation**: oversized evidence is reduced through an explicit
  level ladder that preserves provenance (file + line range) at every level.
- **No silent loss**: every omission and reduction is recorded with a reason.
- **Coherent**: evidence tied to the same source artifact stays grouped, so a
  snippet, its symbols and its call relationships are packed together.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Optional, Sequence

from app.application.domain.arbitration import ArbitratedCandidate, AuthorityTier
from app.services.token_budget import ContextBudgetPlan, estimate_tokens

# ---------------------------------------------------------------------------
# Reduction ladder
# ---------------------------------------------------------------------------

LEVEL_FULL = 0          # Full task-relevant evidence.
LEVEL_NORMALIZED = 1    # Redundant metadata / repeated lines removed.
LEVEL_WINDOWED = 2      # Surrounding source reduced to the relevant region.
LEVEL_SYMBOL_BODY = 3   # Exact symbol body preferred over file content.
LEVEL_SKELETON = 4      # Signatures + control flow + relationships only.
LEVEL_REFERENCE = 5     # Concise evidence reference (provenance only).

MAX_LEVEL = LEVEL_REFERENCE

LEVEL_NAMES = {
    LEVEL_FULL: "full",
    LEVEL_NORMALIZED: "normalized",
    LEVEL_WINDOWED: "relevant_region",
    LEVEL_SYMBOL_BODY: "symbol_body",
    LEVEL_SKELETON: "signatures_and_control_flow",
    LEVEL_REFERENCE: "evidence_reference",
}

_BLOCK_ELISION = "# [...] {count} lines elided by budget"

#: Token allowance for a rendered block's provenance header, fences and elision
#: note. Reserved before sizing a code region so a block never overshoots the
#: window budget it was given.
_BLOCK_OVERHEAD_TOKENS = 24

#: Navigation index bound for the package's relevant-file list. The list is a
#: pointer index, not evidence; its cap is recorded in the report notes.
_FILE_INDEX_LIMIT = 12

_DEFINITION_KEYWORDS = (
    "def ", "class ", "async def ", "function ", "export function ",
    "export default function ", "export class ", "export const ", "const ",
    "let ", "var ", "interface ", "type ", "enum ", "struct ", "impl ",
    "pub fn ", "fn ", "func ", "public ", "private ", "protected ",
    "static ", "abstract ", "export interface ", "export type ",
    "typedef ", "namespace ", "module ", "record ",
)

_CONTROL_KEYWORDS = (
    "def ", "class ", "return", "yield", "raise", "throw", "if ", "if(",
    "elif", "else", "for ", "while ", "try", "except", "finally", "catch",
    "switch", "case ", "match ", "with ", "await ", "break", "continue",
    "import ", "from ", "use ", "require(", "=>", "assert ",
)

_TERM_STOP_WORDS = frozenset({
    "the", "and", "for", "are", "can", "you", "does", "how", "what", "where",
    "when", "why", "with", "from", "this", "that", "into", "about", "there",
    "their", "them", "then", "than", "some", "such", "each", "were", "which",
    "will", "have", "has", "was", "not", "but", "its", "our", "your", "all",
    "any", "use", "used", "using", "get", "got", "should", "must", "also",
})


def derive_task_terms(task_prompt: str, extra_terms: Sequence[str] = ()) -> list[str]:
    """Derive deterministic, high-specificity matching terms from a task prompt.

    Callers that already computed the source-search term set should pass it as
    `extra_terms`; this function is the deterministic fallback.
    """
    terms: list[str] = []
    for term in extra_terms:
        clean = str(term).strip()
        if len(clean) > 2 and clean not in terms:
            terms.append(clean)

    for raw in re.split(r"[^\w./\\-]+", task_prompt or ""):
        clean = raw.strip("._-/\\")
        if len(clean) > 2 and clean.lower() not in _TERM_STOP_WORDS and clean not in terms:
            terms.append(clean)

    def specificity(term: str) -> tuple[int, int]:
        symbolish = 1 if re.search(r"[._]|[a-z0-9][A-Z]|[A-Z]{2,}", term) else 0
        return (symbolish, len(term))

    return sorted(terms, key=specificity, reverse=True)[:40]


# ---------------------------------------------------------------------------
# Evidence model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceItem:
    """A single ranked evidence artifact, adapted from arbitration output."""

    id: str
    tier: AuthorityTier
    kind: str
    content: str
    source_file: str = ""
    source_symbol: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    relevance: float = 0.0
    confidence: float = 0.0
    specificity: float = 0.0

    @property
    def order_key(self) -> tuple[int, float, float, float, str]:
        """Ranking order: authority tier, then existing arbitration signals."""
        return (
            int(self.tier.value),
            round(self.relevance, 4),
            round(self.confidence, 4),
            round(self.specificity, 4),
            self.id,
        )

    @property
    def provenance(self) -> str:
        """Traceable provenance string (never fabricated)."""
        if self.source_file and self.line_start:
            end = self.line_end or self.line_start
            return f"`{self.source_file}` (Lines {self.line_start}-{end})"
        if self.source_file:
            return f"`{self.source_file}`"
        if self.source_symbol:
            return f"`{self.source_symbol}`"
        return ""

    @classmethod
    def from_candidate(cls, candidate: ArbitratedCandidate) -> "EvidenceItem":
        """Adapt an arbitrated candidate without re-scoring it."""
        kind = candidate.relationship_kind
        if not kind:
            kind = "source_snippet" if candidate.tier == AuthorityTier.TIER_1_SOURCE else "unknown"
        return cls(
            id=candidate.id,
            tier=candidate.tier,
            kind=kind,
            content=candidate.content,
            source_file=candidate.source_file or "",
            source_symbol=candidate.source_symbol,
            line_start=candidate.line_start,
            line_end=candidate.line_end,
            relevance=candidate.relevance,
            confidence=candidate.confidence,
            specificity=candidate.specificity,
        )


@dataclass
class EvidenceGroup:
    """A coherent evidence unit packed and reduced as a whole."""

    id: str
    kind: str  # "source" | "structural" | "memory"
    items: list[EvidenceItem] = field(default_factory=list)
    mandatory: bool = False
    mandatory_reason: Optional[str] = None

    @property
    def order_key(self) -> tuple[int, float, float, float, str]:
        """Group rank: best item rank wins; ties broken by group id."""
        best = max((item.order_key[:4] for item in self.items), default=(0, 0.0, 0.0, 0.0))
        return (best[0], best[1], best[2], best[3], self.id)

    @property
    def tier(self) -> AuthorityTier:
        """Highest-authority tier present in the group."""
        if not self.items:
            return AuthorityTier.TIER_4_COGNEE
        return max(item.tier for item in self.items)

    @property
    def lead(self) -> EvidenceItem:
        """Highest-ranked item in the group."""
        return max(self.items, key=lambda item: item.order_key)


# ---------------------------------------------------------------------------
# Source parsing and line-level reduction helpers
# ---------------------------------------------------------------------------

_SOURCE_HEADER_RE = re.compile(r"^###\s+`?([^`\n(:]+)`?\s*\(Lines\s*(\d+)(?:-(\d+))?\)\s*$", re.MULTILINE)
_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_+.-]*\s*$")
_PREFIXES = (
    "Call Edge: ", "AST Edge: ", "Symbol: ", "Import: ", "Inheritance: ",
    "JSX Render: ", "AST Structural: ", "Definition: ",
)


def _strip_prefix(text: str) -> str:
    for prefix in _PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text.strip()


def _source_parts(item: "EvidenceItem") -> tuple[Optional[str], Optional[int], Optional[int], list[str]]:
    """Parse a Tier-1 source snippet into (path, start_line, end_line, body)."""
    content = item.content
    match = _SOURCE_HEADER_RE.search(content)
    path = item.source_file or None
    start = item.line_start
    end = item.line_end
    if match:
        path = match.group(1).strip() or path
        start = int(match.group(2))
        end = int(match.group(3)) if match.group(3) else start
        body = content[match.end():]
    else:
        body = content
    lines = body.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and _FENCE_RE.match(lines[0].strip()):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    while lines and not lines[-1].strip():
        lines.pop()
    return path, start, end, lines


def _normalize_lines(lines: Sequence[str], *, dedupe: bool = True) -> list[str]:
    """Collapse redundant whitespace and repeated lines."""
    out: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if not stripped:
            if out and out[-1] == "":
                continue
            out.append("")
            continue
        if dedupe and out and out[-1] == stripped:
            continue
        out.append(stripped)
    while out and out[-1] == "":
        out.pop()
    return out


def _term_hits(lines: Sequence[str], terms: Sequence[str]) -> list[int]:
    lowered_terms = [t.lower() for t in terms if len(t) > 2]
    if not lowered_terms:
        return []
    return [i for i, line in enumerate(lines) if any(term in line.lower() for term in lowered_terms)]


def _first_match_index(lines: Sequence[str], terms: Sequence[str]) -> Optional[int]:
    hits = _term_hits(lines, terms)
    return hits[0] if hits else None


def _relevant_window(lines: Sequence[str], terms: Sequence[str], context: int = 4) -> tuple[int, int]:
    """Return the contiguous window [start, end) covering task-relevant lines."""
    hits = _term_hits(lines, terms)
    if not hits:
        head = min(len(lines), max(1, context * 4))
        return 0, max(1, head)
    start = max(0, hits[0] - context)
    end = min(len(lines), hits[-1] + context + 1)
    return start, max(start + 1, end)


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _enclosing_symbol(lines: Sequence[str], anchor: int) -> tuple[int, int]:
    """Expand `anchor` to the enclosing definition block, provenance-exact.

    Walks up to the nearest definition header at or below the anchor's
    indentation, then down until indentation returns to the block level or the
    brace depth closes.
    """
    if not lines:
        return 0, 1

    anchor = max(0, min(anchor, len(lines) - 1))
    anchor_indent = _indent_of(lines[anchor])

    start = 0
    for idx in range(anchor, -1, -1):
        stripped = lines[idx].lstrip()
        indent = _indent_of(lines[idx])
        if indent <= anchor_indent and any(stripped.startswith(k) for k in _DEFINITION_KEYWORDS):
            start = idx
            break

    base_indent = _indent_of(lines[start])
    brace_depth = 0
    end = anchor + 1
    for idx in range(start, len(lines)):
        stripped = lines[idx].strip()
        brace_depth += stripped.count("{") - stripped.count("}")
        if idx > start and stripped and _indent_of(lines[idx]) <= base_indent:
            if not stripped.startswith(("#", "@", "//", "/*", "*")):
                break
        end = idx + 1
        if idx > anchor and brace_depth <= 0 and stripped.endswith("}"):
            break
    return start, max(end, min(len(lines), start + 1))


def _skeleton_lines(lines: Sequence[str]) -> list[str]:
    """Keep signatures, declarations and control flow; elide pure body lines."""
    out: list[str] = []
    elided = 0
    for line in lines:
        stripped = line.strip()
        keep = (
            not stripped
            or stripped.startswith(("#", "*", "//", "@", "/*", "*/"))
            or any(stripped.startswith(k) for k in _CONTROL_KEYWORDS)
            or stripped.endswith((":", "{", "=>", ";"))
            or stripped.endswith(("(", ",", ")"))
        )
        if keep:
            if elided:
                out.append(_BLOCK_ELISION.format(count=elided))
                elided = 0
            out.append(line)
        else:
            elided += 1
    if elided:
        out.append(_BLOCK_ELISION.format(count=elided))
    return out


def _compact_reference(text: str, limit: int = 160) -> str:
    """Reduce free text to its leading reference, marking any truncation."""
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[: max(1, limit - 15)].rstrip() + " [truncated]"


def _symbols_in_body(body: Sequence[str]) -> list[str]:
    found: list[str] = []
    pattern = re.compile(
        r"(?:def|class|function|interface|type|const|let|var|fn|func|struct|enum)\s+([A-Za-z_][A-Za-z0-9_]*)"
    )
    for line in body:
        for match in pattern.finditer(line):
            name = match.group(1)
            if name not in found:
                found.append(name)
    return found


def _first_identifier(text: str) -> str:
    match = re.search(r"[A-Za-z_][A-Za-z0-9_.]*", text)
    return match.group(0) if match else text[:40]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


class EvidenceRenderer:
    """Renders evidence groups at a given reduction level (provenance-safe)."""

    def __init__(self, task_terms: Sequence[str]) -> None:
        self._terms = [t for t in task_terms if len(t) > 2]

    # -- groups ------------------------------------------------------------
    def render(self, group: EvidenceGroup, level: int, window_budget: Optional[int] = None) -> str:
        """Render an evidence group at `level`.

        Args:
            window_budget: Token allowance for the relevant-region level. When
                supplied, the retained window grows to use the allowance instead
                of collapsing to a minimal slice.
        """
        if group.kind == "source":
            return self._render_source_group(group, level, window_budget)
        return self._render_support_group(group, level)

    def _render_source_group(self, group: EvidenceGroup, level: int, window_budget: Optional[int]) -> str:
        blocks = [
            self._render_source_item(item, level, window_budget)
            if item.kind == "source_snippet"
            else self._render_support_item(item, level)
            for item in group.items
        ]
        return "\n".join(block for block in blocks if block)

    def _render_support_group(self, group: EvidenceGroup, level: int) -> str:
        return "\n".join(
            block for block in (self._render_support_item(item, level) for item in group.items) if block
        )

    # -- source items ------------------------------------------------------
    def _render_source_item(self, item: EvidenceItem, level: int, window_budget: Optional[int] = None) -> str:
        path, start, end, body = _source_parts(item)
        display_path = path or item.source_file or "unknown source"

        if level >= LEVEL_REFERENCE or not body:
            symbols = ", ".join(f"`{s}`" for s in _symbols_in_body(body)[:6])
            detail = f" Symbols: {symbols}." if symbols else ""
            span = f"Lines {start}-{end}" if start else f"{len(body)} lines"
            return (
                f"### `{display_path}` ({span})\n"
                f"- Full source omitted to satisfy the context budget.{detail} "
                f"Read the file at the referenced lines."
            )

        base_line = start or 1

        if level == LEVEL_SKELETON:
            window, ws, we = self._symbol_window(body, base_line)
            rendered = _normalize_lines(_skeleton_lines(_normalize_lines(window)))
            header = f"### `{display_path}` (Lines {ws}-{we}, signatures/control flow)"
            return header + "\n```\n" + "\n".join(rendered) + "\n```"

        if level == LEVEL_SYMBOL_BODY:
            window, ws, we = self._symbol_window(body, base_line)
            header = f"### `{display_path}` (Lines {ws}-{we}, symbol body)"
            return header + "\n```\n" + "\n".join(_normalize_lines(window)) + "\n```"

        if level == LEVEL_WINDOWED:
            win_start, win_end = self._budgeted_window(body, window_budget)
            window = body[win_start:win_end]
            elided = len(body) - len(window)
            header = f"### `{display_path}` (Lines {base_line + win_start}-{base_line + win_end - 1})"
            if elided > 0:
                header += f"\n{_BLOCK_ELISION.format(count=elided)}"
            return header + "\n```\n" + "\n".join(_normalize_lines(window)) + "\n```"

        body = _normalize_lines(body)
        span = f"Lines {start}-{end}" if start else f"{len(body)} lines"
        if level == LEVEL_NORMALIZED and len(body) < 2:
            span = f"{len(body)} lines"
        return f"### `{display_path}` ({span})\n```\n" + "\n".join(body) + "\n```"

    def _symbol_window(self, body: Sequence[str], base_line: int) -> tuple[list[str], int, int]:
        anchor = _first_match_index(body, self._terms)
        if anchor is None:
            return list(body), base_line, base_line + max(0, len(body) - 1)
        sym_start, sym_end = _enclosing_symbol(body, anchor)
        return list(body[sym_start:sym_end]), base_line + sym_start, base_line + sym_end - 1

    def _budgeted_window(self, body: Sequence[str], window_budget: Optional[int]) -> tuple[int, int]:
        """Return the task-relevant window, grown to use `window_budget` tokens.

        The window always starts from the task-relevant region (lines matching the
        task terms and their immediate context) and then expands — after the last
        hit first, then before the first hit — while the estimated token cost stays
        inside the allowance. Growth is deterministic and provenance-exact: the
        result is a single contiguous line range.
        """
        start, end = _relevant_window(body, self._terms)
        if window_budget is None or window_budget <= 0:
            return start, end

        # The rendered block also carries its provenance header, fences and
        # elision note; reserve that before sizing the code region.
        body_budget = max(1, window_budget - _BLOCK_OVERHEAD_TOKENS)

        def cost(low: int, high: int) -> int:
            return estimate_tokens("\n".join(body[low:high]))

        if cost(start, end) > body_budget:
            # Shrink around the first hit until the allowance is respected.
            while end - start > 1 and cost(start, end) > body_budget:
                if end - 1 > start:
                    end -= 1
                else:
                    break
            return start, max(start + 1, end)

        while True:
            grew = False
            if end < len(body):
                candidate_end = min(len(body), end + 1)
                if cost(start, candidate_end) <= body_budget:
                    end = candidate_end
                    grew = True
            if start > 0:
                candidate_start = max(0, start - 1)
                if cost(candidate_start, end) <= body_budget:
                    start = candidate_start
                    grew = True
            if not grew:
                break
        return start, end

    # -- structural and memory items --------------------------------------
    def _render_support_item(self, item: EvidenceItem, level: int) -> str:
        if item.kind == "recall_package":
            return self._render_recall_block(item, level)
        if item.tier in (AuthorityTier.TIER_3_LANCEDB_KUZU, AuthorityTier.TIER_4_COGNEE):
            return self._render_memory_item(item, level)

        content = _strip_prefix(item.content)
        if level == LEVEL_FULL:
            return f"- {_strip_prefix(item.content)}"
        # Structural facts are single-line; the ladder compacts them in place and
        # keeps the relationship intact at every level.
        compact = " ".join(content.split())
        if item.kind == "call_graph":
            compact = compact.replace("->", "→")
        return f"- {compact}"

    def _render_recall_block(self, item: EvidenceItem, level: int) -> str:
        """Render the deterministic derived-recall block (lowest authority tier)."""
        lines = [line for line in _normalize_lines(item.content.splitlines()) if line.strip()]
        if not lines:
            return ""
        if level >= LEVEL_REFERENCE:
            return (
                "### Derived recall context\n"
                "- Derived recall content omitted to satisfy the context budget."
            )
        if level == LEVEL_SKELETON:
            kept = lines[:6]
        elif level == LEVEL_SYMBOL_BODY:
            kept = lines[:12]
        elif level == LEVEL_WINDOWED:
            kept = lines[:30]
        else:
            kept = lines
        body = "\n".join(kept)
        if len(kept) < len(lines):
            body += f"\n{_BLOCK_ELISION.format(count=len(lines) - len(kept))}"
        return "### Derived recall context\n" + body

    def _render_memory_item(self, item: EvidenceItem, level: int) -> str:
        text = item.content
        if level >= LEVEL_REFERENCE:
            return f"- {_compact_reference(text, 120)} [reference only]"
        if level == LEVEL_SKELETON:
            return f"- {_compact_reference(text, 160)}"
        if level == LEVEL_SYMBOL_BODY:
            first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
            return f"- {_compact_reference(first, 200)}"
        if level == LEVEL_WINDOWED:
            lines = [ln for ln in _normalize_lines(text.splitlines()) if ln.strip()][:3]
            return "- " + " ".join(lines)
        if level == LEVEL_NORMALIZED:
            return f"- {' '.join(text.split())}"
        return f"- {text.strip()}"


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


@dataclass
class RetainedEvidence:
    """Telemetry for evidence kept in the final package."""

    id: str
    tier: str
    kind: str
    level: int
    level_name: str
    tokens_before: int
    tokens_after: int
    source_file: str = ""
    source_symbol: str = ""
    mandatory: bool = False
    window_budget: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier,
            "kind": self.kind,
            "level": self.level,
            "level_name": self.level_name,
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "source_file": self.source_file,
            "source_symbol": self.source_symbol,
            "mandatory": self.mandatory,
            "window_budget": self.window_budget,
        }


@dataclass
class OmittedEvidence:
    """Telemetry for evidence that did not fit the budget."""

    id: str
    tier: str
    kind: str
    tokens: int
    reason: str
    source_file: str = ""
    source_symbol: str = ""
    mandatory: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "tier": self.tier,
            "kind": self.kind,
            "tokens": self.tokens,
            "reason": self.reason,
            "source_file": self.source_file,
            "source_symbol": self.source_symbol,
            "mandatory": self.mandatory,
        }


@dataclass
class CompactionReport:
    """Measured budget and loss telemetry for one compaction pass."""

    requested_tokens: int
    fixed_overhead_tokens: int
    task_prompt_tokens: int
    output_reservation_tokens: int
    evidence_budget_tokens: int
    planned_output_reservation_tokens: int = 0
    pre_compaction_tokens: int = 0
    evidence_tokens: int = 0
    final_tokens: int = 0
    candidates_before: int = 0
    candidates_after: int = 0
    retained: list[RetainedEvidence] = field(default_factory=list)
    omitted: list[OmittedEvidence] = field(default_factory=list)
    reduced: list[RetainedEvidence] = field(default_factory=list)
    top_evidence: list[dict[str, Any]] = field(default_factory=list)
    mandatory_evidence_tokens: int = 0
    mandatory_evidence_fit: bool = True
    unplaced_mandatory: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    budget_satisfied: bool = True
    degraded: bool = False
    degradation_reason: Optional[str] = None
    levels_used: dict[str, int] = field(default_factory=dict)
    sections: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def evidence_reduction(self) -> float:
        """Measured fraction of the pre-compaction evidence text removed to fit.

        ``0.0`` means nothing had to be removed. This is a measurement of the
        evidence region only — never a whole-package claim, because the task
        prompt, file index and provenance headers are not reducible.
        """
        if self.pre_compaction_tokens <= 0:
            return 0.0
        removed = max(0, self.pre_compaction_tokens - self.evidence_tokens)
        return round(removed / self.pre_compaction_tokens, 4)

    def to_dict(self) -> dict[str, Any]:
        """Serialize telemetry. Only measured values; no fabricated percentages."""
        return {
            "requested_tokens": self.requested_tokens,
            "fixed_overhead_tokens": self.fixed_overhead_tokens,
            "task_prompt_tokens": self.task_prompt_tokens,
            "output_reservation_tokens": self.output_reservation_tokens,
            "planned_output_reservation_tokens": self.planned_output_reservation_tokens,
            "evidence_budget_tokens": self.evidence_budget_tokens,
            "pre_compaction_tokens": self.pre_compaction_tokens,
            "evidence_tokens": self.evidence_tokens,
            "final_tokens": self.final_tokens,
            "candidates_before": self.candidates_before,
            "candidates_after": self.candidates_after,
            "retained_count": len(self.retained),
            "omitted_count": len(self.omitted),
            "reduced_count": len(self.reduced),
            "retained": [entry.to_dict() for entry in self.retained],
            "omitted": [entry.to_dict() for entry in self.omitted],
            "reduced": [entry.to_dict() for entry in self.reduced],
            "top_evidence": list(self.top_evidence),
            "mandatory_evidence_tokens": self.mandatory_evidence_tokens,
            "mandatory_evidence_fit": self.mandatory_evidence_fit,
            "unplaced_mandatory": list(self.unplaced_mandatory),
            "missing_evidence": list(self.missing_evidence),
            "budget_satisfied": self.budget_satisfied,
            "degraded": self.degraded,
            "degradation_reason": self.degradation_reason,
            "evidence_reduction": self.evidence_reduction,
            "levels_used": dict(self.levels_used),
            "sections": list(self.sections),
            "notes": list(self.notes),
        }


@dataclass
class CompactionResult:
    """Packed evidence plus the document header it was packed against."""

    header_markdown: str
    evidence_markdown: str
    report: CompactionReport
    budget_plan: ContextBudgetPlan

    @property
    def deterministic_markdown(self) -> str:
        """Full package when no synthesis model is invoked."""
        return self.compose(None)

    def compose(self, synthesis_markdown: Optional[str]) -> str:
        """Assemble the delivered package: header, optional synthesis, evidence."""
        parts: list[str] = [self.header_markdown]
        if synthesis_markdown and synthesis_markdown.strip():
            parts.append(synthesis_markdown.strip())
        if self.evidence_markdown.strip():
            parts.append(self.evidence_markdown.strip())
        return "\n\n".join(part for part in parts if part.strip()) + "\n"

    def observe_final(self, final_markdown: str) -> CompactionReport:
        """Record the measured size of the actually delivered document."""
        self.report.final_tokens = estimate_tokens(final_markdown)
        self.report.budget_satisfied = self.report.final_tokens <= self.report.requested_tokens
        if not self.report.budget_satisfied:
            self.report.degraded = True
            if not self.report.degradation_reason:
                self.report.degradation_reason = "final_package_exceeds_requested_budget"
        return self.report


# ---------------------------------------------------------------------------
# Compactor
# ---------------------------------------------------------------------------

_SOURCE_SECTION = "# Relevant Code Snippets & Target Implementations"
_STRUCTURAL_SECTION = "# Structural Code Relationships"
_MEMORY_SECTION = "# Semantic Memory (validated, derived)"
_RECALL_SECTION = "# Derived Recall Context"

_SECTION_ORDER = {"source": 0, "structural": 1, "memory": 2, "recall": 3}
_SECTION_TITLES = {
    "source": _SOURCE_SECTION,
    "structural": _STRUCTURAL_SECTION,
    "memory": _MEMORY_SECTION,
    "recall": _RECALL_SECTION,
}

#: A packed entry: the telemetry record, its group, and the level it was rendered at.
Entry = tuple[RetainedEvidence, EvidenceGroup, int]


class ContextCompactor:
    """Packs ranked evidence into an explicit budget with progressive reduction."""

    def compact(
        self,
        *,
        candidates: Sequence[ArbitratedCandidate | EvidenceItem],
        plan: ContextBudgetPlan,
        task_prompt: str,
        title: str,
        task_terms: Sequence[str] = (),
        task_symbols: Sequence[str] = (),
        task_files: Sequence[str] = (),
        relevant_files: Sequence[str] = (),
        missing_evidence: Sequence[str] = (),
        output_reservation_override: Optional[int] = None,
    ) -> CompactionResult:
        """Pack evidence for `task_prompt` into the plan's evidence allowance.

        Args:
            candidates: Ranked arbitration candidates (already provenance-validated).
            plan: Explicit budget split from :func:`plan_context_budget`.
            task_prompt: Verbatim developer task (always preserved).
            title: Task-context heading text.
            task_terms: Terms used for relevance windowing.
            task_symbols: Symbols extracted from the task (mandatory signal).
            task_files: Files referenced by the task (mandatory signal).
            relevant_files: Repository files ranked relevant to the task, rendered
                as a bounded navigation index in the package header.
            missing_evidence: Evidence the pipeline already knows is absent.
            output_reservation_override: Measured size of a synthesis answer that
                already exists. When supplied it replaces the planned reservation
                so the evidence is re-packed to fit around the real answer — the
                answer is never truncated to make room for evidence.
        """
        renderer = EvidenceRenderer(list(task_terms))
        items = [self._adapt(candidate) for candidate in candidates]
        items = [item for item in items if item.content.strip()]
        items.sort(key=lambda item: item.order_key, reverse=True)

        symbol_set = {s.lower() for s in task_symbols if s}
        file_set = {f.lower().lstrip("./") for f in task_files if f}

        groups = self._build_groups(items, symbol_set, file_set)
        groups.sort(key=lambda group: group.order_key, reverse=True)

        title_text = title.strip() or task_prompt.strip()[:120]
        header = f"# Task\n\n{task_prompt.strip()}\n\n# Task Context: {title_text}"
        file_index, dropped_files = self._build_file_index(relevant_files)
        if file_index:
            header += "\n\n# Relevant Files\n\n" + file_index

        # The output half of the budget: the planned reservation, or the measured
        # size of an answer that already exists.
        reserved_output = (
            plan.output_reservation_tokens
            if output_reservation_override is None
            else max(0, int(output_reservation_override))
        )
        document_target = max(0, plan.requested_tokens - reserved_output)
        measured_allowance = max(0, document_target - estimate_tokens(header))

        report = CompactionReport(
            requested_tokens=plan.requested_tokens,
            fixed_overhead_tokens=plan.fixed_overhead_tokens,
            task_prompt_tokens=plan.task_prompt_tokens,
            output_reservation_tokens=reserved_output,
            planned_output_reservation_tokens=plan.output_reservation_tokens,
            evidence_budget_tokens=measured_allowance,
            pre_compaction_tokens=sum(estimate_tokens(renderer.render(group, LEVEL_FULL)) for group in groups),
            candidates_before=len(items),
            missing_evidence=list(missing_evidence),
        )
        if output_reservation_override is not None:
            report.notes.append("re_packed_for_observed_synthesis")
        if measured_allowance < plan.evidence_budget_tokens:
            report.notes.append("measured_allowance_below_planned_budget")
        if dropped_files:
            report.notes.append(f"file_index_capped:{dropped_files}")
        report.notes.extend(plan.notes)

        entries, omitted, levels = self._pack(groups, renderer, header, document_target)
        evidence_markdown = self._render_document(entries, renderer)

        report.retained = [entry for entry, _group, _level in entries]
        report.omitted = omitted
        report.reduced = [entry for entry in report.retained if entry.level > LEVEL_FULL]
        report.candidates_after = len(report.retained)
        report.evidence_tokens = estimate_tokens(evidence_markdown)
        report.levels_used = levels
        report.sections = self._sections_for(entries)
        report.mandatory_evidence_tokens = sum(
            entry.tokens_after for entry in report.retained if entry.mandatory
        )
        report.top_evidence = [
            {
                "id": entry.id,
                "tier": entry.tier,
                "kind": entry.kind,
                "level": entry.level,
                "tokens": entry.tokens_after,
                "source_file": entry.source_file,
                "source_symbol": entry.source_symbol,
            }
            for entry in report.retained[:8]
        ]

        # Mandatory evidence is never dropped. When it cannot fit the evidence
        # allowance the pack is reported as over-committed instead of being
        # quietly degraded into something smaller than the task requires.
        mandatory_ids = {group.id for group in groups if group.mandatory}
        placed_ids = {entry.id for entry in report.retained}
        report.unplaced_mandatory = sorted(mandatory_ids - placed_ids)
        allowance_exceeded = report.mandatory_evidence_tokens > max(measured_allowance, 1)
        if allowance_exceeded and not report.unplaced_mandatory:
            report.notes.append("mandatory_evidence_exceeds_allowance")
        report.mandatory_evidence_fit = not report.unplaced_mandatory and not allowance_exceeded

        result = CompactionResult(
            header_markdown=header,
            evidence_markdown=evidence_markdown,
            report=report,
            budget_plan=plan,
        )
        result.observe_final(result.deterministic_markdown)
        if report.unplaced_mandatory:
            report.degraded = True
            report.degradation_reason = "mandatory_evidence_dropped"
        elif estimate_tokens(header) > document_target:
            # The task prompt and package scaffolding alone exceed the budget. No
            # packing strategy can satisfy it; the task is still reproduced
            # verbatim rather than truncated, and the state is reported.
            report.degraded = True
            report.degradation_reason = "fixed_prompt_overhead_exceeds_budget"
        elif not report.budget_satisfied and report.degradation_reason is None:
            report.degradation_reason = "mandatory_evidence_exceeds_budget"
        return result

    # -- grouping ----------------------------------------------------------
    @staticmethod
    def _adapt(candidate: ArbitratedCandidate | EvidenceItem) -> EvidenceItem:
        if isinstance(candidate, EvidenceItem):
            return candidate
        return EvidenceItem.from_candidate(candidate)

    def _build_groups(
        self,
        items: Sequence[EvidenceItem],
        symbol_set: set[str],
        file_set: set[str],
    ) -> list[EvidenceGroup]:
        """Form coherent groups; source anchors keep their related evidence."""
        sources = [item for item in items if item.tier == AuthorityTier.TIER_1_SOURCE]
        others = [item for item in items if item.tier != AuthorityTier.TIER_1_SOURCE]

        source_groups: list[EvidenceGroup] = []
        for item in sources:
            reason = self._mandatory_reason(item, symbol_set, file_set)
            source_groups.append(
                EvidenceGroup(
                    id=f"group:{item.id}",
                    kind="source",
                    items=[item],
                    mandatory=reason is not None,
                    mandatory_reason=reason,
                )
            )
        if source_groups and not any(group.mandatory for group in source_groups):
            # Always keep the best available source truth, even for tasks whose
            # prompt matched no symbol and no file.
            source_groups[0].mandatory = True
            source_groups[0].mandatory_reason = "highest-ranked available source evidence"

        # Structural evidence that touches a selected task symbol is mandatory:
        # it is the connecting evidence between the task's symbols and the source
        # artifacts (entry point -> caller -> callee -> target).
        mandatory_structural: list[EvidenceItem] = []
        attachable: list[EvidenceItem] = []
        for item in others:
            if self._touches_task(item, symbol_set, file_set):
                mandatory_structural.append(item)
            else:
                attachable.append(item)

        merged = list(source_groups)
        for item in attachable:
            anchor = self._best_anchor(item, merged)
            if anchor is not None:
                anchor.items.append(item)
            else:
                merged.append(EvidenceGroup(id=f"group:{item.id}", kind=self._kind_for(item), items=[item]))

        if mandatory_structural:
            merged.append(
                EvidenceGroup(
                    id="group:ast:task-linked",
                    kind="structural",
                    items=mandatory_structural,
                    mandatory=True,
                    mandatory_reason="AST relationship to the selected task symbols",
                )
            )
        return merged

    @staticmethod
    def _kind_for(item: EvidenceItem) -> str:
        if item.kind == "recall_package":
            return "recall"
        if item.tier in (AuthorityTier.TIER_3_LANCEDB_KUZU, AuthorityTier.TIER_4_COGNEE):
            return "memory"
        return "structural"

    @staticmethod
    def _mandatory_reason(
        item: EvidenceItem,
        symbol_set: set[str],
        file_set: set[str],
    ) -> Optional[str]:
        """Mandatory-evidence predicate built only on existing arbitration signals."""
        if item.tier == AuthorityTier.TIER_1_SOURCE:
            lowered = item.content.lower()
            if any(symbol in lowered for symbol in symbol_set if len(symbol) > 2):
                return "source evidence matching an extracted task symbol"
            if item.source_file and item.source_file.lower().lstrip("./") in file_set:
                return "source evidence from a task-referenced file"
            if item.relevance >= 1.0:
                return "highest-relevance source evidence for the task"
            return None
        if item.tier == AuthorityTier.TIER_2_MANIFEST_AST:
            return ContextCompactor._structural_reason(item, symbol_set)
        return None

    @staticmethod
    def _structural_reason(item: EvidenceItem, symbol_set: set[str]) -> Optional[str]:
        content = item.content.lower()
        if not any(symbol in content for symbol in symbol_set if len(symbol) > 2):
            return None
        if item.kind == "call_graph":
            return "call relationship to a selected task symbol"
        if item.kind in ("symbol", "definition"):
            return "exact symbol match for the task"
        return "AST evidence referencing a selected task symbol"

    @staticmethod
    def _touches_task(item: EvidenceItem, symbol_set: set[str], file_set: set[str]) -> bool:
        if ContextCompactor._structural_reason(item, symbol_set):
            return True
        if item.source_file and item.source_file.lower().lstrip("./") in file_set:
            return True
        return False

    def _best_anchor(self, item: EvidenceItem, groups: Sequence[EvidenceGroup]) -> Optional[EvidenceGroup]:
        """Attach supporting evidence to the highest-ranked group it explains."""
        if item.kind == "recall_package":
            # A whole derived-recall document is not a supporting fact for one
            # source artifact: it keeps its own group so it can be reduced and
            # dropped on its own, at the lowest authority tier.
            return None
        item_file = (item.source_file or "").lower().lstrip("./")
        for group in groups:
            if group.kind != "source":
                continue
            lead = group.items[0]
            lead_body = lead.content.lower()
            if item_file and lead.source_file and item_file == lead.source_file.lower().lstrip("./"):
                return group
            if item.source_symbol and item.source_symbol.lower() in lead_body:
                return group
            identifier = _first_identifier(_strip_prefix(item.content)).lower()
            if len(identifier) > 3 and identifier in lead_body:
                return group
        return None

    # -- packing -----------------------------------------------------------
    def _pack(
        self,
        groups: Sequence[EvidenceGroup],
        renderer: EvidenceRenderer,
        header: str,
        document_target: int,
    ) -> tuple[list[tuple[RetainedEvidence, EvidenceGroup, int]], list[OmittedEvidence], dict[str, int]]:
        """Allocate, correct, then grow. Reduction always hits the lowest-value evidence first."""
        order = sorted(groups, key=lambda group: group.order_key, reverse=True)
        ranked = [group for group in order if group.mandatory] + [group for group in order if not group.mandatory]

        entries: dict[str, Entry] = {}
        levels: dict[str, int] = {}
        header_tokens = estimate_tokens(header)

        def document_tokens() -> int:
            return header_tokens + estimate_tokens(self._render_document(list(entries.values()), renderer))

        # Phase A — allocate: every group receives a fair share of what remains, so
        # the highest-ranked artifact cannot consume the whole budget and starve
        # the evidence that explains it.
        for index, group in enumerate(ranked):
            groups_left = len(ranked) - index
            remaining = max(0, document_target - document_tokens())
            share = max(1, remaining // max(1, groups_left))
            entry = self._place(group, renderer, share)
            entries[group.id] = (entry, group, entry.level)
            levels[group.id] = entry.level

        # Phase B — correct: if the measured document still exceeds the target, the
        # lowest ranked evidence yields first. High-authority evidence is always
        # the last to be reduced and the last to be dropped.
        omitted: list[OmittedEvidence] = []
        reducible = list(reversed(order))
        progressed = True
        while document_tokens() > document_target and progressed:
            progressed = False
            for group in reducible:
                entry = entries.get(group.id)
                if entry is None:
                    continue
                if entry[2] < MAX_LEVEL:
                    new_level = entry[2] + 1
                    new_entry = self._entry_for(
                        group, new_level, renderer, mandatory=entry[0].mandatory, window_budget=None
                    )
                    entries[group.id] = (new_entry, group, new_level)
                    levels[group.id] = new_level
                    progressed = True
                    break
            if progressed:
                continue
            for group in reducible:
                entry = entries.get(group.id)
                if entry is None or group.mandatory:
                    continue
                omitted.append(self._omission(entry[0], "budget_exhausted_after_max_reduction"))
                del entries[group.id]
                levels.pop(group.id, None)
                progressed = True
                break

        # Phase C — grow: spend whatever budget is still unallocated by restoring
        # fidelity, highest-ranked evidence first. This is what makes a larger
        # budget buy more (rather than the same) evidence. The ladder is not
        # monotonic in cost, so every less-reduced level is tried, best first.
        for _ in range(len(ranked) + 1):
            grew = False
            for group in ranked:
                entry = entries.get(group.id)
                if entry is None:
                    continue
                retained, _group, level = entry
                if level == LEVEL_FULL:
                    continue
                leftover = document_target - document_tokens()
                if leftover <= 0:
                    break
                allowance = retained.tokens_after + leftover
                targets: list[tuple[int, Optional[int]]] = [
                    (target_level, allowance if target_level == LEVEL_WINDOWED else None)
                    for target_level in range(level - 1, LEVEL_FULL - 1, -1)
                ]
                if level >= LEVEL_WINDOWED:
                    # A relevant-region entry grows in place before it can be
                    # restored to full source: this is the path a mid-size budget
                    # takes to buy more evidence.
                    targets.append((LEVEL_WINDOWED, allowance))
                for target_level, window_budget in targets:
                    candidate = self._entry_for(
                        group,
                        target_level,
                        renderer,
                        mandatory=retained.mandatory,
                        window_budget=window_budget,
                    )
                    if candidate.tokens_after <= allowance:
                        entries[group.id] = (candidate, group, target_level)
                        levels[group.id] = target_level
                        grew = True
                        break
            if not grew:
                break

        return list(entries.values()), omitted, levels

    def _place(self, group: EvidenceGroup, renderer: EvidenceRenderer, allowance: int) -> RetainedEvidence:
        """Choose the least-reduced level whose cost fits `allowance`."""
        for level in range(LEVEL_FULL, MAX_LEVEL + 1):
            entry = self._entry_for(
                group,
                level,
                renderer,
                mandatory=group.mandatory,
                window_budget=allowance if level == LEVEL_WINDOWED else None,
            )
            if entry.tokens_after <= allowance:
                return entry
        return self._entry_for(group, MAX_LEVEL, renderer, mandatory=group.mandatory, window_budget=None)

    def _entry_for(
        self,
        group: EvidenceGroup,
        level: int,
        renderer: EvidenceRenderer,
        mandatory: bool,
        window_budget: Optional[int],
    ) -> RetainedEvidence:
        rendered = renderer.render(group, level, window_budget if level == LEVEL_WINDOWED else None)
        lead = group.lead
        return RetainedEvidence(
            id=group.id,
            tier=lead.tier.name,
            kind=self._group_kind(group),
            level=level,
            level_name=LEVEL_NAMES[level],
            tokens_before=estimate_tokens(renderer.render(group, LEVEL_FULL)),
            tokens_after=estimate_tokens(rendered),
            source_file=lead.source_file,
            source_symbol=lead.source_symbol or "",
            mandatory=mandatory,
            window_budget=window_budget or 0,
        )

    @staticmethod
    def _group_kind(group: EvidenceGroup) -> str:
        kinds = [item.kind for item in group.items]
        if "source_snippet" in kinds:
            return "source_snippet"
        if group.kind == "recall":
            return "derived_recall"
        if group.kind == "memory":
            return "semantic_memory"
        return kinds[0] if kinds else "evidence"

    @staticmethod
    def _omission(entry: RetainedEvidence, reason: str) -> OmittedEvidence:
        return OmittedEvidence(
            id=entry.id,
            tier=entry.tier,
            kind=entry.kind,
            tokens=entry.tokens_before,
            reason=reason,
            source_file=entry.source_file,
            source_symbol=entry.source_symbol,
            mandatory=entry.mandatory,
        )

    def _render_document(
        self,
        entries: Sequence[Entry],
        renderer: EvidenceRenderer,
    ) -> str:
        """Render packed groups by section, in a stable section order."""
        buckets: dict[str, list[Entry]] = {
            "source": [], "structural": [], "memory": [], "recall": [],
        }
        for entry in entries:
            buckets[entry[1].kind].append(entry)

        parts: list[str] = []
        for section in sorted(buckets, key=lambda name: _SECTION_ORDER[name]):
            section_entries = sorted(buckets[section], key=lambda entry: entry[1].order_key, reverse=True)
            if not section_entries:
                continue
            blocks: list[str] = []
            for retained, group, level in section_entries:
                block = renderer.render(
                    group,
                    level,
                    self._window_budget_of(retained) if level == LEVEL_WINDOWED else None,
                )
                if block.strip():
                    blocks.append(block)
            if blocks:
                parts.append(f"{_SECTION_TITLES[section]}\n\n" + "\n".join(blocks))
        return "\n\n".join(parts)

    @staticmethod
    def _window_budget_of(retained: RetainedEvidence) -> int:
        return retained.window_budget if retained.level == LEVEL_WINDOWED else 0

    @staticmethod
    def _build_file_index(relevant_files: Sequence[str]) -> tuple[str, int]:
        """Render the bounded relevant-file navigation index.

        Returns:
            (markdown, dropped_count) — the dropped count is reported, never hidden.
        """
        seen: list[str] = []
        for path in relevant_files:
            clean = str(path).strip().lstrip("./")
            if clean and clean not in seen:
                seen.append(clean)
        shown = seen[:_FILE_INDEX_LIMIT]
        if not shown:
            return "", 0
        return "\n".join(f"- `{path}`" for path in shown), max(0, len(seen) - len(shown))

    @staticmethod
    def _sections_for(entries: Sequence[Entry]) -> list[str]:
        present = {entry[1].kind for entry in entries}
        return [name for name in sorted(_SECTION_ORDER, key=lambda n: _SECTION_ORDER[n]) if name in present]
