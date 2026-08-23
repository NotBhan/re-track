"""
Tests for TSModuleResolver.

Verifies deterministic module and path resolution across relative paths,
tsconfig paths mappings, index files, extension probing, and external packages.
"""

import json
from pathlib import Path
import pytest

from app.services.parsers.ts_module_resolver import TSModuleResolver


@pytest.fixture
def mock_ts_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "ts_project"
    repo.mkdir()

    # Create directory structure
    (repo / "src" / "services").mkdir(parents=True)
    (repo / "src" / "components" / "Button").mkdir(parents=True)
    (repo / "src" / "utils").mkdir(parents=True)
    (repo / "src" / "types").mkdir(parents=True)

    # Create files
    (repo / "src" / "services" / "auth.ts").write_text("export class AuthService {}", encoding="utf-8")
    (repo / "src" / "components" / "Button" / "index.tsx").write_text("export const Button = () => null;", encoding="utf-8")
    (repo / "src" / "utils" / "format.js").write_text("export function formatDate() {}", encoding="utf-8")
    (repo / "src" / "types" / "user.d.ts").write_text("export interface User {}", encoding="utf-8")

    # tsconfig.json with baseUrl and paths
    tsconfig = {
        "compilerOptions": {
            "baseUrl": ".",
            "paths": {
                "@/*": ["src/*"],
                "@components/*": ["src/components/*", "src/shared/*"]
            }
        }
    }
    (repo / "tsconfig.json").write_text(json.dumps(tsconfig), encoding="utf-8")

    return repo


def test_relative_import_resolution(mock_ts_repo: Path) -> None:
    resolver = TSModuleResolver(mock_ts_repo)

    # From src/services/auth.ts to ../utils/format
    res = resolver.resolve_import("../utils/format", "src/services/auth.ts")
    assert res.status == "resolved"
    assert res.target_rel_path == "src/utils/format.js"


def test_extension_probing(mock_ts_repo: Path) -> None:
    resolver = TSModuleResolver(mock_ts_repo)

    # No extension provided -> resolves to .ts
    res = resolver.resolve_import("./auth", "src/services/other.ts")
    assert res.status == "resolved"
    assert res.target_rel_path == "src/services/auth.ts"

    # Type definition probing
    res_dts = resolver.resolve_import("../types/user", "src/services/auth.ts")
    assert res_dts.status == "resolved"
    assert res_dts.target_rel_path == "src/types/user.d.ts"


def test_index_module_resolution(mock_ts_repo: Path) -> None:
    resolver = TSModuleResolver(mock_ts_repo)

    # Resolves to directory index: ./Button -> src/components/Button/index.tsx
    res = resolver.resolve_import("./Button", "src/components/App.tsx")
    assert res.status == "resolved"
    assert res.target_rel_path == "src/components/Button/index.tsx"


def test_tsconfig_paths_alias_resolution(mock_ts_repo: Path) -> None:
    resolver = TSModuleResolver(mock_ts_repo)

    # Path alias @/* -> src/*
    res = resolver.resolve_import("@/services/auth", "src/pages/Home.tsx")
    assert res.status == "resolved"
    assert res.target_rel_path == "src/services/auth.ts"

    # Multi-target path alias @components/* -> src/components/*
    res_comp = resolver.resolve_import("@components/Button", "src/pages/Home.tsx")
    assert res_comp.status == "resolved"
    assert res_comp.target_rel_path == "src/components/Button/index.tsx"


def test_external_package_classification(mock_ts_repo: Path) -> None:
    resolver = TSModuleResolver(mock_ts_repo)

    res_react = resolver.resolve_import("react", "src/pages/Home.tsx")
    assert res_react.status == "external"
    assert res_react.is_external is True

    res_lucide = resolver.resolve_import("lucide-react", "src/pages/Home.tsx")
    assert res_lucide.status == "external"


def test_malformed_tsconfig_fallback(tmp_path: Path) -> None:
    repo = tmp_path / "broken_tsconfig"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "src" / "util.ts").write_text("export const x = 1;", encoding="utf-8")
    (repo / "tsconfig.json").write_text("{ invalid json !! // comment", encoding="utf-8")

    resolver = TSModuleResolver(repo)
    # Falls back to standard convention @/ -> src/
    res = resolver.resolve_import("@/util", "src/main.ts")
    assert res.status == "resolved"
    assert res.target_rel_path == "src/util.ts"


def test_path_traversal_rejection(mock_ts_repo: Path) -> None:
    resolver = TSModuleResolver(mock_ts_repo)

    # Attempt to escape workspace root via relative path
    res = resolver.resolve_import("../../../etc/passwd", "src/services/auth.ts")
    assert res.status == "unresolved"
    assert res.target_rel_path is None
