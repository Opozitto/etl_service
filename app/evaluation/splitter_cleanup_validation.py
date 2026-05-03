from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evaluation.rag_chunk_export import iter_processed_json, read_json_document
from app.services.document_service import DocumentService


VALIDATION_VERSION = "stage33_2_splitter_cleanup_validation_v1"

TOC_TITLES = {"содержание", "оглавление", "table of contents"}
BODY_HEADING_RE = re.compile(r"^(\d+(\.\d+)*\.?|[IVXLC]+\.?)\s+\S+", re.IGNORECASE)
SIGNATURE_PLACEHOLDER_RE = re.compile(r"/\s*[_-]{3,}\s*/|[_-]{5,}")
YEAR_LABEL_RE = re.compile(r"\b20\d{2}\s*г\.?", re.IGNORECASE)
SERVICE_TERMS = (
    "утверждаю",
    "утверждено",
    "согласовано",
    "согласовал",
    "подпись",
    "должность",
    "коммерческий директор",
    "ф.и.о",
    "фио",
    "разработал",
    "проверил",
    "лист согласования",
    "(число)",
    "(месяц)",
    "approval",
    "signature",
)

LIMITATIONS = [
    "DOCX page metadata may remain null; this validation does not invent pages.",
    "Validation is deterministic and conservative; it is not semantic document understanding.",
    "No RAG/LLM/embeddings/vector DB/reranking/OCR/table analytics.",
]


