/**
 * Tauri bridge — thin Rust layer that:
 * 1. Launches the Python backend on startup
 * 2. Waits until healthy
 * 3. Proxies Tauri commands to Python HTTP endpoints
 * 4. Shuts down the backend on exit
 */

use serde::{Deserialize, Serialize};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;
use tauri::Manager;

/// Backend process handle
struct BackendProcess(Mutex<Option<Child>>);

/// Base URL for the Python HTTP server
const BACKEND_URL: &str = "http://127.0.0.1:8765";

// --- Request types (used for JSON serialization) ---

#[derive(Serialize, Deserialize, Debug)]
struct IndexRequest {
    repository_path: String,
    dataset_name: String,
    batch_size: Option<u32>,
}

#[derive(Serialize, Deserialize, Debug)]
struct ContextRequest {
    task: String,
    datasets: Vec<String>,
    top_k: Option<u32>,
}

#[derive(Serialize, Deserialize, Debug)]
struct ForgetRequest {
    dataset: Option<String>,
    dataset_id: Option<String>,
    data_id: Option<String>,
}

// --- Helper: HTTP client ---

fn http_post<T: Serialize>(path: &str, body: &T) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = reqwest::blocking::Client::new();
    let resp = client
        .post(&url)
        .json(body)
        .timeout(Duration::from_secs(300)) // 5 min for indexing
        .send()
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(body
            .get("detail")
            .and_then(|d| d.get("message"))
            .and_then(|m| m.as_str())
            .unwrap_or("Unknown error")
            .to_string())
    }
}

fn http_get(path: &str) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = reqwest::blocking::Client::new();
    let resp = client
        .get(&url)
        .timeout(Duration::from_secs(30))
        .send()
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(body
            .get("detail")
            .and_then(|d| d.get("message"))
            .and_then(|m| m.as_str())
            .unwrap_or("Unknown error")
            .to_string())
    }
}

fn http_delete(path: &str) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = reqwest::blocking::Client::new();
    let resp = client
        .delete(&url)
        .timeout(Duration::from_secs(30))
        .send()
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(body
            .get("detail")
            .and_then(|d| d.get("message"))
            .and_then(|m| m.as_str())
            .unwrap_or("Unknown error")
            .to_string())
    }
}

// --- Tauri commands ---

#[tauri::command]
fn health() -> Result<serde_json::Value, String> {
    http_get("/health")
}

#[tauri::command]
fn get_status() -> Result<serde_json::Value, String> {
    http_get("/status")
}

#[tauri::command]
fn index_repository(request: IndexRequest) -> Result<serde_json::Value, String> {
    http_post("/index", &request)
}

#[tauri::command]
fn generate_context(request: ContextRequest) -> Result<serde_json::Value, String> {
    http_post("/context", &request)
}

#[tauri::command]
fn forget_dataset(request: ForgetRequest) -> Result<serde_json::Value, String> {
    http_post("/forget", &request)
}

#[tauri::command]
fn list_datasets() -> Result<serde_json::Value, String> {
    http_get("/datasets")
}

#[tauri::command]
fn get_repository_summaries() -> Result<serde_json::Value, String> {
    http_get("/repositories")
}

#[tauri::command]
fn get_dashboard_stats() -> Result<serde_json::Value, String> {
    http_get("/dashboard/stats")
}

#[tauri::command]
fn get_memory_stats() -> Result<serde_json::Value, String> {
    http_get("/memory/stats")
}

#[tauri::command]
fn run_benchmark() -> Result<serde_json::Value, String> {
    // POST with empty body — benchmarks can be slow, reuse 300s timeout
    let url = format!("{}/benchmarks/run", BACKEND_URL);
    let client = reqwest::blocking::Client::new();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({}))
        .timeout(Duration::from_secs(300))
        .send()
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(body
            .get("detail")
            .and_then(|d| d.get("message"))
            .and_then(|m| m.as_str())
            .unwrap_or("Unknown error")
            .to_string())
    }
}

