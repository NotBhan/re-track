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

### Semantic-memory stage model

`memory_model` (environment variable `SEMANTIC_MEMORY_MODEL`) selects a dedicated model for
semantic-memory extraction. When empty it falls back to the configured inference model. A
reasoning model can consume its entire generation budget on hidden reasoning and never emit the
required JSON, so a non-reasoning instruct model is recommended for this stage.

### LM Studio and structured output

LM Studio is reached through litellm's `lm_studio` provider, for which litellm reports schema
support. Cognee therefore constrains structured output with `response_format: json_schema`, which
LM Studio accepts. Routing LM Studio through the generic `openai` provider makes Cognee send
`response_format: json_object`, which LM Studio rejects with HTTP 400.
