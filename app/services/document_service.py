from __future__ import annotations

import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.pipeline.extractors.registry import ExtractorRegistry
from app.pipeline.errors import ExtractionError
from app.pipeline.transform.structure import build_structure
from app.search.store import SearchIndexStore
from app.schemas.document import (
    DocumentArtifact,
    DocumentMetadata,
    ProcessingInfo,
    SourceInfo,
    StructuredDocument,
)
from app.storage.filesystem import FileStorage
from app.storage.manifest import CorpusManifestStore


OCR_STANDALONE_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
OCR_PDF_REASON = "possible_scanned_pdf"
OCR_IMAGE_REASON = "standalone_image"


@dataclass
class ProcessOutcome:
    document: StructuredDocument
    status: Literal["processed", "duplicate"]


class DocumentService:
    def __init__(self) -> None:
        self.registry = ExtractorRegistry()
        self.storage = FileStorage()
        self.index_store = SearchIndexStore(self.storage)
        self.manifest_store = CorpusManifestStore(self.storage)

    def process_path(self, path: Path) -> StructuredDocument:
        return self.process_path_with_status(path).document

    def process_path_with_status(self, path: Path) -> ProcessOutcome:
        original_checksum = self.storage.compute_checksum(path)
        existing = self.storage.find_by_checksum(original_checksum)
        if existing is not None:
            self.index_store.upsert_document(existing)
            self.manifest_store.upsert_document(existing, status="duplicate")
            return ProcessOutcome(document=existing, status="duplicate")

        extractor = self.registry.get_for_path(path)
        try:
            extracted = extractor.extract(path)
        except ExtractionError:
            raise
        except Exception as exc:
            raise ExtractionError(
                f"Failed to extract {path.name} with extractor {extractor.name}: {exc}",
                code="extract_failed",
            ) from exc
        document_id = str(uuid.uuid4())
        saved_source = self.storage.save_source(path, document_id)
        checksum = self.storage.compute_checksum(saved_source)

        sections, blocks, tables, images, chunks = build_structure(extracted)
        for chunk in chunks:
            chunk.document_id = document_id

        ocr_candidate, ocr_reason = self._detect_ocr_candidate(path, extracted, chunks)

        title = self._resolve_title(path, sections)
        metadata = DocumentMetadata(
            document_id=document_id,
            title=title,
            page_count=extracted.page_count,
            section_count=len(sections),
            block_count=len(blocks),
            table_count=len(tables),
            image_count=len(images),
        )
        source = SourceInfo(
            filename=path.name,
            extension=path.suffix.lower(),
            mime_type=mimetypes.guess_type(path.name)[0],
            size_bytes=saved_source.stat().st_size,
            checksum_sha256=checksum,
            saved_path=str(saved_source),
        )
        document = StructuredDocument(
            metadata=metadata,
            source=source,
            sections=sections,
            blocks=blocks,
            tables=tables,
            images=images,
            chunks=chunks,
            processing_info=ProcessingInfo(
                extractor=extractor.name,
                warnings=extracted.warnings,
                features={
                    "tables_detected": bool(tables),
                    "images_detected": bool(images),
                    "ocr_used": False,
                    "ocr_candidate": ocr_candidate,
                },
                ocr_candidate=ocr_candidate,
                ocr_reason=ocr_reason,
                source_encoding=extracted.metadata.get("source_encoding"),
                text_char_count=len(extracted.text),
                text_block_count=sum(1 for block in blocks if block.text),
                extractor_metadata=extracted.metadata,
            ),
            artifacts=DocumentArtifact(
                result_json_path="",
                source_file_path=str(saved_source),
            ),
        )

        result_path = self.storage.save_result(document)
        document.artifacts.result_json_path = str(result_path)
        self.storage.save_result(document)
        self.index_store.upsert_document(document)
        self.manifest_store.upsert_document(document, status="processed")
        return ProcessOutcome(document=document, status="processed")

    def get_document(self, document_id: str) -> StructuredDocument:
        return self.storage.load_result(document_id)

    def list_documents(self) -> list[StructuredDocument]:
        return [
            StructuredDocument.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self.storage.list_results()
        ]

    def rebuild_corpus_index(self):
        return self.index_store.rebuild()

    def corpus_stats(self) -> dict:
        index = self.index_store.load()
        manifest = self.manifest_store.load()
        return {
            "document_count": index.document_count,
            "chunk_count": index.chunk_count,
            "avg_chunk_length": round(index.avg_chunk_length, 2),
            "updated_at": index.updated_at,
            "manifest_record_count": len(manifest.records),
        }

    def manifest_records(self) -> list[dict]:
        manifest = self.manifest_store.load()
        return [record.model_dump(mode="json") for record in manifest.records]

    @staticmethod
    def _resolve_title(path: Path, sections: list) -> str:
        for section in sections:
            if section.level > 0 and section.title:
                return section.title
        return path.stem

    @staticmethod
    def _detect_ocr_candidate(path: Path, extracted, chunks: list) -> tuple[bool, str | None]:
        suffix = path.suffix.lower()
        if suffix in OCR_STANDALONE_IMAGE_SUFFIXES:
            return True, OCR_IMAGE_REASON

        if suffix == ".pdf":
            has_meaningful_text = bool((extracted.text or "").strip())
            if not has_meaningful_text and not chunks:
                return True, OCR_PDF_REASON

        return False, None
