"""Lightweight reference resolution for the MVP pipeline.

Formats existing Cognee reference metadata into structured citations.
Each reference includes:
- Type: file | symbol | memory_node | documentation | directory
- Path: Repository-relative path or memory identifier
- Section: Where in the source this fact appears
- Score: Relevance score from retrieval
- Provenance chain: fact → memory node → chunk → document → repository path

Interface designed for future upgrade to symbol-level and AST-aware
resolution without pipeline redesign.
"""

import logging
import re

from app.models.responses import PackageReference, RecallResult

logger = logging.getLogger(__name__)


class ReferenceResolver:
    """Formats Cognee references into structured citations.

    Lightweight MVP implementation that classifies references as
    file or memory types based on metadata and text patterns.
    """

    def resolve(self, results: list[RecallResult]) -> list[PackageReference]:
        """Resolve recall results into package references.

        Args:
            results: Recall results to format.

        Returns:
            List of PackageReference with provenance chains.
        """
        refs = []
        for r in results:
            ref = self._resolve_one(r)
            if ref:
                refs.append(ref)
        return refs

    def _resolve_one(self, result: RecallResult) -> PackageReference | None:
        """Resolve a single recall result into a reference.

        Args:
            result: Recall result to resolve.

        Returns:
            PackageReference or None if result should be skipped.
        """
        text = result.text.strip()
        if not text:
            return None

        kind = result.kind.lower() if result.kind else ""

        # Classify reference type
        if kind == "file":
            ref_type = "file"
            path = self._extract_path(text) or text
        elif self._looks_like_path(text):
            ref_type = "file"
            path = text
        else:
            ref_type = "memory"
            path = text[:100]

        return PackageReference(
            ref_type=ref_type,
            path=path,
            section=None,
            score=result.score if result.score is not None else 0.0,
            provenance=[
                f"recall:{result.dataset_name}",
                f"kind:{kind}",
            ],
        )

    def _extract_path(self, text: str) -> str | None:
        """Try to extract a file path from memory text.

        Args:
            text: Memory text to search.

        Returns:
            Extracted path or None.
        """
        match = re.search(r"([/\w.-]+\.\w+)", text)
        return match.group(1) if match else None

    def _looks_like_path(self, text: str) -> bool:
        """Check if text looks like a file path.

        Args:
            text: Text to check.

        Returns:
            True if text contains a path-like pattern.
        """
        return bool(re.search(r"[/\w.-]+\.\w+", text))
