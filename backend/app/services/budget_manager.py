"""Budget enforcement for Context Package sections.

Uses soft-target token budgets with priority classes:
- Critical (5): Task, Objective, Relevant Files, Starting Point — never removed
- High (4): Architecture, Implementation Notes, Constraints — compress, never remove
- Medium (3): Symbols, APIs, Decisions — compress then remove
- Low (1-2): Dependencies, Conventions, References — remove first

Token estimation: 1 token ≈ 4 characters.
"""

import logging

from app.models.responses import PackageSection

logger = logging.getLogger(__name__)

# Priority classes
_CRITICAL = {5}
_HIGH = {4}
_MEDIUM = {3}
_LOW = {1, 2}

# Token estimation constant
_CHARS_PER_TOKEN = 4


class BudgetManager:
    """Enforces soft-target token budgets on Context Package sections.

    When the package exceeds the target, sections are removed or compressed
    in priority order: Low first, then Medium, then High compression.
    Critical sections are never removed.
    """

    def __init__(self, target_tokens: int = 3000) -> None:
        """Initialize the budget manager.

        Args:
            target_tokens: Target token count for the package.
        """
        self._target = target_tokens
        self.last_compression_ratio: float = 1.0

    def apply(self, sections: list[PackageSection]) -> list[PackageSection]:
        """Trim sections to fit within the target budget.

        Priority order for removal:
        1. Low priority (Dependencies, Conventions, References)
        2. Medium priority (Symbols, APIs, Decisions) — remove
        3. High priority (Architecture, Implementation Notes) — compress to 50%
        4. Critical (Task, Objective, Files, Starting Point) — never removed

        Args:
            sections: Sections to budget-trim.

        Returns:
            Trimmed sections fitting within target.
        """
        if not sections:
            return []

        total_tokens = self._estimate_tokens(sections)

        if total_tokens <= self._target:
            self.last_compression_ratio = 1.0
            return sections

        result = list(sections)

        # Phase 1: Remove low priority
        result = [s for s in result if s.priority not in _LOW]
        if self._estimate_tokens(result) <= self._target:
            return self._finalize(result, total_tokens)

        # Phase 2: Remove medium priority
        result = [s for s in result if s.priority not in _MEDIUM]
        if self._estimate_tokens(result) <= self._target:
            return self._finalize(result, total_tokens)

        # Phase 3: Compress high priority sections to 50%
        result = self._compress_by_priority(result, _HIGH, 0.5)
        return self._finalize(result, total_tokens)

    def _estimate_tokens(self, sections: list[PackageSection]) -> int:
        """Estimate token count from character count.

        Args:
            sections: Sections to estimate.

        Returns:
            Estimated token count.
        """
        chars = sum(len(s.content) for s in sections)
        return chars // _CHARS_PER_TOKEN

    def _compress_by_priority(
        self,
        sections: list[PackageSection],
        priorities: set[int],
        ratio: float,
    ) -> list[PackageSection]:
        """Compress sections matching given priorities by truncating at line boundaries.

        Args:
            sections: Sections to compress.
            priorities: Priority levels to compress.
            ratio: Fraction of content to keep (0.0-1.0).

        Returns:
            Compressed sections with intact markdown formatting.
        """
        result = []
        for s in sections:
            if s.priority in priorities:
                truncated = self._truncate_at_line_boundary(s.content, ratio)
                result.append(PackageSection(
                    section_type=s.section_type,
                    heading=s.heading,
                    content=truncated,
                    priority=s.priority,
                    source_sections=s.source_sections,
                    reference_count=s.reference_count,
                ))
            else:
                result.append(s)
        return result

    def _truncate_at_line_boundary(self, content: str, ratio: float) -> str:
        """Truncate content at a line boundary to preserve markdown formatting.

        Finds the last complete line before the character limit.
        Ensures truncated content doesn't end mid-line or mid-bullet.

        Args:
            content: Text content to truncate.
            ratio: Fraction of content to keep (0.0-1.0).

        Returns:
            Truncated content ending at a complete line.
        """
        if not content:
            return content

        target_len = int(len(content) * ratio)
        if target_len >= len(content):
            return content

        # Find the last newline before the target length
        truncated = content[:target_len]
        last_newline = truncated.rfind("\n")

        if last_newline > 0:
            # Cut at the last complete line
            return content[:last_newline]

        # No newline found — return as-is (single line content)
        return truncated

    def _finalize(self, sections: list[PackageSection], original_tokens: int) -> list[PackageSection]:
        """Record compression ratio and return sections.

        Args:
            sections: Final sections.
            original_tokens: Token count before compression.

        Returns:
            The same sections.
        """
        final_tokens = self._estimate_tokens(sections)
        self.last_compression_ratio = original_tokens / max(final_tokens, 1)
        return sections
