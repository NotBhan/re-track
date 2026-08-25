# Phase 10C Architectural Audit: Expanded Multi-Repository Retrieval Benchmarking

## 1. Executive Summary

Phase 10C establishes a deterministic multi-repository retrieval benchmark suite for RE:Track. The suite evaluates retrieval precision, recall, critical evidence preservation, AST relationship extraction, cross-file navigation, and incremental indexing efficiency across diverse programming languages and architectural patterns.

### Key Metrics Summary (Empirical Benchmark Results)
- **Total Evaluated Tasks**: 36
- **Task Pass Rate**: 100.0% (36 / 36 passed)
- **Failed Tasks**: 0
- **Mean Precision@K**: 0.5035
- **Mean Recall@K**: 0.9907
- **Mean Critical File Coverage**: 1.0000
- **Mean Critical Symbol Coverage**: 1.0000
- **Mean Critical Evidence Coverage**: 1.0000 (100% of critical source files and symbols preserved)
- **Mean Noise Ratio**: 0.1571 (Strictly below allowable 0.400 ceiling)
- **Mean Relationship Coverage**: 0.9722 (AST cross-file calls, imports, inheritance, renders)
- **Mean Token Savings**: 81.8% (Mean Compression Ratio: 6.28x)
- **Mean Retrieval Latency**: 0.22ms per task
- **Incremental Mutation Scenarios**: 7 / 7 passed with deterministic AST reuse

---

## 2. Multi-Repository Benchmark Corpus Architecture

All benchmark repositories are located in `benchmarks/corpus/` and adhere strictly to a neutral code-intelligence and engineering domain policy. No commercial, billing, customer, or monetization terminology is used.

### Corpus Repositories Overview

1. **`py_backend`** (Python Layered Architecture):
   - Domain models (`Document`, `DocumentMetadata`, `DocumentStatus`).
   - Abstract ports (`DocumentStorePort`, `DocumentParserPort`).
   - Application service (`DocumentProcessor`).
   - Infrastructure adapters (`LocalFileStore`, `StandardDocumentParser`).
   - API routing & composition root (`DocumentRoutes`, `main.py`).

2. **`ts_react`** (TypeScript + React + Hooks + Context):
   - Domain interfaces (`TaskItem`, `TaskCardProps`, `BoardState`).
   - Context and Provider (`BoardContext`, `BoardProvider`).
   - Custom hook (`useBoard`).
   - Interactive components (`TaskCard`, `TaskBoard`, `App`).

3. **`ts_barrel`** (TypeScript Barrel & Re-Export Patterns):
   - Component definitions (`Badge`, `Panel`, `PanelHeader`).
   - Folder-level barrel (`src/components/index.ts` with named, default, and wildcard re-exports).
   - Root package re-export (`src/index.ts` with aliased re-export `StatusBadge`).

4. **`polyglot`** (Python FastAPI Backend + TypeScript React Frontend + CommonJS):
   - Python domain and service layer (`CatalogItem`, `CatalogService`, `items.py`).
   - TypeScript client DTO & API helpers (`CatalogItemDTO`, `fetchCatalogItems`, `itemClient.ts`).
   - CommonJS utility helpers (`formatter.cjs`, `mathHelper.cjs` with `require` and `module.exports`).
   - React view components (`ItemList`, `App`).

5. **`ts_alias`** (TypeScript `tsconfig.json` Path Aliases + JavaScript ESM):
   - Path configuration: `@core/*`, `@shared/*`, `@features/*`.
   - Core processing pipeline (`ProcessingEngine`, `PipelineRunner`).
   - Formatting utilities (`formatReportData`, `sanitizeInput`, `stringUtils.js`).
   - Feature reporting (`ReportGenerator`).

6. **`monorepo`** (Multi-Package Architecture):
   - `@repo/shared` (`ASTNode`, `SyntaxTree`, `TransformRule`).
   - `@repo/core` (`CodeParser`, `parseSource`).
   - `@repo/ui` (`TreeView`, `TreeViewProps`).
   - `@repo/app` (`WorkspaceView`, `main.ts`).

---

## 3. Evaluation Methodology and Golden Task Catalog

The benchmark suite defines 36 golden retrieval tasks across 12 distinct categories (3 tasks per category):

