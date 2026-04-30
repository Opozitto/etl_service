from pathlib import Path

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.types import ExtractedDocument, RawBlock


class ImageExtractor(BaseExtractor):
    supported_extensions = (".png", ".jpg", ".jpeg")
    name = "image"

    def extract(self, path: Path) -> ExtractedDocument:
        return ExtractedDocument(
            extractor_name=self.name,
            text="",
            blocks=[RawBlock(kind="image", metadata={"filename": path.name})],
            page_count=1,
            warnings=["Standalone image presence captured; OCR may be attempted by the service when available."],
            metadata={"ocr_enabled": False},
        )
