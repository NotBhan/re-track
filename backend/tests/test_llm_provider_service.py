"""Unit tests for LLMProviderService model quality evaluation and quantization parsing."""

import pytest
from app.models.provider import ProviderType, QuantizationLevel
from app.services.llm_provider_service import LLMProviderService


def test_parse_quantization():
    assert LLMProviderService.parse_quantization("phi4-mini:q6_k") == QuantizationLevel.Q6_K
    assert LLMProviderService.parse_quantization("phi4:mini-q4_K_M") == QuantizationLevel.Q4_K_M
    assert LLMProviderService.parse_quantization("phi4-mini-fp16") == QuantizationLevel.FP16
    assert LLMProviderService.parse_quantization("custom-model:latest") == QuantizationLevel.UNKNOWN


def test_evaluate_model_quality_phi4_q6():
    service = LLMProviderService(default_model="phi4-mini:q6_k")
    info = service.evaluate_model_quality("phi4-mini:q6_k")
    assert info.is_phi4_mini is True
    assert info.is_q6_or_higher is True
    assert info.warning is None


def test_evaluate_model_quality_phi4_q4_warning():
    service = LLMProviderService(default_model="phi4-mini:q4_k_m")
    info = service.evaluate_model_quality("phi4-mini:q4_k_m")
    assert info.is_phi4_mini is True
    assert info.is_q6_or_higher is False
    assert info.warning is not None
    assert "Q6_K or higher is recommended" in info.warning


def test_evaluate_model_quality_non_phi4():
    service = LLMProviderService(default_model="llama3.2:3b")
    info = service.evaluate_model_quality("llama3.2:3b")
    assert info.is_phi4_mini is False
    assert info.warning is not None
    assert "not a phi4:mini variant" in info.warning
