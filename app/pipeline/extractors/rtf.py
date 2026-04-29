from pathlib import Path

from striprtf.striprtf import rtf_to_text

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.extractors.utils import decode_text_file
from app.pipeline.types import ExtractedDocument, RawBlock


class RtfExtractor(BaseExtractor):
    supported_extensions = (".rtf",)
    name = "rtf"

    def extract(self, path: Path) -> ExtractedDocument:
        raw, encoding, warnings = decode_text_file(path)
        text = rtf_to_text(raw)
        paragraphs = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        blocks = [RawBlock(kind="paragraph", text=chunk, page_num=1) for chunk in paragraphs]
        return ExtractedDocument(
            extractor_name=self.name,
            text=text,
            blocks=blocks,
            page_count=1,
            metadata={"source_encoding": encoding},
            warnings=warnings,
        )
