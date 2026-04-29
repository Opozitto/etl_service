from io import BytesIO
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes import documents as documents_routes
from app.core.config import get_settings
from app.main import app
from app.search.index import CorpusSearchEngine
from app.services.document_service import DocumentService


client = TestClient(app)


def _make_png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_process_txt_document() -> None:
    payload = b"1. Intro\n\nEnvironmental baseline text.\n\n- item one"
    response = client.post(
        "/api/v1/documents/process",
        files={"file": ("sample.txt", payload, "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()["document"]
    assert data["source"]["filename"] == "sample.txt"
    assert data["metadata"]["block_count"] >= 2
    assert data["sections"]
    assert data["chunks"]


def test_process_known_unsupported_image_format_returns_clear_error() -> None:
    response = client.post(
        "/api/v1/documents/process",
        files={"file": ("sample.heic", b"fake-image-payload", "image/heic")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert ".heic" in detail
    assert ".jpg, .jpeg, .png" in detail
    assert "OCR" in detail


def test_process_xls_document_returns_table_metadata(monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[1]
    sample_path = project_root / "first_test_data" / "Форма 4 Затраты на сырье.XLS"
    smoke_root = project_root / "tests" / ".stage14_api_smoke_xls"
    storage_dir = smoke_root / "storage"
    shutil.rmtree(smoke_root, ignore_errors=True)
    storage_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()
    service = DocumentService()
    monkeypatch.setattr(documents_routes, "service", service)
    monkeypatch.setattr(documents_routes, "search_engine", CorpusSearchEngine(service.storage))

    try:
        response = client.post(
            "/api/v1/documents/process",
            files={
                "file": (
                    sample_path.name,
                    sample_path.read_bytes(),
                    "application/vnd.ms-excel",
                )
            },
        )

        assert response.status_code == 200
        document = response.json()["document"]
        assert document["source"]["filename"] == sample_path.name
        assert document["source"]["extension"] == ".xls"
        assert document["metadata"]["table_count"] >= 1
        assert document["metadata"]["block_count"] >= 2
        assert document["blocks"]
        assert any(block["type"] == "table" for block in document["blocks"])
        assert document["chunks"]
        assert any("Строка" in chunk["text"] for chunk in document["chunks"])
        assert any("сырья" in chunk["text"].lower() for chunk in document["chunks"])
        assert document["processing_info"]["features"]["tables_detected"] is True
        assert Path(document["artifacts"]["result_json_path"]).is_file()

        search_response = client.post(
            "/api/v1/search",
            json={"query": "сырья", "top_k": 3},
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["hits"]
        assert any("Строка" in hit["snippet"] for hit in search_data["hits"])

        ask_response = client.post(
            "/api/v1/ask",
            json={"question": "Где указаны затраты на приобретение сырья?", "top_k": 3, "max_sentences": 2},
        )
        assert ask_response.status_code == 200
        ask_data = ask_response.json()
        assert ask_data["sources"]
        assert ask_data["hits"]
        assert any("Строка" in source["snippet"] for source in ask_data["sources"])
    finally:
        get_settings.cache_clear()
        shutil.rmtree(smoke_root, ignore_errors=True)


def test_process_standalone_png_image_returns_image_metadata(monkeypatch) -> None:
    project_root = Path(__file__).resolve().parents[1]
    smoke_root = project_root / "tests" / ".stage12_api_smoke_png"
    storage_dir = smoke_root / "storage"
    shutil.rmtree(smoke_root, ignore_errors=True)
    storage_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("ETL_STORAGE_DIR", str(storage_dir))
    get_settings.cache_clear()
    monkeypatch.setattr(documents_routes, "service", DocumentService())
    monkeypatch.setattr(
        documents_routes,
        "search_engine",
        CorpusSearchEngine(documents_routes.service.storage),
    )

    try:
        response = client.post(
            "/api/v1/documents/process",
            files={"file": ("sample.png", _make_png_bytes(), "image/png")},
        )

        assert response.status_code == 200
        document = response.json()["document"]
        assert document["source"]["filename"] == "sample.png"
        assert document["source"]["extension"] == ".png"
        assert document["metadata"]["image_count"] == 1
        assert document["images"]
        assert document["blocks"]
        assert document["blocks"][0]["type"] == "image"
        assert document["processing_info"]["features"]["images_detected"] is True
        assert document["processing_info"]["features"]["ocr_used"] is False
    finally:
        get_settings.cache_clear()
        shutil.rmtree(smoke_root, ignore_errors=True)


def test_search_and_ask_work_for_uploaded_document() -> None:
    payload = (
        "1. \u041d\u043e\u0440\u043c\u0430\u0442\u0438\u0432\u044b\n\n"
        "\u041f\u0440\u0435\u0434\u0435\u043b\u044c\u043d\u043e \u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0435 \u0432\u044b\u0431\u0440\u043e\u0441\u044b \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u044f\u044e\u0442\u0441\u044f \u0434\u043b\u044f \u043f\u0440\u0435\u0434\u043f\u0440\u0438\u044f\u0442\u0438\u044f.\n\n"
        "2. \u0412\u044b\u0432\u043e\u0434\n\n"
        "\u041f\u0440\u043e\u0435\u043a\u0442 \u043d\u043e\u0440\u043c\u0430\u0442\u0438\u0432\u043e\u0432 \u043f\u0440\u0435\u0434\u0435\u043b\u044c\u043d\u043e \u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0445 \u0432\u044b\u0431\u0440\u043e\u0441\u043e\u0432 \u043f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043b\u0435\u043d."
    ).encode("utf-8")

    process_response = client.post(
        "/api/v1/documents/process",
        files={"file": ("norms.txt", payload, "text/plain")},
    )
    assert process_response.status_code == 200

    search_response = client.post(
        "/api/v1/search",
        json={"query": "\u043f\u0440\u0435\u0434\u0435\u043b\u044c\u043d\u043e \u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0435 \u0432\u044b\u0431\u0440\u043e\u0441\u044b", "top_k": 3},
    )
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["hits"]
    assert any(
        "предельно" in hit["snippet"].lower() and "выброс" in hit["snippet"].lower()
        for hit in search_data["hits"]
    )

    ask_response = client.post(
        "/api/v1/ask",
        json={
            "question": "\u0427\u0442\u043e \u0441\u043a\u0430\u0437\u0430\u043d\u043e \u043f\u0440\u043e \u043f\u0440\u0435\u0434\u0435\u043b\u044c\u043d\u043e \u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c\u044b\u0435 \u0432\u044b\u0431\u0440\u043e\u0441\u044b?",
            "top_k": 3,
            "max_sentences": 2,
        },
    )
    assert ask_response.status_code == 200
    ask_data = ask_response.json()
    assert ask_data["sources"]
    assert ask_data["hits"]
    assert ask_data["strategy"] == "extractive-rag-baseline"
    assert ask_data["answer"]
    assert "выброс" in ask_data["answer"].lower()
    first_source = ask_data["sources"][0]
    assert first_source["rank"] == 1
    assert first_source["document_id"]
    assert first_source["chunk_id"]
    assert first_source["snippet"]
    assert first_source["score"] >= 0
    assert "filename" in first_source
    assert "section_title" in first_source

    no_hit_response = client.post(
        "/api/v1/ask",
        json={"question": "qwertyuiopasdfghjklzxcvbnm", "top_k": 3, "max_sentences": 2},
    )
    assert no_hit_response.status_code == 200
    no_hit_data = no_hit_response.json()
    assert no_hit_data["answer"]
    assert no_hit_data["sources"] == []
    assert no_hit_data["hits"] == []


def test_corpus_stats_and_reindex_endpoints() -> None:
    process_response = client.post(
        "/api/v1/documents/process",
        files={"file": ("stats.txt", b"1. Section\n\nProduction corpus text for stats.", "text/plain")},
    )
    assert process_response.status_code == 200

    stats_response = client.get("/api/v1/corpus/stats")
    assert stats_response.status_code == 200
    stats_data = stats_response.json()
    assert stats_data["document_count"] >= 1
    assert stats_data["chunk_count"] >= 1
    assert stats_data["manifest_record_count"] >= 1

    reindex_response = client.post("/api/v1/corpus/reindex")
    assert reindex_response.status_code == 200
    reindex_data = reindex_response.json()
    assert reindex_data["status"] == "reindexed"
    assert reindex_data["document_count"] >= 1
    assert reindex_data["chunk_count"] >= 1

    manifest_response = client.get("/api/v1/corpus/manifest")
    assert manifest_response.status_code == 200
    manifest_data = manifest_response.json()
    assert manifest_data
    assert any(item["filename"] == "stats.txt" for item in manifest_data)
