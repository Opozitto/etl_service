from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from app.pipeline.extractors.image import ImageExtractor
from app.pipeline.extractors.registry import (
    ExtractorRegistry,
    KNOWN_UNSUPPORTED_IMAGE_SUFFIXES,
    SUPPORTED_STANDALONE_IMAGE_SUFFIXES,
)
from app.pipeline.extractors.txt import TxtExtractor
from app.pipeline.extractors.xls import XlsExtractor
from app.pipeline.extractors.xlsx import XlsxExtractor
from app.pipeline.transform.structure import build_structure
from app.search.index import CorpusSearchEngine
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
    from app.pipeline.errors import UnsupportedImageFormatError

    with pytest.raises(UnsupportedImageFormatError) as exc_info:
        ExtractorRegistry().get_for_path(Path(f"sample{suffix}"))

    message = str(exc_info.value)
    assert suffix in message
    assert ".jpg, .jpeg, .png" in message
    assert "OCR" in message


def test_registry_preserves_generic_unsupported_extension_error() -> None:
    with pytest.raises(ValueError) as exc_info:
        ExtractorRegistry().get_for_path(Path("sample.foo"))

    assert str(exc_info.value) == "Unsupported file type: .foo"


@pytest.mark.parametrize("suffix", [".xls", ".XLS"])
def test_registry_routes_xls(suffix: str) -> None:
    extractor = ExtractorRegistry().get_for_path(Path(f"sample{suffix}"))

    assert isinstance(extractor, XlsExtractor)


def test_registry_routes_xlsx() -> None:
    registry = ExtractorRegistry()

    assert isinstance(registry.get_for_path(Path("sample.xlsx")), XlsxExtractor)


def test_xls_table_baseline_is_structured_and_searchable(monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = Path(__file__).resolve().parents[1]
    sample_path = project_root / "first_test_data" / "Форма 4 Затраты на сырье.XLS"
    smoke_root = project_root / "tests" / ".stage14_xls_smoke"
    storage_dir = smoke_root / "storage"
    shutil.rmtree(smoke_root, ignore_errors=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    try:
        extracted = XlsExtractor().extract(sample_path)
        assert extracted.extractor_name == "xls"
        assert any(block.kind == "heading" for block in extracted.blocks)
        assert any(block.kind == "table" for block in extracted.blocks)
        assert "ф4 (пл.ф.)" in extracted.text
        assert "Затраты на приобретение сырья" in extracted.text

        sections, blocks, tables, images, chunks = build_structure(extracted)
        assert tables
        assert any(block.type == "table" for block in blocks)
        assert chunks
        assert any(
            "Форма № 4" in chunk.text and "Затраты на приобретение сырья" in chunk.text
            for chunk in chunks
        )

        service = DocumentService()
        outcome = service.process_path_with_status(sample_path)
        document = outcome.document
        assert outcome.status == "processed"
        assert document.source.filename == sample_path.name
        assert document.source.extension == ".xls"
        assert document.metadata.table_count >= 1
        assert document.metadata.block_count >= 2
        assert document.blocks
        assert any(block.type == "table" for block in document.blocks)
        assert document.chunks
        assert document.processing_info.features["tables_detected"] is True
        assert Path(document.artifacts.result_json_path).is_file()

        search_engine = CorpusSearchEngine(service.storage)
        hits = search_engine.search("сырья", top_k=3)
        assert hits
        assert any("сырья" in hit.snippet.lower() for hit in hits)

        ask_response = search_engine.ask("Где указаны затраты на приобретение сырья?", top_k=3, max_sentences=2)
        assert ask_response.sources
        assert ask_response.hits
        assert any("сырья" in source.snippet.lower() for source in ask_response.sources)
    finally:
        get_settings.cache_clear()
        shutil.rmtree(smoke_root, ignore_errors=True)


def test_xlsx_table_baseline_is_structured_and_searchable(monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = Path(__file__).resolve().parents[1]
    sample_path = project_root / "first_test_data" / "Форма 2 Плановая калькуляция затрат.xlsx"
    smoke_root = project_root / "tests" / ".stage13_xlsx_smoke"
    storage_dir = smoke_root / "storage"
    shutil.rmtree(smoke_root, ignore_errors=True)
    storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()

    try:
        extracted = XlsxExtractor().extract(sample_path)
        assert any(block.kind == "table" for block in extracted.blocks)

        sections, blocks, tables, images, chunks = build_structure(extracted)
        assert tables
        assert any(block.type == "table" for block in blocks)
        assert chunks
        assert any("Трудоемкость" in chunk.text and "1199" in chunk.text for chunk in chunks)

        service = DocumentService()
        outcome = service.process_path_with_status(sample_path)
        assert outcome.status == "processed"
        assert outcome.document.tables
        assert outcome.document.blocks
        assert outcome.document.chunks
        assert Path(outcome.document.artifacts.result_json_path).is_file()

        search_engine = CorpusSearchEngine(service.storage)
        hits = search_engine.search("Трудоемкость 1199", top_k=3)
        assert hits
        assert any("Трудоемкость" in hit.snippet and "1199" in hit.snippet for hit in hits)

        ask_response = search_engine.ask("Какая трудоемкость указана в документе?", top_k=3, max_sentences=2)
        assert ask_response.sources
        assert ask_response.hits
        assert any("Трудоемкость" in source.snippet and "1199" in source.snippet for source in ask_response.sources)
    finally:
        get_settings.cache_clear()
        shutil.rmtree(smoke_root, ignore_errors=True)


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
