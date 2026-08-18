# Purpose

Owns the React frontend for RE:Track (RefinedEngine Track).

Responsible for user interaction, repository visualization, call graph exploration, context generation, and telemetry presentation.

---

# Ownership

Owns:

- Context Studio (`src/pages/ContextStudio.tsx`)
  - Prompt Workbench — suggested prompt presets, live token counters, discrete latencies
  - Evidence Provenance Layer — extracted symbols, intent parsing, caller/callee links
  - Progressive Markdown Reveal — token-budgeted Context Package preview & export
- Knowledge Explorer (`src/pages/KnowledgeExplorer.tsx`)
  - 5-State AST Call Graph Topology View
  - Directory & Module Map — framework-aware hierarchy
  - Key Components & Entry Points
- Repositories (`src/pages/Repositories.tsx`) — Catalog, indexing telemetry, and deletion
- Memory (`src/pages/Memory.tsx`) — Multi-layer storage inspector (Ingested files, Vector Index, Knowledge Graph)
- Benchmarks (`src/pages/Benchmarks.tsx`) — Deterministic token baseline evaluation, compression ratios, latency breakdown, immutable run metadata
- Settings (`src/pages/Settings.tsx`) — AI provider configuration, storage, and system telemetry
- State Stores (`src/stores/`) — `repository-store`, `context-package-store`, `memory-store`, `health-store`
- Components (`src/components/`) — `CallGraphView`, `EvidenceProvenanceLayer`, `ProgressiveMarkdownReveal`, `SynthesisProgressBar`, `MemoryStats`
- Type Definitions (`src/types/repository.ts`)

---

# Current Status

- [x] **Visual Design System**: Vercel Geist monochrome dark palette, `#262626` hairline borders, `Geist Sans` & `Geist Mono` typography.
- [x] **Product Interaction Quality**: Keyboard accessibility, active request cancellation, toast feedback, non-blocking telemetry.
- [x] **Information Density & Workflow Clarity**: Task → Repository → Evidence → Context relationship strips, Symbol Inspector drawer, progressive synthesis progress bar.
- [x] **Validation & Integrity (Truth Boundary)**:
  - Strict 5-state AST call graph rendering (`not_analyzed`, `analyzing`, `analyzed`, `zero_edges`, `failed`).
  - No synthetic fallback nodes or mock edges; node IDs are strictly authoritative.
  - Connected path highlighting on hover/selection with inactive element dimming.
  - Multi-tier memory topology separation (Ingested files vs Vector index vs Knowledge graph).
  - Deterministic token reduction benchmarks against full source baseline.

---

# Local Contracts

1. **Truth Boundary Invariant**: The frontend must never invent missing graph nodes/edges, infer graph status from empty arrays, substitute static benchmark scores, or reinterpret unextracted states with fake zeroes.
2. **Backend Communication**: Communicate with backend exclusively through Tauri IPC (`src/lib/api.ts`).
3. **Data Types**: All repository data types live in `src/types/repository.ts`.
4. **State Management**: Keep local UI state inside components; use Zustand stores for cross-page persistence.
5. **CallGraphView Ownership**: `CallGraphView.tsx` owns the spring-force simulation loop. Do not move simulation state into a global store.

---

# Verification

```bash
npm run build          # Must complete with 0 TypeScript/Vite errors
npx tsc --noEmit       # Type check
```

---

# Child DOX Index

- `src/components/repositories/` — `CallGraphView.tsx`, `RepositoryCard.tsx`, `RepositoryDetailPanel.tsx`, `QuickContextModal.tsx`.
- `src/components/context-builder/` — `EvidenceProvenanceLayer.tsx`, `ContextPipelineInputs.tsx`.
- `src/components/dashboard/` — `ProgressiveMarkdownReveal.tsx`.
- `src/components/memory/` — `MemoryStats.tsx`.
- `src/components/benchmarks/` — `MetricCard.tsx`.
- `src/components/shared/` — `SynthesisProgressBar.tsx`, `ProviderAlertBanner.tsx`.
- `src/stores/` — Zustand stores for repositories, packages, memory, and health.
- `src/pages/` — `ContextStudio.tsx`, `KnowledgeExplorer.tsx`, `Repositories.tsx`, `Memory.tsx`, `Benchmarks.tsx`, `Settings.tsx`.
