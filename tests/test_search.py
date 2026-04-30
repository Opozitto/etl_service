from pathlib import Path

from app.search.index import CorpusSearchEngine, build_snippet, bm25_score, normalize_search_tokens, stem_token
from app.search.store import CorpusIndex, IndexedChunk, SearchIndexStore
from app.storage.filesystem import FileStorage


def test_build_snippet_centers_on_query_term() -> None:
    text = (
        "Введение. Общая информация. "
        "Предельно допустимые выбросы рассчитываются по утвержденной методике. "
        "Заключение."
    )
    snippet = build_snippet(text, {"выброс", "предельн"})
    assert "предельно допустимые выбросы" in snippet.lower()


def test_bm25_score_prefers_matching_document() -> None:
    query_tokens = normalize_search_tokens("предельно допустимые выбросы")
    matching = normalize_search_tokens("проект нормативов предельно допустимые выбросы")
    non_matching = normalize_search_tokens("охрана труда и промышленная безопасность")
    doc_freq = {"предельн": 1, "допустим": 1, "выброс": 1}

    matching_score = bm25_score(query_tokens, {token: matching.count(token) for token in set(matching)}, doc_freq, len(matching), 5, 2)
    non_matching_score = bm25_score(query_tokens, {token: non_matching.count(token) for token in set(non_matching)}, doc_freq, len(non_matching), 5, 2)

    assert matching_score > non_matching_score


def test_russian_normalization_handles_close_word_forms() -> None:
    assert stem_token("допустимые") == stem_token("допустимы")
    assert stem_token("выбросы") == stem_token("выброс")


def test_search_and_ask_expose_source_location_fields(tmp_path: Path) -> None:
    storage = FileStorage(storage_root=tmp_path / "storage")
    store = SearchIndexStore(storage)
    store.save(
        CorpusIndex(
            updated_at="2026-05-01T10:00:00",
            document_count=1,
            chunk_count=1,
            avg_chunk_length=6.0,
            doc_frequencies={"эколог": 1, "проект": 1},
            entries=[
                IndexedChunk(
                    document_id="doc-1",
                    source_checksum="abc123",
                    filename="source.pdf",
                    source_filename="source.pdf",
                    source_type="pdf",
                    title="Source document",
                    chunk_id="chk-1",
                    chunk_order=3,
                    section_id="sec-2",
                    section_title="1. Ecology",
                    section_path=["Document", "1. Ecology"],
                    page_start=5,
                    page_end=5,
                    source_block_ids=["blk-1", "blk-2"],
                    table_id="tbl-1",
                    table_row_index=2,
                    location_label="source.pdf - table tbl-1 - row 2 - page 5",
                    citation_label="source.pdf - table tbl-1 - row 2 - page 5",
                    text="Экологический проект содержит расчет выбросов.",
                    tokens=["экологический", "проект", "содержит", "расчет", "выбросов"],
                    normalized_tokens=normalize_search_tokens("Экологический проект содержит расчет выбросов."),
                    token_count=5,
                )
            ],
        )
    )
    engine = CorpusSearchEngine(storage)

    hits = engine.search("экологический проект", top_k=1)
    answer = engine.ask("Что содержит экологический проект?", top_k=1)

    assert hits
    assert hits[0].source_filename == "source.pdf"
    assert hits[0].source_type == "pdf"
    assert hits[0].chunk_order == 3
    assert hits[0].section_path == ["Document", "1. Ecology"]
    assert hits[0].page_start == 5
    assert hits[0].page_end == 5
    assert hits[0].source_block_ids == ["blk-1", "blk-2"]
    assert hits[0].table_id == "tbl-1"
    assert hits[0].table_row_index == 2
    assert hits[0].location_label == "source.pdf - table tbl-1 - row 2 - page 5"
    assert answer.sources[0].citation_label == hits[0].citation_label
