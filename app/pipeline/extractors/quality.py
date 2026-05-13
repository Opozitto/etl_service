from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

from app.pipeline.transform.normalizer import normalize_text


ExtractionQualityStatus = Literal["accepted", "degraded", "empty"]

EXTRACTION_QUALITY_DEGRADED_REASON = "extraction_quality_degraded"

_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")
_CID_RE = re.compile(r"\(cid:\d+\)", re.IGNORECASE)
_REPEATED_SYMBOL_RE = re.compile(r"([^\w\s])\1{7,}", re.UNICODE)
_COMMON_PUNCTUATION = set(".,;:!?()[]{}\"'-/\\№%+=<>|")


@dataclass(frozen=True)
class ExtractionTextQuality:
    status: ExtractionQualityStatus
    accepted: bool
    reason: str | None
    warnings: tuple[str, ...]
    metrics: dict[str, object]


def inspect_rtf_text_quality(text: str) -> ExtractionTextQuality:
    normalized = normalize_text(text or "")
    if not normalized:
        return _empty_quality()

    metrics = _text_quality_metrics(normalized)
    char_count = int(metrics["char_count"])
    printable_ratio = float(metrics["printable_ratio"])
    control_ratio = float(metrics["control_ratio"])
    symbol_noise_ratio = float(metrics["symbol_noise_ratio"])
    alpha_ratio = float(metrics["alpha_ratio"])
    word_like_token_ratio = float(metrics["word_like_token_ratio"])
    repeated_symbol_run_count = int(metrics["repeated_symbol_run_count"])

    reason: str | None = None
    if char_count >= 40 and printable_ratio < 0.88:
        reason = "low_printable_ratio"
    elif char_count >= 40 and control_ratio >= 0.06:
        reason = "excessive_control_chars"
    elif char_count >= 80 and symbol_noise_ratio >= 0.35 and alpha_ratio < 0.35:
        reason = "binary_like_symbol_density"
    elif char_count >= 80 and word_like_token_ratio < 0.18 and symbol_noise_ratio >= 0.22:
        reason = "low_word_quality"
    elif char_count >= 80 and repeated_symbol_run_count >= 2 and symbol_noise_ratio >= 0.18:
        reason = "suspicious_symbol_repetition"

    if reason is None:
        return ExtractionTextQuality(status="accepted", accepted=True, reason=None, warnings=(), metrics=metrics)

    return ExtractionTextQuality(
        status="degraded",
        accepted=False,
        reason=EXTRACTION_QUALITY_DEGRADED_REASON,
        warnings=(f"RTF extraction output suppressed by conservative quality gate: {reason}.",),
        metrics={**metrics, "quality_issue": reason},
    )


def inspect_pdf_cid_fragment_quality(text: str) -> ExtractionTextQuality:
    normalized = normalize_text(text or "")
    if not normalized:
        return _empty_quality()

    metrics = _text_quality_metrics(normalized)
    cid_matches = _CID_RE.findall(normalized)
    cid_char_count = sum(len(match) for match in cid_matches)
    cid_ratio = cid_char_count / len(normalized)
    cid_density_per_100_chars = len(cid_matches) / max(1, len(normalized)) * 100
    metrics = {
        **metrics,
        "cid_artifact_count": len(cid_matches),
        "cid_artifact_ratio": round(cid_ratio, 3),
        "cid_density_per_100_chars": round(cid_density_per_100_chars, 3),
    }

    reason: str | None = None
    if len(cid_matches) >= 3 and cid_ratio >= 0.35:
        reason = "cid_artifact_dominated_fragment"
    elif len(cid_matches) >= 8 and cid_density_per_100_chars >= 8:
        reason = "excessive_cid_artifact_density"

    if reason is None:
        return ExtractionTextQuality(status="accepted", accepted=True, reason=None, warnings=(), metrics=metrics)

    return ExtractionTextQuality(
        status="degraded",
        accepted=False,
        reason=EXTRACTION_QUALITY_DEGRADED_REASON,
        warnings=(f"PDF text fragment suppressed by conservative CID artifact gate: {reason}.",),
        metrics={**metrics, "quality_issue": reason},
    )


def _empty_quality() -> ExtractionTextQuality:
    return ExtractionTextQuality(
        status="empty",
        accepted=False,
        reason="empty_text",
        warnings=(),
        metrics={
            "char_count": 0,
            "printable_ratio": 1.0,
            "control_ratio": 0.0,
            "symbol_noise_ratio": 0.0,
            "alpha_ratio": 0.0,
            "word_like_token_ratio": 0.0,
            "repeated_symbol_run_count": 0,
        },
    )


def _text_quality_metrics(text: str) -> dict[str, object]:
    char_count = len(text)
    printable_count = sum(1 for char in text if char.isprintable() or char.isspace())
    control_count = sum(1 for char in text if _is_control_char(char))
    alpha_count = sum(1 for char in text if char.isalpha())
    symbol_noise_count = sum(1 for char in text if _is_symbol_noise(char))
    tokens = _TOKEN_RE.findall(text)
    word_like_tokens = [token for token in tokens if any(char.isalpha() for char in token) and len(token) >= 2]

    return {
        "char_count": char_count,
        "printable_ratio": round(printable_count / char_count, 3),
        "control_ratio": round(control_count / char_count, 3),
        "symbol_noise_ratio": round(symbol_noise_count / char_count, 3),
        "alpha_ratio": round(alpha_count / char_count, 3),
        "word_like_token_ratio": round(len(word_like_tokens) / len(tokens), 3) if tokens else 0.0,
        "repeated_symbol_run_count": len(_REPEATED_SYMBOL_RE.findall(text)),
    }


def _is_control_char(char: str) -> bool:
    if char in {"\n", "\r", "\t"}:
        return False
    return unicodedata.category(char).startswith("C")


def _is_symbol_noise(char: str) -> bool:
    return not char.isalnum() and not char.isspace() and char not in _COMMON_PUNCTUATION
