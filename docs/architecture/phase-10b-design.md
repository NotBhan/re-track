# Phase 10B Detailed Architectural Design: Tree-sitter Structural Analysis

**Phase**: 10B  
**Title**: Deterministic Syntax-Tree-Based TypeScript / JavaScript / JSX Structural Analysis  
**Role**: Principal Engineer, Static Analysis Architect, and Retrieval Systems Engineer  
**Status**: ARCHITECTURAL DESIGN — READY FOR IMPLEMENTATION  
**Date**: 2026-08-23  
**Contract Baseline**: Root `AGENTS.md`, `docs/architecture.md`, `docs/development_plan.md`, `docs/architecture/phase-10a-audit.md`

---

## 1. Executive Summary & Architectural Scope

In Phase 10A, RE:Track established Manifest 2.0 and an incremental indexing subsystem that guarantees **0 source AST parses** on unchanged repositories (`NOOP`) and isolated parsing on single-file modifications. However, TypeScript, TSX, JavaScript, and JSX structural analysis relied on regular expression heuristics.

**Phase 10B** replaces regex-based extraction with a deterministic **Tree-sitter Concrete Syntax Tree (CST) Code Intelligence Subsystem**.

### Core Invariants Preserved:
1. **Hexagonal Architecture**: All language-specific parsing is isolated behind the `SummaryGeneratorPort` and domain abstractions. Zero leakage into HTTP routers or MCP framing.
2. **Deterministic & Offline**: 100% deterministic native parsing via C bindings (`tree-sitter`, `tree-sitter-typescript`, `tree-sitter-javascript`). Zero LLM inference or non-deterministic heuristic guessing.
3. **Phase 10A Manifest 2.0 Reuse**: Incremental caching, fingerprinting, and atomic persistence (`.tmp` + `os.fsync()` + `os.replace()`) are reused without creating a parallel index storage model.
4. **Zero Python AST Regression**: Python AST analysis remains 100% powered by the native `ast` module and completely untouched.
5. **Truth Boundary Guarantee**: Unresolved dynamic symbols and third-party modules are explicitly classified as `unresolved`, `ambiguous`, or `external`—never synthesized into false-positive edges.
6. **Frozen Golden Benchmark**: Ground truth in `golden_tasks.json` and evaluator formulas in `tests/evaluation/evaluator.py` remain immutable.

---

## 2. ARCH-01 & ARCH-18: Tree-sitter Integration Boundary & Dependency Strategy

### 2.1 Parser Module Boundary
Language parsing is encapsulated in a dedicated internal domain service:
- `backend/app/services/parsers/treesitter_ts_analyzer.py`

This analyzer conforms to an internal parser protocol:
```python
class LanguageParserProtocol(Protocol):
    def parse_file(self, rel_path: str, code: str) -> ParsedModulePayload: ...
```

`RepositorySummaryGenerator` orchestrates language dispatch based on file extensions:
- `.py` -> Python `ast.parse` engine (native).
- `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs` -> `TreeSitterTSAnalyzer`.

### 2.2 Grammar Loading, Caching & Thread Safety
Grammars are compiled into native shared objects provided by PyPI binary wheels:
- `tree-sitter==0.26.0`
- `tree-sitter-typescript==0.23.2` (provides `tree_sitter_typescript.language_typescript()` and `language_tsx()`)
- `tree-sitter-javascript==0.25.0` (provides `tree_sitter_javascript.language_javascript()`)

