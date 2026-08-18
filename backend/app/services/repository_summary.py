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
        call_nodes, call_edges, call_status, call_error = self._build_call_graph(repo_path, filtered_files)

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
            call_graph_status=call_status,
            call_graph_error=call_error,
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
    ) -> tuple[list[CallNode], list[CallEdge], str, str | None]:
        """Build a deterministic function/class/component call graph from Python AST and TS/React imports.

        Adheres strictly to the invariant:
        Static Certainty > Graph Completeness.
        Every CallEdge(source, target) MUST satisfy source in nodes and target in nodes.
        Unresolved, dynamic, shadowed, or ambiguous symbols produce NO internal edge.

        Returns:
            (nodes, edges, status, error) where status is:
            'analyzed' | 'zero_edges' | 'failed'
        """
        nodes: dict[str, CallNode] = {}
        edges: list[CallEdge] = []
        status = "analyzed"
        error_msg: str | None = None

        MAX_NODES = 120
        MAX_EDGES = 300

        # Standard Python builtins to ignore as external
        BUILTIN_FUNCS = frozenset({
            "print", "len", "int", "str", "float", "bool", "dict", "set", "list",
            "tuple", "range", "enumerate", "isinstance", "issubclass", "getattr",
            "setattr", "hasattr", "delattr", "super", "open", "type", "zip",
            "sum", "min", "max", "abs", "round", "all", "any", "id", "repr",
            "dir", "vars", "callable", "map", "filter", "sorted", "next", "iter",
            "help", "eval", "exec", "format", "bytes", "bytearray", "memoryview",
            "slice", "object", "classmethod", "staticmethod", "property",
            "breakpoint", "pow", "divmod", "hash", "input", "bin", "oct", "hex",
            "chr", "ord", "append", "extend", "insert", "remove", "pop", "clear",
            "index", "count", "sort", "reverse", "copy", "update", "keys",
            "values", "items", "get", "setdefault", "strip", "split", "join",
            "replace", "lower", "upper", "startswith", "endswith", "find",
            "rfind", "encode", "decode", "read", "write", "close", "seek",
            "tell", "flush", "log", "debug", "info", "warning", "error",
            "critical", "exception",
        })

        try:
            # ─────────────────────────────────────────────────────────────────
            def _not_hidden(p_file: Path) -> bool:
                try:
                    rel_p = p_file.relative_to(repo_path)
                    return not any(part.startswith(".") for part in rel_p.parts)
                except Exception:
                    return not p_file.name.startswith(".")

            py_files = [
                f for f in files
                if f.suffix == ".py" and not f.name.startswith(".")
                and "migration" not in str(f)
                and "__pycache__" not in str(f)
                and _not_hidden(f)
            ]

            py_trees: dict[str, tuple[ast.AST, str, Path]] = {}
            # Symbol indexes for Python
            label_to_py_nodes: dict[str, list[CallNode]] = {}
            class_methods: dict[str, set[str]] = {}
            class_bases: dict[str, list[str]] = {}

            # --- Python Pass 1: Global Symbol Table Discovery ---
            for pf in py_files[:40]:
                try:
                    code = pf.read_text(errors="ignore")
                    tree = ast.parse(code)
                    rel = str(pf.relative_to(repo_path) if pf.is_relative_to(repo_path) else pf)
                    module_prefix = rel.replace("/", ".").replace(".py", "").removesuffix(".__init__")
                    py_trees[rel] = (tree, module_prefix, pf)

                    for stmt in tree.body:
                        if isinstance(stmt, ast.ClassDef):
                            class_nid = f"{module_prefix}.{stmt.name}" if module_prefix else stmt.name
                            if class_nid not in nodes and len(nodes) < MAX_NODES:
                                node = CallNode(id=class_nid, label=stmt.name, file=rel, kind="class", line=stmt.lineno)
                                nodes[class_nid] = node
                                label_to_py_nodes.setdefault(stmt.name, []).append(node)

                            methods_set = set()
                            bases_list = []
                            for base in stmt.bases:
                                base_name = getattr(base, "id", getattr(base, "attr", None))
                                if base_name:
                                    bases_list.append(base_name)
                            class_bases[class_nid] = bases_list

                            for item in stmt.body:
                                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                    methods_set.add(item.name)
                                    method_nid = f"{class_nid}.{item.name}"
                                    method_label = f"{stmt.name}.{item.name}"
                                    if method_nid not in nodes and len(nodes) < MAX_NODES:
                                        mnode = CallNode(id=method_nid, label=method_label, file=rel, kind="method", line=item.lineno)
                                        nodes[method_nid] = mnode
                                        label_to_py_nodes.setdefault(item.name, []).append(mnode)
                                        label_to_py_nodes.setdefault(method_label, []).append(mnode)
                            class_methods[class_nid] = methods_set

                        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            func_nid = f"{module_prefix}.{stmt.name}" if module_prefix else stmt.name
                            if func_nid not in nodes and len(nodes) < MAX_NODES:
                                fnode = CallNode(id=func_nid, label=stmt.name, file=rel, kind="function", line=stmt.lineno)
                                nodes[func_nid] = fnode
                                label_to_py_nodes.setdefault(stmt.name, []).append(fnode)
                except Exception:
                    continue

            # --- Python Pass 2: Deterministic Import & Call Resolution ---
            for rel, (tree, module_prefix, pf) in py_trees.items():
                # Build per-file import map: alias/name -> full node_id or module_prefix
                import_map: dict[str, str] = {}

                for stmt in tree.body:
                    if isinstance(stmt, ast.Import):
                        for alias in stmt.names:
                            asname = alias.asname or alias.name
                            import_map[asname] = alias.name
                    elif isinstance(stmt, ast.ImportFrom):
                        mod = stmt.module or ""
                        if stmt.level > 0:
                            # Relative import resolution
                            parts = module_prefix.split(".")
                            base_parts = parts[:-stmt.level] if len(parts) >= stmt.level else []
                            if mod:
                                base_parts.append(mod)
                            resolved_mod = ".".join(base_parts)
                        else:
                            resolved_mod = mod

                        for alias in stmt.names:
                            asname = alias.asname or alias.name
                            full_target = f"{resolved_mod}.{alias.name}" if resolved_mod else alias.name
                            import_map[asname] = full_target

                # Walk AST to extract calls & class inheritance
                class _PyCallResolver(ast.NodeVisitor):
                    def __init__(self_inner) -> None:
                        self_inner.current_class: str | None = None
                        self_inner.current_func: str | None = None
                        self_inner.current_func_nid: str | None = None
                        self_inner.local_scope: set[str] = set()

                    def visit_ClassDef(self_inner, node: ast.ClassDef) -> None:
                        class_nid = f"{module_prefix}.{node.name}" if module_prefix else node.name
                        # 1. Inheritance edges
                        for base in node.bases:
                            base_name = getattr(base, "id", getattr(base, "attr", None))
                            if base_name:
                                target_id = None
                                if base_name in import_map and import_map[base_name] in nodes:
                                    target_id = import_map[base_name]
                                elif f"{module_prefix}.{base_name}" in nodes:
                                    target_id = f"{module_prefix}.{base_name}"
                                elif base_name in label_to_py_nodes and len(label_to_py_nodes[base_name]) == 1:
                                    target_id = label_to_py_nodes[base_name][0].id

                                if target_id and target_id in nodes and len(edges) < MAX_EDGES:
                                    edges.append(CallEdge(source=class_nid, target=target_id, kind="inherits"))

                        old_class = self_inner.current_class
                        self_inner.current_class = class_nid
                        self_inner.generic_visit(node)
                        self_inner.current_class = old_class

                    def visit_FunctionDef(self_inner, node: ast.FunctionDef) -> None:
                        self_inner._visit_func(node)

                    def visit_AsyncFunctionDef(self_inner, node: ast.AsyncFunctionDef) -> None:
                        self_inner._visit_func(node)

                    def _visit_func(self_inner, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                        if self_inner.current_class:
                            func_nid = f"{self_inner.current_class}.{node.name}"
                        else:
                            func_nid = f"{module_prefix}.{node.name}" if module_prefix else node.name

                        old_func = self_inner.current_func
                        old_nid = self_inner.current_func_nid
                        old_scope = set(self_inner.local_scope)

                        self_inner.current_func = node.name
                        self_inner.current_func_nid = func_nid

                        # Track local scope: parameters and assigned variables
                        local_vars = set()
                        for arg in node.args.args + getattr(node.args, "kwonlyargs", []) + getattr(node.args, "posonlyargs", []):
                            local_vars.add(arg.arg)
                        if node.args.vararg:
                            local_vars.add(node.args.vararg.arg)
                        if node.args.kwarg:
                            local_vars.add(node.args.kwarg.arg)

                        for child in ast.walk(node):
                            if isinstance(child, ast.Assign):
                                for target in child.targets:
                                    if isinstance(target, ast.Name):
                                        local_vars.add(target.id)
                            elif isinstance(child, (ast.AugAssign, ast.AnnAssign)):
                                if isinstance(child.target, ast.Name):
                                    local_vars.add(child.target.id)
                            elif isinstance(child, ast.For):
                                if isinstance(child.target, ast.Name):
                                    local_vars.add(child.target.id)

                        self_inner.local_scope = local_vars

                        # Walk body for calls
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                target_id = None

                                # Case A: self.method()
                                if isinstance(child.func, ast.Attribute) and isinstance(child.func.value, ast.Name):
                                    if child.func.value.id == "self" and self_inner.current_class:
                                        m_name = child.func.attr
                                        if m_name in class_methods.get(self_inner.current_class, set()):
                                            target_id = f"{self_inner.current_class}.{m_name}"
                                    elif child.func.value.id in import_map:
                                        # module.function() or module.Class()
                                        mod_target = import_map[child.func.value.id]
                                        candidate = f"{mod_target}.{child.func.attr}"
                                        if candidate in nodes:
                                            target_id = candidate

                                # Case B: bare function call func()
                                elif isinstance(child.func, ast.Name):
                                    fname = child.func.id
                                    # Static certainty rule: parameters / shadowed local variables produce UNRESOLVED
                                    if fname not in self_inner.local_scope and fname not in BUILTIN_FUNCS:
                                        if fname in import_map and import_map[fname] in nodes:
                                            target_id = import_map[fname]
                                        elif f"{module_prefix}.{fname}" in nodes:
                                            target_id = f"{module_prefix}.{fname}"
                                        elif fname in label_to_py_nodes:
                                            if len(label_to_py_nodes[fname]) == 1:
                                                # Exactly one unique match across the entire codebase
                                                target_id = label_to_py_nodes[fname][0].id
                                            # Else: ambiguous (multiple same-name symbols) -> UNRESOLVED

                                if target_id and target_id in nodes and func_nid in nodes and target_id != func_nid and len(edges) < MAX_EDGES:
                                    edges.append(CallEdge(source=func_nid, target=target_id, kind="calls"))

                        self_inner.current_func = old_func
                        self_inner.current_func_nid = old_nid
                        self_inner.local_scope = old_scope

                resolver = _PyCallResolver()
                resolver.visit(tree)

            # ─────────────────────────────────────────────────────────────────
            # 2. TYPESCRIPT / REACT / NEXT.JS DETERMINISTIC RESOLVER
            # ─────────────────────────────────────────────────────────────────
            ts_files = [
                f for f in files
                if f.suffix.lower() in (".tsx", ".jsx", ".ts", ".js")
                and not f.name.startswith(".")
                and "node_modules" not in str(f)
                and _not_hidden(f)
            ]

            import_re = re.compile(r"import\s+(?:\{([^}]+)\}|([A-Za-z0-9_]+)|\*\s+as\s+([A-Za-z0-9_]+))\s+from\s+['\"]([^'\"]+)['\"]")
            export_comp_re = re.compile(r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9_]+)")
            export_named_re = re.compile(r"export\s+\{([^}]+)\}")
            jsx_usage_re = re.compile(r"<([A-Z][A-Za-z0-9_]+)(?:[\s/>]|\.[A-Za-z0-9_]+)")

            file_exports: dict[str, dict[str, str]] = {}
            file_to_ts_nodes: dict[str, list[CallNode]] = {}
            label_to_ts_nodes: dict[str, list[CallNode]] = {}
            ts_file_texts: dict[str, tuple[str, Path]] = {}

            # --- TS Pass 1: Component & Module Discovery ---
            for tf in ts_files[:40]:
                try:
                    text = tf.read_text(errors="ignore")
                    rel = str(tf.relative_to(repo_path) if tf.is_relative_to(repo_path) else tf)
                    ts_file_texts[rel] = (text, tf)
                    file_exports[rel] = {}

                    # Match exported named functions / components
                    for comp_name in export_comp_re.findall(text):
                        nid = f"{rel}#{comp_name}"
                        if nid not in nodes and len(nodes) < MAX_NODES:
                            node = CallNode(id=nid, label=comp_name, file=rel, kind="component", line=0)
                            nodes[nid] = node
                            file_exports[rel][comp_name] = nid
                            file_to_ts_nodes.setdefault(rel, []).append(node)
                            label_to_ts_nodes.setdefault(comp_name, []).append(node)

                    # Match export { A, B as C }
                    for named_exports in export_named_re.findall(text):
                        for part in named_exports.split(","):
                            clean_part = part.strip()
                            if not clean_part:
                                continue
                            exp_name = clean_part.split(" as ")[-1].strip()
                            nid = f"{rel}#{exp_name}"
                            if nid not in nodes and len(nodes) < MAX_NODES:
                                node = CallNode(id=nid, label=exp_name, file=rel, kind="component", line=0)
                                nodes[nid] = node
                                file_exports[rel][exp_name] = nid
                                file_to_ts_nodes.setdefault(rel, []).append(node)
                                label_to_ts_nodes.setdefault(exp_name, []).append(node)

                    # Next.js page/layout fallback
                    if not file_exports[rel] and tf.name in ("page.tsx", "page.jsx", "layout.tsx", "layout.jsx", "route.ts"):
                        page_label = tf.parent.name.title() if tf.parent.name else "Root"
                        if tf.name.startswith("layout"):
                            page_label += "Layout"
                        nid = f"{rel}#{page_label}"
                        if nid not in nodes and len(nodes) < MAX_NODES:
                            node = CallNode(id=nid, label=page_label, file=rel, kind="component", line=0)
                            nodes[nid] = node
                            file_exports[rel]["default"] = nid
                            file_exports[rel][page_label] = nid
                            file_to_ts_nodes.setdefault(rel, []).append(node)
                            label_to_ts_nodes.setdefault(page_label, []).append(node)
                except Exception:
                    continue

            # --- TS Pass 2: Deterministic Imports & JSX Renders ---
            for rel, (text, tf) in ts_file_texts.items():
                src_nodes = file_to_ts_nodes.get(rel, [])
                if not src_nodes:
                    continue
                src_id = src_nodes[0].id

                local_import_table: dict[str, str] = {}

                # 1. Imports
                for named, def_import, star_import, imp_path in import_re.findall(text):
                    # Check internal path aliases and relative imports
                    is_internal = imp_path.startswith(".") or imp_path.startswith("@/") or imp_path.startswith("~/")
                    if not is_internal:
                        continue

                    # Try to resolve path on disk
                    clean_path = imp_path.lstrip("./").lstrip("@/").lstrip("~/")
                    target_rel_candidates = [
                        clean_path,
                        f"src/{clean_path}",
                        f"app/{clean_path}",
                        f"{clean_path}.tsx",
                        f"{clean_path}.ts",
                        f"{clean_path}.jsx",
                        f"{clean_path}.js",
                        f"{clean_path}/index.tsx",
                        f"{clean_path}/index.ts",
                        f"src/{clean_path}.tsx",
                        f"src/{clean_path}.ts",
                    ]

                    matched_target_rel = next((c for c in target_rel_candidates if c in file_exports), None)

                    # Extract imported symbol names
                    symbols_to_resolve: list[tuple[str, str]] = []  # (imported_name, local_alias)
                    if named:
                        for item in named.split(","):
                            item = item.strip()
                            if " as " in item:
                                orig, alias = item.split(" as ")
                                symbols_to_resolve.append((orig.strip(), alias.strip()))
                            elif item:
                                symbols_to_resolve.append((item, item))
                    if def_import:
                        symbols_to_resolve.append(("default", def_import.strip()))
                        symbols_to_resolve.append((def_import.strip(), def_import.strip()))
                    if star_import:
                        symbols_to_resolve.append(("*", star_import.strip()))

                    for orig_sym, local_alias in symbols_to_resolve:
                        target_id = None
                        if matched_target_rel:
                            exports = file_exports[matched_target_rel]
                            if orig_sym in exports:
                                target_id = exports[orig_sym]
                            elif "default" in exports and orig_sym == "default":
                                target_id = exports["default"]
                            elif len(exports) == 1:
                                target_id = list(exports.values())[0]

                        # Fallback: Unique match across codebase
                        if not target_id and local_alias in label_to_ts_nodes:
                            if len(label_to_ts_nodes[local_alias]) == 1:
                                target_id = label_to_ts_nodes[local_alias][0].id

                        if target_id and target_id in nodes and target_id != src_id:
                            local_import_table[local_alias] = target_id
                            if len(edges) < MAX_EDGES:
                                edges.append(CallEdge(source=src_id, target=target_id, kind="imports"))

                # 2. JSX Renders
                for used_tag in jsx_usage_re.findall(text):
                    target_id = None
                    if used_tag in local_import_table:
                        target_id = local_import_table[used_tag]
                    elif used_tag in label_to_ts_nodes and len(label_to_ts_nodes[used_tag]) == 1:
                        target_id = label_to_ts_nodes[used_tag][0].id

                    if target_id and target_id in nodes and target_id != src_id and len(edges) < MAX_EDGES:
                        edges.append(CallEdge(source=src_id, target=target_id, kind="renders"))

        except Exception as e:
            logger.error("Call graph generation failed: %s", e)
            status = "failed"
            error_msg = str(e)

        # --- Invariant Validation & Deduplication ---
        seen_edges: set[tuple[str, str, str]] = set()
        deduped_edges: list[CallEdge] = []

        for e in edges:
            # Enforce Backend Invariant: both source and target MUST exist in nodes
            if e.source in nodes and e.target in nodes and e.source != e.target:
                key = (e.source, e.target, e.kind)
                if key not in seen_edges:
                    seen_edges.add(key)
                    deduped_edges.append(e)

        if status == "analyzed" and len(deduped_edges) == 0 and len(nodes) > 0:
            status = "zero_edges"
        elif len(nodes) == 0 and status != "failed":
            status = "not_analyzed"

        logger.info(
            "call graph built | status=%s | nodes=%d | edges=%d",
            status,
            len(nodes),
            len(deduped_edges),
        )
        return list(nodes.values()), deduped_edges, status, error_msg
