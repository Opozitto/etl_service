from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from app.core.config import get_settings


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_storage(tmp_path: Path) -> tuple[Path, Path, Path]:
    storage_root = tmp_path / "storage"
    results_dir = storage_root / "results"
    index_dir = storage_root / "index"
    results_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)
    return storage_root, results_dir, index_dir


def _result_document(
    document_id: str,
    filename: str,
    *,
    text: str,
    table_count: int = 0,
    image_count: int = 0,
    ocr_used: bool = False,
    ocr_engine: str | None = None,
    ocr_status: str = "not_applicable",
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
            "page_count": 1,
            "section_count": 1,
            "block_count": 1,
            "table_count": table_count,
            "image_count": image_count,
        },
        "source": {
            "filename": filename,
            "extension": Path(filename).suffix.lower(),
            "mime_type": "text/plain",
            "size_bytes": 123,
            "checksum_sha256": f"checksum-{document_id}",
            "saved_path": f"storage/uploads/{filename}",
        },
        "sections": [
            {
                "section_id": f"{document_id}-sec",
                "title": "Section",
                "level": 1,
                "order": 1,
                "block_ids": [f"{document_id}-blk"],
            }
        ],
        "blocks": [
            {
                "block_id": f"{document_id}-blk",
                "type": "paragraph",
                "order": 1,
                "text": text,
                "section_id": f"{document_id}-sec",
                "page_num": None,
                "metadata": {},
            }
        ],
        "tables": [],
        "images": [],
        "chunks": [
            {
                "chunk_id": f"{document_id}-chk",
                "document_id": document_id,
                "section_id": f"{document_id}-sec",
                "block_ids": [f"{document_id}-blk"],
                "text": text,
                "order": 1,
                "token_estimate": 10,
            }
        ],
        "processing_info": {
            "extractor": "txt",
            "transform_version": "baseline-v1",
            "warnings": warnings,
            "features": {
                "tables_detected": table_count > 0,
                "images_detected": image_count > 0,
                "ocr_used": ocr_used,
                "ocr_engine": ocr_engine,
                "ocr_text_length": len(text) if ocr_used else 0,
                "ocr_status": ocr_status,
            },
            "source_encoding": "utf-8",
            "text_char_count": len(text),
            "text_block_count": 1,
            "extractor_metadata": {},
        },
        "artifacts": {
            "result_json_path": f"storage/results/{document_id}.json",
            "source_file_path": f"storage/uploads/{filename}",
        },
    }


def _index_payload() -> dict:
    return {
        "version": "1",
        "updated_at": "2026-04-29T10:10:00",
        "document_count": 2,
        "chunk_count": 2,
        "avg_chunk_length": 10.0,
        "doc_frequencies": {
            "эколог": 1,
            "проект": 1,
            "выброс": 1,
            "пдв": 1,
            "сырье": 1,
            "калькуляц": 1,
            "лист": 1,
            "строк": 1,
        },
        "entries": [
            {
                "document_id": "doc-1",
                "source_checksum": "checksum-doc-1",
                "filename": "sample.docx",
                "title": "Title sample.docx",
                "chunk_id": "doc-1-chk",
                "section_id": "doc-1-sec",
                "section_title": "Section",
                "text": "Экология проект. Предельно допустимые выбросы ПДВ.",
                "tokens": ["Экология", "проект", "Предельно", "допустимые", "выбросы", "ПДВ"],
                "normalized_tokens": ["эколог", "проект", "предельно", "допустимые", "выброс", "пдв"],
                "token_count": 6,
            },
            {
                "document_id": "doc-2",
                "source_checksum": "checksum-doc-2",
                "filename": "table.xlsx",
                "title": "Title table.xlsx",
                "chunk_id": "doc-2-chk",
                "section_id": "doc-2-sec",
                "section_title": "Section",
                "text": "Лист 1. Строка 0101. Форма 2 Плановая калькуляция затрат. Приобретение сырья и материалов.",
                "tokens": ["Лист", "1", "Строка", "0101", "Форма", "2", "Плановая", "калькуляция", "затрат", "Приобретение", "сырья", "и", "материалов"],
                "normalized_tokens": ["лист", "1", "строк", "0101", "форма", "2", "плановая", "калькуляц", "затрат", "приобретение", "сырье", "материалов"],
                "token_count": 13,
            },
        ],
    }


def _manifest_payload() -> dict:
    return {
        "version": "1",
        "updated_at": "2026-04-29T10:10:00",
        "records": [
            {
                "document_id": "doc-1",
                "filename": "sample.docx",
                "checksum_sha256": "checksum-doc-1",
                "title": "Title sample.docx",
                "extension": ".docx",
                "extractor": "txt",
                "status": "processed",
                "processed_at": "2026-04-29T10:05:00",
                "warnings": [],
                "source_encoding": "utf-8",
            },
            {
                "document_id": "doc-2",
                "filename": "table.xlsx",
                "checksum_sha256": "checksum-doc-2",
                "title": "Title table.xlsx",
                "extension": ".xlsx",
                "extractor": "txt",
                "status": "processed",
                "processed_at": "2026-04-29T10:05:00",
                "warnings": ["needs review"],
                "source_encoding": "utf-8",
            },
        ],
    }


