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
  ram_percent?: number;
  high_memory_pressure?: boolean;
  cpu_percent?: number;
  gpu_presence?: "AMD" | "NVIDIA" | "None" | string;
  gpu_name?: string | null;
  vram_total_gb?: number;
  vram_used_gb?: number;
  execution_device?: "CPU" | "GPU" | "UNKNOWN" | string;

  // Authoritative Provider & Model runtime state
  provider?: "ollama" | "lmstudio" | "openai_compatible" | string;
  provider_identity?: "ollama" | "lmstudio" | "openai_compatible" | string;
  provider_configured?: boolean;
  provider_reachable?: boolean;
  provider_health_state?: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  provider_base_url?: string | null;
  configured_model?: string | null;
  active_model?: string | null;
  active_model_state?: "active" | "available" | "configured_only" | "unknown" | "none" | string;
  discovered_models?: string[];

  // Authoritative Engine & Cognee runtime state
  engine_state?: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  engine_reason?: string | null;
  cognee_state?: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  cognee_reason?: string | null;

  // Operational metrics
  health_state?: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  storage_canonical_exists?: boolean;
  storage_canonical_writable?: boolean;
  legacy_storage_detected?: boolean;
  repository_count?: number;
  context_package_count?: number;
  cache_files_count?: number;
  cache_total_bytes?: number;
  concurrency_queue_depth?: number;
  concurrency_queue_capacity?: number;
  concurrency_available_slots?: number;
  mcp_server_ready?: boolean;
  recent_errors_count?: number;
}

export interface DetailedHealthResponse extends HealthResponse {
  diagnostics_log_entries?: Array<Record<string, unknown>>;
  storage_paths?: Record<string, string>;
}

export interface BackendStatusResponse {
  status: "ok" | "degraded";
  ollama_reachable: boolean;
  ollama_host: string;
  ollama_port: number;
  llm_provider?: string;
  llm_endpoint?: string;
  llm_model: string;
  embedding_model: string;
  vector_db: string;
  graph_db: string;
  relational_db: string;
  data_root: string;
  system_root: string;
  cognee_initialized: boolean;
  gpu_presence?: string;
  execution_device?: string;

  // Authoritative Provider & Model runtime state
  provider_identity?: string;
  provider_configured?: boolean;
  provider_reachable?: boolean;
  provider_health_state?: string;
  configured_model?: string | null;
  active_model?: string | null;
  active_model_state?: string;
  discovered_models?: string[];

  // Authoritative Engine & Cognee runtime state
  engine_state?: string;
  engine_reason?: string | null;
  cognee_state?: string;
  cognee_reason?: string | null;
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
  model_invoked?: boolean;
  provider_identity?: string | null;
  model_name?: string | null;
  inference_status?: string;
  inference_time_ms?: number;
  evidence_state?: string;
  evidence_score?: number;
  evidence_confidence?: number;
  evidence_files?: string[];
  evidence_symbols?: string[];
  evidence_relationships?: string[];
  observed_evidence?: string[];
  missing_evidence?: string[];
  abstained?: boolean;
  abstention_reason?: string | null;
  model_claims_allowed?: boolean;
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
  retrieval_time_ms?: number;
  ranking_time_ms?: number;
  synthesis_time_ms?: number;
  total_time_ms?: number;
  model_invoked?: boolean;
  provider_identity?: string | null;
  model_name?: string | null;
  inference_status?: string;
  fallback_used?: boolean;
  fallback_reason?: string | null;
  inference_time_ms?: number;
  evidence_state?: string;
  evidence_score?: number;
  evidence_confidence?: number;
  evidence_files?: string[];
  evidence_symbols?: string[];
  evidence_relationships?: string[];
  observed_evidence?: string[];
  missing_evidence?: string[];
  abstained?: boolean;
  abstention_reason?: string | null;
  model_claims_allowed?: boolean;
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
  storage_state?: "healthy" | "degraded" | "unavailable" | string;
  provenance?: Record<string, unknown> | null;
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
  name: string;
  type: string;
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
  call_graph_status?: "not_analyzed" | "analyzing" | "analyzed" | "zero_edges" | "failed";
  call_graph_error?: string | null;
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
  dataset_count: number;
  knowledge_graph_status?: "not_extracted" | "extracting" | "extracted" | "failed";
  graph_nodes?: number | null;
  graph_edges?: number | null;
  storage_subsystems?: {
    lancedb?: "healthy" | "degraded" | "unavailable" | string;
    kuzu?: "healthy" | "degraded" | "unavailable" | string;
    cognee?: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  };
}

