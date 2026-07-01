// --- Backend API Types ---

export type HealthStatus = "ok" | "degraded";

export interface HealthResponse {
  status: HealthStatus;
  ollama_reachable: boolean;
  cognee_initialized: boolean;
  version: string;
}

export interface BackendStatusResponse {
  status: HealthStatus;
  ollama_reachable: boolean;
  ollama_host: string;
  ollama_port: number;
  llm_model: string;
  embedding_model: string;
  vector_db: string;
  graph_db: string;
  relational_db: string;
  data_root: string;
  system_root: string;
  cognee_initialized: boolean;
}

export interface IndexRepositoryRequest {
  repository_path: string;
  dataset_name: string;
  batch_size?: number;
}

export interface IndexRepositoryResponse {
  success: boolean;
  repository_path: string;
  dataset_name: string;
  total_files: number;
  processed_files: number;
  failed_files: number;
  total_batches: number;
  failed_paths: string[];
  summary: string;
}

export interface GenerateContextRequest {
  task: string;
  datasets: string[];
  top_k?: number;
}

export interface ContextResponse {
  success: boolean;
  task: string;
  objective: string;
  markdown: string;
  section_count: number;
  source_count: number;
  token_estimate: number;
  dataset: string;
  retrieved_memories: number;
  deduplicated_memories: number;
  compressed_memories: number;
  compression_ratio: number;
  retrieval_time_ms: number;
  total_time_ms: number;
  reference_count: number;
  section_headings: string[];
}

export interface ForgetDatasetRequest {
  dataset?: string;
  dataset_id?: string;
  data_id?: string;
}

export interface ForgetDatasetResponse {
  success: boolean;
  message: string;
}

// --- UI Domain Types ---

export interface Repository {
  id: string;
  name: string;
  path: string;
  languages: string[];
  fileCount: number;
  memorySize: string;
  lastIndexed: string;
  status: "indexed" | "not_indexed" | "indexing";
  purpose?: string;
  architecture?: { icon: string; label: string }[];
  keyComponents?: { path: string; centrality: string }[];
}

export interface PipelineStep {
  id: string;
  label: string;
  description: string;
  status: "completed" | "active" | "pending";
  progress?: number;
}

export interface Activity {
  id: string;
  type: "index" | "generate" | "sync";
  message: string;
  repoName?: string;
  detail: string;
  timestamp: string;
}

export interface BenchmarkMetric {
  label: string;
  value: string;
  unit?: string;
  trend?: string;
  trendDirection?: "up" | "down" | "stable";
}

export interface Dataset {
  id: string;
  name: string;
  sourceRepo: string;
  type: "Vector DB" | "Graph" | "Document";
  size: string;
  creationDate: string;
}

export interface SettingTab {
  id: string;
  label: string;
  category: "Configuration" | "Application";
}

export interface MemoryTopology {
  totalStoredData: string;
  graphNodes: string;
  graphEdges: string;
}

export interface AdvancedOptions {
  dedup: boolean;
  resolveRefs: boolean;
  aggressiveCompress: boolean;
}
