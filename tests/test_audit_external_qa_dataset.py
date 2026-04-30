from __future__ import annotations

import importlib
import json
from pathlib import Path


def _load_module():
    module = importlib.import_module("scripts.audit_external_qa_dataset")
    return importlib.reload(module)


def _write_tsv(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    lines = ["№ п/п\tВопрос\tОтвет\tДокумент"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines), encoding="utf-8")


def test_tsv_csv_with_russian_headers_is_parsed(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "test_with_answers.csv"
    _write_tsv(qa_path, [("1", "Какой показатель указан?", "42", "report.pdf")])

    rows, info = module.load_qa_rows(qa_path)

    assert len(rows) == 1
    assert rows[0].question == "Какой показатель указан?"
    assert rows[0].answer == "42"
    assert rows[0].document == "report.pdf"
    assert info["delimiter"] == "\t"
    assert info["columns"] == {"question": "Вопрос", "answer": "Ответ", "document": "Документ"}


def test_no_source_placeholders_are_counted(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_tsv(
        qa_path,
        [
            ("1", "Вопрос 1?", "Ответ", "Нет"),
            ("2", "Вопрос 2?", "Ответ", "нет."),
            ("3", "Вопрос 3?", "Ответ", ""),
            ("4", "Вопрос 4?", "Ответ", "—"),
            ("5", "Вопрос 5?", "Ответ", "n/a"),
            ("6", "Вопрос 6?", "Ответ", "не указано"),
        ],
    )

    report = module.build_audit_report(tmp_path, qa_path)

    assert report["qa"]["expected_source_count"] == 0
    assert report["qa"]["missing_expected_source_count"] == 6
    assert report["expected_sources"]["unique_count"] == 0


def test_expected_document_exact_and_normalized_match(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_tsv(
        qa_path,
        [
            ("1", "Где документ?", "Ответ", "Report 2024.PDF"),
            ("2", "Где второй документ?", "Ответ", "Проект ПДВ"),
        ],
    )
    (tmp_path / "Report 2024.PDF").write_text("pdf", encoding="utf-8")
    (tmp_path / "Проект-ПДВ.docx").write_text("docx", encoding="utf-8")

    report = module.build_audit_report(tmp_path, qa_path)

    assert report["status"] == "ok"
    assert report["expected_sources"]["matched_count"] == 2
    methods = {example["document"]: example["method"] for example in report["expected_sources"]["matched_examples"]}
    assert methods["Report 2024.PDF"] == "exact_filename"
    assert methods["Проект ПДВ"] == "normalized_filename_or_stem"


def test_expected_document_base_reference_token_subset_match(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_tsv(qa_path, [("1", "Где таблица?", "Ответ", "Книга 1 - Инвентаризация Эко Агро, Таблица 4.2")])
    (tmp_path / "Том 1 Инвентаризация Эко Агро.docx").write_text("docx", encoding="utf-8")

    report = module.build_audit_report(tmp_path, qa_path)

    assert report["status"] == "ok"
    assert report["expected_sources"]["matched_count"] == 1
    assert report["expected_sources"]["matched_examples"][0]["method"] == "token_subset"


def test_missing_expected_document_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_tsv(qa_path, [("1", "Где документ?", "Ответ", "missing.pdf")])

    report = module.build_audit_report(tmp_path, qa_path)

    assert report["status"] == "needs_attention"
    assert report["expected_sources"]["missing_count"] == 1
    assert report["expected_sources"]["missing_examples"] == [{"document": "missing.pdf", "method": "none"}]


def test_duplicate_ambiguous_match_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_tsv(qa_path, [("1", "Где документ?", "Ответ", "duplicate.pdf")])
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "duplicate.pdf").write_text("a", encoding="utf-8")
    (tmp_path / "b" / "duplicate.pdf").write_text("b", encoding="utf-8")

    report = module.build_audit_report(tmp_path, qa_path)

    assert report["status"] == "needs_attention"
    assert report["expected_sources"]["ambiguous_count"] == 1
    assert report["expected_sources"]["ambiguous_examples"][0]["document"] == "duplicate.pdf"
    assert report["files"]["duplicate_filename_examples"][0]["count"] == 2


def test_supported_and_unsupported_extension_counts(tmp_path: Path) -> None:
    module = _load_module()
    qa_path = tmp_path / "qa.csv"
    _write_tsv(qa_path, [("1", "Где документ?", "Ответ", "image.heic")])
    (tmp_path / "a.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "b.docx").write_text("docx", encoding="utf-8")
    (tmp_path / "image.heic").write_text("heic", encoding="utf-8")
    (tmp_path / "archive.zip").write_text("zip", encoding="utf-8")

    report = module.build_audit_report(tmp_path, qa_path)

    assert report["files"]["supported_count"] == 2
    assert report["files"]["unsupported_count"] == 3
    assert report["files"]["supported_by_extension"] == {".docx": 1, ".pdf": 1}
    assert report["files"]["unsupported_by_extension"] == {".csv": 1, ".heic": 1, ".zip": 1}
    assert report["expected_sources"]["unsupported_matched_count"] == 1
    assert report["status"] == "needs_attention"


def test_table_like_heuristic_is_conservative() -> None:
    module = _load_module()

    assert module.is_table_like_question("Что такое источник выбросов?") is False
    assert module.is_table_like_question("Какая концентрация загрязняющего вещества в таблице?") is True
    assert module.is_table_like_question("Какая концентрация загрязняющего вещества?") is True


def test_json_report_is_written_only_with_explicit_path_and_not_to_storage(tmp_path: Path) -> None:
    module = _load_module()
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    qa_path = dataset_dir / "qa.csv"
    _write_tsv(qa_path, [("1", "Где документ?", "Ответ", "report.pdf")])
    (dataset_dir / "report.pdf").write_text("pdf", encoding="utf-8")

    module.main(["--dataset-dir", str(dataset_dir), "--qa-path", str(qa_path)])
    assert not (tmp_path / "storage").exists()
    assert not list(tmp_path.rglob("audit_report.json"))

    report_path = tmp_path / ".runtime_eval" / "example_data_stage26" / "audit_report.json"
    module.main(
        [
            "--dataset-dir",
            str(dataset_dir),
            "--qa-path",
            str(qa_path),
            "--json-report-path",
            str(report_path),
        ]
    )

    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert not (tmp_path / "storage").exists()
