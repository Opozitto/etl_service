from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.document import StructuredDocument
from app.storage.filesystem import FileStorage


class ManifestRecord(BaseModel):
    document_id: str
    filename: str
    checksum_sha256: str
    title: str
    extension: str
    extractor: str
    status: str
    processed_at: str
    warnings: list[str] = Field(default_factory=list)
    source_encoding: Optional[str] = None


class CorpusManifest(BaseModel):
    version: str = "1"
    updated_at: str
    records: list[ManifestRecord] = Field(default_factory=list)


class CorpusManifestStore:
    def __init__(self, storage: Optional[FileStorage] = None) -> None:
        self.storage = storage or FileStorage()
        self.path = self.storage.index_dir / "ingestion_manifest.json"

    def load(self) -> CorpusManifest:
        if not self.path.exists():
            return self.rebuild()
        try:
            manifest = CorpusManifest.model_validate(self.storage.read_json(self.path))
        except Exception:
            return self.rebuild()
        if not manifest.records and self.storage.list_results():
            return self.rebuild()
        return manifest

    def save(self, manifest: CorpusManifest) -> CorpusManifest:
        self.storage.write_json(self.path, manifest.model_dump(mode="json"))
        return manifest

    def rebuild(self) -> CorpusManifest:
        records: list[ManifestRecord] = []
        for path in self.storage.list_results():
            document = StructuredDocument.model_validate_json(path.read_text(encoding="utf-8"))
            records.append(
                ManifestRecord(
                    document_id=document.metadata.document_id,
                    filename=document.source.filename,
                    checksum_sha256=document.source.checksum_sha256,
                    title=document.metadata.title,
                    extension=document.source.extension,
                    extractor=document.processing_info.extractor,
                    status="processed",
                    processed_at=document.metadata.processed_at.isoformat(),
                    warnings=document.processing_info.warnings,
                    source_encoding=document.processing_info.source_encoding,
                )
            )
        manifest = CorpusManifest(
            updated_at=datetime.utcnow().isoformat(),
            records=sorted(records, key=lambda item: (item.filename.lower(), item.processed_at)),
        )
        return self.save(manifest)

    def upsert_document(self, document: StructuredDocument, status: str) -> CorpusManifest:
        manifest = self.load()
        records = [
            record
            for record in manifest.records
            if not (
                record.checksum_sha256 == document.source.checksum_sha256
                and record.filename.lower() == document.source.filename.lower()
            )
        ]
        records.append(
            ManifestRecord(
                document_id=document.metadata.document_id,
                filename=document.source.filename,
                checksum_sha256=document.source.checksum_sha256,
                title=document.metadata.title,
                extension=document.source.extension,
                extractor=document.processing_info.extractor,
                status=status,
                processed_at=document.metadata.processed_at.isoformat(),
                warnings=document.processing_info.warnings,
                source_encoding=document.processing_info.source_encoding,
            )
        )
        manifest.records = sorted(records, key=lambda item: (item.filename.lower(), item.processed_at))
        manifest.updated_at = datetime.utcnow().isoformat()
        return self.save(manifest)
