from __future__ import annotations

import importlib
import json
from pathlib import Path


def _load_module():
    module = importlib.import_module("app.evaluation.splitter_cleanup_validation")
    return importlib.reload(module)


def _load_cli():
    module = importlib.import_module("scripts.validate_splitter_cleanup")
    return importlib.reload(module)


def _document(*, chunks: list[dict], sections: list[dict] | None = None, tables: list[dict] | None = None) -> dict:
    return {
        "metadata": {"document_id": "doc-1", "title": "Fixture"},
        "source": {"filename": "fixture.txt"},
        "sections": sections or [{"section_id": "sec-1", "title": "1. Введение", "parent_id": "sec-0"}],
        "blocks": [],
        "tables": tables or [],
        "chunks": chunks,
        "processing_info": {"ocr_candidate": False, "text_char_count": 100},
    }


def _chunk(**overrides) -> dict:
    base = {
        "chunk_id": "chk-1",
        "document_id": "doc-1",
        "section_id": "sec-1",
        "content_type": "text",
        "section_title": "1. Введение",
        "section_path": ["Document", "1. Введение"],
        "page_start": 1,
        "page_end": 1,
        "text": "1. Введение\nПолезный текст раздела.",
        "order": 1,
        "token_estimate": 8,
    }
    base.update(overrides)
    return base


def test_validation_detects_toc_parent_violation() -> None:
    module = _load_module()
    report = module.build_validation_report_from_documents(
        [
            _document(
                chunks=[
                    _chunk(
                        section_path=["Document", "СОДЕРЖАНИЕ", "1. ОБЩИЕ СВЕДЕНИЯ"],
                        section_title="1. ОБЩИЕ СВЕДЕНИЯ",
                    )
                ]
            )
        ]
    )

    assert report["summary"]["toc_parent_violations"] == 1
    assert report["issues"][0]["issue_type"] == "toc_parent_violation"


def test_validation_has_zero_toc_parent_violations_when_section_path_is_clean() -> None:
    module = _load_module()
    report = module.build_validation_report_from_documents([_document(chunks=[_chunk()])])

    assert report["summary"]["toc_parent_violations"] == 0
    assert report["issues"] == []


def test_duplicate_heading_detector_catches_identical_first_two_lines() -> None:
    module = _load_module()

    assert module.is_duplicate_heading_text("ВВЕДЕНИЕ\nВВЕДЕНИЕ\nТекст")


def test_duplicate_heading_detector_does_not_overmatch_meaningful_lines() -> None:
    module = _load_module()

    assert not module.is_duplicate_heading_text("ВВЕДЕНИЕ\nТекст введения")


def test_heading_only_chunk_detector_is_conservative() -> None:
    module = _load_module()
    heading = _chunk(text="ВВЕДЕНИЕ", section_title="ВВЕДЕНИЕ", section_path=["Document", "ВВЕДЕНИЕ"])
    body = _chunk(text="ВВЕДЕНИЕ\nПолезный текст раздела.", section_title="ВВЕДЕНИЕ")

    assert module.is_heading_only_chunk(heading)
    assert not module.is_heading_only_chunk(body)


def test_service_table_suspect_does_not_flag_real_table_row_with_metadata() -> None:
    module = _load_module()
    real_table_row = _chunk(
        content_type="table_row",
        table_id="tbl-1",
        table_headers=["Код", "Вещество"],
        table_column_values={"Код": "0301", "Вещество": "Азота диоксид"},
        table_context="Таблица tbl-1: Расчет выбросов",
        row_count=2,
        column_count=2,
        text="Таблица tbl-1. Строка 2 из 2. Колонки: Код: 0301; Вещество: Азота диоксид",
    )

    assert module.is_real_table_chunk(real_table_row)
    assert not module.is_service_table_suspect(real_table_row)


def test_service_table_suspect_flags_short_signature_table_like_chunk() -> None:
    module = _load_module()
    service_table = _chunk(
        content_type="table_row",
        table_id="tbl-1",
        table_headers=[],
        table_column_values={},
        row_count=2,
        column_count=3,
        text="УТВЕРЖДАЮ\nДолжность Подпись Ф.И.О.",
    )

    assert module.is_service_table_suspect(service_table)


def test_report_contract_contains_stage33_2_fields() -> None:
    module = _load_module()
    report = module.build_validation_report_from_documents([_document(chunks=[_chunk(page_start=None, page_end=None)])])

    assert report["validation_version"] == "stage33_2_splitter_cleanup_validation_v1"
    assert report["summary"]["documents_seen"] == 1
    assert report["summary"]["missing_page_expected_limitations"] == 1
    assert "documents" in report
    assert "issues" in report
    assert "limitations" in report
    assert any("DOCX page metadata" in limitation for limitation in report["limitations"])


def test_cli_runs_fresh_processing_in_temp_workspace_and_writes_only_explicit_report(
    tmp_path: Path, capsys
) -> None:
    cli = _load_cli()
    input_path = tmp_path / "sample.txt"
    input_path.write_text(
        "СОДЕРЖАНИЕ\n1. ОБЩИЕ СВЕДЕНИЯ\nОписание предприятия и экологического проекта.",
        encoding="utf-8",
    )
    workspace_dir = tmp_path / "workspace"
    output_path = tmp_path / "report.json"

    cli.main(
        [
            "--input-path",
            str(input_path),
            "--workspace-dir",
            str(workspace_dir),
            "--output-path",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()
    report = json.loads(output_path.read_text(encoding="utf-8"))

    assert "Stage 33.2 splitter cleanup validation" in captured.out
    assert report["summary"]["documents_seen"] == 1
    assert report["summary"]["documents_processed"] == 1
    assert list((workspace_dir / "results").glob("*.json"))
    assert not (tmp_path / "storage").exists()
