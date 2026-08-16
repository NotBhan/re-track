"""Repository Summary generator for RE:Track (RefinedEngine Track).

Analyzes indexed repository files to extract stable, global knowledge:
project purpose, technology stack, directory structure, AST symbols (classes, functions, routes, React components),
and key architectural components while strictly respecting .gitignore patterns.

Generates a RepositorySummary after indexing completes.
"""

import ast
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from app.models.responses import (
    ArchitectureInfo,
    CallEdge,
    CallNode,
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
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
}

# Framework markers and detectors
_FRAMEWORK_MARKERS: dict[str, str] = {
    "manage.py": "Django",
    "wsgi.py": "Django",
    "asgi.py": "Django",
    "settings.py": "Django",
    "package.json": "Node.js",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "requirements.txt": "Python",
    "setup.py": "Python",
    "pyproject.toml": "Python",
    "pom.xml": "Java",
    "build.gradle": "Java/Kotlin",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "Package.swift": "Swift",
    "CMakeLists.txt": "C/C++",
    "pubspec.yaml": "Dart",
    "vite.config.ts": "Vite",
    "vite.config.js": "Vite",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "tailwind.config.js": "TailwindCSS",
    "tailwind.config.ts": "TailwindCSS",
}


class RepositorySummaryGenerator:
    """Generates a RepositorySummary with AST symbol discovery from indexed repository files."""

    def generate(self, repo_path: Path, files: list[Path]) -> RepositorySummary:
        """Generate a RepositorySummary from a repository and its files."""
        logger.info("generating repository summary | path=%s | files=%d", repo_path, len(files))

        # Filter files by gitignore patterns
        filtered_files = self._filter_ignored_files(repo_path, files)

        fingerprint = self._compute_fingerprint(filtered_files)
        rel_files = [f.relative_to(repo_path) if f.is_relative_to(repo_path) else f for f in filtered_files]

        tech_stack = self._extract_tech_stack(repo_path, rel_files)
        repo_map = self._build_repo_map(rel_files)
        architecture = self._infer_architecture(repo_path, repo_map, tech_stack.frameworks)
        components = self._extract_components(repo_path, filtered_files)
        purpose = self._infer_purpose(repo_path, repo_map, tech_stack.frameworks)
        call_nodes, call_edges = self._build_call_graph(repo_path, filtered_files)

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
            call_graph_nodes=call_nodes,
            call_graph_edges=call_edges,
        )

        logger.info(
            "repository summary generated | frameworks=%s | components=%d",
            tech_stack.frameworks,
            len(components),
        )
        return summary

    def _filter_ignored_files(self, repo_path: Path, files: list[Path]) -> list[Path]:
        """Filter files using standard ignore rules and .gitignore patterns."""
        ignored_dir_names = {
            ".git", "node_modules", "dist", "build", "target", ".venv", "venv",
            "__pycache__", ".cache", ".next", ".nuxt", ".output", "coverage",
            ".turbo", ".idea", ".vscode", "tmp", ".parcel-cache",
        }

        # Parse .gitignore if present
        gitignore_patterns = set()
        gi_file = repo_path / ".gitignore"
        if gi_file.exists():
            try:
                for line in gi_file.read_text(errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pattern = line.rstrip("/").lstrip("/")
                        if pattern:
                            gitignore_patterns.add(pattern)
            except Exception:
                pass

        valid_files = []
        for f in files:
            parts = f.parts if isinstance(f, Path) else Path(f).parts
            # Check ignored directory names
            if any(p in ignored_dir_names for p in parts):
                continue
            if any(p.startswith(".agents") or p.startswith("__") for p in parts):
                continue
            # Check gitignore patterns
            rel_str = str(f.relative_to(repo_path)) if f.is_relative_to(repo_path) else str(f)
            if any(pat in rel_str or any(pat == p for p in parts) for pat in gitignore_patterns):
                continue

            valid_files.append(f)

        return valid_files if valid_files else files

    def _compute_fingerprint(self, files: list[Path]) -> str:
        """Compute a fingerprint from file paths."""
        hasher = hashlib.sha256()
        for f in sorted(str(p) for p in files):
            hasher.update(f.encode())
        return hasher.hexdigest()[:16]

    def _extract_tech_stack(self, repo_path: Path, files: list[Path]) -> TechnologyStack:
        """Extract technologies and specific frameworks by checking file extensions, markers, and imports."""
        languages: set[str] = set()
        frameworks: set[str] = set()

        for f in files:
            ext = f.suffix.lower()
            if ext in _EXT_LANG_MAP:
                languages.add(_EXT_LANG_MAP[ext])
            if ext in (".tsx", ".jsx"):
                frameworks.add("React")

            # Check filename markers
            if f.name in _FRAMEWORK_MARKERS:
                frameworks.add(_FRAMEWORK_MARKERS[f.name])

        # Deep framework detection from manifests
        pkg_file = repo_path / "package.json"
        if pkg_file.exists():
            try:
                content = pkg_file.read_text(errors="ignore").lower()
                if "react" in content:
                    frameworks.add("React")
                if "vite" in content:
                    frameworks.add("Vite")
                if "next" in content:
                    frameworks.add("Next.js")
                if "vue" in content:
                    frameworks.add("Vue")
                if "svelte" in content:
                    frameworks.add("Svelte")
                if "tailwindcss" in content:
                    frameworks.add("TailwindCSS")
                if "zustand" in content:
                    frameworks.add("Zustand")
                if "redux" in content:
                    frameworks.add("Redux")
            except Exception:
                pass

        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text().lower()
                if "django" in content:
                    frameworks.add("Django")
                if "fastapi" in content:
                    frameworks.add("FastAPI")
                if "flask" in content:
                    frameworks.add("Flask")
                if "celery" in content:
                    frameworks.add("Celery")
            except Exception:
                pass

        # Check for Django manage.py or settings.py in tree
        if any(f.name == "manage.py" for f in files) or any("settings.py" in str(f) for f in files):
            frameworks.add("Django")

        # Check for Vite config
        if any("vite.config" in f.name for f in files):
            frameworks.add("Vite")
            frameworks.add("React")

        return TechnologyStack(
            languages=sorted(languages),
            frameworks=sorted(frameworks),
            databases=[],
            dependencies=[],
        )

    def _build_repo_map(self, files: list[Path]) -> list[DirectoryEntry]:
        """Build a hierarchical map of actual directories and key modules."""
        dirs: dict[str, list[str]] = {}
        for f in files:
            parts = f.parts
            if len(parts) > 1:
                # Top level directory
                dirs.setdefault(parts[0], []).append(str(f))
                # Depth 2 directory if part of nested package
                if len(parts) >= 3:
                    sub_key = "/".join(parts[:2])
                    dirs.setdefault(sub_key, []).append(str(f))
            else:
                dirs.setdefault(".", []).append(str(f))

        entries = []
        for dir_path, dir_files in sorted(dirs.items()):
            if dir_path.startswith(".") or "__pycache__" in dir_path:
                continue
            desc = self._describe_directory(dir_path, dir_files)
            entries.append(DirectoryEntry(path=dir_path, description=desc))
        return entries

    def _describe_directory(self, name: str, files: list[str]) -> str:
        """Generate an informative architectural description for a directory or app."""
        filenames = {Path(f).name for f in files}

        # React / Vite directory heuristics
        if name in ("src/components", "components"):
            return f"React UI Components ({len(files)} component files)"
        if name in ("src/pages", "src/views", "pages", "views"):
            return f"Page Views & Routing Layouts ({len(files)} pages)"
        if name in ("src/stores", "stores", "src/hooks", "hooks"):
            return f"Client State Stores & Hooks ({len(files)} state modules)"
        if name in ("src/lib", "lib", "src/utils", "utils"):
            return f"Utility functions & Client API bridges ({len(files)} files)"
        if name in ("src/assets", "assets", "public"):
            return f"Static assets, icons & public files ({len(files)} assets)"
        if name == "src-tauri":
            return f"Tauri Rust native core & IPC runtime ({len(files)} files)"

        # Django App Detector
        if any(f in filenames for f in ("models.py", "views.py", "urls.py", "admin.py", "apps.py")):
            has_models = "models.py" in filenames
            has_views = "views.py" in filenames
            features = []
            if has_models:
                features.append("ORM Models")
            if has_views:
                features.append("Views/Handlers")
            feat_str = f" ({', '.join(features)})" if features else ""
            return f"Django Application module{feat_str} — {len(files)} files"

        # Standard known folder descriptions
        if name in ("tests", "test"):
            return f"Test suite ({len(files)} test files)"
        if name == "docs":
            return f"Documentation ({len(files)} docs)"
        if name == "scripts":
            return f"Development scripts ({len(files)} files)"
        if name == "templates":
            return f"HTML Presentation Templates ({len(files)} templates)"
        if name == "static":
            return f"Static assets (CSS, JS, media) ({len(files)} files)"
        if name == "migrations":
            return f"Database schema migrations ({len(files)} migrations)"

        if "services" in name:
            return f"Service layer & business logic ({len(files)} services)"
        if "api" in name or "routers" in name:
            return f"API endpoints & routes ({len(files)} files)"
        if "models" in name:
            return f"Data models & schemas ({len(files)} models)"

        return f"Module ({len(files)} files)"

    def _infer_architecture(
        self, repo_path: Path, repo_map: list[DirectoryEntry], frameworks: list[str]
    ) -> ArchitectureInfo:
        """Infer architecture from framework patterns and directory structure."""
        dir_names = {e.path for e in repo_map}
        layers = []

        if "Django" in frameworks:
            layers.append("Django MVC / MTV")
            if any(e.path == "templates" for e in repo_map):
                layers.append("Django Templates")
            if any("api" in e.path for e in repo_map):
                layers.append("REST API Layer")
            pattern = "monolith" if len(layers) <= 2 else "layered"
        elif "React" in frameworks or "Vite" in frameworks or "Next.js" in frameworks:
            layers.append("React UI Component Tree")
            if any("stores" in e.path for e in repo_map):
                layers.append("Zustand / Reactive State")
            if any("api" in e.path or "lib" in e.path for e in repo_map):
                layers.append("API & Client Services")
            if any("src-tauri" in e.path for e in repo_map):
                layers.append("Tauri Desktop IPC")
            pattern = "layered" if len(layers) > 1 else "monolith"
        elif "FastAPI" in frameworks:
            layers.append("FastAPI Async Endpoints")
            layers.append("Pydantic Schema & Services")
            pattern = "layered"
        else:
            if any(d in dir_names for d in ("backend", "server")):
                layers.append("Backend")
            if any(d in dir_names for d in ("frontend", "src", "client")):
                layers.append("Frontend")
            pattern = "layered" if len(layers) > 1 else "monolith"

        return ArchitectureInfo(
            pattern=pattern,
            layers=layers,
            boundaries=[d for d in dir_names if "/" in d][:10],
            major_flows=[],
        )

    def _extract_components(self, repo_path: Path, files: list[Path]) -> list[ComponentInfo]:
        """Extract concrete AST classes, models, and React components across the codebase."""
        components = []

        # 1. Look for Python files with AST classes and routes
        py_files = [f for f in files if f.suffix.lower() == ".py" and not f.name.startswith(".")]
        for pf in py_files[:25]:
            try:
                code = pf.read_text(errors="ignore")
                parsed = ast.parse(code)
                for node in parsed.body:
                    if isinstance(node, ast.ClassDef):
                        rel_p = pf.relative_to(repo_path) if pf.is_relative_to(repo_path) else pf
                        base_names = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]
                        desc = f"Class {node.name}"
                        if any("model" in b.lower() for b in base_names):
                            desc = f"Django Model (`{node.name}`) in `{rel_p}`"
                        elif any("view" in b.lower() for b in base_names):
                            desc = f"View Controller (`{node.name}`) in `{rel_p}`"
                        elif any("serializer" in b.lower() for b in base_names):
                            desc = f"REST Serializer (`{node.name}`) in `{rel_p}`"
                        else:
                            desc = f"Class `{node.name}` in `{rel_p}`"

                        components.append(
                            ComponentInfo(
                                name=node.name,
                                responsibilities=desc,
                                relationships=base_names,
                            )
                        )
                        if len(components) >= 20:
                            break
            except Exception:
                continue

        # 2. Look for React / TypeScript / Vite components (export function / class / const Component)
        ts_files = [f for f in files if f.suffix.lower() in (".tsx", ".jsx", ".ts", ".js") and not f.name.startswith(".")]
        if len(components) < 10 and ts_files:
            react_component_regex = re.compile(r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9_]+)")
            for tf in ts_files[:30]:
                try:
                    text = tf.read_text(errors="ignore")
                    matches = react_component_regex.findall(text)
                    rel_p = tf.relative_to(repo_path) if tf.is_relative_to(repo_path) else tf
                    for comp_name in matches:
                        components.append(
                            ComponentInfo(
                                name=comp_name,
                                responsibilities=f"React Component (`{comp_name}`) in `{rel_p}`",
                                relationships=["React"],
                            )
                        )
                        if len(components) >= 20:
                            break
                except Exception:
                    continue

        # 3. Fallback: extract major files
        if len(components) < 5:
            for f in files:
                if f.suffix.lower() in (".py", ".ts", ".tsx", ".js") and not f.name.startswith("."):
                    rel_p = f.relative_to(repo_path) if f.is_relative_to(repo_path) else f
                    name = f.stem.replace("_", " ").replace("-", " ").title()
                    components.append(
                        ComponentInfo(
                            name=name,
                            responsibilities=f"Module in `{rel_p}`",
                            relationships=[],
                        )
                    )
                    if len(components) >= 15:
                        break

        return components

    def _infer_purpose(
        self, repo_path: Path, repo_map: list[DirectoryEntry], frameworks: list[str]
    ) -> str:
        """Infer project purpose from README or framework architecture."""
        readme = repo_path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text(errors="replace")[:500]
                lines = content.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("---") and not line.startswith("!"):
                        return line[:200]
            except Exception:
                pass

        fw_str = f" built on {', '.join(frameworks)}" if frameworks else ""
        top_apps = [e.path for e in repo_map if "/" not in e.path and not e.path.startswith(".")]
        return f"{repo_path.name}{fw_str} with core modules: {', '.join(top_apps[:6])}"

    def _build_call_graph(
        self, repo_path: Path, files: list[Path]
    ) -> tuple[list[CallNode], list[CallEdge]]:
        """Build a real function/class/component call graph from Python AST and TS/React imports.

        Python: Visits each function/method body for ast.Call nodes → directed call edges.
        React/TS: Parses import statements and JSX usage → component-level dependency edges.

        Returns:
            (nodes, edges) — capped at 80 nodes / 200 edges for UI performance.
        """
        nodes: dict[str, CallNode] = {}
        edges: list[CallEdge] = []

        MAX_NODES = 80
        MAX_EDGES = 200

        # ── 1. Python AST walk ──────────────────────────────────────────────────
        py_files = [
            f for f in files
            if f.suffix == ".py" and not f.name.startswith(".")
            and "migration" not in str(f)
            and "__pycache__" not in str(f)
        ]

        for pf in py_files[:20]:
            try:
                code = pf.read_text(errors="ignore")
                tree = ast.parse(code)
                rel = str(pf.relative_to(repo_path) if pf.is_relative_to(repo_path) else pf)
                module_prefix = rel.replace("/", ".").replace(".py", "")

                class _CallWalker(ast.NodeVisitor):
                    """Walks a Python AST collecting defs and call edges."""

                    def __init__(self_inner) -> None:
                        self_inner.scope_stack: list[str] = []

                    def _scope_id(self_inner) -> str:
                        return ".".join([module_prefix] + self_inner.scope_stack) if self_inner.scope_stack else module_prefix

                    def visit_ClassDef(self_inner, node: ast.ClassDef) -> None:
                        nid = f"{module_prefix}.{node.name}"
                        label = node.name
                        if nid not in nodes and len(nodes) < MAX_NODES:
                            nodes[nid] = CallNode(id=nid, label=label, file=rel, kind="class", line=node.lineno)
                        # Inheritance edges
                        for base in node.bases:
                            base_name = getattr(base, "id", getattr(base, "attr", None))
                            if base_name and len(edges) < MAX_EDGES:
                                edges.append(CallEdge(source=nid, target=base_name, kind="inherits"))
                        self_inner.scope_stack.append(node.name)
                        self_inner.generic_visit(node)
                        self_inner.scope_stack.pop()

                    def visit_FunctionDef(self_inner, node: ast.FunctionDef) -> None:
                        self_inner._visit_funcdef(node)

                    def visit_AsyncFunctionDef(self_inner, node: ast.AsyncFunctionDef) -> None:
                        self_inner._visit_funcdef(node)

                    def _visit_funcdef(self_inner, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                        parent_scope = self_inner._scope_id()
                        kind = "method" if self_inner.scope_stack else "function"
                        nid = f"{parent_scope}.{node.name}"
                        label = f"{self_inner.scope_stack[-1]}.{node.name}" if self_inner.scope_stack else node.name
                        if nid not in nodes and len(nodes) < MAX_NODES:
                            nodes[nid] = CallNode(id=nid, label=label, file=rel, kind=kind, line=node.lineno)

                        # Walk body for call expressions
                        self_inner.scope_stack.append(node.name)
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                callee = None
                                if isinstance(child.func, ast.Name):
                                    callee = child.func.id
                                elif isinstance(child.func, ast.Attribute):
                                    callee = child.func.attr
                                if callee and len(edges) < MAX_EDGES:
                                    edges.append(CallEdge(source=nid, target=callee, kind="calls"))
                        self_inner.scope_stack.pop()

                walker = _CallWalker()
                walker.visit(tree)
            except Exception:
                continue

        # ── 2. React / TypeScript import chain ─────────────────────────────────
        ts_files = [
            f for f in files
            if f.suffix.lower() in (".tsx", ".jsx", ".ts", ".js")
            and not f.name.startswith(".")
            and "node_modules" not in str(f)
        ]

        import_re = re.compile(r"import\s+(?:\{[^}]*\}|[\w*]+)\s+from\s+['\"]([^'\"]+)['\"]")
        export_comp_re = re.compile(r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9_]+)")
        jsx_usage_re = re.compile(r"<([A-Z][A-Za-z0-9_]+)[\s/>]")

        for tf in ts_files[:25]:
            try:
                text = tf.read_text(errors="ignore")
                rel = str(tf.relative_to(repo_path) if tf.is_relative_to(repo_path) else tf)

                # Register exported components as nodes
                for comp_name in export_comp_re.findall(text):
                    nid = f"{rel}#{comp_name}"
                    if nid not in nodes and len(nodes) < MAX_NODES:
                        nodes[nid] = CallNode(id=nid, label=comp_name, file=rel, kind="component", line=0)

                # Import edges: this file → imported module
                for imp_path in import_re.findall(text):
                    if not imp_path.startswith("."):
                        continue  # skip external packages
                    target_id = imp_path.lstrip("./")
                    # Find matching node for the imported path
                    matched = next(
                        (n for n in nodes.values() if target_id in n.file or target_id == n.label),
                        None,
                    )
                    if matched:
                        # Edge from first component of this file → matched
                        src_comps = export_comp_re.findall(text)
                        if src_comps and len(edges) < MAX_EDGES:
                            src_id = f"{rel}#{src_comps[0]}"
                            if src_id in nodes:
                                edges.append(CallEdge(source=src_id, target=matched.id, kind="imports"))

                # JSX renders edges: component uses another component
                rendered = jsx_usage_re.findall(text)
                src_comps = export_comp_re.findall(text)
                if src_comps:
                    src_id = f"{rel}#{src_comps[0]}"
                    for used in rendered:
                        target = next((n for n in nodes.values() if n.label == used), None)
                        if target and src_id in nodes and len(edges) < MAX_EDGES:
                            edges.append(CallEdge(source=src_id, target=target.id, kind="renders"))
            except Exception:
                continue

        # Deduplicate edges
        seen_edges: set[tuple[str, str, str]] = set()
        deduped_edges = []
        for e in edges:
            key = (e.source, e.target, e.kind)
            if key not in seen_edges:
                seen_edges.add(key)
                deduped_edges.append(e)

        logger.info(
            "call graph built | nodes=%d | edges=%d",
            len(nodes),
            len(deduped_edges),
        )
        return list(nodes.values()), deduped_edges
