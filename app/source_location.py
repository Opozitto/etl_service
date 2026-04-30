from __future__ import annotations

from typing import Any


def normalize_label_part(value: Any) -> str:
    return " ".join(str(value or "").replace("\u00a0", " ").split())


def page_label(page_start: int | None, page_end: int | None) -> str | None:
    if page_start is None and page_end is None:
        return None
    if page_start is not None and page_end is not None and page_start != page_end:
        return f"pages {page_start}-{page_end}"
    page = page_start if page_start is not None else page_end
    return f"page {page}" if page is not None else None


def build_location_label(
    *,
    filename: str | None,
    section_path: list[str] | None = None,
    section_title: str | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    table_id: str | None = None,
    table_row_index: int | None = None,
) -> str | None:
    parts: list[str] = []
    filename_part = normalize_label_part(filename)
    if filename_part:
        parts.append(filename_part)

    table_part = normalize_label_part(table_id)
    if table_part:
        parts.append(f"table {table_part}")
        if table_row_index is not None:
            parts.append(f"row {table_row_index}")
    else:
        path_parts = [normalize_label_part(item) for item in section_path or [] if normalize_label_part(item)]
        if path_parts:
            parts.append(" > ".join(path_parts))
        else:
            title_part = normalize_label_part(section_title)
            if title_part:
                parts.append(title_part)

    page_part = page_label(page_start, page_end)
    if page_part:
        parts.append(page_part)

    return " - ".join(parts) if parts else None
