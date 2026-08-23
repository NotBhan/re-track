"""
Tests for TSCrossFileLinker.

Verifies cross-file symbol linking, class inheritance, interface implementation,
barrel re-export chains, namespace calls, and JSX component render graphs.
"""

from pathlib import Path
import pytest

from app.services.parsers.treesitter_ts_analyzer import TreeSitterTSAnalyzer
from app.services.parsers.ts_cross_file_linker import TSCrossFileLinker
from app.services.parsers.ts_grammar_cache import TSLanguageDialect
from app.services.parsers.ts_module_resolver import TSModuleResolver


@pytest.fixture
def multi_file_project(tmp_path: Path) -> tuple[TSModuleResolver, TreeSitterTSAnalyzer]:
    repo = tmp_path / "cross_file_repo"
    repo.mkdir()
    (repo / "src" / "services").mkdir(parents=True)
    (repo / "src" / "components").mkdir(parents=True)
    (repo / "src" / "lib").mkdir(parents=True)
    (repo / "src" / "types").mkdir(parents=True)

    resolver = TSModuleResolver(repo)
    analyzer = TreeSitterTSAnalyzer()
    return resolver, analyzer


def test_cross_file_function_call(multi_file_project: tuple[TSModuleResolver, TreeSitterTSAnalyzer]) -> None:
    resolver, analyzer = multi_file_project

    util_code = """
    export function formatCurrency(amount: number): string {
        return "$" + amount.toFixed(2);
    }
    """
    service_code = """
    import { formatCurrency } from '../lib/util';

    export function calculateTotal(items: number[]): string {
        const sum = items.reduce((a, b) => a + b, 0);
        return formatCurrency(sum);
    }
    """

    mod_util = analyzer.parse_file("src/lib/util.ts", util_code, TSLanguageDialect.TYPESCRIPT)
    mod_svc = analyzer.parse_file("src/services/billing.ts", service_code, TSLanguageDialect.TYPESCRIPT)

    parsed = {"src/lib/util.ts": mod_util, "src/services/billing.ts": mod_svc}
    resolver.set_known_files(set(parsed.keys()))

    linker = TSCrossFileLinker(resolver)
    nodes, edges, stats = linker.link_modules(parsed)

    assert stats.resolved_edges >= 1
    assert any(
        e.source == "src/services/billing.ts#calculateTotal"
        and e.target == "src/lib/util.ts#formatCurrency"
        and e.kind == "calls"
        for e in edges
    )


def test_cross_file_class_inheritance(multi_file_project: tuple[TSModuleResolver, TreeSitterTSAnalyzer]) -> None:
    resolver, analyzer = multi_file_project

    base_code = """
    export class BaseService {
        public log(msg: string): void {}
    }
    """
    derived_code = """
    import { BaseService } from './base';

    export class UserService extends BaseService {
        public getUser(): string {
            return "user";
        }
    }
    """

    mod_base = analyzer.parse_file("src/services/base.ts", base_code, TSLanguageDialect.TYPESCRIPT)
    mod_derived = analyzer.parse_file("src/services/user.ts", derived_code, TSLanguageDialect.TYPESCRIPT)

    parsed = {"src/services/base.ts": mod_base, "src/services/user.ts": mod_derived}
    resolver.set_known_files(set(parsed.keys()))

    linker = TSCrossFileLinker(resolver)
    nodes, edges, stats = linker.link_modules(parsed)

    assert any(
        e.source == "src/services/user.ts#UserService"
        and e.target == "src/services/base.ts#BaseService"
        and e.kind == "inherits"
        for e in edges
    )


def test_cross_file_barrel_reexport(multi_file_project: tuple[TSModuleResolver, TreeSitterTSAnalyzer]) -> None:
    resolver, analyzer = multi_file_project

    btn_code = "export const Button = () => null;"
    barrel_code = "export * from './Button';"
    page_code = """
    import { Button } from '../components';

    export const HomePage = () => {
        return <Button />;
    };
    """

    mod_btn = analyzer.parse_file("src/components/Button.tsx", btn_code, TSLanguageDialect.TSX)
    mod_barrel = analyzer.parse_file("src/components/index.ts", barrel_code, TSLanguageDialect.TYPESCRIPT)
    mod_page = analyzer.parse_file("src/pages/Home.tsx", page_code, TSLanguageDialect.TSX)

    parsed = {
        "src/components/Button.tsx": mod_btn,
        "src/components/index.ts": mod_barrel,
        "src/pages/Home.tsx": mod_page,
    }
    resolver.set_known_files(set(parsed.keys()))

    linker = TSCrossFileLinker(resolver)
    nodes, edges, stats = linker.link_modules(parsed)

    assert any(
        e.source == "src/pages/Home.tsx#HomePage"
        and e.target == "src/components/Button.tsx#Button"
        and e.kind == "renders"
        for e in edges
    )


def test_namespace_import_calls(multi_file_project: tuple[TSModuleResolver, TreeSitterTSAnalyzer]) -> None:
    resolver, analyzer = multi_file_project

    api_code = """
    export function fetchUser(id: string) { return id; }
    export function deleteUser(id: string) { return true; }
    """
    client_code = """
    import * as API from './api';

    export function execute() {
        API.fetchUser('123');
    }
    """

    mod_api = analyzer.parse_file("src/api.ts", api_code, TSLanguageDialect.TYPESCRIPT)
    mod_client = analyzer.parse_file("src/client.ts", client_code, TSLanguageDialect.TYPESCRIPT)

    parsed = {"src/api.ts": mod_api, "src/client.ts": mod_client}
    resolver.set_known_files(set(parsed.keys()))

    linker = TSCrossFileLinker(resolver)
    nodes, edges, stats = linker.link_modules(parsed)

    assert any(
        e.source == "src/client.ts#execute"
        and e.target == "src/api.ts#fetchUser"
        and e.kind == "calls"
        for e in edges
    )
