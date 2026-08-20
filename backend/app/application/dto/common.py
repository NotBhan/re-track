"""Common application DTOs."""

from typing import Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Structured error response for application use-case failures."""

    error: str = Field(description="Error type name")
    message: str = Field(description="Human-readable error message")
    success: bool = Field(default=False, description="Always False for errors")
    details: Optional[str] = Field(default=None, description="Additional error context")
