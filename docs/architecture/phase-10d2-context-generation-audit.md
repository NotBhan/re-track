# Phase 10D.2 Context Generation Audit & Verification

## Overview

Phase 10D.2 hardens and verifies the context-generation pipeline in RE:Track. It guarantees that model-dependent semantic and intent synthesis invokes the configured local inference provider (LM Studio or Ollama) with explicit telemetry, while deterministic AST and symbol retrieval is truthfully exposed as fallback when the provider is offline or bypassed.

## Key Changes

### 1. IntentParserService Telemetry & Model Invocation
- Removed silent `except Exception: return fallback` swallows.
- Structured logging events (`context_model_invocation_started`, `context_model_invocation_completed`, `context_model_invocation_failed`, `context_deterministic_fallback`) emitted with provider name, model name, and elapsed duration.
- `ParsedIntentRecord` now records `model_invoked`, `provider_identity`, `model_name`, `inference_status`, `fallback_used`, `fallback_reason`, and `inference_time_ms`.

### 2. Provider Port Hardening
- `LLMProviderService.generate_completion()` strictly enforces the configured provider and default model name rather than synthetic fallbacks.
- Correct endpoint normalization for OpenAI-compatible and LM Studio endpoints (`/v1/chat/completions`).
- Explicit error classifications (`ConnectionError`, `TimeoutError`, `ValueError` for HTTP 404 model not found, `PermissionError` for 401/403).

### 3. Context Engine & Use Cases
- `ContextUseCases.get_agent_context()` propagates model invocation telemetry directly to `AgentContextResponse` and MCP tool responses.
- `ContextUseCases.generate_context()` explicitly reports `model_invoked=False`, `fallback_used=True`, `fallback_reason="Deterministic retrieval pipeline (model-free)"` without claiming synthetic AI generation.

### 4. User Interface Truthfulness
- `ContextStudio.tsx` renders a green `Model Synthesized` badge only when `model_invoked=True` and `inference_status="completed"`.
- Displays amber `Deterministic Fallback` badge with tooltip describing the reason when local heuristics are used.
- Context Package output panels clearly distinguish model-synthesized context from deterministic AST context.
- Zero secrets, raw prompts, or sensitive credentials exposed to telemetry or frontend state.

## Verification Matrix

| Test Suite | Coverage | Status |
| :--- | :--- | :--- |
| `tests/test_context_model_invocation.py` | LM Studio & Ollama invocation, fallback telemetry, model name propagation, provider failure handling | Passed |
| `tests/test_context_model_contract.py` | Telemetry defaults, backward compatibility, schema validation invariants | Passed |
| `tests/test_agent_context.py` | Agent context use case, caching, and symbol ranking | Passed |
| `tests/test_ast_integrity.py` | AST resolution purity | Passed |
| `src/test/journeys/*.test.tsx` | All 12 frontend journeys (51 tests) | Passed |
| `npm run build` | Full TypeScript & Vite build | Clean (0 errors) |
