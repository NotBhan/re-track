from api.routes import DocumentRoutes
from application.processor import DocumentProcessor
from infrastructure.file_store import LocalFileStore, StandardDocumentParser


def bootstrap_service() -> DocumentRoutes:
    store = LocalFileStore()
    parser = StandardDocumentParser()
    processor = DocumentProcessor(store=store, parser=parser)
    routes = DocumentRoutes(processor=processor)
    return routes


def main() -> None:
    routes = bootstrap_service()
    res = routes.create_document_route("DOC-1", "Architecture Blueprint", "System design details.")
    print("Bootstrap result:", res)


if __name__ == "__main__":
    main()
