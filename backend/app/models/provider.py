"""Data models for LLM Provider abstraction and active model inspection."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ProviderType(str, Enum):
    """Supported LLM inference provider backends."""

    OLLAMA = "ollama"
    LM_STUDIO = "lmstudio"
    OPENAI_COMPATIBLE = "openai_compatible"


class QuantizationLevel(str, Enum):
    """Detected quantization tiers for local models."""

    Q4_K_M = "q4_k_m"
    Q4_0 = "q4_0"
    Q5_K_M = "q5_k_m"
    Q6_K = "q6_k"
    Q8_0 = "q8_0"
    FP16 = "fp16"
    UNKNOWN = "unknown"


class DiscoveryStatus(str, Enum):
    """Fine-grained discovery and reachability status."""

    AVAILABLE = "available"
    REACHABLE_BUT_EMPTY = "reachable_but_empty"
    UNREACHABLE = "unreachable"
    DISCOVERY_FAILED = "discovery_failed"
    NOT_CONFIGURED = "not_configured"


@dataclass
class LoadedModelInfo:
    """Information about an active or discovered model in the provider."""

    model_id: str
    name: str
    quantization: QuantizationLevel = QuantizationLevel.UNKNOWN
    is_phi4_mini: bool = False
    is_q6_or_higher: bool = False
    warning: Optional[str] = None


@dataclass
class ModelCapabilities:
    """Probed runtime capabilities for a model endpoint."""

    model: str
    chat: str = "unknown"
    tool_calling: str = "unknown"
    json_mode: str = "unknown"
    reasoning: str = "unknown"
    embeddings: str = "not_tested"
    context_window: Optional[int] = None
    embedding_model: Optional[str] = None
    provider: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert capabilities to dictionary format."""
        d: dict[str, Any] = {
            "model": self.model,
            "chat": self.chat,
            "tool_calling": self.tool_calling,
            "json_mode": self.json_mode,
            "reasoning": self.reasoning,
            "embeddings": self.embeddings,
        }
        if self.context_window is not None:
            d["context_window"] = self.context_window
        if self.embedding_model is not None:
            d["embedding_model"] = self.embedding_model
        if self.provider is not None:
            d["provider"] = self.provider
        return d


class CapabilityStatus(str, Enum):
    """Status tiers for probed model capabilities."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"
    NOT_TESTED = "not_tested"


@dataclass
class ProviderHealthStatus:
    """Health and model availability details for the configured provider."""

    provider: ProviderType
    base_url: str
    is_reachable: bool
    active_model: Optional[str] = None
    loaded_models: list[LoadedModelInfo] = field(default_factory=list)
    quantization_warning: Optional[str] = None
    discovery_status: DiscoveryStatus = DiscoveryStatus.NOT_CONFIGURED
    capabilities: Optional[dict[str, Any]] = None


@dataclass
class ProviderDiscoveryResult:
    """Detailed result of a non-mutating model discovery probe."""

    provider: ProviderType
    base_url: str
    is_reachable: bool
    status: DiscoveryStatus
    models: list[LoadedModelInfo] = field(default_factory=list)
    message: str = ""
    error_details: Optional[str] = None


