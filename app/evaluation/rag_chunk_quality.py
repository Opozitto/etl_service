from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evaluation.rag_chunk_export import build_export_report, normalize_text


AUDIT_VERSION = "stage34_3_chunk_quality_taxonomy_reporting_v1"

DEFAULT_SHORT_THRESHOLD = 120
DEFAULT_LONG_THRESHOLD = 3000
COMPACT_TEXT_THRESHOLD = 250
DEFAULT_SAMPLE_LIMIT_PER_ISSUE = 5

RAW_CONTENT_TYPES = ("text", "table", "table_row", "image")
COMPACT_TAXONOMY_BUCKETS = (
    "title_or_cover_fragment",
    "toc_or_list_fragment",
    "formula_or_calculation_micro_evidence",
    "pollutant_or_equipment_micro_evidence",
    "real_low_value_tail",
    "service_or_boilerplate",
    "other_compact_text",
)
TOC_LIST_RE = re.compile(r"(^|\s)(\d+(\.\d+){1,}\.?)\s+\S+|\.{3,}\s*\d+\s*$", re.IGNORECASE)
FORMULA_RE = re.compile(r"[=<>±×*/]|(\b\d+([.,]\d+)?\s*(мг/м3|мг/м³|т/год|г/с|кг/ч|м3/ч|м³/ч)\b)", re.IGNORECASE)
BODY_HEADING_RE = re.compile(r"^(\d+(\.\d+)*\.?|[IVXLC]+\.?)\s+\S+", re.IGNORECASE)
POLLUTANT_SYMBOL_RE = re.compile(r"\b(nox|so2|co)\b", re.IGNORECASE)
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
FORMULA_TERMS = (
    "расчет",
    "расчёт",
    "формула",
    "коэффициент",
    "удельн",
    "мг/м3",
    "мг/м³",
    "т/год",
    "г/с",
)
POLLUTANT_EQUIPMENT_TERMS = (
    "вещество",
    "загрязняющ",
    "источник",
    "выброс",
    "оборудование",
    "котел",
    "котёл",
    "труба",
    "пыль",
    "оксид",
    "диоксид",
    "азот",
    "сера",
)

ISSUE_DETAILS: dict[str, dict[str, str]] = {
    "empty_or_whitespace_text": {
        "severity": "blocker",
        "description": "Chunk text is empty or contains only whitespace.",
        "recommendation": "Stage 30 should keep empty chunks out of future handoff contracts or mark them explicitly.",
    },
    "short_chunk": {
        "severity": "warning",
        "description": "Chunk is short and may not carry enough local context for future source-backed handoff.",
        "recommendation": "Stage 30 should define minimum context expectations and neighbor/section context rules.",
    },
    "long_chunk": {
        "severity": "warning",
        "description": "Chunk is long and may be too broad for precise source-backed citation or future retrieval handoff.",
        "recommendation": "Stage 30 should define target chunk size bounds before any RAG layer is introduced.",
    },
    "missing_section": {
        "severity": "warning",
        "description": "Chunk has no resolvable section context.",
        "recommendation": "Stage 30 should harden section fields in the chunk contract.",
    },
    "missing_page": {
        "severity": "warning",
        "description": "Chunk has no page context from linked blocks.",
        "recommendation": "Stage 32 should harden source location and citation metadata.",
    },
    "table_like_text_without_rich_context": {
        "severity": "warning",
        "description": "Text looks table-like, but current chunk context is not rich enough for reliable table handoff.",
        "recommendation": "Stage 31 should improve table chunk context without adding table analytics.",
    },
    "unknown_content_type": {
        "severity": "warning",
        "description": "Chunk content type could not be classified from current metadata.",
        "recommendation": "Stage 30 should make content_type expectations explicit in the handoff contract.",
    },
    "heading_only_or_low_context": {
        "severity": "info",
        "description": "Chunk looks like a heading or very low-context text fragment.",
        "recommendation": "Stage 30 should decide whether such chunks need neighboring context.",
    },
    "duplicate_or_repeated_text": {
        "severity": "info",
        "description": "The same normalized chunk text appears more than once in the audited set.",
        "recommendation": "Stage 30 should keep duplicate visibility in diagnostics before changing chunking behavior.",
    },
    "image_or_ocr_limited": {
        "severity": "info",
        "description": "Chunk is linked to image/OCR-limited source context already visible in export quality flags.",
        "recommendation": "Keep this as a limitation signal; do not infer OCR text in this audit.",
    },
}


