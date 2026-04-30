from __future__ import annotations

import re
from itertools import count
from typing import Optional

from app.pipeline.transform.normalizer import estimate_tokens, normalize_text
from app.pipeline.types import ExtractedDocument, RawBlock
from app.schemas.document import Block, Chunk, ImageInfo, Section, TableCell, TableData


HEADING_RE = re.compile(r"^(\d+(\.\d+)*\.?|[IVXLC]+\.?)\s+.+$")
LIST_RE = re.compile(r"^(\-|\*|•|\d+\.)\s+.+$")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?;])\s+")


def classify_text_block(block: RawBlock) -> str:
    if block.kind in {"heading", "list_item", "table", "image"}:
        return block.kind
    text = normalize_text(block.text or "")
    if not text:
        return "text"
    if block.style_hint and "heading" in block.style_hint.lower():
        return "heading"
    if HEADING_RE.match(text):
        return "heading"
    if LIST_RE.match(text):
        return "list_item"
    if text.isupper() and 3 <= len(text.split()) <= 12:
        return "heading"
    return "paragraph"


def heading_level(text: str) -> int:
    matched = HEADING_RE.match(text)
    if matched:
        marker = matched.group(1)
        return min(marker.count(".") + 1, 6)
    return 1


def build_structure(
    extracted: ExtractedDocument,
) -> tuple[list[Section], list[Block], list[TableData], list[ImageInfo], list[Chunk]]:
    sections: list[Section] = []
    blocks: list[Block] = []
    tables: list[TableData] = []
    images: list[ImageInfo] = []
    chunks: list[Chunk] = []
    table_block_ids: dict[str, str] = {}

    section_counter = count(1)
    block_counter = count(1)
    table_counter = count(1)
    image_counter = count(1)
    chunk_counter = count(1)

    root_section = Section(section_id="sec-0", title="Document", level=0, order=0)
    sections.append(root_section)
    current_section_id = root_section.section_id
    section_stack: list[Section] = [root_section]

    for raw in extracted.blocks:
        kind = classify_text_block(raw)
        text = normalize_text(raw.text or "")

        if kind == "heading" and text:
            level = heading_level(text)
            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()
            parent_id = section_stack[-1].section_id if section_stack else root_section.section_id
            section = Section(
                section_id=f"sec-{next(section_counter)}",
                title=text,
                level=level,
                parent_id=parent_id,
                order=len(sections),
                page_start=raw.page_num,
                page_end=raw.page_num,
            )
            sections.append(section)
            section_stack.append(section)
            current_section_id = section.section_id

        if kind == "table":
            table_id = f"tbl-{next(table_counter)}"
            rows = raw.data or []
            table = TableData(
                table_id=table_id,
                order=len(tables),
                section_id=current_section_id,
                page_num=raw.page_num,
                n_rows=len(rows),
                n_cols=max((len(row) for row in rows), default=0),
                rows=rows,
                cells=[
                    TableCell(row=row_idx, column=col_idx, value=value)
                    for row_idx, row in enumerate(rows)
                    for col_idx, value in enumerate(row)
                ],
            )
            tables.append(table)
            block = Block(
                block_id=f"blk-{next(block_counter)}",
                type="table",
                order=len(blocks),
                text=text or None,
                section_id=current_section_id,
                page_num=raw.page_num,
                metadata={"table_id": table_id, **raw.metadata},
            )
            blocks.append(block)
            table_block_ids[table_id] = block.block_id
            _attach_block_to_section(sections, current_section_id, block.block_id, raw.page_num)
            continue

        if kind == "image":
            image = ImageInfo(
                image_id=f"img-{next(image_counter)}",
                order=len(images),
                page_num=raw.page_num,
                section_id=current_section_id,
                metadata=raw.metadata,
            )
            images.append(image)
            block = Block(
                block_id=f"blk-{next(block_counter)}",
                type="image",
                order=len(blocks),
                text=text or None,
                section_id=current_section_id,
                page_num=raw.page_num,
                metadata={"image_id": image.image_id, **raw.metadata},
            )
            blocks.append(block)
            _attach_block_to_section(sections, current_section_id, block.block_id, raw.page_num)
            continue

        if text:
            block = Block(
                block_id=f"blk-{next(block_counter)}",
                type=kind,
                order=len(blocks),
                text=text,
                section_id=current_section_id,
                page_num=raw.page_num,
                metadata=raw.metadata,
            )
            blocks.append(block)
            _attach_block_to_section(sections, current_section_id, block.block_id, raw.page_num)

    chunk_order = 0
    section_paths = _section_paths_by_id(sections)
    for section in sections:
        section_blocks = [block for block in blocks if block.section_id == section.section_id and block.text]
        if not section_blocks:
            continue
        section_chunks = _build_section_chunks(
            section=section,
            section_blocks=section_blocks,
            section_path=section_paths.get(section.section_id, []),
            chunk_counter=chunk_counter,
            start_order=chunk_order,
        )
        chunks.extend(section_chunks)
        chunk_order += len(section_chunks)

    for table in tables:
        table_block_id = table_block_ids.get(table.table_id)
        if not table_block_id:
            continue
        table_section = next((section for section in sections if section.section_id == table.section_id), root_section)
        row_chunks = _build_table_row_chunks(
            table=table,
            section=table_section,
            section_path=section_paths.get(table_section.section_id, []),
            table_block_id=table_block_id,
            chunk_counter=chunk_counter,
            start_order=chunk_order,
            table_title=_table_title(table_section),
            sheet_name=_table_sheet_name(blocks, table_block_id),
        )
        chunks.extend(row_chunks)
        chunk_order += len(row_chunks)

    return sections, blocks, tables, images, chunks


