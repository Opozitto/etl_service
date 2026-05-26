from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.core.config import get_settings
from app.extraction.requirements import extract_requirements_from_document
from app.schemas.document import (
    Block,
    Chunk,
    DocumentArtifact,
    DocumentMetadata,
    ProcessingInfo,
    Section,
    SourceInfo,
    StructuredDocument,
    TableData,
)


def _document(
    text: str,
    *,
    document_id: str = "doc-1",
    filename: str = "sample.txt",
    block_id: str = "blk-1",
    chunk_id: str = "chk-1",
    section_id: str = "sec-1",
    section_title: str = "Norms",
    table_rows: list[list[str]] | None = None,
) -> StructuredDocument:
    created_at = datetime(2026, 4, 30, 10, 0, 0)
    tables = [
        TableData(
            table_id="tbl-1",
            order=1,
            section_id=section_id,
            page_num=3,
            n_rows=len(table_rows or []),
            n_cols=max((len(row) for row in table_rows or []), default=0),
            rows=table_rows or [],
            cells=[],
        )
    ] if table_rows is not None else []
    return StructuredDocument(
        metadata=DocumentMetadata(
            document_id=document_id,
            title=filename,
            created_at=created_at,
            processed_at=created_at,
            section_count=1,
            block_count=1,
            table_count=len(tables),
        ),
        source=SourceInfo(
            filename=filename,
            extension=Path(filename).suffix.lower(),
            mime_type="text/plain",
            size_bytes=100,
            checksum_sha256=f"checksum-{document_id}",
        ),
        sections=[
            Section(
                section_id=section_id,
                title=section_title,
                level=1,
                order=1,
                page_start=1,
                page_end=1,
                block_ids=[block_id],
            )
        ],
        blocks=[
            Block(
                block_id=block_id,
                type="paragraph",
                order=1,
                text=text,
                section_id=section_id,
                page_num=1,
                metadata={},
            )
        ],
        tables=tables,
        chunks=[
            Chunk(
                chunk_id=chunk_id,
                document_id=document_id,
                section_id=section_id,
                block_ids=[block_id],
                text=text,
                order=1,
                token_estimate=10,
            )
        ],
        processing_info=ProcessingInfo(
            extractor="txt",
            warnings=[],
            features={},
            source_encoding="utf-8",
            text_char_count=len(text),
            text_block_count=1,
            extractor_metadata={},
        ),
        artifacts=DocumentArtifact(result_json_path="", source_file_path=""),
    )


def _write_document(results_dir: Path, document: StructuredDocument) -> Path:
    path = results_dir / f"{document.metadata.document_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_extracts_obligation_candidate_with_stable_reasons() -> None:
    document = _document("Проект должен содержать раздел по охране атмосферного воздуха. Расчет требуется приложить.")

    candidates = extract_requirements_from_document(document)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.category == "obligation"
    assert candidate.score == 0.8
    assert candidate.document_id == "doc-1"
    assert candidate.filename == "sample.txt"
    assert candidate.source_type == "block"
    assert candidate.block_id == "blk-1"
    assert candidate.section_id == "sec-1"
    assert candidate.section_title == "Norms"
    assert candidate.page == 1
    assert candidate.matched_terms == ["должен", "расчет", "требуется"]
    assert candidate.reason_codes == ["calculation_or_reporting_marker", "domain_hint", "obligation_marker", "section_context"]


def test_extracts_prohibition_candidate() -> None:
    document = _document("Сброс загрязняющих веществ запрещается. Не допускается превышение лимита.")

    candidates = extract_requirements_from_document(document)

    assert len(candidates) == 1
    assert candidates[0].category == "prohibition"
    assert candidates[0].score == 0.84
    assert candidates[0].matched_terms == ["запрещается", "лимит", "не допускается"]


def test_extracts_threshold_or_limit_candidate() -> None:
    document = _document("Для источника указывается ПДК и предельно допустимый норматив выбросов.")

    candidates = extract_requirements_from_document(document)

    assert len(candidates) == 1
    assert candidates[0].category == "threshold_or_limit"
    assert candidates[0].score == 0.82
    assert candidates[0].reason_codes == ["domain_hint", "section_context", "threshold_or_limit_marker"]


def test_neutral_text_has_no_false_positive() -> None:
    document = _document("В документе приведено описание площадки и общие сведения о предприятии.")

    assert extract_requirements_from_document(document) == []


def test_default_category_terms_work_without_config(monkeypatch) -> None:
    monkeypatch.delenv("ETL_RULES_CONFIG_PATH", raising=False)
    get_settings.cache_clear()
    module = importlib.reload(importlib.import_module("app.extraction.requirements"))
    try:
        document = _document("Проект должен содержать раздел.")

        candidate = module.extract_requirements_from_document(document)[0]

        assert candidate.category == "obligation"
        assert "должен" in candidate.matched_terms
    finally:
        get_settings.cache_clear()
        importlib.reload(module)


