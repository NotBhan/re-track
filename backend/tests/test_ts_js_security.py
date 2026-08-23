"""
Security and boundary tests for TypeScript / JavaScript structural analysis.

Verifies that:
1. Path traversal attacks escaping repository root via relative imports are rejected.
2. Malformed tsconfig.json configurations do not cause denial of service.
3. Giant source files with deep recursion / nesting are bounded.
"""

from pathlib import Path
import pytest

from app.services.parsers.treesitter_ts_analyzer import TreeSitterTSAnalyzer
from app.services.parsers.ts_grammar_cache import TSLanguageDialect
from app.services.parsers.ts_module_resolver import TSModuleResolver


def test_path_traversal_via_relative_import_blocked(tmp_path: Path) -> None:
    repo = tmp_path / "sandbox_repo"
    repo.mkdir()
    (repo / "src").mkdir()

    resolver = TSModuleResolver(repo)

    # Malicious attempt to escape workspace
    res = resolver.resolve_import("../../../../../etc/shadow", "src/index.ts")
    assert res.status == "unresolved"
    assert res.target_rel_path is None


def test_malformed_json_tsconfig_safety(tmp_path: Path) -> None:
    repo = tmp_path / "corrupt_repo"
    repo.mkdir()
    (repo / "tsconfig.json").write_text("{ unclosed json: [ 123", encoding="utf-8")

    resolver = TSModuleResolver(repo)
    # Should not raise exception; falls back gracefully
    assert resolver.tsconfig is not None


def test_deeply_nested_syntax_safety(tmp_path: Path) -> None:
    analyzer = TreeSitterTSAnalyzer()

    # Generate 50 levels of nested functions
    nested_code = "export function root() {\n" + ("function nested() {\n" * 40) + "return 42;\n" + ("}\n" * 41)
    payload = analyzer.parse_file("src/nested.ts", nested_code, TSLanguageDialect.TYPESCRIPT)

    assert payload.parse_status in ("ok", "partial")
    assert any(s.name == "root" for s in payload.symbols)
