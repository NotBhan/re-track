# RE:Track Benchmark & Context Engine Evaluation Methodology

## Purpose

This document formalizes the evaluation framework, metric definitions, and baseline methodology used to measure and benchmark RE:Track's Context Engine in Phase 7A.

---

## 1. Core Hypothesis

> *"Given a developer task and a repository, RE:Track should identify and assemble the smallest useful set of repository evidence required by an AI agent."*

Evaluation measures **evidence retrieval quality** and **context efficiency**, not raw token throughput or indiscriminate text recall.

---

## 2. Evaluation Pipeline Boundary (Phase 7A Corrected)

In Phase 7A, the evaluation harness was corrected to execute the **actual production Context Engine entry point** rather than an isolated sub-pipeline or synthetic mock structure:

```text
GoldenTask
   │
   ▼
ContextUseCases.get_agent_context(AgentContextRequest)
   ├── ContextCacheEngine (cleared per task for clean evaluation)
   ├── IntentParser / parse_intent_heuristics
   ├── IndexingService.discover_files + filter_files
   ├── RepositorySummaryGenerator.generate
   ├── CGCService.query_structural_context (AST Call Graph Analysis)
   ├── ContextService.generate_context_package (Cognee/Vector Recall + PackageBuilder)
   └── SourceSearchService.extract_relevant_snippets
   │
   ▼
AgentContextResponse (real Markdown, real related_files, real extracted_symbols, real timing)
   │
   ▼
ContextEngineEvaluator.evaluate_task()
```

### Controlled Boundary Conditions:
- **Zero Synthetic Mocking**: No synthetic `RecallResult` objects or fabricated relevance scores are injected into the E2E benchmark.
- **Cache Isolation**: ContextCache is cleared between task runs to measure true synthesis cost rather than cache replay.
- **Local Fallback Mode**: When running in offline/headless test environments without active GPU/Ollama embeddings, `CogneeService.recall()` falls back cleanly to deterministic AST and keyword snippet synthesis, isolating evaluation from external network flakes.

---

## 3. Canonical Evaluation Dataset (`benchmarks/retrack/golden_tasks.json`)

The golden task dataset consists of 20 realistic software engineering tasks across four core categories:

1. **Architecture & Composition (5 tasks)**:
   - System topology, composition root initialization, storage duality, memory capability segregation, and router modularization.
2. **Bug Localization (5 tasks)**:
   - Storage path mutations, cache invalidation failures, priority budget trimming errors, concurrency lock collisions, and provider health fallbacks.
3. **Feature Addition (5 tasks)**:
   - Implementing new capability ports (e.g. MCP), registering indexing file extensions, adding categorization rules, extending intent heuristics, and adding package persistence endpoints.
4. **Refactoring & Symbol Impact (5 tasks)**:
   - Composition root refactoring (DEBT-003), DTO isolation, AST call graph generation, package builder pipeline assembly, and hardware telemetry adapters.

---

## 4. Quantitative Evaluation Metrics

### 4.1 Collision-Safe File Matching
- Paths are normalized by removing `./`, backslashes, and trailing slashes.
- Matching requires an exact normalized match OR a suffix match where the shorter path contains at least one directory separator (`/`).
- **Bare basename matching without directory context is strictly disallowed** (e.g. `context.py` does NOT match `backend/app/api/routers/context.py`).

### 4.2 Word-Boundary Symbol Matching
- Symbol evidence is recognized through structured response fields (`extracted_symbols`, `callers`, `callees`), backticked code tokens (`` `{symbol}` ``), or word-boundary regex (`\b{symbol}\b`).
- Arbitrary substring occurrences inside unrelated prose words are rejected.

### 4.3 Metric Formulas

1. **Precision@K ($P@K$)**:
   $$\text{Precision@K} = \frac{|\text{Retrieved Files}_{1..K} \cap \text{Expected Files}|}{\min(K, |\text{Retrieved Files}|)}$$
   - Target: $\ge 0.400$.

2. **Recall@K ($R@K$)**:
   $$\text{Recall@K} = \frac{|\text{Retrieved Files}_{1..K} \cap \text{Expected Files}|}{|\text{Expected Files}|}$$
   - Target: $\ge 0.500$.

3. **Critical Evidence Coverage ($C_{\text{crit}}$)**:
   $$C_{\text{crit}} = \frac{|\text{Retrieved Crit Files}| + |\text{Retrieved Crit Symbols}|}{|\text{Total Crit Files}| + |\text{Total Crit Symbols}|}$$
   - Target: $\ge 0.600$.

4. **Noise Ratio ($N_{\text{ratio}}$)**:
   $$N_{\text{ratio}} = \frac{|\text{Retrieved Files} \cap \text{Known Irrelevant Files}|}{|\text{Retrieved Files}|}$$
   - Target: $\le 0.200$.

5. **Token Compression Ratio ($CR$)**:
   $$CR = \frac{\text{Baseline Source Tokens}}{\text{Context Package Tokens}}$$
   - Target: $\ge 5.0\text{x}$.

6. **Monotonic Latency**:
   - Total context synthesis time measured in milliseconds using `time.perf_counter()`.

---

## 5. Execution Commands

```bash
# Run automated evaluation suite (16 tests)
cd backend && uv run pytest tests/evaluation/ -v -s

# Run full regression suite (374 tests)
cd backend && uv run pytest tests/ -q
```
