from abc import ABC, abstractmethod
from typing import Optional

from domain.document import Document, DocumentMetadata


class DocumentStorePort(ABC):
    @abstractmethod
    def save(self, doc: Document) -> str:
        raise NotImplementedError

    @abstractmethod
    def load(self, doc_id: str) -> Optional[Document]:
        raise NotImplementedError

    @abstractmethod
    def exists(self, doc_id: str) -> bool:
        raise NotImplementedError


class DocumentParserPort(ABC):
    @abstractmethod
    def extract_text(self, raw_bytes: bytes, content_type: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def compute_metadata(self, doc_id: str, raw_bytes: bytes, title: str) -> DocumentMetadata:
        raise NotImplementedError
