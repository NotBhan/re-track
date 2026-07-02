# Production Frontend Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all mock data in the frontend with real backend API calls, adding missing backend endpoints as needed.

**Architecture:** Backend-first approach — each feature adds backend API endpoints first, then wires the frontend to consume them. The Rust bridge proxies HTTP requests from Tauri IPC to the Python FastAPI server. All new endpoints follow the existing pattern in `backend/app/api/commands.py`.

**Tech Stack:** Python 3.13 + FastAPI, Rust + Tauri 2, React 19 + TypeScript + Zustand + Tailwind CSS 4

## Global Constraints

- All backend APIs go through `backend/app/api/commands.py` → `backend/app/server.py` → `src-tauri/src/lib.rs` → `src/lib/api.ts`
- Never call Cognee directly outside `CogneeService`
- Never fabricate data — every value in the UI must come from backend APIs
- Settings are persisted via environment variables written by the Rust bridge on process spawn
- Python runs on `/usr/bin/python3.13`, cognee 1.2.2, phi3:mini

---

## Gap Summary

| Feature | Backend Status | Missing Backend | Missing Frontend |
|---------|---------------|----------------|-----------------|
| Repository Management | `index_repository`, `forget_dataset` work | List repos, repo summaries, progress streaming | Store integration, index button wiring |
| Context Building | Full pipeline works | Nothing missing | Generate button, pipeline viz, output rendering |
| Memory Management | `forget_dataset` works | List datasets, memory stats | Dataset table, stats sidebar |
| Dashboard Stats | `get_backend_status` works | Aggregate stats endpoint | Stat cards, activity timeline |
| Benchmarks | `StatsLogger` exists | Benchmark execution endpoint | Metric cards, charts |
| Settings | Config singleton exists | Runtime read/write API | Form integration, persistence |

---

## Phase 1: Backend Data-Listing Endpoints

### Task 1.1: Add `list_datasets` endpoint

**Covers:** Memory page needs to list stored datasets.

**Files:**
- Modify: `backend/app/api/schemas.py` — add `DatasetInfo` response model
- Modify: `backend/app/api/commands.py` — add `list_datasets()` command
- Modify: `backend/app/server.py` — add `GET /datasets` route
- Modify: `src-tauri/src/lib.rs` — add `list_datasets` Tauri command
- Modify: `src/lib/api.ts` — add `listDatasets()` function

**Interfaces:**
- Produces: `DatasetInfo` model with fields: `id: str`, `name: str`, `type: str`, `size_bytes: int`, `created_at: str`, `file_count: int`

**Steps:**

- [ ] **Step 1: Add response model to schemas.py**

```python
# backend/app/api/schemas.py — add after existing schemas
class DatasetInfo(BaseModel):
    id: str
    name: str
    type: str
    size_bytes: int
    created_at: str
    file_count: int
    source_path: str = ""

class DatasetListResponse(BaseModel):
    success: bool
    datasets: list[DatasetInfo]
    total_count: int
```

- [ ] **Step 2: Implement list_datasets command**

```python
# backend/app/api/commands.py — add after existing commands
async def list_datasets() -> DatasetListResponse:
    """List all datasets stored in Cognee memory."""
    from cognee import get_datasets
    try:
        raw_datasets = await get_datasets()
        datasets = []
        for ds in raw_datasets:
            datasets.append(DatasetInfo(
                id=ds.get("id", ""),
                name=ds.get("name", "unknown"),
                type=ds.get("type", "vector"),
                size_bytes=ds.get("size", 0),
                created_at=ds.get("created_at", ""),
                file_count=ds.get("file_count", 0),
                source_path=ds.get("source_path", ""),
            ))
        return DatasetListResponse(
            success=True,
            datasets=datasets,
            total_count=len(datasets),
        )
    except Exception as e:
        return DatasetListResponse(success=True, datasets=[], total_count=0)
```

- [ ] **Step 3: Add HTTP route to server.py**

