# TypeScript & JavaScript Structural Analysis Guide

**Product**: RE:Track  
**Feature**: Tree-sitter Deterministic CST Extraction & Cross-File Intelligence  
**Supported Dialects**: TypeScript, TSX, JavaScript, JSX, CommonJS, ES Modules  
**Parser Version**: 2.0.0  

---

## 1. Overview

RE:Track provides deterministic, high-performance structural analysis for modern TypeScript and JavaScript codebases. Powered by native **Tree-sitter** parsers, RE:Track extracts symbols, class hierarchies, interfaces, function calls, and React/Next.js JSX render relationships directly from the source concrete syntax tree (CST).

All extraction runs **100% locally and offline** without requiring external LLM inference, language servers, or network access.

---

## 2. Supported Languages & Constructs

| Extension | Language | Extracted Symbols & Constructs |
| :--- | :--- | :--- |
| **`.ts`** | TypeScript | Classes, Methods, Functions, Interfaces, Type Aliases, Enums, Namespaces, Decorators, Generics |
| **`.tsx`** | TSX (React/Next.js) | All TypeScript constructs + JSX components, props, fragments, and render trees |
| **`.js`, `.mjs`** | JavaScript (ESM) | ES6 Classes, Functions, Arrow Functions, Default & Named Exports, Dynamic Imports |
| **`.jsx`** | JSX (React) | JavaScript constructs + JSX component instantiation & render hierarchies |
| **`.cjs`** | CommonJS | `require('...')` calls, `module.exports`, `exports.<name>` assignments |

---

## 3. Deterministic Symbol Identity

Every extracted symbol receives an immutable, qualified identifier based on its file path and lexical hierarchy:

- **Top-Level Function**: `src/utils/math.ts#calculateTotal`
- **Class**: `src/services/auth.ts#AuthService`
- **Class Method**: `src/services/auth.ts#AuthService.login`
- **Interface**: `src/types/user.ts#UserProfile`
- **Type Alias**: `src/types/config.ts#AppConfig`
- **Enum**: `src/models/status.ts#OrderStatus`
- **React Component**: `src/components/Header.tsx#Header`

These IDs remain stable across re-indexing runs, enabling efficient incremental caching in Manifest 2.0.

---

## 4. Module & Path Resolution

RE:Track resolves cross-file relationships using a deterministic 4-stage resolution pipeline:

1. **Relative Imports**: Resolves `./` and `../` paths relative to the containing directory, testing file extensions (`.ts`, `.tsx`, `.d.ts`, `.js`, `.jsx`, `/index.ts`, `/index.tsx`).
2. **`tsconfig.json` Path Mapping**: Automatically inspects `compilerOptions.baseUrl` and `compilerOptions.paths` (e.g. `@/*` -> `src/*`), resolving mapped path aliases to internal repository files.
3. **Convention Aliases**: Fallback support for standard framework aliases (`@/`, `~/`, `src/`) even in codebases with minimal configuration.
4. **External & Unresolved Classification**: Third-party packages (e.g. `react`, `lucide-react`, `lodash`) are explicitly classified as `external`. Unresolvable dynamic paths are classified as `unresolved` rather than generating false-positive edges.

---

## 5. Relationships & Call Graph Topologies

RE:Track constructs an interconnected call graph containing:

- **Function Invocations (`calls`)**: Tracks callers and callees across modules.
- **Class Inheritance (`extends`)**: Links derived classes to their base classes.
- **Interface Implementation (`implements`)**: Connects classes implementing interfaces.
- **Type Usage (`references`)**: Tracks type dependencies across files.
- **Component Renders (`renders`)**: Maps parent React components to child components used in JSX markup (excluding native HTML elements like `div`, `button`, etc.).

---

## 6. Incremental Indexing & Manifest Integration

Integrated into RE:Track's **Manifest 2.0** engine:
- **Zero-Parse NOOP**: When files are unchanged, structural intelligence is loaded directly from disk cache in < 1ms with 0 source parses.
- **Isolated Updates**: Modifying a single file parses only that file and relinks immediate dependents.
- **Automatic Migration**: Updating to Parser 2.0.0 triggers a one-time clean rebuild, updating repository manifests to full Tree-sitter fidelity automatically.

---

## 7. Semantic Scope & Limitations

RE:Track structural analysis is a high-speed, lightweight static analyzer designed for context synthesis and topology exploration.
- **Not a Full Type-Checker**: RE:Track does not perform full semantic type checking, overload resolution, or flow-sensitive type narrowing.
- **Dynamic Imports**: Computed dynamic imports (`import(variablePath)`) are safely recorded as `unresolved`.
