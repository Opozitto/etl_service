from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.extraction.tables import (
    build_table_evidence_report,
    evaluate_tables_from_documents,
    extract_table_evidence_from_document,
)
from app.schemas.document import (
    Block,
    Chunk,
    DocumentArtifact,
    DocumentMetadata,
    ProcessingInfo,
    Section,
    SourceInfo,
    StructuredDocument,
    TableData,
)


def _document(
    rows: list[list[str]],
    *,
    document_id: str = "doc-1",
    filename: str = "tables.xlsx",
    section_title: str = "Расчет выбросов",
    table_id: str = "tbl-1",
    block_id: str = "blk-1",
    chunk_id: str = "chk-1",
) -> StructuredDocument:
    created_at = datetime(2026, 4, 30, 10, 0, 0)
    text = "\n".join(" | ".join(row) for row in rows)
    return StructuredDocument(
        metadata=DocumentMetadata(
            document_id=document_id,
            title=filename,
            created_at=created_at,
            processed_at=created_at,
            section_count=1,
            block_count=1,
            table_count=1,
        ),
        source=SourceInfo(
            filename=filename,
            extension=Path(filename).suffix.lower(),
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=100,
            checksum_sha256=f"checksum-{document_id}",
        ),
        sections=[
            Section(
                section_id="sec-1",
                title=section_title,
                level=1,
                order=1,
                page_start=2,
                page_end=2,
                block_ids=[block_id],
            )
        ],
        blocks=[
            Block(
                block_id=block_id,
                type="table",
                order=1,
                text=text,
                section_id="sec-1",
                page_num=2,
                metadata={"table_id": table_id, "sheet_name": "Лист1"},
            )
        ],
        tables=[
            TableData(
                table_id=table_id,
                order=1,
                section_id="sec-1",
                page_num=2,
                n_rows=len(rows),
                n_cols=max((len(row) for row in rows), default=0),
                rows=rows,
                cells=[],
            )
        ],
        chunks=[
            Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                section_id="sec-1",
                block_ids=[block_id],
                text=f"Таблица: {section_title}. {text}",
                order=1,
                token_estimate=20,
            )
        ],
        processing_info=ProcessingInfo(
            extractor="xlsx",
            warnings=[],
            features={"tables_detected": True},
            source_encoding=None,
            text_char_count=len(text),
            text_block_count=1,
            extractor_metadata={},
        ),
        artifacts=DocumentArtifact(result_json_path="", source_file_path=""),
    )


def _write_document(results_dir: Path, document: StructuredDocument) -> Path:
    path = results_dir / f"{document.metadata.document_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_detects_emissions_and_pollutants_table_by_headers() -> None:
    document = _document(
        [
            ["Код", "Загрязняющее вещество", "Выброс г/с", "Выброс т/год"],
            ["0301", "Азота диоксид", "0.12", "1.4"],
        ]
    )

    records = extract_table_evidence_from_document(document)

    assert len(records) == 1
    record = records[0]
    assert record.category in {"emissions", "pollutants"}
    assert "emissions" in record.tags
    assert "pollutants" in record.tags
    assert record.score >= 0.7
    assert record.headers == ["Код", "Загрязняющее вещество", "Выброс г/с", "Выброс т/год"]
    assert record.row_count == 2
    assert record.column_count == 4


def test_detects_limits_or_norms_table_by_pdk_pdv_terms() -> None:
    document = _document(
        [
            ["Вещество", "ПДК", "ПДВ", "Доля ПДК"],
            ["Сера диоксид", "0.5", "0.03", "0.6"],
        ],
        section_title="Нормативы и лимиты",
    )

    record = extract_table_evidence_from_document(document)[0]

    assert record.category == "limits_or_norms"
    assert {"пдк", "пдв", "доля пдк"} <= set(record.matched_terms)
    assert "domain_header_match" in record.reason_codes


def test_detects_costs_or_resources_table() -> None:
    document = _document(
        [
            ["Сырье", "Материал", "Расход", "Затраты"],
            ["Известь", "кг", "120", "5000"],
        ],
        section_title="Материальные ресурсы",
    )

    record = extract_table_evidence_from_document(document)[0]

    assert record.category == "costs_or_resources"
    assert {"сырье", "материал", "расход", "затраты"} <= set(record.matched_terms)
    assert record.score >= 0.7


def test_neutral_table_gets_unknown_or_low_score() -> None:
    document = _document([["Имя", "Комментарий"], ["А", "Общие сведения"]], section_title="Справочник")

    low_threshold_records = extract_table_evidence_from_document(document, min_score=0.0)
    high_threshold_records = extract_table_evidence_from_document(document, min_score=0.45)

    assert low_threshold_records[0].category == "unknown"
    assert low_threshold_records[0].score < 0.45
    assert high_threshold_records == []