// --- Repository commands ---

#[tauri::command]
fn list_repositories() -> Result<serde_json::Value, String> {
    http_get("/repos")
}

#[tauri::command]
fn create_repository(request: serde_json::Value) -> Result<serde_json::Value, String> {
    http_post("/repos", &request)
}

#[tauri::command]
fn scan_repository(repo_id: String) -> Result<serde_json::Value, String> {
    http_post(
        &format!("/repos/{}/scan", repo_id),
        &serde_json::json!({}),
    )
}

#[tauri::command]
fn delete_repository(repo_id: String) -> Result<serde_json::Value, String> {
    http_delete(&format!("/repos/{}", repo_id))
}

// --- Backend lifecycle management ---

fn start_backend() -> Result<Child, String> {
    // Use the directory where Cargo.toml lives (src-tauri's parent)
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| {
        std::env::current_dir()
            .map(|d| d.to_string_lossy().to_string())
            .unwrap_or_default()
    });
    let project_root = std::path::Path::new(&manifest_dir).parent().unwrap_or(std::path::Path::new("."));
    let backend_dir = project_root.join("backend");

    // Required environment variables for Cognee
    let env_vars = [
        ("HUGGINGFACE_TOKENIZER", "nomic-ai/nomic-embed-text-v1"),
        ("COGNEE_SKIP_CONNECTION_TEST", "true"),
        ("ENABLE_BACKEND_ACCESS_CONTROL", "false"),
        ("CACHING", "false"),
        ("LLM_MODEL", "phi3:mini"),
        ("EMBEDDING_MODEL", "nomic-embed-text:latest"),
        ("EMBEDDING_DIMENSIONS", "768"),
        ("VECTOR_DB_PROVIDER", "lancedb"),
        ("GRAPH_DB_PROVIDER", "kuzu"),
    ];

    // Try python3.13 first, then python3, then python
    for cmd in &["python3.13", "python3", "python"] {
        if Command::new(cmd)
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
        {
            let mut command = Command::new(cmd);
            command
                .args([
                    "-m",
                    "uvicorn",
                    "app.server:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8765",
                ])
                .current_dir(&backend_dir)
                .stdout(Stdio::piped())
                .stderr(Stdio::piped());

            // Set environment variables
            for (key, value) in &env_vars {
                command.env(key, value);
            }

            return command
                .spawn()
                .map_err(|e| format!("Failed to start backend: {}", e));
        }
    }
    Err("Python not found".to_string())
}

fn wait_for_backend(max_attempts: u32) -> bool {
    let client = reqwest::blocking::Client::new();
    for _ in 0..max_attempts {
        match client
            .get(format!("{}/health", BACKEND_URL))
            .timeout(Duration::from_secs(2))
            .send()
        {
            Ok(resp) if resp.status().is_success() => return true,
            _ => std::thread::sleep(Duration::from_secs(1)),
        }
    }
    false
}

fn stop_backend(process: &mut Option<Child>) {
    if let Some(mut child) = process.take() {
        let _ = child.kill();
    }
}

// --- App entry point ---

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // Start Python backend
            let mut child = start_backend().expect("Failed to start Python backend");

            // Wait for backend to be ready
            let ready = wait_for_backend(30);
            if !ready {
                child.kill().ok();
                panic!("Python backend did not become ready within 30 seconds");
            }

            // Store process handle
            let state = app.state::<BackendProcess>();
            *state.0.lock().unwrap() = Some(child);

            Ok(())
        })
        .on_window_event(|app, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = app.state::<BackendProcess>();
                let mut process = state.0.lock().unwrap();
                stop_backend(&mut process);
            }
        })
        .invoke_handler(tauri::generate_handler![
            health,
            get_status,
            index_repository,
            generate_context,
            forget_dataset,
            list_datasets,
            get_repository_summaries,
            get_dashboard_stats,
            get_memory_stats,
            run_benchmark,
            list_repositories,
            create_repository,
            scan_repository,
            delete_repository,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
