from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from app.core.config import get_settings


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_storage(tmp_path: Path) -> tuple[Path, Path]:
    storage_root = tmp_path / "storage"
    index_dir = storage_root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    return storage_root, index_dir


def _build_index_payload() -> dict:
    return {
        "version": "1",
        "updated_at": "2026-04-29T10:10:00",
        "document_count": 2,
        "chunk_count": 3,
        "avg_chunk_length": 6.0,
        "doc_frequencies": {
            "экология": 2,
            "проект": 2,
            "предельно": 1,
            "допустимые": 1,
            "выбросы": 1,
            "шум": 1,
        },
        "entries": [
            {
                "document_id": "doc-ecology-1",
                "source_checksum": "checksum-1",
                "filename": "test.docx",
                "title": "ПРОЕКТ НОРМАТИВОВ",
                "chunk_id": "chunk-1",
                "section_id": "sec-1",
                "section_title": "Введение",
                "text": "Экология проект предельно допустимые выбросы для объекта.",
                "tokens": ["Экология", "проект", "предельно", "допустимые", "выбросы", "объекта"],
                "normalized_tokens": ["экология", "проект", "предельно", "допустимые", "выбросы", "объекта"],
                "token_count": 6,
            },
            {
                "document_id": "doc-ecology-2",
                "source_checksum": "checksum-2",
                "filename": "alt.docx",
                "title": "ПРОЕКТ ЭКОЛОГИЯ",
                "chunk_id": "chunk-2",
                "section_id": "sec-2",
                "section_title": "Текст",
                "text": "Экология проект подтверждает результаты.",
                "tokens": ["Экология", "проект", "подтверждает", "результаты"],
                "normalized_tokens": ["экология", "проект", "подтверждает", "результаты"],
                "token_count": 4,
            },
            {
                "document_id": "doc-noise",
                "source_checksum": "checksum-3",
                "filename": "noise.txt",
                "title": "Шум",
                "chunk_id": "chunk-3",
                "section_id": "sec-3",
                "section_title": "Шум",
                "text": "Шумовые характеристики без искомых слов.",
                "tokens": ["Шумовые", "характеристики", "без", "искомых", "слов"],
                "normalized_tokens": ["шумовые", "характеристики", "искомых", "слов"],
                "token_count": 5,
            },
        ],
    }


def _load_module():
    module = importlib.import_module("scripts.evaluate_retrieval")
    return importlib.reload(module)


def test_evaluate_retrieval_builds_read_only_report(tmp_path: Path, monkeypatch, capsys) -> None:
    storage_root, index_dir = _prepare_storage(tmp_path)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()

    index_path = index_dir / "corpus_index.json"
    index_payload = _build_index_payload()
    _write_json(index_path, index_payload)
    before_index = index_path.read_text(encoding="utf-8")

    queries_path = tmp_path / "queries.json"
    _write_json(
        queries_path,
        [
            {
                "id": "ecology_project",
                "query": "экология проект",
                "expected_files": ["test.docx"],
                "expected_document_ids": [],
                "must_have_results": True,
            },
            {
                "id": "missing_query",
                "query": "несуществующий запрос",
                "expected_files": [],
                "expected_document_ids": [],
                "must_have_results": True,
            },
        ],
    )

    report_path = tmp_path / "report.json"
    module = _load_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluate_retrieval",
            "--queries-path",
            str(queries_path),
            "--top-k",
            "3",
            "--report-path",
            str(report_path),
        ],
    )
    module.main()
    captured = capsys.readouterr()

    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_version"] == "stage9_retrieval_quality_eval_v1"
    assert report["index"] == {
        "present": True,
        "document_count": 2,
        "chunk_count": 3,
    }
    assert report["config"] == {"top_k": 3, "queries_count": 2}
    assert report["summary"] == {
        "queries_count": 2,
        "passed": 1,
        "failed": 1,
        "queries_with_results": 1,
        "queries_without_results": 1,
        "expected_hit_queries": 1,
        "expected_hit_passed": 1,
    }

    results_by_id = {item["id"]: item for item in report["results"]}
    pass_item = results_by_id["ecology_project"]
    fail_item = results_by_id["missing_query"]

    assert pass_item["passed"] is True
    assert pass_item["failure_reasons"] == []
    assert pass_item["result_count"] >= 1
    assert pass_item["expected_files"] == ["test.docx"]
    assert pass_item["expected_document_ids"] == []
    assert pass_item["expected_hit_found"] is True
    assert pass_item["best_expected_rank"] is not None
    assert pass_item["best_expected_rank"] <= 3
    assert pass_item["top_hits"]
    first_hit = pass_item["top_hits"][0]
    assert first_hit["rank"] == 1
    assert set(first_hit) == {
        "rank",
        "score",
        "document_id",
        "filename",
        "chunk_id",
        "section_title",
        "title",
        "snippet",
    }
    assert any(hit["filename"] == "test.docx" for hit in pass_item["top_hits"])

    assert fail_item["passed"] is False
    assert fail_item["failure_reasons"] == ["no_results"]
    assert fail_item["result_count"] == 0
    assert fail_item["expected_hit_found"] is False
    assert fail_item["best_expected_rank"] is None
    assert fail_item["top_hits"] == []

    stdout = captured.out
    assert "Retrieval eval: queries=2 passed=1 failed=1 top_k=3" in stdout
    assert "Results: with_hits=1 without_hits=1 expected_hit_passed=1/1" in stdout
    assert "[PASS] ecology_project results=" in stdout
    assert "[FAIL] missing_query reasons=no_results" in stdout
    assert "Saved retrieval eval report to" in stdout

    after_index = index_path.read_text(encoding="utf-8")
    assert after_index == before_index
    assert not (storage_root / "results").exists()

    get_settings.cache_clear()


def test_evaluate_retrieval_fails_cleanly_when_index_missing(tmp_path: Path, monkeypatch) -> None:
    storage_root, index_dir = _prepare_storage(tmp_path)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()

    module = _load_module()
    monkeypatch.setattr(sys, "argv", ["evaluate_retrieval"])

    try:
        module.main()
        raised = None
    except SystemExit as exc:
        raised = exc

    assert raised is not None
    assert "corpus index not found" in str(raised)
    assert not (index_dir / "corpus_index.json").exists()

    get_settings.cache_clear()
