# Expanded Retrieval Benchmarking (Phase 10C)

## Overview

The Expanded Retrieval Benchmarking suite provides empirical, relationship-aware evaluation of RE:Track's code-intelligence engine across multi-file repositories, varied programming languages, and modern architectural conventions.

## Key Capabilities

### 1. Multi-Repository Fixtures
The benchmark operates against 6 synthetic repositories designed to exercise real-world software patterns:
- **`py_backend`**: Layered hexagonal architecture with domain models, abstract ports, application services, and infrastructure stores.
- **`ts_react`**: Modern React application utilizing context providers, custom hooks, and JSX hierarchy.
- **`ts_barrel`**: Direct and indirect barrel re-export trees (`index.ts` with named, default, and wildcard exports).
- **`polyglot`**: Cross-language full-stack repository with Python backend services and TypeScript React frontend clients.
- **`ts_alias`**: TypeScript path alias resolution using `tsconfig.json` path mappings (`@core/*`, `@features/*`, `@shared/*`).
- **`monorepo`**: Multi-package workspaces with cross-package type references, engine parsers, and UI components.

### 2. Comprehensive Retrieval Evaluation
- **36 Golden Retrieval Tasks**: Spanning 12 technical categories (3 tasks each).
- **Multi-Dimensional Metrics**: Evaluates Precision@K, Recall@K, Critical Evidence Coverage, Noise Ratio, Relationship Coverage, Token Efficiency, and Retrieval Latency.
- **AST Relationship Awareness**: Validates caller-callee (`calls`), class/interface inheritance (`inherits`), type imports (`imports`), and component rendering (`renders`).

### 3. Incremental Indexing & Mutation Testing
Evaluates 7 realistic repository mutation workflows:
- Cold initial repository indexing.
- Warm no-op reindexing with 100% AST reuse.
- Single file modification with isolated incremental re-parse.
- Single file addition and graph update.
- Single file deletion and graph cleanup.
- File rename without content modification.
- Dependency modification and cross-file graph relinking.

## Automated Verification

Run the expanded benchmark suite and contract tests with:

```bash
# Run all expanded benchmark tests
cd backend && uv run pytest tests/test_expanded_benchmark*.py -v

# Run full expanded benchmark evaluation runner and generate scorecard
cd backend && uv run python -c "
from app.evaluation.expanded_benchmark import ExpandedBenchmarkRunner
runner = ExpandedBenchmarkRunner(
    corpus_dir='../benchmarks/corpus',
    golden_tasks_file='../benchmarks/expanded/golden_tasks.json',
    results_output_file='../benchmarks/expanded/benchmark_results.json',
    scorecard_output_file='../benchmarks/expanded/benchmark_scorecard.md',
)
summary = runner.run_suite()
print('Passed:', summary.passed_tasks, '/', summary.total_tasks)
"
```