def normalize_for_match(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip().casefold()


def text_preview(value: Any, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()
    return normalized[: max(0, limit)]


def is_toc_title(value: Any) -> bool:
    return normalize_for_match(value).strip(" .:;") in TOC_TITLES


def is_duplicate_heading_text(text: str) -> bool:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    first = normalize_for_match(lines[0])
    second = normalize_for_match(lines[1])
    return bool(first and first == second)


def is_toc_parent_violation(section_path: list[Any]) -> bool:
    normalized_path = [normalize_for_match(item).strip(" .:;") for item in section_path if normalize_for_match(item)]
    for index, title in enumerate(normalized_path[:-1]):
        if title not in TOC_TITLES:
            continue
        descendants = normalized_path[index + 1 :]
        if not descendants or all(item in TOC_TITLES for item in descendants):
            return False
        last = descendants[-1]
        return bool(BODY_HEADING_RE.match(last)) or last not in TOC_TITLES
    return False


def is_heading_only_chunk(item: dict[str, Any]) -> bool:
    text = str(item.get("text") or "")
    stripped = text.strip()
    if not stripped:
        return False
    if str(item.get("content_type") or "text") not in {"text", "heading", "unknown", "None", ""}:
        return False
    section_path = list(item.get("section_path") or [])
    section_title = item.get("section_title") or (section_path[-1] if section_path else "")
    if is_toc_title(section_title):
        return False
    if is_service_text(stripped):
        return False

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    words = re.findall(r"\w+", stripped, flags=re.UNICODE)
    if len(lines) > 2 or len(stripped) > 120 or len(words) > 10:
        return False

    normalized_text = normalize_for_match(stripped).strip(" .:;")
    normalized_section = normalize_for_match(section_title).strip(" .:;")
    if normalized_section and normalized_text == normalized_section:
        return True
    if len(lines) == 1 and BODY_HEADING_RE.match(stripped):
        return True
    if len(lines) == 1 and stripped.isupper() and len(words) <= 8:
        return True
    return False


def is_service_text(text: str) -> bool:
    normalized = normalize_for_match(text)
    return any(term in normalized for term in SERVICE_TERMS)


def service_signature_signal_count(text: str) -> int:
    normalized = normalize_for_match(text)
    signature_placeholders = SIGNATURE_PLACEHOLDER_RE.findall(normalized)
    return sum(
        [
            any(term in normalized for term in ("утверждаю", "утверждено", "согласовано", "согласовал")),
            "коммерческий директор" in normalized,
            "подпись" in normalized,
            len(signature_placeholders) >= 2,
            bool(YEAR_LABEL_RE.search(normalized)) and ("(число)" in normalized or "(месяц)" in normalized),
        ]
    )


def is_real_table_chunk(item: dict[str, Any]) -> bool:
    content_type = str(item.get("content_type") or "")
    if content_type not in {"table", "table_row"} and not item.get("table_id"):
        return False
    if item.get("table_headers") or item.get("table_column_values") or item.get("table_context"):
        return True
    if is_service_text(str(item.get("text") or "")):
        return False
    row_count = item.get("row_count")
    column_count = item.get("column_count")
    return isinstance(row_count, int) and isinstance(column_count, int) and row_count >= 2 and column_count >= 2


def is_service_table_suspect(item: dict[str, Any]) -> bool:
    content_type = str(item.get("content_type") or "")
    if content_type not in {"table", "table_row"} and not item.get("table_id"):
        return False
    if is_real_table_chunk(item):
        return False
    text = str(item.get("text") or "")
    if not is_service_text(text):
        return False
    row_count = item.get("row_count")
    column_count = item.get("column_count")
    has_shape = isinstance(row_count, int) and isinstance(column_count, int)
    if has_shape and (row_count <= 4 or column_count <= 3):
        return True
    return service_signature_signal_count(text) >= 3


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _source_filename(document: dict[str, Any], fallback: str = "") -> str:
    source = document.get("source")
    if isinstance(source, dict):
        return str(source.get("filename") or fallback)
    return fallback


def _metadata(document: dict[str, Any]) -> dict[str, Any]:
    value = document.get("metadata")
    return value if isinstance(value, dict) else {}


def _sections_by_id(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(section.get("section_id") or ""): section for section in _list_of_dicts(document.get("sections"))}


def _section_path(section_id: str | None, sections_by_id: dict[str, dict[str, Any]]) -> list[str]:
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
        title = str(section.get("title") or "").strip()
        if title:
            path.append(title)
        parent_id = section.get("parent_id")
        current_id = parent_id if isinstance(parent_id, str) else None
    return list(reversed(path))


def _chunk_items(document: dict[str, Any]) -> list[dict[str, Any]]:
    sections_by_id = _sections_by_id(document)
    chunks = _list_of_dicts(document.get("chunks"))
    items: list[dict[str, Any]] = []
    for chunk in chunks:
        section_id = str(chunk.get("section_id") or "")
        section_path = chunk.get("section_path")
        if not isinstance(section_path, list) or not section_path:
            section_path = _section_path(section_id, sections_by_id)
        item = dict(chunk)
        item["section_path"] = section_path
        if not item.get("section_title") and section_path:
            item["section_title"] = section_path[-1]
        items.append(item)
    return items


def _issue(
    *,
    issue_type: str,
    severity: str,
    filename: str,
    chunk_id: str = "",
    section_path: list[Any] | None = None,
    text: str = "",
    text_preview_chars: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "severity": severity,
        "filename": filename,
        "chunk_id": chunk_id,
        "section_path": list(section_path or []),
        "text_preview": text_preview(text, text_preview_chars),
        "reason": reason,
    }


def validate_processed_document(document: dict[str, Any], *, text_preview_chars: int = 300) -> dict[str, Any]:
    metadata = _metadata(document)
    filename = _source_filename(document)
    chunks = _chunk_items(document)
    sections = _list_of_dicts(document.get("sections"))
    tables = _list_of_dicts(document.get("tables"))
    document_issues: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()

    for item in chunks:
        chunk_id = str(item.get("chunk_id") or "")
        section_path = list(item.get("section_path") or [])
        text = str(item.get("text") or "")
        if is_toc_parent_violation(section_path):
            counters["toc_parent_violations"] += 1
            document_issues.append(
                _issue(
                    issue_type="toc_parent_violation",
                    severity="warning",
                    filename=filename,
                    chunk_id=chunk_id,
                    section_path=section_path,
                    text=text,
                    text_preview_chars=text_preview_chars,
                    reason="TOC/service heading appears as parent for a non-TOC chunk/section.",
                )
            )
        if is_duplicate_heading_text(text):
            counters["duplicate_heading_violations"] += 1
            document_issues.append(
                _issue(
                    issue_type="duplicate_heading",
                    severity="warning",
                    filename=filename,
                    chunk_id=chunk_id,
                    section_path=section_path,
                    text=text,
                    text_preview_chars=text_preview_chars,
                    reason="First two non-empty text lines are normalized-identical.",
                )
            )
        if is_heading_only_chunk(item):
            counters["heading_only_chunks"] += 1
            document_issues.append(
                _issue(
                    issue_type="heading_only_chunk",
                    severity="info",
                    filename=filename,
                    chunk_id=chunk_id,
                    section_path=section_path,
                    text=text,
                    text_preview_chars=text_preview_chars,
                    reason="Short text chunk looks like a standalone heading without body context.",
                )
            )
        if is_service_table_suspect(item):
            counters["service_table_suspects"] += 1
            document_issues.append(
                _issue(
                    issue_type="service_table_suspect",
                    severity="warning",
                    filename=filename,
                    chunk_id=chunk_id,
                    section_path=section_path,
                    text=text,
                    text_preview_chars=text_preview_chars,
                    reason="Table-like chunk looks like approval/signature/service text and lacks rich row/header data.",
                )
            )
        if is_real_table_chunk(item):
            counters["real_table_chunks"] += 1
        if item.get("page_start") is None:
            counters["missing_page_expected_limitations"] += 1

    issue_counts = {
        "toc_parent_violations": counters.get("toc_parent_violations", 0),
        "duplicate_heading_violations": counters.get("duplicate_heading_violations", 0),
        "heading_only_chunks": counters.get("heading_only_chunks", 0),
        "service_table_suspects": counters.get("service_table_suspects", 0),
    }
    samples = document_issues[:5]
    return {
        "document_id": str(metadata.get("document_id") or ""),
        "filename": filename,
        "chunk_count": len(chunks),
        "section_count": len(sections),
        "table_count": len(tables),
        "issues": issue_counts,
        "samples": samples,
        "_summary_counts": {
            **issue_counts,
            "real_table_chunks": counters.get("real_table_chunks", 0),
            "missing_page_expected_limitations": counters.get("missing_page_expected_limitations", 0),
        },
        "_issues": document_issues,
    }


def build_validation_report_from_documents(
    documents: list[dict[str, Any]],
    *,
    documents_seen: int | None = None,
    text_preview_chars: int = 300,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    validated = [validate_processed_document(document, text_preview_chars=text_preview_chars) for document in documents]
    issues = [issue for document in validated for issue in document.pop("_issues")]
    summary_counts: Counter[str] = Counter()
    for document in validated:
        summary_counts.update(document.pop("_summary_counts"))

    summary = {
        "documents_seen": documents_seen if documents_seen is not None else len(documents),
        "documents_processed": len(documents),
        "documents_with_failures": sum(
            1
            for document in validated
            if document["issues"]["toc_parent_violations"]
            or document["issues"]["duplicate_heading_violations"]
            or document["issues"]["service_table_suspects"]
        ),
        "total_chunks": sum(document["chunk_count"] for document in validated),
        "toc_parent_violations": summary_counts.get("toc_parent_violations", 0),
        "duplicate_heading_violations": summary_counts.get("duplicate_heading_violations", 0),
        "heading_only_chunks": summary_counts.get("heading_only_chunks", 0),
        "service_table_suspects": summary_counts.get("service_table_suspects", 0),
        "real_table_chunks": summary_counts.get("real_table_chunks", 0),
        "missing_page_expected_limitations": summary_counts.get("missing_page_expected_limitations", 0),
    }
    return {
        "validation_version": VALIDATION_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "fresh-processing-temp-workspace",
        "summary": summary,
        "documents": validated,
        "issues": issues,
        "limitations": LIMITATIONS,
        "warnings": warnings or [],
    }


def build_validation_report_from_results_dir(
    results_dir: Path,
    *,
    max_documents: int | None = None,
    text_preview_chars: int = 300,
) -> dict[str, Any]:
    if max_documents is not None and max_documents < 0:
        raise ValueError("max_documents must be greater than or equal to 0")
    paths = list(iter_processed_json(results_dir))
    documents: list[dict[str, Any]] = []
    warnings: list[str] = []
    selected_paths = paths if max_documents is None else paths[:max_documents]
    for path in selected_paths:
        try:
            documents.append(read_json_document(path))
        except ValueError as exc:
            warnings.append(str(exc))
    return build_validation_report_from_documents(
        documents,
        documents_seen=len(selected_paths),
        text_preview_chars=text_preview_chars,
        warnings=warnings,
    )


def process_inputs_to_workspace(input_paths: list[Path], workspace_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    service = DocumentService(storage_root=workspace_dir)
    documents: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in input_paths:
        try:
            outcome = service.process_path_with_status(path)
        except Exception as exc:  # noqa: BLE001 - processing errors must be reportable, not hidden.
            warnings.append(f"{path}: {type(exc).__name__}: {exc}")
            continue
        result_path = Path(outcome.document.artifacts.result_json_path)
        documents.append(read_json_document(result_path))
    return documents, warnings


def build_fresh_validation_report(
    input_paths: list[Path],
    workspace_dir: Path,
    *,
    text_preview_chars: int = 300,
) -> dict[str, Any]:
    documents, warnings = process_inputs_to_workspace(input_paths, workspace_dir)
    report = build_validation_report_from_documents(
        documents,
        documents_seen=len(input_paths),
        text_preview_chars=text_preview_chars,
        warnings=warnings,
    )
    processing_issues = [
        _issue(
            issue_type="processing_error",
            severity="error",
            filename=warning,
            text_preview_chars=text_preview_chars,
            reason="Input document could not be processed in the temporary workspace.",
        )
        for warning in warnings
    ]
    report["issues"].extend(processing_issues)
    report["summary"]["documents_with_failures"] += len(processing_issues)
    report["workspace_dir"] = str(workspace_dir)
    return report


def write_validation_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def print_console_summary(report: dict[str, Any], output_path: Path | None = None) -> None:
    summary = report["summary"]
    print("Stage 33.2 splitter cleanup validation")
    print(f"validation_version={report['validation_version']}")
    print(
        "documents_seen={documents_seen} documents_processed={documents_processed} "
        "documents_with_failures={documents_with_failures} total_chunks={total_chunks}".format(**summary)
    )
    print(
        "toc_parent_violations={toc_parent_violations} "
        "duplicate_heading_violations={duplicate_heading_violations} "
        "heading_only_chunks={heading_only_chunks} "
        "service_table_suspects={service_table_suspects} "
        "real_table_chunks={real_table_chunks} "
        "missing_page_expected_limitations={missing_page_expected_limitations}".format(**summary)
    )
    print("limitations: deterministic validation only; no RAG/LLM/embeddings/vector DB/reranking/OCR/table analytics.")
    if output_path:
        print(f"json_report_path={output_path}")
