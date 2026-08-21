"""Repository Manager — CRUD, import, scan, and persistent metadata storage."""

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.repository import Repository, ScanResult
from app.services.sources.github import GitHubSource
from app.services.sources.local import LocalSource

IGNORED_DIRS = frozenset({
    ".git", "node_modules", "dist", "build", "target",
    "venv", "__pycache__", ".venv", ".cache", ".next",
    ".nuxt", ".output", "coverage", ".turbo", ".idea", ".vscode", "tmp",
})

ESTIMATED_INDEX_TIME_MS_PER_FILE = 100

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".r": "R",
    ".R": "R",
    ".scala": "Scala",
    ".lua": "Lua",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "Less",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".dart": "Dart",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".ml": "OCaml",
}

FRAMEWORK_MARKERS: dict[str, str] = {
    "manage.py": "Django",
    "wsgi.py": "Django",
    "asgi.py": "Django",
    "package.json": "Node.js",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java",
    "build.gradle": "Java/Kotlin",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "Package.swift": "Swift",
    "CMakeLists.txt": "C/C++",
    "mix.exs": "Elixir",
    "cabal.config": "Haskell",
    "pubspec.yaml": "Dart",
    "Makefile": "C/C++",
    "tsconfig.json": "TypeScript",
    "vite.config.ts": "Vite",
    "vite.config.js": "Vite",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
}


