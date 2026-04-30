from __future__ import annotations

import importlib
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.schemas.api import AskSource, SearchHit
from app.schemas.document import (
    Block,
    Chunk,
    DocumentArtifact,
    DocumentMetadata,
    ImageInfo,
    ProcessingInfo,
    Section,
    SourceInfo,
    StructuredDocument,
    TableCell,
    TableData,
)
from app.search.store import CorpusIndex, IndexedChunk, SearchIndexStore
from app.storage.filesystem import FileStorage
from app.storage.manifest import CorpusManifest, CorpusManifestStore, ManifestRecord


EXPECTED_DOCUMENT_KEYS = {
    "metadata",
    "source",
    "sections",
    "blocks",
    "tables",
    "images",
    "chunks",
    "processing_info",
    "artifacts",
}

EXPECTED_METADATA_KEYS = {
    "document_id",
    "title",
    "language",
    "created_at",
    "processed_at",
    "page_count",
    "section_count",
    "block_count",
    "table_count",
    "image_count",
}

EXPECTED_SOURCE_KEYS = {
    "filename",
    "extension",
    "mime_type",
    "size_bytes",
    "checksum_sha256",
    "saved_path",
}

EXPECTED_BLOCK_KEYS = {
    "block_id",
    "type",
    "order",
    "text",
    "section_id",
    "page_num",
    "metadata",
}

EXPECTED_CHUNK_KEYS = {
    "chunk_id",
    "document_id",
    "section_id",
    "block_ids",
    "content_type",
    "source_type",
    "section_title",
    "section_path",
    "page_start",
    "page_end",
    "source_filename",
    "table_id",
    "table_title",
    "table_headers",
    "table_row_index",
    "table_column_values",
    "table_context",
    "row_count",
    "column_count",
    "text",
    "order",
    "token_estimate",
}

EXPECTED_PROCESSING_KEYS = {
    "extractor",
    "transform_version",
    "warnings",
    "features",
    "ocr_candidate",
    "ocr_reason",
    "source_encoding",
    "text_char_count",
    "text_block_count",
    "extractor_metadata",
}

EXPECTED_INDEX_KEYS = {
    "version",
    "updated_at",
    "document_count",
    "chunk_count",
    "avg_chunk_length",
    "doc_frequencies",
    "entries",
}

EXPECTED_INDEX_ENTRY_KEYS = {
    "document_id",
    "source_checksum",
    "filename",
    "source_filename",
    "source_type",
    "title",
    "chunk_id",
    "chunk_order",
    "section_id",
    "section_title",
    "section_path",
    "page_start",
    "page_end",
    "source_block_ids",
    "table_id",
    "table_row_index",
    "location_label",
    "citation_label",
    "text",
    "tokens",
    "normalized_tokens",
    "token_count",
}

EXPECTED_MANIFEST_KEYS = {
    "version",
    "updated_at",
    "records",
}

EXPECTED_MANIFEST_RECORD_KEYS = {
    "document_id",
    "filename",
    "checksum_sha256",
    "title",
    "extension",
    "extractor",
    "status",
    "processed_at",
    "warnings",
    "source_encoding",
}


def _sample_document() -> StructuredDocument:
    created_at = datetime(2026, 4, 28, 12, 0, 0)
    processed_at = datetime(2026, 4, 28, 12, 5, 0)
    return StructuredDocument(
        metadata=DocumentMetadata(
            document_id="doc-1",
            title="Sample Title",
            language="ru",
            created_at=created_at,
            processed_at=processed_at,
            page_count=2,
            section_count=2,
            block_count=2,
            table_count=1,
            image_count=1,
        ),
        source=SourceInfo(
            filename="sample.txt",
            extension=".txt",
            mime_type="text/plain",
            size_bytes=42,
            checksum_sha256="abc123",
            saved_path="/tmp/sample.txt",
        ),
        sections=[
            Section(
                section_id="sec-1",
                title="Intro",
                level=1,
                parent_id="sec-0",
                order=1,
                page_start=1,
                page_end=2,
                block_ids=["blk-1"],
            )
        ],
        blocks=[
            Block(
                block_id="blk-1",
                type="paragraph",
                order=1,
                text="Hello baseline",
                section_id="sec-1",
                page_num=1,
                metadata={"kind": "paragraph"},
            )
        ],
        tables=[
            TableData(
                table_id="tbl-1",
                order=1,
                section_id="sec-1",
                page_num=2,
                n_rows=1,
                n_cols=2,
                rows=[["a", "b"]],
                cells=[TableCell(row=0, column=0, value="a"), TableCell(row=0, column=1, value="b")],
            )
        ],
        images=[
            ImageInfo(
                image_id="img-1",
                order=1,
                page_num=2,
                section_id="sec-1",
                caption="Figure 1",
                metadata={"kind": "image"},
            )
        ],
        chunks=[
            Chunk(
                chunk_id="chk-1",
                document_id="doc-1",
                section_id="sec-1",
                block_ids=["blk-1"],
                text="Hello baseline",
                order=1,
                token_estimate=2,
            )
        ],
        processing_info=ProcessingInfo(
            extractor="txt",
            transform_version="baseline-v1",
            warnings=[],
            features={"tables_detected": True, "images_detected": True, "ocr_used": False},
            source_encoding="utf-8",
            text_char_count=14,
            text_block_count=1,
            extractor_metadata={"source_encoding": "utf-8"},
        ),
        artifacts=DocumentArtifact(
            result_json_path="/tmp/result.json",
            source_file_path="/tmp/sample.txt",
        ),
    )


