"""
Deterministic module and path resolution engine for TypeScript and JavaScript.

Supports relative imports, tsconfig/jsconfig baseUrl + paths alias mapping,
extension probing, index module resolution, and external package classification.
"""

from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import re
from typing import Optional

logger = logging.getLogger(__name__)

PROBING_EXTENSIONS = (
    "",
    ".ts",
    ".tsx",
    ".d.ts",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    "/index.ts",
    "/index.tsx",
    "/index.d.ts",
    "/index.js",
    "/index.jsx",
)


@dataclass
class ModuleResolutionResult:
    """Outcome of resolving an import/require specifier."""
    specifier: str
    target_rel_path: Optional[str] = None  # Canonical POSIX relative path if resolved
    status: str = "unresolved"  # resolved | external | unresolved | ambiguous
    is_external: bool = False
    is_type_definition: bool = False
    error_reason: Optional[str] = None


@dataclass
class TSConfigSettings:
    """Parsed and normalized tsconfig.json / jsconfig.json configuration."""
    base_url: Optional[Path] = None
    paths: dict[str, list[str]] = field(default_factory=dict)
    raw_config_path: Optional[Path] = None


class TSModuleResolver:
    """Resolves TypeScript / JavaScript import specifiers against local workspace files."""

    def __init__(self, repo_path: Path | str, known_files: Optional[set[str]] = None) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.known_files = known_files or set()
        self.tsconfig = self._load_tsconfig()

    def set_known_files(self, files: set[str]) -> None:
        """Update the set of known repository files (normalized POSIX paths)."""
        self.known_files = files

    def _strip_json_comments(self, content: str) -> str:
        """Strip single-line and multi-line comments and trailing commas from JSON/JSONC."""
        # Strip /* ... */
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        # Strip // ...
        content = re.sub(r"//.*", "", content)
        # Strip trailing commas before } or ]
        content = re.sub(r",\s*([\]}])", r"\1", content)
        return content

    def _load_tsconfig(self) -> TSConfigSettings:
        """Discover and parse tsconfig.json or jsconfig.json in the repository root."""
        for cfg_name in ("tsconfig.json", "jsconfig.json", "tsconfig.app.json"):
            cfg_file = self.repo_path / cfg_name
            if cfg_file.exists() and cfg_file.is_file():
                try:
                    text = cfg_file.read_text(encoding="utf-8", errors="ignore")
                    cleaned = self._strip_json_comments(text)
                    data = json.loads(cleaned)

                    opts = data.get("compilerOptions", {})
                    base_url_str = opts.get("baseUrl")
                    base_url = None
                    if base_url_str:
                        base_url = (cfg_file.parent / base_url_str).resolve()
                    else:
                        base_url = cfg_file.parent.resolve()

                    raw_paths = opts.get("paths", {})
                    normalized_paths: dict[str, list[str]] = {}
                    for pattern, targets in raw_paths.items():
                        if isinstance(targets, list):
                            normalized_paths[pattern] = [str(t) for t in targets]
                        elif isinstance(targets, str):
                            normalized_paths[pattern] = [targets]

                    logger.debug("Loaded %s | baseUrl=%s | paths=%d", cfg_name, base_url, len(normalized_paths))
                    return TSConfigSettings(
                        base_url=base_url,
                        paths=normalized_paths,
                        raw_config_path=cfg_file,
                    )
                except Exception as e:
                    logger.warning("Failed to parse %s (%s). Falling back to convention resolution.", cfg_name, e)

        return TSConfigSettings(base_url=self.repo_path)

    def resolve_import(self, specifier: str, importing_file_rel: str) -> ModuleResolutionResult:
        """Resolve an import specifier to a canonical POSIX relative path in the repository."""
        clean_spec = specifier.strip()
        if not clean_spec:
            return ModuleResolutionResult(specifier=specifier, status="unresolved")

        # 1. Relative Import Resolution (starts with ./ or ../)
        if clean_spec.startswith("./") or clean_spec.startswith("../"):
            return self._resolve_relative(clean_spec, importing_file_rel)

        # 2. tsconfig.json Paths Mapping Resolution
        if self.tsconfig and self.tsconfig.paths:
            path_res = self._resolve_tsconfig_paths(clean_spec)
            if path_res.status == "resolved":
                return path_res

        # 3. BaseURL Direct Resolution
        if self.tsconfig and self.tsconfig.base_url:
            base_res = self._resolve_base_url(clean_spec)
            if base_res.status == "resolved":
                return base_res

        # 4. Standard Convention Aliases (@/ -> src/ or ~/ -> src/)
        if clean_spec.startswith("@/") or clean_spec.startswith("~/"):
            convention_res = self._resolve_convention_alias(clean_spec)
            if convention_res.status == "resolved":
                return convention_res

        # 5. External Package Classification
        # If it doesn't start with . or @/ or ~/ and has no / or is scoped like @scope/pkg
        if not clean_spec.startswith(("/", "\\")):
            return ModuleResolutionResult(
                specifier=clean_spec,
                status="external",
                is_external=True,
            )

        return ModuleResolutionResult(specifier=clean_spec, status="unresolved")

    def _probe_file(self, candidate_rel_posix: str) -> Optional[str]:
        """Check if candidate path exists among known repository files with standard extensions."""
        norm_posix = Path(candidate_rel_posix).as_posix().lstrip("./")

        # If known_files set is populated, check membership first
        for ext in PROBING_EXTENSIONS:
            target = f"{norm_posix}{ext}"
            target_clean = Path(target).as_posix()
            if target_clean in self.known_files:
                return target_clean

        # Fallback to direct filesystem probe
        for ext in PROBING_EXTENSIONS:
            candidate_path = (self.repo_path / f"{norm_posix}{ext}").resolve()
            try:
                if candidate_path.is_file() and candidate_path.is_relative_to(self.repo_path):
                    rel = candidate_path.relative_to(self.repo_path).as_posix()
                    return rel
            except Exception:
                continue

        return None

    def _resolve_relative(self, specifier: str, importing_file_rel: str) -> ModuleResolutionResult:
        """Resolve a relative import against the importing file's directory."""
        importing_dir = Path(importing_file_rel).parent
        raw_candidate = importing_dir / specifier
        try:
            resolved_candidate = (self.repo_path / raw_candidate).resolve()
            # Security check: must not escape repository root
            if not resolved_candidate.is_relative_to(self.repo_path):
                return ModuleResolutionResult(
                    specifier=specifier,
                    status="unresolved",
                    error_reason="Path traversal outside workspace root rejected",
                )

            rel_posix = resolved_candidate.relative_to(self.repo_path).as_posix()
            matched = self._probe_file(rel_posix)
            if matched:
                return ModuleResolutionResult(
                    specifier=specifier,
                    target_rel_path=matched,
                    status="resolved",
                )
        except Exception as e:
            return ModuleResolutionResult(
                specifier=specifier,
                status="unresolved",
                error_reason=str(e),
            )

        return ModuleResolutionResult(specifier=specifier, status="unresolved")

    def _resolve_tsconfig_paths(self, specifier: str) -> ModuleResolutionResult:
        """Match and substitute tsconfig paths mappings."""
        base_dir = self.tsconfig.base_url or self.repo_path

        for pattern, targets in self.tsconfig.paths.items():
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if specifier.startswith(prefix):
                    sub = specifier[len(prefix):]
                    for target_tpl in targets:
                        replaced = target_tpl.replace("*", sub)
                        candidate = (base_dir / replaced).resolve()
                        try:
                            if not candidate.is_relative_to(self.repo_path):
                                continue
                            rel_posix = candidate.relative_to(self.repo_path).as_posix()
                            matched = self._probe_file(rel_posix)
                            if matched:
                                return ModuleResolutionResult(
                                    specifier=specifier,
                                    target_rel_path=matched,
                                    status="resolved",
                                )
                        except Exception:
                            continue
            elif pattern == specifier:
                for target in targets:
                    candidate = (base_dir / target).resolve()
                    try:
                        if not candidate.is_relative_to(self.repo_path):
                            continue
                        rel_posix = candidate.relative_to(self.repo_path).as_posix()
                        matched = self._probe_file(rel_posix)
                        if matched:
                            return ModuleResolutionResult(
                                specifier=specifier,
                                target_rel_path=matched,
                                status="resolved",
                            )
                    except Exception:
                        continue

        return ModuleResolutionResult(specifier=specifier, status="unresolved")

    def _resolve_base_url(self, specifier: str) -> ModuleResolutionResult:
        """Resolve specifier directly against compilerOptions.baseUrl."""
        base_dir = self.tsconfig.base_url or self.repo_path
        candidate = (base_dir / specifier).resolve()
        try:
            if candidate.is_relative_to(self.repo_path):
                rel_posix = candidate.relative_to(self.repo_path).as_posix()
                matched = self._probe_file(rel_posix)
                if matched:
                    return ModuleResolutionResult(
                        specifier=specifier,
                        target_rel_path=matched,
                        status="resolved",
                    )
        except Exception:
            pass

        return ModuleResolutionResult(specifier=specifier, status="unresolved")

    def _resolve_convention_alias(self, specifier: str) -> ModuleResolutionResult:
        """Resolve standard convention aliases (@/ -> src/ or app/, ~/ -> src/)."""
        stripped = specifier.lstrip("@/").lstrip("~/")
        for candidate_root in ("src", "app", ""):
            cand = f"{candidate_root}/{stripped}".lstrip("/")
            matched = self._probe_file(cand)
            if matched:
                return ModuleResolutionResult(
                    specifier=specifier,
                    target_rel_path=matched,
                    status="resolved",
                )

        return ModuleResolutionResult(specifier=specifier, status="unresolved")
