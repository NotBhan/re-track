# Purpose

Owns the backend services for RE:Track (RefinedEngine Track).

Responsibilities include project indexing, Cognee integration, context retrieval, memory management, and Context Package generation.

---

# Ownership

Owns:

- CogneeService
- IndexingService
- ContextService
- PackageBuilder
- BudgetManager
- MarkdownRenderer
- RepositorySummaryGenerator
- Pipeline stages (Deduplicator, Ranker, Compressor, Categorizer, ReferenceResolver)
- StatsLogger
- Configuration
- Data Models
- Error Handling
- Logging

---

# Current Status

Milestone 1 — Backend Foundation: **Completed**
Milestone 2 — API Layer: **Completed**
Milestone 3 — Package Generation: **Completed**
Milestone 4 — Integration: **Completed**
Milestone 5 — Evidence & Validation: **Completed**

Production services implemented and verified:

- CogneeService ✅
- IndexingService (incremental delta indexing) ✅
- ManifestService (SHA256 file fingerprinting) ✅
- LLMProviderService (OpenAI-compatible multi-provider & model health) ✅
- CGCService (CodeGraphContext structural graph queries) ✅
- IntentParserService (task intent & symbol extraction) ✅
- ContextService (rewired to PackageBuilder) ✅
- PackageBuilder ✅
- BudgetManager ✅
- MarkdownRenderer ✅
- RepositorySummaryGenerator ✅
- Pipeline stages (dedup, rank, compress, categorize, references) ✅
- StatsLogger ✅

API layer implemented and verified:

- Commands (health, get_backend_status, index_repository, generate_context, get_agent_context, forget_dataset) ✅
- Schemas (Pydantic request/response models with full metadata) ✅
- REST Endpoints (/health, /status, /index, /context, /api/v1/context, /packages) ✅

CLI implemented and verified:

- CLI commands (health, status, index, context, forget) ✅
- Rich terminal formatting (tables, panels, spinners, markdown) ✅

Evaluation implemented and verified:

- Benchmark framework (15 questions) ✅
- Quality metrics ✅
- Stats logging ✅
- Unit tests suite (11/11 passing) ✅

Next: Frontend Foundation & Native IPC verification

---

# Local Contracts

Backend should remain independent from frontend implementation.

Business logic belongs here.

All Cognee interactions must go through CogneeService.

Never call `cognee.*` directly outside CogneeService.

---

# Work Guidance

Keep modules focused.

Avoid unnecessary abstractions.

Prefer composition over complex inheritance.

Use structured logging (no print statements).

Use complete Python type hints.

---

# Verification

Verify backend behavior matches project documentation.

Set up the virtualenv first:

```bash
cd backend/
.venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port 8765
# or to create it fresh:
# uv venv .venv --python 3.12 && .venv/bin/pip install -r requirements.txt
```

Run playground scripts to validate Cognee integration:

```bash
cd backend/playground
.venv/bin/python setup.py
.venv/bin/python remember_demo.py
.venv/bin/python recall_demo.py
.venv/bin/python improve_demo.py
.venv/bin/python forget_demo.py
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
Data models (RememberResult, RecallResult, ContextPackage, RepositorySummary, PackageMetadata, IndexingProgress) and error hierarchy.

app/services/
CogneeService, IndexingService, ContextService, PackageBuilder, BudgetManager, MarkdownRenderer, RepositorySummaryGenerator, StatsLogger.

app/services/pipeline/
Pipeline stages: Deduplicator, Ranker, Compressor, Categorizer, ReferenceResolver.

app/api/
API layer: async commands exposing services, Pydantic request/response schemas with full metadata.

app/cli/
CLI layer: Typer application exposing API commands to developers. Rich terminal formatting.

playground/
Validation scripts for Cognee integration.
