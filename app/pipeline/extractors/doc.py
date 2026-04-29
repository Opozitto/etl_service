from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.extractors.docx import DocxExtractor
from app.pipeline.types import ExtractedDocument


class DocExtractor(BaseExtractor):
    supported_extensions = (".doc",)
    name = "doc"

    def __init__(self) -> None:
        self.docx_extractor = DocxExtractor()

    def extract(self, path: Path) -> ExtractedDocument:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            command = [
                "soffice",
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                str(output_dir),
                str(path),
            ]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            converted_path = output_dir / f"{path.stem}.docx"
            if completed.returncode != 0 or not converted_path.exists():
                stderr = completed.stderr.strip() or completed.stdout.strip()
                raise ValueError(
                    "DOC extraction requires a local LibreOffice conversion step. "
                    f"Conversion failed for {path.name}: {stderr or 'unknown error'}"
                )

            extracted = self.docx_extractor.extract(converted_path)
            extracted.extractor_name = self.name
            extracted.warnings.append("Legacy DOC was converted to DOCX via local LibreOffice before extraction.")
            return extracted

