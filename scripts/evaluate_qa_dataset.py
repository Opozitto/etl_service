from __future__ import annotations

import argparse
import csv
import json
import re
from time import perf_counter
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from app.core.config import get_settings
from app.schemas.api import SearchHit
from app.schemas.document import StructuredDocument
from app.search.index import CorpusSearchEngine, normalize_search_tokens, normalize_for_match, tokenize
from app.search.store import CorpusIndex, IndexedChunk


REPORT_VERSION = "stage24_qa_retrieval_readiness_v1"
REPORT_DETAIL_LEVELS = ("summary", "failures", "full")
DEFAULT_FAILURES_LIMIT = 10
DEFAULT_MISSING_SOURCE_LIMIT = 5
SCOPE_NOTE = (
    "QA/retrieval readiness evaluation for future source-backed answer layer / RAG layer; "
    "not a guarantee of generative answer quality. No LLM, no embeddings, no generation."
)
QUESTION_COLUMNS = ("Вопрос", "question", "query")
ANSWER_COLUMNS = ("Ответ", "answer", "expected_answer", "gold_answer")
DOCUMENT_COLUMNS = ("Документ", "Источник", "source", "document", "expected_document", "file", "filename")
ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "cp1251")
DELIMITER_FALLBACKS = ("\t", ";", ",", "|")
TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)
DOCUMENT_EXTENSION_RE = re.compile(r"\.(pdf|docx?|rtf|txt|xlsx?|jpe?g|png)$", flags=re.IGNORECASE)
PUNCT_SPACE_RE = re.compile(r"[^\w]+", flags=re.UNICODE)

TABLE_QUESTION_TERMS = (
    "таблица",
    "строка",
    "столбец",
    "графа",
    "ячейка",
    "значение",
    "показатель",
    "координаты",
    "расчетная точка",
    "точка воздействия",
    "номер источника",
    "источник №",
    "изав №",
    "параметры выбросов",
    "перечень загрязняющих веществ",
    "г/с",
    "т/год",
    "мг/м3",
    "мг/м3",
    "м3/с",
    "м3/ч",
    "мг/м³",
    "м³/с",
    "м³/ч",
)


@dataclass(frozen=True)
class QARow:
    row_number: int
    question: str
    expected_answer: str
    expected_document: str


class ReadOnlyIndexStore:
    def __init__(self, index: CorpusIndex) -> None:
        self._index = index

    def load(self) -> CorpusIndex:
        return self._index


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def normalize_column_name(name: str) -> str:
    return normalize_text(name.lstrip("\ufeff")).lower().replace("ё", "е")


def normalize_document_key(text: str) -> str:
    normalized = normalize_text(text).lower().replace("ё", "е")
    normalized = DOCUMENT_EXTENSION_RE.sub("", normalized)
    normalized = PUNCT_SPACE_RE.sub(" ", normalized)
    return normalize_text(normalized)


def token_set(text: str) -> set[str]:
    return set(normalize_search_tokens(text))


def token_recall(expected: str, actual: str) -> float:
    expected_tokens = token_set(expected)
    if not expected_tokens:
        return 0.0
    actual_tokens = token_set(actual)
    if not actual_tokens:
        return 0.0
    return round(len(expected_tokens & actual_tokens) / len(expected_tokens), 4)


def preview(text: str, max_chars: int = 220) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def normalize_expected_source(text: str) -> str:
    normalized = normalize_text(text).lower().replace("ё", "е")
    normalized = normalized.rstrip(".!?,;: ")
    return normalized


def is_missing_expected_source(text: str) -> bool:
    normalized = normalize_expected_source(text)
    if not normalized:
        return True
    return normalized in {
        "-",
        "—",
        "n/a",
        "na",
        "none",
        "null",
        "нет",
        "не указан",
        "не указано",
        "отсутствует",
    }


def resolve_delimiter_override(delimiter: str | None) -> str | None:
    if delimiter is None:
        return None
    normalized = delimiter.strip().lower()
    if normalized in {"\\t", "tab", "tsv", "t"}:
        return "\t"
    if normalized in {";", "semicolon", "scsv"}:
        return ";"
    if normalized in {",", "comma", "csv"}:
        return ","
    if normalized in {"|", "pipe"}:
        return "|"
    return delimiter