def _attach_block_to_section(
    sections: list[Section], section_id: str, block_id: str, page_num: Optional[int]
) -> None:
    for section in sections:
        if section.section_id == section_id:
            section.block_ids.append(block_id)
            if page_num is not None:
                if section.page_start is None or page_num < section.page_start:
                    section.page_start = page_num
                if section.page_end is None or page_num > section.page_end:
                    section.page_end = page_num
            return


def _build_section_chunks(
    section: Section,
    section_blocks: list[Block],
    section_path: list[str],
    chunk_counter,
    start_order: int,
    max_chars: int = 1200,
    target_chars: int = 850,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_block_ids: list[str] = []
    order = start_order
    heading_context = section.title if section.level > 0 else ""

    def flush() -> None:
        nonlocal current_parts, current_block_ids, order
        chunk_text = normalize_text("\n".join(part for part in current_parts if part).strip())
        if not chunk_text:
            current_parts = []
            current_block_ids = []
            return
        unique_block_ids = list(dict.fromkeys(current_block_ids))
        chunk_blocks = [block for block in section_blocks if block.block_id in set(unique_block_ids)]
        page_start, page_end = _page_range_from_blocks(chunk_blocks)
        table_id = _table_id_from_blocks(chunk_blocks)
        chunks.append(
            Chunk(
                chunk_id=f"chk-{next(chunk_counter)}",
                document_id="",
                section_id=section.section_id,
                block_ids=unique_block_ids,
                content_type=_content_type_from_blocks(chunk_blocks),
                section_title=section.title,
                section_path=section_path,
                page_start=page_start,
                page_end=page_end,
                table_id=table_id,
                text=chunk_text,
                order=order,
                token_estimate=estimate_tokens(chunk_text),
            )
        )
        order += 1
        overlap_parts = current_parts[-2:] if len(current_parts) > 2 else current_parts[-1:]
        overlap_block_ids = current_block_ids[-2:] if len(current_block_ids) > 2 else current_block_ids[-1:]
        current_parts = list(overlap_parts)
        current_block_ids = list(overlap_block_ids)

    for block in section_blocks:
        block_text = normalize_text(block.text or "")
        if not block_text:
            continue
        for part in _split_block_for_chunking(block_text):
            candidate_parts = list(current_parts)
            candidate_ids = list(current_block_ids)
            if not candidate_parts and heading_context:
                candidate_parts.append(heading_context)
            candidate_parts.append(part)
            candidate_ids.append(block.block_id)
            candidate_text = normalize_text("\n".join(candidate_parts))

            if len(candidate_text) > max_chars and current_parts:
                flush()
                candidate_parts = list(current_parts)
                candidate_ids = list(current_block_ids)
                if not candidate_parts and heading_context:
                    candidate_parts.append(heading_context)
                candidate_parts.append(part)
                candidate_ids.append(block.block_id)

            current_parts = candidate_parts
            current_block_ids = candidate_ids

            if len(normalize_text("\n".join(current_parts))) >= target_chars:
                flush()

    if current_parts:
        flush()
    return chunks


def _build_table_row_chunks(
    table: TableData,
    section: Section,
    section_path: list[str],
    table_block_id: str,
    chunk_counter,
    start_order: int,
    table_title: str,
    sheet_name: str,
) -> list[Chunk]:
    rows = [row for row in table.rows if any(normalize_text(cell) for cell in row)]
    if not rows:
        return []

    chunks: list[Chunk] = []
    order = start_order
    headers = rows[0] if len(rows) > 1 else []
    data_rows = rows[1:] if len(rows) > 1 else rows

    for row_index, row in enumerate(data_rows, start=2 if len(rows) > 1 else 1):
        column_values = _table_column_values(headers, row)
        table_context = _format_table_context(table.table_id, table_title, sheet_name, section_path)
        row_text = _format_table_row_text(
            table_context=table_context,
            row_index=row_index,
            row_count=table.n_rows,
            headers=headers,
            row=row,
        )
        if not row_text:
            continue
        chunks.append(
            Chunk(
                chunk_id=f"chk-{next(chunk_counter)}",
                document_id="",
                section_id=section.section_id,
                block_ids=[table_block_id],
                content_type="table_row",
                section_title=section.title,
                section_path=section_path,
                page_start=table.page_num,
                page_end=table.page_num,
                table_id=table.table_id,
                table_title=table_title or sheet_name or None,
                table_headers=[normalize_text(header) for header in headers if normalize_text(header)],
                table_row_index=row_index,
                table_column_values=column_values,
                table_context=table_context or None,
                row_count=table.n_rows,
                column_count=table.n_cols,
                text=row_text,
                order=order,
                token_estimate=estimate_tokens(row_text),
            )
        )
        order += 1
    return chunks


def _format_table_row_text(
    table_context: str,
    row_index: int,
    row_count: int,
    headers: list[str],
    row: list[str],
) -> str:
    context_parts: list[str] = []
    if table_context:
        context_parts.append(table_context)

    value_parts: list[str] = []
    unlabeled_values: list[str] = []
    for column_index, value in enumerate(row):
        value_text = normalize_text(value)
        if not value_text:
            continue
        header_text = normalize_text(headers[column_index]) if column_index < len(headers) else ""
        if header_text:
            value_parts.append(f"{header_text}: {value_text}")
        else:
            unlabeled_values.append(value_text)

    if not value_parts and not unlabeled_values:
        return ""

    if row_count:
        context_parts.append(f"Строка {row_index} из {row_count}.")
    else:
        context_parts.append(f"Строка {row_index}.")
    if value_parts:
        context_parts.append("Колонки: " + "; ".join(value_parts))
    if unlabeled_values:
        context_parts.append("Значения строки: " + "; ".join(unlabeled_values))
    return normalize_text(" ".join(context_parts))


def _table_column_values(headers: list[str], row: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for column_index, header in enumerate(headers):
        header_text = normalize_text(header)
        value_text = normalize_text(row[column_index]) if column_index < len(row) else ""
        if header_text and value_text:
            values[header_text] = value_text
    return values


def _format_table_context(table_id: str, table_title: str, sheet_name: str, section_path: list[str]) -> str:
    parts: list[str] = []
    title = table_title or sheet_name
    if title:
        parts.append(f"Таблица {table_id}: {title}")
    else:
        parts.append(f"Таблица: {table_id}")
    if section_path:
        parts.append("Раздел: " + " > ".join(section_path))
    if sheet_name and sheet_name != title:
        parts.append(f"Лист: {sheet_name}")
    return normalize_text(". ".join(parts))


def _table_title(section: Section) -> str:
    if section.title and section.title != "Document":
        return section.title
    return ""


def _table_sheet_name(blocks: list[Block], table_block_id: str) -> str:
    for block in blocks:
        if block.block_id == table_block_id:
            return normalize_text(str(block.metadata.get("sheet_name", "")))
    return ""


def _section_paths_by_id(sections: list[Section]) -> dict[str, list[str]]:
    sections_by_id = {section.section_id: section for section in sections}
    paths: dict[str, list[str]] = {}
    for section in sections:
        current_id: str | None = section.section_id
        seen: set[str] = set()
        path: list[str] = []
        while current_id and current_id not in seen:
            seen.add(current_id)
            current = sections_by_id.get(current_id)
            if current is None:
                break
            if current.title:
                path.append(current.title)
            current_id = current.parent_id
        paths[section.section_id] = list(reversed(path))
    return paths


def _page_range_from_blocks(blocks: list[Block]) -> tuple[int | None, int | None]:
    pages = [block.page_num for block in blocks if block.page_num is not None]
    if not pages:
        return None, None
    return min(pages), max(pages)


def _table_id_from_blocks(blocks: list[Block]) -> str | None:
    table_ids = {
        normalize_text(str(block.metadata.get("table_id", "")))
        for block in blocks
        if isinstance(block.metadata, dict) and normalize_text(str(block.metadata.get("table_id", "")))
    }
    if len(table_ids) == 1:
        return next(iter(table_ids))
    return None


def _content_type_from_blocks(blocks: list[Block]) -> str:
    block_types = {block.type for block in blocks}
    if block_types == {"table"}:
        return "table"
    if block_types == {"image"}:
        return "image"
    if block_types.intersection({"paragraph", "heading", "list_item", "text", "table", "image"}):
        return "text"
    return "unknown"


def _split_block_for_chunking(text: str) -> list[str]:
    if len(text) <= 350:
        return [text]
    sentences = [item.strip() for item in SENTENCE_SPLIT_RE.split(text) if item.strip()]
    if len(sentences) <= 1:
        return _split_by_length(text, 320)

    parts: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= 320:
            current = candidate
            continue
        if current:
            parts.append(current)
        if len(sentence) > 320:
            parts.extend(_split_by_length(sentence, 320))
            current = ""
        else:
            current = sentence
    if current:
        parts.append(current)
    return parts or [text]


def _split_by_length(text: str, size: int) -> list[str]:
    return [text[idx : idx + size].strip() for idx in range(0, len(text), size) if text[idx : idx + size].strip()]