| Category | Description | Primary Verification Target |
| :--- | :--- | :--- |
| `python_layered_architecture` | Multi-tier Python architecture | Domain, ports, application, adapters |
| `typescript_structural` | TypeScript interfaces, hooks, context | Type inheritance, custom hooks |
| `javascript_structural` | Standalone JS/CJS/ESM utility modules | CommonJS `require`, ESM exports (`.cjs`, `.js`) |
| `barrel_reexport` | Barrel re-export propagation | Index re-exports (named, default, wildcard) |
| `path_alias` | TypeScript path alias resolution | `@core/*`, `@features/*` cross-module calls |
| `cross_package_monorepo` | Multi-package workspaces | Cross-package imports and component usage |
| `polyglot_cross_language` | Mixed Python + TS/React | Frontend API DTOs matching backend route handlers |
| `calls_relationship` | Direct function and method invocations | AST call graph edges (`calls`) |
| `inherits_implements` | Class inheritance and interface implementation | AST inheritance edges (`inherits`) |
| `type_reference` | DTO and interface type references | Cross-file type imports (`imports`) |
| `jsx_render` | Component composition and rendering | React AST JSX edges (`renders`) |
| `noise_discrimination` | Filtering irrelevant implementation files | Negative evidence and noise penalties |

---

## 4. Relationship-Aware Scoring & Metric Formulae

Each task is evaluated using formal deterministic scoring functions:

1. **Precision@K**:
   $$\text{Precision@K} = \frac{|\text{Retrieved Files} \cap \text{Expected Files}|}{|\text{Retrieved Files}|}$$

2. **Recall@K**:
   $$\text{Recall@K} = \frac{|\text{Retrieved Files} \cap \text{Expected Files}|}{|\text{Expected Files}|}$$

3. **Critical Evidence Coverage**:
   $$\text{Coverage}_{\text{critical}} = \frac{|\text{Retrieved Files} \cap \text{Critical Files}| + |\text{Retrieved Symbols} \cap \text{Critical Symbols}|}{|\text{Critical Files}| + |\text{Critical Symbols}|}$$

4. **Noise Ratio**:
   $$\text{Noise Ratio} = \frac{|\text{Retrieved Files} \cap \text{Disallowed Noise}|}{|\text{Retrieved Files}|}$$

5. **Relationship Coverage**:
   $$\text{Coverage}_{\text{rel}} = \frac{|\text{Extracted AST Edges} \cap \text{Expected Relationships}|}{|\text{Expected Relationships}|}$$

---

## 5. Incremental Mutation Scenarios

Incremental indexing behavior was validated across 7 mutation scenarios against isolated temporary copies:

1. **`cold_initial_index`**: Full cold parse of all 6 corpus fixtures (36 code files parsed, 0 reused across all repos).
2. **`warm_noop_reindex`**: Unmodified working tree with existing manifest (0 parsed, 6 reused, 0 changes detected).
3. **`single_file_modification`**: Single file modified in place (1 parsed, 5 reused, 1 modified file detected).
4. **`single_file_addition`**: Single new file added (1 parsed, 6 reused, 1 added file detected).
5. **`single_file_deletion`**: Single file removed (0 parsed, 5 reused, 1 deleted file detected).
6. **`rename_without_edit`**: File moved/renamed without content alteration. Manifest layer detects rename via SHA-256 fingerprint equality (`delta.renamed`), while AST layer parses 1 file to re-bind module prefix / node IDs, reusing $N-1$ files from cache.
7. **`dependency_relink`**: Type definition altered affecting dependent modules (1 parsed, 5 reused, AST graph fully relinked).

---

## 6. Scientific Interpretation & Motivation for Phase 10D

### Empirical Findings
1. **Critical Completeness**: With 100.0% Critical File Coverage and 100.0% Critical Symbol Coverage, the Context Engine never omits essential code or type definitions required to complete a programming task.
2. **Structural Dependency Noise**: Mean Precision@K is **0.5035** (Mean Noise Ratio: **0.1571**). The retrieval pipeline includes 1-hop structural neighbors (e.g. re-export barrels, port definitions, imported components) to guarantee comprehensive context, which introduces supplementary files.
3. **Motivation for Phase 10D (Adaptive Query-Aware Retrieval)**:
   - High structural recall without adaptive pruning leads to moderate precision.
   - Phase 10D will introduce query-directed candidate pruning, dynamic budget allocation, and symbol-level selective inclusion to elevate Precision toward >0.80 without sacrificing Critical Evidence Coverage.

---

## 7. Frozen Baseline Immutability Contract

To prevent benchmark drift and regression masking, all Phase 7/9D baseline assets remain byte-for-byte immutable and protected by automated SHA-256 integrity tests:
- `benchmarks/retrack/golden_tasks.json`: `3ca041be5adb31d0483b27893593be9c62449264add54807723556dcbf292a91`
- `benchmarks/retrack/context_engine_baseline_scorecard.md`: `259c7648c77b2606921af413261c1f8f6671707cefa13bec300b84c966946cdc`
- `backend/tests/test_benchmark_baseline_contract.py`: `ae6fe23b90a275020860e30d5431b22fde0b38358a9e70d566be550b515eccac`
