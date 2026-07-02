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
}

export interface ScanResult {
  success: boolean;
  languages: string[];
  frameworks: string[];
  file_count: number;
  size_bytes: number;
  ignored_dirs: string[];
  estimated_index_time_ms: number;
}