export interface MemoryGraphNode {
  id: string;
  label: string;
  kind: string;
  type?: string | null;
  properties?: Record<string, string>;
  provenance?: Record<string, unknown> | null;
}

export interface MemoryGraphEdge {
  source: string;
  target: string;
  kind: string;
  relationship_type?: string | null;
  properties?: Record<string, string>;
  provenance?: Record<string, unknown> | null;
}

export interface MemoryGraphResponse {
  success: boolean;
  status: "extracted" | "not_extracted" | "extracting" | "failed";
  storage_state?: "healthy" | "degraded" | "unavailable" | string;
  nodes: MemoryGraphNode[];
  edges: MemoryGraphEdge[];
  total_nodes: number;
  total_edges: number;
  dataset_name?: string | null;
  message: string;
}

export interface VectorDatasetInfo {
  id: string;
  name: string;
  file_count: number;
  size_bytes: number;
  created_at?: string | null;
  vector_status: "ready" | "indexing" | "empty" | string;
  chunk_count: number;
  provenance?: Record<string, unknown> | null;
}

export interface MemoryVectorsResponse {
  success: boolean;
  storage_state?: "healthy" | "degraded" | "unavailable" | string;
  vector_db_provider: string;
  embedding_model: string;
  embedding_dimensions: number;
  total_datasets: number;
  total_files: number;
  total_vectors?: number;
  tables?: Array<{ table_name: string; row_count: number }>;
  datasets: VectorDatasetInfo[];
  message?: string;
}

export interface MemoryDataItem {
  id: string;
  name: string;
  mime_type: string;
  data_size: number;
  created_at?: string | null;
  extension: string;
  content_hash: string;
  pipeline_status?: Record<string, unknown>;
  provenance?: Record<string, unknown> | null;
}

export interface DatasetDataItemsResponse {
  success: boolean;
  dataset_id: string;
  dataset_name: string;
  items: MemoryDataItem[];
  total_count: number;
}

export interface CognifyResponse {
  success: boolean;
  dataset_name?: string | null;
  total_vectors: number;
  total_nodes: number;
  total_edges: number;
  message: string;
}

export interface BenchmarkResultItem {
  question: string;
  baseline_tokens?: number;
  context_tokens?: number;
  token_count?: number;
  compression_ratio: number;
  token_savings_percent?: number;
  retrieval_time_ms?: number;
  total_time_ms?: number;
  latency_ms?: number;
  section_count: number;
  retrieved_memories: number;
  accuracy_status?: string;
  passed: boolean;
}