```python
from tree_sitter import Language, Parser
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts

class GrammarCache:
    """Thread-safe singleton registry for Tree-sitter Language instances."""
    _instance: Optional["GrammarCache"] = None

    def __init__(self) -> None:
        self.ts_lang = Language(tsts.language_typescript())
        self.tsx_lang = Language(tsts.language_tsx())
        self.js_lang = Language(tsts.language_javascript())

    @classmethod
    def get_instance(cls) -> "GrammarCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

**Parser Isolation Rule**: `Parser` instances in Python `tree-sitter` maintain internal C state during execution. To prevent concurrency hazards across async tasks or thread pools, `TreeSitterTSAnalyzer` creates or borrows a lightweight `Parser()` instance per parsing thread/task, setting the cached `Language` pointer.

### 2.3 Language-to-Grammar Dispatch Table

| Extension | Detected Language | Grammar Selected | Supported Dialect Features |
| :--- | :--- | :--- | :--- |
| `.ts` | TypeScript | `GrammarCache.ts_lang` | Types, Interfaces, Enums, Generics, Namespaces, Decorators, Classes |
| `.tsx` | TSX / React | `GrammarCache.tsx_lang` | All TypeScript constructs + JSX elements & fragments |
| `.js`, `.mjs`, `.cjs` | JavaScript | `GrammarCache.js_lang` | ES6 Classes, Functions, ESM `import`/`export`, CommonJS `require`/`module.exports` |
| `.jsx` | JSX / React | `GrammarCache.js_lang` / `tsx_lang` | JavaScript + JSX elements & fragments |

---

## 3. ARCH-02 & ARCH-03: Canonical CST Extraction Model & Symbol Identity

### 3.1 Canonical Symbol & Relationship Data Structures

```python
@dataclass
class SourceSpan:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

@dataclass
class ExtractedSymbol:
    id: str                 # Deterministic qualified ID: "src/services/auth.ts#AuthService.login"
    name: str               # Short symbol name: "login"
    qualified_name: str     # Qualified name within file: "AuthService.login"
    kind: str               # function | async_function | class | method | interface | type | enum | variable | component | namespace
    file: str               # Relative POSIX path: "src/services/auth.ts"
    span: SourceSpan
    exported: bool = False
    is_default_export: bool = False
    docstring: Optional[str] = None
    container: Optional[str] = None  # Parent class/namespace ID if nested

@dataclass
class ExtractedImport:
    source_module: str      # Raw string from import: "./utils", "@/components/Button"
    imported_name: str      # Named import ("Button"), default ("default"), or wildcard ("*")
    local_name: str         # Binding in local file: "PrimaryButton"
    is_type_only: bool      # import type { ... }
    file: str               # File containing import
    span: SourceSpan

@dataclass
class ExtractedExport:
    exported_name: str      # Name visible to importers: "User" or "default"
    local_name: str         # Local symbol name in file: "UserModel"
    source_module: Optional[str] = None # For re-exports: export { User } from './models'
    is_type_only: bool = False
    file: str = ""
    span: Optional[SourceSpan] = None

@dataclass
class ExtractedRelationship:
    source_id: str          # Source node ID: "src/pages/Login.tsx#LoginPage"
    target_name: str        # Target symbol or call name: "AuthService.login" or "Button"
    relation: str           # calls | imports | exports | re_exports | extends | implements | renders | references | instantiates
    target_id: Optional[str] = None # Resolved symbol ID (if resolved)
    resolution_status: str = "unresolved" # resolved | unresolved | ambiguous | external
    span: Optional[SourceSpan] = None
