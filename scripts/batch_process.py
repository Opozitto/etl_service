from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.document_service import DocumentService


def iter_supported_files(root: Path) -> list[Path]:
    supported = {".pdf", ".doc", ".docx", ".rtf", ".txt", ".xlsx", ".png", ".jpg", ".jpeg"}
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in supported)


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
        "input_dir": str(input_dir),
        "processed": 0,
        "duplicates": 0,
        "errors": 0,
        "items": [],
    }

    for path in files:
        try:
            outcome = service.process_path_with_status(path)
            report["items"].append(
                {
                    "file": str(path),
                    "status": outcome.status,
                    "document_id": outcome.document.metadata.document_id,
                    "title": outcome.document.metadata.title,
                    "warnings": outcome.document.processing_info.warnings,
                    "source_encoding": outcome.document.processing_info.source_encoding,
                }
            )
            if outcome.status == "duplicate":
                report["duplicates"] += 1
                print(f"Duplicate {path.name} -> {outcome.document.metadata.document_id}")
            else:
                report["processed"] += 1
                print(f"Processed {path.name} -> {outcome.document.metadata.document_id}")
        except Exception as exc:
            report["errors"] += 1
            report["items"].append({"file": str(path), "status": "error", "error": str(exc)})
            print(f"Error {path.name}: {exc}")

    if args.report_path:
        report_path = Path(args.report_path).resolve()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved report to {report_path}")

    print(f"Summary: processed={report['processed']} duplicates={report['duplicates']} errors={report['errors']}")



if __name__ == "__main__":
    main()
