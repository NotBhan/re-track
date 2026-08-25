# Phase 10C Architectural Design: Expanded Retrieval Benchmarking

**Phase**: 10C  
**Title**: Multi-Repository Golden Task Retrieval Benchmarking & Mutation Evaluation  
**Role**: Principal Retrieval Engineer, Evaluation Architect, and Research Validation Lead  
**Status**: ARCHITECTURAL DESIGN (APPROVED BASELINE)  
**Contract Baseline**: Root `AGENTS.md`, `docs/architecture.md`, `docs/development_plan.md`, `docs/architecture/phase-10a-audit.md`, `docs/architecture/phase-10b-audit.md`  

---

## 1. Executive Summary & Purpose

Phase 10C expands RE:Track's quantitative retrieval evaluation from the single-repository 20-task benchmark (`benchmarks/retrack/`) into a statistically comprehensive, **multi-repository golden task benchmark suite** (`benchmarks/expanded/`).

The objectives are:
1. **Multi-Repository Generalization**: Validate retrieval across 6 distinct fixture repositories rather than relying solely on RE:Track's own codebase.
2. **Phase 10B Structural Verification**: Quantify retrieval performance on Tree-sitter extracted relationships: AST calls, class inheritance, interface implementation, type references, JSX component render trees, barrel re-export chains, and `tsconfig.json` path aliases.
3. **Phase 10A Incremental Indexing Invariants**: Empirically evaluate cold indexing, warm NOOP reuse, and 7 deterministic repository mutation scenarios (file modification, addition, deletion, rename, relinking) against expected parse counts and retrieval accuracy.
4. **Baseline Isolation & Immutability**: Keep the frozen Phase 7/9D benchmark (`benchmarks/retrack/`) byte-for-byte untouched, establishing a new, separate Phase 10C baseline scorecard.

---

## 2. Inconsistency Resolution Log

| Identified Challenge | Analysis & Root Cause | Architectural Decision |
|---|---|---|
| **Benchmark Leakage Risk** | If benchmark repos live in the primary repo, regular scans might index benchmark code. | Benchmark repositories reside in `benchmarks/corpus/`, excluded from default repository scanning unless explicitly registered as a target repo. |
| **Static vs Incremental Tasks** | Static retrieval tasks cannot prove Phase 10A incremental behavior (0-parse NOOP, selective relinking). | Phase 10C incorporates a dedicated **Incremental Mutation Framework** executing 7 deterministic mutation scenarios on isolated temporary copies. |
| **Relationship Correctness** | A file containing a target symbol might be retrieved without the retrieval engine actually resolving the typed edge. | Relationship Coverage explicitly requires matched, typed, resolved edge tuples `(source_id, target_id, kind)` in the synthesized context package. |
| **Noise Ratio Ambiguity** | Measuring noise purely as `1 - Precision` penalizes helpful context files. | Ground truth specifies both `disallowed_noise` and `allowed_evidence`. Unlisted files that are not disallowed are categorized as neutral context. |
| **Benchmark Execution Time** | Running 36 tasks across 6 repos with multiple mutation scenarios could exceed CI budget. | Benchmark execution is decoupled into fast cold/warm retrieval (< 10s) and targeted incremental mutation tests (< 5s), achieving the < 15s total budget. |

---

## 3. Architecture & Subsystem Layout

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                 BENCHMARK SUITE ARCHITECTURE                             │
├────────────────────────────────────────┬─────────────────────────────────────────────────┤
│        FROZEN BASELINE (PHASE 7/9D)    │           EXPANDED BENCHMARK (PHASE 10C)        │
│  benchmarks/retrack/                   │  benchmarks/corpus/                             │
│   ├── golden_tasks.json (20 tasks)     │   ├── repo_01_py_backend/                      │
│   └── baseline_scorecard.md (FROZEN)   │   ├── repo_02_ts_react/                        │
│                                        │   ├── repo_03_ts_barrel/                       │
│  backend/tests/                        │   ├── repo_04_polyglot/                        │
│   └── test_benchmark_baseline_contract │   ├── repo_05_ts_alias/                        │
│       (Asserts byte-for-byte lock)     │   └── repo_06_monorepo/                        │
│                                        │  benchmarks/expanded/                           │
│                                        │   ├── golden_tasks.json (36 tasks)              │
│                                        │   ├── benchmark_results.json                    │
│                                        │   └── benchmark_scorecard.md                    │
└────────────────────────────────────────┴─────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             EXPANDED EVALUATOR PIPELINE                                  │
│  backend/app/evaluation/expanded_benchmark.py                                            │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│  1. Corpus Loader & Schema Validator (validates repository paths & task definitions)     │
│  2. Cold Indexer & Warm Cache Manager (manages Manifest 2.0 & ContextCacheEngine)        │
│  3. Incremental Mutation Runner (7 isolated temp-copy mutation scenarios)                │
│  4. Metric Engine: Precision@K, Recall@K, Critical Coverage, Noise Ratio, Relationships  │
│  5. Multi-Level Attributor: Global, Repository-Level, Category-Level, Task-Level         │
│  6. Report Generator: Machine-readable JSON + Human-readable Markdown Scorecard           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Benchmark Corpus Composition