def _use_tmp_storage(monkeypatch, tmp_path: Path) -> Path:
    storage_root = tmp_path / "storage"
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()
    return storage_root


def _fresh_app(monkeypatch, tmp_path: Path):
    _use_tmp_storage(monkeypatch, tmp_path)
    documents_module = importlib.import_module("app.api.routes.documents")
    importlib.reload(documents_module)
    main_module = importlib.import_module("app.main")
    importlib.reload(main_module)
    return main_module.app


def test_processed_document_contract_round_trip() -> None:
    document = _sample_document()
    payload = document.model_dump(mode="json")

    assert set(payload) == EXPECTED_DOCUMENT_KEYS
    assert set(payload["metadata"]) == EXPECTED_METADATA_KEYS
    assert set(payload["source"]) == EXPECTED_SOURCE_KEYS
    assert set(payload["blocks"][0]) == EXPECTED_BLOCK_KEYS
    assert set(payload["chunks"][0]) == EXPECTED_CHUNK_KEYS
    assert set(payload["processing_info"]) == EXPECTED_PROCESSING_KEYS
    assert payload["processing_info"]["ocr_candidate"] is False
    assert payload["processing_info"]["ocr_reason"] is None

    restored = StructuredDocument.model_validate(payload)
    assert restored.model_dump(mode="json") == payload


def test_chunk_contract_is_backward_compatible_with_old_payload() -> None:
    payload = {
        "chunk_id": "chk-old",
        "document_id": "doc-old",
        "section_id": "sec-1",
        "block_ids": ["blk-1"],
        "text": "Old chunk payload",
        "order": 1,
        "token_estimate": 3,
    }

    chunk = Chunk.model_validate(payload)

    assert chunk.content_type is None
    assert chunk.source_type is None
    assert chunk.section_title is None
    assert chunk.section_path == []
    assert chunk.page_start is None
    assert chunk.page_end is None
    assert chunk.source_filename is None
    assert chunk.table_id is None
    assert chunk.table_title is None
    assert chunk.table_headers == []
    assert chunk.table_row_index is None
    assert chunk.table_column_values == {}
    assert chunk.table_context is None
    assert chunk.row_count is None
    assert chunk.column_count is None


def test_search_and_ask_source_schemas_are_backward_compatible_with_old_payloads() -> None:
    search_hit = SearchHit.model_validate(
        {
            "document_id": "doc-old",
            "title": "Old",
            "filename": "old.txt",
            "score": 1.0,
            "chunk_id": "chk-old",
            "section_id": "sec-1",
            "section_title": "Intro",
            "snippet": "Old snippet",
        }
    )
    ask_source = AskSource.model_validate(
        {
            "rank": 1,
            "score": 1.0,
            "document_id": "doc-old",
            "filename": "old.txt",
            "title": "Old",
            "chunk_id": "chk-old",
            "section_id": "sec-1",
            "section_title": "Intro",
            "snippet": "Old snippet",
        }
    )

    assert search_hit.source_filename is None
    assert search_hit.section_path == []
    assert search_hit.source_block_ids == []
    assert search_hit.location_label is None
    assert ask_source.source_filename is None
    assert ask_source.section_path == []
    assert ask_source.source_block_ids == []
    assert ask_source.citation_label is None


