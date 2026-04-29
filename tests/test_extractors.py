from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from app.pipeline.errors import UnsupportedImageFormatError
from app.pipeline.extractors.image import ImageExtractor
from app.pipeline.extractors.registry import (
    ExtractorRegistry,
    KNOWN_UNSUPPORTED_IMAGE_SUFFIXES,
    SUPPORTED_STANDALONE_IMAGE_SUFFIXES,
)
from app.pipeline.extractors.txt import TxtExtractor
from app.services.document_service import DocumentService


def test_txt_extractor_uses_fallback_encoding(tmp_path: Path) -> None:
    payload = "\u041f\u0440\u0438\u043c\u0435\u0440 \u0442\u0435\u043a\u0441\u0442\u0430 \u0432 cp1251".encode(
        "cp1251"
    )
    path = tmp_path / "encoded.txt"
    path.write_bytes(payload)

    extracted = TxtExtractor().extract(path)

    assert "\u041f\u0440\u0438\u043c\u0435\u0440 \u0442\u0435\u043a\u0441\u0442\u0430" in extracted.text
    assert extracted.metadata["source_encoding"] == "cp1251"
    assert extracted.warnings


@pytest.mark.parametrize("suffix", SUPPORTED_STANDALONE_IMAGE_SUFFIXES)
def test_registry_supports_standalone_image_suffixes(suffix: str) -> None:
    extractor = ExtractorRegistry().get_for_path(Path(f"sample{suffix}"))

    assert isinstance(extractor, ImageExtractor)


@pytest.mark.parametrize("suffix", KNOWN_UNSUPPORTED_IMAGE_SUFFIXES)
def test_registry_rejects_known_unsupported_image_suffixes(suffix: str) -> None:
    with pytest.raises(UnsupportedImageFormatError) as exc_info:
        ExtractorRegistry().get_for_path(Path(f"sample{suffix}"))

    message = str(exc_info.value)
    assert "Неподдерживаемый формат изображения" in message
    assert suffix in message
    assert "Поддерживаемые standalone image-форматы: .jpg, .jpeg, .png" in message
    assert "OCR пока не реализован" in message


def test_registry_preserves_generic_unsupported_extension_error() -> None:
    with pytest.raises(ValueError) as exc_info:
        ExtractorRegistry().get_for_path(Path("sample.foo"))

    assert str(exc_info.value) == "Unsupported file type: .foo"


@pytest.mark.parametrize("suffix", SUPPORTED_STANDALONE_IMAGE_SUFFIXES)
def test_document_service_processes_standalone_image_without_ocr(
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    smoke_root = project_root / "tests" / f".stage12_smoke_{suffix.lstrip('.')}"
    storage_dir = smoke_root / "storage"
    smoke_root.mkdir(parents=True, exist_ok=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    image_path = smoke_root / f"sample{suffix}"
    color = "white" if suffix in {".jpg", ".jpeg"} else "black"
    Image.new("RGB", (2, 2), color=color).save(image_path)

    try:
        outcome = DocumentService().process_path_with_status(image_path)
        document = outcome.document
        assert outcome.status == "processed"
        assert document.source.filename == image_path.name
        assert document.source.extension == suffix
        assert document.metadata.image_count == 1
        assert document.metadata.block_count == 1
        assert document.metadata.page_count == 1
        assert document.images
        assert document.images[0].metadata["filename"] == image_path.name
        assert document.blocks
        assert document.blocks[0].type == "image"
        assert document.blocks[0].metadata["image_id"] == document.images[0].image_id
        assert document.processing_info.features["images_detected"] is True
        assert document.processing_info.features["ocr_used"] is False
        assert document.processing_info.text_char_count == 0
        assert document.processing_info.text_block_count == 0
        assert Path(document.artifacts.result_json_path).is_file()
    finally:
        get_settings.cache_clear()
        shutil.rmtree(smoke_root, ignore_errors=True)