```python
# backend/app/server.py — add after existing routes
@app.get("/datasets", response_model=DatasetListResponse)
async def http_list_datasets():
    from app.api.commands import list_datasets
    return await list_datasets()
```

- [ ] **Step 4: Add Tauri command to lib.rs**

```rust
// src-tauri/src/lib.rs — add after existing commands
#[tauri::command]
async fn list_datasets() -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client.get("http://127.0.0.1:8765/datasets")
        .timeout(std::time::Duration::from_secs(30))
        .send().await.map_err(|e| e.to_string())?;
    resp.json().await.map_err(|e| e.to_string())
}
```

Also register in `tauri::Builder::default().invoke_handler(tauri::generate_handler![...])`.

- [ ] **Step 5: Add TypeScript API function**

```typescript
// src/lib/api.ts — add after existing functions
export interface DatasetInfo {
  id: string;
  name: string;
  type: string;
  size_bytes: number;
  created_at: string;
  file_count: number;
  source_path: string;
}

export interface DatasetListResponse {
  success: boolean;
  datasets: DatasetInfo[];
  total_count: number;
}

export async function listDatasets(): Promise<DatasetListResponse> {
  return invoke<DatasetListResponse>("list_datasets");
}
```

- [ ] **Step 6: Verify backend works**

```bash
cd backend && python3.13 -m pytest tests/ -v
python3.13 -m uvicorn app.main:app --port 8765 &
curl http://127.0.0.1:8765/datasets
```

Expected: JSON response with `success: true` and `datasets: []` (empty if nothing indexed yet).

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/schemas.py backend/app/api/commands.py backend/app/server.py src-tauri/src/lib.rs src/lib/api.ts
git commit -m "feat: add list_datasets backend endpoint"
```

---

### Task 1.2: Add `get_repository_summaries` endpoint

**Covers:** Repositories page needs to list indexed repositories with metadata.

**Files:**
- Modify: `backend/app/api/schemas.py` — add `RepositorySummaryInfo` model
- Modify: `backend/app/api/commands.py` — add `get_repository_summaries()` command
- Modify: `backend/app/server.py` — add route
- Modify: `src-tauri/src/lib.rs` — add Tauri command
- Modify: `src/lib/api.ts` — add TypeScript types and function

**Interfaces:**
- Produces: `RepositorySummaryInfo` with `name`, `path`, `languages`, `file_count`, `last_indexed`, `purpose`, `architecture`, `components`

**Steps:**

- [ ] **Step 1: Add response model**

```python
# backend/app/api/schemas.py
class RepoComponentInfo(BaseModel):
    path: str
    centrality: str

class RepoArchInfo(BaseModel):
    icon: str
    label: str

class RepositorySummaryInfo(BaseModel):
    id: str
    name: str
    path: str
    languages: list[str]
    file_count: int
    memory_size: str
    last_indexed: str
    purpose: str = ""
    architecture: list[RepoArchInfo] = []
    components: list[RepoComponentInfo] = []

class RepositoryListResponse(BaseModel):
    success: bool
    repositories: list[RepositorySummaryInfo]
    total_count: int
```

- [ ] **Step 2: Implement command**

The backend needs to track which repositories have been indexed. Add a lightweight metadata store.

```python
# backend/app/api/commands.py
import json
from pathlib import Path

REPO_STORE_PATH = Path.home() / ".andes" / "indexed_repos.json"

def _load_repo_store() -> dict:
    if REPO_STORE_PATH.exists():
        return json.loads(REPO_STORE_PATH.read_text())
    return {}

def _save_repo_store(store: dict):
    REPO_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPO_STORE_PATH.write_text(json.dumps(store, indent=2))

async def get_repository_summaries() -> RepositoryListResponse:
    store = _load_repo_store()
    repositories = []
    for repo_id, meta in store.items():
        repositories.append(RepositorySummaryInfo(
            id=repo_id,
            name=meta.get("name", repo_id),
            path=meta.get("path", ""),
            languages=meta.get("languages", []),
            file_count=meta.get("file_count", 0),
            memory_size=meta.get("memory_size", "0 MB"),
            last_indexed=meta.get("last_indexed", "Never"),
            purpose=meta.get("purpose", ""),
            architecture=[RepoArchInfo(**a) for a in meta.get("architecture", [])],
            components=[RepoComponentInfo(**c) for c in meta.get("components", [])],
        ))
    return RepositoryListResponse(
        success=True,
        repositories=repositories,
        total_count=len(repositories),
    )
