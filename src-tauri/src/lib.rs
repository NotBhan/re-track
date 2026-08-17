/**
 * Tauri bridge — thin Rust layer that:
 * 1. Launches the Python backend on startup
 * 2. Waits until healthy
 * 3. Proxies Tauri commands to Python HTTP endpoints asynchronously
 * 4. Shuts down the backend on exit
 */

use serde::{Deserialize, Serialize};
use std::fs;
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use std::time::Duration;
use tauri::Manager;

/// Backend process handle
struct BackendProcess(Mutex<Option<Child>>);

/// Base URL for the Python HTTP server
const BACKEND_URL: &str = "http://127.0.0.1:8765";

static HTTP_CLIENT: OnceLock<reqwest::Client> = OnceLock::new();

fn get_http_client() -> &'static reqwest::Client {
    HTTP_CLIENT.get_or_init(|| {
        reqwest::Client::builder()
            .pool_max_idle_per_host(10)
            .build()
            .unwrap_or_else(|_| reqwest::Client::new())
    })
}

// --- Request types (used for JSON serialization) ---

#[derive(Serialize, Deserialize, Debug)]
struct IndexRequest {
    repository_path: String,
    dataset_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    batch_size: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    force_reindex: Option<bool>,
}

#[derive(Serialize, Deserialize, Debug)]
struct ContextRequest {
    task: String,
    datasets: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    top_k: Option<u32>,
}

#[derive(Serialize, Deserialize, Debug)]
struct ForgetRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    dataset: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    dataset_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    data_id: Option<String>,
}

// --- Helper: HTTP client ---

/// Extract a human-readable message from a FastAPI error body.
fn extract_error(body: &serde_json::Value) -> String {
    match body.get("detail") {
        Some(serde_json::Value::Object(obj)) => obj
            .get("message")
            .and_then(|m| m.as_str())
            .unwrap_or("Unknown error")
            .to_string(),
        Some(serde_json::Value::Array(arr)) => arr
            .first()
            .and_then(|e| e.get("msg"))
            .and_then(|m| m.as_str())
            .map(|s| format!("Validation error: {}", s))
            .unwrap_or_else(|| "Validation error".to_string()),
        Some(serde_json::Value::String(s)) => s.clone(),
        _ => body.to_string(),
    }
}

async fn http_post<T: Serialize>(path: &str, body: &T) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = get_http_client();
    let resp = client
        .post(&url)
        .json(body)
        .timeout(Duration::from_secs(300)) // 5 min for indexing/LLM synthesis
        .send()
        .await
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(extract_error(&body))
    }
}

async fn http_get(path: &str) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = get_http_client();
    let resp = client
        .get(&url)
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(extract_error(&body))
    }
}

async fn http_delete(path: &str) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = get_http_client();
    let resp = client
        .delete(&url)
        .timeout(Duration::from_secs(30))
        .send()
        .await
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    if status.is_success() {
        Ok(body)
    } else {
        Err(extract_error(&body))
    }
}

// --- Tauri commands ---

#[tauri::command]
async fn health() -> Result<serde_json::Value, String> {
    http_get("/health").await
}

#[tauri::command]
async fn get_status() -> Result<serde_json::Value, String> {
    http_get("/status").await
}

#[tauri::command]
async fn index_repository(request: IndexRequest) -> Result<serde_json::Value, String> {
    http_post("/index", &request).await
}

#[derive(Serialize, Deserialize, Debug)]
struct AgentContextReq {
    task_prompt: String,
    repository_path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    dataset_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    include_structural_graph: Option<bool>,
}

#[tauri::command]
async fn generate_context(request: ContextRequest) -> Result<serde_json::Value, String> {
    http_post("/context", &request).await
}

#[tauri::command]
async fn get_agent_context(request: AgentContextReq) -> Result<serde_json::Value, String> {
    http_post("/api/v1/context", &request).await
}

#[tauri::command]
async fn forget_dataset(request: ForgetRequest) -> Result<serde_json::Value, String> {
    http_post("/forget", &request).await
}

#[tauri::command]
async fn list_datasets() -> Result<serde_json::Value, String> {
    http_get("/datasets").await
}

#[tauri::command]
async fn get_repository_summaries() -> Result<serde_json::Value, String> {
    http_get("/repositories").await
}

#[tauri::command]
async fn get_dashboard_stats() -> Result<serde_json::Value, String> {
    http_get("/dashboard/stats").await
}

#[tauri::command]
async fn get_memory_stats() -> Result<serde_json::Value, String> {
    http_get("/memory/stats").await
}

