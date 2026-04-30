from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from app.core.config import get_settings


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_qa(path: Path, rows: list[tuple[str, str, str]], header: tuple[str, str, str] = ("Вопрос", "Ответ", "Источник")) -> None:
    lines = [";".join(header)]
    lines.extend(";".join(row) for row in rows)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_tsv(path: Path, rows: list[tuple[str, str, str, str]], header: tuple[str, str, str, str] = ("№ п/п", "Вопрос", "Ответ", "Документ")) -> None:
    lines = ["\t".join(header)]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines), encoding="utf-8")


def _document_payload(document_id: str, filename: str, text: str, title: str | None = None) -> dict:
    return {
        "metadata": {
            "document_id": document_id,
            "title": title or filename,
            "language": "ru",
            "created_at": "2026-04-30T10:00:00",
            "processed_at": "2026-04-30T10:05:00",
            "page_count": 1,
            "section_count": 1,
            "block_count": 1,
            "table_count": 0,
            "image_count": 0,
        },
        "source": {
            "filename": filename,
            "extension": Path(filename).suffix.lower(),
            "mime_type": "text/plain",
            "size_bytes": 100,
            "checksum_sha256": f"checksum-{document_id}",
        },
        "sections": [
            {
                "section_id": f"{document_id}-sec",
                "title": "Раздел",
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
                "page_num": 1,
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
                "token_estimate": 20,
            }
        ],
        "processing_info": {
            "extractor": "txt",
            "transform_version": "baseline-v1",
            "warnings": [],
            "features": {},
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


def _prepare_results(tmp_path: Path) -> Path:
    results_dir = tmp_path / "storage" / "results"
    _write_json(
        results_dir / "doc-emissions.json",
        _document_payload(
            "doc-emissions",
            "emissions.docx",
            "ПДВ для источника выбросов составляет 1.2 т/год. Загрязняющее вещество указано в таблице.",
            title="Нормативы выбросов",
        ),
    )
    _write_json(
        results_dir / "doc-water.json",
        _document_payload(
            "doc-water",
            "water.txt",
            "Контроль сточных вод проводится ежеквартально по программе мониторинга.",
            title="Водный мониторинг",
        ),
    )
    return results_dir


def _load_module():
    module = importlib.import_module("scripts.evaluate_qa_dataset")
    return importlib.reload(module)


def test_csv_reader_handles_russian_columns_and_semicolon(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_qa(qa_path, [("Какой ПДВ?", "1.2 т/год", "emissions.docx")])

    rows, info = module.load_qa_rows(qa_path)

    assert len(rows) == 1
    assert rows[0].question == "Какой ПДВ?"
    assert rows[0].expected_answer == "1.2 т/год"
    assert rows[0].expected_document == "emissions.docx"
    assert info["delimiter"] == ";"
    assert info["columns"] == {"question": "Вопрос", "answer": "Ответ", "document": "Источник"}


def test_reader_handles_real_like_tsv_with_russian_headers_and_spaces(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.tsv"
    _write_tsv(
        qa_path,
        [("1", "Какой ПДВ?", "1.2 т/год", "emissions.docx")],
        header=("№ п/п", "  Вопрос  ", " Ответ ", " Документ "),
    )

    rows, info = module.load_qa_rows(qa_path)

    assert len(rows) == 1
    assert rows[0].question == "Какой ПДВ?"
    assert rows[0].expected_answer == "1.2 т/год"
    assert rows[0].expected_document == "emissions.docx"
    assert info["delimiter"] == "\t"
    assert info["columns"]["question"].strip() == "Вопрос"
    assert info["columns"]["answer"].strip() == "Ответ"
    assert info["columns"]["document"].strip() == "Документ"


def test_evaluator_computes_hits_and_overlap_metrics(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(
        qa_path,
        [
            ("Какой ПДВ для источника выбросов?", "ПДВ составляет 1.2 т/год", "emissions.docx"),
            ("Как проводится контроль сточных вод?", "Контроль сточных вод проводится ежеквартально", "water.txt"),
        ],
    )

    report = module.build_report(qa_path=qa_path, results_dir=results_dir, top_k=5)

    summary = report["summary"]
    assert summary["questions_total"] == 2
    assert summary["evaluated_questions"] == 2
    assert summary["skipped_questions"] == 0
    assert summary["source_expected_count"] == 2
    assert summary["document_hit_at_1"] == 2
    assert summary["document_hit_at_3"] == 2
    assert summary["document_hit_at_5"] == 2
    assert summary["source_hit_rate"] == 1.0
    assert summary["answer_overlap_avg"] > 0
    assert summary["evidence_overlap_avg"] > 0
    assert summary["no_hit_count"] == 0
    assert report["top_failures"] == []


def test_report_includes_timing_keys(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(qa_path, [("Какой ПДВ для источника выбросов?", "1.2 т/год", "emissions.docx")])

    report = module.build_report(qa_path=qa_path, results_dir=results_dir)

    assert set(report["timings"]) == {
        "load_qa_seconds",
        "load_results_seconds",
        "evaluate_seconds",
        "write_report_seconds",
        "total_seconds",
        "avg_seconds_per_question",
    }
    assert report["timings"]["total_seconds"] >= 0
    assert report["timings"]["avg_seconds_per_question"] >= 0


def test_skip_answer_overlap_skips_extracting_ask_answer(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(qa_path, [("Какой ПДВ для источника выбросов?", "1.2 т/год", "emissions.docx")])

    report = module.build_report(qa_path=qa_path, results_dir=results_dir, skip_answer_overlap=True)

    assert report["config"]["skip_answer_overlap"] is True
    assert report["summary"]["answer_overlap_evaluated"] is False
    assert report["summary"]["skipped_answer_overlap"] is True
    assert report["summary"]["answer_overlap_avg"] is None
    assert report["summary"]["source_hit_rate"] == 1.0
    assert report["results"][0]["answer_overlap"] is None
    assert report["results"][0]["answer_overlap_evaluated"] is False
    assert report["results"][0]["skipped_answer_overlap"] is True


def test_summary_detail_level_omits_bulky_question_details(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(
        qa_path,
        [
            ("Какой ПДВ для источника выбросов?", "1.2 т/год", "emissions.docx"),
            ("Несуществующий термин", "нет", "missing.pdf"),
        ],
    )

    report = module.build_report(qa_path=qa_path, results_dir=results_dir, report_detail_level="summary")

    assert report["config"]["report_detail_level"] == "summary"
    assert report["summary"]["questions_total"] == 2
    assert report["results"] == []
    assert "top_failures" in report
    assert "missing_source_examples" in report


def test_failures_detail_level_keeps_failures_without_success_details(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(
        qa_path,
        [
            ("Какой ПДВ для источника выбросов?", "1.2 т/год", "emissions.docx"),
            ("Какой ПДВ для источника выбросов?", "1.2 т/год", "missing.pdf"),
            ("Какой ПДВ для источника выбросов?", "1.2 т/год", "Нет"),
        ],
    )

    report = module.build_report(
        qa_path=qa_path,
        results_dir=results_dir,
        report_detail_level="failures",
        failures_limit=1,
        missing_source_limit=1,
    )

    assert report["config"]["report_detail_level"] == "failures"
    assert all(item["status"] == "fail" for item in report["results"])
    assert len(report["top_failures"]) == 1
    assert len(report["missing_source_examples"]) == 1
    assert not any(item["expected_document"] == "emissions.docx" for item in report["results"])


def test_failures_limit_bounds_top_failures(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(
        qa_path,
        [
            ("Какой ПДВ для источника выбросов?", "1.2 т/год", "missing-1.pdf"),
            ("Какой ПДВ для источника выбросов?", "1.2 т/год", "missing-2.pdf"),
        ],
    )

    report = module.build_report(qa_path=qa_path, results_dir=results_dir, failures_limit=1)

    assert len(report["top_failures"]) == 1


def test_missing_source_limit_bounds_examples(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(
        qa_path,
        [
            ("Какой ПДВ?", "1.2 т/год", "Нет"),
            ("Как контроль?", "квартально", "нет."),
        ],
    )

    report = module.build_report(qa_path=qa_path, results_dir=results_dir, missing_source_limit=1)

    assert len(report["missing_source_examples"]) == 1


def test_top_hits_limit_bounds_stored_hits_without_changing_top_k_eval(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(qa_path, [("Контроль ПДВ вод мониторинг", "контроль", "water.txt")])

    full_report = module.build_report(qa_path=qa_path, results_dir=results_dir, top_k=2)
    limited_report = module.build_report(qa_path=qa_path, results_dir=results_dir, top_k=2, top_hits_limit=1)

    assert full_report["summary"]["source_hit_rate"] == limited_report["summary"]["source_hit_rate"]
    assert full_report["results"][0]["retrieved_documents"] == limited_report["results"][0]["retrieved_documents"]
    assert len(full_report["results"][0]["top_hits"]) >= len(limited_report["results"][0]["top_hits"])
    assert len(limited_report["results"][0]["top_hits"]) == 1


def test_missing_expected_source_and_no_hit_are_graceful(tmp_path: Path) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    _write_qa(
        qa_path,
        [
            ("Какой ПДВ для источника выбросов?", "ПДВ составляет 1.2 т/год", "Нет"),
            ("Какой ПДВ для источника выбросов?", "ПДВ составляет 1.2 т/год", "нет."),
            ("Какой ПДВ для источника выбросов?", "ПДВ составляет 1.2 т/год", ""),
            ("Несуществующий термин абракадабра", "Нет ответа", "missing.pdf"),
        ],
    )

    report = module.build_report(qa_path=qa_path, results_dir=results_dir, top_k=5)

    assert report["summary"]["missing_expected_source_count"] == 3
    assert report["summary"]["source_expected_count"] == 1
    assert report["summary"]["document_hit_at_1"] == 0
    assert report["summary"]["document_hit_at_3"] == 0
    assert report["summary"]["document_hit_at_5"] == 0
    assert report["summary"]["source_hit_rate"] == 0.0
    assert report["summary"]["no_hit_count"] == 1
    reasons = {failure["reason"] for failure in report["top_failures"]}
    assert "no_results" in reasons
    assert "expected_source_not_found" not in reasons
    assert all(example["expected_document"] in {"Нет", "нет.", ""} for example in report["missing_source_examples"])
    assert all(failure["expected_document"] == "missing.pdf" for failure in report["top_failures"])


def test_column_override_flags_work(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_qa(
        qa_path,
        [("Какой ПДВ?", "1.2 т/год", "emissions.docx")],
        header=("my_query", "my_gold", "my_file"),
    )

    rows, info = module.load_qa_rows(
        qa_path,
        question_column="my_query",
        answer_column="my_gold",
        document_column="my_file",
    )

    assert rows[0].question == "Какой ПДВ?"
    assert info["columns"] == {"question": "my_query", "answer": "my_gold", "document": "my_file"}


def test_tab_delimiter_override_is_supported(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.tsv"
    _write_tsv(qa_path, [("1", "Какой ПДВ?", "1.2 т/год", "emissions.docx")])

    rows, info = module.load_qa_rows(qa_path, delimiter="tab")
    backslash_rows, backslash_info = module.load_qa_rows(qa_path, delimiter="\\t")
    tsv_rows, tsv_info = module.load_qa_rows(qa_path, delimiter="tsv")

    assert len(rows) == 1
    assert info["delimiter"] == "\t"
    assert len(backslash_rows) == 1
    assert backslash_info["delimiter"] == "\t"
    assert len(tsv_rows) == 1
    assert tsv_info["delimiter"] == "\t"


def test_missing_qa_path_raises_friendly_system_exit(tmp_path: Path) -> None:
    module = _load_module()
    missing = tmp_path / "missing.csv"

    try:
        module.main(["--qa-path", str(missing)])
        raised = None
    except SystemExit as exc:
        raised = exc

    assert raised is not None
    assert str(raised) == f"QA file not found: {missing}"


def test_json_report_path_is_utf8_and_not_ascii_escaped(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_module()
    results_dir = _prepare_results(tmp_path)
    qa_path = tmp_path / "qa.csv"
    report_path = tmp_path / ".runtime_eval" / "qa_eval.json"
    _write_qa(qa_path, [("Какой ПДВ для источника выбросов?", "ПДВ составляет 1.2 т/год", "emissions.docx")])

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_qa_dataset",
            "--qa-path",
            str(qa_path),
            "--results-dir",
            str(results_dir),
            "--json-report-path",
            str(report_path),
        ],
    )
    module.main()
    captured = capsys.readouterr()

    raw = report_path.read_text(encoding="utf-8")
    report = json.loads(raw)
    assert report["report_version"] == "stage24_qa_retrieval_readiness_v1"
    assert "Какой ПДВ" in raw
    assert "\\u041a" not in raw
    assert "Saved QA/retrieval eval report to" in captured.out


def test_table_question_heuristic_identifies_domain_questions() -> None:
    module = _load_module()

    assert module.is_table_question("Какое значение ПДВ в таблице выбросов?")
    assert module.is_table_question("Укажите расход сырья, т/год")
    assert module.is_table_question("Какая концентрация загрязняющего вещества?")
    assert module.is_table_question("Какие параметры выбросов по ИЗАВ № 3?")
    assert module.is_table_question("Укажите расчетную точку и координаты")
    assert module.is_table_question("Сколько г/с выбрасывает источник?")
    assert module.is_table_question("Сколько т/год составляет выброс?")
    assert not module.is_table_question("Кратко описан ли проект?")
    assert not module.is_table_question("Что такое источник выбросов?")


def test_cli_is_read_only_for_storage_dirs(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    storage_root = tmp_path / "storage"
    results_dir = _prepare_results(tmp_path)
    index_dir = storage_root / "index"
    uploads_dir = storage_root / "uploads"
    index_dir.mkdir(parents=True)
    uploads_dir.mkdir(parents=True)
    index_probe = index_dir / "probe.txt"
    uploads_probe = uploads_dir / "probe.txt"
    index_probe.write_text("index", encoding="utf-8")
    uploads_probe.write_text("uploads", encoding="utf-8")
    before_results = {path.name: path.read_text(encoding="utf-8") for path in sorted(results_dir.glob("*.json"))}
    before_index = {path.name: path.read_text(encoding="utf-8") for path in sorted(index_dir.glob("*"))}
    before_uploads = {path.name: path.read_text(encoding="utf-8") for path in sorted(uploads_dir.glob("*"))}

    qa_path = tmp_path / "qa.csv"
    _write_qa(qa_path, [("Какой ПДВ для источника выбросов?", "ПДВ составляет 1.2 т/год", "emissions.docx")])
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()
    monkeypatch.setattr(sys, "argv", ["evaluate_qa_dataset", "--qa-path", str(qa_path), "--results-dir", str(results_dir)])
    module.main()

    assert {path.name: path.read_text(encoding="utf-8") for path in sorted(results_dir.glob("*.json"))} == before_results
    assert {path.name: path.read_text(encoding="utf-8") for path in sorted(index_dir.glob("*"))} == before_index
    assert {path.name: path.read_text(encoding="utf-8") for path in sorted(uploads_dir.glob("*"))} == before_uploads
    assert not (index_dir / "corpus_index.json").exists()

    get_settings.cache_clear()
