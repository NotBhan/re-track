# Inference Provider Configuration & Discovery Guide

## Supported Providers

RE:Track supports local and remote OpenAI-compatible inference runners:

1. **Ollama** (Default)
   - **Default Base URL**: `http://127.0.0.1:11434/v1`
   - **Default API Key**: `ollama` or `local`
   - **Probing Endpoints**: `/v1/models` and native `/api/tags`
2. **LM Studio**
   - **Default Base URL**: `http://127.0.0.1:1234/v1`
   - **Default API Key**: `lm-studio` or `local`
   - **Probing Endpoints**: `/v1/models` and `/models`
3. **Custom OpenAI-Compatible**
   - **Default Base URL**: User-defined (e.g., `http://127.0.0.1:8080/v1` or remote endpoints)
   - **Authentication**: Bearer token via `Authorization: Bearer <API_KEY>`

---

## Model Discovery Workflow

1. Open **Settings** → **Inference & Provider Configuration**.
2. Select your provider from the dropdown (or enter a custom URL).
3. Click **Discover** to probe the runner for available models.
   - The probe is non-mutating and does not alter your active model configuration.
   - Discovered models will populate the **Active Model** dropdown.
4. Select the desired model (e.g. `phi4-mini:q6_k` or `qwen2.5-coder:7b`).
5. Click **Save & Apply** to hot-reload the backend runner and persist settings to disk (`~/.retrack/settings.json`).

---

## Discovery Status Indicators

| Status | Description | Action Required |
|---|---|---|
| `available` | Endpoint reachable, model(s) retrieved. | Select model and click Save & Apply. |
| `reachable_but_empty` | Endpoint reachable (HTTP 200), but 0 models loaded. | Load or pull a model in your local runner first. |
| `unreachable` | Connection refused, timeout, or DNS resolution failed. | Check runner execution and port. |
| `discovery_failed` | Authentication failed (401/403) or unexpected response. | Verify API key and base URL path. |
| `not_configured` | No endpoint configured. | Enter endpoint URL and discover. |

---

## Security & Persistence

- Settings are saved to `~/.retrack/settings.json` with POSIX `0600` permissions.
- Parent directory `~/.retrack` enforces `0700` permissions.
- Raw API keys are masked in status and telemetry responses (`sk-...123` or `configured`).
- Browser `localStorage` does not retain backend credentials or provider configuration.

---

## Configuration Precedence (Deterministic)

Exactly one precedence model governs every provider field — LLM provider/endpoint/model/API key,
embedding provider/endpoint/model/API key/dimensions, and the dedicated semantic-memory model.
Highest priority wins, per field:

1. **explicit constructor arguments** (`Settings(...)`)
2. **operator environment variables** — only values the operator actually set, never values
   RE:Track wrote itself
3. **persisted settings** (`~/.retrack/settings.json`)
4. **`backend/.env`**
5. **field defaults**

`Settings.apply_to_environment()` still exports provider identity into `os.environ` for Cognee
compatibility, but RE:Track records what it wrote. A later `Settings` instance therefore never
inherits an earlier instance's provider configuration, so provider/embedding availability no
longer depends on what a previous component did at runtime or on startup order.

`backend/.env` is resolved relative to the backend package, **not** the process working directory,
so identical launches produce identical configuration regardless of where they were started.

### LLM and embedding identity are independent

Changing the LLM identity never moves the embedding identity, and vice versa. No provider,
endpoint, or model is ever substituted. The configured embedding provider is mapped to the Cognee
embedding engine by a fixed, documented table — never a fallback:

| Configured embedding provider | Cognee engine | Endpoint requirement |
|---|---|---|
| `ollama` | `ollama` | optional; defaults to `http://<host>:<port>/api/embed` |
| `openai_compatible` (aliases `lmstudio`, `lm-studio`) | `openai_compatible` | required, must end in `/v1` |
| `fastembed` | `fastembed` | none (local) |
| any other value | LiteLLM provider of that name | provider-specific |

Every non-Ollama embedding provider requires an explicit endpoint: an unconfigured one reports
`not_configured` instead of borrowing the LLM endpoint.

### Embedding availability states

`Settings.probe_embedding_provider()` — surfaced on `/health` and `/status` as `embedding_state` —
reports exactly one truthful state and performs no substitution:

| State | Meaning |
|---|---|
| `available` | endpoint reachable and the configured model is listed |
| `model_missing` | endpoint reachable but the configured model is absent |
| `unreachable` | endpoint could not be reached |
| `not_configured` | endpoint or model is not configured |

Embedding health is evaluated separately from LLM health; a reachable LLM does not imply usable
embeddings and vice versa.

### Semantic-memory stage identity (a third, independent identity)

The semantic-memory extraction stage has its own provider / endpoint / model, configured through
its own path and never inferred from the interactive LLM or the embedding identity:

| Field | Environment variable | Notes |
|---|---|---|
| provider | `SEMANTIC_MEMORY_PROVIDER` | `ollama`, `lmstudio`, `openai_compatible`, … |
| endpoint | `SEMANTIC_MEMORY_ENDPOINT` | required for non-Ollama providers; empty means `not_configured` |
| model | `SEMANTIC_MEMORY_MODEL` (settings `memory_model`) | the dedicated extraction model |
| api key | `SEMANTIC_MEMORY_API_KEY` | defaults to `local` |

`Settings.semantic_memory_identity()` reports this identity, and `ApplicationContainer` builds a
dedicated extraction connection from it. **No substitution occurs**: when the endpoint or the model
is unconfigured the stage reports an explicit unavailable state (`not_configured`) and performs
zero inference. The interactive reasoning model is never reused for extraction, and no other model
is silently selected.

When configured but not actually served by the provider, the stage reports `model_unavailable`
rather than degrading into a generic generation failure.

### Semantic-memory availability states

`Settings.probe_semantic_memory_provider()` — surfaced on `/health` and `/status` as
`semantic_memory_state` — reports exactly one truthful state and performs no substitution:

| State | Meaning |
|---|---|
| `available` | endpoint reachable and the configured extraction model is listed |
| `model_missing` | endpoint reachable but the configured extraction model is absent |
| `unreachable` | endpoint could not be reached |
| `not_configured` | endpoint or extraction model is not configured |

### Embedded vector/graph materialization (`cognify`)

The indexing and cognification path only *ingests* (`CogneeService.add`), so it creates no
LanceDB vectors and no Kùzu graph records. Materializing them is a separate, explicit `cognify`
operation.

**Ollama caveat (verified):** when the *interactive* LLM provider is Ollama, Cognee's LiteLLM
Ollama adapter requires the native base URL in `LLM_ENDPOINT`
(`http://127.0.0.1:11434`), **not** the OpenAI-compatible form (`.../v1`). With `/v1`, litellm
appends `/api/...` and the request 404s. This affects Cognee's graph-extraction pass only; the
semantic-memory extraction client is an independent identity and correctly uses the `/v1` form.

### Why a dedicated extraction model

A reasoning model can consume its entire generation budget on hidden reasoning and never emit the
required JSON, so a small **non-reasoning instruction-following** model is required for this stage.
See `docs/cognee_integration.md` → *Semantic-Memory Extraction Stage* for the full contract.

### LM Studio and structured output

LM Studio is reached through litellm's `lm_studio` provider, for which litellm reports schema
support. Cognee therefore constrains structured output with `response_format: json_schema`, which
LM Studio accepts. Routing LM Studio through the generic `openai` provider makes Cognee send
`response_format: json_object`, which LM Studio rejects with HTTP 400.
