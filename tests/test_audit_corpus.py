from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from app.core.config import get_settings


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _result_document(
    *,
    document_id: str,
    filename: str,
    extension: str,
    extractor: str,
    text_char_count,
    text_block_count,
    section_count: int,
    block_count: int,
    chunk_count: int,
    table_count: int = 0,
    image_count: int = 0,
    warnings: list[str] | None = None,
) -> dict:
    warnings = warnings or []
    return {
        "metadata": {
            "document_id": document_id,
            "title": f"Title {filename}",
            "language": "ru",
            "created_at": "2026-04-29T10:00:00",
            "processed_at": "2026-04-29T10:05:00",
            "page_count": None,
            "section_count": section_count,
            "block_count": block_count,
            "table_count": table_count,
            "image_count": image_count,
        },
        "source": {
            "filename": filename,
            "extension": extension,
            "mime_type": "text/plain" if extension == ".txt" else "application/pdf",
            "size_bytes": 123,
            "checksum_sha256": f"checksum-{document_id}",
            "saved_path": f"storage/uploads/{filename}",
        },
        "sections": [{"section_id": f"{document_id}-sec", "title": "Section", "level": 1, "order": 1, "block_ids": []}]
        if section_count
        else [],
        "blocks": [
            {
                "block_id": f"{document_id}-blk",
                "type": "paragraph",
                "order": 1,
                "text": "Some text",
                "section_id": f"{document_id}-sec" if section_count else None,
                "page_num": None,
                "metadata": {},
            }
        ]
        if block_count
        else [],
        "tables": [],
        "images": [],
        "chunks": [
            {
                "chunk_id": f"{document_id}-chk",
                "document_id": document_id,
                "section_id": f"{document_id}-sec" if section_count else None,
                "block_ids": [f"{document_id}-blk"] if block_count else [],
                "text": "Some text chunk",
                "order": 1,
                "token_estimate": 3,
            }
        ]
        if chunk_count
        else [],
        "processing_info": {
            "extractor": extractor,
            "transform_version": "baseline-v1",
            "warnings": warnings,
            "features": {"tables_detected": False, "images_detected": False, "ocr_used": False},
            "source_encoding": "utf-8",
            "text_char_count": text_char_count,
            "text_block_count": text_block_count,
            "extractor_metadata": {},
        },
        "artifacts": {
            "result_json_path": f"storage/results/{document_id}.json",
            "source_file_path": f"storage/uploads/{filename}",
        },
    }


def _prepare_storage(tmp_path: Path) -> tuple[Path, Path, Path]:
    storage_root = tmp_path / "storage"
    results_dir = storage_root / "results"
    index_dir = storage_root / "index"
    results_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    return storage_root, results_dir, index_dir


def _run_audit(monkeypatch, tmp_path: Path, report_path: Path | None = None, extra_args: list[str] | None = None) -> object:
    storage_root, _, _ = _prepare_storage(tmp_path)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()
    module = importlib.import_module("scripts.audit_corpus")
    importlib.reload(module)
    argv = ["audit_corpus"]
    if extra_args:
        argv.extend(extra_args)
    if report_path is not None:
        argv.extend(["--report-path", str(report_path)])
    monkeypatch.setattr(sys, "argv", argv)
    module.main()
    return module


