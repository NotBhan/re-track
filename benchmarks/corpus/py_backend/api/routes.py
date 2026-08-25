from typing import Any, Optional

from application.processor import DocumentProcessor, ProcessResult
from domain.document import Document
from infrastructure.file_store import LocalFileStore, StandardDocumentParser


class DocumentRoutes:
    def __init__(self, processor: DocumentProcessor) -> None:
        self.processor = processor

    def create_document_route(self, doc_id: str, title: str, content: str) -> dict[str, Any]:
        raw_bytes = content.encode("utf-8")
        result: ProcessResult = self.processor.process_document(
            doc_id=doc_id,
            title=title,
            raw_bytes=raw_bytes,
        )
        return {
            "status": "success",
            "doc_id": result.doc_id,
            "extracted_length": result.extracted_length,
            "summary": result.summary,
        }

    def get_document_route(self, doc_id: str) -> dict[str, Any]:
        doc: Optional[Document] = self.processor.retrieve_document(doc_id)
        if not doc:
            return {"status": "not_found", "doc_id": doc_id}
        return {
            "status": "found",
            "doc_id": doc.metadata.doc_id,
            "title": doc.metadata.title,
            "byte_size": doc.metadata.byte_size,
            "summary": doc.summary,
        }
