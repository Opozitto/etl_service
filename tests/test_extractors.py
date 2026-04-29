from __future__ import annotations

import pytest
from pathlib import Path

from app.pipeline.errors import UnsupportedImageFormatError
from app.pipeline.extractors.image import ImageExtractor
from app.pipeline.extractors.registry import (
    ExtractorRegistry,
    KNOWN_UNSUPPORTED_IMAGE_SUFFIXES,
    SUPPORTED_STANDALONE_IMAGE_SUFFIXES,
)
from app.pipeline.extractors.txt import TxtExtractor


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