def test_audit_corpus_builds_read_only_report(tmp_path: Path, monkeypatch, capsys) -> None:
    storage_root, results_dir, index_dir = _prepare_storage(tmp_path)

    doc_warning = _result_document(
        document_id="doc-warning",
        filename="warning.txt",
        extension=".txt",
        extractor="txt",
        text_char_count=42,
        text_block_count=1,
        section_count=1,
        block_count=1,
        chunk_count=1,
        warnings=["needs review"],
    )
    doc_zero_chunks = _result_document(
        document_id="doc-zero-chunks",
        filename="empty.pdf",
        extension=".pdf",
        extractor="pdf",
        text_char_count=900,
        text_block_count=2,
        section_count=1,
        block_count=2,
        chunk_count=0,
    )
    doc_missing_index = _result_document(
        document_id="doc-missing-index",
        filename="missing.txt",
        extension=".txt",
        extractor="txt",
        text_char_count=800,
        text_block_count=1,
        section_count=1,
        block_count=1,
        chunk_count=1,
    )
    doc_null_metrics = _result_document(
        document_id="doc-null-metrics",
        filename="legacy.txt",
        extension=".txt",
        extractor="txt",
        text_char_count=None,
        text_block_count=None,
        section_count=1,
        block_count=1,
        chunk_count=1,
    )

    results_payloads = [
        ("doc-warning.json", doc_warning),
        ("doc-zero-chunks.json", doc_zero_chunks),
        ("doc-missing-index.json", doc_missing_index),
        ("doc-null-metrics.json", doc_null_metrics),
    ]
    for filename, payload in results_payloads:
        _write_json(results_dir / filename, payload)

    _write_json(
        index_dir / "corpus_index.json",
        {
            "version": "1",
            "updated_at": "2026-04-29T10:10:00",
            "document_count": 3,
            "chunk_count": 3,
            "avg_chunk_length": 3.0,
            "doc_frequencies": {"some": 2},
            "entries": [
                {
                    "document_id": "doc-warning",
                    "source_checksum": "checksum-doc-warning",
                    "filename": "warning.txt",
                    "title": "Title warning.txt",
                    "chunk_id": "doc-warning-chk",
                    "section_id": "doc-warning-sec",
                    "section_title": "Section",
                    "text": "Some text chunk",
                    "tokens": ["some", "text", "chunk"],
                    "normalized_tokens": ["some", "text", "chunk"],
                    "token_count": 3,
                },
                {
                    "document_id": "doc-zero-chunks",
                    "source_checksum": "checksum-doc-zero-chunks",
                    "filename": "empty.pdf",
                    "title": "Title empty.pdf",
                    "chunk_id": "doc-zero-chunks-chk",
                    "section_id": "doc-zero-chunks-sec",
                    "section_title": "Section",
                    "text": "Some text chunk",
                    "tokens": ["some", "text", "chunk"],
                    "normalized_tokens": ["some", "text", "chunk"],
                    "token_count": 3,
                },
                {
                    "document_id": "doc-null-metrics",
                    "source_checksum": "checksum-doc-null-metrics",
                    "filename": "legacy.txt",
                    "title": "Title legacy.txt",
                    "chunk_id": "doc-null-metrics-chk",
                    "section_id": "doc-null-metrics-sec",
                    "section_title": "Section",
                    "text": "Some text chunk",
                    "tokens": ["some", "text", "chunk"],
                    "normalized_tokens": ["some", "text", "chunk"],
                    "token_count": 3,
                },
            ],
        },
    )
    _write_json(
        index_dir / "ingestion_manifest.json",
        {
            "version": "1",
            "updated_at": "2026-04-29T10:10:00",
            "records": [
                {
                    "document_id": "doc-warning",
                    "filename": "warning.txt",
                    "checksum_sha256": "checksum-doc-warning",
                    "title": "Title warning.txt",
                    "extension": ".txt",
                    "extractor": "txt",
                    "status": "processed",
                    "processed_at": "2026-04-29T10:05:00",
                    "warnings": ["needs review"],
                    "source_encoding": "utf-8",
                },
                {
                    "document_id": "doc-zero-chunks",
                    "filename": "empty.pdf",
                    "checksum_sha256": "checksum-doc-zero-chunks",
                    "title": "Title empty.pdf",
                    "extension": ".pdf",
                    "extractor": "pdf",
                    "status": "processed",
                    "processed_at": "2026-04-29T10:05:00",
                    "warnings": [],
                    "source_encoding": "utf-8",
                },
                {
                    "document_id": "doc-missing-index",
                    "filename": "missing.txt",
                    "checksum_sha256": "checksum-doc-missing-index",
                    "title": "Title missing.txt",
                    "extension": ".txt",
                    "extractor": "txt",
                    "status": "duplicate",
                    "processed_at": "2026-04-29T10:05:00",
                    "warnings": [],
                    "source_encoding": "utf-8",
                },
                {
                    "document_id": "doc-null-metrics",
                    "filename": "legacy.txt",
                    "checksum_sha256": "checksum-doc-null-metrics",
                    "title": "Title legacy.txt",
                    "extension": ".txt",
                    "extractor": "txt",
                    "status": "processed",
                    "processed_at": "2026-04-29T10:05:00",
                    "warnings": [],
                    "source_encoding": "utf-8",
                },
            ],
        },
    )

    report_path = tmp_path / "audit_report.json"
    before_results = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(results_dir.glob("*.json"))
    }
    before_index = (index_dir / "corpus_index.json").read_text(encoding="utf-8")
    before_manifest = (index_dir / "ingestion_manifest.json").read_text(encoding="utf-8")

    _run_audit(monkeypatch, tmp_path, report_path=report_path, extra_args=["--low-text-char-count", "500"])
    captured = capsys.readouterr()

    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_version"] == "stage8_corpus_quality_audit_v1"
    assert report["inputs"] == {
        "results_count": 4,
        "index_present": True,
        "manifest_present": True,
    }
    assert report["thresholds"] == {
        "low_text_char_count": 500,
        "min_chunks": 1,
        "min_blocks": 1,
        "min_sections": 1,
    }
    assert report["summary"]["total_documents"] == 4
    assert report["summary"]["indexed_documents"] == 3
    assert report["summary"]["indexed_chunks"] == 3
    assert report["summary"]["manifest_records"] == 4
    assert report["summary"]["by_extension"] == {".txt": 3, ".pdf": 1}
    assert report["summary"]["warnings_documents"] == 1
    assert report["summary"]["null_text_metric_documents"] == 1
    assert report["summary"]["low_text_documents"] == 1
    assert report["summary"]["no_chunk_documents"] == 1
    assert report["summary"]["no_block_documents"] == 0
    assert report["summary"]["no_section_documents"] == 0
    assert report["summary"]["missing_from_index_documents"] == 1
    assert report["summary"]["by_status"] == {"processed": 3, "duplicate": 1}
    assert report["summary"]["by_extractor"] == {"txt": 3, "pdf": 1}

    problem_documents = {item["document_id"]: item for item in report["problem_documents"]}
    assert problem_documents["doc-warning"]["tags"] == ["warnings", "low_text"]
    assert problem_documents["doc-warning"]["warnings"] == ["needs review"]
    assert problem_documents["doc-zero-chunks"]["tags"] == ["no_chunks"]
    assert problem_documents["doc-missing-index"]["tags"] == ["missing_from_index"]
    assert problem_documents["doc-null-metrics"]["tags"] == ["null_text_metrics"]
    assert "low_text" not in problem_documents["doc-null-metrics"]["tags"]

    assert "Corpus audit: documents=4 indexed=3 chunks=3 problems=4" in captured.out
    assert "Warnings=1 low_text=1 no_chunks=1 missing_from_index=1" in captured.out
    assert "Saved audit report to" in captured.out

    after_results = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(results_dir.glob("*.json"))
    }
    after_index = (index_dir / "corpus_index.json").read_text(encoding="utf-8")
    after_manifest = (index_dir / "ingestion_manifest.json").read_text(encoding="utf-8")
    assert after_results == before_results
    assert after_index == before_index
    assert after_manifest == before_manifest

    get_settings.cache_clear()


def test_audit_corpus_handles_missing_index_and_manifest(tmp_path: Path, monkeypatch, capsys) -> None:
    storage_root, results_dir, index_dir = _prepare_storage(tmp_path)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()

    _write_json(
        results_dir / "doc.json",
        _result_document(
            document_id="doc-only",
            filename="only.txt",
            extension=".txt",
            extractor="txt",
            text_char_count=10,
            text_block_count=1,
            section_count=1,
            block_count=1,
            chunk_count=1,
        ),
    )

    module = importlib.import_module("scripts.audit_corpus")
    importlib.reload(module)
    monkeypatch.setattr(sys, "argv", ["audit_corpus"])
    module.main()
    captured = capsys.readouterr()

    assert "indexed=0" in captured.out
    assert "missing_from_index=0" in captured.out
    assert "problems=1" in captured.out

    report = module.build_audit_report(storage_root)
    assert report["inputs"] == {
        "results_count": 1,
        "index_present": False,
        "manifest_present": False,
    }
    assert report["summary"]["indexed_documents"] == 0
    assert report["summary"]["indexed_chunks"] == 0
    assert report["summary"]["manifest_records"] == 0
    assert report["summary"]["missing_from_index_documents"] == 0

    get_settings.cache_clear()
