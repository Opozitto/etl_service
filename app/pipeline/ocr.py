from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.pipeline.transform.normalizer import normalize_text


OCRStatus = Literal["success", "engine_unavailable", "timeout", "failed", "empty_text"]


@dataclass(frozen=True)
class OCRResult:
    text: str
    engine: str | None
    success: bool
    status: OCRStatus
    reason: str | None = None
    error: str | None = None


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
