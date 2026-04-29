from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.services.document_service import DocumentService


def iter_supported_files(root: Path) -> list[Path]:
    supported = {".pdf", ".doc", ".docx", ".rtf", ".txt", ".xlsx", ".png", ".jpg", ".jpeg"}
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in supported)


def build_report_item(path: Path, outcome) -> dict:
    document = outcome.document
    return {
        "file": str(path),
        "status": outcome.status,
        "extension": document.source.extension,
        "size_bytes": document.source.size_bytes,
        "document_id": document.metadata.document_id,
        "title": document.metadata.title,
        "page_count": document.metadata.page_count,
        "section_count": document.metadata.section_count,
        "block_count": document.metadata.block_count,
        "table_count": document.metadata.table_count,
        "image_count": document.metadata.image_count,
        "chunk_count": len(document.chunks),
        "text_char_count": document.processing_info.text_char_count,
        "text_block_count": document.processing_info.text_block_count,
        "warnings": document.processing_info.warnings,
        "source_encoding": document.processing_info.source_encoding,
    }


def build_error_item(path: Path, exc: Exception) -> dict:
    return {
        "file": str(path),
        "status": "error",
        "extension": path.suffix.lower(),
        "warnings": [],
        "error": str(exc),
    }


def build_summary(items: list[dict]) -> dict:
    by_status = Counter(item["status"] for item in items)
    by_extension = Counter(
        item.get("extension") or Path(item["file"]).suffix.lower() for item in items if item.get("file")
    )

    totals = {
        "size_bytes": 0,
        "page_count": 0,
        "section_count": 0,
        "block_count": 0,
        "table_count": 0,
        "image_count": 0,
        "chunk_count": 0,
        "text_char_count": 0,
        "text_block_count": 0,
    }
    for item in items:
        for key in totals:
            value = item.get(key)
            if isinstance(value, int):
                totals[key] += value

    problem_files = []
    for item in items:
        warnings = item.get("warnings") or []
        if item["status"] != "error" and not warnings:
            continue
        problem_file = {
            "file": item["file"],
            "status": item["status"],
        }
        if item.get("error"):
            problem_file["error"] = item["error"]
        if warnings:
            problem_file["warnings"] = warnings
        problem_files.append(problem_file)

    return {
        "total_files": len(items),
        "processed": by_status.get("processed", 0),
        "duplicates": by_status.get("duplicate", 0),
        "errors": by_status.get("error", 0),
        "by_status": dict(by_status),
        "by_extension": dict(by_extension),
        "totals": totals,
        "problem_files": problem_files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch process a directory of documents")
    parser.add_argument("--input-dir", required=True, help="Directory with source documents")
    parser.add_argument("--report-path", help="Optional path to save JSON batch report")
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    service = DocumentService()
    files = iter_supported_files(input_dir)
    if not files:
        print(f"No supported files found in {input_dir}")
        return

    report = {
        "report_version": "stage7_batch_report_v1",
        "input_dir": str(input_dir),
        "processed": 0,
        "duplicates": 0,
        "errors": 0,
        "items": [],
    }

    for path in files:
        try:
            outcome = service.process_path_with_status(path)
            item = build_report_item(path, outcome)
            report["items"].append(item)
            if outcome.status == "duplicate":
                report["duplicates"] += 1
                print(f"Duplicate {path.name} -> {outcome.document.metadata.document_id}")
            else:
                report["processed"] += 1
                print(f"Processed {path.name} -> {outcome.document.metadata.document_id}")
        except Exception as exc:
            report["errors"] += 1
            report["items"].append(build_error_item(path, exc))
            print(f"Error {path.name}: {exc}")

    report["summary"] = build_summary(report["items"])

    if args.report_path:
        report_path = Path(args.report_path).resolve()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved report to {report_path}")

    print(f"Summary: processed={report['processed']} duplicates={report['duplicates']} errors={report['errors']}")



if __name__ == "__main__":
    main()
