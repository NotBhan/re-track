"""
Runtime model capability probe and store for RE:Track backend.

Tests actual local inference endpoint support for chat, tool calling,
JSON mode, embeddings, and context window without inferring capabilities
solely from model names. Unverified capabilities are strictly represented
as 'unknown'.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

import httpx
import requests

from app.models.provider import (
    CapabilityStatus,
    ModelCapabilities,
    ProviderType,
)

logger = logging.getLogger(__name__)

DEFAULT_CAPABILITY_STORE_PATH = Path.home() / ".retrack" / "model_capabilities.json"


def fetch_trusted_model_metadata(
    base_url: str,
    model: str,
    timeout: float = 5.0,
    api_key: str = "local",
    provider: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Obtain model metadata from trusted provider endpoints.

    Does not guess defaults. Returns empty dict if metadata is unavailable.
    """
    clean_base = base_url.rstrip("/")
    root_url = clean_base[:-3] if clean_base.endswith("/v1") else clean_base
    headers = {"Authorization": f"Bearer {api_key}"}

    # 1. LM Studio: /api/v0/models
    try:
        resp = requests.get(f"{root_url}/api/v0/models", headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            models_list = data.get("data", []) if isinstance(data, dict) else []
            for item in models_list:
                m_id = item.get("id") or ""
                # Compare full id or leaf name
                if m_id == model or m_id.split("/")[-1] == model.split("/")[-1] or m_id.split(":")[0] == model.split(":")[0]:
                    ctx = item.get("loaded_context_length") or item.get("max_context_length")
                    meta: dict[str, Any] = {
                        "source": "lmstudio_api_v0",
                        "quantization": item.get("quantization"),
                        "arch": item.get("arch"),
                        "type": item.get("type"),
                    }
                    if isinstance(ctx, int) and ctx > 0:
                        meta["context_window"] = ctx
                    return meta
    except Exception as e:
        logger.debug("LM Studio metadata probe skipped: %s", e)

    # 2. Ollama: /api/tags and /api/show
    try:
        resp = requests.get(f"{root_url}/api/tags", timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            tags = data.get("models", []) if isinstance(data, dict) else []
            for item in tags:
                name = item.get("name") or item.get("model") or ""
                if name == model or name.split(":")[0] == model.split(":")[0]:
                    details = item.get("details", {})
                    ctx = details.get("context_length")
                    meta = {
                        "source": "ollama_api_tags",
                        "quantization": details.get("quantization_level"),
                        "family": details.get("family"),
                    }
                    if isinstance(ctx, int) and ctx > 0:
                        meta["context_window"] = ctx
                    return meta
    except Exception as e:
        logger.debug("Ollama metadata probe skipped: %s", e)

    return {}


async def async_fetch_trusted_model_metadata(
    base_url: str,
    model: str,
    timeout: float = 5.0,
    api_key: str = "local",
    provider: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Asynchronously obtain model metadata from trusted provider endpoints."""
    clean_base = base_url.rstrip("/")
    root_url = clean_base[:-3] if clean_base.endswith("/v1") else clean_base
    headers = {"Authorization": f"Bearer {api_key}"}

    # 1. LM Studio: /api/v0/models
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{root_url}/api/v0/models", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models_list = data.get("data", []) if isinstance(data, dict) else []
                for item in models_list:
                    m_id = item.get("id") or ""
                    if m_id == model or m_id.split("/")[-1] == model.split("/")[-1] or m_id.split(":")[0] == model.split(":")[0]:
                        ctx = item.get("loaded_context_length") or item.get("max_context_length")
                        meta: dict[str, Any] = {
                            "source": "lmstudio_api_v0",
                            "quantization": item.get("quantization"),
                            "arch": item.get("arch"),
                            "type": item.get("type"),
                        }
                        if isinstance(ctx, int) and ctx > 0:
                            meta["context_window"] = ctx
                        return meta
    except Exception as e:
        logger.debug("Async LM Studio metadata probe skipped: %s", e)

    # 2. Ollama: /api/tags
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{root_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                tags = data.get("models", []) if isinstance(data, dict) else []
                for item in tags:
                    name = item.get("name") or item.get("model") or ""
                    if name == model or name.split(":")[0] == model.split(":")[0]:
                        details = item.get("details", {})
                        ctx = details.get("context_length")
                        meta = {
                            "source": "ollama_api_tags",
                            "quantization": details.get("quantization_level"),
                            "family": details.get("family"),
                        }
                        if isinstance(ctx, int) and ctx > 0:
                            meta["context_window"] = ctx
                        return meta
    except Exception as e:
        logger.debug("Async Ollama metadata probe skipped: %s", e)

    return {}


def detect_model_capabilities(
    base_url: str,
    model: str,
    timeout: int = 15,
    *,
    api_key: str = "local",
    embedding_base_url: Optional[str] = None,
    embedding_model: Optional[str] = None,
    trusted_metadata: Optional[dict[str, Any]] = None,
    context_window: Optional[int] = None,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Probe an OpenAI-compatible local model endpoint.

    Tests actual endpoint support for chat, tool calling, JSON mode,
    and separately configured embeddings. Does not infer capabilities
    solely from model names.
    """
    clean_base = base_url.rstrip("/")
    if not clean_base.endswith("/v1"):
        completions_url = f"{clean_base}/v1/chat/completions"
    else:
        completions_url = f"{clean_base}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    result: dict[str, Any] = {
        "model": model,
        "chat": "unknown",
        "tool_calling": "unknown",
        "json_mode": "unknown",
        "reasoning": "unknown",
        "embeddings": "not_tested",
    }

    def probe(payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            completions_url,
            headers=headers,
            json={"model": model, "max_tokens": 32, **payload},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]

    # 1. Chat probe
    try:
        probe({"messages": [{"role": "user", "content": "Reply OK"}]})
        result["chat"] = "supported"
    except Exception:
        result["chat"] = "unavailable"
        return result

    # 2. Tool calling probe
    try:
        msg = probe({
            "messages": [{"role": "user", "content": "Call the test tool."}],
            "tools": [{
                "type": "function",
                "function": {
                    "name": "capability_test",
                    "description": "Capability probe",
                    "parameters": {"type": "object", "properties": {}},
                },
            }],
            "tool_choice": {
                "type": "function",
                "function": {"name": "capability_test"},
            },
        })
        result["tool_calling"] = (
            "supported" if msg.get("tool_calls") else "unsupported"
        )
    except Exception:
        result["tool_calling"] = "unknown"

    # 3. JSON mode probe
    try:
        msg = probe({
            "messages": [{
                "role": "user",
                "content": 'Return {"ok": true} as JSON.',
            }],
            "response_format": {"type": "json_object"},
        })
        json.loads(msg.get("content") or "")
        result["json_mode"] = "supported"
    except Exception:
        result["json_mode"] = "unknown"

    # 4. Reasoning: keep 'unknown' unless verified through model metadata or dedicated evaluation.
    # A model producing <think> text alone does NOT establish reliable reasoning capability.
    meta = trusted_metadata or fetch_trusted_model_metadata(base_url, model, timeout=5, api_key=api_key)
    if meta.get("verified_reasoning"):
        result["reasoning"] = "supported"
    else:
        result["reasoning"] = "unknown"

    # 5. Embeddings: test the separately configured embedding model through /embeddings;
    # don't assume the chat model supports them.
    if embedding_model:
        emb_base = (embedding_base_url or base_url).rstrip("/")
        if not emb_base.endswith("/v1"):
            emb_url = f"{emb_base}/v1/embeddings"
        else:
            emb_url = f"{emb_base}/embeddings"
        try:
            emb_resp = requests.post(
                emb_url,
                headers=headers,
                json={"model": embedding_model, "input": "probe test"},
                timeout=timeout,
            )
            if emb_resp.status_code == 200 and "data" in emb_resp.json():
                result["embeddings"] = "supported"
                result["embedding_model"] = embedding_model
            else:
                result["embeddings"] = "unavailable"
        except Exception:
            result["embeddings"] = "unavailable"
    else:
        result["embeddings"] = "not_tested"

    # 6. Context window: obtain from trusted metadata or configuration, not a guessed default.
    ctx = context_window or meta.get("context_window")
    if isinstance(ctx, int) and ctx > 0:
        result["context_window"] = ctx
    else:
        result["context_window"] = None

    return result


async def async_detect_model_capabilities(
    base_url: str,
    model: str,
    timeout: int = 15,
    *,
    api_key: str = "local",
    embedding_base_url: Optional[str] = None,
    embedding_model: Optional[str] = None,
    trusted_metadata: Optional[dict[str, Any]] = None,
    context_window: Optional[int] = None,
    provider: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Asynchronously probe an OpenAI-compatible local model endpoint."""
    clean_base = base_url.rstrip("/")
    if not clean_base.endswith("/v1"):
        completions_url = f"{clean_base}/v1/chat/completions"
    else:
        completions_url = f"{clean_base}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    result: dict[str, Any] = {
        "model": model,
        "chat": "unknown",
        "tool_calling": "unknown",
        "json_mode": "unknown",
        "reasoning": "unknown",
        "embeddings": "not_tested",
    }

    async def probe(client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
        response = await client.post(
            completions_url,
            headers=headers,
            json={"model": model, "max_tokens": 32, **payload},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]

    async with httpx.AsyncClient(timeout=float(timeout)) as client:
        # 1. Chat probe
        try:
            await probe(client, {"messages": [{"role": "user", "content": "Reply OK"}]})
            result["chat"] = "supported"
        except Exception:
            result["chat"] = "unavailable"
            return result

        # 2. Tool calling probe
        try:
            msg = await probe(client, {
                "messages": [{"role": "user", "content": "Call the test tool."}],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "capability_test",
                        "description": "Capability probe",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": "capability_test"},
                },
            })
            result["tool_calling"] = (
                "supported" if msg.get("tool_calls") else "unsupported"
            )
        except Exception:
            result["tool_calling"] = "unknown"

        # 3. JSON mode probe
        try:
            msg = await probe(client, {
                "messages": [{
                    "role": "user",
                    "content": 'Return {"ok": true} as JSON.',
                }],
                "response_format": {"type": "json_object"},
            })
            json.loads(msg.get("content") or "")
            result["json_mode"] = "supported"
        except Exception:
            result["json_mode"] = "unknown"

    # 4. Reasoning
    meta = trusted_metadata or await async_fetch_trusted_model_metadata(base_url, model, timeout=5.0, api_key=api_key)
    if meta.get("verified_reasoning"):
        result["reasoning"] = "supported"
    else:
        result["reasoning"] = "unknown"

    # 5. Embeddings
    if embedding_model:
        emb_base = (embedding_base_url or base_url).rstrip("/")
        if not emb_base.endswith("/v1"):
            emb_url = f"{emb_base}/v1/embeddings"
        else:
            emb_url = f"{emb_base}/embeddings"
        try:
            async with httpx.AsyncClient(timeout=float(timeout)) as client:
                emb_resp = await client.post(
                    emb_url,
                    headers=headers,
                    json={"model": embedding_model, "input": "probe test"},
                )
                if emb_resp.status_code == 200 and "data" in emb_resp.json():
                    result["embeddings"] = "supported"
                    result["embedding_model"] = embedding_model
                else:
                    result["embeddings"] = "unavailable"
        except Exception:
            result["embeddings"] = "unavailable"
    else:
        result["embeddings"] = "not_tested"

    # 6. Context window
    ctx = context_window or meta.get("context_window")
    if isinstance(ctx, int) and ctx > 0:
        result["context_window"] = ctx
    else:
        result["context_window"] = None

    return result


class CapabilityStore:
    """Thread-safe persistent store for probed model capabilities per provider and model."""

    def __init__(self, store_path: Optional[Path] = None) -> None:
        self.store_path = store_path or DEFAULT_CAPABILITY_STORE_PATH
        self._cache: dict[str, dict[str, Any]] = {}
        self.load_persisted()

    @staticmethod
    def _key(provider: str, base_url: str, model: str) -> str:
        clean_url = (base_url or "").strip().rstrip("/")
        clean_prov = (provider or "openai_compatible").strip().lower()
        clean_model = (model or "").strip()
        return f"{clean_prov}::{clean_url}::{clean_model}"

    def load_persisted(self) -> None:
        """Load capabilities from persistent JSON file."""
        if not self.store_path.exists():
            return
        try:
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self._cache = data
        except Exception as e:
            logger.warning("Failed to load model capabilities from %s: %s", self.store_path, e)

    def save_persisted(self) -> None:
        """Atomically persist capabilities to JSON file."""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.store_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
            tmp_path.replace(self.store_path)
        except Exception as e:
            logger.warning("Failed to save model capabilities to %s: %s", self.store_path, e)

    def get(self, provider: str, base_url: str, model: str) -> Optional[dict[str, Any]]:
        """Retrieve stored capabilities for provider, endpoint, and model."""
        key = self._key(provider, base_url, model)
        return self._cache.get(key)

    def set(self, provider: str, base_url: str, model: str, capabilities: dict[str, Any]) -> None:
        """Store capabilities in memory and persist."""
        key = self._key(provider, base_url, model)
        caps = dict(capabilities)
        caps["provider"] = provider
        self._cache[key] = caps
        self.save_persisted()

    async def refresh_async(
        self,
        provider: str,
        base_url: str,
        model: str,
        timeout: int = 15,
        api_key: str = "local",
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        context_window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Probe endpoint asynchronously and update store."""
        caps = await async_detect_model_capabilities(
            base_url=base_url,
            model=model,
            timeout=timeout,
            api_key=api_key,
            embedding_base_url=embedding_base_url,
            embedding_model=embedding_model,
            context_window=context_window,
        )
        self.set(provider, base_url, model, caps)
        return caps

    def refresh(
        self,
        provider: str,
        base_url: str,
        model: str,
        timeout: int = 15,
        api_key: str = "local",
        embedding_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None,
        context_window: Optional[int] = None,
    ) -> dict[str, Any]:
        """Probe endpoint synchronously and update store."""
        caps = detect_model_capabilities(
            base_url=base_url,
            model=model,
            timeout=timeout,
            api_key=api_key,
            embedding_base_url=embedding_base_url,
            embedding_model=embedding_model,
            context_window=context_window,
        )
        self.set(provider, base_url, model, caps)
        return caps


_DEFAULT_STORE: Optional[CapabilityStore] = None


def get_capability_store() -> CapabilityStore:
    """Retrieve global singleton CapabilityStore."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = CapabilityStore()
    return _DEFAULT_STORE
