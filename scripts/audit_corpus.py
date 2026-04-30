from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings


REPORT_VERSION = "stage8_corpus_quality_audit_v1"
OCR_STANDALONE_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
OCR_IMAGE_REASON = "standalone_image"
OCR_PDF_REASON = "possible_scanned_pdf"


def load_json_file(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def normalize_list(value: object) -> list:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def detect_ocr_candidate(document: dict) -> tuple[bool, str | None, list[str]]:
    source = document.get("source") or {}
    processing_info = document.get("processing_info") or {}
    filename = source.get("filename") or ""
    extension = (source.get("extension") or Path(filename).suffix.lower()).lower()
    text_char_count = processing_info.get("text_char_count")
    text_block_count = processing_info.get("text_block_count")
    chunk_count = len(document.get("chunks") or [])

    ocr_candidate = processing_info.get("ocr_candidate")
    ocr_reason = processing_info.get("ocr_reason")

    if isinstance(ocr_candidate, bool) and ocr_candidate:
        reason = ocr_reason if isinstance(ocr_reason, str) and ocr_reason else None
        if not reason:
            reason = OCR_PDF_REASON if extension == ".pdf" else OCR_IMAGE_REASON
        return True, reason, [reason]

    if extension in OCR_STANDALONE_IMAGE_SUFFIXES:
        return True, OCR_IMAGE_REASON, [OCR_IMAGE_REASON]

    if extension == ".pdf":
        signals: list[str] = []
        if text_char_count in (None, 0) or not (isinstance(text_char_count, int) and text_char_count > 0):
            signals.append("no_text_extracted")
        if text_block_count in (None, 0) or not (isinstance(text_block_count, int) and text_block_count > 0):
            signals.append("no_text_blocks")
        if chunk_count == 0:
            signals.append("no_chunks")
        if signals and len(signals) >= 2:
            return True, OCR_PDF_REASON, signals

    return False, None, []


def iter_result_documents(results_dir: Path) -> list[dict]:
    documents: list[dict] = []
    for path in sorted(results_dir.glob("*.json")):
        payload = load_json_file(path)
        if isinstance(payload, dict):
            documents.append(payload)
    return documents


def load_index_data(index_path: Path) -> tuple[bool, dict | None]:
    payload = load_json_file(index_path)
    return payload is not None, payload


def load_manifest_data(manifest_path: Path) -> tuple[bool, dict | None]:
    payload = load_json_file(manifest_path)
    return payload is not None, payload


def build_problem_document(
    document: dict,
    manifest_record: dict | None,
    index_document_ids: set[str],
    low_text_char_count: int,
    min_chunks: int,
    min_blocks: int,
    min_sections: int,
    index_present: bool,
) -> tuple[dict, list[str]]:
    metadata = document.get("metadata") or {}
    source = document.get("source") or {}
    processing_info = document.get("processing_info") or {}
    warnings = normalize_list(processing_info.get("warnings"))

    document_id = metadata.get("document_id") or ""
    filename = source.get("filename") or ""
    extension = source.get("extension") or Path(filename).suffix.lower()
    extractor = processing_info.get("extractor") or ""
    status = (manifest_record or {}).get("status") or "unknown"

    text_char_count = processing_info.get("text_char_count")
    text_block_count = processing_info.get("text_block_count")
    section_count = as_int(metadata.get("section_count")) or 0
    block_count = as_int(metadata.get("block_count")) or 0
    table_count = as_int(metadata.get("table_count")) or 0
    image_count = as_int(metadata.get("image_count")) or 0
    chunk_count = len(document.get("chunks") or [])

    tags: list[str] = []
    if warnings:
        tags.append("warnings")
    if text_char_count is None or text_block_count is None:
        tags.append("null_text_metrics")
    if isinstance(text_char_count, int) and not isinstance(text_char_count, bool) and text_char_count < low_text_char_count:
        tags.append("low_text")
    if chunk_count < min_chunks:
        tags.append("no_chunks")
    if block_count < min_blocks:
        tags.append("no_blocks")
    if section_count < min_sections:
        tags.append("no_sections")
    if index_present and document_id and document_id not in index_document_ids:
        tags.append("missing_from_index")

    problem_document = {
        "document_id": document_id,
        "filename": filename,
        "extension": extension,
        "extractor": extractor,
        "status": status,
        "text_char_count": text_char_count,
        "text_block_count": text_block_count,
        "section_count": section_count,
        "block_count": block_count,
        "chunk_count": chunk_count,
        "table_count": table_count,
        "image_count": image_count,
        "warnings": warnings,
        "tags": tags,
    }
    return problem_document, tags


def build_audit_report(
    storage_dir: Path,
    low_text_char_count: int = 500,
    min_chunks: int = 1,
    min_blocks: int = 1,
    min_sections: int = 1,
) -> dict:
    results_dir = storage_dir / "results"
    index_dir = storage_dir / "index"
    index_path = index_dir / "corpus_index.json"
    manifest_path = index_dir / "ingestion_manifest.json"

    documents = iter_result_documents(results_dir)
    index_present, index_data = load_index_data(index_path)
    manifest_present, manifest_data = load_manifest_data(manifest_path)

    index_entries = (index_data or {}).get("entries") or []
    index_document_ids = {
        entry.get("document_id")
        for entry in index_entries
        if isinstance(entry, dict) and entry.get("document_id")
    }
    manifest_records = (manifest_data or {}).get("records") or []
    manifest_by_document_id = {
        record.get("document_id"): record
        for record in manifest_records
        if isinstance(record, dict) and record.get("document_id")
    }

    by_extension = Counter()
    by_extractor = Counter()
    by_status = Counter()
    problem_documents: list[dict] = []
    ocr_candidates: list[dict] = []

    warnings_documents = 0
    null_text_metric_documents = 0
    low_text_documents = 0
    no_chunk_documents = 0
    no_block_documents = 0
    no_section_documents = 0
    missing_from_index_documents = 0
    ocr_candidate_documents = 0

    for document in documents:
        metadata = document.get("metadata") or {}
        source = document.get("source") or {}
        processing_info = document.get("processing_info") or {}
        warnings = normalize_list(processing_info.get("warnings"))

        extension = source.get("extension") or Path(source.get("filename") or "").suffix.lower()
        extractor = processing_info.get("extractor") or "unknown"
        document_id = metadata.get("document_id") or ""
        status = (manifest_by_document_id.get(document_id) or {}).get("status") or "unknown"

        by_extension[extension] += 1
        by_extractor[extractor] += 1
        by_status[status] += 1

        text_char_count = processing_info.get("text_char_count")
        text_block_count = processing_info.get("text_block_count")
        section_count = as_int(metadata.get("section_count")) or 0
        block_count = as_int(metadata.get("block_count")) or 0
        chunk_count = len(document.get("chunks") or [])

        if warnings:
            warnings_documents += 1
        if text_char_count is None or text_block_count is None:
            null_text_metric_documents += 1
        if isinstance(text_char_count, int) and not isinstance(text_char_count, bool) and text_char_count < low_text_char_count:
            low_text_documents += 1
        if chunk_count < min_chunks:
            no_chunk_documents += 1
        if block_count < min_blocks:
            no_block_documents += 1
        if section_count < min_sections:
            no_section_documents += 1
        if index_present and document_id and document_id not in index_document_ids:
            missing_from_index_documents += 1

        is_ocr_candidate, ocr_reason, ocr_signals = detect_ocr_candidate(document)
        if is_ocr_candidate:
            ocr_candidate_documents += 1
            ocr_candidates.append(
                {
                    "document_id": document_id,
                    "filename": source.get("filename") or "",
                    "extension": extension,
                    "status": status,
                    "reason": ocr_reason,
                    "signals": ocr_signals,
                    "text_char_count": text_char_count,
                    "text_block_count": text_block_count,
                    "chunk_count": chunk_count,
                }
            )

        problem_document, tags = build_problem_document(
            document=document,
            manifest_record=manifest_by_document_id.get(document_id),
            index_document_ids=index_document_ids,
            low_text_char_count=low_text_char_count,
            min_chunks=min_chunks,
            min_blocks=min_blocks,
            min_sections=min_sections,
            index_present=index_present,
        )
        if tags:
            problem_documents.append(problem_document)

    indexed_documents = as_int((index_data or {}).get("document_count")) or 0
    indexed_chunks = as_int((index_data or {}).get("chunk_count")) or 0

    report = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "storage_dir": str(storage_dir),
        "inputs": {
            "results_count": len(documents),
            "index_present": index_present,
            "manifest_present": manifest_present,
        },
        "thresholds": {
            "low_text_char_count": low_text_char_count,
            "min_chunks": min_chunks,
            "min_blocks": min_blocks,
            "min_sections": min_sections,
        },
        "summary": {
            "total_documents": len(documents),
            "indexed_documents": indexed_documents,
            "indexed_chunks": indexed_chunks,
            "manifest_records": len(manifest_records),
            "by_extension": dict(by_extension),
            "by_extractor": dict(by_extractor),
            "by_status": dict(by_status),
            "warnings_documents": warnings_documents,
            "null_text_metric_documents": null_text_metric_documents,
            "low_text_documents": low_text_documents,
            "no_chunk_documents": no_chunk_documents,
            "no_block_documents": no_block_documents,
            "no_section_documents": no_section_documents,
            "missing_from_index_documents": missing_from_index_documents,
            "ocr_candidate_documents": ocr_candidate_documents,
        },
        "problem_documents": problem_documents,
        "ocr_candidates": ocr_candidates,
    }
    return report


