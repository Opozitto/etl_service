from __future__ import annotations

from app.services.document_service import DocumentService


def main() -> None:
    service = DocumentService()
    index = service.rebuild_corpus_index()
    print(
        f"Rebuilt corpus index: documents={index.document_count} chunks={index.chunk_count} updated_at={index.updated_at}"
    )


if __name__ == "__main__":
    main()
