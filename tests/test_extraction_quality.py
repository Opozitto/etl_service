from __future__ import annotations

import shutil
from pathlib import Path

from app.pipeline.extractors.pdf import PdfExtractor
from app.pipeline.extractors.quality import inspect_pdf_cid_fragment_quality, inspect_rtf_text_quality
from app.pipeline.extractors.rtf import RtfExtractor


def test_rtf_quality_accepts_normal_multilingual_text() -> None:
    quality = inspect_rtf_text_quality("Справка о проекте / Project reference 2026. pH 7.0.")

    assert quality.accepted is True
    assert quality.status == "accepted"
    assert quality.reason is None


def test_rtf_quality_degrades_binary_like_garbage() -> None:
    garbage = ("\x00\x01\x02@@@###%%% " * 12) + "x"

    quality = inspect_rtf_text_quality(garbage)

    assert quality.accepted is False
    assert quality.status == "degraded"
    assert quality.reason == "extraction_quality_degraded"
    assert quality.metrics["quality_issue"] in {
        "low_printable_ratio",
        "excessive_control_chars",
        "binary_like_symbol_density",
        "low_word_quality",
    }
    assert quality.warnings


def test_rtf_extractor_suppresses_degraded_text(monkeypatch) -> None:
    work_dir = Path(__file__).resolve().parent / ".stage39_2_quality"
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / "sample.rtf"
    garbage = ("\x00\x01\x02@@@###%%% " * 12) + "x"

    try:
        path.write_text("{\\rtf1 fake}", encoding="utf-8")
        monkeypatch.setattr("app.pipeline.extractors.rtf.rtf_to_text", lambda raw: garbage)

        extracted = RtfExtractor().extract(path)

        assert extracted.text == ""
        assert extracted.blocks == []
        assert extracted.metadata["extraction_quality_status"] == "degraded"
        assert extracted.metadata["extraction_quality_reason"] == "extraction_quality_degraded"
        assert any("RTF extraction output suppressed" in warning for warning in extracted.warnings)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def test_pdf_cid_quality_accepts_sparse_artifacts() -> None:
    text = "Нормальная строка таблицы: код (cid:57), значение 12.5, описание выбросов."

    quality = inspect_pdf_cid_fragment_quality(text)

    assert quality.accepted is True
    assert quality.status == "accepted"


def test_pdf_cid_quality_degrades_dominated_fragment() -> None:
    text = "(cid:123) (cid:57) (cid:880) (cid:42) (cid:17) (cid:88)"

    quality = inspect_pdf_cid_fragment_quality(text)

    assert quality.accepted is False
    assert quality.status == "degraded"
    assert quality.reason == "extraction_quality_degraded"
    assert quality.metrics["quality_issue"] == "cid_artifact_dominated_fragment"
    assert quality.warnings


def test_pdf_extractor_suppresses_only_cid_dominated_paragraph(monkeypatch) -> None:
    work_dir = Path(__file__).resolve().parent / ".stage39_2_quality"
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / "sample.pdf"

    class _Page:
        images = []

        def extract_text(self):
            return (
                "Полезный текст про экологический проект.\n\n"
                "(cid:123) (cid:57) (cid:880) (cid:42) (cid:17) (cid:88)"
            )

        def extract_tables(self):
            return []

    class _Pdf:
        pages = [_Page()]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    try:
        path.write_bytes(b"%PDF fake")
        monkeypatch.setattr("app.pipeline.extractors.pdf.pdfplumber.open", lambda pdf_path: _Pdf())

        extracted = PdfExtractor().extract(path)

        assert extracted.text == "Полезный текст про экологический проект."
        assert [block.text for block in extracted.blocks if block.kind == "paragraph"] == [
            "Полезный текст про экологический проект."
        ]
        assert any("PDF text fragment suppressed" in warning for warning in extracted.warnings)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
