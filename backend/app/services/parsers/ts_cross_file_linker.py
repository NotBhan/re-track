"""
Cross-file symbol, call, inheritance, interface, and JSX render linking engine.

Resolves imported symbols, re-export chains, namespace accesses, and JSX render hierarchies
into a deterministic, typed call graph.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Optional

from app.models.responses import CallEdge, CallNode
from app.services.parsers.treesitter_ts_analyzer import (
    ExtractedExport,
    ExtractedImport,
    ExtractedRelationship,
    ExtractedSymbol,
    ParsedModulePayload,
)
from app.services.parsers.ts_module_resolver import TSModuleResolver

logger = logging.getLogger(__name__)

MAX_REEXPORT_DEPTH = 5


@dataclass
class LinkingStats:
    """Statistics recorded during cross-file graph synthesis."""
    total_relationships: int = 0
    resolved_edges: int = 0
    unresolved_edges: int = 0
    ambiguous_edges: int = 0
    external_edges: int = 0


class TSCrossFileLinker:
    """Resolves cross-module symbol relationships across TypeScript and JavaScript modules."""

    def __init__(self, resolver: TSModuleResolver) -> None:
        self.resolver = resolver
        self.stats = LinkingStats()

    def link_modules(
        self,
        parsed_modules: dict[str, ParsedModulePayload],
        existing_nodes: Optional[dict[str, CallNode]] = None,
        max_nodes: int = 200,
        max_edges: int = 500,
    ) -> tuple[list[CallNode], list[CallEdge], LinkingStats]:
        """Synthesize resolved CallNode and CallEdge objects from parsed module payloads."""
        self.stats = LinkingStats()
        nodes: dict[str, CallNode] = dict(existing_nodes or {})
        edges: list[CallEdge] = []
        edge_keys: set[tuple[str, str, str]] = set()

        # 1. Build Global Symbol & Export Index
        file_symbols: dict[str, dict[str, ExtractedSymbol]] = {}
        file_exports: dict[str, dict[str, ExtractedExport]] = {}

        for rel, mod in parsed_modules.items():
            file_symbols[rel] = {s.name: s for s in mod.symbols}
            file_symbols[rel].update({s.qualified_name: s for s in mod.symbols})
            file_exports[rel] = {e.exported_name: e for e in mod.exports}

            # Register symbols as CallNodes
            for s in mod.symbols:
                if s.id not in nodes and len(nodes) < max_nodes:
                    node = CallNode(
                        id=s.id,
                        label=s.qualified_name or s.name,
                        file=s.file,
                        kind=s.kind,
                        line=s.span.start_line,
                    )
                    nodes[s.id] = node

        # 2. Resolve Relationships across Modules
        for rel, mod in parsed_modules.items():
            # Build local import lookup table: local_name -> (target_rel_path, imported_name, is_external, is_namespace)
            import_table: dict[str, tuple[Optional[str], str, bool, bool]] = {}
            primary_source_id = mod.symbols[0].id if mod.symbols else None

            for imp in mod.imports:
                res = self.resolver.resolve_import(imp.source_module, rel)
                if res.status == "resolved" and res.target_rel_path:
                    is_ns = imp.imported_name == "*"
                    import_table[imp.local_name] = (res.target_rel_path, imp.imported_name, False, is_ns)

                    # Generate structural imports edge
                    if primary_source_id:
                        lookup_name = imp.imported_name if imp.imported_name not in ("default", "*") else imp.local_name
                        resolved_sym = self._resolve_exported_symbol(
                            res.target_rel_path, lookup_name, parsed_modules, file_symbols, file_exports
                        )
                        if not resolved_sym and imp.imported_name == "default":
                            resolved_sym = self._resolve_exported_symbol(
                                res.target_rel_path, "default", parsed_modules, file_symbols, file_exports
                            )
                        if not resolved_sym:
                            target_syms = file_symbols.get(res.target_rel_path, {})
                            if len(target_syms) == 1:
                                resolved_sym = list(target_syms.values())[0]

                        if resolved_sym and primary_source_id != resolved_sym.id:
                            edge_key = (primary_source_id, resolved_sym.id, "imports")
                            if (
                                primary_source_id in nodes
                                and resolved_sym.id in nodes
                                and edge_key not in edge_keys
                                and len(edges) < max_edges
                            ):
                                edges.append(CallEdge(source=primary_source_id, target=resolved_sym.id, kind="imports"))
                                edge_keys.add(edge_key)
                elif res.is_external:
                    import_table[imp.local_name] = (None, imp.imported_name, True, False)

            # Process each relationship
            for rel_entry in mod.relationships:
                self.stats.total_relationships += 1
                source_id = rel_entry.source_id
                target_name = rel_entry.target_name
                relation = rel_entry.relation

                resolved_target_id: Optional[str] = None
                status = "unresolved"

                # Case A: Namespace Access (e.g. Utils.formatDate or Dialog.Root)
                if "." in target_name:
                    parts = target_name.split(".", 1)
                    base_id, member_name = parts[0], parts[1]

                    if base_id in import_table:
                        target_file, imp_name, is_ext, is_ns = import_table[base_id]
                        if is_ext:
                            status = "external"
                            self.stats.external_edges += 1
                        elif target_file:
                            # Trace export in target file
                            resolved_sym = self._resolve_exported_symbol(
                                target_file, member_name, parsed_modules, file_symbols, file_exports
                            )
                            if resolved_sym:
                                resolved_target_id = resolved_sym.id
                                status = "resolved"

                # Case B: Direct Symbol (e.g. Button, fetchData, UserProfile)
                if not resolved_target_id and status != "external":
                    if target_name in import_table:
                        target_file, imp_name, is_ext, is_ns = import_table[target_name]
                        if is_ext:
                            status = "external"
                            self.stats.external_edges += 1
                        elif target_file:
                            lookup_name = target_name if imp_name in ("default", "*") else imp_name
                            resolved_sym = self._resolve_exported_symbol(
                                target_file, lookup_name, parsed_modules, file_symbols, file_exports
                            )
                            if resolved_sym:
                                resolved_target_id = resolved_sym.id
                                status = "resolved"
                    elif target_name in file_symbols.get(rel, {}):
                        # Local symbol in the same file
                        resolved_sym = file_symbols[rel][target_name]
                        resolved_target_id = resolved_sym.id
                        status = "resolved"

                rel_entry.target_id = resolved_target_id
                rel_entry.resolution_status = status

                if status == "resolved" and resolved_target_id:
                    self.stats.resolved_edges += 1
                    edge_key = (source_id, resolved_target_id, relation)
                    if (
                        source_id in nodes
                        and resolved_target_id in nodes
                        and source_id != resolved_target_id
                        and edge_key not in edge_keys
                        and len(edges) < max_edges
                    ):
                        edge_kind_mapped = "inherits" if relation in ("extends", "implements") else ("renders" if relation == "jsx_renders" else "calls")
                        edge = CallEdge(source=source_id, target=resolved_target_id, kind=edge_kind_mapped)
                        edges.append(edge)
                        edge_keys.add(edge_key)
                elif status == "unresolved":
                    self.stats.unresolved_edges += 1

        return list(nodes.values()), edges, self.stats

    def _resolve_exported_symbol(
        self,
        target_file: str,
        symbol_name: str,
        parsed_modules: dict[str, ParsedModulePayload],
        file_symbols: dict[str, dict[str, ExtractedSymbol]],
        file_exports: dict[str, dict[str, ExtractedExport]],
        visited_files: Optional[set[str]] = None,
        depth: int = 0,
    ) -> Optional[ExtractedSymbol]:
        """Trace exports, default exports, and re-export chains across modules."""
        if depth > MAX_REEXPORT_DEPTH:
            return None

        visited = set(visited_files or set())
        if target_file in visited:
            return None
        visited.add(target_file)

        # 1. Direct local symbol match in target file
        symbols_in_file = file_symbols.get(target_file, {})
        if symbol_name in symbols_in_file:
            return symbols_in_file[symbol_name]

        # 2. Check exported symbols
        exports_in_file = file_exports.get(target_file, {})
        if symbol_name in exports_in_file:
            exp = exports_in_file[symbol_name]
            if exp.source_module:
                # Re-export from another file: export { foo } from './foo'
                res = self.resolver.resolve_import(exp.source_module, target_file)
                if res.status == "resolved" and res.target_rel_path:
                    return self._resolve_exported_symbol(
                        res.target_rel_path, exp.local_name, parsed_modules, file_symbols, file_exports, visited, depth + 1
                    )
            elif exp.local_name in symbols_in_file:
                return symbols_in_file[exp.local_name]

        # 3. Check wildcard re-exports: export * from './barrel'
        for exp in exports_in_file.values():
            if exp.exported_name == "*" and exp.source_module:
                res = self.resolver.resolve_import(exp.source_module, target_file)
                if res.status == "resolved" and res.target_rel_path:
                    cand = self._resolve_exported_symbol(
                        res.target_rel_path, symbol_name, parsed_modules, file_symbols, file_exports, visited, depth + 1
                    )
                    if cand:
                        return cand

        return None
