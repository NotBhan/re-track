# RE:Track Modern Desktop GUI — Source Contract

## Architecture & Ownership

This directory contains the completely redesigned modern GUI for RE:Track.
It is organized into clean architectural layers:

- `app/` — Global application shell, navigation header, and notification/toast provider.
- `components/` — Quiet, atomic design system primitives (`Button`, `Input`, `Badge`, `Dialog`, `Tabs`, `EmptyState`).
- `features/` — High-cohesion, domain-focused user journey features:
  - `features/code/` — Repository Catalog, CallGraphView (5-state integrity), ManifestTable, IndexingProgressView, RepositoryAddModal.
  - `features/context/` — ContextWorkbench, EvidenceViewer (5-tier evidence breakdown), SynthesisOutput, PackageDrawer.
  - `features/memory/` — MemoryHub (with explicit Derived Storage notice), IngestedFilesView, VectorSpaceView, KnowledgeGraphView.
  - `features/system/` — SystemHub, TelemetryGauges (truth boundary enforced), ProviderSettings, StorageSettings, DisplaySettings (UI scaling), DiagnosticsViewer, BenchmarkRunner.
- `stores/` — Lightweight Zustand domain stores (`repositoryStore`, `contextStore`, `memoryStore`, `systemStore`, `uiScaleStore`).
- `lib/` — Tauri IPC bridge (`api.ts`), styling utilities (`utils.ts`).
- `test/` — Full regression test suite verifying core user journeys.

---

## Local Contracts

1. **Visual System Contract (DESIGN-vercel.md)**:
   The visual system strictly adheres to the Geist design language:
   - High-contrast black-and-white duet with near-black `#000000`/`#0a0a0a` canvas and `#ededed` primary text.
   - Zero gratuitous chromatic chrome, glowing neon borders, or rainbow badges.
   - Strict semantic-only colors (blue for focus/links, emerald for success/active, amber for warning/degraded, red for errors/destructive).
   - Generous 36px+ interactive control target heights and user-controlled zoom scaling.

2. **Truth Boundary Guarantee**:
   The backend is the sole authority for repository analysis, graph identity, memory statistics, benchmark measurements, and hardware telemetry.
   The frontend must NEVER invent missing nodes/edges, infer status from empty arrays, substitute static metrics, or recover missing data with synthetic fallbacks.
   When telemetry is unavailable or backend is offline, components must display "Unavailable" rather than fabricated readings.

3. **Epistemic Clarity**:
   The memory engine features (`features/memory/`) must explicitly declare to the user that LanceDB vector chunks and Kùzu graphs represent derived knowledge rather than source ground truth.

4. **Presentation Independence**:
   Components only handle presentation and user interactions. No business logic, AST parsing, or graph traversal algorithms reside in the frontend. All data access flows through `src/lib/api.ts` directly to Tauri IPC invoke handlers.