def test_optional_rules_config_adds_requirement_category_terms(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "rules.json"
    config_path.write_text(
        json.dumps(
            {
                "requirements": {
                    "additional_category_terms": {
                        "obligation": ["must provide"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ETL_RULES_CONFIG_PATH", str(config_path))
    get_settings.cache_clear()
    module = importlib.reload(importlib.import_module("app.extraction.requirements"))
    try:
        document = _document("The sample facility must provide a short emissions register.")

        candidate = module.extract_requirements_from_document(document)[0]

        assert candidate.category == "obligation"
        assert candidate.matched_terms == ["must provide"]
    finally:
        monkeypatch.delenv("ETL_RULES_CONFIG_PATH", raising=False)
        get_settings.cache_clear()
        importlib.reload(module)


def test_invalid_rules_config_falls_back_to_requirement_defaults(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "rules.json"
    config_path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("ETL_RULES_CONFIG_PATH", str(config_path))
    get_settings.cache_clear()
    with pytest.warns(RuntimeWarning):
        module = importlib.reload(importlib.import_module("app.extraction.requirements"))
    try:
        document = _document("Проект должен содержать раздел.")

        candidate = module.extract_requirements_from_document(document)[0]

        assert candidate.category == "obligation"
    finally:
        monkeypatch.delenv("ETL_RULES_CONFIG_PATH", raising=False)
        get_settings.cache_clear()
        importlib.reload(module)


def test_table_source_fields_are_preserved() -> None:
    document = _document(
        "Нейтральный блок.",
        table_rows=[["Показатель", "Значение"], ["ПДВ", "Контроль проводится ежеквартально"]],
    )

    candidates = extract_requirements_from_document(document)

    table_candidates = [candidate for candidate in candidates if candidate.source_type == "table"]
    assert len(table_candidates) == 1
    candidate = table_candidates[0]
    assert candidate.category == "threshold_or_limit"
    assert candidate.table_id == "tbl-1"
    assert candidate.page == 3
    assert "table_context" in candidate.reason_codes


def test_cli_is_read_only_and_writes_report_only_when_requested(tmp_path: Path, monkeypatch, capsys) -> None:
    storage_root = tmp_path / "storage"
    results_dir = storage_root / "results"
    index_dir = storage_root / "index"
    uploads_dir = storage_root / "uploads"
    results_dir.mkdir(parents=True)
    index_dir.mkdir(parents=True)
    uploads_dir.mkdir(parents=True)
    _write_document(results_dir, _document("Контроль выбросов проводится ежеквартально.", document_id="doc-1"))
    index_probe = index_dir / "probe.txt"
    uploads_probe = uploads_dir / "probe.txt"
    index_probe.write_text("index", encoding="utf-8")
    uploads_probe.write_text("uploads", encoding="utf-8")
    before_results = {path.name: path.read_text(encoding="utf-8") for path in results_dir.glob("*")}
    before_index = {path.name: path.read_text(encoding="utf-8") for path in index_dir.glob("*")}
    before_uploads = {path.name: path.read_text(encoding="utf-8") for path in uploads_dir.glob("*")}

    module = importlib.import_module("scripts.extract_requirements")
    importlib.reload(module)
    monkeypatch.setattr(sys, "argv", ["extract_requirements", "--results-dir", str(results_dir)])
    module.main()
    captured = capsys.readouterr()

    assert "Stage 22 requirements extraction v1" in captured.out
    assert "Documents seen=1 documents_with_candidates=1 candidates=1" in captured.out
    assert "monitoring_or_control=1" in captured.out
    assert len(list(tmp_path.rglob("*.json"))) == 1
    assert {path.name: path.read_text(encoding="utf-8") for path in results_dir.glob("*")} == before_results
    assert {path.name: path.read_text(encoding="utf-8") for path in index_dir.glob("*")} == before_index
    assert {path.name: path.read_text(encoding="utf-8") for path in uploads_dir.glob("*")} == before_uploads

    report_path = tmp_path / "reports" / "requirements.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["extract_requirements", "--results-dir", str(results_dir), "--json-report-path", str(report_path)],
    )
    module.main()

    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_version"] == "stage22_requirements_v1"
    assert report["summary"]["total_candidates"] == 1
    assert report["candidates"][0]["document_id"] == "doc-1"


def test_requirements_api_returns_candidates_and_empty_case(tmp_path: Path, monkeypatch) -> None:
    storage_root = tmp_path / "storage"
    results_dir = storage_root / "results"
    results_dir.mkdir(parents=True)
    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_root))
    get_settings.cache_clear()
    _write_document(results_dir, _document("Необходимо вести контроль выбросов.", document_id="doc-api"))

    documents_module = importlib.import_module("app.api.routes.documents")
    importlib.reload(documents_module)
    main_module = importlib.import_module("app.main")
    importlib.reload(main_module)
    client = TestClient(main_module.app)

    response = client.get("/api/v1/corpus/requirements")
    assert response.status_code == 200
    payload = response.json()
    assert payload["report_version"] == "stage22_requirements_v1"
    assert payload["summary"]["documents_seen"] == 1
    assert payload["summary"]["total_candidates"] == 1
    assert payload["candidates"][0]["document_id"] == "doc-api"
    assert payload["candidates"][0]["filename"] == "sample.txt"
    assert payload["candidates"][0]["source_type"] == "block"
    assert payload["candidates"][0]["block_id"] == "blk-1"

    empty_response = client.get("/api/v1/corpus/requirements", params={"query": "missing"})
    assert empty_response.status_code == 200
    empty_payload = empty_response.json()
    assert empty_payload["summary"]["total_candidates"] == 0
    assert empty_payload["candidates"] == []

    get_settings.cache_clear()
