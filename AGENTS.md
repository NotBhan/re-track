# DOX Framework

DOX (Documentation-Oriented eXecution) is the operational contract for this repository.

All AI agents must follow the DOX hierarchy before planning, modifying, or generating code.

Documentation is the source of truth for project intent. Implementation should remain synchronized with documentation throughout development.

---

# Core Contract

- Every `AGENTS.md` governs its subtree.
- Child `AGENTS.md` files inherit every parent contract.
- Child `AGENTS.md` files may specialize local behavior but may not weaken parent contracts.
- Documentation should evolve together with implementation.
- Never assume project knowledge from previous conversations. Re-read the applicable DOX chain in every session.
- **Truth Boundary Guarantee**: The backend is the sole authority for repository analysis, graph identity, memory statistics, benchmark measurements, and hardware telemetry. The frontend must NEVER invent missing nodes/edges, infer status from empty arrays, substitute static metrics, or recover missing data with synthetic fallbacks.

---

# Read Before Editing

Before modifying any file:

1. Read this root `AGENTS.md`.
2. Determine every file or directory that will be modified.
3. Walk from repository root to every target.
4. Read every `AGENTS.md` encountered.
5. Apply the nearest `AGENTS.md` as the local contract.
6. Respect `.agentignore` before scanning the repository.
7. Read only the documentation necessary for the current task.

---

# Planning Contract

Before implementing any feature determine:

- What problem is being solved?
- Is the feature inside the MVP scope?
- Which documentation owns this change?
- Which files actually require modification?
- Can existing implementation be reused?

Avoid unnecessary implementation.

---

# Update Contract

After meaningful changes:

- Update affected documentation.
- Remove stale documentation.
- Keep architecture synchronized.
- Keep memory model synchronized.
- Keep development plan synchronized.
- Keep Child DOX Index current.

---

# Documentation Hierarchy

1. `docs/vision.md`
2. `docs/problem_statement.md`
3. `docs/scope.md`
4. `docs/architecture.md`
5. `docs/implementation_plan.md`
6. `docs/repository_knowledge_model.md`
7. `docs/memory_model.md`
8. `docs/cognee_integration.md`
9. `docs/development_plan.md`
10. `docs/success_metrics.md`

---

# Verification Commands

Before completing work:

```bash
# Backend unit & integration tests (440 passed)
cd backend && uv run pytest tests/ -q

# AST integrity tests
cd backend && uv run pytest tests/test_ast_integrity.py -v

# Frontend TypeScript & build check
npm run build
```

---

# Child DOX Index

- `docs/` — Project documentation and design. Authoritative source for vision, architecture, implementation plan, repository knowledge model, and project contracts.
- `backend/` — Python backend: Cognee integration, deterministic AST call graph extraction, context engine, repository summary generation, benchmark runner, API layer.
- `src/` — React frontend: Context Studio, Knowledge Explorer (AST Topology & Call Graph), Repositories, Memory, Benchmarks, Settings.
- `src-tauri/` — Desktop runtime and native Tauri IPC integration.
- `scripts/` — Development and automation scripts.
- `examples/` — Example projects and demo datasets.