export interface BenchmarkSuiteResponse {
  success: boolean;
  results: BenchmarkResultItem[];
  avg_retrieval_latency_ms?: number;
  avg_total_latency_ms?: number;
  avg_latency_ms?: number;
  avg_token_savings_percent?: number;
  avg_compression_ratio?: number;
  avg_tokens?: number;
  accuracy_summary?: string;
  total_questions: number;
  run_metadata?: Record<string, unknown>;
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

export interface DiscoveredModel {
  model_id: string;
  name: string;
  quantization: string;
  is_phi4_mini: boolean;
  is_q6_or_higher: boolean;
  warning?: string | null;
}

export interface ProviderDiscoveryRequest {
  provider: "ollama" | "lmstudio" | "openai_compatible" | string;
  base_url: string;
  api_key?: string;
}

export interface ProviderDiscoveryResponse {
  success: boolean;
  provider: string;
  base_url: string;
  is_reachable: boolean;
  status: "available" | "reachable_but_empty" | "unreachable" | "discovery_failed" | "not_configured" | string;
  models: DiscoveredModel[];
  message: string;
  error_details?: string | null;
}

export interface ProviderStatusResponse {
  success: boolean;
  provider: string;
  base_url: string;
  active_model?: string | null;
  is_reachable: boolean;
  health_state: "healthy" | "degraded" | "unavailable" | "not_configured" | string;
  discovery_status: string;
  loaded_models: DiscoveredModel[];
  quantization_warning?: string | null;
  api_key_configured: boolean;
  api_key_masked: string;
}

export interface UpdateProviderRequest {
  provider: "ollama" | "lmstudio" | "openai_compatible" | string;
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
  health_state?: string;
  loaded_models: string[];
  quantization_warning?: string | null;
  api_key_configured?: boolean;
  api_key_masked?: string;
}

/**
 * Get authoritative active inference provider status.
 */
export async function getProviderStatus(): Promise<ProviderStatusResponse> {
  return invoke<ProviderStatusResponse>("get_provider_status");
}

/**
 * Non-mutating model discovery probe for candidate or active provider endpoints.
 */
export async function discoverProvider(
  request: ProviderDiscoveryRequest
): Promise<ProviderDiscoveryResponse> {
  return invoke<ProviderDiscoveryResponse>("discover_provider", { request });
}

/**
 * Hot-reload and persist the active LLM inference provider.
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
 * Get authoritative Cognee Knowledge Graph nodes and edges.
 */
export async function getMemoryGraph(dataset?: string): Promise<MemoryGraphResponse> {
  return invoke<MemoryGraphResponse>("get_memory_graph", { dataset });
}

/**
 * Get authoritative Vector Space and embedding index statistics.
 */
export async function getMemoryVectors(): Promise<MemoryVectorsResponse> {
  return invoke<MemoryVectorsResponse>("get_memory_vectors");
}

/**
 * Get stored/ingested files and documents for a dataset.
 */
export async function getDatasetItems(datasetId: string): Promise<DatasetDataItemsResponse> {
  return invoke<DatasetDataItemsResponse>("get_dataset_items", { datasetId });
}

/**
 * Extract memory vectors in LanceDB and build knowledge graph in Kùzu.
 */
export async function cognifyDataset(
  request: { dataset_name?: string } = {}
): Promise<CognifyResponse> {
  return invoke<CognifyResponse>("cognify_dataset", { request });
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

export interface SuggestedPrompt {
  label: string;
  prompt: string;
}

export interface SuggestedPromptsResponse {
  success: boolean;
  prompts: SuggestedPrompt[];
  source: "ai" | "heuristic";
}

/**
 * Get AI or AST-derived prompt recommendations for a repository.
 */
export async function getSuggestedPrompts(
  repoId: string
): Promise<SuggestedPromptsResponse> {
  return invoke<SuggestedPromptsResponse>("get_suggested_prompts", { repoId });
}

export interface AppSettingsResponse {
  success: boolean;
  vector_db: string;
  graph_db: string;
  relational_db: string;
  enable_kg_extraction: boolean;
  auto_link_entities: boolean;
  caching: boolean;
  data_root: string;
  system_root: string;
  llm_provider: string;
  llm_endpoint?: string;
  llm_host: string;
  llm_port: number;
  llm_model: string;
  embedding_model: string;
  api_key_configured?: boolean;
  api_key_masked?: string;
}


export interface CogneeSettingsRequest {
  vector_db?: string;
  graph_db?: string;
  enable_kg_extraction?: boolean;
  auto_link_entities?: boolean;
  caching?: boolean;
}

/**
 * Get current application and Cognee configuration.
 */
export async function getAppSettings(): Promise<AppSettingsResponse> {
  return invoke<AppSettingsResponse>("get_settings");
}

/**
 * Update and persist Cognee / storage settings to backend and disk.
 */
export async function updateCogneeSettings(
  req: CogneeSettingsRequest
): Promise<AppSettingsResponse> {
  return invoke<AppSettingsResponse>("update_cognee_settings", { request: req });
}

/**
 * Get detailed operational health, storage paths, and recent diagnostic logs.
 */
export async function getDetailedHealth(): Promise<DetailedHealthResponse> {
  return invoke<DetailedHealthResponse>("detailed_health");
}

/**
 * Generate and retrieve sanitized operational diagnostics.
 */
export async function getDiagnostics(): Promise<Record<string, unknown>> {
  return invoke<Record<string, unknown>>("get_diagnostics");
}

/**
 * Export sanitized operational diagnostics bundle to persistent JSON file.
 */
export async function exportDiagnostics(): Promise<{ status: string; export_path: string }> {
  return invoke<{ status: string; export_path: string }>("export_diagnostics");
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
