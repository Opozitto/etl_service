from __future__ import annotations

from app.pipeline.ocr import inspect_ocr_text_quality


def test_ocr_quality_accepts_plain_english_text() -> None:
    quality = inspect_ocr_text_quality("OCR extracted text for search and review")

    assert quality.accepted is True
    assert quality.status == "accepted"
    assert quality.reason is None


def test_ocr_quality_accepts_normal_multilingual_text() -> None:
    quality = inspect_ocr_text_quality("Справка о проекте / Project reference 2026")

    assert quality.accepted is True
    assert quality.status == "accepted"
    assert quality.reason is None


def test_ocr_quality_degrades_suspicious_latinized_ru_output() -> None:
    quality = inspect_ocr_text_quality("Crpapka 0 KOM4eCTBe ucTo4HuKOB BbI6pocoB")

    assert quality.accepted is False
    assert quality.status == "degraded"
    assert quality.reason == "ocr_quality_degraded"
    assert quality.metrics["quality_issue"] == "suspicious_latinized_ru_ocr"
    assert quality.metrics["suspicious_latinized_ru_token_count"] >= 2
    assert quality.warnings


def test_ocr_quality_degrades_short_audit_sample_shape() -> None:
    quality = inspect_ocr_text_quality("Curyanuoumas Kapra...")

    assert quality.accepted is False
    assert quality.status == "degraded"
    assert quality.reason == "ocr_quality_degraded"
    assert quality.metrics["quality_issue"] == "suspicious_latinized_ru_ocr"


def test_ocr_quality_degrades_excessive_symbol_noise() -> None:
    quality = inspect_ocr_text_quality("abc @@ ## %% ?? ~~ 123 @@ ## %% ?? ~~")

    assert quality.accepted is False
    assert quality.status == "degraded"
    assert quality.reason == "ocr_quality_degraded"
    assert quality.metrics["quality_issue"] == "excessive_mixed_symbol_noise"
