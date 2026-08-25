from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DocumentStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    doc_id: str
    title: str
    content_type: str
    byte_size: int
    tags: list[str] = field(default_factory=list)


@dataclass
class Document:
    metadata: DocumentMetadata
    raw_content: bytes
    status: DocumentStatus = DocumentStatus.DRAFT
    summary: Optional[str] = None
