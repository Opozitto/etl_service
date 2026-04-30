from __future__ import annotations

import importlib
import json
from pathlib import Path


def _load_quality_module():
    module = importlib.import_module("app.evaluation.rag_chunk_quality")
    return importlib.reload(module)


def _load_cli_module():
    module = importlib.import_module("scripts.audit_rag_chunks")
    return importlib.reload(module)


def _item(**overrides) -> dict:
    base = {
        "document_id": "doc-1",
        "filename": "doc-1.pdf",
        "chunk_id": "chunk-1",
        "order": 1,
        "content_type": "text",
        "section_id": "sec-1",
        "section_title": "Section",
        "page_start": 1,
        "page_end": 1,
        "table_id": None,
        "text": "This is a normal chunk with enough local context for a deterministic audit fixture.",
        "text_preview": "This is a normal chunk with enough local context for a deterministic audit fixture.",
        "quality_flags": [],
        "handoff_notes": [],
    }
    base.update(overrides)
    return base


def _processed_document() -> dict:
    return {
        "metadata": {"document_id": "doc-cli", "title": "CLI fixture"},
        "source": {"filename": "cli.pdf"},
        "sections": [{"section_id": "sec-1", "title": "Main", "parent_id": None}],
        "blocks": [
            {
                "block_id": "blk-1",
                "type": "paragraph",
                "text": "Tiny",
                "section_id": "sec-1",
                "page_num": 1,
                "metadata": {},
            }
        ],
        "tables": [],
        "chunks": [
            {
                "chunk_id": "chunk-cli",
                "document_id": "doc-cli",
                "section_id": "sec-1",
                "block_ids": ["blk-1"],
                "text": "Tiny",
                "order": 1,
            }
        ],
        "processing_info": {"ocr_candidate": False, "text_char_count": 4},
    }


def _write_doc(results_dir: Path, document: dict, name: str = "doc.json") -> Path:
    path = results_dir / name
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def test_audit_builds_from_synthetic_export_records() -> None:
    module = _load_quality_module()

    report = module.build_quality_audit_from_items([_item()])

    assert report["audit_version"] == "stage29_2_rag_chunk_quality_audit_v1"
    assert report["summary"]["audited_chunks"] == 1
    assert report["summary"]["documents_seen"] == 1
    assert report["summary"]["documents_with_chunks"] == 1
    assert report["issues"] == []
    assert "recommendations" in report
    assert "limitations" in report


def test_issue_flags_are_counted_correctly() -> None:
    module = _load_quality_module()
    long_text = "long text " * 25
    items = [
        _item(chunk_id="short", text="Tiny", text_preview="Tiny"),
        _item(chunk_id="long", text=long_text, text_preview=long_text),
        _item(chunk_id="missing-section", section_id=None, quality_flags=["missing_section"]),
        _item(chunk_id="missing-page", page_start=None, page_end=None, quality_flags=["missing_page"]),
        _item(
            chunk_id="table-like",
            text="pollutant | value | unit",
            text_preview="pollutant | value | unit",
            quality_flags=["table_like_text"],
        ),
        _item(chunk_id="unknown", content_type="unknown", quality_flags=["unknown_content_type"]),
    ]

    report = module.build_quality_audit_from_items(
        items,
        short_threshold=10,
        long_threshold=200,
        include_samples=True,
    )
    counts = report["summary"]["issue_counts"]

    assert counts["short_chunk"] == 1
    assert counts["long_chunk"] == 1
    assert counts["missing_section"] == 1
    assert counts["missing_page"] == 1
    assert counts["table_like_text_without_rich_context"] == 1
    assert counts["unknown_content_type"] == 1
    assert report["summary"]["table_like_chunk_count"] == 1
    assert report["summary"]["unknown_content_type_count"] == 1


def test_severity_aggregation_works() -> None:
    module = _load_quality_module()

    report = module.build_quality_audit_from_items(
        [
            _item(chunk_id="empty", text="", text_preview="", quality_flags=["empty_or_whitespace_text"]),
            _item(chunk_id="missing-page", page_start=None, page_end=None, quality_flags=["missing_page"]),
            _item(chunk_id="image", content_type="image", quality_flags=["image_or_ocr_limited"]),
        ]
    )

    assert report["summary"]["severity_counts"]["blocker"] == 1
    assert report["summary"]["severity_counts"]["warning"] >= 1
    assert report["summary"]["severity_counts"]["info"] >= 1


def test_per_document_issue_counts_work() -> None:
    module = _load_quality_module()

    report = module.build_quality_audit_from_items(
        [
            _item(document_id="doc-1", filename="a.pdf", chunk_id="a", text="Tiny", text_preview="Tiny"),
            _item(
                document_id="doc-2",
                filename="b.pdf",
                chunk_id="b",
                page_start=None,
                page_end=None,
                quality_flags=["missing_page"],
            ),
        ],
        short_threshold=10,
    )

    docs = {document["document_id"]: document for document in report["documents"]}
    assert docs["doc-1"]["issue_counts"]["short_chunk"] == 1
    assert docs["doc-2"]["issue_counts"]["missing_page"] == 1
    assert report["summary"]["documents_with_issues"] == 2


