"""
Tree-sitter Concrete Syntax Tree (CST) analyzer for TypeScript, TSX, JavaScript, and JSX.

Extracts symbols, types, classes, methods, imports, exports, re-exports,
call invocations, class inheritance, interface implementation, and JSX render trees.
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
from typing import Any, Optional

from tree_sitter import Node, Tree

from app.services.parsers.ts_grammar_cache import TSGrammarCache, TSLanguageDialect

logger = logging.getLogger(__name__)

# Common HTML/SVG intrinsic tags to ignore during JSX component resolution
INTRINSIC_HTML_TAGS = {
    "a", "abbr", "address", "area", "article", "aside", "audio", "b", "base", "bdi", "bdo",
    "blockquote", "body", "br", "button", "canvas", "caption", "cite", "code", "col",
    "colgroup", "data", "datalist", "dd", "del", "details", "dfn", "dialog", "div", "dl",
    "dt", "em", "embed", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
    "h3", "h4", "h5", "h6", "head", "header", "hgroup", "hr", "html", "i", "iframe", "img",
    "input", "ins", "kbd", "label", "legend", "li", "link", "main", "map", "mark", "menu",
    "meta", "meter", "nav", "noscript", "object", "ol", "optgroup", "option", "output", "p",
    "param", "picture", "pre", "progress", "q", "rp", "rt", "ruby", "s", "samp", "script",
    "section", "select", "slot", "small", "source", "span", "strong", "style", "sub", "summary",
    "sup", "table", "tbody", "td", "template", "textarea", "tfoot", "th", "thead", "time",
    "title", "tr", "track", "u", "ul", "var", "video", "wbr",
    # Common SVG tags
    "svg", "path", "circle", "rect", "line", "polyline", "polygon", "g", "defs", "clippath",
    "text", "use", "symbol", "lineargradient", "radialgradient", "stop", "mask", "pattern"
}

PASCAL_CASE_RE = re.compile(r"^[A-Z][A-Za-z0-9_]*$")


@dataclass
class SourceSpan:
    """Precise source location span."""
    start_line: int
    start_col: int
    end_line: int
    end_col: int

    def to_dict(self) -> dict[str, int]:
        return {
            "start_line": self.start_line,
            "start_col": self.start_col,
            "end_line": self.end_line,
            "end_col": self.end_col,
        }

    @classmethod
    def from_node(cls, node: Node) -> "SourceSpan":
        return cls(
            start_line=node.start_point[0] + 1,
            start_col=node.start_point[1],
            end_line=node.end_point[0] + 1,
            end_col=node.end_point[1],
        )


@dataclass
class ExtractedSymbol:
    """Canonical symbol extracted from syntax tree."""
    id: str  # Deterministic qualified ID: "rel_path#Symbol" or "rel_path#Class.method"
    name: str  # Short symbol name
    qualified_name: str  # Qualified name within file
    kind: str  # function | async_function | class | method | interface | type | enum | variable | component | namespace
    file: str  # Relative POSIX path
    span: SourceSpan
    exported: bool = False
    is_default_export: bool = False
    docstring: Optional[str] = None
    container: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "file": self.file,
            "span": self.span.to_dict(),
            "exported": self.exported,
            "is_default_export": self.is_default_export,
            "docstring": self.docstring,
            "container": self.container,
        }


@dataclass
class ExtractedImport:
    """Import statement extracted from source."""
    source_module: str  # Raw path/module string
    imported_name: str  # "default", named symbol, or "*"
    local_name: str  # Local binding
    file: str
    span: SourceSpan
    is_type_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_module": self.source_module,
            "imported_name": self.imported_name,
            "local_name": self.local_name,
            "file": self.file,
            "span": self.span.to_dict(),
            "is_type_only": self.is_type_only,
        }


@dataclass
class ExtractedExport:
    """Export declaration extracted from source."""
    exported_name: str  # "default" or exported symbol name
    local_name: str  # Local symbol name
    file: str
    source_module: Optional[str] = None  # Non-null for re-exports
    is_type_only: bool = False
    span: Optional[SourceSpan] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "exported_name": self.exported_name,
            "local_name": self.local_name,
            "file": self.file,
            "source_module": self.source_module,
            "is_type_only": self.is_type_only,
            "span": self.span.to_dict() if self.span else None,
        }


@dataclass
class ExtractedRelationship:
    """Structural or call relationship originating from a symbol or file."""
    source_id: str
    target_name: str
    relation: str  # calls | imports | re_exports | extends | implements | type_reference | jsx_renders | instantiates
    target_id: Optional[str] = None
    resolution_status: str = "unresolved"  # resolved | unresolved | ambiguous | external
    span: Optional[SourceSpan] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_name": self.target_name,
            "relation": self.relation,
            "target_id": self.target_id,
            "resolution_status": self.resolution_status,
            "span": self.span.to_dict() if self.span else None,
        }


@dataclass
class ParsedModulePayload:
    """Complete parsed structural payload for a TypeScript/JavaScript module."""
    rel_path: str
    dialect: TSLanguageDialect
    symbols: list[ExtractedSymbol] = field(default_factory=list)
    imports: list[ExtractedImport] = field(default_factory=list)
    exports: list[ExtractedExport] = field(default_factory=list)
    relationships: list[ExtractedRelationship] = field(default_factory=list)
    has_syntax_errors: bool = False
    parse_status: str = "ok"  # ok | partial | failed
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rel_path": self.rel_path,
            "dialect": self.dialect.value,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": [i.to_dict() for i in self.imports],
            "exports": [e.to_dict() for e in self.exports],
            "relationships": [r.to_dict() for r in self.relationships],
            "has_syntax_errors": self.has_syntax_errors,
            "parse_status": self.parse_status,
            "error_message": self.error_message,
        }


class TreeSitterTSAnalyzer:
    """Deterministic AST/CST analyzer for TypeScript, TSX, JavaScript, and JSX."""

    def __init__(self, grammar_cache: Optional[TSGrammarCache] = None) -> None:
        self._grammar_cache = grammar_cache or TSGrammarCache.get_instance()

    def parse_file(
        self,
        rel_path: str,
        code: str | bytes,
        dialect: Optional[TSLanguageDialect] = None,
    ) -> ParsedModulePayload:
        """Parse source code into structured symbols, imports, exports, and relationships."""
        code_bytes = code.encode("utf-8") if isinstance(code, str) else code
        if dialect is None:
            dialect = self._grammar_cache.detect_dialect(rel_path) or TSLanguageDialect.TYPESCRIPT

        parser = self._grammar_cache.create_parser(dialect)
        tree = parser.parse(code_bytes)

        if tree is None or tree.root_node is None:
            return ParsedModulePayload(
                rel_path=rel_path,
                dialect=dialect,
                parse_status="failed",
                error_message="Tree-sitter parser failed to produce root node",
            )

        has_error = tree.root_node.has_error
        parse_status = "partial" if has_error else "ok"

        symbols: list[ExtractedSymbol] = []
        imports: list[ExtractedImport] = []
        exports: list[ExtractedExport] = []
        relationships: list[ExtractedRelationship] = []

        walker = _ModuleCSTWalker(rel_path, code_bytes, dialect)
        walker.walk(tree.root_node)

        return ParsedModulePayload(
            rel_path=rel_path,
            dialect=dialect,
            symbols=walker.symbols,
            imports=walker.imports,
            exports=walker.exports,
            relationships=walker.relationships,
            has_syntax_errors=has_error,
            parse_status=parse_status,
        )


class _ModuleCSTWalker:
    """Internal recursive walker extracting symbols and references from Tree-sitter CST."""

    def __init__(self, rel_path: str, code_bytes: bytes, dialect: TSLanguageDialect) -> None:
        self.rel_path = rel_path
        self.code_bytes = code_bytes
        self.dialect = dialect
        self.symbols: list[ExtractedSymbol] = []
        self.imports: list[ExtractedImport] = []
        self.exports: list[ExtractedExport] = []
        self.relationships: list[ExtractedRelationship] = []
        self._current_container: Optional[str] = None
        self._current_symbol_id: Optional[str] = None

    def text(self, node: Node) -> str:
        """Get source slice for a syntax node."""
        return self.code_bytes[node.start_byte:node.end_byte].decode("utf-8", "ignore")

    def walk(self, root: Node) -> None:
        """Walk the top-level statements of the module."""
        for child in root.children:
            self._visit_top_level_statement(child)

    def _visit_top_level_statement(self, node: Node, is_exported: bool = False, is_default: bool = False) -> None:
        ntype = node.type

        # Handle export statements
        if ntype == "export_statement":
            is_def = False
            for c in node.children:
                if c.type == "default":
                    is_def = True
                elif c.type in (
                    "function_declaration", "class_declaration", "abstract_class_declaration",
                    "interface_declaration", "type_alias_declaration", "enum_declaration",
                    "lexical_declaration", "variable_declaration"
                ):
                    self._visit_top_level_statement(c, is_exported=True, is_default=is_def)
                elif c.type == "export_clause":
                    self._extract_export_clause(c, node)
                elif c.type in ("identifier", "call_expression"):
                    # export default Ident;
                    id_text = self.text(c).strip()
                    self.exports.append(
                        ExtractedExport(
                            exported_name="default",
                            local_name=id_text,
                            file=self.rel_path,
                            span=SourceSpan.from_node(node),
                        )
                    )
            # Check for export * from '...'
            self._extract_export_all(node)
            return

        # Handle import statements
        if ntype == "import_statement":
            self._extract_import_statement(node)
            return

        # Handle interfaces
        if ntype == "interface_declaration":
            self._extract_interface(node, is_exported, is_default)
            return

        # Handle type aliases
        if ntype == "type_alias_declaration":
            self._extract_type_alias(node, is_exported, is_default)
            return

        # Handle enums
        if ntype == "enum_declaration":
            self._extract_enum(node, is_exported, is_default)
            return

        # Handle classes
        if ntype in ("class_declaration", "abstract_class_declaration"):
            self._extract_class(node, is_exported, is_default)
            return

        # Handle function declarations
        if ntype == "function_declaration":
            self._extract_function(node, is_exported, is_default)
            return

        # Handle lexical declarations (const/let/var)
        if ntype in ("lexical_declaration", "variable_declaration"):
            self._extract_lexical_declaration(node, is_exported, is_default)
            return

        # Handle CommonJS require & module.exports expression statements
        if ntype == "expression_statement":
            self._extract_expression_statement(node)
            return

    def _extract_import_statement(self, node: Node) -> None:
        """Extract ESM import clauses and sources."""
        source_module = ""
        is_type_only = False

        for c in node.children:
            if c.type == "type":
                is_type_only = True
            elif c.type == "string":
                # Strip quotes
                source_module = self.text(c).strip("'\"")
            elif c.type == "import_clause":
                for ic in c.children:
                    if ic.type == "type":
                        is_type_only = True
                    elif ic.type == "identifier":
                        # Default import: import React from 'react'
                        local = self.text(ic).strip()
                        self.imports.append(
                            ExtractedImport(
                                source_module=source_module,
                                imported_name="default",
                                local_name=local,
                                file=self.rel_path,
                                span=SourceSpan.from_node(ic),
                                is_type_only=is_type_only,
                            )
                        )
                    elif ic.type == "namespace_import":
                        # Namespace import: import * as Utils from './utils'
                        for nc in ic.children:
                            if nc.type == "identifier":
                                local = self.text(nc).strip()
                                self.imports.append(
                                    ExtractedImport(
                                        source_module=source_module,
                                        imported_name="*",
                                        local_name=local,
                                        file=self.rel_path,
                                        span=SourceSpan.from_node(ic),
                                        is_type_only=is_type_only,
                                    )
                                )
                    elif ic.type == "named_imports":
                        for spec in ic.children:
                            if spec.type == "import_specifier":
                                self._extract_import_specifier(spec, source_module, is_type_only)

        # Fix source_module if string was parsed after import_clause
        if source_module:
            for imp in self.imports:
                if imp.file == self.rel_path and not imp.source_module:
                    imp.source_module = source_module

    def _extract_import_specifier(self, spec: Node, source_module: str, is_type_only: bool) -> None:
        spec_type = is_type_only
        name = ""
        alias = ""
        for c in spec.children:
            if c.type == "type":
                spec_type = True
            elif c.type == "identifier":
                if not name:
                    name = self.text(c).strip()
                else:
                    alias = self.text(c).strip()

        local_name = alias if alias else name
        if name:
            self.imports.append(
                ExtractedImport(
                    source_module=source_module,
                    imported_name=name,
                    local_name=local_name,
                    file=self.rel_path,
                    span=SourceSpan.from_node(spec),
                    is_type_only=spec_type,
                )
            )

    def _extract_export_clause(self, export_clause: Node, parent_export_stmt: Node) -> None:
        """Extract named exports and re-exports: export { a as b } from './mod'"""
        source_module = None
        for c in parent_export_stmt.children:
            if c.type == "string":
                source_module = self.text(c).strip("'\"")

        for c in export_clause.children:
            if c.type == "export_specifier":
                name = ""
                alias = ""
                is_type = False
                for sc in c.children:
                    if sc.type == "type":
                        is_type = True
                    elif sc.type == "identifier":
                        if not name:
                            name = self.text(sc).strip()
                        else:
                            alias = self.text(sc).strip()
                exp_name = alias if alias else name
                if name:
                    self.exports.append(
                        ExtractedExport(
                            exported_name=exp_name,
                            local_name=name,
                            file=self.rel_path,
                            source_module=source_module,
                            is_type_only=is_type,
                            span=SourceSpan.from_node(c),
                        )
                    )

    def _extract_export_all(self, node: Node) -> None:
        """Extract export * from './mod' or export * as ns from './mod'"""
        has_star = False
        source_mod = ""
        alias = None
        for c in node.children:
            if c.type == "*":
                has_star = True
            elif c.type == "namespace_export":
                for nc in c.children:
                    if nc.type == "identifier":
                        alias = self.text(nc).strip()
            elif c.type == "string":
                source_mod = self.text(c).strip("'\"")

        if has_star and source_mod:
            self.exports.append(
                ExtractedExport(
                    exported_name=alias or "*",
                    local_name="*",
                    file=self.rel_path,
                    source_module=source_mod,
                    span=SourceSpan.from_node(node),
                )
            )

    def _extract_interface(self, node: Node, is_exported: bool, is_default: bool) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for c in node.children:
                if c.type in ("type_identifier", "identifier"):
                    name_node = c
                    break
        if not name_node:
            return

        name = self.text(name_node).strip()
        sym_id = f"{self.rel_path}#{name}"
        span = SourceSpan.from_node(node)

        sym = ExtractedSymbol(
            id=sym_id,
            name=name,
            qualified_name=name,
            kind="interface",
            file=self.rel_path,
            span=span,
            exported=is_exported,
            is_default_export=is_default,
        )
        self.symbols.append(sym)
        if is_exported:
            self.exports.append(
                ExtractedExport(
                    exported_name="default" if is_default else name,
                    local_name=name,
                    file=self.rel_path,
                    is_type_only=True,
                    span=span,
                )
            )

        # Extract interface extends
        for c in node.children:
            if c.type in ("extends_type_clause", "extends_clause"):
                for ec in c.children:
                    if ec.type in ("type_identifier", "identifier"):
                        target_name = self.text(ec).strip()
                        self.relationships.append(
                            ExtractedRelationship(
                                source_id=sym_id,
                                target_name=target_name,
                                relation="extends",
                                span=SourceSpan.from_node(ec),
                            )
                        )

    def _extract_type_alias(self, node: Node, is_exported: bool, is_default: bool) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for c in node.children:
                if c.type in ("type_identifier", "identifier"):
                    name_node = c
                    break
        if not name_node:
            return

        name = self.text(name_node).strip()
        sym_id = f"{self.rel_path}#{name}"
        span = SourceSpan.from_node(node)

        sym = ExtractedSymbol(
            id=sym_id,
            name=name,
            qualified_name=name,
            kind="type",
            file=self.rel_path,
            span=span,
            exported=is_exported,
            is_default_export=is_default,
        )
        self.symbols.append(sym)
        if is_exported:
            self.exports.append(
                ExtractedExport(
                    exported_name="default" if is_default else name,
                    local_name=name,
                    file=self.rel_path,
                    is_type_only=True,
                    span=span,
                )
            )

        # Type references in type value
        value_node = node.child_by_field_name("value")
        if value_node:
            self._extract_type_references_in_node(value_node, sym_id)

    def _extract_enum(self, node: Node, is_exported: bool, is_default: bool) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for c in node.children:
                if c.type in ("identifier", "type_identifier"):
                    name_node = c
                    break
        if not name_node:
            return

        name = self.text(name_node).strip()
        sym_id = f"{self.rel_path}#{name}"
        span = SourceSpan.from_node(node)

        sym = ExtractedSymbol(
            id=sym_id,
            name=name,
            qualified_name=name,
            kind="enum",
            file=self.rel_path,
            span=span,
            exported=is_exported,
            is_default_export=is_default,
        )
        self.symbols.append(sym)
        if is_exported:
            self.exports.append(
                ExtractedExport(
                    exported_name="default" if is_default else name,
                    local_name=name,
                    file=self.rel_path,
                    span=span,
                )
            )

    def _extract_class(self, node: Node, is_exported: bool, is_default: bool) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for c in node.children:
                if c.type in ("type_identifier", "identifier"):
                    name_node = c
                    break
        class_name = self.text(name_node).strip() if name_node else ("default" if is_default else "AnonymousClass")
        sym_id = f"{self.rel_path}#{class_name}"
        span = SourceSpan.from_node(node)

        sym = ExtractedSymbol(
            id=sym_id,
            name=class_name,
            qualified_name=class_name,
            kind="class",
            file=self.rel_path,
            span=span,
            exported=is_exported,
            is_default_export=is_default,
        )
        self.symbols.append(sym)
        if is_exported:
            self.exports.append(
                ExtractedExport(
                    exported_name="default" if is_default else class_name,
                    local_name=class_name,
                    file=self.rel_path,
                    span=span,
                )
            )

        # Heritage (extends / implements)
        for c in node.children:
            if c.type == "class_heritage":
                for hc in c.children:
                    if hc.type == "extends_clause":
                        for ec in hc.children:
                            if ec.type in ("identifier", "type_identifier", "nested_identifier"):
                                base_name = self.text(ec).strip()
                                self.relationships.append(
                                    ExtractedRelationship(
                                        source_id=sym_id,
                                        target_name=base_name,
                                        relation="extends",
                                        span=SourceSpan.from_node(ec),
                                    )
                                )
                    elif hc.type == "implements_clause":
                        for ic in hc.children:
                            if ic.type in ("type_identifier", "identifier"):
                                iface_name = self.text(ic).strip()
                                self.relationships.append(
                                    ExtractedRelationship(
                                        source_id=sym_id,
                                        target_name=iface_name,
                                        relation="implements",
                                        span=SourceSpan.from_node(ic),
                                    )
                                )

        # Class body methods
        body_node = node.child_by_field_name("body")
        if body_node:
            for item in body_node.children:
                if item.type == "method_definition":
                    self._extract_method(item, sym_id, class_name)

    def _extract_method(self, node: Node, class_id: str, class_name: str) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        m_name = self.text(name_node).strip()
        qualified_name = f"{class_name}.{m_name}"
        method_id = f"{self.rel_path}#{qualified_name}"
        span = SourceSpan.from_node(node)

        # Check async
        is_async = False
        for c in node.children:
            if c.type == "async":
                is_async = True

        sym = ExtractedSymbol(
            id=method_id,
            name=m_name,
            qualified_name=qualified_name,
            kind="async_function" if is_async else "method",
            file=self.rel_path,
            span=span,
            container=class_id,
        )
        self.symbols.append(sym)

        # Extract calls/renders within method body
        body = node.child_by_field_name("body")
        if body:
            self._extract_calls_and_renders(body, method_id)

    def _extract_function(self, node: Node, is_exported: bool, is_default: bool) -> None:
        name_node = node.child_by_field_name("name")
        fn_name = self.text(name_node).strip() if name_node else ("default" if is_default else "anonymous")
        sym_id = f"{self.rel_path}#{fn_name}"
        span = SourceSpan.from_node(node)

        is_async = False
        for c in node.children:
            if c.type == "async":
                is_async = True

        # Check if PascalCase React Component or returns JSX
        is_component = bool(PASCAL_CASE_RE.match(fn_name))
        kind = "component" if is_component else ("async_function" if is_async else "function")

        sym = ExtractedSymbol(
            id=sym_id,
            name=fn_name,
            qualified_name=fn_name,
            kind=kind,
            file=self.rel_path,
            span=span,
            exported=is_exported,
            is_default_export=is_default,
        )
        self.symbols.append(sym)
        if is_exported:
            self.exports.append(
                ExtractedExport(
                    exported_name="default" if is_default else fn_name,
                    local_name=fn_name,
                    file=self.rel_path,
                    span=span,
                )
            )

        body = node.child_by_field_name("body")
        if body:
            self._extract_calls_and_renders(body, sym_id)

    def _extract_lexical_declaration(self, node: Node, is_exported: bool, is_default: bool) -> None:
        """Extract const Foo = () => { ... } or const bar = require('...')"""
        for decl in node.children:
            if decl.type == "variable_declarator":
                name_node = decl.child_by_field_name("name")
                val_node = decl.child_by_field_name("value")
                if not name_node:
                    continue

                var_name = self.text(name_node).strip()
                sym_id = f"{self.rel_path}#{var_name}"
                span = SourceSpan.from_node(decl)

                # Check if CommonJS require: const x = require('./x')
                if val_node and val_node.type == "call_expression":
                    fn_node = val_node.child_by_field_name("function")
                    if fn_node and self.text(fn_node).strip() == "require":
                        args = val_node.child_by_field_name("arguments")
                        if args:
                            for arg in args.children:
                                if arg.type == "string":
                                    req_path = self.text(arg).strip("'\"")
                                    self.imports.append(
                                        ExtractedImport(
                                            source_module=req_path,
                                            imported_name="default",
                                            local_name=var_name,
                                            file=self.rel_path,
                                            span=SourceSpan.from_node(decl),
                                        )
                                    )

                # Check if Arrow Function or Component
                if val_node and val_node.type in ("arrow_function", "function_expression"):
                    is_async = any(c.type == "async" for c in val_node.children)
                    is_component = bool(PASCAL_CASE_RE.match(var_name))
                    kind = "component" if is_component else ("async_function" if is_async else "function")

                    sym = ExtractedSymbol(
                        id=sym_id,
                        name=var_name,
                        qualified_name=var_name,
                        kind=kind,
                        file=self.rel_path,
                        span=span,
                        exported=is_exported,
                        is_default_export=is_default,
                    )
                    self.symbols.append(sym)
                    if is_exported:
                        self.exports.append(
                            ExtractedExport(
                                exported_name="default" if is_default else var_name,
                                local_name=var_name,
                                file=self.rel_path,
                                span=span,
                            )
                        )

                    body = val_node.child_by_field_name("body")
                    if body:
                        self._extract_calls_and_renders(body, sym_id)
                elif is_exported:
                    # Exported constant or variable
                    sym = ExtractedSymbol(
                        id=sym_id,
                        name=var_name,
                        qualified_name=var_name,
                        kind="variable",
                        file=self.rel_path,
                        span=span,
                        exported=is_exported,
                        is_default_export=is_default,
                    )
                    self.symbols.append(sym)
                    self.exports.append(
                        ExtractedExport(
                            exported_name="default" if is_default else var_name,
                            local_name=var_name,
                            file=self.rel_path,
                            span=span,
                        )
                    )

    def _extract_expression_statement(self, node: Node) -> None:
        """Handle module.exports = ... and exports.foo = ..."""
        for child in node.children:
            if child.type == "assignment_expression":
                left = child.child_by_field_name("left")
                right = child.child_by_field_name("right")
                if left:
                    left_text = self.text(left).strip()
                    if left_text == "module.exports":
                        right_text = self.text(right).strip() if right else "default"
                        self.exports.append(
                            ExtractedExport(
                                exported_name="default",
                                local_name=right_text,
                                file=self.rel_path,
                                span=SourceSpan.from_node(node),
                            )
                        )
                    elif left_text.startswith("exports."):
                        exp_prop = left_text.split(".", 1)[1]
                        right_text = self.text(right).strip() if right else exp_prop
                        self.exports.append(
                            ExtractedExport(
                                exported_name=exp_prop,
                                local_name=right_text,
                                file=self.rel_path,
                                span=SourceSpan.from_node(node),
                            )
                        )

    def _extract_calls_and_renders(self, node: Node, caller_id: str) -> None:
        """Recursively scan an expression or block for function calls, instantiations, and JSX renders."""
        ntype = node.type

        # Function calls: foo() or obj.method()
        if ntype == "call_expression":
            fn = node.child_by_field_name("function")
            if fn:
                target_name = self.text(fn).strip()
                if target_name != "require":
                    self.relationships.append(
                        ExtractedRelationship(
                            source_id=caller_id,
                            target_name=target_name,
                            relation="calls",
                            span=SourceSpan.from_node(fn),
                        )
                    )

        # Instantiations: new Client()
        elif ntype == "new_expression":
            ctor = node.child_by_field_name("constructor")
            if ctor:
                target_name = self.text(ctor).strip()
                self.relationships.append(
                    ExtractedRelationship(
                        source_id=caller_id,
                        target_name=target_name,
                        relation="instantiates",
                        span=SourceSpan.from_node(ctor),
                    )
                )

        # JSX elements: <Button ...> or <Button /> or <Dialog.Root>
        elif ntype in ("jsx_opening_element", "jsx_self_closing_element"):
            name_node = None
            for c in node.children:
                if c.type in ("identifier", "nested_identifier", "member_expression"):
                    name_node = c
                    break

            if name_node:
                tag_name = self.text(name_node).strip()
                # In React/JSX, components start with uppercase letter or contain dot (e.g. Dialog.Root)
                if tag_name and (tag_name[0].isupper() or "." in tag_name):
                    self.relationships.append(
                        ExtractedRelationship(
                            source_id=caller_id,
                            target_name=tag_name,
                            relation="jsx_renders",
                            span=SourceSpan.from_node(name_node),
                        )
                    )

        # Recurse into children
        for child in node.children:
            self._extract_calls_and_renders(child, caller_id)

    def _extract_type_references_in_node(self, node: Node, source_id: str) -> None:
        """Scan a type expression for referenced type identifiers."""
        if node.type in ("type_identifier", "identifier"):
            t_name = self.text(node).strip()
            if t_name and t_name not in ("string", "number", "boolean", "any", "unknown", "never", "void", "null", "undefined", "Promise", "Record", "Array", "Partial", "Omit", "Pick"):
                self.relationships.append(
                    ExtractedRelationship(
                        source_id=source_id,
                        target_name=t_name,
                        relation="type_reference",
                        span=SourceSpan.from_node(node),
                    )
                )
        for child in node.children:
            self._extract_type_references_in_node(child, source_id)
