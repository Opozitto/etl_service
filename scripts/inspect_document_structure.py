from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.core.config import get_settings
from app.evaluation.rag_chunk_export import export_document_chunks, normalize_text
from app.services.document_service import DocumentService


REPORT_VERSION = "stage38_2_single_file_structure_inspector_v1"
DEFAULT_WORKSPACE_DIR = Path(".runtime_eval") / "inspect_document_structure_workspace"
DEFAULT_TEXT_PREVIEW_CHARS = 240
DEFAULT_TABLE_ROW_PREVIEW_LIMIT = 3
PRODUCTION_STORAGE_CHILDREN = {"index", "results", "uploads"}


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def _sha256(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as file_obj:
        while chunk := file_obj.read(1024 * 1024):
            sha256.update(chunk)
    return sha256.hexdigest()


def _preview(value: Any, limit: int) -> str:
    text = normalize_text(value)
    if limit <= 0:
        return ""
    return text[:limit]


def _safe_workspace_dir(path: Path) -> Path:
    if not path.is_absolute():
        first_part = path.parts[0].lower() if path.parts else ""
        if first_part == "storage":
            raise ValueError("workspace dir must not be production storage or a storage/* path")

    resolved = path.resolve()
    if resolved.anchor == str(resolved):
        raise ValueError(f"workspace dir is not safe: {resolved}")

    production_storage = get_settings().resolved_storage_dir.resolve()
    if resolved == production_storage or production_storage in resolved.parents:
        raise ValueError(f"workspace dir must not be inside production storage: {resolved}")

    for child_name in PRODUCTION_STORAGE_CHILDREN:
        child = (production_storage / child_name).resolve()
        if resolved == child or child in resolved.parents:
            raise ValueError(f"workspace dir must not be inside production storage/{child_name}: {resolved}")

    return resolved


def _reject_production_storage_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    production_storage = get_settings().resolved_storage_dir.resolve()
    if resolved == production_storage or production_storage in resolved.parents:
        raise ValueError(f"{label} must not be inside production storage: {resolved}")
    return resolved


def prepare_workspace(workspace_dir: Path, *, clean_workspace: bool) -> Path:
    resolved = _safe_workspace_dir(workspace_dir)
    if clean_workspace and resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _limit(items: Sequence[Any], max_items: int | None) -> tuple[list[Any], dict[str, int | bool]]:
    total = len(items)
    if max_items is None:
        limited = list(items)
    else:
        limited = list(items[:max_items])
    return limited, {
        "total": total,
        "shown": len(limited),
        "truncated": len(limited) < total,
    }


def _section_lookup(document) -> dict[str, Any]:
    return {section.section_id: section for section in document.sections}


def _section_context(section_id: str | None, sections_by_id: dict[str, Any]) -> dict[str, Any]:
    if not section_id or section_id not in sections_by_id:
        return {"section_title": None, "section_path": []}
    path: list[str] = []
    seen: set[str] = set()
    current_id: str | None = section_id
    while current_id and current_id not in seen:
        seen.add(current_id)
        section = sections_by_id.get(current_id)
        if section is None:
            break
        if section.title:
            path.append(section.title)
        current_id = section.parent_id
    path.reverse()
    return {
        "section_title": sections_by_id[section_id].title,
        "section_path": path,
    }


def _metadata_summary(document) -> dict[str, Any]:
    return {
        "document_id": document.metadata.document_id,
        "title": document.metadata.title,
        "language": document.metadata.language,
        "created_at": document.metadata.created_at.isoformat(),
        "processed_at": document.metadata.processed_at.isoformat(),
        "page_count": document.metadata.page_count,
        "section_count": document.metadata.section_count,
        "block_count": document.metadata.block_count,
        "table_count": document.metadata.table_count,
        "image_count": document.metadata.image_count,
        "chunk_count": len(document.chunks),
    }


def _processing_summary(document) -> dict[str, Any]:
    processing = document.processing_info
    return {
        "extractor": processing.extractor,
        "transform_version": processing.transform_version,
        "warnings": processing.warnings,
        "features": processing.features,
        "ocr_candidate": processing.ocr_candidate,
        "ocr_reason": processing.ocr_reason,
        "source_encoding": processing.source_encoding,
        "text_char_count": processing.text_char_count,
        "text_block_count": processing.text_block_count,
        "extractor_metadata": processing.extractor_metadata,
    }


def _sections_preview(document) -> list[dict[str, Any]]:
    return [
        {
            "section_id": section.section_id,
            "title": section.title,
            "level": section.level,
            "parent_id": section.parent_id,
            "order": section.order,
            "page_start": section.page_start,
            "page_end": section.page_end,
            "block_count": len(section.block_ids),
            "block_ids": section.block_ids,
        }
        for section in document.sections
    ]


def _blocks_preview(document, *, max_blocks: int | None, text_preview_chars: int) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    sections_by_id = _section_lookup(document)
    blocks, limits = _limit(document.blocks, max_blocks)
    return [
        {
            "block_id": block.block_id,
            "order": block.order,
            "type": block.type,
            "section_id": block.section_id,
            **_section_context(block.section_id, sections_by_id),
            "page_num": block.page_num,
            "metadata": block.metadata,
            "text_preview": _preview(block.text, text_preview_chars),
        }
        for block in blocks
    ], limits


def _chunks_preview(document, *, max_chunks: int | None, text_preview_chars: int) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    exported = export_document_chunks(
        document.model_dump(mode="json"),
        max_chunks=max_chunks,
        include_text=False,
        text_preview_chars=text_preview_chars,
    )
    return [
        {
            "chunk_id": item["chunk_id"],
            "order": item["order"],
            "chunk_order": item["chunk_order"],
            "content_type": item["content_type"],
            "section_id": item["section_id"],
            "section_title": item["section_title"],
            "section_path": item["section_path"],
            "page_start": item["page_start"],
            "page_end": item["page_end"],
            "source_block_ids": item["source_block_ids"],
            "block_ids": item["source_block_ids"],
            "table_id": item["table_id"],
            "table_title": item["table_title"],
            "table_headers": item["table_headers"],
            "table_row_index": item["table_row_index"],
            "table_column_values": item["table_column_values"],
            "table_context": item["table_context"],
            "row_count": item["row_count"],
            "column_count": item["column_count"],
            "location_label": item["location_label"],
            "citation_label": item["citation_label"],
            "token_estimate": next(
                (chunk.token_estimate for chunk in document.chunks if chunk.chunk_id == item["chunk_id"]),
                None,
            ),
            "text_preview": item["text_preview"],
            "quality_flags": item["quality_flags"],
            "handoff_notes": item["handoff_notes"],
        }
        for item in exported
    ], {
        "total": len(document.chunks),
        "shown": len(exported),
        "truncated": len(exported) < len(document.chunks),
    }


def _headers_from_rows(rows: list[list[str]]) -> list[str]:
    if len(rows) <= 1:
        return []
    return [normalize_text(cell) for cell in rows[0] if normalize_text(cell)]


def _tables_preview(document, *, max_tables: int | None, text_preview_chars: int) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    sections_by_id = _section_lookup(document)
    tables, limits = _limit(document.tables, max_tables)
    items: list[dict[str, Any]] = []
    for table in tables:
        rows = [
            [_preview(cell, text_preview_chars) for cell in row]
            for row in table.rows[:DEFAULT_TABLE_ROW_PREVIEW_LIMIT]
        ]
        items.append(
            {
                "table_id": table.table_id,
                "order": table.order,
                "section_id": table.section_id,
                **_section_context(table.section_id, sections_by_id),
                "page_num": table.page_num,
                "n_rows": table.n_rows,
                "n_cols": table.n_cols,
                "headers": _headers_from_rows(table.rows),
                "rows_preview": rows,
                "rows_preview_count": len(rows),
            }
        )
    return items, limits


def _images_preview(document, *, max_images: int | None, text_preview_chars: int) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    sections_by_id = _section_lookup(document)
    images, limits = _limit(document.images, max_images)
    return [
        {
            "image_id": image.image_id,
            "order": image.order,
            "section_id": image.section_id,
            **_section_context(image.section_id, sections_by_id),
            "page_num": image.page_num,
            "caption_preview": _preview(image.caption, text_preview_chars),
            "metadata": image.metadata,
        }
        for image in images
    ], limits


def _artifacts_summary(document, workspace_dir: Path) -> dict[str, Any]:
    return {
        "workspace_dir": str(workspace_dir),
        "uploads_dir": str(workspace_dir / get_settings().uploads_dir_name),
        "results_dir": str(workspace_dir / get_settings().results_dir_name),
        "index_dir": str(workspace_dir / get_settings().index_dir_name),
        "result_json_path": document.artifacts.result_json_path,
        "source_file_path": document.artifacts.source_file_path,
        "saved_source_path": document.source.saved_path,
    }


def _input_summary(input_path: Path) -> dict[str, Any]:
    return {
        "input_path": str(input_path),
        "filename": input_path.name,
        "extension": input_path.suffix.lower(),
        "size_bytes": input_path.stat().st_size if input_path.exists() else None,
        "checksum_sha256": _sha256(input_path) if input_path.exists() and input_path.is_file() else None,
    }


def _failed_report(
    *,
    input_path: Path,
    workspace_dir: Path,
    error: Exception,
    text_preview_chars: int,
    max_blocks: int | None,
    max_chunks: int | None,
    max_tables: int | None,
    max_images: int | None,
) -> dict[str, Any]:
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "error",
        "error_message": str(error),
        "input": _input_summary(input_path),
        "workspace_dir": str(workspace_dir),
        "config": {
            "text_preview_chars": text_preview_chars,
            "max_blocks": max_blocks,
            "max_chunks": max_chunks,
            "max_tables": max_tables,
            "max_images": max_images,
        },
        "document_id": None,
        "metadata": None,
        "source": None,
        "processing_info": None,
        "counts": {
            "sections": 0,
            "blocks": 0,
            "chunks": 0,
            "tables": 0,
            "images": 0,
        },
        "limits": {},
        "sections": [],
        "blocks": [],
        "chunks": [],
        "tables": [],
        "images": [],
        "artifacts": {
            "workspace_dir": str(workspace_dir),
            "uploads_dir": str(workspace_dir / get_settings().uploads_dir_name),
            "results_dir": str(workspace_dir / get_settings().results_dir_name),
            "index_dir": str(workspace_dir / get_settings().index_dir_name),
            "result_json_path": None,
            "source_file_path": None,
            "saved_source_path": None,
        },
        "limitations": [
            "processing failed; sections/blocks/chunks/tables/images are not reported as successful output",
            "inspector does not run scanned PDF OCR, embedded DOCX/PDF OCR, LLM/RAG, embeddings or table analytics",
        ],
    }


