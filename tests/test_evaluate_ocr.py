from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from app.core.config import get_settings
from app.pipeline.ocr import OCRResult


def _load_module():
    module = importlib.import_module("scripts.evaluate_ocr")
    return importlib.reload(module)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _snapshot_files(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _prepare_storage(tmp_path: Path) -> Path:
    storage_root = tmp_path / "storage"
    _write_text(storage_root / "index" / "corpus_index.json", "{\"version\": \"1\"}")
    _write_text(storage_root / "index" / "ingestion_manifest.json", "{\"version\": \"1\"}")
    _write_text(storage_root / "results" / "existing.json", "{\"ok\": true}")
    _write_text(storage_root / "uploads" / "existing.txt", "upload sentinel")
    return storage_root


def _prepare_input_dir(tmp_path: Path) -> Path:
    input_dir = tmp_path / "samples"
    _write_bytes(input_dir / "photo.jpg", b"jpg")
    _write_bytes(input_dir / "scan.heic", b"heic")
    _write_bytes(input_dir / "pages.pdf", b"pdf")
    return input_dir


def test_evaluate_ocr_reports_success_and_writes_json_only_when_requested(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    storage_root = _prepare_storage(tmp_path)
    input_dir = _prepare_input_dir(tmp_path)
    report_path = tmp_path / "reports" / "ocr_report.json"

    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()
    module = _load_module()

    monkeypatch.setattr(module.LocalOCRAdapter, "is_available", lambda self: True)
    monkeypatch.setattr(
        module.LocalOCRAdapter,
        "run",
        lambda self, path: OCRResult(
            text="OCR extracted text for smoke",
            engine="tesseract",
            success=True,
            status="success",
        ),
    )

    before_storage = _snapshot_files(storage_root)

    exit_code = module.main(["--input-dir", str(input_dir), "--json-report-path", str(report_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "OCR smoke/eval report" in captured.out
    assert "photo.jpg" in captured.out
    assert "status=success" in captured.out
    assert "status=unsupported_image_like" in captured.out
    assert "status=skipped_pdf_out_of_scope" in captured.out
    assert "This is a smoke/eval layer, not a production OCR quality guarantee." in captured.out
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_version"] == "stage21_ocr_smoke_eval_v1"
    assert report["stage"] == "Stage 21 OCR smoke evaluation"
    assert report["engine"] == "tesseract"
    assert report["engine_available"] is True
    assert report["ocr_language"] is None
    assert report["summary"] == {
        "total_images_seen": 2,
        "supported_images": 1,
        "unsupported_image_like_files": 1,
        "pdf_files_out_of_scope": 1,
        "ocr_success_count": 1,
        "ocr_empty_count": 0,
        "ocr_failed_count": 0,
        "ocr_unavailable_count": 0,
        "avg_text_length_success": 28.0,
        "engine_available": True,
    }
    assert report["scope_note"].startswith("Read-only smoke/eval layer for OCR readiness")
    assert len(report["files"]) == 3

    files = {item["filename"]: item for item in report["files"]}
    assert files["photo.jpg"]["ocr_status"] == "success"
    assert files["photo.jpg"]["ocr_used"] is True
    assert files["photo.jpg"]["text_length"] == 28
    assert files["photo.jpg"]["text_preview"] == "OCR extracted text for smoke"
    assert files["photo.jpg"]["engine"] == "tesseract"
    assert files["photo.jpg"]["ocr_language"] is None
    assert files["photo.jpg"]["elapsed_ms"] >= 0
    assert files["scan.heic"]["ocr_status"] == "unsupported_image_like"
    assert files["scan.heic"]["ocr_used"] is False
    assert files["scan.heic"]["notes"] == "unsupported_image_like_format"
    assert files["pages.pdf"]["ocr_status"] == "skipped_pdf_out_of_scope"
    assert files["pages.pdf"]["notes"] == "scanned_pdf_ocr_out_of_scope_stage21"

    after_storage = _snapshot_files(storage_root)
    assert after_storage == before_storage

    get_settings.cache_clear()


def test_evaluate_ocr_passes_language_and_writes_it_to_report(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    input_dir = tmp_path / "samples"
    _write_bytes(input_dir / "photo.jpg", b"jpg")
    report_path = tmp_path / "reports" / "ocr_report.json"
    seen_languages: list[str | None] = []

    monkeypatch.setenv("ETL_STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    module = _load_module()

    monkeypatch.setattr(module.LocalOCRAdapter, "is_available", lambda self: True)

    def _fake_run(self, path, language=None):
        seen_languages.append(language)
        return OCRResult(
            text="Справка о количестве источников выбросов",
            engine="tesseract",
            success=True,
            status="success",
        )

    monkeypatch.setattr(module.LocalOCRAdapter, "run", _fake_run)

    exit_code = module.main(
        [
            "--input-dir",
            str(input_dir),
            "--json-report-path",
            str(report_path),
            "--language",
            "rus+eng",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert seen_languages == ["rus+eng"]
    assert "OCR language: rus+eng" in captured.out

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["ocr_language"] == "rus+eng"
    assert report["files"][0]["ocr_language"] == "rus+eng"

    get_settings.cache_clear()


def test_evaluate_ocr_reports_engine_unavailable(monkeypatch, tmp_path: Path, capsys) -> None:
    input_dir = tmp_path / "samples"
    _write_bytes(input_dir / "photo.png", b"png")

    monkeypatch.setenv("ETL_STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    module = _load_module()

    monkeypatch.setattr(module.LocalOCRAdapter, "is_available", lambda self: False)
    monkeypatch.setattr(
        module.LocalOCRAdapter,
        "run",
        lambda self, path: OCRResult(
            text="",
            engine="tesseract",
            success=False,
            status="engine_unavailable",
            reason="ocr_engine_unavailable",
        ),
    )

    exit_code = module.main(["--input-dir", str(input_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "available: no" in captured.out
    assert "status=engine_unavailable" in captured.out
    assert "unavailable=1" in captured.out
    assert "avg_text_length_success=0.0" in captured.out

    get_settings.cache_clear()


def test_evaluate_ocr_reports_failure_without_json_path(monkeypatch, tmp_path: Path, capsys) -> None:
    input_dir = tmp_path / "samples"
    _write_bytes(input_dir / "photo.png", b"png")
    unexpected_report = tmp_path / "reports" / "ocr_report.json"

    monkeypatch.setenv("ETL_STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    module = _load_module()

    monkeypatch.setattr(module.LocalOCRAdapter, "is_available", lambda self: True)
    monkeypatch.setattr(
        module.LocalOCRAdapter,
        "run",
        lambda self, path: OCRResult(
            text="",
            engine="tesseract",
            success=False,
            status="failed",
            reason="ocr_failed",
            error="broken",
        ),
    )

    exit_code = module.main(["--input-dir", str(input_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "status=failed" in captured.out
    assert "failed=1" in captured.out
    assert "unavailable=0" in captured.out
    assert "ocr_failed" in captured.out
    assert not unexpected_report.exists()

    get_settings.cache_clear()