def test_samples_are_limited_per_issue() -> None:
    module = _load_quality_module()
    items = [_item(chunk_id=f"short-{index}", text="Tiny", text_preview="Tiny") for index in range(4)]

    report = module.build_quality_audit_from_items(
        items,
        short_threshold=10,
        include_samples=True,
        sample_limit_per_issue=2,
    )

    short_samples = [sample for sample in report["samples"] if sample["issue_code"] == "short_chunk"]
    assert len(short_samples) == 2


def test_samples_preserve_source_location_fields() -> None:
    module = _load_quality_module()

    report = module.build_quality_audit_from_items(
        [
            _item(
                text="Tiny",
                text_preview="Tiny",
                source_filename="source.pdf",
                chunk_order=4,
                section_path=["Document", "Section"],
                page_start=2,
                page_end=2,
                source_block_ids=["blk-1"],
                table_id="tbl-1",
                table_row_index=3,
                location_label="source.pdf - table tbl-1 - row 3 - page 2",
                citation_label="source.pdf - table tbl-1 - row 3 - page 2",
            )
        ],
        short_threshold=10,
        include_samples=True,
    )

    sample = report["samples"][0]
    assert sample["source_filename"] == "source.pdf"
    assert sample["chunk_order"] == 4
    assert sample["section_path"] == ["Document", "Section"]
    assert sample["page_start"] == 2
    assert sample["source_block_ids"] == ["blk-1"]
    assert sample["table_id"] == "tbl-1"
    assert sample["table_row_index"] == 3
    assert sample["citation_label"] == "source.pdf - table tbl-1 - row 3 - page 2"


def test_cli_does_not_write_output_without_explicit_output_path(tmp_path: Path, capsys) -> None:
    cli = _load_cli_module()
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_doc(results_dir, _processed_document())

    cli.main(["--results-dir", str(results_dir)])
    captured = capsys.readouterr()

    assert "Stage 29.2 chunk quality audit" in captured.out
    assert not list(tmp_path.glob("*.json"))
    assert not (tmp_path / ".runtime_eval").exists()


def test_cli_writes_json_report_with_explicit_output_path(tmp_path: Path) -> None:
    cli = _load_cli_module()
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_doc(results_dir, _processed_document())
    output_path = tmp_path / "rag_chunk_quality.json"

    cli.main(["--results-dir", str(results_dir), "--output-path", str(output_path), "--include-samples"])
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert report["audit_version"] == "stage29_2_rag_chunk_quality_audit_v1"
    assert report["summary"]["documents_seen"] == 1
    assert report["summary"]["audited_chunks"] == 1
    assert "summary" in report
    assert "issues" in report
    assert "documents" in report
    assert "samples" in report
    assert "recommendations" in report
    assert "limitations" in report


def test_report_recommendations_and_limitations_are_present() -> None:
    module = _load_quality_module()

    report = module.build_quality_audit_from_items([_item()])

    assert any("Stage 30" in recommendation for recommendation in report["recommendations"])
    assert any("Stage 31" in recommendation for recommendation in report["recommendations"])
    assert any("Stage 32" in recommendation for recommendation in report["recommendations"])
    assert any("No OCR" in limitation for limitation in report["limitations"])


def test_audit_accepts_stage30_source_filename_records() -> None:
    module = _load_quality_module()

    report = module.build_quality_audit_from_items(
        [
            _item(
                filename="",
                source_filename="stage30.pdf",
                source_type="pdf",
                section_path=["Document", "Section"],
            )
        ]
    )

    assert report["documents"][0]["filename"] == "stage30.pdf"
    assert report["summary"]["content_type_counts"]["text"] == 1


def test_rich_stage31_table_context_is_not_flagged_as_poor_table_context() -> None:
    module = _load_quality_module()

    report = module.build_quality_audit_from_items(
        [
            _item(
                chunk_id="rich-table",
                content_type="table_row",
                table_id=None,
                table_context="Таблица tbl-1: Расчет выбросов",
                table_headers=["Код", "Вещество"],
                table_column_values={"Код": "0301", "Вещество": "Азота диоксид"},
                text="Таблица tbl-1: Расчет выбросов. Строка 2 из 2. Колонки: Код: 0301; Вещество: Азота диоксид",
                text_preview="Таблица tbl-1: Расчет выбросов. Строка 2 из 2. Колонки: Код: 0301; Вещество: Азота диоксид",
                quality_flags=["table_like_text"],
            )
        ],
        short_threshold=10,
    )

    assert "table_like_text_without_rich_context" not in report["summary"]["issue_counts"]
    assert report["summary"]["table_like_chunk_count"] == 1
