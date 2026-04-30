from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal

from app.schemas.document import StructuredDocument, TableData


TableEvidenceCategory = Literal[
    "emissions",
    "pollutants",
    "limits_or_norms",
    "measurements",
    "costs_or_resources",
    "sources_or_equipment",
    "unknown",
]

REPORT_VERSION = "stage23_table_evidence_v1"
STAGE_NAME = "Stage 23 Table-aware evidence evaluation"
SCOPE_NOTE = (
    "Deterministic source-backed table evidence only; not SQL/table analytics; "
    "no automatic calculations."
)
WHITESPACE_RE = re.compile(r"\s+")

CATEGORY_TERMS: dict[TableEvidenceCategory, tuple[str, ...]] = {
    "emissions": (
        "выброс",
        "пдв",
        "ндв",
        "г/с",
        "т/год",
    ),
    "pollutants": (
        "вещество",
        "загрязняющее вещество",
        "код",
    ),
    "limits_or_norms": (
        "пдк",
        "пдв",
        "ндв",
        "норматив",
        "лимит",
        "разрешение",
        "доля пдк",
    ),
    "measurements": (
        "концентрация",
        "мг/м3",
        "мг/м³",
        "контроль",
        "мониторинг",
        "замер",
        "периодичность",
    ),
    "costs_or_resources": (
        "расход",
        "сырье",
        "сырьё",
        "материал",
        "затраты",
    ),
    "sources_or_equipment": (
        "источник",
        "источник выбросов",
        "оборудование",
        "газоочистка",
    ),
}


@dataclass(frozen=True)
class TableEvidenceRecord:
    document_id: str
    filename: str
    table_id: str | None
    source_type: str
    category: TableEvidenceCategory
    tags: list[str]
    score: float
    matched_terms: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    block_id: str | None = None
    chunk_id: str | None = None
    section_id: str | None = None
    section_title: str | None = None
    page: int | None = None
    row_count: int = 0
    column_count: int = 0
    headers: list[str] = field(default_factory=list)
    detected_columns: list[str] = field(default_factory=list)
    preview_rows: list[list[str]] = field(default_factory=list)
    snippet: str = ""
    text_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "table_id": self.table_id,
            "block_id": self.block_id,
            "chunk_id": self.chunk_id,
            "source_type": self.source_type,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "page": self.page,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "headers": self.headers,
            "detected_columns": self.detected_columns,
            "preview_rows": self.preview_rows,
            "category": self.category,
            "tags": self.tags,
            "score": self.score,
            "matched_terms": self.matched_terms,
            "reason_codes": self.reason_codes,
            "snippet": self.snippet,
            "text_preview": self.text_preview,
        }