#[tauri::command]
async fn run_benchmark() -> Result<serde_json::Value, String> {
    let url = format!("{}/benchmarks/run", BACKEND_URL);
    let client = get_http_client();
    let resp = client
        .post(&url)
        .json(&serde_json::json!({}))
        .timeout(Duration::from_secs(300))
        .send()
        .await
        .map_err(|e| format!("HTTP request failed: {}", e))?;

    let status = resp.status();
    let body: serde_json::Value = resp
        .json()
        .await
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
async fn update_provider(request: serde_json::Value) -> Result<serde_json::Value, String> {
    http_post("/provider/update", &request).await
}

#[tauri::command]
async fn list_repositories() -> Result<serde_json::Value, String> {
    http_get("/repos").await
}

#[tauri::command]
async fn create_repository(request: serde_json::Value) -> Result<serde_json::Value, String> {
    http_post("/repos", &request).await
}

#[tauri::command]
async fn scan_repository(repo_id: String) -> Result<serde_json::Value, String> {
    http_post(
        &format!("/repos/{}/scan", repo_id),
        &serde_json::json!({}),
    )
    .await
}

#[tauri::command]
async fn get_repository_progress(repo_id: String) -> Result<serde_json::Value, String> {
    http_get(&format!("/repos/{}/progress", repo_id)).await
}

#[tauri::command]
async fn delete_repository(repo_id: String) -> Result<serde_json::Value, String> {
    http_delete(&format!("/repos/{}", repo_id)).await
}

// --- Context Package commands ---

#[tauri::command]
async fn list_context_packages() -> Result<serde_json::Value, String> {
    http_get("/packages").await
}

#[tauri::command]
async fn save_context_package(request: serde_json::Value) -> Result<serde_json::Value, String> {
    http_post("/packages", &request).await
}

#[tauri::command]
async fn get_context_package(package_id: String) -> Result<serde_json::Value, String> {
    http_get(&format!("/packages/{}", package_id)).await
}

#[tauri::command]
async fn delete_context_package(package_id: String) -> Result<serde_json::Value, String> {
    http_delete(&format!("/packages/{}", package_id)).await
}

#[tauri::command]
async fn append_context_package(
    package_id: String,
    request: serde_json::Value,
) -> Result<serde_json::Value, String> {
    http_post(&format!("/packages/{}/append", package_id), &request).await
}

// --- Backend lifecycle management ---

fn resolve_backend_dir() -> std::path::PathBuf {
    if let Ok(manifest) = std::env::var("CARGO_MANIFEST_DIR") {
        let src_tauri = std::path::Path::new(&manifest);
        if let Some(root) = src_tauri.parent() {
            let candidate = root.join("backend");
            if candidate.exists() {
                return candidate;
            }
        }
    }

    if let Ok(exe) = std::env::current_exe() {
        let mut dir = exe.as_path();
        for _ in 0..5 {
            if let Some(parent) = dir.parent() {
                let candidate = parent.join("backend");
                if candidate.exists() {
                    return candidate;
                }
                dir = parent;
            }
        }
    }

    std::path::PathBuf::from("backend")
}

fn resolve_python(backend_dir: &std::path::Path) -> Result<String, String> {
    let venv_python = backend_dir.join(".venv/bin/python");
    if venv_python.exists() {
        return Ok(venv_python.to_string_lossy().to_string());
    }

    for cmd in &["python3.13", "python3", "python"] {
        if Command::new(cmd)
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
        {
            return Ok(cmd.to_string());
        }
    }

    Err("Python not found. Create a virtualenv at backend/.venv or install Python.".to_string())
}

fn start_backend() -> Result<Child, String> {
    let backend_dir = resolve_backend_dir();
    let python = resolve_python(&backend_dir)?;

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

    let log_path = std::env::temp_dir().join("retrack-backend.log");
    let log_file = fs::File::create(&log_path)
        .map_err(|e| format!("Failed to create backend log {}: {}", log_path.display(), e))?;
    let log_err = log_file
        .try_clone()
        .unwrap_or_else(|_| fs::File::create("/dev/null").unwrap());

    let mut command = Command::new(&python);
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
        .env("PYTHONPATH", &backend_dir)
        .stdout(Stdio::from(log_file))
        .stderr(Stdio::from(log_err));

    for (key, value) in &env_vars {
        command.env(key, value);
    }

    eprintln!(
        "[RE:Track] Starting backend | python={} | dir={} | log={}",
        python,
        backend_dir.display(),
        log_path.display()
    );

    command
        .spawn()
        .map_err(|e| format!("Failed to spawn backend process: {}", e))
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
            let mut child = start_backend().expect("Failed to start Python backend");

            let ready = wait_for_backend(60);
            if !ready {
                child.kill().ok();
                let log = std::env::temp_dir().join("retrack-backend.log");
                panic!(
                    "Python backend did not become ready within 60 seconds. \
                     Check logs: {}",
                    log.display()
                );
            }

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
            get_agent_context,
            forget_dataset,
            list_datasets,
            get_repository_summaries,
            get_dashboard_stats,
            get_memory_stats,
            run_benchmark,
            list_repositories,
            create_repository,
            scan_repository,
            get_repository_progress,
            delete_repository,
            list_context_packages,
            save_context_package,
            get_context_package,
            delete_context_package,
            append_context_package,
            update_provider,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
