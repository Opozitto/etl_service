from __future__ import annotations

import shutil
import subprocess
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.pipeline.transform.normalizer import normalize_text


OCRStatus = Literal["success", "engine_unavailable", "timeout", "failed", "empty_text"]
OCRQualityStatus = Literal["accepted", "degraded", "empty"]
OCR_QUALITY_DEGRADED_REASON = "ocr_quality_degraded"

_TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")
_COMMON_PUNCTUATION = set(".,;:!?()[]{}\"'-/№")
_SUSPICIOUS_LATINIZED_RU_PATTERNS = (
    re.compile(r"curyanuoumas", re.IGNORECASE),
    re.compile(r"kapra", re.IGNORECASE),
    re.compile(r"c[rt]p?a[pb]k[aа]", re.IGNORECASE),
    re.compile(r"k[o0][mм][a-zа-яё0-9]*4[eе]?[cс][tт][bв][eе]", re.IGNORECASE),
)


@dataclass(frozen=True)
class OCRResult:
    text: str
    engine: str | None
    success: bool
    status: OCRStatus
    reason: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class OCRTextQuality:
    status: OCRQualityStatus
    accepted: bool
    reason: str | None
    warnings: tuple[str, ...]
    metrics: dict[str, object]


def inspect_ocr_text_quality(text: str) -> OCRTextQuality:
    normalized = normalize_text(text or "")
    if not normalized:
        return OCRTextQuality(
            status="empty",
            accepted=False,
            reason="ocr_empty_text",
            warnings=(),
            metrics={
                "char_count": 0,
                "printable_ratio": 1.0,
                "cyrillic_ratio": 0.0,
                "latin_ratio": 0.0,
                "symbol_noise_ratio": 0.0,
                "mixed_token_ratio": 0.0,
                "suspicious_latinized_ru_token_count": 0,
            },
        )

    char_count = len(normalized)
    printable_count = sum(1 for char in normalized if char.isprintable() or char.isspace())
    alpha_count = sum(1 for char in normalized if char.isalpha())
    cyrillic_count = sum(1 for char in normalized if _is_cyrillic(char))
    latin_count = sum(1 for char in normalized if _is_latin(char))
    symbol_noise_count = sum(1 for char in normalized if _is_symbol_noise(char))
    tokens = _TOKEN_RE.findall(normalized)
    mixed_tokens = [token for token in tokens if _is_mixed_ocr_token(token)]
    suspicious_tokens = [token for token in tokens if _is_suspicious_latinized_ru_token(token)]

    printable_ratio = printable_count / char_count
    cyrillic_ratio = cyrillic_count / alpha_count if alpha_count else 0.0
    latin_ratio = latin_count / alpha_count if alpha_count else 0.0
    symbol_noise_ratio = symbol_noise_count / char_count
    mixed_token_ratio = len(mixed_tokens) / len(tokens) if tokens else 0.0

    metrics: dict[str, object] = {
        "char_count": char_count,
        "printable_ratio": round(printable_ratio, 3),
        "cyrillic_ratio": round(cyrillic_ratio, 3),
        "latin_ratio": round(latin_ratio, 3),
        "symbol_noise_ratio": round(symbol_noise_ratio, 3),
        "mixed_token_ratio": round(mixed_token_ratio, 3),
        "suspicious_latinized_ru_token_count": len(suspicious_tokens),
        "suspicious_latinized_ru_tokens": suspicious_tokens[:5],
    }

    reason: str | None = None
    if char_count >= 8 and printable_ratio < 0.85:
        reason = "low_printable_ratio"
    elif char_count >= 20 and symbol_noise_ratio >= 0.3 and alpha_count / char_count < 0.7:
        reason = "excessive_mixed_symbol_noise"
    elif _has_suspicious_latinized_ru_shape(
        char_count=char_count,
        cyrillic_ratio=cyrillic_ratio,
        suspicious_tokens=suspicious_tokens,
    ):
        reason = "suspicious_latinized_ru_ocr"
    elif char_count >= 12 and mixed_token_ratio >= 0.5 and symbol_noise_ratio >= 0.18:
        reason = "excessive_mixed_symbol_noise"

    if reason is None:
        return OCRTextQuality(status="accepted", accepted=True, reason=None, warnings=(), metrics=metrics)

    return OCRTextQuality(
        status="degraded",
        accepted=False,
        reason=OCR_QUALITY_DEGRADED_REASON,
        warnings=(f"OCR output suppressed by conservative quality gate: {reason}.",),
        metrics={**metrics, "quality_issue": reason},
    )