```

### 3.2 Tree-sitter CST Query Patterns

Extraction traverses the concrete syntax tree using Tree-sitter queries and AST walker patterns:

1. **Functions & Arrow Functions**:
   - `(function_declaration name: (identifier) @name)`
   - `(lexical_declaration (variable_declarator name: (identifier) @name value: [(arrow_function) (function_expression)]))`
2. **Classes & Methods**:
   - `(class_declaration name: (type_identifier) @class_name body: (class_body [(method_definition name: (property_identifier) @method_name)]))`
   - `(abstract_class_declaration ...)`
3. **Interfaces & Type Aliases**:
   - `(interface_declaration name: (type_identifier) @name)`
   - `(type_alias_declaration name: (type_identifier) @name)`
4. **Enums**:
   - `(enum_declaration name: (identifier) @name)`
5. **JSX Components & Renders**:
   - Component functions identified by PascalCase naming convention (`^[A-Z][A-Za-z0-9_]*$`) or returning JSX expressions (`(jsx_element)`, `(jsx_self_closing_element)`).
   - Render edges extracted from `(jsx_element open_tag: (jsx_opening_element name: (identifier) @tag))` and `(jsx_self_closing_element name: (identifier) @tag)`.
6. **CommonJS Constructs**:
   - `(call_expression function: (identifier) @fn_name (#eq? @fn_name "require") arguments: (arguments (string (string_fragment) @path)))`
   - `(assignment_expression left: (member_expression object: (identifier) @obj property: (property_identifier) @prop) (#eq? @obj "module") (#eq? @prop "exports"))`

### 3.3 Stable Deterministic Node Identity
Node IDs must be immutable, collision-resistant, and reconstructible across indexing runs without random UUIDs:

$$\text{Node ID} = \text{rel\_path} + \text{"\#"} + \text{qualified\_symbol\_name}$$

**Examples**:
- Function in file: `src/utils/format.ts#formatDate`
- Method in class: `src/services/api.ts#ApiClient.request`
- Interface: `src/types/user.ts#UserProfile`
- Anonymous default export function: `src/pages/index.tsx#default`
- Default export React component: `src/components/Header.tsx#Header` (derived from named function/class or file basename if anonymous component).
- Overloads / Duplicate declarations: Qualified by kind if signatures collide (e.g. `src/types/data.ts#Data:interface` vs `src/types/data.ts#Data:type`).

---

## 4. ARCH-04 & ARCH-05: Module Resolution & `tsconfig.json` Path Engine

### 4.1 Resolution Strategy & Bounded Traversal
Cross-file module resolution executes deterministically in strict precedence order:

```text
Import String: "source_module" (e.g., "@/components/Button", "../utils/date")
   │
   ▼
[ Step 1: Relative Import Check ]
   Is it relative? (starts with "./" or "../")
   ├── YES ──> Resolve relative to importing file's directory
   │           Test extensions: .ts, .tsx, .d.ts, .js, .jsx, /index.ts, /index.tsx, /index.js
   └── NO ───> Proceed to Step 2
   │
   ▼
[ Step 2: tsconfig.json Path Mapping ]
   Is tsconfig.json present with compilerOptions.paths or baseUrl?
   ├── YES ──> Match path patterns (e.g. "@/*" -> ["src/*"])
   │           Resolve matching filesystem candidate within repository root
   └── NO ───> Proceed to Step 3
   │
   ▼
[ Step 3: Package-Local & Well-Known Conventions ]
   Test standard conventions:
   - "@/..." -> "src/..." or "app/..."
   - "~/..." -> "src/..." or "app/..."
   - "src/..." -> root-relative "src/..."
   │
   ▼
[ Step 4: Classification ]
   ├── Matched internal repo file ──> Return "resolved" with Canonical RelPath
   ├── Matched npm package / node_modules ──> Return "external"
   └── No match ──> Return "unresolved"
```

### 4.2 `tsconfig.json` Parser Specification
- **Discovery**: Searches repository root for `tsconfig.json` (or `jsconfig.json`).
- **Parsing**: Tolerant JSON parsing handling comments (`//`, `/* */`) and trailing commas.
- **`baseUrl`**: Resolved relative to `tsconfig.json` directory.
- **`paths` Mapping**:
  - Supports wildcard substitution: `"@/*": ["src/*"]`.
  - Supports multi-target fallbacks: `"@components/*": ["src/components/*", "src/shared/components/*"]`.
  - Strict containment check: `target_path.resolve().is_relative_to(repo_root)`. Traversal attempts escaping repo root (e.g. `../../etc`) are rejected immediately.
- **Malformed / Missing Config**: Logs diagnostic warning and falls back cleanly to default relative + convention resolution. Never raises an unhandled exception or aborts indexing.

---

## 5. ARCH-06 & ARCH-07: Cross-File Call & Type Relationship Resolution

### 5.1 Import / Export Symbol Linking
When `File A` references symbol `S` imported from `File B`:

1. **Named Import**: `import { S } from './b'`
   - Target File resolved to `b.ts`.
   - Lookup exported symbol `S` in `b.ts`.
   - If found -> create edge: `FileA#Caller` --(`calls` / `references`)--> `b.ts#S` (`resolution_status: resolved`).
2. **Aliased Import**: `import { S as LocalS } from './b'`
   - Local symbol `LocalS` in `File A` maps to `S` in `b.ts`.
   - Usage of `LocalS()` resolves to `b.ts#S`.
3. **Default Import**: `import DefaultComp from './b'`
   - Target File resolved to `b.ts`.
   - Lookup `default` export in `b.ts` (or the primary named export if `default` aliases a declared component/function).
4. **Namespace Import**: `import * as API from './api'`
   - Usage of `API.fetchUser()` resolves property `fetchUser` against `api.ts` exports.
5. **Re-export / Barrel Resolution**: `export { User } from './models/user'`
   - Follows re-export chain up to depth 5 to locate the originating definition file.
   - Circular re-export chains are bounded by a visited set.

### 5.2 TypeScript Structural Relationships vs. Runtime Calls
RE:Track explicitly distinguishes structural type hierarchy edges from runtime call invocations:

| Relationship Kind | Description | Edge Type in CallGraph |
| :--- | :--- | :--- |
| `calls` | Runtime function / method execution | `CallEdge(kind="calls")` |
| `extends` | Class inheritance (`class A extends B`) | `CallEdge(kind="inherits")` |
| `implements` | Interface implementation (`class A implements I`) | `CallEdge(kind="implements")` |
| `references` | Type usage (`type T = UserProfile`) | `CallEdge(kind="references")` |
| `renders` | JSX component instantiation (`<Header />`) | `CallEdge(kind="renders")` |

---

## 6. ARCH-08: JSX / TSX Component & Render Graph

### 6.1 Intrinsic Elements vs. User Components
- **Intrinsic HTML Elements**: Elements starting with lowercase letters (`div`, `span`, `button`, `svg`, `path`, `main`, `header`, etc.) are ignored during symbol linking to prevent graph pollution.
- **User Components**: Elements starting with uppercase letters (`<Button />`, `<Dialog.Root />`, `<ContextCard />`) are resolved:
  - If imported locally -> link to imported component definition node.
  - If declared in the same file -> link to local component node.
  - If accessed via namespace (`<Dialog.Root />`) -> resolve `Root` against `Dialog` namespace/module.

### 6.2 Dynamic Component Expressions
Dynamic component renders (e.g. `<Component {...props} />`, `<routes[currentRoute] />`) where the tag is a variable expression are recorded as `dynamic_render` with `resolution_status: "ambiguous"` or `"unresolved"`. No speculative synthetic edges are created.

---

## 7. ARCH-09 & ARCH-10: Manifest 2.0 Integration & Phase 10A Incremental Impact Model

### 7.1 Parser Version Transition & Migration
- **Manifest Schema Version**: Remains `"2.0"` (structure is fully compatible).
- **Parser Version**: Updated to `PARSER_VERSION = "2.0.0"`.
- **Automatic Migration**: `ManifestService.load_manifest()` detects `manifest.parser_version != "2.0.0"` and returns `None`, cleanly triggering a one-time deterministic `FULL` rebuild. Existing user data is safely upgraded without manual intervention.

### 7.2 Serialized Manifest Payload per File
`FileFingerprint` in Manifest 2.0 persists:
```json
{
  "path": "src/components/Button.tsx",
  "mtime": 1787473100.0,
  "size": 1420,
  "sha256": "4a7b...",
  "language": "TypeScript",
  "symbols": ["Button", "ButtonProps"],
  "imports": ["@/lib/utils.cn as cn", "react.FC as FC"],
  "ast_nodes": [
    {
      "id": "src/components/Button.tsx#Button",
      "label": "Button",
      "file": "src/components/Button.tsx",
      "kind": "component",
      "line": 12,
      "exported": true
    }
  ],
  "ast_edges": [
    {
      "source": "src/components/Button.tsx#Button",
      "target": "src/lib/utils.ts#cn",
      "kind": "calls",
      "resolution_status": "resolved"
    }
  ],
  "last_indexed_at": 1787473110.0
}
```

### 7.3 Incremental Scenarios & Impact Propagation

```text
┌─────────────────────────┬──────────────────────┬──────────────────────┬────────────────────────────┐
│ Repository Mutation     │ Source Parsing Scope │ Call Graph Relinking │ Cache Invalidation Scope   │
├─────────────────────────┼──────────────────────┼──────────────────────┼────────────────────────────┤
│ Unchanged Repository    │ 0 files parsed       │ Reused from Manifest │ Zero cache invalidations   │
│ Single TS File Edit     │ 1 file parsed        │ File + Importers     │ Contexts referencing file  │
│ TS File Added           │ 1 file parsed        │ New file only        │ Zero (no prior dependents) │
│ TS File Deleted         │ 0 files parsed       │ Purge deleted nodes  │ Contexts referencing file  │
│ TS File Renamed         │ 0 files parsed (hash)│ Relink references    │ Contexts referencing file  │
│ Barrel Export Changed   │ 1 file parsed        │ All barrel consumers │ Dependent context packages │
│ tsconfig.json Changed   │ Re-resolve all edges │ Re-link all imports  │ Repo cache invalidated     │
└─────────────────────────┴──────────────────────┴──────────────────────┴────────────────────────────┘
```

---

## 8. ARCH-11 & ARCH-17: Error Handling, Resilience & Failure Rollback

1. **Syntax Error Resilience**:
   - If Tree-sitter encounters a file with syntax errors, `tree.root_node.has_error` is flagged.
   - Tree-sitter’s error-tolerant parser recovers partial CST nodes. Valid declarations before/after the syntax error are preserved.
   - The file is marked with `parse_status: "partial"` or `"failed"`. Indexing continues uninterrupted for all other files.
2. **Grammar Initialization Failure**:
   - If Tree-sitter native bindings fail to load (e.g. binary incompatibility), the subsystem logs an error and gracefully falls back to basic symbol discovery without crashing the backend process.
3. **Atomic Commit & Crash Recovery**:
   - Manifest staging writes to `<manifest_path>.tmp`, calls `os.fsync()`, and renames via `os.replace()`. Interrupted writes leave the prior valid manifest intact.

---

## 9. ARCH-12: Security Boundary & Sandboxing

1. **Workspace Authorization**: All file discovery respects `WorkspaceAuthorizationPort.is_path_authorized()`. Unauthorized paths are rejected prior to any filesystem read or CST parsing.
2. **Symlink Containment**: Links targeting paths outside repository boundaries are pruned during scan.
3. **`tsconfig.json` Traversal Guard**: Path mapping targets resolving outside the repository root are rejected:
   ```python
   target_resolved = (repo_path / raw_target).resolve()
   if not target_resolved.is_relative_to(repo_path.resolve()):
       logger.warning("Rejected path traversal in tsconfig: %s", raw_target)
       return None
   ```
4. **Dataset Isolation**: Multi-repository indexes remain strictly isolated in distinct dataset partitions and manifest files.

---

## 10. ARCH-13 & ARCH-14: Observability, Diagnostics & Public Contracts

### 10.1 Structured Diagnostics Events
Diagnostic logs follow RE:Track’s JSONL format (`~/.retrack/logs/app.jsonl`) with secret redaction and **zero source code / raw prompts**:

- `tsjs_parse_started`: `{"event": "tsjs_parse_started", "file_count": 45}`
- `tsjs_parse_completed`: `{"event": "tsjs_parse_completed", "files_parsed": 45, "symbols_extracted": 312, "duration_ms": 38.4}`
- `tsjs_resolution_completed`: `{"event": "tsjs_resolution_completed", "resolved_edges": 240, "unresolved_edges": 12, "ambiguous_edges": 0, "duration_ms": 12.1}`
- `tsjs_incremental_relink`: `{"event": "tsjs_incremental_relink", "relinked_files": 3, "duration_ms": 4.2}`

### 10.2 Public API & FastMCP Backward Compatibility
- FastMCP tool `get_ast_call_graph`: Emits standard nodes and edges. Extended with optional metadata (`resolution_status`, `is_type_only`) in edge objects without breaking existing MCP clients or Knowledge Explorer SVG renderers.
- `get_repository_summary`: Key components and architectural flows populated from validated Tree-sitter CST analysis.

---

## 11. ARCH-15 & ARCH-16: Benchmark Strategy & Performance Evaluation

### 11.1 Benchmark Integrity
- **Frozen Golden Baseline**: `benchmarks/retrack/golden_tasks.json` and `context_engine_baseline.json` remain untouched.
- `tests/test_benchmark_baseline_contract.py` regression gate remains mandatory and strictly enforced.

### 11.2 Empirical Performance Metrics (Target Profiles)
Measured across synthetic 50–500 file TypeScript / React benchmark repositories:
- `parse_ms_per_file`: Measured distribution (P50, P90, P99).
- `resolution_ms`: Module & symbol resolution time.
- `relink_ms`: Incremental edge relinking latency.
- `noop_parse_count`: Verified **exactly 0** for unchanged repositories.

---

## 12. ARCH-19: Compatibility & Migration Matrix

| Existing State | Incoming Request | Transition Action | Outcome |
| :--- | :--- | :--- | :--- |
| **No Manifest** | Index Repository | Full Tree-sitter CST Scan | Manifest 2.0 (`parser 2.0.0`) created |
| **Manifest 2.0 (`parser 1.0.0`)** | Index Repository | Version mismatch detected | Automatic clean FULL rebuild -> Manifest 2.0 (`parser 2.0.0`) |
| **Manifest 2.0 (`parser 2.0.0`)** | Index (Unchanged Repo) | NOOP detection | **0 source parses**, Manifest reused (< 1ms) |
| **Manifest 2.0 (`parser 2.0.0`)** | Index (1 Changed File) | Incremental Delta | **1 file parsed**, dependent edges relinked |
| **Corrupt JSON Manifest** | Index Repository | Load failure detected | Clean FULL rebuild executed |
| **Malformed `tsconfig.json`** | Module Resolution | Parse warning logged | Default relative/convention resolution applied |

---

## 13. ARCH-20: Phased Implementation Sequence

```text
Step 1: Dependency & Grammar Foundation
        Declare tree-sitter, tree-sitter-typescript, tree-sitter-javascript in pyproject.toml.
        Build GrammarCache and basic CST traversal fixtures.

Step 2: TreeSitterTSAnalyzer Extraction Engine
        Implement symbol, import, export, and JSX render extraction.
        Test with backend/tests/test_ts_js_parser.py (13 unit cases).

Step 3: Deterministic Module & Path Resolution Engine
        Implement relative, tsconfig paths, barrel re-export resolution.
        Test with backend/tests/test_ts_js_import_resolution.py (11 cases).

Step 4: Cross-File Call & Relationship Linker
        Implement cross-file function calls, class inheritance, interface implementation, and JSX renders.
        Test with backend/tests/test_ts_js_cross_file_graph.py (8 cases).

Step 5: Manifest 2.0 & Incremental Subsystem Integration
        Bump PARSER_VERSION to "2.0.0", integrate with repository_summary.py and indexing_service.py.
        Test with backend/tests/test_ts_js_incremental.py (10 cases).

Step 6: Security, Compatibility & Regression Gate Verification
        Verify security containment (backend/tests/test_ts_js_security.py),
        compatibility (backend/tests/test_ts_js_compatibility.py),
        and empirical performance (backend/tests/test_ts_js_performance.py).
        Execute full regression suite: 440+ backend tests, 50 frontend tests, npm run build.
```

---

## 14. Architecture Sign-Off Verdict

The Phase 10B architectural design provides an **implementation-ready, deterministic, zero-inference, crash-safe** structural analysis engine for TypeScript, TSX, JavaScript, and JSX. It upholds all Truth Boundary invariants and seamlessly integrates into Manifest 2.0.