def _non_negative(value: int | None, name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{name} must be greater than or equal to 0")


def _positive_or_zero(value: int, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be greater than or equal to 0")


def _chunk_text(item: dict[str, Any]) -> str:
    return normalize_text(item.get("text") if "text" in item else item.get("text_preview"))


def _filename(item: dict[str, Any]) -> str:
    return str(item.get("filename") or item.get("source_filename") or "")


def _content_type(item: dict[str, Any]) -> str:
    return str(item.get("content_type") or "unknown")


def _normalize_for_match(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip().casefold()


def _has_table_row_index(item: dict[str, Any]) -> bool:
    return item.get("table_row_index") is not None


def _has_table_column_values(item: dict[str, Any]) -> bool:
    value = item.get("table_column_values")
    return bool(value) if isinstance(value, dict | list | tuple) else value is not None


def _has_any_table_context(item: dict[str, Any]) -> bool:
    return bool(item.get("table_id")) or _has_table_row_index(item) or _has_table_column_values(item)


def _is_service_or_boilerplate(item: dict[str, Any], text: str) -> bool:
    flags = set(item.get("quality_flags") or [])
    content_type = _content_type(item)
    normalized = _normalize_for_match(text)
    if content_type == "service_text" or "service_text" in flags or "service_or_boilerplate" in flags:
        return True
    if any(term in normalized for term in SERVICE_TERMS):
        return True
    return False


def _compact_text_bucket(item: dict[str, Any], *, compact_threshold: int = COMPACT_TEXT_THRESHOLD) -> str | None:
    if _content_type(item) != "text":
        return None
    text = _chunk_text(item)
    if not text or len(text) >= compact_threshold:
        return None

    normalized = _normalize_for_match(text)
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if _is_service_or_boilerplate(item, text):
        return "service_or_boilerplate"
    if "содержание" in normalized or "оглавление" in normalized or "table of contents" in normalized:
        return "toc_or_list_fragment"
    if TOC_LIST_RE.search(text) or sum(1 for line in lines if BODY_HEADING_RE.match(line)) >= 2:
        return "toc_or_list_fragment"
    if FORMULA_RE.search(normalized) or any(term in normalized for term in FORMULA_TERMS):
        return "formula_or_calculation_micro_evidence"
    if POLLUTANT_SYMBOL_RE.search(normalized) or any(term in normalized for term in POLLUTANT_EQUIPMENT_TERMS):
        return "pollutant_or_equipment_micro_evidence"
    if len(words) <= 8 and (text.isupper() or _normalize_for_match(item.get("section_title")) == normalized.strip(" .:;")):
        return "title_or_cover_fragment"
    if len(text) < DEFAULT_SHORT_THRESHOLD:
        return "real_low_value_tail"
    return "other_compact_text"


def _raw_content_type_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    raw_counts = Counter(_content_type(item) for item in items)
    result = {content_type: raw_counts.get(content_type, 0) for content_type in RAW_CONTENT_TYPES}
    unknown_count = raw_counts.get("unknown", 0)
    other_count = sum(count for content_type, count in raw_counts.items() if content_type not in RAW_CONTENT_TYPES and content_type != "unknown")
    if unknown_count:
        result["unknown"] = unknown_count
    if other_count:
        result["other"] = other_count
    return result


def _table_context_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "chunks_with_table_id": sum(1 for item in items if item.get("table_id")),
        "chunks_with_table_row_index": sum(1 for item in items if _has_table_row_index(item)),
        "chunks_with_table_column_values": sum(1 for item in items if _has_table_column_values(item)),
        "mixed_text_with_table_context": sum(
            1 for item in items if _content_type(item) == "text" and _has_any_table_context(item)
        ),
    }


def _strict_table_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    table_row_items = [item for item in items if _content_type(item) == "table_row"]
    return {
        "strict_table_row_chunks": len(table_row_items),
        "strict_table_row_chunks_with_column_values": sum(1 for item in table_row_items if _has_table_column_values(item)),
        "strict_table_row_chunks_with_rich_row_context": sum(1 for item in table_row_items if _has_rich_table_context(item)),
    }


def _short_text_thresholds(items: list[dict[str, Any]], *, severe_threshold: int) -> dict[str, Any]:
    severe_items = [
        item for item in items if _content_type(item) == "text" and _chunk_text(item) and len(_chunk_text(item)) < severe_threshold
    ]
    compact_items = [
        item
        for item in items
        if _content_type(item) == "text" and _chunk_text(item) and len(_chunk_text(item)) < COMPACT_TEXT_THRESHOLD
    ]

    def summarize(short_items: list[dict[str, Any]]) -> dict[str, int]:
        service = sum(1 for item in short_items if _is_service_or_boilerplate(item, _chunk_text(item)))
        return {"total": len(short_items), "service": service, "nonservice": len(short_items) - service}

    return {
        "severe_short_text": {
            "threshold_chars": severe_threshold,
            "description": "text chunks shorter than 120 chars by default; potential micro-fragments.",
            **summarize(severe_items),
        },
        "compact_text_evidence": {
            "threshold_chars": COMPACT_TEXT_THRESHOLD,
            "description": "text chunks shorter than 250 chars; compact evidence is not automatically a defect.",
            **summarize(compact_items),
        },
    }


def _compact_text_taxonomy(items: list[dict[str, Any]]) -> dict[str, Any]:
    bucket_counts = Counter()
    for item in items:
        bucket = _compact_text_bucket(item)
        if bucket:
            bucket_counts[bucket] += 1
    buckets = {bucket: bucket_counts.get(bucket, 0) for bucket in COMPACT_TAXONOMY_BUCKETS}
    return {
        "threshold_chars": COMPACT_TEXT_THRESHOLD,
        "buckets": buckets,
        "note": "Compact chunks can be useful formula, calculation, pollutant, equipment, TOC/list or title evidence; only repeated real_low_value_tail needs cleanup review.",
    }


def _quality_recommendations(short_metrics: dict[str, Any], taxonomy: dict[str, Any]) -> list[str]:
    buckets = taxonomy["buckets"]
    severe_nonservice = short_metrics["severe_short_text"]["nonservice"]
    recommendations: list[str] = []
    if buckets["real_low_value_tail"] == 0 and severe_nonservice <= 5:
        recommendations.append("no_action_needed")
    if buckets["real_low_value_tail"]:
        recommendations.append("inspect_examples")
        recommendations.append("targeted_splitter_cleanup_only_if_repeated")
    recommendations.append("do_not_merge_table_chunks_with_text_chunks")
    recommendations.append("keep_table_path_separate")
    recommendations.append("keep_audit_deterministic_read_only")
    return recommendations


def _is_heading_only_or_low_context(text: str, content_type: str, short_threshold: int) -> bool:
    if not text:
        return False
    words = text.split()
    if content_type == "heading":
        return True
    if len(text) <= short_threshold and len(words) <= 6:
        return True
    if len(words) <= 8 and text.rstrip().endswith(":"):
        return True
    return False


def _table_like_without_rich_context(item: dict[str, Any]) -> bool:
    flags = set(item.get("quality_flags") or [])
    if "table_like_text" not in flags:
        return False
    if _has_rich_table_context(item):
        return False
    return True


def _has_rich_table_context(item: dict[str, Any]) -> bool:
    content_type = _content_type(item)
    if content_type not in {"table", "table_row"}:
        return False
    if item.get("table_id"):
        return True
    if item.get("table_context"):
        return True
    if item.get("table_headers") and item.get("table_column_values"):
        return True
    return False


def _issue_codes_for_item(
    item: dict[str, Any],
    *,
    short_threshold: int,
    long_threshold: int,
    duplicate_texts: set[str],
) -> list[str]:
    flags = set(item.get("quality_flags") or [])
    text = _chunk_text(item)
    text_len = len(text)
    issues: list[str] = []

    if not text:
        issues.append("empty_or_whitespace_text")
    if text and text_len < short_threshold:
        issues.append("short_chunk")
    if text_len > long_threshold:
        issues.append("long_chunk")
    if "missing_section" in flags or not item.get("section_id"):
        issues.append("missing_section")
    if "missing_page" in flags or item.get("page_start") is None:
        issues.append("missing_page")
    if _table_like_without_rich_context(item):
        issues.append("table_like_text_without_rich_context")
    if "unknown_content_type" in flags or _content_type(item) == "unknown":
        issues.append("unknown_content_type")
    if _is_heading_only_or_low_context(text, _content_type(item), short_threshold):
        issues.append("heading_only_or_low_context")
    if text in duplicate_texts:
        issues.append("duplicate_or_repeated_text")
    if "image_or_ocr_limited" in flags:
        issues.append("image_or_ocr_limited")

    return [code for code in ISSUE_DETAILS if code in set(issues)]


def _sample_from_item(item: dict[str, Any], issue_code: str, text_preview_chars: int) -> dict[str, Any]:
    return {
        "issue_code": issue_code,
        "document_id": item.get("document_id") or "",
        "filename": _filename(item),
        "source_filename": item.get("source_filename") or item.get("filename") or "",
        "chunk_id": item.get("chunk_id") or "",
        "order": item.get("order"),
        "chunk_order": item.get("chunk_order") if item.get("chunk_order") is not None else item.get("order"),
        "content_type": _content_type(item),
        "section_id": item.get("section_id"),
        "section_title": item.get("section_title"),
        "section_path": list(item.get("section_path") or []),
        "page_start": item.get("page_start"),
        "page_end": item.get("page_end"),
        "source_block_ids": list(item.get("source_block_ids") or []),
        "table_id": item.get("table_id"),
        "table_row_index": item.get("table_row_index"),
        "location_label": item.get("location_label"),
        "citation_label": item.get("citation_label"),
        "text_preview": _chunk_text(item)[:text_preview_chars],
        "quality_flags": sorted(item.get("quality_flags") or []),
        "handoff_notes": list(item.get("handoff_notes") or []),
    }


def build_quality_audit_from_items(
    items: list[dict[str, Any]],
    *,
    documents_seen: int | None = None,
    documents_with_chunks: int | None = None,
    total_chunks: int | None = None,
    results_dir: Path | None = None,
    max_documents: int | None = None,
    max_chunks_per_document: int | None = None,
    text_preview_chars: int = 300,
    short_threshold: int = DEFAULT_SHORT_THRESHOLD,
    long_threshold: int = DEFAULT_LONG_THRESHOLD,
    sample_limit_per_issue: int = DEFAULT_SAMPLE_LIMIT_PER_ISSUE,
    include_samples: bool = False,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    _non_negative(max_documents, "max_documents")
    _non_negative(max_chunks_per_document, "max_chunks_per_document")
    _positive_or_zero(text_preview_chars, "text_preview_chars")
    _positive_or_zero(short_threshold, "short_threshold")
    _positive_or_zero(long_threshold, "long_threshold")
    _positive_or_zero(sample_limit_per_issue, "sample_limit_per_issue")
    if long_threshold < short_threshold:
        raise ValueError("long_threshold must be greater than or equal to short_threshold")

    normalized_texts = [_chunk_text(item) for item in items if _chunk_text(item)]
    text_counts = Counter(normalized_texts)
    duplicate_texts = {text for text, count in text_counts.items() if count > 1}
    text_lengths = [len(_chunk_text(item)) for item in items]

    issue_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    content_type_counts = Counter(_content_type(item) for item in items)
    document_map: dict[tuple[str, str], dict[str, Any]] = {}
    per_issue_samples: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in items:
        document_id = str(item.get("document_id") or "")
        filename = _filename(item)
        key = (document_id, filename)
        if key not in document_map:
            document_map[key] = {
                "document_id": document_id,
                "filename": filename,
                "chunk_count": 0,
                "issue_counts": Counter(),
                "severity_counts": Counter(),
                "sample_chunks": [],
            }
        document_record = document_map[key]
        document_record["chunk_count"] += 1

        item_issues = _issue_codes_for_item(
            item,
            short_threshold=short_threshold,
            long_threshold=long_threshold,
            duplicate_texts=duplicate_texts,
        )
        for issue_code in item_issues:
            severity = ISSUE_DETAILS[issue_code]["severity"]
            issue_counts[issue_code] += 1
            severity_counts[severity] += 1
            document_record["issue_counts"][issue_code] += 1
            document_record["severity_counts"][severity] += 1
            if include_samples and len(per_issue_samples[issue_code]) < sample_limit_per_issue:
                sample = _sample_from_item(item, issue_code, text_preview_chars)
                per_issue_samples[issue_code].append(sample)
                document_record["sample_chunks"].append(sample)

    documents: list[dict[str, Any]] = []
    for document in document_map.values():
        documents.append(
            {
                "document_id": document["document_id"],
                "filename": document["filename"],
                "chunk_count": document["chunk_count"],
                "issue_counts": dict(sorted(document["issue_counts"].items())),
                "severity_counts": dict(sorted(document["severity_counts"].items())),
                "sample_chunks": document["sample_chunks"][:sample_limit_per_issue] if include_samples else [],
            }
        )
    documents.sort(key=lambda value: (-sum(value["issue_counts"].values()), value["filename"], value["document_id"]))

    top_issue_documents = [
        {
            "document_id": document["document_id"],
            "filename": document["filename"],
            "issue_count": sum(document["issue_counts"].values()),
            "issue_counts": document["issue_counts"],
            "severity_counts": document["severity_counts"],
        }
        for document in documents
        if document["issue_counts"]
    ][:10]

    issues = [
        {
            "issue_code": issue_code,
            "severity": ISSUE_DETAILS[issue_code]["severity"],
            "count": issue_counts.get(issue_code, 0),
            "description": ISSUE_DETAILS[issue_code]["description"],
            "recommendation": ISSUE_DETAILS[issue_code]["recommendation"],
        }
        for issue_code in ISSUE_DETAILS
        if issue_counts.get(issue_code, 0)
    ]

    samples = [sample for issue_code in ISSUE_DETAILS for sample in per_issue_samples.get(issue_code, [])]
    raw_content_type_counts = _raw_content_type_counts(items)
    table_context_counts = _table_context_counts(items)
    strict_table_counts = _strict_table_counts(items)
    short_text_thresholds = _short_text_thresholds(items, severe_threshold=short_threshold)
    compact_text_taxonomy = _compact_text_taxonomy(items)
    summary = {
        "audit_version": AUDIT_VERSION,
        "documents_processed": documents_with_chunks if documents_with_chunks is not None else len(document_map),
        "documents_seen": documents_seen if documents_seen is not None else len(document_map),
        "documents_with_chunks": documents_with_chunks if documents_with_chunks is not None else len(document_map),
        "total_chunks": total_chunks if total_chunks is not None else len(items),
        "audited_chunks": len(items),
        "issue_counts": dict(sorted(issue_counts.items())),
        "severity_counts": dict(sorted(severity_counts.items())),
        "content_type_counts": dict(sorted(content_type_counts.items())),
        "raw_content_type_counts": raw_content_type_counts,
        "table_context_counts": table_context_counts,
        "strict_table_counts": strict_table_counts,
        "short_text_thresholds": short_text_thresholds,
        "compact_text_taxonomy": compact_text_taxonomy,
        "average_text_chars": round(sum(text_lengths) / len(text_lengths), 2) if text_lengths else 0,
        "median_text_chars": statistics.median(text_lengths) if text_lengths else 0,
        "min_text_chars": min(text_lengths) if text_lengths else 0,
        "max_text_chars": max(text_lengths) if text_lengths else 0,
        "chunks_missing_section": issue_counts.get("missing_section", 0),
        "chunks_missing_page": issue_counts.get("missing_page", 0),
        "short_chunk_count": issue_counts.get("short_chunk", 0),
        "long_chunk_count": issue_counts.get("long_chunk", 0),
        "table_like_chunk_count": sum(1 for item in items if "table_like_text" in set(item.get("quality_flags") or [])),
        "unknown_content_type_count": issue_counts.get("unknown_content_type", 0),
        "duplicate_text_count": issue_counts.get("duplicate_or_repeated_text", 0),
        "repeated_text_count": issue_counts.get("duplicate_or_repeated_text", 0),
        "documents_with_issues": sum(1 for document in documents if document["issue_counts"]),
        "top_issue_documents": top_issue_documents,
    }

    recommendations = _quality_recommendations(short_text_thresholds, compact_text_taxonomy)
    limitations = [
        "Audit reads existing processed JSON/export records only and does not fix chunking behavior.",
        "Heuristics are deterministic and conservative; they do not perform semantic or ML quality evaluation.",
        "No OCR, LLM generation, embeddings, vector DB, reranking or table analytics are performed.",
        "Raw content_type counts and broad table-linked counts answer different questions.",
        "content_type='text' with table context is not an ordinary text chunk.",
        "content_type='table_row' is the strict stable row-level table evidence count.",
        "Compact text chunks below 250 chars are evidence taxonomy candidates, not automatic defects.",
        "Real cleanup is needed only for repeated real_low_value_tail or other confirmed repeated problems.",
    ]
    if warnings:
        limitations.append("Some processed JSON files could not be read; see warnings.")

    return {
        "taxonomy_version": AUDIT_VERSION,
        "audit_version": AUDIT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "read-only",
        "results_dir": str(results_dir) if results_dir else None,
        "config": {
            "max_documents": max_documents,
            "max_chunks_per_document": max_chunks_per_document,
            "text_preview_chars": text_preview_chars,
            "short_threshold": short_threshold,
            "long_threshold": long_threshold,
            "sample_limit_per_issue": sample_limit_per_issue,
            "include_samples": include_samples,
        },
        "summary": summary,
        "documents_processed": summary["documents_processed"],
        "total_chunks": summary["total_chunks"],
        "raw_content_type_counts": raw_content_type_counts,
        "table_context_counts": table_context_counts,
        "strict_table_counts": strict_table_counts,
        "short_text_thresholds": short_text_thresholds,
        "compact_text_taxonomy": compact_text_taxonomy,
        "issues": issues,
        "issues_sample": samples,
        "documents": documents,
        "samples": samples,
        "recommendations": recommendations,
        "limitations": limitations,
        "warnings": warnings or [],
    }


def build_quality_audit_report(
    results_dir: Path,
    *,
    max_documents: int | None = None,
    max_chunks_per_document: int | None = None,
    text_preview_chars: int = 300,
    short_threshold: int = DEFAULT_SHORT_THRESHOLD,
    long_threshold: int = DEFAULT_LONG_THRESHOLD,
    sample_limit_per_issue: int = DEFAULT_SAMPLE_LIMIT_PER_ISSUE,
    include_samples: bool = False,
) -> dict[str, Any]:
    export_report = build_export_report(
        results_dir,
        max_documents=max_documents,
        max_chunks_per_document=max_chunks_per_document,
        include_text=True,
        text_preview_chars=text_preview_chars,
    )
    summary = export_report["summary"]
    return build_quality_audit_from_items(
        list(export_report["items"]),
        documents_seen=summary["documents_seen"],
        documents_with_chunks=summary["documents_with_chunks"],
        total_chunks=summary["total_chunks"],
        results_dir=results_dir,
        max_documents=max_documents,
        max_chunks_per_document=max_chunks_per_document,
        text_preview_chars=text_preview_chars,
        short_threshold=short_threshold,
        long_threshold=long_threshold,
        sample_limit_per_issue=sample_limit_per_issue,
        include_samples=include_samples,
        warnings=list(export_report.get("warnings") or []),
    )


def write_quality_audit_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def print_console_summary(report: dict[str, Any], output_path: Path | None = None) -> None:
    summary = report["summary"]
    print("Stage 34.3 chunk quality taxonomy audit")
    print(f"audit_version={report['audit_version']}")
    print(
        "documents_seen={documents_seen} documents_with_chunks={documents_with_chunks} "
        "total_chunks={total_chunks} audited_chunks={audited_chunks}".format(**summary)
    )
    print(f"issue_counts={summary['issue_counts']}")
    print(f"severity_counts={summary['severity_counts']}")
    print(f"raw_content_type_counts={summary['raw_content_type_counts']}")
    print(f"table_context_counts={summary['table_context_counts']}")
    print(f"strict_table_counts={summary['strict_table_counts']}")
    print(f"legacy_content_type_counts={summary['content_type_counts']}")
    severe = summary["short_text_thresholds"]["severe_short_text"]
    compact = summary["short_text_thresholds"]["compact_text_evidence"]
    print(
        "severe_short_text<{threshold_chars}: total={total} service={service} nonservice={nonservice}".format(
            **severe
        )
    )
    print(
        "compact_text_evidence<{threshold_chars}: total={total} service={service} nonservice={nonservice}".format(
            **compact
        )
    )
    print(f"compact_text_taxonomy={summary['compact_text_taxonomy']['buckets']}")
    print(
        "text_chars avg={average_text_chars} median={median_text_chars} "
        "min={min_text_chars} max={max_text_chars}".format(**summary)
    )
    print(f"documents_with_issues={summary['documents_with_issues']}")
    if summary["top_issue_documents"]:
        print("top_issue_documents:")
        for document in summary["top_issue_documents"][:5]:
            print(
                "- {filename} document_id={document_id} issue_count={issue_count} issues={issue_counts}".format(
                    **document
                )
            )
    print("recommendations:")
    for recommendation in report["recommendations"]:
        print(f"- {recommendation}")
    print("limitations:")
    print("- raw content_type counts and broad table-linked counts answer different questions.")
    print("- content_type='text' with table context is not an ordinary text chunk.")
    print("- content_type='table_row' is strict stable row-level table evidence.")
    print("- compact <250 chunks can be useful evidence; they are not automatic defects.")
    print("- read-only audit; no RAG/LLM/embeddings/vector DB/reranking/OCR/table analytics.")
    if output_path:
        print(f"json_report_path={output_path}")