def _load_module():
    module = importlib.import_module("scripts.demo_customer_flow")
    return importlib.reload(module)


def test_demo_customer_flow_builds_read_only_report(tmp_path: Path, monkeypatch, capsys) -> None:
    storage_root, results_dir, index_dir = _prepare_storage(tmp_path)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()

    text_one = "Экология проект. Предельно допустимые выбросы ПДВ."
    text_two = "Лист 1. Строка 0101. Форма 2 Плановая калькуляция затрат. Приобретение сырья и материалов."
    _write_json(
        results_dir / "doc-1.json",
        _result_document(
            "doc-1",
            "sample.docx",
            text=text_one,
            ocr_used=True,
            ocr_engine="tesseract",
            ocr_status="success",
        ),
    )
    _write_json(results_dir / "doc-2.json", _result_document("doc-2", "table.xlsx", text=text_two, table_count=1, warnings=["needs review"]))
    _write_json(index_dir / "corpus_index.json", _index_payload())
    _write_json(index_dir / "ingestion_manifest.json", _manifest_payload())

    before_results = {path.name: path.read_text(encoding="utf-8") for path in sorted(results_dir.glob("*.json"))}
    before_index = (index_dir / "corpus_index.json").read_text(encoding="utf-8")
    before_manifest = (index_dir / "ingestion_manifest.json").read_text(encoding="utf-8")

    report_path = tmp_path / "demo_report.json"
    module = _load_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "demo_customer_flow",
            "--json-report-path",
            str(report_path),
        ],
    )
    module.main()
    captured = capsys.readouterr()

    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_version"] == "stage17_customer_demo_smoke_v1"
    assert report["mode"] == "read-only"
    assert report["capabilities"]["supported_formats"] == ["pdf", "doc", "docx", "rtf", "txt", "xlsx", "xls"]
    assert report["capabilities"]["metadata_only_image_formats"] == ["jpg", "jpeg", "png"]
    assert report["capabilities"]["unsupported_image_like_formats"] == ["heic", "heif", "tiff", "tif", "bmp", "webp"]
    assert any("optional local OCR" in item for item in report["capabilities"]["limits"])
    assert "LLM generation is not implemented." in report["capabilities"]["limits"]
    assert report["corpus"]["indexed_documents"] == 2
    assert report["corpus"]["indexed_chunks"] == 2
    assert report["corpus"]["documents_with_tables"] == 1
    assert report["corpus"]["documents_with_images"] == 0
    assert report["corpus"]["documents_with_warnings"] == 1
    assert report["corpus"]["ocr_used_documents"] == 1
    assert report["corpus"]["ocr_used_engines"] == {"tesseract": 1}
    assert report["corpus"]["ocr_used_statuses"] == {"success": 1}
    assert report["corpus"]["audit_summary"]["warnings_documents"] == 1
    assert report["corpus"]["audit_summary"]["missing_from_index_documents"] == 0

    scenarios = {item["id"]: item for item in report["scenarios"]}
    assert scenarios["S4"]["status"] == "supported-now"
    assert "row/value retrieval is lexical" in scenarios["S4"]["note"]
    assert scenarios["S6"]["status"] == "limited"
    assert "optional local OCR" in scenarios["S6"]["note"]
    assert scenarios["S7"]["status"] == "limited"
    assert report["table_scenario"]["row_context_probe"]["status"] == "hit"
    assert report["table_scenario"]["row_context_probe"]["has_row_context"] is True
    assert report["table_scenario"]["row_context_probe"]["top_hit"]["snippet"]
    assert "Строка" in report["table_scenario"]["row_context_probe"]["top_hit"]["snippet"]
    assert report["table_scenario"]["row_context_probe"]["top_hit"]["filename"] == "table.xlsx"

    queries = {item["query"]: item for item in report["queries"]}
    assert queries["экология проект"]["status"] == "hit"
    assert queries["ПДВ"]["status"] == "hit"
    assert queries["выброс"]["status"] == "hit"
    assert queries["затраты на сырье"]["status"] == "hit"
    assert queries["затраты на сырье"]["top_hits"][0]["filename"] == "table.xlsx"

    assert "Демо-проверка customer flow" in captured.out
    assert "Режим: read-only / без изменения storage" in captured.out
    assert "Аудит корпуса: найдено проблемных/требующих внимания документов" in captured.out
    assert "OCR used documents: 1" in captured.out
    assert "Это диагностический слой качества корпуса, а не ошибка запуска demo." in captured.out
    assert "Возможности baseline:" in captured.out
    assert "Сценарии:" in captured.out
    assert "Табличный сценарий:" in captured.out
    assert "Проба контекста строки:" in captured.out
    assert "Демо-запросы:" in captured.out
    assert "Ограничения:" in captured.out
    assert "OCR не реализован." in captured.out
    assert "Генерация LLM не реализована." in captured.out
    assert "затраты на сырье: hit" in captured.out
    assert "Поиск по источникам" in captured.out
    assert "Видимость аудита" in captured.out
    assert "Краткий справочник" not in captured.out

    after_results = {path.name: path.read_text(encoding="utf-8") for path in sorted(results_dir.glob("*.json"))}
    after_index = (index_dir / "corpus_index.json").read_text(encoding="utf-8")
    after_manifest = (index_dir / "ingestion_manifest.json").read_text(encoding="utf-8")
    assert after_results == before_results
    assert after_index == before_index
    assert after_manifest == before_manifest

    get_settings.cache_clear()


