# Phase 10D.1.1 Architectural Audit — Runtime Engine State Reconciliation

**Status**: COMPLETED & FROZEN  
**Role**: Principal Frontend Architect, Backend Integration Engineer, Tauri Runtime Engineer, Production Reliability Engineer  
**Date**: 2026-08-25  

---

## 1. Executive Summary

During Phase 10D.1, authoritative provider detection, non-mutating model discovery, atomic POSIX-permissioned persistence, and secret masking were successfully established. However, when configured with LM Studio (`http://127.0.0.1:1234/v1`), runtime engine state indicators across the RE:Track application diverged:
- Settings > Inference reported LM Studio as configured, healthy, with 8 discovered models.
- Global top bar and bottom status deck reported `"Engine offline"`.
- Repositories page displayed `"AI Provider Offline"`.
- Header telemetry displayed a stale synthetic fallback (`"phi4-mini"`).
- Cognee was reported as offline, dragging the entire engine health down.

Phase 10D.1.1 resolved all root causes of this divergence without adding extraneous abstractions, without port-based heuristics, and without inventing synthetic fallback models.

---

## 2. Root Cause Analysis & Resolution

| ID | Symptom / Defect | Root Cause | Resolution |
|---|---|---|---|
| **RC-1** | Backend started with Ollama port `11434` despite LM Studio in `settings.json`. | `Settings.apply_to_environment()` defaulted to `self.ollama.llm_endpoint` when `self.llm_endpoint` was not synced, overriding `os.environ` during Cognee initialization. | Fixed `apply_to_environment()` to prioritize `self.llm_endpoint`, `self.llm_provider`, and `self.llm_api_key`. |
| **RC-2** | Cognee failed to initialize and reported offline under LM Studio. | `CogneeService.initialize()` unconditionally invoked `validate_ollama()`, probing hardcoded port `11434`. | Introduced `validate_provider()` which validates the active configured provider and maps LM Studio to LiteLLM OpenAI provider. |
| **RC-3** | Cognee initialization failure disabled the entire inference engine. | `ApplicationContainer.initialize()` blocked `llm_provider` when Cognee threw exceptions. | Decoupled initialization order: `llm_provider` is initialized first, and Cognee initialization errors are caught and marked degraded without disabling inference. |
| **RC-4** | Active model was incorrectly inferred from discovered models. | `LLMProviderService.check_health()` took `models[0]` from discovery as active model. | Active model is only set if backend has authoritative proof or if `default_model` is explicitly configured and present. |
| **RC-5** | Synthetic `"phi4-mini"` model fallback in frontend TopBar. | `TopBar.tsx` used `activeModel \|\| "phi4-mini"`. | Replaced with `activeModel \|\| configuredModel \|\| "No active model"`, strictly upholding the Truth Boundary guarantee. |
| **RC-6** | Multiple disparate health endpoints and store drift. | Frontend derived status from partial fields across `HealthResponse` and `BackendStatusResponse`. | Enriched both DTOs with canonical runtime fields: `engine_state`, `engine_reason`, `provider_identity`, `provider_reachable`, `provider_health_state`, `active_model`, `configured_model`, `cognee_state`, `cognee_reason`. |

---

## 3. Authoritative Runtime Engine State Contract

Both `GET /health` (`HealthResponse`) and `GET /status` (`BackendStatusResponse`) now provide the following canonical fields:

```json
{
  "provider_identity": "lmstudio",
  "provider_configured": true,
  "provider_reachable": true,
  "provider_health_state": "healthy",
  "provider_base_url": "http://127.0.0.1:1234/v1",
  "configured_model": "qwen2.5-coder:7b",
  "active_model": "qwen2.5-coder:7b",
  "active_model_state": "active",
  "discovered_models": ["qwen2.5-coder:7b", "phi4-mini:latest"],
  "engine_state": "healthy",
  "engine_reason": null,
  "cognee_state": "healthy",
  "cognee_reason": null
}
```

### State Truth Rules
1. **Inference Reachability**: `provider_reachable == true` means the configured inference endpoint responded to probe requests.
2. **Independent Memory Health**: `cognee_state` is evaluated separately from `engine_state`. If Cognee is offline but LM Studio is online, `engine_state == "healthy"` while `cognee_state == "unavailable"`.
3. **Model Honesty**: `discovered_models` contains candidate models; `active_model` contains only the active running model (or `null` if unknown).

---

## 4. Frontend Component State Alignment

Every runtime surface consumes `useHealthStore` without reconstructing or guessing state:

1. **`TopBar.tsx`**:
   - Badge derived from `engineState`: `"Engine Ready"` (green), `"Engine Degraded"` (amber), `"Engine Unavailable"` (red), or `"Engine Offline"` (gray).
   - Displays `activeModel || configuredModel || "No active model"` (zero synthetic fallbacks).
2. **`Sidebar.tsx`**:
   - Status deck displays `engineLabel`, `displayModel`, and `providerLabel` (e.g. `qwen2.5-coder · LM Studio`).
   - Cognee status displayed independently (`ready` / `offline`).
3. **`ProviderAlertBanner.tsx`**:
   - Consumes `providerReachable` and dynamic `providerLabel` (`LM Studio`, `Ollama`).
4. **`Memory.tsx`**:
   - Displays independent status badges for Inference Provider (`LM Studio: Ready`) and Cognee Memory (`Cognee: Initialized` / `Offline`).
5. **`SettingsStore.ts`**:
   - Upon `saveProviderSettings()`, triggers `useHealthStore.getState().pollHealth()` immediately to synchronize all UI decks without page refresh.

---

## 5. Verification & Test Suite Summary

### Automated Test Results
- **Backend Pytest Suite**: **586/586 PASSED** (100%) in 5m 51s (`backend/tests/`)
- **Dedicated Provider & Reconciliation Tests**: **13/13 PASSED** (`tests/test_provider_configuration.py` & `tests/test_phase_8e_provider_lifecycle.py`)
- **AST Integrity Test Suite**: **4/4 PASSED** (`tests/test_ast_integrity.py`)
- **Frontend Vitest Behavioral Journeys**: **51/51 PASSED** (`src/test/journeys/`)
- **Frontend Production Build Check**: **0 Errors**, 100% clean TypeScript compile (`npm run build`)

---

## 6. Phase 10D.1.1 Sign-Off

Phase 10D.1.1 is hereby **COMPLETED**, **VERIFIED**, and **FROZEN**. All runtime surfaces across RE:Track faithfully reflect the backend's authoritative provider and memory state.
