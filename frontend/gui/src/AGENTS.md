# Purpose

Owns the React frontend for RE:Track (RefinedEngine Track).

Responsible for user interaction, repository visualization, call graph exploration, context generation, and telemetry presentation.

---

# Ownership

Owns:

- Workspace (`src/pages/Workspace.tsx`, `src/components/workspace/`)
  - Workspace Header & Scope Selector
  - 4-Stage Lifecycle Stepper (`Scan` -> `Manifest` -> `AST Extraction` -> `Cognification`)
  - 50-Node Bounded AST Call Graph with 1-Hop Neighbor Expansion
  - Deterministic Manifest & Evidence Table with exact byte counts
- Context Studio (`src/pages/ContextStudio.tsx`)
  - 3-Column Studio Layout (Input Workbench / Retrieval Arbitration & Evidence / Context Package & History)
  - 4 Authoritative Retrieval Tiers (Filesystem Source, Manifest / AST, LanceDB / Kùzu, Cognee Semantic Memory)
  - Token Budget allocation & synthesis controls
  - Package History Drawer (`src/components/context-packages/PackageHistoryDrawer.tsx`)
- Memory Engine (`src/pages/Memory.tsx`, `src/components/memory/`)
  - Multi-tier derived storage inspector (Semantic Records, Vector Space, Knowledge Graph)
  - Provenance Drawer with SHA-256 verification and epistemic status notices
  - Strict Derived Storage Truth Boundary (`/memory` suppressed when no repo selected)
- System & Telemetry (`src/pages/SystemTelemetry.tsx`)
  - Global scope (independent of repository selection)
  - Three Runtime Identities: Configured Model, Verified Active Model, Last Executing Model
  - Truthful Hardware & Execution Telemetry (Device, CPU, RAM, GPU/VRAM or None detected, "Unavailable" when offline)
  - Unified System tabs: Provider & Runtime, Storage & Subsystems, Benchmarks, Diagnostics
- State Stores (`src/stores/`) — `repository-store`, `context-package-store`, `memory-store`, `health-store`
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

- `src/components/workspace/` — `WorkspaceHeader.tsx`, `LifecycleStepper.tsx`, `ManifestEvidenceTable.tsx`.
- `src/components/repositories/` — `CallGraphView.tsx` (50-node bounded + 1-hop expansion), `RepositoryCard.tsx`, `RepositoryDetailPanel.tsx`, `QuickContextModal.tsx`.
- `src/components/context-builder/` — `TierEvidenceStack.tsx`, `EvidenceProvenanceLayer.tsx`, `ContextPipelineInputs.tsx`.
- `src/components/context-packages/` — `PackageHistoryDrawer.tsx`.
- `src/components/dashboard/` — `ProgressiveMarkdownReveal.tsx`.
- `src/components/memory/` — `ProvenanceDrawer.tsx`, `DatasetTable.tsx`, `KnowledgeGraphView.tsx`, `VectorSpaceView.tsx`, `MemoryStats.tsx`.
- `src/components/settings/` — `OllamaSettings.tsx`.
- `src/components/benchmarks/` — `MetricCard.tsx`.
- `src/components/shared/` — `SynthesisProgressBar.tsx`, `ProviderAlertBanner.tsx`.
- `src/stores/` — Zustand stores for repositories, packages, memory, and health.
- `src/pages/` — `Workspace.tsx`, `ContextStudio.tsx`, `Memory.tsx`, `SystemTelemetry.tsx`.