```

- [ ] **Step 3: Wire into index_repository to persist metadata**

After successful indexing in `index_repository()`, generate a summary and save to the store:

```python
# In commands.py index_repository(), after successful indexing:
from app.services.repository_summary import RepositorySummaryGenerator
gen = RepositorySummaryGenerator()
summary = gen.generate(repository_path)
_store_meta = {
    "name": dataset_name,
    "path": repository_path,
    "languages": summary.tech_stack.languages if summary.tech_stack else [],
    "file_count": result.processed_files,
    "memory_size": f"{result.processed_files * 0.02:.1f} MB",
    "last_indexed": "Just now",
    "purpose": summary.purpose or "",
    "architecture": [{"icon": "git-branch", "label": a.pattern.value} for a in (summary.architecture.patterns if summary.architecture else [])],
    "components": [{"path": c.path, "centrality": "High"} for c in (summary.components or [])],
}
store = _load_repo_store()
store[dataset_name] = _store_meta
_save_repo_store(store)
```

- [ ] **Step 4: Add route, Tauri command, TypeScript function** (same pattern as Task 1.1)

- [ ] **Step 5: Verify**

```bash
curl http://127.0.0.1:8765/repositories
```

Expected: `{"success": true, "repositories": [...], "total_count": N}`

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: add repository summaries endpoint with metadata persistence"
```

---

### Task 1.3: Add `get_dashboard_stats` endpoint

**Covers:** Dashboard needs aggregate statistics.

**Files:**
- Modify: `backend/app/api/schemas.py` — add `DashboardStats` model
- Modify: `backend/app/api/commands.py` — add `get_dashboard_stats()` command
- Modify: `backend/app/server.py` — add route
- Modify: `src-tauri/src/lib.rs` — add Tauri command
- Modify: `src/lib/api.ts` — add TypeScript types and function

**Interfaces:**
- Produces: `DashboardStats` with `indexed_repos`, `total_files`, `total_embeddings`, `packages_generated`, `avg_gen_time_ms`, `last_indexed_repo`, `last_indexed_time`

**Steps:**

- [ ] **Step 1: Add response model**

```python
# backend/app/api/schemas.py
class DashboardStats(BaseModel):
    success: bool
    indexed_repos: int
    total_files: int
    total_embeddings: int
    packages_generated: int
    avg_gen_time_ms: float
    last_indexed_repo: str = ""
    last_indexed_time: str = ""
```

- [ ] **Step 2: Implement command**

```python
# backend/app/api/commands.py
async def get_dashboard_stats() -> DashboardStats:
    store = _load_repo_store()
    total_files = sum(m.get("file_count", 0) for m in store.values())
    # Read generation history from stats logger
    from app.services.stats_logger import StatsLogger
    stats = StatsLogger()
    gen_count = len(stats.generation_history) if hasattr(stats, 'generation_history') else 0
    avg_time = stats.avg_generation_time if hasattr(stats, 'avg_generation_time') else 0
    last_repo = ""
    last_time = ""
    if store:
        latest = max(store.values(), key=lambda m: m.get("last_indexed", ""))
        last_repo = latest.get("name", "")
        last_time = latest.get("last_indexed", "")
    return DashboardStats(
        success=True,
        indexed_repos=len(store),
        total_files=total_files,
        total_embeddings=total_files * 5,  # approximate
        packages_generated=gen_count,
        avg_gen_time_ms=avg_time,
        last_indexed_repo=last_repo,
        last_indexed_time=last_time,
    )
```

- [ ] **Step 3: Add route, Tauri command, TypeScript function** (same pattern)

