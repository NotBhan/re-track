"""
OpenAI-compatible LLM Provider Service for RE:Track.

Supports Ollama, LM Studio, and generic OpenAI-compatible local/remote servers.
Inspects loaded models and evaluates model quality (e.g. phi4:mini variant and Q6+ status)
without initiating unapproved model downloads.
"""

import logging
import re
from typing import Any, Optional
import httpx

from app.models.provider import (
    LoadedModelInfo,
    ProviderHealthStatus,
    ProviderType,
    QuantizationLevel,
)

logger = logging.getLogger(__name__)


class LLMProviderService:
    """Async client wrapper for OpenAI-compatible inference endpoints."""

    def __init__(
        self,
        provider_type: ProviderType = ProviderType.OLLAMA,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "local",
        default_model: str = "phi4-mini",
        timeout: float = 5.0,
    ) -> None:
        self.provider_type = provider_type
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout

    @staticmethod
    def parse_quantization(model_id: str) -> QuantizationLevel:
        """Infer quantization tier from model tag or filename."""
        lowered = model_id.lower()
        if "q6_k" in lowered or "q6" in lowered:
            return QuantizationLevel.Q6_K
        if "q8_0" in lowered or "q8" in lowered:
            return QuantizationLevel.Q8_0
        if "fp16" in lowered or "f16" in lowered:
            return QuantizationLevel.FP16
        if "q5_k" in lowered or "q5" in lowered:
            return QuantizationLevel.Q5_K_M
        if "q4_k" in lowered or "q4_0" in lowered or "q4" in lowered:
            return QuantizationLevel.Q4_K_M
        return QuantizationLevel.UNKNOWN

    def evaluate_model_quality(self, model_id: str) -> LoadedModelInfo:
        """Evaluate if the loaded model is phi4:mini and check quantization tier."""
        lowered = model_id.lower()
        is_phi4 = bool(re.search(r"phi[-_]?4[-_]?mini", lowered))
        quant = self.parse_quantization(model_id)

        is_q6_plus = quant in (
            QuantizationLevel.Q6_K,
            QuantizationLevel.Q8_0,
            QuantizationLevel.FP16,
        )

        warning = None
        if is_phi4 and not is_q6_plus and quant != QuantizationLevel.UNKNOWN:
            warning = (
                f"Model '{model_id}' is running with {quant.value} quantization. "
                "For optimal reasoning in constrained 8GB VRAM/RAM environments, "
                "phi4:mini Q6_K or higher is recommended."
            )
        elif not is_phi4:
            warning = (
                f"Active model '{model_id}' is not a phi4:mini variant. "
                "RE:Track reasoning and compression performance is tuned for phi4:mini."
            )

        return LoadedModelInfo(
            model_id=model_id,
            name=model_id.split(":")[0],
            quantization=quant,
            is_phi4_mini=is_phi4,
            is_q6_or_higher=is_q6_plus,
            warning=warning,
        )

    async def list_models(self) -> list[LoadedModelInfo]:
        """Query /models endpoint to discover available models in the active provider."""
        models_url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(models_url, headers=headers)
                if resp.status_code != 200:
                    logger.warning("GET %s returned status %d", models_url, resp.status_code)
                    return []
                data = resp.json()
                items = data.get("data", [])
                results = []
                for item in items:
                    m_id = item.get("id") or item.get("name") or ""
                    if m_id:
                        results.append(self.evaluate_model_quality(m_id))
                return results
        except Exception as e:
            logger.debug("Failed to list models from %s: %s", models_url, e)
            return []

    async def check_health(self) -> ProviderHealthStatus:
        """Perform non-blocking health check and inspect loaded model quality."""
        models = await self.list_models()
        is_reachable = len(models) > 0

        # If /models was empty, attempt basic connection probe
        if not is_reachable:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{self.base_url}/models")
                    is_reachable = resp.status_code in (200, 401, 403)
            except Exception:
                is_reachable = False

        active_model = self.default_model
        quant_warning = None

        # Find matching model info
        for m in models:
            if m.model_id == self.default_model or m.name == self.default_model:
                quant_warning = m.warning
                break
        else:
            if models:
                active_model = models[0].model_id
                quant_warning = models[0].warning

        return ProviderHealthStatus(
            provider=self.provider_type,
            base_url=self.base_url,
            is_reachable=is_reachable,
            active_model=active_model,
            loaded_models=models,
            quantization_warning=quant_warning,
        )

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """Execute a completion via OpenAI-compatible /chat/completions API."""
        chat_url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(chat_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
