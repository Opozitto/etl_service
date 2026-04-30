from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.source_location import build_location_label


EXPORT_VERSION = "stage29_1_rag_chunk_export_v1"

SHORT_CHUNK_CHAR_LIMIT = 120
PAGE_FIELDS = ("page_num", "page", "page_number", "page_start", "page_end")
TABLE_LIKE_RE = re.compile(r"(\|.+\|)|(\t)|(;.*;.*)|(\brow\s+\d+\b)|(\bcolumn\s+\d+\b)", re.IGNORECASE)
TABLE_TERMS = (
    "таблиц",
    "строка",
    "колонка",
    "столбец",
    "графа",
    "table",
    "row",
    "column",
)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def read_json_document(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"cannot read processed JSON as UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"cannot parse processed JSON {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"processed JSON must be an object: {path}")
    return payload


def iter_processed_json(results_dir: Path) -> Iterable[Path]:
    if not results_dir.exists():
        raise ValueError(f"results dir not found: {results_dir}")
    if not results_dir.is_dir():
        raise ValueError(f"results path is not a directory: {results_dir}")
    yield from sorted(path for path in results_dir.glob("*.json") if path.is_file())


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _metadata(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("metadata")
    return value if isinstance(value, dict) else {}


def _source(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("source")
    return value if isinstance(value, dict) else {}


def _processing_info(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("processing_info")
    return value if isinstance(value, dict) else {}


def section_path(section_id: str | None, sections_by_id: dict[str, dict[str, Any]]) -> list[str]:
    if not section_id:
        return []
    path: list[str] = []
    seen: set[str] = set()
    current_id: str | None = section_id
    while current_id and current_id not in seen:
        seen.add(current_id)
        section = sections_by_id.get(current_id)
        if not section:
            break
        title = normalize_text(section.get("title"))
        if title:
            path.append(title)
        current_id = section.get("parent_id") if isinstance(section.get("parent_id"), str) else None
    return list(reversed(path))


def _chunk_section_path(chunk: dict[str, Any], section_id: str | None, sections_by_id: dict[str, dict[str, Any]]) -> list[str]:
    direct = chunk.get("section_path")
    if isinstance(direct, list):
        values = [normalize_text(item) for item in direct if normalize_text(item)]
        if values:
            return values
    return section_path(section_id, sections_by_id)


def _chunk_int(chunk: dict[str, Any], field: str) -> int | None:
    value = chunk.get(field)
    return value if isinstance(value, int) else None


def _chunk_text_field(chunk: dict[str, Any], field: str) -> str | None:
    value = normalize_text(chunk.get(field))
    return value or None


def _chunk_list_field(chunk: dict[str, Any], field: str) -> list[str]:
    value = chunk.get(field)
    if not isinstance(value, list):
        return []
    return [normalize_text(item) for item in value if normalize_text(item)]


def _chunk_dict_field(chunk: dict[str, Any], field: str) -> dict[str, str]:
    value = chunk.get(field)
    if not isinstance(value, dict):
        return {}
    return {
        normalize_text(key): normalize_text(item)
        for key, item in value.items()
        if normalize_text(key) and normalize_text(item)
    }


def _block_page_values(block: dict[str, Any]) -> list[int]:
    values: list[int] = []
    for field in PAGE_FIELDS:
        raw = block.get(field)
        if isinstance(raw, int):
            values.append(raw)
    metadata = block.get("metadata")
    if isinstance(metadata, dict):
        for field in PAGE_FIELDS:
            raw = metadata.get(field)
            if isinstance(raw, int):
                values.append(raw)
    return values


def page_range(blocks: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    pages: list[int] = []
    for block in blocks:
        pages.extend(_block_page_values(block))
    if not pages:
        return None, None
    return min(pages), max(pages)


def table_id_from_blocks(blocks: list[dict[str, Any]], tables: list[dict[str, Any]]) -> str | None:
    table_ids = {normalize_text(table.get("table_id")) for table in tables if normalize_text(table.get("table_id"))}
    for block in blocks:
        metadata = block.get("metadata")
        if isinstance(metadata, dict):
            candidate = normalize_text(metadata.get("table_id"))
            if candidate:
                return candidate
        candidate = normalize_text(block.get("table_id"))
        if candidate:
            return candidate
    if len(table_ids) == 1 and any(block.get("type") == "table" for block in blocks):
        return next(iter(table_ids))
    return None


def _table_by_id(tables: list[dict[str, Any]], table_id: str | None) -> dict[str, Any] | None:
    if not table_id:
        return None
    for table in tables:
        if normalize_text(table.get("table_id")) == table_id:
            return table
    return None


def _table_rows(table: dict[str, Any] | None) -> list[list[str]]:
    if not table:
        return []
    rows = table.get("rows")
    if not isinstance(rows, list):
        return []
    cleaned_rows: list[list[str]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        values = [normalize_text(cell) for cell in row]
        if any(values):
            cleaned_rows.append(values)
    return cleaned_rows


def _table_headers_from_table(table: dict[str, Any] | None) -> list[str]:
    rows = _table_rows(table)
    if len(rows) <= 1:
        return []
    headers = [normalize_text(cell) for cell in rows[0]]
    return [header for header in headers if header]


def _table_title_from_context(
    chunk: dict[str, Any],
    section: dict[str, Any] | None,
    blocks: list[dict[str, Any]],
) -> str | None:
    direct = _chunk_text_field(chunk, "table_title")
    if direct:
        return direct
    for block in blocks:
        metadata = block.get("metadata")
        if isinstance(metadata, dict):
            sheet_name = normalize_text(metadata.get("sheet_name"))
            if sheet_name:
                return sheet_name
    if section:
        title = normalize_text(section.get("title"))
        if title and title != "Document":
            return title
    return None


def is_table_like_text(text: str) -> bool:
    normalized = normalize_text(text).lower()
    if not normalized:
        return False
    if TABLE_LIKE_RE.search(normalized):
        return True
    return any(term in normalized for term in TABLE_TERMS)


def derive_content_type(chunk: dict[str, Any], blocks: list[dict[str, Any]], table_id: str | None) -> str:
    block_types = {normalize_text(block.get("type")) for block in blocks}
    text = normalize_text(chunk.get("text")).lower()
    if "image" in block_types:
        return "image"
    if "table" in block_types or table_id:
        if "строка" in text or "row" in text:
            return "table_row"
        return "table"
    if block_types.intersection({"paragraph", "heading", "list_item", "text"}):
        return "text"
    return "unknown"


def derive_quality_flags(
    *,
    chunk: dict[str, Any],
    section_present: bool,
    page_start: int | None,
    content_type: str,
    blocks: list[dict[str, Any]],
    document: dict[str, Any],
) -> list[str]:
    flags: list[str] = []
    text = str(chunk.get("text") or "")
    if not text.strip():
        flags.append("empty_or_whitespace_text")
    elif len(normalize_text(text)) < SHORT_CHUNK_CHAR_LIMIT:
        flags.append("short_chunk")
    if not section_present:
        flags.append("missing_section")
    if page_start is None:
        flags.append("missing_page")
    if is_table_like_text(text):
        flags.append("table_like_text")
    if content_type == "unknown":
        flags.append("unknown_content_type")
    if _is_image_or_ocr_limited(blocks, document):
        flags.append("image_or_ocr_limited")
    return sorted(set(flags))


def _is_image_or_ocr_limited(blocks: list[dict[str, Any]], document: dict[str, Any]) -> bool:
    if any(block.get("type") == "image" and not normalize_text(block.get("text")) for block in blocks):
        return True
    processing = _processing_info(document)
    text_char_count = processing.get("text_char_count")
    if processing.get("ocr_candidate") is True and (text_char_count is None or text_char_count == 0):
        return True
    return False


def handoff_notes(quality_flags: list[str], content_type: str, table_id: str | None) -> list[str]:
    notes: list[str] = []
    if "missing_section" in quality_flags:
        notes.append("section context is missing or cannot be resolved")
    if "missing_page" in quality_flags:
        notes.append("page context is not available in linked blocks")
    if "short_chunk" in quality_flags:
        notes.append("chunk is short and may need neighboring context")
    if "table_like_text" in quality_flags and not table_id:
        notes.append("text looks table-like, but table_id could not be resolved")
    if content_type == "image" or "image_or_ocr_limited" in quality_flags:
        notes.append("image/OCR-limited source context; no OCR text is inferred here")
    if content_type == "unknown":
        notes.append("content type could not be classified from current metadata")
    return notes


def export_document_chunks(
    document: dict[str, Any],
    *,
    max_chunks: int | None = None,
    include_text: bool = False,
    text_preview_chars: int = 300,
) -> list[dict[str, Any]]:
    metadata = _metadata(document)
    source = _source(document)
    sections = _list_of_dicts(document.get("sections"))
    blocks = _list_of_dicts(document.get("blocks"))
    tables = _list_of_dicts(document.get("tables"))
    chunks = _list_of_dicts(document.get("chunks"))

    sections_by_id = {normalize_text(section.get("section_id")): section for section in sections}
    blocks_by_id = {normalize_text(block.get("block_id")): block for block in blocks}

    items: list[dict[str, Any]] = []
    for chunk in chunks[:max_chunks]:
        section_id = normalize_text(chunk.get("section_id")) or None
        source_block_ids = [normalize_text(block_id) for block_id in chunk.get("block_ids") or [] if normalize_text(block_id)]
        linked_blocks = [blocks_by_id[block_id] for block_id in source_block_ids if block_id in blocks_by_id]
        section = sections_by_id.get(section_id or "")
        section_present = section is not None
        derived_page_start, derived_page_end = page_range(linked_blocks)
        page_start = _chunk_int(chunk, "page_start")
        page_end = _chunk_int(chunk, "page_end")
        if page_start is None:
            page_start = derived_page_start
        if page_end is None:
            page_end = derived_page_end
        table_id = _chunk_text_field(chunk, "table_id") or table_id_from_blocks(linked_blocks, tables)
        content_type = _chunk_text_field(chunk, "content_type") or derive_content_type(chunk, linked_blocks, table_id)
        is_table_item = content_type in {"table", "table_row"} or table_id is not None
        linked_table = _table_by_id(tables, table_id) if is_table_item else None
        table_headers = _chunk_list_field(chunk, "table_headers") or _table_headers_from_table(linked_table)
        table_column_values = _chunk_dict_field(chunk, "table_column_values") if is_table_item else {}
        row_count = _chunk_int(chunk, "row_count") if is_table_item else None
        column_count = _chunk_int(chunk, "column_count") if is_table_item else None
        if is_table_item and row_count is None and linked_table:
            row_count = linked_table.get("n_rows") if isinstance(linked_table.get("n_rows"), int) else None
        if is_table_item and column_count is None and linked_table:
            column_count = linked_table.get("n_cols") if isinstance(linked_table.get("n_cols"), int) else None
        flags = derive_quality_flags(
            chunk=chunk,
            section_present=section_present,
            page_start=page_start,
            content_type=content_type,
            blocks=linked_blocks,
            document=document,
        )
        text = str(chunk.get("text") or "")
        source_filename = _chunk_text_field(chunk, "source_filename") or normalize_text(source.get("filename"))
        section_title = _chunk_text_field(chunk, "section_title") or (normalize_text(section.get("title")) if section else None)
        resolved_section_path = _chunk_section_path(chunk, section_id, sections_by_id)
        table_row_index = _chunk_int(chunk, "table_row_index") if is_table_item else None
        location_label = build_location_label(
            filename=source_filename,
            section_path=resolved_section_path,
            section_title=section_title,
            page_start=page_start,
            page_end=page_end,
            table_id=table_id,
            table_row_index=table_row_index,
        )
        item = {
            "document_id": normalize_text(chunk.get("document_id")) or normalize_text(metadata.get("document_id")),
            "filename": source_filename,
            "source_filename": source_filename,
            "source_type": _chunk_text_field(chunk, "source_type") or normalize_text(source.get("extension")).lstrip("."),
            "title": normalize_text(metadata.get("title")),
            "chunk_id": normalize_text(chunk.get("chunk_id")),
            "order": chunk.get("order"),
            "chunk_order": chunk.get("order"),
            "content_type": content_type,
            "section_id": section_id,
            "section_title": section_title,
            "section_path": resolved_section_path,
            "page_start": page_start,
            "page_end": page_end,
            "source_block_ids": source_block_ids,
            "table_id": table_id,
            "table_title": _table_title_from_context(chunk, section, linked_blocks) if is_table_item else None,
            "table_headers": table_headers,
            "table_row_index": table_row_index,
            "table_column_values": table_column_values,
            "table_context": _chunk_text_field(chunk, "table_context") if is_table_item else None,
            "row_count": row_count,
            "column_count": column_count,
            "location_label": location_label,
            "citation_label": location_label,
            "text_preview": normalize_text(text)[: max(0, text_preview_chars)],
            "quality_flags": flags,
            "handoff_notes": handoff_notes(flags, content_type, table_id),
        }
        if include_text:
            item["text"] = text
        items.append(item)
    return items


def build_export_report(
    results_dir: Path,
    *,
    max_documents: int | None = None,
    max_chunks_per_document: int | None = None,
    include_text: bool = False,
    text_preview_chars: int = 300,
) -> dict[str, Any]:
    if max_documents is not None and max_documents < 0:
        raise ValueError("max_documents must be greater than or equal to 0")
    if max_chunks_per_document is not None and max_chunks_per_document < 0:
        raise ValueError("max_chunks_per_document must be greater than or equal to 0")
    if text_preview_chars < 0:
        raise ValueError("text_preview_chars must be greater than or equal to 0")

    documents_seen = 0
    documents_with_chunks = 0
    total_chunks = 0
    exported_items: list[dict[str, Any]] = []
    warnings: list[str] = []

    paths = list(iter_processed_json(results_dir))
    for path in paths[:max_documents]:
        documents_seen += 1
        try:
            document = read_json_document(path)
        except ValueError as exc:
            warnings.append(str(exc))
            continue
        chunks = _list_of_dicts(document.get("chunks"))
        if chunks:
            documents_with_chunks += 1
        total_chunks += len(chunks)
        exported_items.extend(
            export_document_chunks(
                document,
                max_chunks=max_chunks_per_document,
                include_text=include_text,
                text_preview_chars=text_preview_chars,
            )
        )

    content_type_counts = Counter(item["content_type"] for item in exported_items)
    flag_counts = Counter(flag for item in exported_items for flag in item["quality_flags"])
    summary = {
        "export_version": EXPORT_VERSION,
        "documents_seen": documents_seen,
        "documents_with_chunks": documents_with_chunks,
        "total_chunks": total_chunks,
        "exported_chunks": len(exported_items),
        "content_type_counts": dict(sorted(content_type_counts.items())),
        "quality_flag_counts": dict(sorted(flag_counts.items())),
        "chunks_missing_section": flag_counts.get("missing_section", 0),
        "chunks_missing_page": flag_counts.get("missing_page", 0),
        "short_chunk_count": flag_counts.get("short_chunk", 0),
        "table_like_chunk_count": flag_counts.get("table_like_text", 0),
        "image_or_ocr_limited_count": flag_counts.get("image_or_ocr_limited", 0),
    }
    limitations = [
        "export is read-only and derived from existing processed JSON only",
        "page numbers are null when linked blocks do not expose page metadata",
        "content_type is conservative and does not perform table analytics or OCR",
    ]
    if warnings:
        limitations.append("some processed JSON files could not be read; see warnings")
    return {
        "taxonomy_version": EXPORT_VERSION,
        "export_version": EXPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "read-only",
        "results_dir": str(results_dir),
        "config": {
            "max_documents": max_documents,
            "max_chunks_per_document": max_chunks_per_document,
            "include_text": include_text,
            "text_preview_chars": text_preview_chars,
        },
        "summary": summary,
        "limitations": limitations,
        "warnings": warnings,
        "items": exported_items,
    }


def write_export_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def print_console_summary(report: dict[str, Any], output_path: Path | None = None) -> None:
    summary = report["summary"]
    print("Stage 29.1 RAG-ready chunk export")
    print(f"taxonomy_version={report['taxonomy_version']}")
    print(
        "documents_seen={documents_seen} documents_with_chunks={documents_with_chunks} "
        "total_chunks={total_chunks} exported_chunks={exported_chunks}".format(**summary)
    )
    print(f"content_type_counts={summary['content_type_counts']}")
    print(f"quality_flag_counts={summary['quality_flag_counts']}")
    print(
        "limitations: read-only export; pages/tables/images shown only when existing metadata allows it; "
        "no RAG/LLM/embeddings/vector DB."
    )
    if output_path:
        print(f"json_report_path={output_path}")