The corpus consists of 6 self-contained, deterministic repositories located in `benchmarks/corpus/`:

| Repository ID | Tech Stack | Architectural Characteristic | Primary Test Focus |
|---|---|---|---|
| `py_backend` | Python 3.12 | Layered architecture: domain entities, use cases, ports, adapters, FastAPI routers | Python AST symbol discovery, call hierarchies, dependency injection |
| `ts_react` | TypeScript, React 19, TSX | Modern SPA: custom hooks, Context API, component hierarchy, Router | JSX component renders, hook calls, UI state flow |
| `ts_barrel` | TypeScript | Multi-tier library with deep barrel re-exports (`export *`, `export { X as Y }`) | Recursive barrel re-export resolution, namespace exports |
| `polyglot` | Python + TypeScript | FastAPI backend + React Vite frontend with shared API contract models | Cross-language endpoint-to-client retrieval, unified graph |
| `ts_alias` | TypeScript, Next.js | `tsconfig.json` with `baseUrl` and wildcard `paths` (`@/*`, `@core/*`, `@shared/*`) | Compiler-compliant alias resolution, multi-target mappings |
| `monorepo` | TS / Python Monorepo | Multi-package workspace with internal workspace dependencies (`@acme/core`, `@acme/ui`) | Cross-package boundary retrieval, workspace root isolation |

---

## 5. Canonical 12-Category Task Taxonomy

Phase 10C defines exactly 12 canonical retrieval categories (3 tasks per category across the corpus = 36 total tasks):

```text
┌───────────────────────────────────────────────────────────────────────────────────┐
│                           12 CANONICAL RETRIEVAL CATEGORIES                       │
├────────────────────────────────────────┬──────────────────────────────────────────┤
│ 1. python_layered_architecture         │ 7. polyglot_cross_language               │
│ 2. typescript_structural               │ 8. calls_relationship                    │
│ 3. javascript_structural               │ 9. inherits_implements                   │
│ 4. barrel_reexport                     │ 10. type_reference                       │
│ 5. path_alias                          │ 11. jsx_render                           │
│ 6. cross_package_monorepo              │ 12. noise_discrimination                 │
└────────────────────────────────────────┴──────────────────────────────────────────┘
```

### Detailed Category Specifications

1. **`python_layered_architecture`**:
   - *Description*: Retrieves across domain entities, use cases, repository interfaces, and FastAPI routes.
   - *Phase Alignment*: Validates native Python AST symbol and call extraction.
2. **`typescript_structural`**:
   - *Description*: Retrieves classes, methods, functions, and interfaces within TypeScript modules.
   - *Phase Alignment*: Validates Phase 10B Tree-sitter TypeScript grammar extraction.
3. **`javascript_structural`**:
   - *Description*: Retrieves CommonJS (`require`, `module.exports`), ES module exports, and arrow functions.
   - *Phase Alignment*: Validates Phase 10B JavaScript grammar and CommonJS compatibility.
4. **`barrel_reexport`**:
   - *Description*: Traces symbols exported through multi-level `index.ts` barrel files (`export * from './Button'`, `export { User as UserModel }`).
   - *Phase Alignment*: Validates Phase 10B `TSCrossFileLinker` re-export traversal up to depth 5.
5. **`path_alias`**:
   - *Description*: Resolves module imports configured via `tsconfig.json` `compilerOptions.paths` (e.g. `@core/auth` -> `packages/core/src/auth.ts`).
   - *Phase Alignment*: Validates Phase 10B `TSModuleResolver` paths and wildcard substitution.
6. **`cross_package_monorepo`**:
   - *Description*: Locates symbols and dependencies spanning distinct packages in a monorepo workspace.
   - *Phase Alignment*: Validates workspace root boundary containment and multi-package indexing.
7. **`polyglot_cross_language`**:
   - *Description*: Connects frontend API client calls with corresponding backend Python route handlers and schemas.
   - *Phase Alignment*: Validates unified multi-language call graph coexistence without namespace collisions.
8. **`calls_relationship`**:
   - *Description*: Validates explicit invocation edges `(Caller -> Callee, kind="calls")` across files.
   - *Phase Alignment*: Validates call edge precision and edge endpoint existence.
9. **`inherits_implements`**:
   - *Description*: Identifies class inheritance (`extends`) and interface implementations (`implements`).
   - *Phase Alignment*: Validates class heritage and interface extraction.
10. **`type_reference`**:
    - *Description*: Traces type alias and interface usage across function signatures and return types.
    - *Phase Alignment*: Validates type dependency resolution.
11. **`jsx_render`**:
    - *Description*: Maps component hierarchies where parent components render child components (`<Button />`, `<Dialog.Root />`).
    - *Phase Alignment*: Validates JSX opening and self-closing element component render edges.