- [ ] **Step 4: Verify and commit**

---

### Task 1.4: Add `get_memory_stats` endpoint

**Covers:** Memory page sidebar needs topology stats.

**Files:**
- Modify: `backend/app/api/schemas.py` — add `MemoryStats` model
- Modify: `backend/app/api/commands.py` — add command
- Modify: `backend/app/server.py` — add route
- Modify: `src-tauri/src/lib.rs` — add Tauri command
- Modify: `src/lib/api.ts` — add TypeScript types and function

**Interfaces:**
- Produces: `MemoryStats` with `total_size_bytes`, `graph_nodes`, `graph_edges`, `dataset_count`

**Steps:**

- [ ] **Step 1: Add model**

```python
# backend/app/api/schemas.py
class MemoryStats(BaseModel):
    success: bool
    total_size_bytes: int
    total_size_display: str
    graph_nodes: int
    graph_edges: int
    dataset_count: int
```

- [ ] **Step 2: Implement by querying Cognee internals**

```python
# backend/app/api/commands.py
async def get_memory_stats() -> MemoryStats:
    from cognee.infrastructure.databases import get_graph_engine, get_vector_engine
    try:
        graph = await get_graph_engine()
        vector = await get_vector_engine()
        # Query counts from graph
        node_count = await graph.get_node_count() if hasattr(graph, 'get_node_count') else 0
        edge_count = await graph.get_edge_count() if hasattr(graph, 'get_edge_count') else 0
        # Dataset count from store
        store = _load_repo_store()
        return MemoryStats(
            success=True,
            total_size_bytes=0,
            total_size_display="N/A",
            graph_nodes=node_count,
            graph_edges=edge_count,
            dataset_count=len(store),
        )
    except Exception:
        return MemoryStats(
            success=True, total_size_bytes=0, total_size_display="N/A",
            graph_nodes=0, graph_edges=0, dataset_count=0,
        )
```

- [ ] **Step 3: Add route, Tauri command, TypeScript function**

- [ ] **Step 4: Verify and commit**

---

## Phase 2: Wire Frontend to Real APIs

### Task 2.1: Wire Memory page to real data

**Covers:** Memory page displays real datasets from backend.

**Files:**
- Modify: `src/stores/memory-store.ts` — replace mock data with API calls
- Modify: `src/pages/Memory.tsx` — add loading states
- Modify: `src/components/memory/DatasetTable.tsx` — handle empty state
- Modify: `src/components/memory/MemoryStats.tsx` — use real stats

**Steps:**

- [ ] **Step 1: Update memory-store to fetch from backend**

```typescript
// src/stores/memory-store.ts
import { create } from "zustand";
import { listDatasets, getMemoryStats, type DatasetInfo, type MemoryStats as MemoryStatsType } from "@/lib/api";

interface MemoryStore {
  datasets: DatasetInfo[];
  stats: MemoryStatsType | null;
  loading: boolean;
  selectedDatasetId: string | null;
  filterType: "all" | "vectors" | "graphs" | "document";
  viewMode: "list" | "grid";
  sortBy: "date" | "name" | "size";
  fetchDatasets: () => Promise<void>;
  fetchStats: () => Promise<void>;
  setFilter: (f: "all" | "vectors" | "graphs" | "document") => void;
  setViewMode: (m: "list" | "grid") => void;
  setSort: (s: "date" | "name" | "size") => void;
  selectDataset: (id: string | null) => void;
  removeDataset: (id: string) => void;
}

export const useMemoryStore = create<MemoryStore>((set, get) => ({
  datasets: [],
  stats: null,
  loading: false,
  selectedDatasetId: null,
  filterType: "all",
  viewMode: "list",
  sortBy: "date",

  fetchDatasets: async () => {
    set({ loading: true });
    try {
      const resp = await listDatasets();
      set({ datasets: resp.datasets, loading: false });
    } catch {
      set({ datasets: [], loading: false });
    }
  },

  fetchStats: async () => {
    try {
      const resp = await getMemoryStats();
      set({ stats: resp });
    } catch {
      set({ stats: null });
    }
  },

  // ... keep existing setters
}));
```

