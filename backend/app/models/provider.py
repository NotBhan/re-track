"""Data models for LLM Provider abstraction and active model inspection."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
class ProviderHealthStatus:
    """Health and model availability details for the configured provider."""

    provider: ProviderType
    base_url: str
    is_reachable: bool
    active_model: Optional[str] = None
    loaded_models: list[LoadedModelInfo] = field(default_factory=list)
    quantization_warning: Optional[str] = None
    discovery_status: DiscoveryStatus = DiscoveryStatus.NOT_CONFIGURED


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

