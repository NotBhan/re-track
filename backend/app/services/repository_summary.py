"""Repository Summary generator for AndesContext.

Analyzes indexed repository files to extract stable, global knowledge:
project purpose, technology stack, directory structure, and key components.

Generates a RepositorySummary after indexing completes.
"""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.models.responses import (
    ArchitectureInfo,
    ComponentInfo,
    DirectoryEntry,
    RepositorySummary,
    TechnologyStack,
)

logger = logging.getLogger(__name__)

# Extension to language mapping
_EXT_LANG_MAP: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
}

# Extension to framework hints
_EXT_FRAMEWORK_MAP: dict[str, str] = {
    ".tsx": "React",
    ".jsx": "React",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


class RepositorySummaryGenerator:
    """Generates a RepositorySummary from indexed repository files."""

    def generate(self, repo_path: Path, files: list[Path]) -> RepositorySummary:
        """Generate a RepositorySummary from a repository and its files.

        Args:
            repo_path: Root directory of the repository.
            files: List of indexed file paths.

        Returns:
            RepositorySummary with extracted stable facts.
        """
        logger.info("generating repository summary | path=%s | files=%d", repo_path, len(files))

        fingerprint = self._compute_fingerprint(files)
        rel_files = [f.relative_to(repo_path) if f.is_relative_to(repo_path) else f for f in files]

        tech_stack = self._extract_tech_stack(rel_files)
        repo_map = self._build_repo_map(rel_files)
        architecture = self._infer_architecture(repo_map)
        components = self._extract_components(rel_files)
        purpose = self._infer_purpose(repo_path, repo_map)

        summary = RepositorySummary(
            version="1.0",
            repository_fingerprint=fingerprint,
            generated_at=datetime.now(timezone.utc).isoformat(),
            indexed_commit=None,
            project_purpose=purpose,
            technology_stack=tech_stack,
            repository_map=repo_map,
            architecture=architecture,
            key_components=components,
            entry_points=[],
            public_apis=[],
            coding_conventions=None,
            domain_vocabulary={},
        )

        logger.info(
            "repository summary generated | languages=%d | dirs=%d | components=%d",
            len(tech_stack.languages),
            len(repo_map),
            len(components),
        )
        return summary

    def _compute_fingerprint(self, files: list[Path]) -> str:
        """Compute a fingerprint from file paths."""
        hasher = hashlib.sha256()
        for f in sorted(str(p) for p in files):
            hasher.update(f.encode())
        return hasher.hexdigest()[:16]

    def _extract_tech_stack(self, files: list[Path]) -> TechnologyStack:
        """Extract technologies from file extensions."""
        languages: set[str] = set()
        frameworks: set[str] = set()

        for f in files:
            ext = f.suffix.lower()
            if ext in _EXT_LANG_MAP:
                languages.add(_EXT_LANG_MAP[ext])
            if ext in _EXT_FRAMEWORK_MAP:
                frameworks.add(_EXT_FRAMEWORK_MAP[ext])

        return TechnologyStack(
            languages=sorted(languages),
            frameworks=sorted(frameworks),
            databases=[],
            dependencies=[],
        )

    def _build_repo_map(self, files: list[Path]) -> list[DirectoryEntry]:
        """Build a map of top-level directories."""
        dirs: dict[str, list[str]] = {}
        for f in files:
            parts = f.parts
            if len(parts) > 1:
                top_dir = parts[0]
                dirs.setdefault(top_dir, []).append(str(f))
            else:
                dirs.setdefault(".", []).append(str(f))

        entries = []
        for dir_path, dir_files in sorted(dirs.items()):
            desc = self._describe_directory(dir_path, dir_files)
            entries.append(DirectoryEntry(path=dir_path, description=desc))
        return entries

    def _describe_directory(self, name: str, files: list[str]) -> str:
        """Generate a one-line description for a directory."""
        exts = set()
        for f in files:
            p = Path(f)
            if p.suffix:
                exts.add(p.suffix.lower())

        if name in ("tests", "test"):
            return "Test suite"
        if name == "docs":
            return "Documentation"
        if name == "scripts":
            return "Development scripts"
        if name == ".github":
            return "CI/CD configuration"
        if ".py" in exts:
            return f"Python module ({len(files)} files)"
        if ".ts" in exts or ".tsx" in exts:
            return f"TypeScript module ({len(files)} files)"
        return f"Source directory ({len(files)} files)"

    def _infer_architecture(self, repo_map: list[DirectoryEntry]) -> ArchitectureInfo:
        """Infer architecture from directory structure."""
        dir_names = {e.path for e in repo_map}
        layers = []
        if "backend" in dir_names or "server" in dir_names:
            layers.append("Backend")
        if "frontend" in dir_names or "src" in dir_names:
            layers.append("Frontend")
        if "tests" in dir_names:
            layers.append("Tests")

        return ArchitectureInfo(
            pattern="layered" if len(layers) > 1 else "monolith",
            layers=layers,
            boundaries=[],
            major_flows=[],
        )

    def _extract_components(self, files: list[Path]) -> list[ComponentInfo]:
        """Extract key components from file structure."""
        components = []
        service_files = [f for f in files if "service" in f.name.lower()]
        for sf in service_files[:10]:
            name = sf.stem.replace("_", " ").title()
            components.append(ComponentInfo(
                name=name,
                responsibilities=f"Defined in {sf}",
                relationships=[],
            ))
        return components

    def _infer_purpose(self, repo_path: Path, repo_map: list[DirectoryEntry]) -> str:
        """Infer project purpose from README or directory structure."""
        readme = repo_path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text(errors="replace")[:500]
                lines = content.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("---"):
                        return line[:200]
            except Exception:
                pass

        dir_names = [e.path for e in repo_map]
        return f"Software project with directories: {', '.join(dir_names[:5])}"
