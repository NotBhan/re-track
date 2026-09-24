/**
 * Tauri IPC bridge for RE:Track.
 * Directly communicates with Rust invoke handlers in src-tauri/src/lib.rs.
 */

import { invoke } from "@tauri-apps/api/core";
import type {
  Repository,
  ScanResult,
  IndexingProgress,
  HealthResponse,
  DetailedHealthResponse,
  BackendStatusResponse,
  ProviderStatusResponse,
  ProviderDiscoveryRequest,
  ProviderDiscoveryResponse,
  UpdateProviderRequest,
  UpdateProviderResponse,
  AgentContextRequest,
  AgentContextResponse,
  ContextRequest,
  ContextResponse,
  SavedContextPackage,
  ContextPackageSaveRequest,
  ContextPackageAppendRequest,
  DatasetInfo,
  MemoryStatsResponse,
  MemoryGraphResponse,
  MemoryVectorsResponse,
  MemoryDataItem,
  CognifyResponse,
  AppSettingsResponse,
  CogneeSettingsRequest,
  BenchmarkSuiteResponse,
  SuggestedPromptsResponse,
} from "../types/api";

// --- System & Telemetry ---

export async function getHealth(): Promise<HealthResponse> {
  return invoke<HealthResponse>("health");
}

export async function getDetailedHealth(): Promise<DetailedHealthResponse> {
  return invoke<DetailedHealthResponse>("detailed_health");
}

export async function getBackendStatus(): Promise<BackendStatusResponse> {
  return invoke<BackendStatusResponse>("get_status");
}

export async function getDashboardStats(): Promise<{
  success: boolean;
  indexed_repos: number;
  total_files: number;
  total_embeddings: number;
  packages_generated: number;
  avg_gen_time_ms: number;
  last_indexed_repo: string;
  last_indexed_time: string;
}> {
  return invoke("get_dashboard_stats");
}

export async function getDiagnostics(): Promise<Record<string, unknown>> {
  return invoke("get_diagnostics");
}

export async function exportDiagnostics(): Promise<{ status: string; export_path: string }> {
  return invoke("export_diagnostics");
}

export async function runBenchmark(): Promise<BenchmarkSuiteResponse> {
  return invoke<BenchmarkSuiteResponse>("run_benchmark");
}

// --- Inference Providers & Runtime Settings ---

export async function getProviderStatus(): Promise<ProviderStatusResponse> {
  return invoke<ProviderStatusResponse>("get_provider_status");
}

export async function discoverProvider(
  request: ProviderDiscoveryRequest
): Promise<ProviderDiscoveryResponse> {
  return invoke<ProviderDiscoveryResponse>("discover_provider", { request });
}

export async function updateProvider(
  request: UpdateProviderRequest
): Promise<UpdateProviderResponse> {
  return invoke<UpdateProviderResponse>("update_provider", { request });
}

export async function getAppSettings(): Promise<AppSettingsResponse> {
  return invoke<AppSettingsResponse>("get_settings");
}

export async function updateCogneeSettings(
  request: CogneeSettingsRequest
): Promise<AppSettingsResponse> {
  return invoke<AppSettingsResponse>("update_cognee_settings", { request });
}

// --- Repositories & AST Knowledge ---

export async function listRepositories(): Promise<{
  success: boolean;
  repositories: Repository[];
  total_count: number;
}> {
  return invoke("list_repositories");
}

export async function createRepository(request: {
  source_type: string;
  source_url?: string;
  local_path?: string;
  name?: string;
}): Promise<Repository> {
  return invoke("create_repository", { request });
}

export async function scanRepository(repoId: string): Promise<ScanResult> {
  return invoke("scan_repository", { repoId });
}

export async function indexRepository(request: {
  repository_path: string;
  dataset_name: string;
  batch_size?: number;
  force_reindex?: boolean;
}): Promise<{
  success: boolean;
  repository_path: string;
  dataset_name: string;
  total_files: number;
  processed_files: number;
  failed_files: number;
  total_batches: number;
  failed_paths: string[];
  summary: string;
}> {
  return invoke("index_repository", { request });
}

export async function getRepositoryProgress(repoId: string): Promise<IndexingProgress> {
  return invoke("get_repository_progress", { repoId });
}

export async function deleteRepository(repoId: string): Promise<{ success: boolean }> {
  return invoke("delete_repository", { repoId });
}

export async function getRepositorySummaries(): Promise<{
  success: boolean;
  repositories: any[];
  total_count: number;
}> {
  return invoke("get_repository_summaries");
}

export async function getSuggestedPrompts(repoId: string): Promise<SuggestedPromptsResponse> {
  return invoke<SuggestedPromptsResponse>("get_suggested_prompts", { repoId });
}

// --- Context Generation & Packages ---

export async function getAgentContext(
  request: AgentContextRequest
): Promise<AgentContextResponse> {
  return invoke<AgentContextResponse>("get_agent_context", { request });
}

export async function generateContext(
  request: ContextRequest
): Promise<ContextResponse> {
  return invoke<ContextResponse>("generate_context", { request });
}

export async function listContextPackages(): Promise<{
  success: boolean;
  packages: SavedContextPackage[];
  total_count: number;
}> {
  return invoke("list_context_packages");
}

export async function getContextPackage(packageId: string): Promise<SavedContextPackage> {
  return invoke("get_context_package", { packageId });
}

export async function saveContextPackage(
  request: ContextPackageSaveRequest
): Promise<SavedContextPackage> {
  return invoke("save_context_package", { request });
}

export async function deleteContextPackage(packageId: string): Promise<{ success: boolean }> {
  return invoke("delete_context_package", { packageId });
}

export async function appendContextPackage(
  packageId: string,
  request: ContextPackageAppendRequest
): Promise<SavedContextPackage> {
  return invoke("append_context_package", { packageId, request });
}

// --- Derived Semantic Memory ---

export async function listDatasets(): Promise<{
  success: boolean;
  datasets: DatasetInfo[];
  total_count: number;
}> {
  return invoke("list_datasets");
}

export async function getDatasetItems(datasetId: string): Promise<{
  success: boolean;
  dataset_id: string;
  dataset_name: string;
  items: MemoryDataItem[];
  total_count: number;
}> {
  return invoke("get_dataset_items", { datasetId });
}

export async function getMemoryStats(): Promise<MemoryStatsResponse> {
  return invoke<MemoryStatsResponse>("get_memory_stats");
}

export async function getMemoryVectors(): Promise<MemoryVectorsResponse> {
  return invoke<MemoryVectorsResponse>("get_memory_vectors");
}

export async function getMemoryGraph(dataset?: string): Promise<MemoryGraphResponse> {
  return invoke<MemoryGraphResponse>("get_memory_graph", { dataset });
}

export async function cognifyDataset(
  request: { dataset_name?: string } = {}
): Promise<CognifyResponse> {
  return invoke<CognifyResponse>("cognify_dataset", { request });
}

export async function forgetDataset(request: {
  dataset?: string;
  dataset_id?: string;
  data_id?: string;
}): Promise<{ success: boolean; message: string }> {
  return invoke("forget_dataset", { request });
}
