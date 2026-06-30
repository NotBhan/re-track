"""Markdown renderer for Context Packages.

Renders structured package data as human-readable Markdown.
Independent of package assembly — can be swapped for JSON, MCP, or UI renderers.

Output format:
- Task section (always first)
- Objective section (if present)
- Repository Context (if summary provided)
- Content sections (skipped if empty)
- References (always last)
"""

import logging

from app.models.responses import PackageReference, PackageSection, RepositorySummary

logger = logging.getLogger(__name__)


class MarkdownRenderer:
    """Renders a Context Package as Markdown.

    The renderer is format-agnostic at the data level — it receives
    structured objects and produces a string. Future renderers can
    reuse the same PackageSection/PackageReference models.
    """

    def render(
        self,
        task: str,
        objective: str,
        sections: list[PackageSection],
        references: list[PackageReference],
        repository_summary: RepositorySummary | None,
    ) -> str:
        """Render a complete Context Package as Markdown.

        Args:
            task: Developer request.
            objective: Desired outcome.
            sections: Content sections (empty sections are skipped).
            references: Traceable references.
            repository_summary: Optional repository summary to include.

        Returns:
            Formatted Markdown string.
        """
        parts: list[str] = []

        # Task (always first)
        parts.append(f"# Task\n\n{task}")

        # Objective
        if objective:
            parts.append(f"# Objective\n\n{objective}")

        # Repository Context (from summary)
        if repository_summary:
            summary_md = self._render_summary(repository_summary)
            if summary_md:
                parts.append(f"# Repository Context\n\n{summary_md}")

        # Content sections (skip empty)
        for section in sections:
            if section.content.strip():
                parts.append(f"# {section.heading}\n\n{section.content}")

        # References (always last)
        if references:
            ref_lines = []
            for i, ref in enumerate(references, 1):
                ref_lines.append(
                    f"{i}. [{ref.ref_type}] `{ref.path}` (score: {ref.score:.2f})"
                )
            parts.append("# References\n\n" + "\n".join(ref_lines))

        return "\n\n---\n\n".join(parts)

    def _render_summary(self, summary: RepositorySummary) -> str:
        """Render Repository Summary as Markdown.

        Args:
            summary: Repository summary to render.

        Returns:
            Markdown representation of the summary.
        """
        parts = []

        if summary.project_purpose:
            parts.append(f"**Purpose**: {summary.project_purpose}")

        if summary.technology_stack:
            tech = summary.technology_stack
            items = []
            if tech.languages:
                items.append(f"Languages: {', '.join(tech.languages)}")
            if tech.frameworks:
                items.append(f"Frameworks: {', '.join(tech.frameworks)}")
            if tech.databases:
                items.append(f"Databases: {', '.join(tech.databases)}")
            if items:
                parts.append("**Technology**: " + " | ".join(items))

        if summary.repository_map:
            dirs = "\n".join(
                f"- `{e.path}` — {e.description}"
                for e in summary.repository_map
            )
            parts.append(f"**Repository Map**:\n{dirs}")

        if summary.architecture and summary.architecture.layers:
            layers = ", ".join(summary.architecture.layers)
            parts.append(f"**Architecture**: {summary.architecture.pattern} ({layers})")

        if summary.key_components:
            comps = "\n".join(
                f"- **{c.name}**: {c.responsibilities}"
                for c in summary.key_components[:5]
            )
            parts.append(f"**Key Components**:\n{comps}")

        return "\n\n".join(parts)