def score_delimiter(raw_text: str, delimiter: str, field_candidates: Sequence[str]) -> tuple[int, int, int]:
    reader = csv.reader(raw_text.splitlines(), delimiter=delimiter)
    rows = [row for row in reader if row]
    if not rows:
        return (0, 0, 0)
    headers = rows[0]
    normalized_headers = [normalize_column_name(header) for header in headers]
    candidate_headers = {normalize_column_name(candidate) for candidate in field_candidates}
    recognized = sum(1 for header in normalized_headers if header in candidate_headers)
    widest_row = max((len(row) for row in rows[:5]), default=0)
    return (recognized, widest_row, len(headers))


def choose_delimiter(raw_text: str, override: str | None, field_candidates: Sequence[str]) -> str:
    resolved_override = resolve_delimiter_override(override)
    if resolved_override:
        return resolved_override

    candidate_delimiters: list[str] = []
    try:
        sniffed = csv.Sniffer().sniff(raw_text[:4096], delimiters="\t;,|")
        candidate_delimiters.append(sniffed.delimiter)
    except csv.Error:
        pass
    for delimiter in DELIMITER_FALLBACKS:
        if delimiter not in candidate_delimiters:
            candidate_delimiters.append(delimiter)

    scored = [(score_delimiter(raw_text, delimiter, field_candidates), delimiter) for delimiter in candidate_delimiters]
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_delimiter = scored[0]
    if best_score == (0, 0, 0):
        return "\t" if "\t" in raw_text else ";"
    return best_delimiter