def build_inspection_report(
    *,
    input_path: Path,
    workspace_dir: Path = DEFAULT_WORKSPACE_DIR,
    text_preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS,
    max_blocks: int | None = None,
    max_chunks: int | None = None,
    max_tables: int | None = None,
    max_images: int | None = None,
    clean_workspace: bool = False,
) -> dict[str, Any]:
    if text_preview_chars < 0:
        raise ValueError("text_preview_chars must be greater than or equal to 0")
    for label, value in {
        "max_blocks": max_blocks,
        "max_chunks": max_chunks,
        "max_tables": max_tables,
        "max_images": max_images,
    }.items():
        if value is not None and value < 0:
            raise ValueError(f"{label} must be greater than or equal to 0")

    resolved_input = input_path.resolve()
    if not resolved_input.exists():
        raise ValueError(f"input path not found: {resolved_input}")
    if not resolved_input.is_file():
        raise ValueError(f"input path must be a file: {resolved_input}")

    resolved_workspace = prepare_workspace(workspace_dir, clean_workspace=clean_workspace)
    config = {
        "text_preview_chars": text_preview_chars,
        "max_blocks": max_blocks,
        "max_chunks": max_chunks,
        "max_tables": max_tables,
        "max_images": max_images,
    }

    try:
        outcome = DocumentService(storage_root=resolved_workspace).process_path_with_status(resolved_input)
    except Exception as exc:
        return _failed_report(
            input_path=resolved_input,
            workspace_dir=resolved_workspace,
            error=exc,
            text_preview_chars=text_preview_chars,
            max_blocks=max_blocks,
            max_chunks=max_chunks,
            max_tables=max_tables,
            max_images=max_images,
        )

    document = outcome.document
    blocks, block_limits = _blocks_preview(document, max_blocks=max_blocks, text_preview_chars=text_preview_chars)
    chunks, chunk_limits = _chunks_preview(document, max_chunks=max_chunks, text_preview_chars=text_preview_chars)
    tables, table_limits = _tables_preview(document, max_tables=max_tables, text_preview_chars=text_preview_chars)
    images, image_limits = _images_preview(document, max_images=max_images, text_preview_chars=text_preview_chars)
    counts = {
        "sections": len(document.sections),
        "blocks": len(document.blocks),
        "chunks": len(document.chunks),
        "tables": len(document.tables),
        "images": len(document.images),
        "warnings": len(document.processing_info.warnings),
    }
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": outcome.status,
        "input": _input_summary(resolved_input),
        "workspace_dir": str(resolved_workspace),
        "config": config,
        "document_id": document.metadata.document_id,
        "metadata": _metadata_summary(document),
        "source": document.source.model_dump(mode="json"),
        "processing_info": _processing_summary(document),
        "counts": counts,
        "limits": {
            "blocks": block_limits,
            "chunks": chunk_limits,
            "tables": table_limits,
            "images": image_limits,
        },
        "sections": _sections_preview(document),
        "blocks": blocks,
        "chunks": chunks,
        "tables": tables,
        "images": images,
        "artifacts": _artifacts_summary(document, resolved_workspace),
        "limitations": [
            "report previews are bounded; full text is intentionally not included by default",
            "page values are null when extractor/block metadata does not expose page context",
            "content_type and location labels use existing deterministic metadata only",
            "inspector does not run scanned PDF OCR, embedded DOCX/PDF OCR, LLM/RAG, embeddings or table analytics",
            "workspace output is runtime inspection data and is not intended to be committed",
        ],
    }


