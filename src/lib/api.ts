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
