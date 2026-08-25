from typing import Optional

from domain.document import Document, DocumentMetadata, DocumentStatus
from domain.ports import DocumentParserPort, DocumentStorePort


class LocalFileStore(DocumentStorePort):
    def __init__(self, base_directory: str = "/tmp/documents") -> None:
        self.base_directory = base_directory
        self._memory_index: dict[str, Document] = {}

    def save(self, doc: Document) -> str:
        self._memory_index[doc.metadata.doc_id] = doc
        return doc.metadata.doc_id

    def load(self, doc_id: str) -> Optional[Document]:
        return self._memory_index.get(doc_id)

    def exists(self, doc_id: str) -> bool:
        return doc_id in self._memory_index


class StandardDocumentParser(DocumentParserPort):
    def extract_text(self, raw_bytes: bytes, content_type: str) -> str:
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return raw_bytes.decode("latin-1", errors="ignore")

    def compute_metadata(self, doc_id: str, raw_bytes: bytes, title: str) -> DocumentMetadata:
        return DocumentMetadata(
            doc_id=doc_id,
            title=title,
            content_type="text/plain",
            byte_size=len(raw_bytes),
            tags=["ingested", "standard"],
        )