12. **`noise_discrimination`**:
    - *Description*: Evaluates whether queries with distractors avoid retrieving irrelevant files (`disallowed_noise`).
    - *Phase Alignment*: Validates Context Engine relevance filtering and noise suppression.

---

## 6. Golden Task Data Model

```json
{
  "task_id": "EXP-BARREL-01",
  "repository_id": "ts_barrel",
  "category": "barrel_reexport",
  "difficulty": "medium",
  "task_prompt": "Where is the canonical implementation of the NotificationBadge component exported through the UI package barrel?",
  "expected_files": [
    "packages/ui/src/components/NotificationBadge.tsx",
    "packages/ui/src/components/index.ts",
    "packages/ui/src/index.ts"
  ],
  "critical_files": [
    "packages/ui/src/components/NotificationBadge.tsx"
  ],
  "expected_symbols": [
    "NotificationBadge",
    "BadgeProps"
  ],
  "expected_relationships": [
    {
      "source": "packages/ui/src/index.ts#NotificationBadge",
      "target": "packages/ui/src/components/NotificationBadge.tsx#NotificationBadge",
      "kind": "re_exports"
    }
  ],
  "allowed_evidence": [
    "packages/ui/package.json"
  ],
  "disallowed_noise": [
    "packages/core/src/logger.ts",
    "packages/ui/src/components/Avatar.tsx"
  ],
  "mutation_scenario": null
}
```

---

## 7. Mathematical Evaluation Metric Formulas

### 1. Precision@K
$$\text{Precision@K} = \frac{|\text{Retrieved Files} \cap \text{Expected Files}|}{|\text{Retrieved Files}|}$$

### 2. Recall@K
$$\text{Recall@K} = \frac{|\text{Retrieved Files} \cap \text{Expected Files}|}{|\text{Expected Files}|}$$

### 3. Critical Evidence Coverage
$$\text{Critical Coverage} = \frac{|\text{Retrieved Files} \cap \text{Critical Files}|}{|\text{Critical Files}|}$$
*(If $|\text{Critical Files}| = 0$, defaults to $1.0$).*

### 4. Noise Ratio
$$\text{Noise Ratio} = \frac{|\text{Retrieved Files} \cap \text{Disallowed Noise}|}{|\text{Retrieved Files}|}$$
*(Measures intrusion of explicitly irrelevant distractor files).*

### 5. Relationship Coverage
$$\text{Relationship Coverage} = \frac{|\text{Retrieved Resolved Edges} \cap \text{Expected Relationships}|}{|\text{Expected Relationships}|}$$
*(Requires both source and target endpoints to match, with kind equivalence).*

### 6. Token Efficiency
$$\text{Token Efficiency} = 1.0 - \left(\frac{\text{Retrieved Context Tokens}}{\text{Full Repository Baseline Tokens}}\right)$$

---

## 8. Incremental Mutation Evaluation Framework

To evaluate Phase 10A incremental indexing invariants dynamically, the benchmark runner executes 7 isolated mutation scenarios against temporary copies of fixture repositories:

| Mutation Scenario | Executed Operation | Expected Parse Observable | Expected Reuse Observable | Expected Graph Observable |
|---|---|---|---|---|
| `cold_initial_index` | Index fresh repository from scratch | `files_parsed == N` | `files_reused == 0` | Full graph synthesized |
| `warm_noop_reindex` | Re-index unchanged repository | `files_parsed == 0` | `files_reused == N` | `0` AST parses, identical graph |
| `single_file_modification` | Mutate 1 source file (add function) | `files_parsed == 1` | `files_reused == N - 1` | Relinked edges for modified file |
| `single_file_addition` | Add 1 new component file | `files_parsed == 1` | `files_reused == N` | New nodes & edges registered |
| `single_file_deletion` | Delete 1 leaf module | `files_parsed == 0` | `files_reused == N - 1` | Deleted node & edges expunged |
| `rename_without_edit` | Rename file without modifying content | `files_parsed == 0` | `files_reused == N` | Fingerprint transferred, 0 re-parse |
| `dependency_relink` | Modify an imported barrel file | `files_parsed == 1` | `files_reused == N - 1` | Downstream callers relinked |

---

## 9. Immutability & Determinism Invariants

1. **Frozen Baseline Lock**: `backend/tests/test_expanded_benchmark_contract.py` validates that `benchmarks/retrack/golden_tasks.json` and `benchmarks/retrack/context_engine_baseline_scorecard.md` have unchanged SHA-256 checksums matching the Phase 9D baseline.
2. **Deterministic Traversal**: Repositories, files, and tasks are sorted lexicographically by ID/path before evaluation.
3. **Zero Network Calls**: All evaluations run offline against local benchmark fixtures.
4. **No Synthetic Hints**: Source fixtures contain realistic application code without artificial keywords or task-prompt marker comments.
5. **Two-Pass Reproducibility**: Running the expanded benchmark suite consecutively on the same machine produces identical floating-point scores within $\epsilon < 10^{-6}$.
