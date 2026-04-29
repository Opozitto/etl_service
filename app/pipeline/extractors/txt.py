from pathlib import Path

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.extractors.utils import decode_text_file
from app.pipeline.types import ExtractedDocument, RawBlock


class TxtExtractor(BaseExtractor):
    supported_extensions = (".txt",)
    name = "txt"

    def extract(self, path: Path) -> ExtractedDocument:
        text, encoding, warnings = decode_text_file(path)
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