def test_source_fields_preview_and_counts_are_preserved() -> None:
    document = _document(
        [
            ["Источник выбросов", "Оборудование", "Газоочистка"],
            ["Труба 1", "Котел", "Циклон"],
            ["Труба 2", "Печь", "Фильтр"],
        ],
        filename="sources.xlsx",
    )

    record = extract_table_evidence_from_document(document)[0]

    assert record.document_id == "doc-1"
    assert record.filename == "sources.xlsx"
    assert record.table_id == "tbl-1"
    assert record.block_id == "blk-1"
    assert record.chunk_id == "chk-1"
    assert record.source_type == "table"
    assert record.section_id == "sec-1"
    assert record.section_title == "Расчет выбросов"
    assert record.page == 2
    assert record.row_count == 3
    assert record.column_count == 3
    assert record.preview_rows == document.tables[0].rows
    assert record.category == "sources_or_equipment"
    assert record.snippet


def test_duplicate_table_evidence_is_bounded() -> None:
    first = _document([["ПДК", "ПДВ"], ["0.1", "0.2"]], document_id="doc-1")
    duplicate = _document([["ПДК", "ПДВ"], ["0.1", "0.2"]], document_id="doc-1")

    records = evaluate_tables_from_documents([first, duplicate])

    assert len(records) == 1


def test_report_summary_counts_categories_and_max_tables() -> None:
    first = _document([["ПДК", "ПДВ"], ["0.1", "0.2"]], document_id="doc-1")
    second = _document([["Сырье", "Затраты"], ["Песок", "100"]], document_id="doc-2")

    report = build_table_evidence_report([first, second], Path("results"), max_tables=1)

    assert report["report_version"] == "stage23_table_evidence_v1"
    assert report["summary"]["documents_seen"] == 2
    assert report["summary"]["documents_with_tables"] == 2
    assert report["summary"]["tables_seen"] == 2
    assert report["summary"]["candidate_tables"] == 1
    assert len(report["tables"]) == 1


def test_cli_is_read_only_and_writes_report_only_when_requested(tmp_path: Path, monkeypatch, capsys) -> None:
    storage_root = tmp_path / "storage"
    results_dir = storage_root / "results"
    index_dir = storage_root / "index"
    uploads_dir = storage_root / "uploads"
    results_dir.mkdir(parents=True)
    index_dir.mkdir(parents=True)
    uploads_dir.mkdir(parents=True)
    _write_document(results_dir, _document([["ПДК", "ПДВ"], ["0.1", "0.2"]]))
    index_probe = index_dir / "probe.txt"
    uploads_probe = uploads_dir / "probe.txt"
    index_probe.write_text("index", encoding="utf-8")
    uploads_probe.write_text("uploads", encoding="utf-8")
    before_results = {path.name: path.read_text(encoding="utf-8") for path in results_dir.glob("*")}
    before_index = {path.name: path.read_text(encoding="utf-8") for path in index_dir.glob("*")}
    before_uploads = {path.name: path.read_text(encoding="utf-8") for path in uploads_dir.glob("*")}

    module = importlib.import_module("scripts.evaluate_tables")
    importlib.reload(module)
    monkeypatch.setattr(sys, "argv", ["evaluate_tables", "--results-dir", str(results_dir)])
    module.main()
    captured = capsys.readouterr()

    assert "Stage 23 table-aware evidence evaluation" in captured.out
    assert "documents_seen=1" in captured.out
    assert "documents_with_tables=1" in captured.out
    assert "tables_seen=1" in captured.out
    assert "candidate_tables=1" in captured.out
    assert "deterministic source-backed table evidence only" in captured.out
    assert len(list((tmp_path / "reports").glob("*.json"))) == 0
    assert {path.name: path.read_text(encoding="utf-8") for path in results_dir.glob("*")} == before_results
    assert {path.name: path.read_text(encoding="utf-8") for path in index_dir.glob("*")} == before_index
    assert {path.name: path.read_text(encoding="utf-8") for path in uploads_dir.glob("*")} == before_uploads

    report_path = tmp_path / "reports" / "table_evidence_v1.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["evaluate_tables", "--results-dir", str(results_dir), "--json-report-path", str(report_path)],
    )
    module.main()

    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_version"] == "stage23_table_evidence_v1"
    assert report["summary"]["candidate_tables"] == 1
    assert report["tables"][0]["document_id"] == "doc-1"


def test_tables_api_returns_candidates_and_filters(tmp_path: Path, monkeypatch) -> None:
    storage_root = tmp_path / "storage"
    results_dir = storage_root / "results"
    results_dir.mkdir(parents=True)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()
    _write_document(results_dir, _document([["ПДК", "ПДВ"], ["0.1", "0.2"]], document_id="doc-api-1"))
    _write_document(results_dir, _document([["Сырье", "Затраты"], ["Песок", "100"]], document_id="doc-api-2"))

    documents_module = importlib.import_module("app.api.routes.documents")
    importlib.reload(documents_module)
    main_module = importlib.import_module("app.main")
    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.get("/api/v1/corpus/tables")
    assert response.status_code == 200
    payload = response.json()
    assert payload["report_version"] == "stage23_table_evidence_v1"
    assert payload["summary"]["documents_seen"] == 2
    assert payload["summary"]["tables_seen"] == 2
    assert payload["summary"]["candidate_tables"] == 2
    assert payload["tables"][0]["source_type"] == "table"

    filtered = client.get("/api/v1/corpus/tables", params={"category": "costs_or_resources", "max_tables": 1})
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["summary"]["candidate_tables"] == 1
    assert filtered_payload["tables"][0]["category"] == "costs_or_resources"

    get_settings.cache_clear()
