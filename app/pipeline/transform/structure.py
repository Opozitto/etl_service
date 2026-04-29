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
    text = normalize_text(block.text or "")
    if not text:
        return "text"
    if block.kind in {"heading", "list_item", "table", "image"}:
        return block.kind
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
    for section in sections:
        section_blocks = [block for block in blocks if block.section_id == section.section_id and block.text]
        if not section_blocks:
            continue
        section_chunks = _build_section_chunks(
            section=section,
            section_blocks=section_blocks,
            chunk_counter=chunk_counter,
            start_order=chunk_order,
        )
        chunks.extend(section_chunks)
        chunk_order += len(section_chunks)

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
        chunks.append(
            Chunk(
                chunk_id=f"chk-{next(chunk_counter)}",
                document_id="",
                section_id=section.section_id,
                block_ids=list(dict.fromkeys(current_block_ids)),
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
