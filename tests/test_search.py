from app.search.index import build_snippet, bm25_score, normalize_search_tokens, stem_token


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
