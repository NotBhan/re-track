# Context Generation Product Specification

## Purpose & Behavioral Contract

RE:Track synthesizes compact, high-precision Context Packages for external AI coding agents and interactive developer workflows.

### Operational Modes

1. **Model-Synthesized Context (`model_invoked: true`)**
   - Developer prompt is analyzed by the configured local inference provider (LM Studio / Ollama / OpenAI-compatible).
   - Structured JSON schema extracts task categories, exact code symbols, and file targets.
   - Combined with deterministic AST call graph expansion and vector memory retrieval.
   - UI Badge: `Model Synthesized` (Emerald Sparkles).

2. **Deterministic Fallback Context (`fallback_used: true`)**
   - Triggered when the local inference provider is offline, unreachable, unconfigured, or returns invalid schema.
   - Zero-hallucination regex heuristics extract referenced symbols, file patterns, and intent categories.
   - Deterministic AST call graph expansion and lexical code ranking continue to operate without disruption.
   - UI Badge: `Deterministic Fallback` (Amber).
   - Telemetry includes truthful `fallback_reason` (e.g., `ConnectionError: Connection refused`).

### Truth Boundary & Telemetry Guarantees

- **No Synthetic Inferences**: RE:Track never claims model completion when deterministic heuristics were run.
- **Provider Transparency**: The exact provider type and active model identifier used for synthesis are exposed in package metadata.
- **Credential Safety**: No API keys, bearer tokens, or raw prompts enter telemetry events or client-side storage.
