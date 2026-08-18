"""Tests for deterministic AST call graph extraction and invariants."""

import tempfile
from pathlib import Path
from app.services.repository_summary import RepositorySummaryGenerator


def test_python_ast_import_and_call_resolution():
    """Verify that Python internal calls and aliases resolve deterministically."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # File 1: services/auth.py
        auth_file = root / "services" / "auth.py"
        auth_file.parent.mkdir(parents=True, exist_ok=True)
        auth_file.write_text("""
class AuthService:
    def authenticate(self, token: str) -> bool:
        return True

def verify_token(token: str) -> bool:
    return True
""")

        # File 2: handlers/login.py
        login_file = root / "handlers" / "login.py"
        login_file.parent.mkdir(parents=True, exist_ok=True)
        login_file.write_text("""
from services.auth import verify_token as check_token, AuthService

def handle_login(req):
    check_token(req.token)
    service = AuthService()

class LoginHandler(AuthService):
    def post(self):
        self.authenticate("test")
""")

        gen = RepositorySummaryGenerator()
        files = [auth_file, login_file]
        summary = gen.generate(root, files)

        node_ids = {n.id for n in summary.call_graph_nodes}
        assert len(summary.call_graph_nodes) > 0

        # Invariant 1: All edge endpoints exist in nodes
        for e in summary.call_graph_edges:
            assert e.source in node_ids, f"Edge source {e.source} not in nodes"
            assert e.target in node_ids, f"Edge target {e.target} not in nodes"
            assert e.source != e.target, f"Self-loop edge {e.source}"

        # Invariant 2: Import alias check_token resolves to services.auth.verify_token
        call_edges = [e for e in summary.call_graph_edges if e.kind == "calls"]
        assert any(e.source == "handlers.login.handle_login" and e.target == "services.auth.verify_token" for e in call_edges)

        # Invariant 3: Class inheritance resolves to services.auth.AuthService
        inherit_edges = [e for e in summary.call_graph_edges if e.kind == "inherits"]
        assert any(e.source == "handlers.login.LoginHandler" and e.target == "services.auth.AuthService" for e in inherit_edges)


def test_python_parameter_and_variable_shadowing():
    """Verify that parameters and locally shadowed variables produce UNRESOLVED (no edge)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        svc_file = root / "service.py"
        svc_file.write_text("""
def process():
    return "ok"
""")

        caller_file = root / "caller.py"
        caller_file.write_text("""
from service import process

def param_shadow(process):
    # Parameter shadows imported symbol -> must produce 0 edges
    process()

def var_shadow():
    # Local variable shadows imported symbol -> must produce 0 edges
    process = lambda: 123
    process()
""")

        gen = RepositorySummaryGenerator()
        summary = gen.generate(root, [svc_file, caller_file])

        edges_for_shadows = [
            e for e in summary.call_graph_edges
            if e.source in ("caller.param_shadow", "caller.var_shadow")
        ]
        assert len(edges_for_shadows) == 0, f"Shadowed variables incorrectly generated edges: {edges_for_shadows}"


def test_python_ambiguous_symbols_produce_no_edge():
    """Verify that ambiguous same-name symbols across modules produce 0 edges without explicit import."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        mod_a = root / "module_a.py"
        mod_a.write_text("def execute_task(): pass")

        mod_b = root / "module_b.py"
        mod_b.write_text("def execute_task(): pass")

        mod_c = root / "module_c.py"
        mod_c.write_text("""
def runner():
    # execute_task is not imported and exists in multiple modules -> ambiguous
    execute_task()
""")

        gen = RepositorySummaryGenerator()
        summary = gen.generate(root, [mod_a, mod_b, mod_c])

        runner_edges = [e for e in summary.call_graph_edges if e.source == "module_c.runner"]
        assert len(runner_edges) == 0, f"Ambiguous symbol produced an edge: {runner_edges}"


def test_typescript_react_path_aliases_and_jsx_renders():
    """Verify that Next.js / TypeScript @/ path aliases and JSX renders resolve correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # File 1: src/components/button.tsx
        btn_file = root / "src" / "components" / "button.tsx"
        btn_file.parent.mkdir(parents=True, exist_ok=True)
        btn_file.write_text("""
export function Button() {
    return <button>Click</button>;
}
""")

        # File 2: src/app/page.tsx
        page_file = root / "src" / "app" / "page.tsx"
        page_file.parent.mkdir(parents=True, exist_ok=True)
        page_file.write_text("""
import { Button } from '@/components/button';

export default function Home() {
    return (
        <div>
            <Button />
        </div>
    );
}
""")

        gen = RepositorySummaryGenerator()
        summary = gen.generate(root, [btn_file, page_file])

        node_ids = {n.id for n in summary.call_graph_nodes}
        assert len(summary.call_graph_nodes) >= 2

        for e in summary.call_graph_edges:
            assert e.source in node_ids, f"Edge source {e.source} not in nodes"
            assert e.target in node_ids, f"Edge target {e.target} not in nodes"

        # Check imports edge
        import_edges = [e for e in summary.call_graph_edges if e.kind == "imports"]
        assert any(e.target == "src/components/button.tsx#Button" for e in import_edges)

        # Check renders edge
        render_edges = [e for e in summary.call_graph_edges if e.kind == "renders"]
        assert any(e.target == "src/components/button.tsx#Button" for e in render_edges)
