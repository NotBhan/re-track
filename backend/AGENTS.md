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
6. **Deterministic retrieval mode**: `CogneeService.recall` always passes an explicit
   `SearchType` with `auto_route=False` (default `SearchType.CHUNKS` → `ChunksRetriever`).
   Retrieval must never let Cognee's query router select an LLM-backed strategy
   (`GRAPH_COMPLETION_COT` and friends) merely to choose a retrieval mode.
7. **Embedding provider identity is separate from the LLM provider identity.**
   `Settings.embedding_identity()` / `probe_embedding_provider()` report the configured
   embedding provider, endpoint, model and availability (`available` | `model_missing` |
   `unreachable` | `not_configured`). No provider/model substitution is ever performed.
8. **Retrieval failure is reported, never masked**: `ContextPackage.metadata.retrieval_state`
   / `ContextResponse.retrieval_state` are `ok` or `unavailable` with a truthful
   `retrieval_error`, while authoritative tiers (Tier 1 source, Tier 2 AST) remain the
   source of truth and evidence gating is unchanged.
9. **Single deterministic configuration precedence** (`app/config/settings.py`), highest wins
   per field: explicit constructor arguments → operator environment variables → persisted
   settings (`~/.retrack/settings.json`) → `backend/.env` → field defaults. `backend/.env` is
   resolved relative to the backend package, never the process working directory.
10. **No process-global provider contamination**: `Settings.apply_to_environment()` records the
    environment variables it writes, and construction removes those self-written values, so a
    prior `Settings` instance can never configure a later one. Env keywords remain a supported
    override only when the operator set them.
11. **Three independent identities, never inferred from one another**: interactive inference
    (`llm_provider` / `llm_endpoint` / `ollama.llm_model`), embeddings
    (`embedding_identity()`), and semantic-memory extraction
    (`semantic_memory_identity()` = `semantic_memory_provider` / `semantic_memory_endpoint` /
    `ollama.memory_model`). Each is resolved and reported separately.
12. **No semantic-memory model substitution**: `ollama.memory_model` / `SEMANTIC_MEMORY_MODEL`
    selects the dedicated extraction model. When it is empty the semantic-memory stage is
    explicitly `not_configured` with **zero** inference — the interactive reasoning model is
    never substituted. A configured-but-unserved extraction model is reported as
    `model_unavailable`. `Settings.probe_semantic_memory_provider()` reports
    `available | model_missing | unreachable | not_configured` and performs no substitution.
13. **Cognification performs no hidden model pass**: `CogneeService.add()` only ingests;
    `cognee.cognify()` / `cognee.remember()` are never invoked from the indexing/cognification
    path. LM Studio maps to litellm's `lm_studio` provider so Cognee uses
    `response_format: json_schema` (LM Studio rejects `json_object` with HTTP 400).

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