class RepositoryManager:
    """Manages repository CRUD, import, scan, and metadata persistence."""

    def __init__(
        self,
        store_path: str | Path | None = None,
        legacy_store_path: str | Path | None = None,
        repos_dir: str | Path | None = None,
        legacy_repos_dir: str | Path | None = None,
    ) -> None:
        if store_path is None:
            self._store_path = Path.home() / ".retrack" / "repositories.json"
            self._legacy_store_path = Path(legacy_store_path) if legacy_store_path is not None else (Path.home() / ".andes" / "repositories.json")
        else:
            self._store_path = Path(store_path)
            self._legacy_store_path = Path(legacy_store_path) if legacy_store_path is not None else None

        if repos_dir is None:
            self._repos_dir = Path.home() / ".retrack" / "repos"
            self._legacy_repos_dir = Path(legacy_repos_dir) if legacy_repos_dir is not None else (Path.home() / ".andes" / "repos")
        else:
            self._repos_dir = Path(repos_dir)
            self._legacy_repos_dir = Path(legacy_repos_dir) if legacy_repos_dir is not None else None

        self._repositories: dict[str, dict[str, Any]] = {}
        self._active_progress: dict[str, dict[str, Any]] = {}
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self) -> None:
        if self._store_path.exists():
            try:
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._repositories = data
                    return
            except Exception:
                pass

        if self._legacy_store_path is not None and self._legacy_store_path.exists():
            try:
                data = json.loads(self._legacy_store_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._repositories = data
                    return
            except Exception:
                pass

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._store_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._repositories, f, indent=2)
            f.flush()
            import os
            os.fsync(f.fileno())
        tmp_path.replace(self._store_path)

    @staticmethod
    def _repo_to_dict(repo: Repository) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": repo.id,
            "name": repo.name,
            "source_type": repo.source_type,
            "local_path": repo.local_path,
            "branch": repo.branch,
            "source_url": repo.source_url,
            "commit_hash": repo.commit_hash,
            "status": repo.status,
            "languages": repo.languages,
            "frameworks": repo.frameworks,
            "file_count": repo.file_count,
            "size_bytes": repo.size_bytes,
            "indexed_at": repo.indexed_at,
            "error_message": repo.error_message,
            "created_at": repo.created_at,
            "summary": repo.summary,
            "entry_points": repo.entry_points,
            "architecture": repo.architecture,
            "components": repo.components,
            "dependencies": repo.dependencies,
            "metadata": repo.metadata,
        }
        if repo.scan_result is not None:
            d["scan_result"] = {
                "languages": repo.scan_result.languages,
                "frameworks": repo.scan_result.frameworks,
                "file_count": repo.scan_result.file_count,
                "size_bytes": repo.scan_result.size_bytes,
                "ignored_dirs": repo.scan_result.ignored_dirs,
                "warnings": repo.scan_result.warnings,
                "estimated_index_time_ms": repo.scan_result.estimated_index_time_ms,
            }
        return d

    @staticmethod
    def _dict_to_repo(d: dict[str, Any]) -> Repository:
        scan_result = None
        if "scan_result" in d and d["scan_result"] is not None:
            sr = d["scan_result"]
            scan_result = ScanResult(
                languages=sr.get("languages", []),
                frameworks=sr.get("frameworks", []),
                file_count=sr.get("file_count", 0),
                size_bytes=sr.get("size_bytes", 0),
                ignored_dirs=sr.get("ignored_dirs", []),
                warnings=sr.get("warnings", []),
                estimated_index_time_ms=sr.get("estimated_index_time_ms", 0),
            )
        return Repository(
            id=d["id"],
            name=d["name"],
            source_type=d["source_type"],
            local_path=d["local_path"],
            branch=d.get("branch", "main"),
            source_url=d.get("source_url"),
            commit_hash=d.get("commit_hash"),
            status=d.get("status", "registered"),
            languages=d.get("languages", []),
            frameworks=d.get("frameworks", []),
            file_count=d.get("file_count", 0),
            size_bytes=d.get("size_bytes", 0),
            indexed_at=d.get("indexed_at"),
            scan_result=scan_result,
            error_message=d.get("error_message"),
            created_at=d.get("created_at", ""),
            summary=d.get("summary", ""),
            entry_points=d.get("entry_points", []),
            architecture=d.get("architecture", ""),
            components=d.get("components", []),
            dependencies=d.get("dependencies", []),
            metadata=d.get("metadata", {}),
        )

    # ── CRUD ──────────────────────────────────────────────────────

    def list_repositories(self) -> list[Repository]:
        return [self._dict_to_repo(d) for d in self._repositories.values()]

    def get_repository(self, repo_id: str) -> Repository:
        if repo_id not in self._repositories:
            raise KeyError(f"Repository not found: {repo_id}")
        return self._dict_to_repo(self._repositories[repo_id])

    def update_repository(self, repo_id: str, **kwargs: Any) -> Repository:
        if repo_id not in self._repositories:
            raise KeyError(f"Repository not found: {repo_id}")
        d = self._repositories[repo_id]
        for key, value in kwargs.items():
            if key in d:
                d[key] = value
        self._save()
        return self._dict_to_repo(d)

    def delete_repository(self, repo_id: str) -> None:
        if repo_id not in self._repositories:
            raise KeyError(f"Repository not found: {repo_id}")
        del self._repositories[repo_id]
        self._save()

    # ── Import ────────────────────────────────────────────────────

    def import_repository(
        self,
        source_type: str,
        source_url: str | None = None,
        local_path: str | None = None,
        name: str | None = None,
    ) -> Repository:
        if source_type == "github":
            if not source_url:
                raise ValueError("source_url required for github source")
            workspace = self._repos_dir
            source = GitHubSource(url=source_url, workspace=workspace)
            local_path_resolved = str(source.import_to())
            branch, commit_hash = self._get_git_info(local_path_resolved)
            repo_name = name or source.get_repo_name()
        elif source_type == "local":
            if not local_path:
                raise ValueError("local_path required for local source")
            source = LocalSource(path=local_path)
            local_path_resolved = str(source.import_to())
            branch, commit_hash = self._get_git_info(local_path_resolved)
            repo_name = name or Path(local_path).name
        else:
            raise ValueError(f"Unknown source type: {source_type}")

        # Check for existing duplicate repository (same resolved local path or GitHub URL)
        for existing_id, existing_data in self._repositories.items():
            same_path = existing_data.get("local_path") == local_path_resolved
            same_url = source_url and existing_data.get("source_url") == source_url
            if same_path or same_url:
                # Return existing repository with updated name/metadata
                if name and name != existing_data.get("name"):
                    existing_data["name"] = name
                if branch:
                    existing_data["branch"] = branch
                if commit_hash:
                    existing_data["commit_hash"] = commit_hash
                self._save()
                return self._dict_to_repo(existing_data)

        repo_id = uuid.uuid4().hex[:12]
        repo = Repository(
            id=repo_id,
            name=repo_name,
            source_type=source_type,
            local_path=local_path_resolved,
            branch=branch,
            source_url=source_url if source_type == "github" else None,
            commit_hash=commit_hash,
            status="registered",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repositories[repo_id] = self._repo_to_dict(repo)
        self._save()
        return repo

    # ── Scan ──────────────────────────────────────────────────────

    def scan_repository(self, repo_id: str) -> ScanResult:
        if repo_id not in self._repositories:
            raise KeyError(f"Repository not found: {repo_id}")
        d = self._repositories[repo_id]
        repo = self._dict_to_repo(d)

        if not Path(repo.local_path).is_dir():
            raise FileNotFoundError(f"Local path does not exist: {repo.local_path}")

        languages: set[str] = set()
        frameworks: set[str] = set()
        file_count = 0
        size_bytes = 0

        # Metadata extraction helpers
        code_extensions = set(EXTENSION_LANGUAGE_MAP.keys())
        COMPONENTS_EXCLUDE = frozenset({"node_modules", "dist", "build", "__pycache__", ".git", ".venv", "venv", "target"})
        entry_point_names = {
            "main.py", "index.ts", "index.tsx", "lib.rs", "main.go",
            "App.tsx", "app.py", "server.py",
        }
        entry_points: list[str] = []
        top_level_dirs: set[str] = set()
        top_level_with_code: dict[str, bool] = {}

        # Parse .gitignore if present in repository root
        gitignore_patterns: set[str] = set()
        gi_file = Path(repo.local_path) / ".gitignore"
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

        for root, dirs, files in Path(repo.local_path).walk():
            dirs[:] = [
                d for d in dirs
                if d not in IGNORED_DIRS
                and not d.startswith(".agents")
                and not d.startswith("__")
                and d not in gitignore_patterns
                and not any(pat == d or pat.rstrip("/") == d for pat in gitignore_patterns)
            ]
            for f in files:
                p = Path(root) / f
                rel_p = str(p.relative_to(repo.local_path)) if p.is_relative_to(repo.local_path) else f
                if any(pat in rel_p or pat == f for pat in gitignore_patterns):
                    continue
                try:
                    size_bytes += p.stat().st_size
                except OSError:
                    continue
                file_count += 1
                ext = p.suffix.lower()
                if ext in EXTENSION_LANGUAGE_MAP:
                    languages.add(EXTENSION_LANGUAGE_MAP[ext])

                # Entry points
                if f in entry_point_names and len(entry_points) < 5:
                    rel = str(Path(root).relative_to(repo.local_path) / f)
                    if rel not in entry_points:
                        entry_points.append(rel)

                # Components: track top-level dirs containing code
                rel_path = Path(root).relative_to(repo.local_path)
                parts = rel_path.parts
                if parts and parts[0] not in COMPONENTS_EXCLUDE:
                    top_level_dirs.add(parts[0])
                    if ext in code_extensions:
                        top_level_with_code[parts[0]] = True

            for marker, framework in FRAMEWORK_MARKERS.items():
                if (Path(root) / marker).exists():
                    frameworks.add(framework)

        # Architecture inference
        has_src = (Path(repo.local_path) / "src").is_dir()
        code_dir_count = len([d for d in top_level_dirs if d in top_level_with_code])
        if has_src:
            architecture = "modular"
        elif code_dir_count >= 3:
            architecture = "multi-module"
        else:
            architecture = "flat"

        # Components: top-level dirs with code files
        components = sorted(top_level_with_code.keys())

        # Dependencies: parse known manifest files
        dependencies = self._extract_dependencies(repo.local_path)
        dep_lower = {d.lower() for d in dependencies}
        if "django" in dep_lower:
            frameworks.add("Django")
        if "fastapi" in dep_lower:
            frameworks.add("FastAPI")
        if "flask" in dep_lower:
            frameworks.add("Flask")
        if "react" in dep_lower:
            frameworks.add("React")
        if "next" in dep_lower:
            frameworks.add("Next.js")
        if "tauri" in dep_lower or (Path(repo.local_path) / "src-tauri").is_dir():
            frameworks.add("Tauri")

        estimated_index_time = file_count * ESTIMATED_INDEX_TIME_MS_PER_FILE

        scan_result = ScanResult(
            languages=sorted(languages),
            frameworks=sorted(frameworks),
            file_count=file_count,
            size_bytes=size_bytes,
            ignored_dirs=sorted(IGNORED_DIRS),
            estimated_index_time_ms=estimated_index_time,
        )

        d["languages"] = scan_result.languages
        d["frameworks"] = scan_result.frameworks
        d["file_count"] = scan_result.file_count
        d["size_bytes"] = scan_result.size_bytes
        # Keep indexed status if already indexed, otherwise mark registered (ready)
        current_status = d.get("status", "registered")
        d["status"] = "indexed" if current_status == "indexed" else "registered"
        d["entry_points"] = entry_points
        d["architecture"] = architecture
        d["components"] = components
        d["dependencies"] = dependencies
        d["scan_result"] = {
            "languages": scan_result.languages,
            "frameworks": scan_result.frameworks,
            "file_count": scan_result.file_count,
            "size_bytes": scan_result.size_bytes,
            "ignored_dirs": scan_result.ignored_dirs,
            "warnings": scan_result.warnings,
            "estimated_index_time_ms": scan_result.estimated_index_time_ms,
        }
        self._save()
        return scan_result

    @staticmethod
    def _extract_dependencies(local_path: str) -> list[str]:
        root = Path(local_path)
        deps: list[str] = []

        # requirements.txt
        req_file = root / "requirements.txt"
        if req_file.exists():
            for line in req_file.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    name = line.split("==")[0].split(">=")[0].split("<=")[0].split("!=")[0].strip()
                    if name:
                        deps.append(name)

        # package.json
        pkg_file = root / "package.json"
        if pkg_file.exists():
            try:
                pkg = json.loads(pkg_file.read_text())
                for dep_name in list(pkg.get("dependencies", {}).keys()) + list(pkg.get("devDependencies", {}).keys()):
                    deps.append(dep_name)
            except (json.JSONDecodeError, AttributeError):
                pass

        # Cargo.toml
        cargo_file = root / "Cargo.toml"
        if cargo_file.exists():
            try:
                text = cargo_file.read_text()
                in_deps = False
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("["):
                        in_deps = stripped in ("[dependencies]", "[dev-dependencies]")
                    elif in_deps and "=" in stripped:
                        dep_name = stripped.split("=")[0].strip()
                        if dep_name and not dep_name.startswith("#"):
                            deps.append(dep_name)
            except Exception:
                pass

        # go.mod
        go_file = root / "go.mod"
        if go_file.exists():
            try:
                in_require = False
                for line in go_file.read_text().splitlines():
                    stripped = line.strip()
                    if stripped.startswith("require"):
                        in_require = True
                        # inline require: require github.com/foo v1.0.0
                        rest = stripped[len("require"):].strip()
                        if rest and not rest.startswith("("):
                            dep_name = rest.split()[0] if rest.split() else ""
                            if dep_name:
                                deps.append(dep_name)
                            in_require = False
                    elif in_require:
                        if stripped == ")":
                            in_require = False
                        else:
                            dep_name = stripped.split()[0] if stripped.split() else ""
                            if dep_name:
                                deps.append(dep_name)
            except Exception:
                pass

        return sorted(set(deps))

    # ── Progress ───────────────────────────────────────────────────

    def set_indexing_progress(self, repo_id: str, progress: dict[str, Any]) -> None:
        self._active_progress[repo_id] = progress
        if repo_id in self._repositories:
            if "status" in progress:
                self._repositories[repo_id]["status"] = progress["status"]
            if "indexed_at" in progress:
                self._repositories[repo_id]["indexed_at"] = progress["indexed_at"]
            if "error" in progress and progress["error"]:
                self._repositories[repo_id]["error_message"] = progress["error"]
            self._save()

    def get_indexing_progress(self, repo_id: str) -> dict[str, Any]:
        if repo_id in self._active_progress:
            return self._active_progress[repo_id]

        repo = self.get_repository(repo_id)
        return {
            "status": repo.status,
            "stage": self._get_stage_label(repo.status),
            "processed_files": repo.file_count if repo.status == "indexed" else 0,
            "total_files": repo.file_count,
            "elapsed_ms": 0,
            "languages": repo.languages,
            "frameworks": repo.frameworks,
            "error": repo.error_message,
            "file_count": repo.file_count,
            "size_bytes": repo.size_bytes,
        }

    @staticmethod
    def _get_stage_label(status: str) -> str:
        labels = {
            "registered": "Ready to index",
            "scanning": "Scanning AST files...",
            "indexing": "Synthesizing vector embeddings...",
            "indexed": "Indexing Completed",
            "error": "Indexing Failed",
        }
        return labels.get(status, "Ready to index")

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _get_git_info(path: str) -> tuple[str, str | None]:
        branch = "main"
        commit_hash: str | None = None
        try:
            result = subprocess.run(
                ["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, check=True,
            )
            branch = result.stdout.strip() or "main"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        try:
            result = subprocess.run(
                ["git", "-C", path, "rev-parse", "HEAD"],
                capture_output=True, text=True, check=True,
            )
            commit_hash = result.stdout.strip() or None
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return branch, commit_hash
