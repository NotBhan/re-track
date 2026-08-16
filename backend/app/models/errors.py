"""Custom exceptions for RE:Track (RefinedEngine Track) backend."""


class RETrackError(Exception):
    """Base exception for all RE:Track errors."""


# Backward compatibility alias
AndesContextError = RETrackError


class ConfigurationError(RETrackError):
    """Raised when configuration is invalid or incomplete."""


class OllamaConnectionError(RETrackError):
    """Raised when Ollama is unreachable."""


class ModelNotFoundError(RETrackError):
    """Raised when a required Ollama model is not available."""


class TokenizerError(RETrackError):
    """Raised when the HuggingFace tokenizer is missing or invalid."""


class CogneeServiceError(RETrackError):
    """Raised when a Cognee operation fails."""