def test_corpus_index_contract_round_trip(tmp_path: Path, monkeypatch) -> None:
    storage_root = _use_tmp_storage(monkeypatch, tmp_path)
    try:
        storage = FileStorage()
        store = SearchIndexStore(storage)
        index = CorpusIndex(
            version="1",
            updated_at="2026-04-28T12:00:00",
            document_count=1,
            chunk_count=1,
            avg_chunk_length=2.0,
            doc_frequencies={"baseline": 1},
            entries=[
                IndexedChunk(
                    document_id="doc-1",
                    source_checksum="abc123",
                    filename="sample.txt",
                    source_filename="sample.txt",
                    source_type="txt",
                    title="Sample Title",
                    chunk_id="chk-1",
                    chunk_order=1,
                    section_id="sec-1",
                    section_title="Intro",
                    section_path=["Document", "Intro"],
                    page_start=1,
                    page_end=1,
                    source_block_ids=["blk-1"],
                    table_id=None,
                    table_row_index=None,
                    location_label="sample.txt - Document > Intro - page 1",
                    citation_label="sample.txt - Document > Intro - page 1",
                    text="Hello baseline",
                    tokens=["hello", "baseline"],
                    normalized_tokens=["hello", "baseline"],
                    token_count=2,
                )
            ],
        )

        payload = index.model_dump(mode="json")
        assert set(payload) == EXPECTED_INDEX_KEYS
        assert set(payload["entries"][0]) == EXPECTED_INDEX_ENTRY_KEYS

        store.save(index)
        restored = store.load()
        assert restored.model_dump(mode="json") == payload
        assert storage.corpus_index_path.parent == storage_root / "index"
    finally:
        get_settings.cache_clear()


def test_indexed_chunk_contract_is_backward_compatible_with_old_payload() -> None:
    payload = {
        "document_id": "doc-old",
        "source_checksum": "abc123",
        "filename": "old.txt",
        "title": "Old",
        "chunk_id": "chk-old",
        "section_id": "sec-1",
        "section_title": "Intro",
        "text": "Old indexed text",
        "tokens": ["old", "indexed", "text"],
        "normalized_tokens": ["old", "indexed", "text"],
        "token_count": 3,
    }

    entry = IndexedChunk.model_validate(payload)

    assert entry.source_filename is None
    assert entry.source_type is None
    assert entry.chunk_order is None
    assert entry.section_path == []
    assert entry.page_start is None
    assert entry.page_end is None
    assert entry.source_block_ids == []
    assert entry.table_id is None
    assert entry.table_row_index is None
    assert entry.location_label is None
    assert entry.citation_label is None


def test_ingestion_manifest_contract_round_trip(tmp_path: Path, monkeypatch) -> None:
    storage_root = _use_tmp_storage(monkeypatch, tmp_path)
    try:
        storage = FileStorage()
        store = CorpusManifestStore(storage)
        manifest = CorpusManifest(
            version="1",
            updated_at="2026-04-28T12:00:00",
            records=[
                ManifestRecord(
                    document_id="doc-1",
                    filename="sample.txt",
                    checksum_sha256="abc123",
                    title="Sample Title",
                    extension=".txt",
                    extractor="txt",
                    status="processed",
                    processed_at="2026-04-28T12:05:00",
                    warnings=[],
                    source_encoding="utf-8",
                )
            ],
        )

        payload = manifest.model_dump(mode="json")
        assert set(payload) == EXPECTED_MANIFEST_KEYS
        assert set(payload["records"][0]) == EXPECTED_MANIFEST_RECORD_KEYS
        assert payload["records"][0]["status"] in {"processed", "duplicate"}

        store.save(manifest)
        restored = store.load()
        assert restored.model_dump(mode="json") == payload
        assert storage.index_dir / "ingestion_manifest.json" == storage_root / "index" / "ingestion_manifest.json"
    finally:
        get_settings.cache_clear()


def test_documents_api_shape(tmp_path: Path, monkeypatch) -> None:
    app = _fresh_app(monkeypatch, tmp_path)
    client = TestClient(app)
    try:
        storage = FileStorage()

        response = client.post(
            "/api/v1/documents/process",
            files={"file": ("api.txt", b"1. Intro\n\nHello API.", "text/plain")},
        )
        assert response.status_code == 200
        document = response.json()["document"]
        assert set(document) == EXPECTED_DOCUMENT_KEYS
        assert set(document["metadata"]) == EXPECTED_METADATA_KEYS
        assert document["source"]["filename"] == "api.txt"

        list_response = client.get("/api/v1/documents")
        assert list_response.status_code == 200
        documents = list_response.json()
        assert len(documents) == 1
        assert documents[0]["filename"] == "api.txt"
        assert set(documents[0]) == {"document_id", "title", "filename", "processed_at", "page_count"}

        document_id = document["metadata"]["document_id"]
        detail_response = client.get(f"/api/v1/documents/{document_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()["document"]
        assert detail["metadata"]["document_id"] == document_id
        assert detail["source"]["filename"] == "api.txt"
        assert set(detail["processing_info"]) == EXPECTED_PROCESSING_KEYS
        assert detail["processing_info"]["ocr_candidate"] is False
        assert detail["processing_info"]["ocr_reason"] is None
        assert Path(detail["artifacts"]["result_json_path"]).parent == storage.results_dir
        assert Path(detail["artifacts"]["source_file_path"]).parent == storage.uploads_dir

        assert len(list(storage.results_dir.glob("*.json"))) == 1
        assert len(list(storage.uploads_dir.glob("*.txt"))) == 1
    finally:
        get_settings.cache_clear()
