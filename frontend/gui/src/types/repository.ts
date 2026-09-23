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
