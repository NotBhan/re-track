from dataclasses import dataclass
from typing import Optional

from domain.document import Document, DocumentMetadata, DocumentStatus
from domain.ports import DocumentParserPort, DocumentStorePort


@dataclass
class ProcessResult:
    doc_id: str
    status: DocumentStatus
    extracted_length: int
    summary: Optional[str] = None


class DocumentProcessor:
    def __init__(self, store: DocumentStorePort, parser: DocumentParserPort) -> None:
        self._store = store
        self._parser = parser

    def process_document(self, doc_id: str, title: str, raw_bytes: bytes, content_type: str = "text/plain") -> ProcessResult:
        meta = self._parser.compute_metadata(doc_id, raw_bytes, title)
        text = self._parser.extract_text(raw_bytes, content_type)
        summary = text[:100] if len(text) > 100 else text

        doc = Document(
            metadata=meta,
            raw_content=raw_bytes,
            status=DocumentStatus.PROCESSED,
            summary=summary,
        )
        self._store.save(doc)

        return ProcessResult(
            doc_id=doc_id,
            status=doc.status,
            extracted_length=len(text),
            summary=summary,
        )

    def retrieve_document(self, doc_id: str) -> Optional[Document]:
        return self._store.load(doc_id)
