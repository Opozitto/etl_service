from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

from app.schemas.document import StructuredDocument


RequirementCategory = Literal[
    "obligation",
    "prohibition",
    "threshold_or_limit",
    "monitoring_or_control",
    "calculation_or_reporting",
    "unknown",
]

SENTENCE_RE = re.compile(r"(?<=[.!?;])\s+|\n+")
WHITESPACE_RE = re.compile(r"\s+")

OBLIGATION_TERMS = (
    "должен",
    "должна",
    "должно",
    "должны",
    "обязан",
    "обязана",
    "обязано",
    "обязаны",
    "необходимо",
    "требуется",
    "следует",
    "подлежит",
    "подлежат",
    "устанавливается",
)
PROHIBITION_TERMS = (
    "запрещается",
    "не допускается",
    "допускается только",
)
THRESHOLD_TERMS = (
    "предельно допустим",
    "пдв",
    "пдк",
    "ндв",
    "норматив",
    "лимит",
)
MONITORING_TERMS = (
    "контроль",
    "мониторинг",
    "проводится",
    "осуществляется",
)
CALCULATION_TERMS = (
    "расчет",
    "расчёт",
    "отчет",
    "отчёт",
    "декларация",
    "представляется",
)

DOMAIN_HINT_TERMS = (
    "норматив",
    "предельно допустим",
    "пдв",
    "пдк",
    "ндв",
    "лимит",
    "расчет",
    "расчёт",
    "контроль",
    "мониторинг",
)

CATEGORY_TERMS: tuple[tuple[RequirementCategory, tuple[str, ...], str, float], ...] = (
    ("prohibition", PROHIBITION_TERMS, "prohibition_marker", 0.72),
    ("obligation", OBLIGATION_TERMS, "obligation_marker", 0.68),
    ("threshold_or_limit", THRESHOLD_TERMS, "threshold_or_limit_marker", 0.62),
    ("monitoring_or_control", MONITORING_TERMS, "monitoring_or_control_marker", 0.48),
    ("calculation_or_reporting", CALCULATION_TERMS, "calculation_or_reporting_marker", 0.5),
)


@dataclass(frozen=True)
class RequirementSource:
    document_id: str
    filename: str
    source_type: str = "unknown"
    block_id: str | None = None
    chunk_id: str | None = None
    table_id: str | None = None
    section_id: str | None = None
    section_title: str | None = None
    page: int | None = None


@dataclass(frozen=True)
class RequirementCandidate:
    document_id: str
    filename: str
    category: RequirementCategory
    score: float
    source_type: str
    text: str
    snippet: str
    matched_terms: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    block_id: str | None = None
    chunk_id: str | None = None
    table_id: str | None = None
    section_id: str | None = None
    section_title: str | None = None
    page: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "category": self.category,
            "score": self.score,
            "source_type": self.source_type,
            "block_id": self.block_id,
            "chunk_id": self.chunk_id,
            "table_id": self.table_id,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "page": self.page,
            "matched_terms": self.matched_terms,
            "reason_codes": self.reason_codes,
            "text": self.text,
            "snippet": self.snippet,
        }


def normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.replace("\u00a0", " ")).strip()


def split_windows(text: str, max_chars: int = 700) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    windows: list[str] = []
    current = ""
    for sentence in SENTENCE_RE.split(normalized):
        sentence = normalize_text(sentence)
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                windows.append(current)
                current = ""
            for start in range(0, len(sentence), max_chars):
                windows.append(sentence[start : start + max_chars].strip())
            continue
        if current and len(current) + 1 + len(sentence) > max_chars:
            windows.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip() if current else sentence
    if current:
        windows.append(current)
    return windows


def extract_requirements_from_document(
    document: StructuredDocument,
    min_score: float = 0.45,
    max_per_document: int | None = None,
    query: str | None = None,
) -> list[RequirementCandidate]:
    section_titles = {section.section_id: section.title for section in document.sections}
    candidates: list[RequirementCandidate] = []
    seen: set[tuple[str, str, str]] = set()

    for source, text in iter_document_sources(document, section_titles):
        for window in split_windows(text):
            candidate = classify_window(window, source)
            if candidate is None or candidate.score < min_score:
                continue
            if query and not candidate_matches_query(candidate, query):
                continue
            key = (candidate.section_id or "", normalize_text(candidate.text).lower())
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)

    candidates.sort(key=lambda item: (item.score, len(item.matched_terms), item.filename), reverse=True)
    if max_per_document is not None:
        return candidates[:max_per_document]
    return candidates


def extract_requirements_from_documents(
    documents: Iterable[StructuredDocument],
    min_score: float = 0.45,
    max_per_document: int | None = None,
    query: str | None = None,
) -> list[RequirementCandidate]:
    candidates: list[RequirementCandidate] = []
    for document in documents:
        candidates.extend(
            extract_requirements_from_document(
                document=document,
                min_score=min_score,
                max_per_document=max_per_document,
                query=query,
            )
        )
    return candidates