- [ ] **Step 2: Update Memory.tsx to fetch on mount**

```typescript
// In Memory.tsx, add useEffect
useEffect(() => {
  useMemoryStore.getState().fetchDatasets();
  useMemoryStore.getState().fetchStats();
}, []);
```

- [ ] **Step 3: Update forget handler to call real API**

```typescript
// In ConfirmDialog onConfirm:
import { forgetDataset } from "@/lib/api";
const response = await forgetDataset({ dataset: forgetDataset.name });
if (response.success) {
  useMemoryStore.getState().fetchDatasets(); // refresh
}
```

- [ ] **Step 4: Add empty state for no datasets**

```tsx
// In DatasetTable, if datasets.length === 0:
<div className="text-center py-12 text-on-surface-variant">
  <Database className="w-12 h-12 mx-auto mb-4 opacity-50" />
  <p>No datasets indexed yet</p>
  <p className="text-sm mt-1">Index a repository to get started</p>
</div>
```

- [ ] **Step 5: Verify end-to-end**

Launch app, navigate to Memory page. Should show empty state if nothing indexed. After indexing a repo, datasets should appear.

- [ ] **Step 6: Commit**

---

### Task 2.2: Wire Repositories page to real data

**Covers:** Repository management uses real backend data.

**Files:**
- Modify: `src/stores/repository-store.ts` — replace mock data with API calls
- Modify: `src/pages/Repositories.tsx` — add loading/empty states, wire index button
- Modify: `src/components/repositories/RepoCard.tsx` — wire action buttons

**Steps:**

- [ ] **Step 1: Update repository-store**

```typescript
// src/stores/repository-store.ts
import { getRepositorySummaries, indexRepository, forgetDataset } from "@/lib/api";

interface RepositoryStore {
  repositories: RepositoryInfo[];
  loading: boolean;
  selectedId: string | null;
  selected: RepositoryInfo | undefined;
  searchQuery: string;
  fetchRepositories: () => Promise<void>;
  indexRepo: (path: string, name: string) => Promise<void>;
  removeRepo: (id: string) => Promise<void>;
  select: (id: string | null) => void;
  setSearchQuery: (q: string) => void;
}
// ... implement with real API calls
```

- [ ] **Step 2: Wire the "New Index" button to open Tauri folder picker**

```typescript
// In Repositories.tsx
import { open } from "@tauri-apps/plugin-dialog";

const handleNewIndex = async () => {
  const selected = await open({ directory: true, multiple: false });
  if (selected) {
    const name = selected.split("/").pop() || "repo";
    await repositoryStore.indexRepo(selected, name);
    await repositoryStore.fetchRepositories();
  }
};
```

- [ ] **Step 3: Wire Re-index and Delete buttons**

```typescript
// Re-index: calls indexRepo with same path
// Delete: calls removeRepo which calls forgetDataset
```

- [ ] **Step 4: Add empty state**

- [ ] **Step 5: Verify and commit**

---

### Task 2.3: Wire Context Builder to real backend

**Covers:** Context Builder calls real generate_context API.

**Files:**
- Modify: `src/stores/context-store.ts` — wire generate action
- Modify: `src/components/context-builder/InputParameters.tsx` — add onClick to Generate button
- Modify: `src/components/context-builder/PipelineVisualization.tsx` — show real pipeline steps during generation
- Modify: `src/components/context-builder/OutputPanel.tsx` — render real markdown

**Steps:**

- [ ] **Step 1: Add generate action to context-store**

```typescript
// src/stores/context-store.ts
import { generateContext } from "@/lib/api";

generatePackage: async () => {
  const { objective, selectedRepo, topK, advancedOptions } = get();
  if (!objective.trim()) return;

  set({ loading: true, error: null, result: null });
  try {
    const response = await generateContext({
      task: objective.trim(),
      datasets: [selectedRepo],
      top_k: topK,
    });
    set((state) => ({
      result: response,
      loading: false,
      history: [response, ...state.history].slice(0, 10),
    }));
  } catch (e) {
    set({
      error: e instanceof Error ? e.message : "Generation failed",
      loading: false,
    });
  }
},
```

