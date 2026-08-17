# Purpose

Owns the React frontend for RE:Track (RefinedEngine Track).

Responsible for user interaction, repository visualization, and call graph rendering.

---

# Ownership

Owns:

- Dashboard (Prompt Workbench + Repository AST Map)
  - Prompt Workbench — task input, agent context synthesis, Context Package viewer
  - Repository AST Map — two sub-views:
    - Directory List — filterable subfolder/symbol list
    - Call Graph — interactive force-directed SVG visualization
- Memory Viewer
- Benchmarks
- Settings
- Repository store (Zustand, `src/stores/repository-store.ts`)
- Health store (`src/stores/health-store.ts`)
- Component library (`src/components/`)
- Type definitions (`src/types/repository.ts` — includes `CallGraphNode`, `CallGraphEdge`)

---

# Current Status

Milestone 3 — Frontend Foundation: **Completed**
Milestone 4 — Repository Knowledge Layer (UI): **Completed**
Milestone 5 — Call Graph Visualization: **Completed**
Milestone 6 — Polish: **In Progress**

Implemented and verified:

- Vercel Geist monochrome aesthetic (black canvas, `#262626` borders, `Geist Mono`) ✅
- Repository dropdown in Dashboard for fast repo switching ✅
- Repository AST Map with Directory List sub-view ✅
- CallGraphView.tsx — interactive force-directed SVG, no external lib ✅
  - Spring simulation at 60 fps
  - Drag nodes, scroll-to-zoom, click-drag pan
  - Node shapes by kind: square=class, diamond=component, circle=function/method
  - Edge styles: solid=calls, dashed=imports, thick=inherits, dotted=renders
  - Hover tooltip with label, kind, file, line number
  - Legend and Reset View button
- Dynamic "N nodes · M edges" count badge ✅
- `CallGraphNode` and `CallGraphEdge` types in `src/types/repository.ts` ✅

---

# Local Contracts

Frontend must not contain backend business logic.

Communicate with backend exclusively through Tauri IPC (`src/lib/api.ts`).

All repository data types live in `src/types/repository.ts`.

Design system: Vercel Geist aesthetic — `#000000` / `#0a0a0a` canvas, `#262626` borders, `Geist Mono` font, no gradients except subtle.

When adding new call graph node/edge kinds, update both `src/types/repository.ts` and `CallGraphView.tsx` (legend + render logic + color maps).

---

# Work Guidance

Prefer reusable components in `src/components/`.

Keep state localized where possible; use Zustand stores for shared state.

Use Tailwind utility classes and design tokens — no inline style strings for colors.

`CallGraphView.tsx` owns the simulation loop. Do not move simulation state into a global store; keep it local to the component.

---

# Verification

```bash
npm run build          # Must complete with 0 TypeScript errors
npx tsc --noEmit       # Type check
```

---

# Child DOX Index

src/components/
  Shared UI components, design tokens, and feature-level components.

src/components/repositories/
  RepositoryCard.tsx — Repository card view.
  RepositoryDetailPanel.tsx — Right panel with repository summary, files, and actions.
  CallGraphView.tsx — Interactive force-directed call graph SVG.
  ReindexModal.tsx — Telemetry progress modal for repository indexing.

src/components/context-builder/
  ContextPipelineInputs.tsx — Parameter inputs for multi-stage context synthesis.
  ContextPipelineVisualization.tsx — Visual pipeline stages & metrics.
  ContextPackageOutputPanel.tsx — Formatted/Raw Context Package preview & actions.

src/components/context-packages/
  ContextPackageCard.tsx — Saved Context Package card with diff/copy/export tools.

src/pages/
  ContextStudio.tsx — Main workspace (Prompt Workbench + Synthesis Modal + AST Map).
  Repositories.tsx — Repository catalog & management.
  KnowledgeExplorer.tsx — Structural AST and call graph inspection.
  ContextBuilder.tsx — Multi-stage context pipeline studio.
  ContextPackages.tsx — Saved Context Packages library & comparison.
  Memory.tsx — Cognee dataset inspector.
  Benchmarks.tsx — Latency & throughput analytics.
  Settings.tsx — Backend, Ollama, Cognee, & Storage configuration.

src/stores/
  repository-store.ts — Indexed repositories, active selection, and reindexing telemetry.
  context-store.ts — Multi-stage context pipeline state.
  context-package-store.ts — Saved packages store with localStorage persistence.
  health-store.ts — Backend, Ollama, and Cognee telemetry polling.

src/types/
  repository.ts — Repository, CallGraphNode, CallGraphEdge, ScanResult.

src/lib/
  api.ts — Tauri IPC wrapper for all backend commands.
