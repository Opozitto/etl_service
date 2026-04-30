from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from app.evaluation.rag_chunk_export import build_export_report, print_console_summary, write_export_report


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only RAG-ready chunk inspection/export")
    parser.add_argument("--results-dir", default="storage/results", help="Directory with processed StructuredDocument JSON")
    parser.add_argument("--output-path", help="Optional path to save JSON export report")
    parser.add_argument("--max-documents", type=non_negative_int, help="Limit number of processed JSON documents")
    parser.add_argument(
        "--max-chunks-per-document",
        type=non_negative_int,
        help="Limit exported chunks per document",
    )
    parser.add_argument("--include-text", action="store_true", help="Include full chunk text in JSON output")
    parser.add_argument("--text-preview-chars", type=non_negative_int, default=300)
    args = parser.parse_args(argv)

    try:
        report = build_export_report(
            Path(args.results_dir).resolve(),
            max_documents=args.max_documents,
            max_chunks_per_document=args.max_chunks_per_document,
            include_text=args.include_text,
            text_preview_chars=args.text_preview_chars,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output_path = Path(args.output_path).resolve() if args.output_path else None
    if output_path:
        write_export_report(output_path, report)
    print_console_summary(report, output_path=output_path)


if __name__ == "__main__":
    main()
