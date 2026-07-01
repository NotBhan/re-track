/**
 * Tauri IPC wrapper for AndesContext backend commands.
 *
 * All backend communication goes through this module.
 * Handles JSON serialization/deserialization and error wrapping.
 */

import { invoke } from "@tauri-apps/api/core";

// --- Types matching backend schemas ---

export interface HealthResponse {
  status: "ok" | "degraded";
  ollama_reachable: boolean;
  cognee_initialized: boolean;
  version: string;
}

export interface BackendStatusResponse {
  status: "ok" | "degraded";
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

export interface ErrorResponse {
  error: string;
  message: string;
  success: false;
  details?: string;
}

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

export interface RepoArchInfo {
  icon: string;
  label: string;
}

export interface RepoComponentInfo {
  path: string;
  centrality: string;
}

export interface RepositorySummaryInfo {
  id: string;
  name: string;
  path: string;
  languages: string[];
  file_count: number;
  memory_size: string;
  last_indexed: string;
  purpose?: string;
  architecture?: RepoArchInfo[];
  components?: RepoComponentInfo[];
}

export interface RepositoryListResponse {
  success: boolean;
  repositories: RepositorySummaryInfo[];
  total_count: number;
}

export interface DashboardStats {
  success: boolean;
  indexed_repos: number;
  total_files: number;
  total_embeddings: number;
  packages_generated: number;
  avg_gen_time_ms: number;
  last_indexed_repo: string;
  last_indexed_time: string;
}

export interface MemoryStatsResponse {
  success: boolean;
  total_size_display: string;
  graph_nodes: number;
  graph_edges: number;
  dataset_count: number;
}

// --- API functions ---

/**
 * Check system health.
 */
export async function health(): Promise<HealthResponse> {
  return invoke<HealthResponse>("health");
}

/**
 * Get detailed backend status.
 */
export async function getBackendStatus(): Promise<BackendStatusResponse> {
  return invoke<BackendStatusResponse>("get_status");
}

/**
 * Index a repository into Cognee memory.
 */
export async function indexRepository(
  request: IndexRepositoryRequest
): Promise<IndexRepositoryResponse> {
  return invoke<IndexRepositoryResponse>("index_repository", { request });
}

/**
 * Generate a Context Package for a developer task.
 */
export async function generateContext(
  request: GenerateContextRequest
): Promise<ContextResponse> {
  return invoke<ContextResponse>("generate_context", { request });
}

/**
 * Forget (delete) a dataset from Cognee memory.
 */
export async function forgetDataset(
  request: ForgetDatasetRequest
): Promise<ForgetDatasetResponse> {
  return invoke<ForgetDatasetResponse>("forget_dataset", { request });
}

/**
 * List all datasets stored in Cognee memory.
 */
export async function listDatasets(): Promise<DatasetListResponse> {
  return invoke<DatasetListResponse>("list_datasets");
}

/**
 * List all indexed repositories with metadata.
 */
export async function getRepositorySummaries(): Promise<RepositoryListResponse> {
  return invoke<RepositoryListResponse>("get_repository_summaries");
}

/**
 * Get aggregate dashboard statistics.
 */
export async function getDashboardStats(): Promise<DashboardStats> {
  return invoke<DashboardStats>("get_dashboard_stats");
}

/**
 * Get memory topology statistics.
 */
export async function getMemoryStats(): Promise<MemoryStatsResponse> {
  return invoke<MemoryStatsResponse>("get_memory_stats");
}
