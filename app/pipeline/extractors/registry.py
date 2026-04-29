from pathlib import Path
from typing import Callable

from app.pipeline.extractors.base import BaseExtractor
from app.pipeline.errors import UnsupportedImageFormatError, UnsupportedSpreadsheetFormatError


SUPPORTED_STANDALONE_IMAGE_SUFFIXES: tuple[str, ...] = (".jpg", ".jpeg", ".png")
KNOWN_UNSUPPORTED_IMAGE_SUFFIXES: tuple[str, ...] = (".heic", ".heif", ".tif", ".tiff", ".bmp", ".webp")


class ExtractorRegistry:
    def __init__(self) -> None:
        self._factories: list[tuple[tuple[str, ...], Callable[[], BaseExtractor]]] = [
            ((".pdf",), self._build_pdf),
            ((".doc",), self._build_doc),
            ((".docx",), self._build_docx),
            ((".rtf",), self._build_rtf),
            ((".txt",), self._build_txt),
            ((".xlsx",), self._build_xlsx),
            (SUPPORTED_STANDALONE_IMAGE_SUFFIXES, self._build_image),
        ]

    def get_for_path(self, path: Path) -> BaseExtractor:
        suffix = path.suffix.lower()
        for extensions, factory in self._factories:
            if suffix in extensions:
                return factory()
        if suffix == ".xls":
            raise UnsupportedSpreadsheetFormatError(suffix, (".xlsx",))
        if suffix in KNOWN_UNSUPPORTED_IMAGE_SUFFIXES:
            raise UnsupportedImageFormatError(suffix, SUPPORTED_STANDALONE_IMAGE_SUFFIXES)
        raise ValueError(f"Unsupported file type: {path.suffix}")

    @staticmethod
    def _build_pdf() -> BaseExtractor:
        from app.pipeline.extractors.pdf import PdfExtractor

        return PdfExtractor()

    @staticmethod
    def _build_doc() -> BaseExtractor:
        from app.pipeline.extractors.doc import DocExtractor

        return DocExtractor()

    @staticmethod
    def _build_docx() -> BaseExtractor:
        from app.pipeline.extractors.docx import DocxExtractor

        return DocxExtractor()

    @staticmethod
    def _build_rtf() -> BaseExtractor:
        from app.pipeline.extractors.rtf import RtfExtractor

        return RtfExtractor()

    @staticmethod
    def _build_txt() -> BaseExtractor:
        from app.pipeline.extractors.txt import TxtExtractor

        return TxtExtractor()

    @staticmethod
    def _build_xlsx() -> BaseExtractor:
        from app.pipeline.extractors.xlsx import XlsxExtractor

        return XlsxExtractor()

    @staticmethod
    def _build_image() -> BaseExtractor:
        from app.pipeline.extractors.image import ImageExtractor

        return ImageExtractor()
