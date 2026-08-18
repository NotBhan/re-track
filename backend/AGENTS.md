# Purpose

Owns the backend services for RE:Track (RefinedEngine Track).

Responsibilities include repository indexing, Cognee integration, deterministic AST call graph extraction, context retrieval, memory management, Context Package generation, and reproducible benchmarks.

---

# Ownership

Owns:

- CogneeService (Cognee lifecycle wrapper: remember, recall, improve, forget)
- IndexingService (incremental delta indexing + .gitignore-aware filtering)
- ManifestService (SHA256 file fingerprinting)
- LLMProviderService (OpenAI-compatible multi-provider & model health)
- CGCService (CodeGraphContext structural graph queries)
- IntentParserService (task intent & symbol extraction)
- ContextService & PackageBuilder (dedup → rank → compress → render)
- BudgetManager (line-boundary token compression and priority enforcement)
- MarkdownRenderer (structured markdown artifact generation)
- RepositorySummaryGenerator (Depth-2.5 framework grouping + 2-pass AST call graph engine)
- BenchmarkEngine (`backend/app/api/benchmarks.py` — full source baseline tokenization, discrete latencies, run metadata)
- API Commands (`backend/app/api/commands.py`) & Schemas (`backend/app/api/schemas.py`)
- CLI (`backend/app/cli/`)
- Test Suites (`backend/tests/` — 294 unit tests + `test_ast_integrity.py`)

---

# Current Status

Production services implemented and verified:

- CogneeService ✅
- IndexingService (incremental delta indexing + .gitignore filtering) ✅
- ManifestService (SHA256 file fingerprinting) ✅
- LLMProviderService (Multi-provider Ollama / LM Studio health) ✅
- IntentParserService (task intent & symbol extraction) ✅
- ContextService (discrete latency tracking: retrieval, ranking, synthesis) ✅
- PackageBuilder & BudgetManager (line-boundary token compression) ✅
- RepositorySummaryGenerator (2-pass deterministic Python & TypeScript AST resolver) ✅
- BenchmarkEngine (authoritative baseline tokenization, compression ratio, token savings %) ✅
- Hardware Telemetry (detected GPU presence vs active execution device, RAM pressure) ✅
- Tests: 294 tests passing ✅

---

# Deterministic AST Call Graph Invariants

1. **Resolution Pipeline**:
   `AST Parse` → `Module Symbol Table` → `Import/Alias Table` → `Qualified Name Resolution` → `Internal Symbol Check` → `CallEdge Generation`.
2. **Backend Invariant**:
   Every edge strictly satisfies:
   `assert edge.source in node_ids and edge.target in node_ids`
   Self-loops and unresolved/dynamic symbols produce **0 internal edges**.
3. **5 Explicit Graph States**:
   `"not_analyzed"`, `"analyzing"`, `"analyzed"` (>0 edges), `"zero_edges"` (isolated symbols), `"failed"`.

---

# Local Contracts

1. Backend must remain independent from frontend implementation.
2. Business logic belongs here; frontend does not infer or fabricate state.
3. All Cognee interactions must go through `CogneeService`.
4. Call graph extraction must stay inside `RepositorySummaryGenerator._build_call_graph`.
5. Benchmark calculations must use exact codebase tokenization against the configured tokenizer.

---

# Verification

```bash
cd backend/
source .venv/bin/activate

# Full test suite (294 passed)
pytest tests/ -q

# AST deterministic resolution integrity tests
pytest tests/test_ast_integrity.py -v
```

Run backend server:

```bash
.venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port 8765
```

---

# Child DOX Index

- `app/` — Production backend: config, core, models, services, utils, api.
- `app/config/` — Environment loading, provider configuration, Cognee config setup.
- `app/core/` — Structured logging.
- `app/models/` — Data models (`CallNode`, `CallEdge`, `RepositorySummary`, `AgentContextResponse`, `HealthResponse`, `MemoryStatsResponse`).
- `app/services/` — `CogneeService`, `IndexingService`, `ContextService`, `PackageBuilder`, `BudgetManager`, `MarkdownRenderer`, `RepositorySummaryGenerator`.
- `app/services/pipeline/` — Pipeline stages: Deduplicator, Ranker, Compressor, Categorizer, ReferenceResolver.
- `app/api/` — API commands, Pydantic schemas, benchmark runner, repo metadata persistence.
- `app/cli/` — Typer CLI application.
- `tests/` — Test suite including unit tests, integration tests, and `test_ast_integrity.py`.
