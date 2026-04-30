from __future__ import annotations

import re
from collections import Counter, defaultdict
from math import log
from typing import Optional

from app.schemas.api import AskResponse, AskSource, SearchHit
from app.search.store import IndexedChunk, SearchIndexStore
from app.storage.filesystem import FileStorage


TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;])\s+")
STOPWORDS = {
    "и",
    "в",
    "во",
    "на",
    "с",
    "со",
    "что",
    "как",
    "для",
    "по",
    "из",
    "к",
    "ко",
    "о",
    "об",
    "от",
    "до",
    "у",
    "не",
    "это",
    "а",
    "или",
    "ли",
    "про",
    "сказано",
    "говорится",
    "вопрос",
    "корпусе",
}
RUSSIAN_SUFFIXES = (
    "иями",
    "ями",
    "ами",
    "его",
    "ого",
    "ему",
    "ому",
    "ыми",
    "ими",
    "иях",
    "ах",
    "ях",
    "иям",
    "ям",
    "ием",
    "ем",
    "ам",
    "ом",
    "ев",
    "ов",
    "ие",
    "ые",
    "ое",
    "ей",
    "ий",
    "ый",
    "ой",
    "ым",
    "им",
    "ую",
    "юю",
    "ая",
    "яя",
    "ою",
    "ею",
    "ия",
    "ья",
    "ью",
    "ию",
    "ых",
    "их",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "о",
    "у",
    "ю",
)


def tokenize(text: str) -> list[str]:
    return [token.lower().replace("ё", "е") for token in TOKEN_RE.findall(text)]


def stem_token(token: str) -> str:
    if len(token) <= 4:
        return token
    for suffix in RUSSIAN_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def normalize_search_tokens(text: str) -> list[str]:
    normalized: list[str] = []
    for token in tokenize(text):
        if token in STOPWORDS or len(token) <= 1:
            continue
        normalized.append(stem_token(token))
    return normalized


class CorpusSearchEngine:
    def __init__(self, storage: Optional[FileStorage] = None) -> None:
        self.storage = storage or FileStorage()
        self.index_store = SearchIndexStore(self.storage)

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        query_tokens = normalize_search_tokens(query)
        if not query_tokens:
            return []

        index = self.index_store.load()
        entries = index.entries
        if not entries:
            return []

        query_terms = set(query_tokens)
        query_phrase = normalize_for_match(query)
        doc_freq = Counter(index.doc_frequencies)
        avg_len = index.avg_chunk_length or 1.0

        raw_hits: list[tuple[float, IndexedChunk]] = []
        for entry in entries:
            score = self._score_entry(
                entry=entry,
                query_tokens=query_tokens,
                query_terms=query_terms,
                query_phrase=query_phrase,
                doc_freq=doc_freq,
                avg_len=avg_len,
                corpus_size=len(entries),
            )
            if score > 0:
                raw_hits.append((score, entry))

        raw_hits.sort(key=lambda item: item[0], reverse=True)
        return self._dedupe_and_format_hits(raw_hits, query_terms, top_k)

    def ask(self, question: str, top_k: int = 5, max_sentences: int = 4) -> AskResponse:
        hits = self.search(question, top_k=top_k)
        sources = [
            AskSource(
                rank=rank,
                score=hit.score,
                document_id=hit.document_id,
                filename=hit.filename,
                source_filename=hit.source_filename,
                source_type=hit.source_type,
                title=hit.title,
                chunk_id=hit.chunk_id,
                chunk_order=hit.chunk_order,
                section_id=hit.section_id,
                section_title=hit.section_title,
                section_path=hit.section_path,
                page_start=hit.page_start,
                page_end=hit.page_end,
                source_block_ids=hit.source_block_ids,
                table_id=hit.table_id,
                table_row_index=hit.table_row_index,
                location_label=hit.location_label,
                citation_label=hit.citation_label,
                snippet=hit.snippet,
            )
            for rank, hit in enumerate(hits, start=1)
        ]
        if not hits:
            return AskResponse(
                question=question,
                answer="нет информации в корпусе",
                sources=[],
                hits=[],
                strategy="extractive-rag-baseline",
            )

        query_terms = set(normalize_search_tokens(question))
        candidate_sentences: list[tuple[float, str]] = []
        seen_sentences: set[str] = set()

        for hit in hits:
            for sentence in split_sentences(hit.snippet):
                normalized = normalize_for_match(sentence)
                if not normalized or normalized in seen_sentences:
                    continue
                seen_sentences.add(normalized)
                overlap = len(query_terms & set(normalize_search_tokens(sentence)))
                if overlap == 0:
                    continue
                candidate_sentences.append((overlap + hit.score, sentence.strip()))

        candidate_sentences.sort(key=lambda item: item[0], reverse=True)
        selected = [sentence for _, sentence in candidate_sentences[:max_sentences]]
        answer = " ".join(selected) if selected else hits[0].snippet
        return AskResponse(
            question=question,
            answer=answer,
            sources=sources,
            hits=hits,
            strategy="extractive-rag-baseline",
        )

    def _score_entry(
        self,
        entry: IndexedChunk,
        query_tokens: list[str],
        query_terms: set[str],
        query_phrase: str,
        doc_freq: Counter[str],
        avg_len: float,
        corpus_size: int,
    ) -> float:
        normalized_tokens = entry.normalized_tokens or normalize_search_tokens(entry.text)
        term_counts = Counter(normalized_tokens)
        score = bm25_score(query_tokens, term_counts, doc_freq, max(len(normalized_tokens), 1), avg_len, corpus_size)
        overlap = len(query_terms & set(normalized_tokens))
        if overlap == 0:
            return 0.0

        score += overlap * 0.45
        normalized_text = normalize_for_match(entry.text)
        if query_phrase and query_phrase in normalized_text:
            score += 2.0
        if entry.section_title and query_phrase in normalize_for_match(entry.section_title):
            score += 1.0
        if query_phrase in normalize_for_match(entry.title):
            score += 0.8
        if entry.section_title:
            score += len(query_terms & set(normalize_search_tokens(entry.section_title))) * 0.25
        score += len(query_terms & set(normalize_search_tokens(entry.title))) * 0.15
        score *= heading_penalty(entry)
        score *= duplication_penalty(entry.text)
        if len(normalized_tokens) >= 25:
            score += 0.35
        return score

    def _dedupe_and_format_hits(
        self, raw_hits: list[tuple[float, IndexedChunk]], query_terms: set[str], top_k: int
    ) -> list[SearchHit]:
        results: list[SearchHit] = []
        seen_keys: set[tuple[str, str, Optional[str], str]] = set()
        per_source_counts: defaultdict[str, int] = defaultdict(int)

        for score, entry in raw_hits:
            dedupe_key = (
                entry.filename.lower(),
                entry.source_checksum,
                entry.section_id,
                normalize_for_match(entry.text[:200]),
            )
            if dedupe_key in seen_keys:
                continue
            if per_source_counts[entry.source_checksum] >= 3:
                continue
            seen_keys.add(dedupe_key)
            per_source_counts[entry.source_checksum] += 1
            results.append(
                SearchHit(
                    document_id=entry.document_id,
                    title=entry.title,
                    filename=entry.filename,
                    source_filename=entry.source_filename or entry.filename,
                    source_type=entry.source_type,
                    score=round(score, 4),
                    chunk_id=entry.chunk_id,
                    chunk_order=entry.chunk_order,
                    section_id=entry.section_id,
                    section_title=entry.section_title,
                    section_path=entry.section_path,
                    page_start=entry.page_start,
                    page_end=entry.page_end,
                    source_block_ids=entry.source_block_ids,
                    table_id=entry.table_id,
                    table_row_index=entry.table_row_index,
                    location_label=entry.location_label,
                    citation_label=entry.citation_label,
                    snippet=build_snippet(entry.text, query_terms),
                )
            )
            if len(results) >= top_k:
                break
        return results


