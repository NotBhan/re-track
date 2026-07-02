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
    "venv", "__pycache__", ".venv",
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
    "mix.exs": "Elixir",
    "cabal.config": "Haskell",
    "pubspec.yaml": "Dart",
    "Makefile": "C/C++",
    "tsconfig.json": "TypeScript",
}


class RepositoryManager:
    """Manages repository CRUD, import, scan, and metadata persistence."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        if store_path is None:
            store_path = Path.home() / ".andes" / "repositories.json"
        self._store_path = Path(store_path)
        self._repositories: dict[str, dict[str, Any]] = {}
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self) -> None:
        if self._store_path.exists():
            data = json.loads(self._store_path.read_text())
            if isinstance(data, dict):
                self._repositories = data

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._store_path.write_text(json.dumps(self._repositories, indent=2))

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
            workspace = Path.home() / ".andes" / "repos"
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

        for root, dirs, files in Path(repo.local_path).walk():
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for f in files:
                p = Path(root) / f
                try:
                    size_bytes += p.stat().st_size
                except OSError:
                    continue
                file_count += 1
                ext = p.suffix.lower()
                if ext in EXTENSION_LANGUAGE_MAP:
                    languages.add(EXTENSION_LANGUAGE_MAP[ext])

            for marker, framework in FRAMEWORK_MARKERS.items():
                if (Path(root) / marker).exists():
                    frameworks.add(framework)

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
        d["status"] = "scanning"
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
