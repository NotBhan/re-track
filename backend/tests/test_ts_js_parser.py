"""
Unit tests for TreeSitterTSAnalyzer.

Verifies deterministic concrete syntax tree parsing and symbol/import/export/relationship
extraction across TypeScript, TSX, JavaScript, and JSX files.
"""

from pathlib import Path
import pytest

from app.services.parsers.treesitter_ts_analyzer import TreeSitterTSAnalyzer
from app.services.parsers.ts_grammar_cache import TSLanguageDialect


@pytest.fixture
def analyzer() -> TreeSitterTSAnalyzer:
    return TreeSitterTSAnalyzer()


def test_ts_function_extraction(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    export async function calculateMetrics(data: number[], threshold: number = 0.5): Promise<Metrics> {
        // Calculate result
        return { total: data.length, pass: true };
    }
    """
    payload = analyzer.parse_file("src/utils/metrics.ts", code, TSLanguageDialect.TYPESCRIPT)
    assert payload.parse_status == "ok"
    assert len(payload.symbols) == 1
    sym = payload.symbols[0]
    assert sym.name == "calculateMetrics"
    assert sym.kind == "async_function"
    assert sym.exported is True
    assert sym.id == "src/utils/metrics.ts#calculateMetrics"
    assert sym.span.start_line == 2


def test_ts_class_and_methods(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    export class AuthService extends BaseAuth implements IAuthenticator {
        private secret: string;

        constructor(secret: string) {
            this.secret = secret;
        }

        public async verifyToken(token: string): Promise<boolean> {
            return validate(token);
        }
    }
    """
    payload = analyzer.parse_file("src/services/auth.ts", code, TSLanguageDialect.TYPESCRIPT)
    assert payload.parse_status == "ok"
    sym_map = {s.name: s for s in payload.symbols}
    assert "AuthService" in sym_map
    assert sym_map["AuthService"].kind == "class"
    assert sym_map["AuthService"].exported is True

    assert "verifyToken" in sym_map
    assert sym_map["verifyToken"].kind == "async_function"
    assert sym_map["verifyToken"].id == "src/services/auth.ts#AuthService.verifyToken"

    # Heritage relations
    extends_rel = [r for r in payload.relationships if r.relation == "extends"]
    assert len(extends_rel) >= 1
    assert extends_rel[0].target_name == "BaseAuth"

    implements_rel = [r for r in payload.relationships if r.relation == "implements"]
    assert len(implements_rel) >= 1
    assert implements_rel[0].target_name == "IAuthenticator"

    # Method call
    call_rel = [r for r in payload.relationships if r.relation == "calls"]
    assert any(r.target_name == "validate" for r in call_rel)


def test_interface_and_type_alias(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    export interface UserProfile extends BaseEntity {
        id: string;
        username: string;
    }

    export type UserRole = "admin" | "member" | UserProfile;
    """
    payload = analyzer.parse_file("src/types/user.ts", code, TSLanguageDialect.TYPESCRIPT)
    assert payload.parse_status == "ok"
    sym_map = {s.name: s for s in payload.symbols}
    assert "UserProfile" in sym_map
    assert sym_map["UserProfile"].kind == "interface"
    assert "UserRole" in sym_map
    assert sym_map["UserRole"].kind == "type"

    # Interface extends
    extends_rel = [r for r in payload.relationships if r.relation == "extends"]
    assert len(extends_rel) == 1
    assert extends_rel[0].target_name == "BaseEntity"


def test_enum_extraction(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    export enum OrderStatus {
        Pending = "PENDING",
        Completed = "COMPLETED",
        Failed = "FAILED"
    }
    """
    payload = analyzer.parse_file("src/models/order.ts", code, TSLanguageDialect.TYPESCRIPT)
    assert payload.parse_status == "ok"
    assert len(payload.symbols) == 1
    assert payload.symbols[0].name == "OrderStatus"
    assert payload.symbols[0].kind == "enum"
    assert payload.symbols[0].exported is True


def test_generic_function_and_decorators(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    export function identity<T>(arg: T): T {
        return arg;
    }

    @Injectable()
    export class Repository<T> {
        public find(): T[] {
            return [];
        }
    }
    """
    payload = analyzer.parse_file("src/repo.ts", code, TSLanguageDialect.TYPESCRIPT)
    assert payload.parse_status == "ok"
    sym_map = {s.name: s for s in payload.symbols}
    assert "identity" in sym_map
    assert "Repository" in sym_map
    assert "find" in sym_map


def test_javascript_and_arrow_functions(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    const helper = (a, b) => a + b;
    export const multiply = function(x, y) {
        return x * y;
    };
    export default helper;
    """
    payload = analyzer.parse_file("src/math.js", code, TSLanguageDialect.JAVASCRIPT)
    assert payload.parse_status == "ok"
    sym_map = {s.name: s for s in payload.symbols}
    assert "helper" in sym_map
    assert "multiply" in sym_map
    assert sym_map["multiply"].exported is True


def test_commonjs_require_and_exports(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    const path = require('path');
    const db = require('./database');

    function connect() {
        return db.init();
    }

    module.exports = connect;
    exports.status = 'ready';
    """
    payload = analyzer.parse_file("lib/connector.cjs", code, TSLanguageDialect.JAVASCRIPT)
    assert payload.parse_status == "ok"
    # Imports extracted from require()
    import_mods = {i.source_module: i.local_name for i in payload.imports}
    assert "path" in import_mods
    assert "./database" in import_mods

    # Exports extracted
    exp_names = {e.exported_name: e.local_name for e in payload.exports}
    assert "default" in exp_names
    assert "status" in exp_names


def test_tsx_component_and_jsx_renders(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    import React from 'react';
    import { Button } from './Button';
    import { Dialog } from './Dialog';

    export const ContextStudio: React.FC = () => {
        const handleClick = () => logEvent('clicked');
        return (
            <div className="studio">
                <Button onClick={handleClick}>Run</Button>
                <Dialog.Root>
                    <span>Modal</span>
                </Dialog.Root>
            </div>
        );
    };
    """
    payload = analyzer.parse_file("src/pages/ContextStudio.tsx", code, TSLanguageDialect.TSX)
    assert payload.parse_status == "ok"
    sym_map = {s.name: s for s in payload.symbols}
    assert "ContextStudio" in sym_map
    assert sym_map["ContextStudio"].kind == "component"
    assert sym_map["ContextStudio"].exported is True

    # JSX Renders (excluding 'div' and 'span')
    renders = [r for r in payload.relationships if r.relation == "jsx_renders"]
    rendered_tags = {r.target_name for r in renders}
    assert "Button" in rendered_tags
    assert "Dialog.Root" in rendered_tags
    assert "div" not in rendered_tags
    assert "span" not in rendered_tags


def test_syntax_error_recovery(analyzer: TreeSitterTSAnalyzer) -> None:
    code = """
    export function validFunctionOne() {
        return 1;
    }

    // Malformed syntax below
    export class IncompleteClass {
        broken syntax ??? !!!
    }

    export function validFunctionTwo() {
        return 2;
    }
    """
    payload = analyzer.parse_file("src/broken.ts", code, TSLanguageDialect.TYPESCRIPT)
    assert payload.has_syntax_errors is True
    assert payload.parse_status == "partial"

    # Verify that valid symbols before and after the syntax error were successfully extracted
    sym_names = {s.name for s in payload.symbols}
    assert "validFunctionOne" in sym_names
    assert "validFunctionTwo" in sym_names