def bm25_score(
    query_tokens: list[str],
    term_counts: Counter[str],
    doc_freq: Counter[str],
    doc_len: int,
    avg_len: float,
    corpus_size: int,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    score = 0.0
    for token in query_tokens:
        tf = term_counts.get(token, 0)
        if tf == 0:
            continue
        df = doc_freq.get(token, 0)
        idf = log(1 + ((corpus_size - df + 0.5) / (df + 0.5)))
        denom = tf + k1 * (1 - b + b * (doc_len / max(avg_len, 1.0)))
        score += idf * ((tf * (k1 + 1)) / max(denom, 1e-9))
    return score


def normalize_for_match(text: str) -> str:
    return " ".join(normalize_search_tokens(text))


def heading_penalty(entry: IndexedChunk) -> float:
    text = normalize_whitespace(entry.text)
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 1.0
    upper_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    short_heading = len(entry.tokens) <= 18 and upper_ratio > 0.7
    repeated_title = bool(entry.section_title) and normalize_whitespace(entry.section_title) == text
    if short_heading and repeated_title:
        return 0.28
    if short_heading:
        return 0.42
    if repeated_title:
        return 0.55
    return 1.0


def duplication_penalty(text: str) -> float:
    cleaned = sanitize_snippet_source(text)
    words = cleaned.split()
    if len(words) >= 6:
        half = len(words) // 2
        left = " ".join(words[:half])
        right = " ".join(words[half:])
        if normalize_for_match(left) == normalize_for_match(right):
            return 0.7
    return 1.0


def build_snippet(text: str, query_terms: set[str], window: int = 320) -> str:
    text = sanitize_snippet_source(text)
    normalized_text = normalize_for_match(text)
    words = text.split()
    if not words:
        return ""
    best_position = 0
    raw_words = [token.lower() for token in words]
    for index, word in enumerate(raw_words):
        stemmed = stem_token(word.strip(".,:;!?()[]{}\"'"))
        if stemmed in query_terms:
            best_position = index
            break
    approx_char_position = len(" ".join(words[:best_position]))
    start = max(0, approx_char_position - window // 3)
    end = min(len(text), start + window)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return normalize_whitespace(snippet)


def sanitize_snippet_source(text: str) -> str:
    lines = [normalize_whitespace(line) for line in text.splitlines() if normalize_whitespace(line)]
    deduped: list[str] = []
    last = ""
    for line in lines:
        if normalize_for_match(line) == normalize_for_match(last):
            continue
        deduped.append(line)
        last = line
    joined = " ".join(deduped) if deduped else normalize_whitespace(text)
    words = joined.split()
    if len(words) >= 6:
        half = len(words) // 2
        left = " ".join(words[:half])
        right = " ".join(words[half:])
        if normalize_for_match(left) == normalize_for_match(right):
            return left
    return joined


def split_sentences(text: str) -> list[str]:
    return [normalize_whitespace(item) for item in SENTENCE_SPLIT_RE.split(text) if item.strip()]


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