def write_json_report(path: Path, report: dict[str, Any]) -> Path:
    resolved = _reject_production_storage_path(path, "json report path")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved


def render_markdown_report(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Single-file structure inspector",
        "",
        f"- report_version: `{report['report_version']}`",
        f"- status: `{report['status']}`",
        f"- input: `{report['input']['input_path']}`",
        f"- workspace: `{report['workspace_dir']}`",
        f"- document_id: `{report.get('document_id')}`",
        "",
    ]
    if report["status"] == "error":
        lines.extend(["## Error", "", report.get("error_message") or "unknown error", ""])
    lines.extend(
        [
            "## Counts",
            "",
            "| item | count |",
            "| --- | ---: |",
        ]
    )
    for key, value in report["counts"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")

    metadata = report.get("metadata") or {}
    processing = report.get("processing_info") or {}
    lines.extend(
        [
            "## Metadata",
            "",
            f"- title: `{metadata.get('title')}`",
            f"- extractor: `{processing.get('extractor')}`",
            f"- source_encoding: `{processing.get('source_encoding')}`",
            f"- text_char_count: `{processing.get('text_char_count')}`",
            f"- text_block_count: `{processing.get('text_block_count')}`",
            f"- warnings: `{processing.get('warnings') or []}`",
            f"- features: `{processing.get('features') or {}}`",
            "",
            "## Sections",
            "",
        ]
    )
    for section in report["sections"]:
        lines.append(
            "- `{section_id}` order={order} level={level} title={title} blocks={block_count}".format(**section)
        )
    if not report["sections"]:
        lines.append("- none")
    lines.append("")

    _append_item_section(lines, "Blocks", report["blocks"], report["limits"].get("blocks", {}), "block_id")
    _append_item_section(lines, "Chunks", report["chunks"], report["limits"].get("chunks", {}), "chunk_id")
    _append_item_section(lines, "Tables", report["tables"], report["limits"].get("tables", {}), "table_id")
    _append_item_section(lines, "Images", report["images"], report["limits"].get("images", {}), "image_id")

    lines.extend(["## Artifacts", ""])
    for key, value in report["artifacts"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Limitations / notes", ""])
    for note in report["limitations"]:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def _append_item_section(lines: list[str], title: str, items: list[dict[str, Any]], limits: dict[str, Any], id_field: str) -> None:
    lines.extend([f"## {title}", ""])
    if limits:
        lines.append(
            f"_shown {limits.get('shown')} of {limits.get('total')}; truncated={str(limits.get('truncated')).lower()}_"
        )
        lines.append("")
    if not items:
        lines.extend(["- none", ""])
        return
    for item in items:
        lines.append(f"### `{item.get(id_field)}`")
        lines.append("")
        for key, value in item.items():
            if key == id_field:
                continue
            if isinstance(value, (dict, list)):
                rendered = json.dumps(value, ensure_ascii=False)
            else:
                rendered = str(value)
            lines.append(f"- {key}: `{rendered}`")
        lines.append("")


def write_markdown_report(path: Path, report: dict[str, Any]) -> Path:
    resolved = _reject_production_storage_path(path, "markdown report path")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(render_markdown_report(report), encoding="utf-8")
    return resolved


def print_console_summary(report: dict[str, Any]) -> None:
    print("Stage 38.2 single-file structure inspector")
    print(f"status={report['status']}")
    print(f"input_path={report['input']['input_path']}")
    print(f"workspace_dir={report['workspace_dir']}")
    print(f"document_id={report.get('document_id')}")
    if report["status"] == "error":
        print(f"error={report.get('error_message')}")
    counts = report["counts"]
    print(
        "sections={sections} blocks={blocks} chunks={chunks} tables={tables} images={images} warnings={warnings}".format(
            **counts
        )
    )
    processing = report.get("processing_info") or {}
    print(f"extractor={processing.get('extractor')} source_encoding={processing.get('source_encoding')}")
    print("limitations: bounded previews; temporary workspace only; no RAG/LLM/OCR expansion/table analytics.")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Inspect one document structure in an isolated temporary workspace")
    parser.add_argument("--input-path", required=True, help="Path to one input file")
    parser.add_argument("--workspace-dir", default=str(DEFAULT_WORKSPACE_DIR), help="Temporary workspace root")
    parser.add_argument("--output-path", help="Optional Markdown report path")
    parser.add_argument("--json-report-path", help="Optional JSON report path")
    parser.add_argument("--text-preview-chars", type=non_negative_int, default=DEFAULT_TEXT_PREVIEW_CHARS)
    parser.add_argument("--max-blocks", type=non_negative_int)
    parser.add_argument("--max-chunks", type=non_negative_int)
    parser.add_argument("--max-tables", type=non_negative_int)
    parser.add_argument("--max-images", type=non_negative_int)
    parser.add_argument("--clean-workspace", action="store_true", help="Clean the safe temporary workspace before processing")
    parser.add_argument("--keep-workspace", action="store_true", help="Accepted for explicitness; workspace is kept by default")
    args = parser.parse_args(argv)

    try:
        report = build_inspection_report(
            input_path=Path(args.input_path),
            workspace_dir=Path(args.workspace_dir),
            text_preview_chars=args.text_preview_chars,
            max_blocks=args.max_blocks,
            max_chunks=args.max_chunks,
            max_tables=args.max_tables,
            max_images=args.max_images,
            clean_workspace=args.clean_workspace,
        )
        markdown_path = write_markdown_report(Path(args.output_path), report) if args.output_path else None
        json_path = write_json_report(Path(args.json_report_path), report) if args.json_report_path else None
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if markdown_path:
        print(f"markdown_report_path={markdown_path}")
    if json_path:
        print(f"json_report_path={json_path}")
    if not markdown_path and not json_path:
        print_console_summary(report)

    if report["status"] == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