def read_csv_rows(path: Path, encoding: str | None = None, delimiter: str | None = None) -> tuple[list[dict[str, str]], list[str], str, str]:
    encodings = (encoding,) if encoding else ENCODING_CANDIDATES
    last_error: Exception | None = None
    for candidate_encoding in encodings:
        try:
            raw_text = path.read_text(encoding=candidate_encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        selected_delimiter = choose_delimiter(raw_text, delimiter, QUESTION_COLUMNS + ANSWER_COLUMNS + DOCUMENT_COLUMNS)
        reader = csv.DictReader(raw_text.splitlines(), delimiter=selected_delimiter)
        fieldnames = list(reader.fieldnames or [])
        rows = [
            {str(key): normalize_text(value or "") for key, value in row.items() if key is not None}
            for row in reader
        ]
        return rows, fieldnames, candidate_encoding, selected_delimiter
    raise ValueError(f"cannot read CSV {path}: {last_error}") from last_error


def resolve_column(fieldnames: Sequence[str], override: str | None, candidates: Sequence[str], label: str) -> str:
    if override:
        override_key = normalize_column_name(override)
        for fieldname in fieldnames:
            if normalize_column_name(fieldname) == override_key:
                return fieldname
        raise ValueError(
            f"Column '{override}' for {label} not found. Available columns: {', '.join(fieldnames) or 'none'}"
        )
    normalized_map = {normalize_column_name(name): name for name in fieldnames}
    for candidate in candidates:
        found = normalized_map.get(normalize_column_name(candidate))
        if found:
            return found
    raise ValueError(
        "Cannot detect {label} column. Available columns: {columns}. "
        "Use --question-column / --answer-column / --document-column.".format(
            label=label,
            columns=", ".join(fieldnames) or "none",
        )
    )


def load_qa_rows(
    qa_path: Path,
    question_column: str | None = None,
    answer_column: str | None = None,
    document_column: str | None = None,
    encoding: str | None = None,
    delimiter: str | None = None,
    max_questions: int | None = None,
) -> tuple[list[QARow], dict[str, Any]]:
    raw_rows, fieldnames, selected_encoding, selected_delimiter = read_csv_rows(
        qa_path,
        encoding=encoding,
        delimiter=delimiter,
    )
    question_col = resolve_column(fieldnames, question_column, QUESTION_COLUMNS, "question")
    answer_col = resolve_column(fieldnames, answer_column, ANSWER_COLUMNS, "answer")
    document_col = resolve_column(fieldnames, document_column, DOCUMENT_COLUMNS, "document/source")

    rows: list[QARow] = []
    for index, raw in enumerate(raw_rows, start=2):
        question = normalize_text(raw.get(question_col, ""))
        if not question:
            continue
        rows.append(
            QARow(
                row_number=index,
                question=question,
                expected_answer=normalize_text(raw.get(answer_col, "")),
                expected_document=normalize_text(raw.get(document_col, "")),
            )
        )
        if max_questions is not None and len(rows) >= max_questions:
            break

    return rows, {
        "encoding": selected_encoding,
        "delimiter": selected_delimiter,
        "columns": {
            "question": question_col,
            "answer": answer_col,
            "document": document_col,
        },
        "available_columns": fieldnames,
    }


def load_documents_from_results(results_dir: Path) -> tuple[list[StructuredDocument], list[str]]:
    documents: list[StructuredDocument] = []
    skipped_files: list[str] = []
    if not results_dir.exists():
        return documents, skipped_files
    for path in sorted(results_dir.glob("*.json")):
        try:
            documents.append(StructuredDocument.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception:
            skipped_files.append(str(path))
    return documents, skipped_files


def build_read_only_index(documents: Iterable[StructuredDocument]) -> CorpusIndex:
    entries: list[IndexedChunk] = []
    seen_chunks: set[tuple[str, str, str | None, str]] = set()
    for document in documents:
        section_titles = {section.section_id: section.title for section in document.sections}
        for chunk in document.chunks:
            tokens = tokenize(chunk.text)
            normalized_tokens = normalize_search_tokens(chunk.text)
            if not tokens:
                continue
            dedupe_key = (
                document.source.filename.lower(),
                document.source.checksum_sha256,
                chunk.section_id,
                normalize_for_match(chunk.text[:200]),
            )
            if dedupe_key in seen_chunks:
                continue
            seen_chunks.add(dedupe_key)
            entries.append(
                IndexedChunk(
                    document_id=document.metadata.document_id,
                    source_checksum=document.source.checksum_sha256,
                    filename=document.source.filename,
                    title=document.metadata.title,
                    chunk_id=chunk.chunk_id,
                    section_id=chunk.section_id,
                    section_title=section_titles.get(chunk.section_id or ""),
                    text=chunk.text,
                    tokens=tokens,
                    normalized_tokens=normalized_tokens,
                    token_count=len(tokens),
                )
            )

    doc_frequencies: Counter[str] = Counter()
    for entry in entries:
        doc_frequencies.update(set(entry.normalized_tokens))
    unique_sources = {(entry.source_checksum, entry.filename.lower()) for entry in entries}
    avg_chunk_length = sum(entry.token_count for entry in entries) / max(len(entries), 1)
    return CorpusIndex(
        updated_at="read-only",
        document_count=len(unique_sources),
        chunk_count=len(entries),
        avg_chunk_length=avg_chunk_length,
        doc_frequencies=dict(doc_frequencies),
        entries=entries,
    )


def build_search_engine(index: CorpusIndex) -> CorpusSearchEngine:
    engine = CorpusSearchEngine.__new__(CorpusSearchEngine)
    engine.index_store = ReadOnlyIndexStore(index)  # type: ignore[assignment]
    return engine


def document_matches(expected: str, hit: SearchHit) -> bool:
    expected_key = normalize_document_key(expected)
    if not expected_key:
        return False
    candidates = [
        hit.filename,
        hit.title,
        hit.document_id,
        f"{hit.filename} {hit.title}",
    ]
    candidate_keys = [normalize_document_key(candidate) for candidate in candidates if candidate]
    return any(
        expected_key == candidate_key or expected_key in candidate_key or candidate_key in expected_key
        for candidate_key in candidate_keys
        if candidate_key
    )


def hit_at(expected_document: str, hits: Sequence[SearchHit], k: int) -> bool:
    if not expected_document:
        return False
    return any(document_matches(expected_document, hit) for hit in hits[:k])


def is_table_question(question: str, expected_answer: str = "", expected_document: str = "") -> bool:
    haystack = normalize_text(f"{question} {expected_answer} {expected_document}").lower().replace("ё", "е")
    token_haystack = set(tokenize(haystack))
    strong_terms = {
        "таблица",
        "строка",
        "столбец",
        "графа",
        "ячейка",
        "значение",
        "показатель",
        "концентрация",
        "концентрации",
        "координаты",
    }
    if token_haystack & strong_terms:
        return True
    explicit_phrases = (
        "номер источника",
        "источник №",
        "изав №",
        "параметры выбросов",
        "перечень загрязняющих веществ",
        "расчетная точка",
        "точка воздействия",
        "концентрация загрязняющего вещества",
        "максимальная концентрация",
        "приземная концентрация",
    )
    if any(phrase in haystack for phrase in explicit_phrases):
        return True
    if any(unit in haystack for unit in ("г/с", "т/год", "мг/м3", "мг/м³", "м3/с", "м3/ч", "м³/с", "м³/ч")):
        return True
    if any(marker in haystack for marker in ("какое значение", "укажите значение", "сколько")) and any(
        unit in haystack for unit in ("г/с", "т/год", "мг/м3", "мг/м³", "м3/с", "м3/ч", "м³/с", "м³/ч")
    ):
        return True
    if "источник" in token_haystack and ("№" in haystack or "номер" in token_haystack):
        return True
    return False


def format_hit(hit: SearchHit, rank: int) -> dict[str, Any]:
    return {
        "rank": rank,
        "score": hit.score,
        "document_id": hit.document_id,
        "filename": hit.filename,
        "title": hit.title,
        "chunk_id": hit.chunk_id,
        "section_id": hit.section_id,
        "section_title": hit.section_title,
        "snippet": hit.snippet,
    }


def make_timings(
    *,
    load_qa_seconds: float = 0.0,
    load_results_seconds: float = 0.0,
    evaluate_seconds: float = 0.0,
    write_report_seconds: float = 0.0,
    questions_total: int = 0,
) -> dict[str, float]:
    total_seconds = load_qa_seconds + load_results_seconds + evaluate_seconds + write_report_seconds
    return {
        "load_qa_seconds": round(load_qa_seconds, 4),
        "load_results_seconds": round(load_results_seconds, 4),
        "evaluate_seconds": round(evaluate_seconds, 4),
        "write_report_seconds": round(write_report_seconds, 4),
        "total_seconds": round(total_seconds, 4),
        "avg_seconds_per_question": round(total_seconds / questions_total, 4) if questions_total else 0.0,
    }


def apply_report_detail_level(
    report: dict[str, Any],
    report_detail_level: str,
) -> dict[str, Any]:
    if report_detail_level == "full":
        return report
    if report_detail_level == "failures":
        report["results"] = [item for item in report.get("results", []) if item.get("status") != "pass"]
        return report
    if report_detail_level == "summary":
        report["results"] = []
        return report
    raise ValueError(f"Unsupported report detail level: {report_detail_level}")


def evaluate_qa_rows(
    rows: Sequence[QARow],
    documents: Sequence[StructuredDocument],
    results_dir: Path,
    top_k: int = 5,
    skipped_result_files: Sequence[str] = (),
    skip_answer_overlap: bool = False,
    report_detail_level: str = "full",
    failures_limit: int = DEFAULT_FAILURES_LIMIT,
    missing_source_limit: int = DEFAULT_MISSING_SOURCE_LIMIT,
    top_hits_limit: int | None = None,
) -> dict[str, Any]:
    if report_detail_level not in REPORT_DETAIL_LEVELS:
        raise ValueError(f"Unsupported report detail level: {report_detail_level}")
    if failures_limit < 0 or missing_source_limit < 0:
        raise ValueError("Report limits must be greater than or equal to 0")
    stored_top_hits_limit = top_k if top_hits_limit is None else top_hits_limit
    if stored_top_hits_limit < 0:
        raise ValueError("top_hits_limit must be greater than or equal to 0")

    base_summary = {
        "questions_total": len(rows),
        "evaluated_questions": 0,
        "skipped_questions": len(rows),
        "source_expected_count": 0,
        "missing_expected_source_count": 0,
        "document_hit_at_1": 0,
        "document_hit_at_3": 0,
        "document_hit_at_5": 0,
        "source_hit_rate": 0.0,
        "answer_overlap_avg": None if skip_answer_overlap else 0.0,
        "answer_overlap_evaluated": not skip_answer_overlap,
        "skipped_answer_overlap": skip_answer_overlap,
        "evidence_overlap_avg": 0.0,
        "table_question_count": 0,
        "table_question_document_hit_rate": 0.0,
        "no_hit_count": 0,
    }
    if not documents:
        return {
            "report_version": REPORT_VERSION,
            "scope_note": SCOPE_NOTE,
            "mode": "read-only",
            "status": "no_documents",
            "results_dir": str(results_dir),
            "config": {
                "top_k": top_k,
                "report_detail_level": report_detail_level,
                "skip_answer_overlap": skip_answer_overlap,
                "failures_limit": failures_limit,
                "missing_source_limit": missing_source_limit,
                "top_hits_limit": stored_top_hits_limit,
            },
            "diagnostics": {
                "message": "No processed StructuredDocument JSON files found in results dir.",
                "skipped_result_files": list(skipped_result_files),
            },
            "notes": [
                "The evaluator reads processed JSON only and does not run ingestion.",
                "Answer overlap uses the current extractive ask path when hits are available.",
            ],
            "summary": base_summary,
            "timings": make_timings(questions_total=len(rows)),
            "results": [],
            "top_failures": [],
            "missing_source_examples": [],
        }

    index = build_read_only_index(documents)
    engine = build_search_engine(index)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    answer_overlaps: list[float] = []
    evidence_overlaps: list[float] = []
    table_questions = 0
    table_hits = 0
    source_expected_count = 0
    missing_expected_source_count = 0
    source_hits = 0
    missing_source_examples: list[dict[str, Any]] = []
    no_hit_count = 0

    for row in rows:
        hits = engine.search(row.question, top_k=top_k)
        if not hits:
            no_hit_count += 1
        ask_response = None if skip_answer_overlap else engine.ask(row.question, top_k=top_k) if hits else None
        answer_text = ask_response.answer if ask_response is not None else ""
        evidence_text = " ".join(hit.snippet for hit in hits)
        answer_overlap = None if skip_answer_overlap else token_recall(row.expected_answer, answer_text)
        evidence_overlap = token_recall(row.expected_answer, evidence_text)
        if answer_overlap is not None:
            answer_overlaps.append(answer_overlap)
        evidence_overlaps.append(evidence_overlap)

        has_expected_source = not is_missing_expected_source(row.expected_document)
        if has_expected_source:
            source_expected_count += 1
        else:
            missing_expected_source_count += 1
        hit1 = hit_at(row.expected_document, hits, 1)
        hit3 = hit_at(row.expected_document, hits, min(3, top_k))
        hit5 = hit_at(row.expected_document, hits, min(5, top_k))
        source_hit = hit_at(row.expected_document, hits, top_k) if has_expected_source else False
        if source_hit:
            source_hits += 1

        table_like = is_table_question(row.question, row.expected_answer, row.expected_document)
        if table_like:
            table_questions += 1
            if source_hit:
                table_hits += 1

        reason = "ok"
        if not has_expected_source:
            reason = "missing_expected_source"
        elif not hits:
            reason = "no_results"
        elif not source_hit:
            reason = "expected_source_not_found"

        item = {
            "row_number": row.row_number,
            "question": row.question,
            "expected_answer_preview": preview(row.expected_answer),
            "expected_document": row.expected_document,
            "retrieved_documents": [hit.filename for hit in hits],
            "hit_at_1": hit1,
            "hit_at_3": hit3,
            "hit_at_5": hit5,
            "answer_overlap": answer_overlap,
            "evidence_overlap": evidence_overlap,
            "table_like_question": table_like,
            "status": "pass" if reason == "ok" else "fail",
            "reason": reason,
            "answer_overlap_evaluated": not skip_answer_overlap,
            "skipped_answer_overlap": skip_answer_overlap,
            "answer_surrogate_note": "answer overlap skipped" if skip_answer_overlap else "current extractive ask answer" if ask_response is not None else "no answer; no hits",
            "top_hits": [format_hit(hit, rank) for rank, hit in enumerate(hits[:stored_top_hits_limit], start=1)],
        }
        results.append(item)
        if reason == "missing_expected_source":
            if len(missing_source_examples) < missing_source_limit:
                missing_source_examples.append(
                    {
                        "question": item["question"],
                        "expected_answer_preview": item["expected_answer_preview"],
                        "expected_document": item["expected_document"],
                        "retrieved_documents": item["retrieved_documents"],
                        "reason": reason,
                        "status": item["status"],
                    }
                )
        elif reason != "ok":
            failure_keys = [
                "question",
                "expected_answer_preview",
                "expected_document",
                "retrieved_documents",
                "hit_at_1",
                "hit_at_3",
                "hit_at_5",
                "answer_overlap",
                "answer_overlap_evaluated",
                "skipped_answer_overlap",
                "evidence_overlap",
                "reason",
                "status",
            ]
            failures.append({key: item[key] for key in failure_keys})

    evaluated = len(rows)
    source_hit_rate = round(source_hits / source_expected_count, 4) if source_expected_count else 0.0
    table_question_document_hit_rate = round(table_hits / table_questions, 4) if table_questions else 0.0
    summary = {
        "questions_total": len(rows),
        "evaluated_questions": evaluated,
        "skipped_questions": 0,
        "source_expected_count": source_expected_count,
        "missing_expected_source_count": missing_expected_source_count,
        "document_hit_at_1": sum(1 for item in results if item["hit_at_1"] and not is_missing_expected_source(item["expected_document"])),
        "document_hit_at_3": sum(1 for item in results if item["hit_at_3"] and not is_missing_expected_source(item["expected_document"])),
        "document_hit_at_5": sum(1 for item in results if item["hit_at_5"] and not is_missing_expected_source(item["expected_document"])),
        "source_hit_rate": source_hit_rate,
        "answer_overlap_avg": None if skip_answer_overlap else round(sum(answer_overlaps) / evaluated, 4) if evaluated else 0.0,
        "answer_overlap_evaluated": not skip_answer_overlap,
        "skipped_answer_overlap": skip_answer_overlap,
        "evidence_overlap_avg": round(sum(evidence_overlaps) / evaluated, 4) if evaluated else 0.0,
        "table_question_count": table_questions,
        "table_question_document_hit_rate": table_question_document_hit_rate,
        "no_hit_count": no_hit_count,
    }

    report = {
        "report_version": REPORT_VERSION,
        "scope_note": SCOPE_NOTE,
        "mode": "read-only",
        "status": "ok",
        "results_dir": str(results_dir),
        "config": {
            "top_k": top_k,
            "report_detail_level": report_detail_level,
            "skip_answer_overlap": skip_answer_overlap,
            "failures_limit": failures_limit,
            "missing_source_limit": missing_source_limit,
            "top_hits_limit": stored_top_hits_limit,
        },
        "diagnostics": {
            "documents_loaded": len(documents),
            "index_document_count": index.document_count,
            "index_chunk_count": index.chunk_count,
            "skipped_result_files": list(skipped_result_files),
        },
        "notes": [
            "The evaluator reads processed JSON only and does not run ingestion.",
            "Answer overlap uses the current extractive ask path; evidence overlap uses concatenated top-k snippets.",
            "Missing expected source placeholders such as 'Нет' are excluded from document-hit denominators.",
        ],
        "summary": summary,
        "timings": make_timings(questions_total=len(rows)),
        "results": results,
        "top_failures": failures[:failures_limit],
        "missing_source_examples": missing_source_examples,
    }
    return apply_report_detail_level(report, report_detail_level)


def build_report(
    qa_path: Path,
    results_dir: Path,
    top_k: int = 5,
    max_questions: int | None = None,
    question_column: str | None = None,
    answer_column: str | None = None,
    document_column: str | None = None,
    encoding: str | None = None,
    delimiter: str | None = None,
    skip_answer_overlap: bool = False,
    report_detail_level: str = "full",
    failures_limit: int = DEFAULT_FAILURES_LIMIT,
    missing_source_limit: int = DEFAULT_MISSING_SOURCE_LIMIT,
    top_hits_limit: int | None = None,
) -> dict[str, Any]:
    if not qa_path.exists():
        raise ValueError(f"QA file not found: {qa_path}")
    load_qa_started = perf_counter()
    rows, csv_info = load_qa_rows(
        qa_path=qa_path,
        question_column=question_column,
        answer_column=answer_column,
        document_column=document_column,
        encoding=encoding,
        delimiter=delimiter,
        max_questions=max_questions,
    )
    load_qa_seconds = perf_counter() - load_qa_started
    load_results_started = perf_counter()
    documents, skipped_files = load_documents_from_results(results_dir)
    load_results_seconds = perf_counter() - load_results_started
    evaluate_started = perf_counter()
    report = evaluate_qa_rows(
        rows=rows,
        documents=documents,
        results_dir=results_dir,
        top_k=top_k,
        skipped_result_files=skipped_files,
        skip_answer_overlap=skip_answer_overlap,
        report_detail_level=report_detail_level,
        failures_limit=failures_limit,
        missing_source_limit=missing_source_limit,
        top_hits_limit=top_hits_limit,
    )
    evaluate_seconds = perf_counter() - evaluate_started
    report["qa_path"] = str(qa_path)
    report["csv"] = csv_info
    report["timings"] = make_timings(
        load_qa_seconds=load_qa_seconds,
        load_results_seconds=load_results_seconds,
        evaluate_seconds=evaluate_seconds,
        questions_total=len(rows),
    )
    return report


def print_report(report: dict[str, Any]) -> None:
    summary = report["summary"]
    config = report["config"]
    timings = report.get("timings", {})
    print("Stage 25 QA/retrieval dataset evaluation")
    print(SCOPE_NOTE)
    print(f"QA path: {report.get('qa_path')}")
    print(f"Results dir: {report['results_dir']}")
    print(f"Mode: {report.get('mode', 'read-only')}")
    print(f"Report detail level: {config.get('report_detail_level', 'full')}")
    print(f"Skip answer overlap: {str(config.get('skip_answer_overlap', False)).lower()}")
    print(
        "questions_total={questions_total} evaluated={evaluated_questions} skipped={skipped_questions} top_k={top_k}".format(
            top_k=config["top_k"],
            **summary,
        )
    )
    print(
        "document_hit_at_1={document_hit_at_1} document_hit_at_3={document_hit_at_3} document_hit_at_5={document_hit_at_5} source_hit_rate={source_hit_rate}".format(
            **summary
        )
    )
    print(
        "answer_overlap_avg={answer_overlap_avg} evidence_overlap_avg={evidence_overlap_avg} no_hit_count={no_hit_count}".format(
            **summary
        )
    )
    print(
        "table_question_count={table_question_count} table_question_document_hit_rate={table_question_document_hit_rate}".format(
            **summary
        )
    )
    print(
        "timings: load_qa={load_qa_seconds}s load_results={load_results_seconds}s evaluate={evaluate_seconds}s write_report={write_report_seconds}s total={total_seconds}s avg_per_question={avg_seconds_per_question}s".format(
            load_qa_seconds=timings.get("load_qa_seconds", 0.0),
            load_results_seconds=timings.get("load_results_seconds", 0.0),
            evaluate_seconds=timings.get("evaluate_seconds", 0.0),
            write_report_seconds=timings.get("write_report_seconds", 0.0),
            total_seconds=timings.get("total_seconds", 0.0),
            avg_seconds_per_question=timings.get("avg_seconds_per_question", 0.0),
        )
    )
    if report.get("json_report_path"):
        print(f"JSON report: {report['json_report_path']}")
    if report["status"] != "ok":
        print(f"Diagnostic: {report['diagnostics'].get('message', report['status'])}")
        return
    failures = report.get("top_failures") or []
    if not failures:
        print("Top failures: none")
        return
    print("Top failures:")
    for index, failure in enumerate(failures, start=1):
        print(
            "{rank}. reason={reason} hit@1={hit1} hit@3={hit3} hit@5={hit5} source={source}".format(
                rank=index,
                reason=failure["reason"],
                hit1=failure["hit_at_1"],
                hit3=failure["hit_at_3"],
                hit5=failure["hit_at_5"],
                source=failure["expected_document"] or "n/a",
            )
        )
        print(f"   question: {preview(failure['question'], 160)}")
        print(f"   retrieved: {', '.join(failure['retrieved_documents']) or 'none'}")


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only QA/retrieval readiness evaluation for external CSV dataset")
    parser.add_argument("--qa-path", required=True, help="Path to CSV with questions, expected answers and expected source")
    parser.add_argument("--results-dir", default=None, help="Directory with processed StructuredDocument JSON files")
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieval hits to evaluate")
    parser.add_argument("--max-questions", type=int, help="Optional limit for QA rows")
    parser.add_argument("--question-column", help="Override question column name")
    parser.add_argument("--answer-column", help="Override expected answer column name")
    parser.add_argument("--document-column", help="Override expected document/source column name")
    parser.add_argument("--json-report-path", help="Optional path to save the JSON report")
    parser.add_argument("--encoding", help="Optional CSV encoding override")
    parser.add_argument("--delimiter", help="Optional CSV delimiter override")
    parser.add_argument("--skip-answer-overlap", action="store_true", help="Skip extractive ask answer-overlap scoring for faster retrieval-only smoke runs")
    parser.add_argument("--report-detail-level", choices=REPORT_DETAIL_LEVELS, default="full", help="JSON report detail level")
    parser.add_argument("--failures-limit", type=non_negative_int, default=DEFAULT_FAILURES_LIMIT, help="Maximum top_failures records stored in the JSON report")
    parser.add_argument("--missing-source-limit", type=non_negative_int, default=DEFAULT_MISSING_SOURCE_LIMIT, help="Maximum missing_source_examples records stored in the JSON report")
    parser.add_argument("--top-hits-limit", type=non_negative_int, default=None, help="Maximum top_hits records stored per question in the JSON report")
    args = parser.parse_args(argv)

    settings = get_settings()
    results_dir = Path(args.results_dir).resolve() if args.results_dir else settings.resolved_storage_dir / "results"
    started_at = perf_counter()
    try:
        report = build_report(
            qa_path=Path(args.qa_path).resolve(),
            results_dir=results_dir,
            top_k=args.top_k,
            max_questions=args.max_questions,
            question_column=args.question_column,
            answer_column=args.answer_column,
            document_column=args.document_column,
            encoding=args.encoding,
            delimiter=args.delimiter,
            skip_answer_overlap=args.skip_answer_overlap,
            report_detail_level=args.report_detail_level,
            failures_limit=args.failures_limit,
            missing_source_limit=args.missing_source_limit,
            top_hits_limit=args.top_hits_limit,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    write_report_seconds = 0.0
    if args.json_report_path:
        report_path = Path(args.json_report_path).resolve()
        report["json_report_path"] = str(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        write_started = perf_counter()
        report["timings"] = make_timings(
            load_qa_seconds=report["timings"]["load_qa_seconds"],
            load_results_seconds=report["timings"]["load_results_seconds"],
            evaluate_seconds=report["timings"]["evaluate_seconds"],
            write_report_seconds=0.0,
            questions_total=report["summary"]["questions_total"],
        )
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        write_report_seconds = perf_counter() - write_started
        report["timings"] = make_timings(
            load_qa_seconds=report["timings"]["load_qa_seconds"],
            load_results_seconds=report["timings"]["load_results_seconds"],
            evaluate_seconds=report["timings"]["evaluate_seconds"],
            write_report_seconds=write_report_seconds,
            questions_total=report["summary"]["questions_total"],
        )
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        report["timings"] = make_timings(
            load_qa_seconds=report["timings"]["load_qa_seconds"],
            load_results_seconds=report["timings"]["load_results_seconds"],
            evaluate_seconds=report["timings"]["evaluate_seconds"],
            write_report_seconds=write_report_seconds,
            questions_total=report["summary"]["questions_total"],
        )

    report["timings"]["total_seconds"] = round(perf_counter() - started_at, 4)
    report["timings"]["avg_seconds_per_question"] = round(
        report["timings"]["total_seconds"] / report["summary"]["questions_total"],
        4,
    ) if report["summary"]["questions_total"] else 0.0
    if args.json_report_path:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(report)
    if args.json_report_path:
        print(f"Saved QA/retrieval eval report to {report_path}")


if __name__ == "__main__":
    main()
