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
    DiscoveryStatus,
    LoadedModelInfo,
    ProviderDiscoveryResult,
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

    @classmethod
    def evaluate_model_quality(cls, model_id: str) -> LoadedModelInfo:
        """Evaluate if the loaded model is phi4:mini and check quantization tier."""
        lowered = model_id.lower()
        is_phi4 = bool(re.search(r"phi[-_]?4[-_]?mini", lowered))
        quant = cls.parse_quantization(model_id)

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

    @classmethod
    async def discover_models_for_endpoint(
        cls,
        provider_type: ProviderType | str,
        base_url: str,
        api_key: str = "local",
        timeout: float = 5.0,
    ) -> ProviderDiscoveryResult:
        """Non-mutating model discovery probe for candidate or active provider endpoints."""
        clean_url = (base_url or "").strip().rstrip("/")
        if not clean_url:
            return ProviderDiscoveryResult(
                provider=provider_type if isinstance(provider_type, ProviderType) else ProviderType.OPENAI_COMPATIBLE,
                base_url="",
                is_reachable=False,
                status=DiscoveryStatus.NOT_CONFIGURED,
                models=[],
                message="Provider endpoint URL is not configured.",
            )

        p_type = provider_type if isinstance(provider_type, ProviderType) else (
            ProviderType.LM_STUDIO if "lm" in str(provider_type).lower() or "studio" in str(provider_type).lower()
            else ProviderType.OLLAMA if "ollama" in str(provider_type).lower()
            else ProviderType.OPENAI_COMPATIBLE
        )

        # Build candidate URLs for model discovery
        candidate_urls: list[str] = []
        if clean_url.endswith("/v1"):
            candidate_urls.append(f"{clean_url}/models")
            base_no_v1 = clean_url[:-3]
            if p_type == ProviderType.OLLAMA:
                candidate_urls.append(f"{base_no_v1}/api/tags")
        else:
            candidate_urls.append(f"{clean_url}/v1/models")
            candidate_urls.append(f"{clean_url}/models")
            if p_type == ProviderType.OLLAMA:
                candidate_urls.append(f"{clean_url}/api/tags")

        headers = {"Authorization": f"Bearer {api_key}"}
        last_error = None
        last_status_code = None

        for url in candidate_urls:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(url, headers=headers)
                    last_status_code = resp.status_code

                    if resp.status_code == 200:
                        data = resp.json()
                        raw_items = []
                        if isinstance(data, dict):
                            raw_items = data.get("data") or data.get("models") or []
                        elif isinstance(data, list):
                            raw_items = data

                        results: list[LoadedModelInfo] = []
                        for item in raw_items:
                            m_id = ""
                            if isinstance(item, dict):
                                m_id = item.get("id") or item.get("name") or item.get("model") or ""
                            elif isinstance(item, str):
                                m_id = item
                            if m_id:
                                results.append(cls.evaluate_model_quality(m_id))

                        if len(results) == 0:
                            return ProviderDiscoveryResult(
                                provider=p_type,
                                base_url=clean_url,
                                is_reachable=True,
                                status=DiscoveryStatus.REACHABLE_BUT_EMPTY,
                                models=[],
                                message=f"Provider is reachable at {clean_url}, but no models are currently loaded or available.",
                            )

                        return ProviderDiscoveryResult(
                            provider=p_type,
                            base_url=clean_url,
                            is_reachable=True,
                            status=DiscoveryStatus.AVAILABLE,
                            models=results,
                            message=f"Discovered {len(results)} model(s) from {p_type.value}.",
                        )
                    elif resp.status_code in (401, 403):
                        return ProviderDiscoveryResult(
                            provider=p_type,
                            base_url=clean_url,
                            is_reachable=True,
                            status=DiscoveryStatus.DISCOVERY_FAILED,
                            models=[],
                            message=f"Authentication failed (HTTP {resp.status_code}) for endpoint {clean_url}.",
                            error_details=f"HTTP {resp.status_code}",
                        )
            except httpx.ConnectError as ce:
                last_error = f"Connection refused: {ce}"
            except httpx.TimeoutException:
                last_error = "Connection timed out"
            except Exception as e:
                last_error = str(e)

        # If none of candidate URLs succeeded
        if last_error and ("refused" in last_error.lower() or "timed out" in last_error.lower()):
            return ProviderDiscoveryResult(
                provider=p_type,
                base_url=clean_url,
                is_reachable=False,
                status=DiscoveryStatus.UNREACHABLE,
                models=[],
                message=f"Provider endpoint '{clean_url}' is unreachable. Verify host and port.",
                error_details=last_error,
            )

        return ProviderDiscoveryResult(
            provider=p_type,
            base_url=clean_url,
            is_reachable=False,
            status=DiscoveryStatus.DISCOVERY_FAILED,
            models=[],
            message=f"Model discovery failed for endpoint '{clean_url}'.",
            error_details=last_error or f"HTTP {last_status_code}",
        )

    async def list_models(self) -> list[LoadedModelInfo]:
        """Query /models endpoint to discover available models in the active provider."""
        result = await self.discover_models_for_endpoint(
            provider_type=self.provider_type,
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        return result.models

    async def check_health(self) -> ProviderHealthStatus:
        """Perform non-blocking health check and inspect loaded model quality."""
        discovery = await self.discover_models_for_endpoint(
            provider_type=self.provider_type,
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        models = discovery.models
        is_reachable = discovery.is_reachable

        active_model = self.default_model if self.default_model else None
        quant_warning = None

        # Find matching model info if default_model is specified
        if active_model:
            for m in models:
                if m.model_id == active_model or m.name == active_model:
                    quant_warning = m.warning
                    break

        return ProviderHealthStatus(
            provider=self.provider_type,
            base_url=self.base_url,
            is_reachable=is_reachable,
            active_model=active_model,
            loaded_models=models,
            quantization_warning=quant_warning,
            discovery_status=discovery.status,
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
        clean_base = (self.base_url or "").strip().rstrip("/")
        if not clean_base:
            raise ValueError("Provider endpoint URL is not configured.")

        chat_url = f"{clean_base}/chat/completions"
        if not clean_base.endswith("/v1") and not chat_url.endswith("/v1/chat/completions"):
            chat_url = f"{clean_base}/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        target_model = model or self.default_model or "phi4-mini"

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(chat_url, headers=headers, json=payload)
                if resp.status_code == 404:
                    raise ValueError(f"Model '{target_model}' not found on provider at {clean_base} (HTTP 404).")
                elif resp.status_code in (401, 403):
                    raise PermissionError(f"Authentication failed (HTTP {resp.status_code}) for provider at {clean_base}.")
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if not choices or not isinstance(choices, list) or "message" not in choices[0]:
                    raise ValueError(f"Malformed completion response from {clean_base}: missing choices/message.")
                return choices[0]["message"].get("content", "").strip()
        except httpx.ConnectError as ce:
            raise ConnectionError(f"Connection refused to provider at {clean_base}: {ce}") from ce
        except httpx.TimeoutException as te:
            raise TimeoutError(f"Inference request to provider at {clean_base} timed out: {te}") from te


    async def discover_models(
        self,
        provider_type: str,
        base_url: str,
        api_key: str = "local",
        timeout: float = 3.0,
    ) -> ProviderDiscoveryResult:
        """Probe an endpoint and return discovered models without mutating state."""
        return await self.discover_models_for_endpoint(
            provider_type=provider_type,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )


