from __future__ import annotations

import importlib
import json
from pathlib import Path


def _load_export_module():
    module = importlib.import_module("app.evaluation.rag_chunk_export")
    return importlib.reload(module)


def _load_cli_module():
    module = importlib.import_module("scripts.export_rag_chunks")
    return importlib.reload(module)


def _document(**overrides) -> dict:
    base = {
        "metadata": {
            "document_id": "doc-1",
            "title": "Test document",
            "page_count": 3,
            "section_count": 2,
            "block_count": 3,
            "table_count": 1,
            "image_count": 0,
        },
        "source": {
            "filename": "test.pdf",
            "extension": ".pdf",
            "checksum_sha256": "abc",
        },
        "sections": [
            {"section_id": "sec-0", "title": "Document", "level": 0, "parent_id": None, "order": 0},
            {"section_id": "sec-1", "title": "1. Main", "level": 1, "parent_id": "sec-0", "order": 1},
            {"section_id": "sec-2", "title": "1.1 Detail", "level": 2, "parent_id": "sec-1", "order": 2},
        ],
        "blocks": [
            {
                "block_id": "blk-1",
                "type": "paragraph",
                "order": 1,
                "text": "Main text block",
                "section_id": "sec-2",
                "page_num": 2,
                "metadata": {},
            },
            {
                "block_id": "blk-2",
                "type": "paragraph",
                "order": 2,
                "text": "Next page block",
                "section_id": "sec-2",
                "page_num": 3,
                "metadata": {},
            },
            {
                "block_id": "tbl-block",
                "type": "table",
                "order": 3,
                "text": "a | b",
                "section_id": "sec-2",
                "page_num": 3,
                "metadata": {"table_id": "tbl-1"},
            },
        ],
        "tables": [{"table_id": "tbl-1", "order": 1, "section_id": "sec-2", "page_num": 3, "rows": []}],
        "images": [],
        "chunks": [
            {
                "chunk_id": "chk-1",
                "document_id": "doc-1",
                "section_id": "sec-2",
                "block_ids": ["blk-1", "blk-2"],
                "text": "This is a normal chunk with enough text to avoid the short chunk flag. "
                "It has two linked pages.",
                "order": 1,
                "token_estimate": 20,
            }
        ],
        "processing_info": {"ocr_candidate": False, "text_char_count": 100},
        "artifacts": {"result_json_path": "x"},
    }
    base.update(overrides)
    return base


def _write_doc(results_dir: Path, document: dict, name: str = "doc.json") -> Path:
    path = results_dir / name
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def test_section_path_derivation() -> None:
    module = _load_export_module()

    item = module.export_document_chunks(_document())[0]

    assert item["section_title"] == "1.1 Detail"
    assert item["section_path"] == ["Document", "1. Main", "1.1 Detail"]


def test_page_start_and_page_end_derivation_from_blocks() -> None:
    module = _load_export_module()

    item = module.export_document_chunks(_document())[0]

    assert item["page_start"] == 2
    assert item["page_end"] == 3


def test_content_type_derivation_from_block_types_and_table_like_chunks() -> None:
    module = _load_export_module()
    document = _document(
        chunks=[
            {
                "chunk_id": "chk-table",
                "document_id": "doc-1",
                "section_id": "sec-2",
                "block_ids": ["tbl-block"],
                "text": "Строка 2. pollutant | value",
                "order": 1,
                "token_estimate": 10,
            }
        ]
    )

    item = module.export_document_chunks(document)[0]

    assert item["content_type"] == "table_row"
    assert item["table_id"] == "tbl-1"
    assert "table_like_text" in item["quality_flags"]


def test_quality_flags_for_short_missing_page_and_missing_section() -> None:
    module = _load_export_module()
    document = _document(
        sections=[],
        blocks=[
            {
                "block_id": "blk-no-page",
                "type": "paragraph",
                "order": 1,
                "text": "Tiny",
                "section_id": "missing",
                "page_num": None,
                "metadata": {},
            }
        ],
        chunks=[
            {
                "chunk_id": "chk-short",
                "document_id": "doc-1",
                "section_id": "missing",
                "block_ids": ["blk-no-page"],
                "text": "Tiny",
                "order": 1,
                "token_estimate": 1,
            }
        ],
    )

    item = module.export_document_chunks(document)[0]

    assert {"short_chunk", "missing_page", "missing_section"}.issubset(set(item["quality_flags"]))


def test_cli_does_not_write_output_without_explicit_output_path(tmp_path: Path, capsys) -> None:
    cli = _load_cli_module()
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_doc(results_dir, _document())

    cli.main(["--results-dir", str(results_dir)])
    captured = capsys.readouterr()

    assert "Stage 29.1 RAG-ready chunk export" in captured.out
    assert not list(tmp_path.glob("*.json"))
    assert not (tmp_path / ".runtime_eval").exists()


def test_json_output_contract_with_explicit_output_path(tmp_path: Path) -> None:
    cli = _load_cli_module()
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_doc(results_dir, _document())
    output_path = tmp_path / "rag_chunks_preview.json"

    cli.main(["--results-dir", str(results_dir), "--output-path", str(output_path)])
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert report["taxonomy_version"] == "stage29_1_rag_chunk_export_v1"
    assert report["summary"]["documents_seen"] == 1
    assert report["summary"]["documents_with_chunks"] == 1
    assert report["summary"]["total_chunks"] == 1
    assert report["summary"]["exported_chunks"] == 1
    assert "summary" in report
    assert "items" in report
    assert "chunks" not in report
    assert report["summary"]["exported_chunks"] == len(report["items"])
    assert report["items"][0]["chunk_id"] == "chk-1"


def test_include_text_false_true_behavior() -> None:
    module = _load_export_module()
    document = _document()

    without_text = module.export_document_chunks(document, include_text=False)[0]
    with_text = module.export_document_chunks(document, include_text=True)[0]

    assert "text" not in without_text
    assert "text" in with_text
    assert with_text["text"] == document["chunks"][0]["text"]
