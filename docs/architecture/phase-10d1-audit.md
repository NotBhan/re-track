# Phase 10D.1 Audit: Frontend ↔ Backend Integration and Provider Configuration Hardening

## Overview
Phase 10D.1 solidifies the operational surface between the desktop frontend and the authoritative backend. It eliminates port-based heuristics, removes secret persistence from `localStorage`, introduces non-mutating model discovery, and establishes atomic filesystem persistence for runtime settings.

---

## 1. Truth Boundary Guarantee & State Hydration
- **Port Heuristic Elimination**: Previously, `OllamaSettings.tsx` inspected `status?.ollama_port === 1234` to guess if LM Studio was running. The backend now exposes `GET /provider/status` and `GET /settings`, which report the explicit provider identity (`ollama`, `lmstudio`, `openai_compatible`), base URL, and active model.
- **Authoritative Hydration**: The frontend Zustand store (`src/stores/settings-store.ts`) dropped the `zustand/middleware/persist` wrapper for backend configuration. On mount, settings are hydrated authoritatively from the backend via `getAppSettings()` and `getProviderStatus()`.
- **Secret Redaction**: API keys and tokens are never returned in cleartext from the backend or persisted to browser `localStorage`. Endpoints return `api_key_configured: bool` and `api_key_masked: str` (e.g., `"sk-...123"` or `"local"`).

---

## 2. Non-Mutating Model Discovery Engine
The backend implements `POST /provider/discover` (orchestrated by `LLMProviderService.discover_models_for_endpoint` and `SystemUseCases.discover_provider_models`):
- **Candidate Probing**: Probes candidate endpoints using multi-target path resolution (`/v1/models`, `/models`, and Ollama native `/api/tags`) without modifying active backend state or mutating configuration.
- **Truthful Status Codes**:
  - `available`: Endpoint is reachable and returns one or more models.
  - `reachable_but_empty`: Endpoint is reachable (HTTP 200), but 0 models are loaded in the runner. The UI warns the user to load a model in the runner first without synthesizing dummy entries.
  - `unreachable`: Connection refused, timeout, or DNS failure.
  - `discovery_failed`: Authentication failure (HTTP 401/403) or unexpected payload structure.
  - `not_configured`: Provider endpoint is unset.
- **Quantization Inspection**: Tags discovered models with phi4:mini compatibility and quantization indicators (`Q6_K`, `Q4_K_M`, `FP16`), raising quantization warnings when below recommended fidelity.

---

## 3. Atomic Filesystem Persistence
- **Storage Path**: Settings are saved to `~/.retrack/settings.json` (or custom configured store path).
- **Atomic Operations**: `save_persisted_settings()` writes to a temporary file (`.tmp`) in the directory before performing an atomic rename (`replace`).
- **POSIX Permission Hardening**:
  - Settings directory (`~/.retrack`) enforces `0o700` (`rwx------`).
  - Settings file (`~/.retrack/settings.json`) enforces `0o600` (`rw-------`).

---

## 4. Architectural Boundaries
- **Hexagonal / Clean Architecture Purity**: `SystemUseCases` depends strictly on the `LLMProviderPort` protocol rather than concrete services (`app.services.llm_provider_service`).
- **Tauri IPC Transport**: Added `get_provider_status` and `discover_provider` commands in `src-tauri/src/lib.rs` and `e2e/tauri-bridge.ts`.