def load_documents_from_results(results_dir: Path) -> list[StructuredDocument]:
    documents: list[StructuredDocument] = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            documents.append(StructuredDocument.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return documents


def build_requirements_report(
    documents: list[StructuredDocument],
    results_dir: Path,
    min_score: float = 0.45,
    max_per_document: int | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    candidates = extract_requirements_from_documents(
        documents=documents,
        min_score=min_score,
        max_per_document=max_per_document,
        query=query,
    )
    categories = Counter(candidate.category for candidate in candidates)
    documents_with_candidates = {candidate.document_id for candidate in candidates}
    return {
        "report_version": "stage22_requirements_v1",
        "stage": "Stage 22 Requirements extraction v1",
        "scope_note": (
            "Deterministic source-backed candidate extraction from processed JSON; "
            "no LLM generation and no legal/compliance guarantee."
        ),
        "results_dir": str(results_dir),
        "summary": {
            "documents_seen": len(documents),
            "documents_with_candidates": len(documents_with_candidates),
            "total_candidates": len(candidates),
            "categories": dict(sorted(categories.items())),
        },
        "candidates": [candidate.to_dict() for candidate in candidates],
    }


def iter_document_sources(
    document: StructuredDocument,
    section_titles: dict[str, str],
) -> Iterable[tuple[RequirementSource, str]]:
    for block in document.blocks:
        if not block.text:
            continue
        yield (
            RequirementSource(
                document_id=document.metadata.document_id,
                filename=document.source.filename,
                source_type="block",
                block_id=block.block_id,
                section_id=block.section_id,
                section_title=section_titles.get(block.section_id or ""),
                page=block.page_num,
            ),
            block.text,
        )

    for chunk in document.chunks:
        if not chunk.text:
            continue
        yield (
            RequirementSource(
                document_id=document.metadata.document_id,
                filename=document.source.filename,
                source_type="chunk",
                chunk_id=chunk.chunk_id,
                section_id=chunk.section_id,
                section_title=section_titles.get(chunk.section_id or ""),
            ),
            chunk.text,
        )

    for table in document.tables:
        table_text = table_to_text(table.rows)
        if not table_text:
            continue
        yield (
            RequirementSource(
                document_id=document.metadata.document_id,
                filename=document.source.filename,
                source_type="table",
                table_id=table.table_id,
                section_id=table.section_id,
                section_title=section_titles.get(table.section_id or ""),
                page=table.page_num,
            ),
            table_text,
        )


def table_to_text(rows: list[list[str]]) -> str:
    return normalize_text(" ".join(" | ".join(str(cell) for cell in row if str(cell).strip()) for row in rows))


def classify_window(text: str, source: RequirementSource) -> RequirementCandidate | None:
    lowered = normalize_text(text).lower().replace("ё", "е")
    matches: list[tuple[RequirementCategory, str, str, float]] = []
    for category, terms, reason_code, base_score in CATEGORY_TERMS:
        for term in terms:
            if term in lowered:
                matches.append((category, term, reason_code, base_score))

    if not matches:
        return None

    category, _, _, base_score = max(matches, key=lambda item: item[3])
    matched_terms = sorted({term for _, term, _, _ in matches})
    reason_codes = sorted({reason_code for _, _, reason_code, _ in matches})
    domain_hints = sorted({term for term in DOMAIN_HINT_TERMS if term in lowered})
    if domain_hints:
        reason_codes.append("domain_hint")

    score = base_score
    score += min(0.12, 0.03 * max(len(matched_terms) - 1, 0))
    score += min(0.12, 0.04 * len(domain_hints))
    if source.source_type == "table":
        score += 0.03
        reason_codes.append("table_context")
    if source.section_title:
        score += 0.02
        reason_codes.append("section_context")
    score = round(min(score, 0.95), 2)

    normalized = normalize_text(text)
    return RequirementCandidate(
        document_id=source.document_id,
        filename=source.filename,
        category=category,
        score=score,
        source_type=source.source_type,
        block_id=source.block_id,
        chunk_id=source.chunk_id,
        table_id=source.table_id,
        section_id=source.section_id,
        section_title=source.section_title,
        page=source.page,
        matched_terms=matched_terms,
        reason_codes=sorted(set(reason_codes)),
        text=normalized,
        snippet=build_snippet(normalized),
    )


def build_snippet(text: str, max_chars: int = 240) -> str:
    text = normalize_text(text)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def candidate_matches_query(candidate: RequirementCandidate, query: str) -> bool:
    normalized_query = query.lower().replace("ё", "е")
    haystack = " ".join(
        [
            candidate.text,
            candidate.category,
            candidate.filename,
            candidate.section_title or "",
            " ".join(candidate.matched_terms),
            " ".join(candidate.reason_codes),
        ]
    ).lower().replace("ё", "е")
    return normalized_query in haystack