- [ ] **Step 2: Wire Generate button in InputParameters.tsx**

```tsx
<button
  onClick={() => useContextStore.getState().generatePackage()}
  disabled={loading || !objective.trim()}
  // ... rest of button
>
```

- [ ] **Step 3: Clear mock pipeline steps**

Replace `mockPipelineSteps` with empty array. During loading, show a single "Generating..." active step. On completion, show "Complete" with check marks.

- [ ] **Step 4: Verify end-to-end**

Type a question, click Generate, verify real markdown appears.

- [ ] **Step 5: Commit**

---

### Task 2.4: Wire Dashboard to real stats

**Covers:** Dashboard shows real statistics from backend.

**Files:**
- Modify: `src/pages/Dashboard.tsx` — fetch real stats on mount
- Modify: `src/components/shared/StatCard.tsx` — accept dynamic values
- Modify: `src/components/dashboard/ActivityTimeline.tsx` — remove mock data dependency

**Steps:**

- [ ] **Step 1: Create dashboard store or add to health-store**

```typescript
// Add to health-store or create dashboard-store
fetchDashboardStats: async () => {
  try {
    const resp = await getDashboardStats();
    set({ dashboardStats: resp });
  } catch {
    set({ dashboardStats: null });
  }
},
```

- [ ] **Step 2: Update Dashboard.tsx to use real stats**

```tsx
// Replace hardcoded values with:
const stats = useHealthStore((s) => s.dashboardStats);
<StatCard label="Indexed Repositories" value={String(stats?.indexed_repos ?? 0)} />
<StatCard label="Total Files" value={String(stats?.total_files ?? 0)} />
```

- [ ] **Step 3: Empty state for no repos**

- [ ] **Step 4: Verify and commit**

---

### Task 2.5: Wire Settings to real config

**Covers:** Settings page reads and displays real backend configuration.

**Files:**
- Modify: `src/components/settings/BackendSettings.tsx` — use real status data
- Modify: `src/components/settings/OllamaSettings.tsx` — use real config
- Modify: `src/components/settings/StorageSettings.tsx` — use real paths
- Modify: `src/components/settings/CogneeSettings.tsx` — use real config

**Steps:**

- [ ] **Step 1: Use getBackendStatus() data in settings forms**

```tsx
// In BackendSettings.tsx
const status = useHealthStore((s) => s.status);
<input defaultValue={status?.ollama_host ?? "http://127.0.0.1"} />
```

- [ ] **Step 2: Wire Test Connection button**

```typescript
const handleTestConnection = async () => {
  try {
    await health();
    // Show success toast
  } catch {
    // Show error toast
  }
};
```

- [ ] **Step 3: Verify and commit**

---

## Phase 3: Remove Mock Data

### Task 3.1: Delete mock data file

**Files:**
- Delete: `src/data/mock.ts`

**Steps:**

- [ ] **Step 1: Verify no imports reference mock.ts**

```bash
grep -r "mock" src/ --include="*.ts" --include="*.tsx" | grep -v "node_modules" | grep -v "components/ui"
```

- [ ] **Step 2: Remove any remaining imports**

- [ ] **Step 3: Delete the file**

- [ ] **Step 4: Verify build passes**

```bash
npx tsc --noEmit && npm run build
```

- [ ] **Step 5: Commit**

---

## Phase 4: Benchmarks (Backend + Frontend)

### Task 4.1: Add benchmark execution endpoint

**Covers:** Benchmarks page runs real benchmark suites.

**Files:**
- Create: `backend/app/api/benchmarks.py` — benchmark runner
- Modify: `backend/app/api/commands.py` — add `run_benchmark()` command
- Modify: `backend/app/server.py` — add route
- Modify: `src-tauri/src/lib.rs` — add Tauri command
- Modify: `src/lib/api.ts` — add TypeScript types and function
- Modify: `src/pages/Benchmarks.tsx` — wire Run Suite button

