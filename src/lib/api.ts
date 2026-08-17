/**
 * Tauri IPC wrapper for RE:Track (RefinedEngine Track) backend commands.
 *
 * All backend communication goes through this module.
 * Handles JSON serialization/deserialization and error wrapping.
 */

import { invoke } from "@tauri-apps/api/core";

import type { Repository, ScanResult } from "@/types/repository";

// --- Types matching backend schemas ---

export interface HealthResponse {
  status: "ok" | "degraded";
  ollama_reachable: boolean;
  cognee_initialized: boolean;
  version: string;
  ram_total_gb?: number;
  ram_used_gb?: number;
  cpu_percent?: number;
  gpu_name?: string | null;
  vram_total_gb?: number;
  vram_used_gb?: number;
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
  force_reindex?: boolean;
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

export interface AgentContextRequest {
  task_prompt: string;
  repository_path: string;
  dataset_name?: string;
  max_tokens?: number;
  include_structural_graph?: boolean;
}

export interface AgentContextResponse {
  success: boolean;
  context_markdown: string;
  task_summary: string;
  intent_category: string;
  extracted_symbols: string[];
  callers: string[];
  callees: string[];
  related_files: string[];
  quantization_warning?: string | null;
  estimated_tokens: number;
  generation_time_ms: number;
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

export interface BenchmarkResultItem {
  question: string;
  latency_ms: number;
  token_count: number;
  section_count: number;
  retrieved_memories: number;
  compression_ratio: number;
  quality_score: number;
  passed: boolean;
}

export interface BenchmarkSuiteResponse {
  success: boolean;
  results: BenchmarkResultItem[];
  avg_latency_ms: number;
  avg_tokens: number;
  pass_rate: number;
  total_questions: number;
}

// --- Context Package types ---

export interface SavedContextPackage {
  id: string;
  name: string;
  task: string;
  objective: string;
  repository_id: string;
  repository_name: string;
  repository_branch: string;
  repository_commit: string;
  indexing_version: string;
  markdown: string;
  section_count: number;
  token_estimate: number;
  retrieved_memories: number;
  deduplicated_memories: number;
  compression_ratio: number;
  total_time_ms: number;
  created_at: string;
  updated_at: string;
  tags: string[];
}

export interface ContextPackageSaveRequest {
  name: string;
  task?: string;
  objective?: string;
  repository_id?: string;
  repository_name?: string;
  repository_branch?: string;
  repository_commit?: string;
  indexing_version?: string;
  markdown?: string;
  section_count?: number;
  token_estimate?: number;
  retrieved_memories?: number;
  deduplicated_memories?: number;
  compression_ratio?: number;
  total_time_ms?: number;
  tags?: string[];
}

export interface ContextPackageListResponse {
  success: boolean;
  packages: SavedContextPackage[];
  total_count: number;
}

export interface ContextPackageAppendRequest {
  additional_task: string;
  additional_markdown?: string;
  additional_objective?: string;
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

export interface UpdateProviderRequest {
  provider: "ollama" | "lmstudio" | "openai_compatible";
  base_url: string;
  model: string;
  api_key?: string;
}

export interface UpdateProviderResponse {
  success: boolean;
  provider: string;
  base_url: string;
  model: string;
  reachable: boolean;
  loaded_models: string[];
}

/**
 * Hot-reload the active LLM inference provider without restarting the backend.
 */
export async function updateProvider(
  request: UpdateProviderRequest
): Promise<UpdateProviderResponse> {
  return invoke<UpdateProviderResponse>("update_provider", { request });
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
  * Generate an optimized context package for external AI coding agents via middleware.
  */
export async function getAgentContext(
  request: AgentContextRequest
): Promise<AgentContextResponse> {
  return invoke<AgentContextResponse>("get_agent_context", { request });
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

/**
 * Run a benchmark suite.
 */
export async function runBenchmark(): Promise<BenchmarkSuiteResponse> {
  return invoke<BenchmarkSuiteResponse>("run_benchmark");
}

// --- Repository management ---

/**
 * List all repositories.
 */
export async function listRepositories(): Promise<{ success: boolean; repositories: Repository[]; total_count: number }> {
  return invoke("list_repositories");
}

/**
 * Create a new repository.
 */
export async function createRepository(req: {
  source_type: string;
  source_url?: string;
  local_path?: string;
  name?: string;
}): Promise<Repository> {
  return invoke("create_repository", { request: req });
}

/**
 * Scan a repository for languages and frameworks.
 */
export async function scanRepository(repoId: string): Promise<ScanResult> {
  return invoke("scan_repository", { repoId });
}

/**
 * Delete a repository.
 */
export async function deleteRepository(repoId: string): Promise<{ success: boolean }> {
  return invoke("delete_repository", { repoId });
}

// --- Indexing Progress ---

export interface IndexingProgress {
  status: string;
  stage: string;
  processed_files: number;
  total_files: number;
  elapsed_ms: number;
  languages: string[];
  frameworks: string[];
  error: string | null;
  file_count: number;
  size_bytes: number;
}

/**
 * Get indexing progress for a repository.
 */
export async function getRepositoryProgress(repoId: string): Promise<IndexingProgress> {
  return invoke<IndexingProgress>("get_repository_progress", { repoId });
}

// --- Context Package management ---

/**
 * List all saved context packages.
 */
export async function listContextPackages(): Promise<ContextPackageListResponse> {
  return invoke<ContextPackageListResponse>("list_context_packages");
}

/**
 * Save a context package.
 */
export async function saveContextPackage(
  req: ContextPackageSaveRequest
): Promise<SavedContextPackage> {
  return invoke<SavedContextPackage>("save_context_package", { request: req });
}

/**
 * Get a single context package by ID.
 */
export async function getContextPackage(
  packageId: string
): Promise<SavedContextPackage> {
  return invoke<SavedContextPackage>("get_context_package", { packageId });
}

/**
 * Delete a context package.
 */
export async function deleteContextPackage(
  packageId: string
): Promise<{ success: boolean }> {
  return invoke("delete_context_package", { packageId });
}

/**
 * Append content to an existing context package.
 */
export async function appendContextPackage(
  packageId: string,
  req: ContextPackageAppendRequest
): Promise<SavedContextPackage> {
  return invoke<SavedContextPackage>("append_context_package", { packageId, request: req });
}

// --- UI domain types (previously in src/types/index.ts) ---

export interface BenchmarkMetric {
  label: string;
  value: string;
  unit?: string;
  trend?: string;
  trendDirection?: "up" | "down" | "stable";
}

export interface AdvancedOptions {
  dedup: boolean;
  resolveRefs: boolean;
  aggressiveCompress: boolean;
}
