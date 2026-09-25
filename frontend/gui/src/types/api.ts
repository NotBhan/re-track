/**
 * RE:Track Authoritative Domain Types
 * Matches FastAPI backend response schemas and Tauri IPC command contracts.
 */

// --- AST & Code Structure ---

export interface CallGraphNode {
  id: string;
  label: string;
  file: string;
  kind: "function" | "method" | "class" | "component" | "module";
  line?: number;
}

export interface CallGraphEdge {
  source: string;
  target: string;
  kind: "calls" | "imports" | "inherits" | "renders";
}

export interface Repository {
  id: string;
  name: string;
  source_type: "github" | "local";
  source_url: string | null;
  local_path: string;
  branch: string;
  commit_hash: string | null;
  status: "registered" | "scanning" | "indexed" | "indexing" | "error";
  languages: string[];
  frameworks: string[];
  file_count: number;
  size_bytes: number;
  indexed_at: string | null;
  error_message: string | null;
  summary: string;
  entry_points: string[];
  architecture: string;
  components: string[];
  dependencies: string[];
  metadata: Record<string, unknown>;
  call_graph_status?: "not_analyzed" | "analyzing" | "analyzed" | "zero_edges" | "failed";
  call_graph_error?: string | null;
  call_graph_nodes?: CallGraphNode[];
  call_graph_edges?: CallGraphEdge[];
}

export interface ScanResult {
  repository_id: string;
  file_count: number;
  languages: string[];
  frameworks: string[];
  entry_points: string[];
  summary: string;
  components: string[];
  estimated_index_time_ms?: number;
}

export interface IndexingProgress {
  status: string;
  stage: string;
  stage_index?: number | null;
  stage_total?: number | null;
  processed_files: number;
  total_files: number;
  elapsed_ms: number;
  languages: string[];
  frameworks: string[];
  error: string | null;
  file_count: number;
  size_bytes: number;
}

// --- Inference Providers & Runtime ---

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

// --- Health & System Telemetry ---

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
  provider_identity?: string;
  provider_configured?: boolean;
  provider_reachable?: boolean;
  provider_health_state?: string;
  configured_model?: string | null;
  active_model?: string | null;
  active_model_state?: string;
  discovered_models?: string[];
  engine_state?: string;
  engine_reason?: string | null;
  cognee_state?: string;
  cognee_reason?: string | null;
}

// --- Context Generation & Agent Context ---

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

export interface ContextRequest {
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

export interface ContextPackageAppendRequest {
  additional_task: string;
  additional_markdown?: string;
  additional_objective?: string;
}

// --- Semantic Memory & Derived Storage ---

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

export interface CognifyResponse {
  success: boolean;
  dataset_name?: string | null;
  total_vectors: number;
  total_nodes: number;
  total_edges: number;
  message: string;
}

// --- Settings & Configuration ---

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

// --- Benchmarks & Diagnostics ---

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

export interface SuggestedPrompt {
  label: string;
  prompt: string;
}

export interface SuggestedPromptsResponse {
  success: boolean;
  prompts: SuggestedPrompt[];
  source: "ai" | "heuristic";
}