def load_documents_from_results(results_dir: Path) -> list[StructuredDocument]:
    documents: list[StructuredDocument] = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            documents.append(StructuredDocument.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return documents


def evaluate_tables_from_documents(
    documents: Iterable[StructuredDocument],
    min_score: float = 0.25,
    max_tables: int | None = None,
    category: str | None = None,
) -> list[TableEvidenceRecord]:
    records: list[TableEvidenceRecord] = []
    seen: set[tuple[str, str, str]] = set()
    category_filter = category.lower() if category else None

    for document in documents:
        for record in extract_table_evidence_from_document(document, min_score=min_score):
            if category_filter and record.category != category_filter and category_filter not in record.tags:
                continue
            key = (
                record.document_id,
                record.table_id or "",
                normalize_text(record.snippet).lower(),
            )
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

    records.sort(
        key=lambda item: (
            item.score,
            len(item.matched_terms),
            item.row_count,
            item.filename.lower(),
            item.table_id or "",
        ),
        reverse=True,
    )
    if max_tables is not None:
        return records[:max_tables]
    return records


def extract_table_evidence_from_document(
    document: StructuredDocument,
    min_score: float = 0.25,
) -> list[TableEvidenceRecord]:
    section_titles = {section.section_id: section.title for section in document.sections}
    table_blocks = {
        str(block.metadata.get("table_id")): block
        for block in document.blocks
        if block.type == "table" and block.metadata.get("table_id")
    }
    records: list[TableEvidenceRecord] = []

    for table in document.tables:
        block = table_blocks.get(table.table_id)
        chunk_id = first_table_chunk_id(document, block.block_id if block else None)
        record = build_table_evidence_record(
            document=document,
            table=table,
            section_title=section_titles.get(table.section_id or ""),
            block_id=block.block_id if block else None,
            chunk_id=chunk_id,
        )
        if record.score >= min_score:
            records.append(record)

    return records


def build_table_evidence_report(
    documents: list[StructuredDocument],
    results_dir: Path,
    min_score: float = 0.25,
    max_tables: int | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    tables_seen = sum(len(document.tables) for document in documents)
    documents_with_tables = {document.metadata.document_id for document in documents if document.tables}
    records = evaluate_tables_from_documents(
        documents=documents,
        min_score=min_score,
        max_tables=max_tables,
        category=category,
    )
    categories = Counter(record.category for record in records)
    return {
        "report_version": REPORT_VERSION,
        "stage": STAGE_NAME,
        "scope_note": SCOPE_NOTE,
        "results_dir": str(results_dir),
        "summary": {
            "documents_seen": len(documents),
            "documents_with_tables": len(documents_with_tables),
            "tables_seen": tables_seen,
            "candidate_tables": len(records),
            "categories": dict(sorted(categories.items())),
        },
        "tables": [record.to_dict() for record in records],
    }


def build_table_evidence_record(
    document: StructuredDocument,
    table: TableData,
    section_title: str | None,
    block_id: str | None,
    chunk_id: str | None,
) -> TableEvidenceRecord:
    rows = clean_rows(table.rows)
    headers = detect_headers(rows)
    preview_rows = rows[:4]
    header_text = " ".join(headers)
    body_text = table_to_text(rows[1:] if headers and len(rows) > 1 else rows)
    all_text = normalize_text(f"{header_text} {body_text}")
    category_scores, matched_terms_by_category = score_categories(header_text, body_text)
    category = select_category(category_scores)
    matched_terms = sorted(
        {
            term
            for terms in matched_terms_by_category.values()
            for term in terms
        }
    )
    tags = sorted(category for category, score in category_scores.items() if score > 0)
    if not tags:
        tags = ["unknown"]

    reason_codes: list[str] = []
    if headers:
        reason_codes.append("headers_detected")
    if any(score >= 0.35 for score in category_scores.values()):
        reason_codes.append("domain_header_match")
    if any(0 < score < 0.35 for score in category_scores.values()):
        reason_codes.append("domain_cell_match")
    if row_count(rows) > 1:
        reason_codes.append("table_rows_present")
    if block_id:
        reason_codes.append("block_context")
    if section_title:
        reason_codes.append("section_context")

    score = calculate_score(category_scores, headers=headers, rows=rows, section_title=section_title)
    return TableEvidenceRecord(
        document_id=document.metadata.document_id,
        filename=document.source.filename,
        table_id=table.table_id,
        block_id=block_id,
        chunk_id=chunk_id,
        source_type="table",
        section_id=table.section_id,
        section_title=section_title,
        page=table.page_num,
        row_count=table.n_rows or row_count(rows),
        column_count=table.n_cols or column_count(rows),
        headers=headers,
        detected_columns=headers,
        preview_rows=preview_rows,
        category=category,
        tags=tags,
        score=score,
        matched_terms=matched_terms,
        reason_codes=sorted(set(reason_codes)) or ["unknown_table"],
        snippet=build_snippet(all_text),
        text_preview=build_snippet(all_text),
    )


def score_categories(
    header_text: str,
    body_text: str,
) -> tuple[dict[TableEvidenceCategory, float], dict[TableEvidenceCategory, set[str]]]:
    normalized_headers = normalize_for_match(header_text)
    normalized_body = normalize_for_match(body_text)
    scores: dict[TableEvidenceCategory, float] = {category: 0.0 for category in CATEGORY_TERMS}
    matches: dict[TableEvidenceCategory, set[str]] = {category: set() for category in CATEGORY_TERMS}

    for category, terms in CATEGORY_TERMS.items():
        for term in terms:
            normalized_term = normalize_for_match(term)
            if normalized_term and normalized_term in normalized_headers:
                scores[category] += 0.34
                matches[category].add(term)
            elif normalized_term and normalized_term in normalized_body:
                scores[category] += 0.14
                matches[category].add(term)

    return scores, matches


def calculate_score(
    category_scores: dict[TableEvidenceCategory, float],
    headers: list[str],
    rows: list[list[str]],
    section_title: str | None,
) -> float:
    best = max(category_scores.values(), default=0.0)
    score = 0.08
    score += min(best, 0.68)
    if headers:
        score += 0.12
    if row_count(rows) >= 2:
        score += 0.06
    if column_count(rows) >= 2:
        score += 0.04
    if section_title and any(term in normalize_for_match(section_title) for term in ("расчет", "расчёт", "таблиц")):
        score += 0.04
    return round(min(score, 0.95), 2)


def select_category(category_scores: dict[TableEvidenceCategory, float]) -> TableEvidenceCategory:
    if not category_scores:
        return "unknown"
    category, score = max(category_scores.items(), key=lambda item: item[1])
    if score <= 0:
        return "unknown"
    return category


def detect_headers(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    first = [normalize_text(cell) for cell in rows[0]]
    if not any(first):
        return []
    if len(rows) == 1:
        return first
    non_empty = [cell for cell in first if cell]
    if not non_empty:
        return []
    alpha_cells = sum(1 for cell in non_empty if any(char.isalpha() for char in cell))
    numeric_cells = sum(1 for cell in non_empty if is_numeric_like(cell))
    if alpha_cells >= max(1, len(non_empty) // 2) and numeric_cells <= max(0, len(non_empty) // 3):
        return first
    return []


def first_table_chunk_id(document: StructuredDocument, block_id: str | None) -> str | None:
    if not block_id:
        return None
    for chunk in document.chunks:
        if block_id in chunk.block_ids:
            return chunk.chunk_id
    return None


def clean_rows(rows: list[list[str]]) -> list[list[str]]:
    cleaned: list[list[str]] = []
    for row in rows:
        normalized = [normalize_text(str(cell)) for cell in row]
        while normalized and not normalized[-1]:
            normalized.pop()
        if any(normalized):
            cleaned.append(normalized)
    return cleaned


def row_count(rows: list[list[str]]) -> int:
    return len(rows)


def column_count(rows: list[list[str]]) -> int:
    return max((len(row) for row in rows), default=0)


def table_to_text(rows: list[list[str]]) -> str:
    return normalize_text(" ".join(" | ".join(cell for cell in row if cell) for row in rows))


def build_snippet(text: str, max_chars: int = 280) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def normalize_text(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text.replace("\u00a0", " ")).strip()


def normalize_for_match(text: str) -> str:
    return normalize_text(text).lower().replace("ё", "е")


def is_numeric_like(text: str) -> bool:
    cleaned = text.replace(",", ".").replace(" ", "")
    try:
        float(cleaned)
    except ValueError:
        return False
    return True
