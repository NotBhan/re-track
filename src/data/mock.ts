import type {
  Repository,
  PipelineStep,
  Activity,
  BenchmarkMetric,
  Dataset,
  SettingTab,
  MemoryTopology,
} from "@/types";

// --- Repositories ---

export const mockRepositories: Repository[] = [
  {
    id: "repo-1",
    name: "andes-core-engine",
    path: "~/dev/projects/andes-core-engine",
    languages: ["TS", "RS"],
    fileCount: 1245,
    memorySize: "4.2 GB",
    lastIndexed: "2 hrs ago",
    status: "indexed",
    purpose:
      "Core processing engine for local AI memory graph construction. Handles file parsing, embedding generation, and initial vector storage.",
    architecture: [
      { icon: "git-branch", label: "Event-driven microkernel" },
      { icon: "database", label: "Local SQLite + LanceDB" },
    ],
    keyComponents: [
      { path: "src/parser/ast.rs", centrality: "High Centrality" },
      { path: "src/embedding/worker.ts", centrality: "Hot Path" },
    ],
  },
  {
    id: "repo-2",
    name: "auth-service-go",
    path: "~/dev/services/auth-service",
    languages: ["GO"],
    fileCount: 84,
    memorySize: "156 MB",
    lastIndexed: "1 day ago",
    status: "indexed",
  },
  {
    id: "repo-3",
    name: "andes-web-client",
    path: "~/dev/projects/andes-web-client",
    languages: ["TS", "JS"],
    fileCount: 312,
    memorySize: "890 MB",
    lastIndexed: "Never",
    status: "not_indexed",
  },
  {
    id: "repo-4",
    name: "infra-deployments",
    path: "~/dev/infra/deployments",
    languages: ["YAML", "TF"],
    fileCount: 67,
    memorySize: "34 MB",
    lastIndexed: "3 days ago",
    status: "indexed",
  },
];

// --- Pipeline Steps ---

export const mockPipelineSteps: PipelineStep[] = [
  {
    id: "recall",
    label: "Semantic Recall",
    description: "Queried vector DB. Found 42 potential snippets.",
    status: "completed",
  },
  {
    id: "dedup",
    label: "Deduplication & Ranking",
    description: "Removed 12 overlaps. Ranked top 25 by relevance.",
    status: "completed",
  },
  {
    id: "refs",
    label: "Reference Resolution",
    description: "Tracing imports and type definitions...",
    status: "active",
    progress: 66,
  },
  {
    id: "compress",
    label: "Compression & Structuring",
    description: "Pending...",
    status: "pending",
  },
];

// --- Activity Timeline ---

export const mockActivities: Activity[] = [
  {
    id: "act-1",
    type: "index",
    message: "Indexed",
    repoName: "andes-ui",
    detail: "14,230 nodes added",
    timestamp: "2 mins ago",
  },
  {
    id: "act-2",
    type: "generate",
    message: "Generated Package for 'Refactor Auth'",
    detail: "45kb package",
    timestamp: "15 mins ago",
  },
  {
    id: "act-3",
    type: "sync",
    message: "Background Sync Completed",
    detail: "No changes detected",
    timestamp: "1 hour ago",
  },
  {
    id: "act-4",
    type: "index",
    message: "Indexed",
    repoName: "andes-core",
    detail: "89,102 nodes added",
    timestamp: "3 hours ago",
  },
];

// --- Benchmark Metrics ---

export const mockBenchmarkMetrics: BenchmarkMetric[] = [
  {
    label: "Avg Quality Score",
    value: "94.2",
    trend: "+2.4",
    trendDirection: "up",
  },
  {
    label: "Gen Latency (p95)",
    value: "245",
    unit: "ms",
    trend: "-12ms",
    trendDirection: "down",
  },
  {
    label: "Hallucination Rate",
    value: "0.8",
    unit: "%",
    trend: "stable",
    trendDirection: "stable",
  },
  {
    label: "Context Coverage",
    value: "88.5",
    unit: "%",
    trend: "+5.1%",
    trendDirection: "up",
  },
];

// --- Datasets ---

export const mockDatasets: Dataset[] = [
  {
    id: "ds-1",
    name: "core-auth-services",
    sourceRepo: "github.com/org/core-auth",
    type: "Vector DB",
    size: "245 MB",
    creationDate: "2 hours ago",
  },
  {
    id: "ds-2",
    name: "andes-core-engine",
    sourceRepo: "github.com/andes/core-engine",
    type: "Vector DB",
    size: "4.2 GB",
    creationDate: "2 days ago",
  },
  {
    id: "ds-3",
    name: "web-client",
    sourceRepo: "github.com/andes/web-client",
    type: "Graph",
    size: "128 MB",
    creationDate: "5 days ago",
  },
];

// --- Memory Topology ---

export const mockMemoryTopology: MemoryTopology = {
  totalStoredData: "1.2 TB",
  graphNodes: "14.2M",
  graphEdges: "38.5M",
};

// --- Settings Tabs ---

export const mockSettingTabs: SettingTab[] = [
  { id: "backend", label: "Backend", category: "Configuration" },
  { id: "cognee", label: "Cognee", category: "Configuration" },
  { id: "ollama", label: "Ollama", category: "Configuration" },
  { id: "storage", label: "Storage", category: "Configuration" },
  { id: "theme", label: "Theme", category: "Application" },
  { id: "about", label: "About", category: "Application" },
];
