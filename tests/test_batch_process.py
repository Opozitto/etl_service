from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from app.core.config import get_settings


def _run_batch_process(input_dir: Path, report_path: Path, monkeypatch) -> dict:
    storage_root = report_path.parent / "storage"
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()

    batch_process = importlib.import_module("scripts.batch_process")
    monkeypatch.setattr(sys, "argv", ["batch_process", "--input-dir", str(input_dir), "--report-path", str(report_path)])
    batch_process.main()
    return json.loads(report_path.read_text(encoding="utf-8"))


def test_batch_process_writes_stage7_report(tmp_path: Path, monkeypatch) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    first_file = input_dir / "alpha.txt"
    second_file = input_dir / "alpha_copy.txt"
    payload = "1. Intro\n\nBatch report baseline text.\n\n- item one\n- item two"
    first_file.write_text(payload, encoding="utf-8")
    second_file.write_text(payload, encoding="utf-8")

    report_path = tmp_path / "report.json"
    report = _run_batch_process(input_dir, report_path, monkeypatch)

    assert report["report_version"] == "stage7_batch_report_v1"
    assert report["input_dir"] == str(input_dir.resolve())
    assert report["processed"] == 1
    assert report["duplicates"] == 1
    assert report["errors"] == 0
    assert len(report["items"]) == 2
    assert "summary" in report

    summary = report["summary"]
    assert summary["total_files"] == 2
    assert summary["processed"] == 1
    assert summary["duplicates"] == 1
    assert summary["errors"] == 0

    items = report["items"]
    assert summary["by_status"] == {
        "processed": 1,
        "duplicate": 1,
    }
    assert summary["by_extension"] == {".txt": 2}

    warning_items = [item for item in items if item.get("warnings")]
    assert summary["problem_files"]
    assert all(set(problem_file) >= {"file", "status", "warnings"} for problem_file in summary["problem_files"])
    assert all(problem_file["status"] in {"processed", "duplicate", "error"} for problem_file in summary["problem_files"])
    for warning_item in warning_items:
        assert any(
            problem_file["file"] == warning_item["file"]
            and problem_file["status"] == warning_item["status"]
            and problem_file["warnings"] == warning_item["warnings"]
            for problem_file in summary["problem_files"]
        )

    expected_totals = {
        "size_bytes": sum(item["size_bytes"] or 0 for item in items),
        "page_count": sum(item["page_count"] or 0 for item in items),
        "section_count": sum(item["section_count"] or 0 for item in items),
        "block_count": sum(item["block_count"] or 0 for item in items),
        "table_count": sum(item["table_count"] or 0 for item in items),
        "image_count": sum(item["image_count"] or 0 for item in items),
        "chunk_count": sum(item["chunk_count"] or 0 for item in items),
        "text_char_count": sum(item["text_char_count"] or 0 for item in items),
        "text_block_count": sum(item["text_block_count"] or 0 for item in items),
    }
    assert summary["totals"] == expected_totals

    for item in items:
        assert item["file"]
        assert item["status"] in {"processed", "duplicate"}
        assert item["extension"] == ".txt"
        assert item["size_bytes"] > 0
        assert item["document_id"]
        assert item["title"]
        assert item["section_count"] >= 1
        assert item["block_count"] >= 1
        assert item["table_count"] >= 0
        assert item["image_count"] >= 0
        assert item["chunk_count"] >= 1
        assert item["text_char_count"] > 0
        assert item["text_block_count"] >= 1
        assert isinstance(item["warnings"], list)

    get_settings.cache_clear()