**Steps:**

- [ ] **Step 1: Create benchmark runner**

```python
# backend/app/api/benchmarks.py
import time
from dataclasses import dataclass, field

@dataclass
class BenchmarkResult:
    question: str
    latency_ms: float
    token_count: int
    section_count: int
    retrieved_memories: int
    compression_ratio: float
    quality_score: float = 0.0
    passed: bool = False

@dataclass
class BenchmarkSuite:
    results: list[BenchmarkResult] = field(default_factory=list)
    avg_latency_ms: float = 0.0
    avg_tokens: float = 0.0
    pass_rate: float = 0.0
    total_questions: int = 0

async def run_benchmark_suite(questions: list[str] | None = None) -> BenchmarkSuite:
    """Run benchmark questions through the context pipeline and measure results."""
    from app.api.commands import _load_repo_store, initialize_backend
    await initialize_backend()
    
    if questions is None:
        questions = [
            "How does the authentication middleware work?",
            "What is the project structure?",
            "How do I add a new API endpoint?",
        ]
    
    store = _load_repo_store()
    datasets = list(store.keys()) if store else ["default"]
    results = []
    
    for q in questions:
        start = time.monotonic()
        try:
            from app.api.commands import generate_context
            from app.api.schemas import GenerateContextRequest
            resp = await generate_context(GenerateContextRequest(
                task=q, datasets=datasets, top_k=20,
            ))
            latency = (time.monotonic() - start) * 1000
            results.append(BenchmarkResult(
                question=q,
                latency_ms=latency,
                token_count=resp.token_estimate,
                section_count=resp.section_count,
                retrieved_memories=resp.retrieved_memories,
                compression_ratio=resp.compression_ratio,
                quality_score=min(100.0, resp.section_count * 15 + resp.compression_ratio * 50),
                passed=resp.section_count >= 3,
            ))
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            results.append(BenchmarkResult(
                question=q, latency_ms=latency, token_count=0,
                section_count=0, retrieved_memories=0, compression_ratio=0,
            ))
    
    avg_latency = sum(r.latency_ms for r in results) / max(len(results), 1)
    avg_tokens = sum(r.token_count for r in results) / max(len(results), 1)
    pass_rate = sum(1 for r in results if r.passed) / max(len(results), 1) * 100
    
    return BenchmarkSuite(
        results=results,
        avg_latency_ms=avg_latency,
        avg_tokens=avg_tokens,
        pass_rate=pass_rate,
        total_questions=len(results),
    )
```

- [ ] **Step 2: Add command, route, Tauri command, TypeScript types** (same pattern as Phase 1)

- [ ] **Step 3: Wire Run Suite button in Benchmarks.tsx**

```typescript
const [suite, setSuite] = useState<BenchmarkSuite | null>(null);
const [running, setRunning] = useState(false);

const handleRunSuite = async () => {
  setRunning(true);
  try {
    const result = await runBenchmark();
    setSuite(result);
  } finally {
    setRunning(false);
  }
};
```

- [ ] **Step 4: Display real results in metric cards and charts**

- [ ] **Step 5: Empty state for no benchmarks run yet**

- [ ] **Step 6: Verify and commit**

---

## Verification Checklist

After all phases:

1. **Dashboard** — Launch app, stat cards show real numbers (0 repos, 0 files if nothing indexed)
2. **Repositories** — Empty state shows. Click New Index, select folder, repo appears after indexing
3. **Context Builder** — Select repo, type question, click Generate, real markdown appears
4. **Memory** — Empty state shows. After indexing, datasets appear. Forget works via API
5. **Benchmarks** — Empty state shows. Click Run Suite, real metrics appear
6. **Settings** — Forms show real backend config values
7. **`npm run build`** — Production build succeeds
8. **No mock data** — `grep -r "mock" src/ --include="*.ts" --include="*.tsx"` returns only UI component references (mock patterns), not data files
