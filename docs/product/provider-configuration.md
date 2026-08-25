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
