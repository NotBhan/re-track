"""Repository Summary generator for RE:Track (RefinedEngine Track).

Analyzes indexed repository files to extract stable, global knowledge:
project purpose, technology stack, directory structure, AST symbols (classes, functions, routes, React components),
and key architectural components while strictly respecting .gitignore patterns.

Supports incremental AST symbol discovery, reusing persisted deterministic AST nodes
for unchanged files (0 parses) and performing impact-aware relinking for modified files.
"""

import ast
import hashlib
import logging
from pathlib import Path
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.responses import (
    ArchitectureInfo,
    CallEdge,
    CallNode,
    ComponentInfo,
    DirectoryEntry,
    RepositorySummary,
    TechnologyStack,
)
from app.services.manifest_service import (
    FileFingerprint,
    IndexDelta,
    MANIFEST_SCHEMA_VERSION,
    PARSER_VERSION,
    RepositoryManifest,
)
from app.services.parsers.treesitter_ts_analyzer import (
    ExtractedExport,
    ExtractedImport,
    ExtractedRelationship,
    ExtractedSymbol,
    ParsedModulePayload,
    SourceSpan,
    TreeSitterTSAnalyzer,
)
from app.services.parsers.ts_cross_file_linker import TSCrossFileLinker
from app.services.parsers.ts_grammar_cache import TSGrammarCache, TSLanguageDialect
from app.services.parsers.ts_module_resolver import TSModuleResolver

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
    """Generates a RepositorySummary with deterministic AST symbol discovery from indexed repository files."""

    def __init__(self) -> None:
        self.last_parse_stats: dict[str, int] = {
            "files_parsed": 0,
            "files_reused": 0,
            "relinked_files": 0,
        }
        self.file_ast_metadata: dict[str, dict[str, Any]] = {}

    def generate(
        self,
        repo_path: Path,
        files: list[Path],
        existing_manifest: Optional[RepositoryManifest] = None,
        delta: Optional[IndexDelta] = None,
    ) -> RepositorySummary:
        """Generate a RepositorySummary from a repository and its files with incremental AST reuse."""
        logger.info("generating repository summary | path=%s | files=%d", repo_path, len(files))

        # Filter files by gitignore patterns
        filtered_files = self._filter_ignored_files(repo_path, files)

        fingerprint = self._compute_fingerprint(repo_path, filtered_files, existing_manifest)
        rel_files = [f.relative_to(repo_path) if f.is_relative_to(repo_path) else f for f in filtered_files]

        tech_stack = self._extract_tech_stack(repo_path, rel_files)
        repo_map = self._build_repo_map(rel_files)
        architecture = self._infer_architecture(repo_path, repo_map, tech_stack.frameworks)
        components = self._extract_components(repo_path, filtered_files)
        purpose = self._infer_purpose(repo_path, repo_map, tech_stack.frameworks)
        call_nodes, call_edges, call_status, call_error = self._build_call_graph(
            repo_path, filtered_files, existing_manifest, delta
        )

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
            "repository summary generated | frameworks=%s | components=%d | parsed=%d | reused=%d | relinked=%d",
            tech_stack.frameworks,
            len(components),
            self.last_parse_stats["files_parsed"],
            self.last_parse_stats["files_reused"],
            self.last_parse_stats["relinked_files"],
        )
        return summary

    def _filter_ignored_files(self, repo_path: Path, files: list[Path]) -> list[Path]:
        """Filter files using standard ignore rules, .gitignore, .agentignore patterns, and symlink containment."""
        ignored_dir_names = {
            ".git", "node_modules", "dist", "build", "target", ".venv", "venv",
            "__pycache__", ".cache", ".next", ".nuxt", ".output", "coverage",
            ".turbo", ".idea", ".vscode", "tmp", ".parcel-cache",
        }

        # Parse .gitignore and .agentignore if present
        ignore_patterns = set()
        for ignore_name in (".gitignore", ".agentignore"):
            ignore_file = repo_path / ignore_name
            if ignore_file.exists():
                try:
                    for line in ignore_file.read_text(errors="ignore").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            pattern = line.rstrip("/").lstrip("/")
                            if pattern:
                                ignore_patterns.add(pattern)
                except Exception:
                    pass

        repo_canon = repo_path.resolve()
        valid_files = []
        for f in files:
            p_obj = f if isinstance(f, Path) else Path(f)
            try:
                p_canon = p_obj.resolve()
                if not p_canon.is_relative_to(repo_canon):
                    continue  # Symlink leaves repository boundary
                if not p_canon.exists() or not p_canon.is_file():
                    continue  # Broken symlink
            except Exception:
                continue

            try:
                rel = p_obj.relative_to(repo_canon)
            except ValueError:
                continue

            rel_parts = rel.parts
            # Check ignored directory names in relative path
            if any(p in ignored_dir_names for p in rel_parts[:-1]):
                continue
            if any(p.startswith(".agents") or p.startswith("__") or (p.startswith(".") and p != ".") for p in rel_parts[:-1]):
                continue
            if p_obj.name.startswith("."):
                continue
            # Check ignore patterns
            rel_str = str(rel)
            if any(pat in rel_str or any(pat == p for p in rel_parts) for pat in ignore_patterns):
                continue

            valid_files.append(p_obj)

        return valid_files

    def _compute_fingerprint(
        self,
        repo_path: Path,
        files: list[Path],
        existing_manifest: Optional[RepositoryManifest] = None,
    ) -> str:
        """Compute a deterministic SHA-256 fingerprint from schema version, parser version, and file identities."""
        hasher = hashlib.sha256()
        header = f"{MANIFEST_SCHEMA_VERSION}:{PARSER_VERSION}:{repo_path.resolve()}"
        hasher.update(header.encode("utf-8"))

        for f in sorted(files, key=lambda p: str(p)):
            try:
                rel = str(f.resolve().relative_to(repo_path.resolve()).as_posix())
                sha = ""
                if existing_manifest and rel in existing_manifest.files:
                    sha = existing_manifest.files[rel].sha256
                else:
                    sha = ManifestService.compute_sha256(f)
                entry_str = f"|{rel}:{sha}:{f.stat().st_size if f.exists() else 0}"
                hasher.update(entry_str.encode("utf-8"))
            except Exception:
                continue

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

        # Check for Next.js config
        if any("next.config" in f.name for f in files):
            frameworks.add("Next.js")

        databases: set[str] = set()
        dependencies: set[str] = set()

        return TechnologyStack(
            languages=sorted(list(languages)),
            frameworks=sorted(list(frameworks)),
            databases=sorted(list(databases)),
            dependencies=sorted(list(dependencies)),
        )

    def _build_repo_map(self, rel_files: list[Path]) -> list[DirectoryEntry]:
        """Build high-level directory map with deterministic path normalization."""
        dirs: dict[str, int] = {}
        for f in rel_files:
            parent = f.parent
            if parent != Path("."):
                top_dir = str(parent).split("/")[0] if "/" in str(parent) else str(parent)
                dirs[top_dir] = dirs.get(top_dir, 0) + 1

        entries = []
        for d, count in sorted(dirs.items()):
            desc = self._describe_directory(d)
            entries.append(DirectoryEntry(path=d, description=f"{desc} ({count} files)"))
        return entries

    def _describe_directory(self, dir_name: str) -> str:
        """Infer standard directory purpose based on conventional naming."""
        d = dir_name.lower()
        if "test" in d:
            return "Test suite and validation fixtures"
        if "doc" in d:
            return "Documentation and architecture design"
        if d in ("src", "app", "lib", "core"):
            return "Primary application source code"
        if "component" in d:
            return "UI component library"
        if "api" in d or "router" in d:
            return "API route handlers and controllers"
        if "service" in d:
            return "Domain business logic services"
        if "model" in d or "schema" in d:
            return "Data models and type definitions"
        if "script" in d:
            return "Automation and development scripts"
        return "Application module"

    def _infer_architecture(
        self,
        repo_path: Path,
        repo_map: list[DirectoryEntry],
        frameworks: list[str],
    ) -> ArchitectureInfo:
        """Infer architectural pattern and structural layers."""
        paths = {e.path.lower() for e in repo_map}
        layers: list[str] = []

        if any("frontend" in p or "client" in p or "ui" in p or "src" in p for p in paths):
            layers.append("Frontend")
        if any("backend" in p or "server" in p or "api" in p or "app" in p for p in paths):
            layers.append("Backend")
        if any("service" in p for p in paths):
            layers.append("Services")
        if any("model" in p or "schema" in p or "db" in p for p in paths):
            layers.append("Data / Persistence")

        pattern = "modular"
        if "Frontend" in layers and "Backend" in layers:
            pattern = "layered"
        elif "FastAPI" in frameworks or "Django" in frameworks:
            pattern = "mvc" if "Django" in frameworks else "layered"

        return ArchitectureInfo(
            pattern=pattern,
            layers=layers or ["Application Core"],
            boundaries=[],
            major_flows=[],
        )

    def _extract_components(self, repo_path: Path, files: list[Path]) -> list[ComponentInfo]:
        """Extract key architectural components by checking module names and class definitions."""
        components: list[ComponentInfo] = []
        for f in files:
            if f.suffix == ".py":
                try:
                    content = f.read_text(errors="ignore")
                    for line in content.splitlines()[:50]:
                        if line.startswith("class ") and ":" in line:
                            class_name = line.split("class ")[1].split("(")[0].split(":")[0].strip()
                            if any(class_name.endswith(s) for s in ("Service", "Engine", "Manager", "Store", "Handler", "Generator", "Client")):
                                components.append(ComponentInfo(
                                    name=class_name,
                                    responsibilities=f"Core {class_name} implementation",
                                    relationships=[],
                                ))
                except Exception:
                    pass
        return components[:15]

    def _infer_purpose(
        self,
        repo_path: Path,
        repo_map: list[DirectoryEntry],
        frameworks: list[str],
    ) -> str:
        """Infer high-level project purpose from README or technology stack."""
        readme = repo_path / "README.md"
        if readme.exists():
            try:
                lines = readme.read_text(errors="ignore").splitlines()
                for line in lines[:10]:
                    cleaned = line.strip().lstrip("#").strip()
                    if cleaned and len(cleaned) > 10 and not cleaned.startswith("["):
                        return cleaned
            except Exception:
                pass
        return f"Software repository utilizing {', '.join(frameworks) if frameworks else 'modern technologies'}."

    def _build_call_graph(
        self,
        repo_path: Path,
        files: list[Path],
        existing_manifest: Optional[RepositoryManifest] = None,
        delta: Optional[IndexDelta] = None,
    ) -> tuple[list[CallNode], list[CallEdge], str, str | None]:
        """Deterministic Multi-Language AST Structural Extraction & Call Graph Construction.

        Supports incremental symbol reuse from existing_manifest for unchanged files,
        reading & parsing only modified/added files, and impact-aware relinking.
        """
        nodes: dict[str, CallNode] = {}
        edges: list[CallEdge] = []
        status = "analyzed"
        error_msg: str | None = None

        self.last_parse_stats = {"files_parsed": 0, "files_reused": 0, "relinked_files": 0}
        self.file_ast_metadata = {}

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
            def _not_hidden(p_file: Path) -> bool:
                try:
                    rel_p = p_file.relative_to(repo_path)
                    return not any(part.startswith(".") for part in rel_p.parts)
                except Exception:
                    return not p_file.name.startswith(".")

            # Determine unchanged relative paths set
            unchanged_rels: set[str] = set()
            if delta and existing_manifest:
                for u in delta.unchanged:
                    try:
                        rel_u = str(u.resolve().relative_to(repo_path.resolve()).as_posix())
                        if rel_u in existing_manifest.files and existing_manifest.files[rel_u].ast_nodes:
                            unchanged_rels.add(rel_u)
                    except Exception:
                        pass

            # ─────────────────────────────────────────────────────────────────
            # 1. PYTHON DETERMINISTIC RESOLVER
            # ─────────────────────────────────────────────────────────────────
            py_files = [
                f for f in files
                if f.suffix == ".py" and not f.name.startswith(".")
                and "migration" not in str(f)
                and "__pycache__" not in str(f)
                and _not_hidden(f)
            ]

            py_trees: dict[str, tuple[ast.AST, str, Path]] = {}
            label_to_py_nodes: dict[str, list[CallNode]] = {}
            class_methods: dict[str, set[str]] = {}
            class_bases: dict[str, list[str]] = {}
            file_import_maps: dict[str, dict[str, str]] = {}
            file_to_py_nodes: dict[str, list[CallNode]] = {}

            # --- Python Pass 1: Global Symbol Discovery (Incremental) ---
            for pf in py_files[:40]:
                try:
                    rel = str(pf.resolve().relative_to(repo_path.resolve()).as_posix())
                    module_prefix = rel.replace("/", ".").replace(".py", "").removesuffix(".__init__")

                    # If file is unchanged and cached in manifest -> REUSE (0 parse)
                    if rel in unchanged_rels and existing_manifest:
                        fp = existing_manifest.files[rel]
                        cached_nodes: list[CallNode] = []
                        for nd in fp.ast_nodes:
                            cnode = CallNode(
                                id=nd["id"],
                                label=nd["label"],
                                file=nd.get("file", rel),
                                kind=nd.get("kind", "function"),
                                line=nd.get("line", 0),
                            )
                            if cnode.id not in nodes and len(nodes) < MAX_NODES:
                                nodes[cnode.id] = cnode
                                cached_nodes.append(cnode)
                                label_to_py_nodes.setdefault(cnode.label, []).append(cnode)
                                if "." in cnode.label:
                                    # Method label "ClassName.method_name"
                                    method_short = cnode.label.split(".")[-1]
                                    label_to_py_nodes.setdefault(method_short, []).append(cnode)

                        file_to_py_nodes[rel] = cached_nodes
                        # Reconstruct import map from cached imports
                        imp_map = {}
                        for imp_entry in fp.imports:
                            if " as " in imp_entry:
                                orig, alias = imp_entry.split(" as ")
                                imp_map[alias.strip()] = orig.strip()
                            else:
                                imp_map[imp_entry] = imp_entry
                        file_import_maps[rel] = imp_map

                        self.file_ast_metadata[rel] = {
                            "language": "Python",
                            "symbols": list(fp.symbols),
                            "imports": list(fp.imports),
                            "ast_nodes": [n.to_dict() if hasattr(n, "to_dict") else nd for n, nd in zip(cached_nodes, fp.ast_nodes)],
                            "ast_edges": list(fp.ast_edges),
                        }
                        self.last_parse_stats["files_reused"] += 1
                        continue

                    # Otherwise: modified, newly added, or full rebuild -> READ & PARSE
                    code = pf.read_text(errors="ignore")
                    tree = ast.parse(code)
                    py_trees[rel] = (tree, module_prefix, pf)
                    self.last_parse_stats["files_parsed"] += 1

                    extracted_symbols: list[str] = []
                    extracted_imports: list[str] = []
                    extracted_nodes: list[CallNode] = []

                    # Discover imports for this file
                    file_imports: dict[str, str] = {}
                    for stmt in tree.body:
                        if isinstance(stmt, ast.Import):
                            for alias in stmt.names:
                                asname = alias.asname or alias.name
                                file_imports[asname] = alias.name
                                extracted_imports.append(f"{alias.name} as {asname}" if alias.asname else alias.name)
                        elif isinstance(stmt, ast.ImportFrom):
                            mod = stmt.module or ""
                            if stmt.level > 0:
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
                                file_imports[asname] = full_target
                                extracted_imports.append(f"{full_target} as {asname}" if alias.asname else full_target)

                    file_import_maps[rel] = file_imports

                    # Discover classes, methods, and functions
                    for stmt in tree.body:
                        if isinstance(stmt, ast.ClassDef):
                            class_nid = f"{module_prefix}.{stmt.name}" if module_prefix else stmt.name
                            if class_nid not in nodes and len(nodes) < MAX_NODES:
                                node = CallNode(id=class_nid, label=stmt.name, file=rel, kind="class", line=stmt.lineno)
                                nodes[class_nid] = node
                                extracted_nodes.append(node)
                                extracted_symbols.append(stmt.name)
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
                                        extracted_nodes.append(mnode)
                                        extracted_symbols.append(item.name)
                                        label_to_py_nodes.setdefault(item.name, []).append(mnode)
                                        label_to_py_nodes.setdefault(method_label, []).append(mnode)
                            class_methods[class_nid] = methods_set

                        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            func_nid = f"{module_prefix}.{stmt.name}" if module_prefix else stmt.name
                            if func_nid not in nodes and len(nodes) < MAX_NODES:
                                fnode = CallNode(id=func_nid, label=stmt.name, file=rel, kind="function", line=stmt.lineno)
                                nodes[func_nid] = fnode
                                extracted_nodes.append(fnode)
                                extracted_symbols.append(stmt.name)
                                label_to_py_nodes.setdefault(stmt.name, []).append(fnode)

                    file_to_py_nodes[rel] = extracted_nodes
                    self.file_ast_metadata[rel] = {
                        "language": "Python",
                        "symbols": extracted_symbols,
                        "imports": extracted_imports,
                        "ast_nodes": [
                            {"id": n.id, "label": n.label, "file": n.file, "kind": n.kind, "line": n.line}
                            for n in extracted_nodes
                        ],
                        "ast_edges": [],
                    }
                except Exception:
                    continue

            # --- Python Pass 2: Deterministic Import & Call Resolution (Impact-Aware) ---
            # Files that must be resolved: any file parsed in py_trees
            for rel, (tree, module_prefix, pf) in py_trees.items():
                import_map = file_import_maps.get(rel, {})
                file_edges: list[CallEdge] = []

                class _PyCallResolver(ast.NodeVisitor):
                    def __init__(self_inner) -> None:
                        self_inner.current_class: str | None = None
                        self_inner.current_func: str | None = None
                        self_inner.current_func_nid: str | None = None
                        self_inner.local_scope: set[str] = set()

                    def visit_ClassDef(self_inner, node: ast.ClassDef) -> None:
                        class_nid = f"{module_prefix}.{node.name}" if module_prefix else node.name
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
                                    edge = CallEdge(source=class_nid, target=target_id, kind="inherits")
                                    edges.append(edge)
                                    file_edges.append(edge)

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

                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                target_id = None

                                if isinstance(child.func, ast.Attribute) and isinstance(child.func.value, ast.Name):
                                    if child.func.value.id == "self" and self_inner.current_class:
                                        m_name = child.func.attr
                                        if m_name in class_methods.get(self_inner.current_class, set()):
                                            target_id = f"{self_inner.current_class}.{m_name}"
                                    elif child.func.value.id in import_map:
                                        mod_target = import_map[child.func.value.id]
                                        candidate = f"{mod_target}.{child.func.attr}"
                                        if candidate in nodes:
                                            target_id = candidate

                                elif isinstance(child.func, ast.Name):
                                    fname = child.func.id
                                    if fname not in self_inner.local_scope and fname not in BUILTIN_FUNCS:
                                        if fname in import_map and import_map[fname] in nodes:
                                            target_id = import_map[fname]
                                        elif f"{module_prefix}.{fname}" in nodes:
                                            target_id = f"{module_prefix}.{fname}"
                                        elif fname in label_to_py_nodes:
                                            if len(label_to_py_nodes[fname]) == 1:
                                                target_id = label_to_py_nodes[fname][0].id

                                if target_id and target_id in nodes and func_nid in nodes and target_id != func_nid and len(edges) < MAX_EDGES:
                                    edge = CallEdge(source=func_nid, target=target_id, kind="calls")
                                    edges.append(edge)
                                    file_edges.append(edge)

                        self_inner.current_func = old_func
                        self_inner.current_func_nid = old_nid
                        self_inner.local_scope = old_scope

                resolver = _PyCallResolver()
                resolver.visit(tree)

                if rel in self.file_ast_metadata:
                    self.file_ast_metadata[rel]["ast_edges"] = [
                        {"source": e.source, "target": e.target, "kind": e.kind} for e in file_edges
                    ]
                self.last_parse_stats["relinked_files"] += 1

            # For unchanged files, reuse their cached edges if both endpoints exist in nodes
            for rel in unchanged_rels:
                if existing_manifest and rel in existing_manifest.files:
                    cached_edges_raw = existing_manifest.files[rel].ast_edges
                    for ed in cached_edges_raw:
                        if ed["source"] in nodes and ed["target"] in nodes and ed["source"] != ed["target"]:
                            edges.append(CallEdge(source=ed["source"], target=ed["target"], kind=ed.get("kind", "calls")))

            # ─────────────────────────────────────────────────────────────────
            # 2. TYPESCRIPT / JAVASCRIPT TREE-SITTER STRUCTURAL ANALYZER
            # ─────────────────────────────────────────────────────────────────
            ts_files = [
                f for f in files
                if f.suffix.lower() in (".tsx", ".jsx", ".ts", ".js", ".mjs", ".cjs")
                and not f.name.startswith(".")
                and "node_modules" not in str(f)
                and _not_hidden(f)
            ]

            all_ts_rel_paths = {str(tf.resolve().relative_to(repo_path.resolve()).as_posix()) for tf in ts_files}
            ts_analyzer = TreeSitterTSAnalyzer()
            ts_resolver = TSModuleResolver(repo_path, known_files=all_ts_rel_paths)
            parsed_modules: dict[str, ParsedModulePayload] = {}
            changed_ts_rels: set[str] = set()

            for tf in ts_files[:50]:
                try:
                    rel = str(tf.resolve().relative_to(repo_path.resolve()).as_posix())

                    # If unchanged and cached -> REUSE
                    if rel in unchanged_rels and existing_manifest and rel in existing_manifest.files:
                        fp = existing_manifest.files[rel]
                        cached_symbols: list[ExtractedSymbol] = []
                        cached_exports: list[ExtractedExport] = []

                        for nd in fp.ast_nodes:
                            nid = nd["id"]
                            nlabel = nd["label"]
                            nkind = nd.get("kind", "function")
                            nline = nd.get("line", 0)
                            cnode = CallNode(
                                id=nid,
                                label=nlabel,
                                file=nd.get("file", rel),
                                kind=nkind,
                                line=nline,
                            )
                            if nid not in nodes and len(nodes) < MAX_NODES:
                                nodes[nid] = cnode

                            cached_symbols.append(
                                ExtractedSymbol(
                                    id=nid,
                                    name=nlabel,
                                    qualified_name=nlabel,
                                    kind=nkind,
                                    file=rel,
                                    span=SourceSpan(start_line=nline, start_col=0, end_line=nline, end_col=0),
                                    exported=True,
                                )
                            )
                            cached_exports.append(
                                ExtractedExport(
                                    exported_name=nlabel,
                                    local_name=nlabel,
                                    file=rel,
                                )
                            )

                        cached_imports = [
                            ExtractedImport(
                                source_module=imp,
                                imported_name="*",
                                local_name=imp,
                                file=rel,
                                span=SourceSpan(start_line=1, start_col=0, end_line=1, end_col=0),
                            )
                            for imp in fp.imports
                        ]

                        parsed_modules[rel] = ParsedModulePayload(
                            rel_path=rel,
                            dialect=TSLanguageDialect.TYPESCRIPT,
                            symbols=cached_symbols,
                            imports=cached_imports,
                            exports=cached_exports,
                            parse_status="ok",
                        )

                        self.file_ast_metadata[rel] = {
                            "language": "TypeScript",
                            "symbols": list(fp.symbols),
                            "imports": list(fp.imports),
                            "ast_nodes": [nd for nd in fp.ast_nodes],
                            "ast_edges": list(fp.ast_edges),
                        }
                        self.last_parse_stats["files_reused"] += 1
                        continue

                    # Otherwise: parse source with Tree-sitter
                    text = tf.read_text(errors="ignore")
                    payload = ts_analyzer.parse_file(rel, text)
                    parsed_modules[rel] = payload
                    changed_ts_rels.add(rel)
                    self.last_parse_stats["files_parsed"] += 1

                    extracted_ast_nodes: list[dict[str, Any]] = []
                    for s in payload.symbols:
                        if s.id not in nodes and len(nodes) < MAX_NODES:
                            node = CallNode(
                                id=s.id,
                                label=s.qualified_name or s.name,
                                file=s.file,
                                kind=s.kind,
                                line=s.span.start_line,
                            )
                            nodes[s.id] = node
                        extracted_ast_nodes.append({
                            "id": s.id,
                            "label": s.qualified_name or s.name,
                            "file": s.file,
                            "kind": s.kind,
                            "line": s.span.start_line,
                        })

                    self.file_ast_metadata[rel] = {
                        "language": "TypeScript",
                        "symbols": [s.name for s in payload.symbols],
                        "imports": [i.source_module for i in payload.imports],
                        "ast_nodes": extracted_ast_nodes,
                        "ast_edges": [],
                    }
                except Exception as ex:
                    logger.debug("Failed parsing TS module %s: %s", tf, ex)
                    continue

            # --- TS Pass 2: Deterministic Cross-File Linking ---
            ts_linker = TSCrossFileLinker(ts_resolver)
            _, ts_edges, linking_stats = ts_linker.link_modules(
                parsed_modules, existing_nodes=nodes, max_nodes=MAX_NODES, max_edges=MAX_EDGES
            )

            # Route edges to respective file metadata and global graph
            edges_by_file: dict[str, list[dict[str, str]]] = {}
            for edge in ts_edges:
                if len(edges) < MAX_EDGES:
                    edges.append(edge)
                src_file = edge.source.split("#", 1)[0] if "#" in edge.source else None
                if src_file and src_file in self.file_ast_metadata:
                    edges_by_file.setdefault(src_file, []).append({
                        "source": edge.source,
                        "target": edge.target,
                        "kind": edge.kind,
                    })

            for changed_rel in changed_ts_rels:
                if changed_rel in self.file_ast_metadata:
                    self.file_ast_metadata[changed_rel]["ast_edges"] = edges_by_file.get(changed_rel, [])
                self.last_parse_stats["relinked_files"] += 1

            # For unchanged TS files that weren't relinked, preserve valid cached edges
            for rel in unchanged_rels:
                if rel not in changed_ts_rels and existing_manifest and rel in existing_manifest.files:
                    cached_ts_edges = existing_manifest.files[rel].ast_edges
                    for ed in cached_ts_edges:
                        if ed["source"] in nodes and ed["target"] in nodes and ed["source"] != ed["target"]:
                            if len(edges) < MAX_EDGES:
                                edges.append(CallEdge(source=ed["source"], target=ed["target"], kind=ed.get("kind", "calls")))

        except Exception as e:
            logger.error("Call graph generation failed: %s", e)
            status = "failed"
            error_msg = str(e)

        # --- Invariant Validation & Deduplication ---
        seen_edges: set[tuple[str, str, str]] = set()
        deduped_edges: list[CallEdge] = []

        for e in edges:
            if e.source in nodes and e.target in nodes and e.source != e.target:
                key = (e.source, e.target, e.kind)
                if key not in seen_edges:
                    seen_edges.add(key)
                    deduped_edges.append(e)

        if status == "analyzed" and len(deduped_edges) == 0 and len(nodes) > 0:
            status = "zero_edges"
        elif len(nodes) == 0 and status != "failed":
            status = "not_analyzed"

        return list(nodes.values()), deduped_edges, status, error_msg