def _is_cyrillic(char: str) -> bool:
    return "\u0400" <= char <= "\u04ff"


def _is_latin(char: str) -> bool:
    return ("A" <= char <= "Z") or ("a" <= char <= "z")


def _is_symbol_noise(char: str) -> bool:
    return not char.isalnum() and not char.isspace() and char not in _COMMON_PUNCTUATION


def _is_mixed_ocr_token(token: str) -> bool:
    has_latin = any(_is_latin(char) for char in token)
    has_cyrillic = any(_is_cyrillic(char) for char in token)
    has_digit = any(char.isdigit() for char in token)
    return (has_latin and has_cyrillic) or (len(token) >= 5 and has_latin and has_digit)


def _is_suspicious_latinized_ru_token(token: str) -> bool:
    if len(token) < 5:
        return False
    if any(pattern.search(token) for pattern in _SUSPICIOUS_LATINIZED_RU_PATTERNS):
        return True
    has_latin = any(_is_latin(char) for char in token)
    has_digit = any(char.isdigit() for char in token)
    has_cyrillic = any(_is_cyrillic(char) for char in token)
    return has_latin and has_digit and not has_cyrillic


def _has_suspicious_latinized_ru_shape(
    *,
    char_count: int,
    cyrillic_ratio: float,
    suspicious_tokens: list[str],
) -> bool:
    if cyrillic_ratio >= 0.15:
        return False
    if len(suspicious_tokens) >= 2:
        return True
    if char_count <= 80 and any(any(char.isdigit() for char in token) for token in suspicious_tokens):
        return True
    return False


class LocalOCRAdapter:
    def __init__(self, engine_command: str = "tesseract", timeout_seconds: float = 30.0) -> None:
        self.engine_command = engine_command
        self.timeout_seconds = timeout_seconds

    @property
    def engine_name(self) -> str:
        return Path(self.engine_command).name or self.engine_command

    def is_available(self) -> bool:
        return shutil.which(self.engine_command) is not None

    def probe_version(self) -> OCRResult:
        if not self.is_available():
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="engine_unavailable",
                reason="ocr_engine_unavailable",
            )

        try:
            completed = subprocess.run(
                [self.engine_command, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="timeout",
                reason="ocr_timeout",
                error=str(exc),
            )
        except FileNotFoundError as exc:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="engine_unavailable",
                reason="ocr_engine_unavailable",
                error=str(exc),
            )
        except OSError as exc:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="failed",
                reason="ocr_failed",
                error=str(exc),
            )

        version_text = normalize_text(completed.stdout or completed.stderr or "")
        if completed.returncode != 0:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="failed",
                reason="ocr_failed",
                error=version_text or f"exit_code_{completed.returncode}",
            )

        return OCRResult(
            text=version_text,
            engine=self.engine_name,
            success=True,
            status="success",
        )

    def run(self, path: Path, language: str | None = None) -> OCRResult:
        if not self.is_available():
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="engine_unavailable",
                reason="ocr_engine_unavailable",
            )

        try:
            command = [self.engine_command, str(path), "stdout"]
            if language:
                command.extend(["-l", language])
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="timeout",
                reason="ocr_timeout",
                error=str(exc),
            )
        except FileNotFoundError as exc:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="engine_unavailable",
                reason="ocr_engine_unavailable",
                error=str(exc),
            )
        except OSError as exc:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="failed",
                reason="ocr_failed",
                error=str(exc),
            )

        stdout = normalize_text(completed.stdout or "")
        stderr = normalize_text(completed.stderr or "")

        if completed.returncode != 0:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="failed",
                reason="ocr_failed",
                error=stderr or f"exit_code_{completed.returncode}",
            )

        if not stdout:
            return OCRResult(
                text="",
                engine=self.engine_name,
                success=False,
                status="empty_text",
                reason="ocr_empty_text",
                error=stderr or None,
            )

        return OCRResult(
            text=stdout,
            engine=self.engine_name,
            success=True,
            status="success",
        )