def test_demo_customer_flow_refresh_index_rebuilds_index(tmp_path: Path, monkeypatch) -> None:
    storage_root, results_dir, index_dir = _prepare_storage(tmp_path)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()

    text = "Экология проект. Предельно допустимые выбросы ПДВ."
    _write_json(results_dir / "doc-1.json", _result_document("doc-1", "sample.docx", text=text, table_count=1))
    _write_json(index_dir / "corpus_index.json", {"version": "1", "updated_at": "2026-04-29T10:10:00", "document_count": 0, "chunk_count": 0, "avg_chunk_length": 0.0, "doc_frequencies": {}, "entries": []})
    _write_json(index_dir / "ingestion_manifest.json", _manifest_payload())

    module = _load_module()
    monkeypatch.setattr(sys, "argv", ["demo_customer_flow", "--refresh-index"])
    module.main()

    refreshed = json.loads((index_dir / "corpus_index.json").read_text(encoding="utf-8"))
    assert refreshed["document_count"] == 1
    assert refreshed["chunk_count"] == 1

    get_settings.cache_clear()


def test_demo_customer_flow_table_probe_falls_back_without_spreadsheet_row_context(tmp_path: Path, monkeypatch, capsys) -> None:
    storage_root, results_dir, index_dir = _prepare_storage(tmp_path)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()

    spreadsheet_text = "Форма 2 Плановая калькуляция затрат. Приобретение сырья и материалов."
    doc_text = "Строка 0101. Таблица 9. Текстовый документ с таблицей, но не spreadsheet evidence."
    _write_json(results_dir / "doc-1.json", _result_document("doc-1", "sample.docx", text=doc_text))
    _write_json(results_dir / "doc-2.json", _result_document("doc-2", "table.xlsx", text=spreadsheet_text, table_count=1))
    _write_json(index_dir / "corpus_index.json", _index_payload())
    _write_json(index_dir / "ingestion_manifest.json", _manifest_payload())

    # Replace the row-context chunk with a spreadsheet chunk that lacks row markers.
    index_payload = _index_payload()
    index_payload["entries"][0]["filename"] = "sample.docx"
    index_payload["entries"][0]["text"] = "Строка 0101. Таблица 9. Текстовый документ с таблицей, но не spreadsheet evidence."
    index_payload["entries"][0]["normalized_tokens"] = ["строк", "0101", "таблиц", "9", "текстов", "документ", "таблиц", "spreadsheet", "evidence"]
    index_payload["entries"][0]["tokens"] = ["Строка", "0101", "Таблица", "9", "Текстовый", "документ", "с", "таблицей", "но", "не", "spreadsheet", "evidence"]
    index_payload["entries"][1]["text"] = spreadsheet_text
    index_payload["entries"][1]["normalized_tokens"] = ["форма", "2", "плановая", "калькуляц", "затрат", "приобретение", "сырье", "материалов"]
    index_payload["entries"][1]["tokens"] = ["Форма", "2", "Плановая", "калькуляция", "затрат", "Приобретение", "сырья", "и", "материалов"]
    _write_json(index_dir / "corpus_index.json", index_payload)

    module = _load_module()
    report_path = tmp_path / "demo_report.json"
    monkeypatch.setattr(sys, "argv", ["demo_customer_flow", "--json-report-path", str(report_path)])
    module.main()
    captured = capsys.readouterr()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["table_scenario"]["row_context_probe"]["status"] == "no-hit"
    assert report["table_scenario"]["row_context_probe"]["top_hit"] is None
    assert report["table_scenario"]["refresh_hint_needed"] is True
    assert "В текущем индексе row-level XLS/XLSX контекст не найден" in captured.out
    assert "Краткий справочник" not in captured.out
    assert "Табличный сценарий:" in captured.out

    get_settings.cache_clear()