def print_summary(report: dict) -> None:
    summary = report["summary"]
    print(
        "Corpus audit: documents={documents} indexed={indexed} chunks={chunks} problems={problems}".format(
            documents=summary["total_documents"],
            indexed=summary["indexed_documents"],
            chunks=summary["indexed_chunks"],
            problems=len(report["problem_documents"]),
        )
    )
    print(
        "Warnings={warnings} low_text={low_text} no_chunks={no_chunks} missing_from_index={missing}".format(
            warnings=summary["warnings_documents"],
            low_text=summary["low_text_documents"],
            no_chunks=summary["no_chunk_documents"],
            missing=summary["missing_from_index_documents"],
        )
    )
    print(f"OCR candidates={summary['ocr_candidate_documents']}")
    for candidate in report["ocr_candidates"]:
        signals = ", ".join(candidate["signals"]) if candidate["signals"] else "n/a"
        print(
            "  - {filename} ({reason}; signals={signals})".format(
                filename=candidate["filename"],
                reason=candidate["reason"],
                signals=signals,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only corpus quality audit")
    parser.add_argument("--report-path", help="Optional path to save the audit JSON report")
    parser.add_argument("--low-text-char-count", type=int, default=500)
    parser.add_argument("--min-chunks", type=int, default=1)
    parser.add_argument("--min-blocks", type=int, default=1)
    parser.add_argument("--min-sections", type=int, default=1)
    args = parser.parse_args()

    storage_dir = get_settings().resolved_storage_dir
    report = build_audit_report(
        storage_dir=storage_dir,
        low_text_char_count=args.low_text_char_count,
        min_chunks=args.min_chunks,
        min_blocks=args.min_blocks,
        min_sections=args.min_sections,
    )

    print_summary(report)

    if args.report_path:
        report_path = Path(args.report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved audit report to {report_path}")


if __name__ == "__main__":
    main()
