from pathlib import Path

import pdfplumber

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.extractors.quality import inspect_pdf_cid_fragment_quality
from app.pipeline.errors import ExtractionError
from app.pipeline.types import ExtractedDocument, RawBlock


class PdfExtractor(BaseExtractor):
    supported_extensions = (".pdf",)
    name = "pdf"

    def extract(self, path: Path) -> ExtractedDocument:
        blocks: list[RawBlock] = []
        text_parts: list[str] = []
        image_count = 0
        warnings: list[str] = []

        try:
            with pdfplumber.open(path) as pdf:
                for page_idx, page in enumerate(pdf.pages, start=1):
                    page_text = (page.extract_text() or "").strip()
                    if page_text:
                        accepted_chunks: list[str] = []
                        for chunk in [item.strip() for item in page_text.split("\n\n") if item.strip()]:
                            quality = inspect_pdf_cid_fragment_quality(chunk)
                            if not quality.accepted and quality.status == "degraded":
                                warnings.extend(quality.warnings)
                                continue
                            accepted_chunks.append(chunk)
                            blocks.append(RawBlock(kind="paragraph", text=chunk, page_num=page_idx))
                        if accepted_chunks:
                            text_parts.append("\n\n".join(accepted_chunks))

                    try:
                        tables = page.extract_tables() or []
                    except Exception:
                        tables = []
                        warnings.append(f"Table extraction failed on page {page_idx}.")

                    for table in tables:
                        cleaned = [
                            [("" if cell is None else str(cell).strip()) for cell in row]
                            for row in table
                            if row
                        ]
                        if any(any(cell for cell in row) for row in cleaned):
                            blocks.append(
                                RawBlock(
                                    kind="table",
                                    text="\n".join(" | ".join(row) for row in cleaned),
                                    page_num=page_idx,
                                    data=cleaned,
                                )
                            )

                    page_images = len(page.images or [])
                    image_count += page_images
                    for img_idx in range(page_images):
                        blocks.append(
                            RawBlock(
                                kind="image",
                                page_num=page_idx,
                                metadata={"image_index": img_idx},
                            )
                        )

                if not text_parts:
                    warnings.append("PDF text extraction produced empty text; OCR may be required.")

                return ExtractedDocument(
                    extractor_name=self.name,
                    text="\n\n".join(text_parts),
                    blocks=blocks,
                    page_count=len(pdf.pages),
                    metadata={"image_count": image_count},
                    warnings=warnings,
                )
        except Exception as exc:
            raise ExtractionError(f"Failed to extract PDF {path.name}: {exc}", code="pdf_extract_failed") from exc
