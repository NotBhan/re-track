# Purpose

Owns the backend services for RE:Track (RefinedEngine Track).

Responsibilities include repository indexing, Cognee integration, call graph extraction, context retrieval, memory management, and Context Package generation.

---

# Ownership

Owns:

- CogneeService
- IndexingService (delta + .gitignore-aware filtering)
- ContextService
- PackageBuilder
- BudgetManager
- MarkdownRenderer
- RepositorySummaryGenerator
  - `_build_repo_map` — directory structure grouping
  - `_extract_components` — Python AST + React/TS regex
  - `_build_call_graph` — `ast.Call` traversal + TS import chain
- Pipeline stages (Deduplicator, Ranker, Compressor, Categorizer, ReferenceResolver)
- StatsLogger
- Configuration
- Data Models (`CallNode`, `CallEdge`, `RepositorySummary`, `ComponentInfo`, etc.)
- Error Handling
- Logging

---

# Current Status

Milestone 1 — Backend Foundation: **Completed**
Milestone 2 — API Layer: **Completed**
Milestone 3 — Frontend Foundation: **Completed**
Milestone 4 — Repository Knowledge Layer: **Completed**
Milestone 5 — Call Graph: **Completed**
Milestone 6 — Polish: **In Progress**

Production services implemented and verified:

- CogneeService ✅
- IndexingService (incremental delta indexing + .gitignore filtering) ✅
- ManifestService (SHA256 file fingerprinting) ✅
- LLMProviderService (OpenAI-compatible multi-provider & model health) ✅
- CGCService (CodeGraphContext structural graph queries) ✅
- IntentParserService (task intent & symbol extraction) ✅
- ContextService (rewired to PackageBuilder) ✅
- PackageBuilder ✅
- BudgetManager ✅
- MarkdownRenderer ✅
- RepositorySummaryGenerator (Depth-2.5 + call graph) ✅
- CallGraphExtractor (embedded in RepositorySummaryGenerator) ✅
- Pipeline stages (dedup, rank, compress, categorize, references) ✅
- StatsLogger ✅

API layer implemented and verified:

- Commands: health, get_backend_status, index_repository, generate_context, get_agent_context, forget_dataset, get_repository_summaries, _persist_repo_metadata ✅
- Schemas (Pydantic request/response models with full metadata) ✅
- REST Endpoints (/health, /status, /index, /context, /api/v1/context, /packages) ✅

Call graph persistence:
- `call_graph_nodes` and `call_graph_edges` serialized to repo metadata store in `_persist_repo_metadata` ✅

Tests: 284+ tests passing ✅

---

# Local Contracts

Backend must remain independent from frontend implementation.

Business logic belongs here.

All Cognee interactions must go through CogneeService.

Never call `cognee.*` directly outside CogneeService.

Call graph extraction must stay inside `RepositorySummaryGenerator._build_call_graph`. Do not scatter AST parsing elsewhere.

---

# Work Guidance

Keep modules focused.

Avoid unnecessary abstractions.

Prefer composition over complex inheritance.

Use structured logging (no print statements).

Use complete Python type hints.

When adding new node/edge kinds to the call graph, update both `responses.py` (the dataclass) and `CallGraphView.tsx` (legend + render logic).

---

# Verification

```bash
cd backend/
source .venv/bin/activate
pytest tests/ -q                    # Must pass all 284+ tests
```

Run backend server:

```bash
.venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port 8765
```

---

# Child DOX Index

app/
  Production backend: config, core, models, services, utils, api.

app/config/
  Environment loading, provider configuration, Cognee config setup.

app/core/
  Structured logging.

app/models/
  Data models: RememberResult, RecallResult, ContextPackage, RepositorySummary,
  PackageMetadata, IndexingProgress, CallNode, CallEdge, DirectoryEntry,
  ComponentInfo, and error hierarchy.

app/services/
  CogneeService, IndexingService, ContextService, PackageBuilder, BudgetManager,
  MarkdownRenderer, RepositorySummaryGenerator (includes call graph extractor),
  StatsLogger.

app/services/pipeline/
  Pipeline stages: Deduplicator, Ranker, Compressor, Categorizer, ReferenceResolver.

app/api/
  API layer: async commands exposing services, Pydantic request/response schemas,
  repo metadata persistence with call graph data.

app/cli/
  CLI layer: Typer application exposing API commands to developers. Rich formatting.

playground/
  Validation scripts for Cognee integration.
