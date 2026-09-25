# RE:Track Modern Desktop GUI — Source Contract

## Status

This GUI is the **accepted baseline** for the desktop experience: repository management, startup hydration, truthful progress/confidence presentation, rendered/raw context output, the shared dropdown system, and 80–150% scaling are implemented and verified. Extend it with incremental, contract-following fixes — do not redesign it from scratch. Checkpoint notes live in `docs/development_plan.md` (Interface Workstream Status).

## Architecture & Ownership

This directory contains the completely redesigned modern GUI for RE:Track.
It is organized into clean architectural layers:

- `app/` — Global application shell, navigation header, and notification/toast provider.
- `components/` — Quiet, atomic design system primitives (`Button`, `Input`, `Select`, `Badge`, `Dialog`, `Tabs`, `EmptyState`). `Select` is the single listbox control for every dropdown in the GUI.
- `features/` — High-cohesion, domain-focused user journey features:
  - `features/repositories/` — Repository Management destination: tracked-repository list, active selection, real-data summary panel, re-index/delete actions.
  - `features/code/` — Repository Catalog (AST explorer), CallGraphView (5-state integrity), ManifestTable, IndexingProgressView, RepositoryAddModal.
  - `features/context/` — ContextWorkbench, EvidenceViewer, ModelProcessingPanel (non-numeric runtime progress), SynthesisOutput (rendered/raw markdown), PackageDrawer.
  - `features/memory/` — MemoryHub (with explicit Derived Storage notice), IngestedFilesView, VectorSpaceView, KnowledgeGraphView.
  - `features/system/` — SystemHub, TelemetryGauges (truth boundary enforced), ProviderSettings, StorageSettings, DisplaySettings (UI scaling), DiagnosticsViewer, BenchmarkRunner.
- `stores/` — Lightweight Zustand domain stores (`repositoryStore`, `contextStore`, `memoryStore`, `systemStore`, `uiScaleStore`, `preferencesStore`).
- `lib/` — Tauri IPC bridge (`api.ts`), styling utilities (`utils.ts`).
- `test/` — Vitest regression suites; `e2e/` (repository root) holds live-backend Playwright specs.

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

5. **Startup Hydration**:
   Persisted repositories are hydrated on launch by `repositoryStore.bootstrapRepositories()`, which retries until the backend answers and re-synchronizes whenever the backend becomes reachable. The active repository is persisted in `localStorage` (`retrack:active-repository`) and restored on the next launch. UI surfaces must not present an empty repository state while hydration is still pending.

6. **Honest Progress and Confidence**:
   The GUI never fabricates percentages. Context synthesis shows elapsed time plus the runtime state reported by `/health` (concurrency slot/queue), because the provider contract exposes no token-level progress. Indexing shows the phase index reported by the backend IndexingService. Evidence confidence is rendered as a qualitative grounding tier (cross-validated / single-channel / not computed) rather than a bare percentage, and evidence strength is shown from the engine's own weighted score.

7. **UI Scale**:
   `uiScaleStore` applies CSS `zoom` to the document root and pins the root box to `viewport / factor` so the scaled layout stays exactly viewport-sized at 80–150%. Application chrome must size itself with `h-full`/`w-full`/flex percentages instead of `vh`/`vw` units, which do not follow a zoomed root.
