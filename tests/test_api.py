from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
    assert "Unsupported image format" in detail
    assert ".heic" in detail
    assert "Supported standalone image formats: .jpg, .jpeg, .png" in detail
    assert "OCR is not implemented yet." in detail


def test_search_and_ask_work_for_uploaded_document() -> None:
    payload = (
        "1. Нормативы\n\n"
        "Предельно допустимые выбросы определяются для предприятия.\n\n"
        "2. Вывод\n\n"
        "Проект нормативов предельно допустимых выбросов подготовлен."
    ).encode("utf-8")

    process_response = client.post(
        "/api/v1/documents/process",
        files={"file": ("norms.txt", payload, "text/plain")},
    )
    assert process_response.status_code == 200

    search_response = client.post(
        "/api/v1/search",
        json={"query": "предельно допустимые выбросы", "top_k": 3},
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
        json={"question": "Что сказано про предельно допустимые выбросы?", "top_k": 3, "max_sentences": 2},
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
    assert no_hit_data["answer"] == "нет информации в корпусе"
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
