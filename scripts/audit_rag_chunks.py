from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from app.evaluation.rag_chunk_quality import (
    COMPACT_TAXONOMY_BUCKETS,
    DEFAULT_LONG_THRESHOLD,
    DEFAULT_SAMPLE_LIMIT_PER_ISSUE,
    DEFAULT_SHORT_THRESHOLD,
    build_quality_audit_report,
    print_console_summary,
    write_quality_audit_report,
)


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def sample_buckets(value: str) -> set[str]:
    buckets = {bucket.strip() for bucket in value.split(",") if bucket.strip()}
    unknown = sorted(buckets.difference(COMPACT_TAXONOMY_BUCKETS))
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown compact taxonomy buckets: {', '.join(unknown)}")
    return buckets


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only RAG chunk quality audit")
    parser.add_argument("--results-dir", default="storage/results", help="Directory with processed StructuredDocument JSON")
    parser.add_argument("--output-path", help="Optional path to save JSON audit report")
    parser.add_argument("--json-report-path", help="Alias for --output-path")
    parser.add_argument("--max-documents", type=non_negative_int, help="Limit number of processed JSON documents")
    parser.add_argument(
        "--max-chunks-per-document",
        type=non_negative_int,
        help="Limit audited chunks per document",
    )
    parser.add_argument("--text-preview-chars", type=non_negative_int, default=300)
    parser.add_argument("--short-threshold", type=non_negative_int, default=DEFAULT_SHORT_THRESHOLD)
    parser.add_argument("--long-threshold", type=non_negative_int, default=DEFAULT_LONG_THRESHOLD)
    parser.add_argument("--sample-limit-per-issue", type=non_negative_int, default=DEFAULT_SAMPLE_LIMIT_PER_ISSUE)
    parser.add_argument("--include-samples", action="store_true", help="Include bounded sample chunks in JSON report")
    parser.add_argument("--sample-limit", type=non_negative_int, help="Limit samples per compact taxonomy bucket")
    parser.add_argument(
        "--sample-buckets",
        type=sample_buckets,
        help="Comma-separated compact taxonomy buckets to sample, for example real_low_value_tail,other_compact_text",
    )
    args = parser.parse_args(argv)

    try:
        report = build_quality_audit_report(
            Path(args.results_dir).resolve(),
            max_documents=args.max_documents,
            max_chunks_per_document=args.max_chunks_per_document,
            text_preview_chars=args.text_preview_chars,
            short_threshold=args.short_threshold,
            long_threshold=args.long_threshold,
            sample_limit_per_issue=args.sample_limit_per_issue,
            include_samples=args.include_samples,
            sample_limit=args.sample_limit,
            sample_buckets=args.sample_buckets,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    selected_output_path = args.output_path or args.json_report_path
    output_path = Path(selected_output_path).resolve() if selected_output_path else None
    if output_path:
        write_quality_audit_report(output_path, report)
    print_console_summary(report, output_path=output_path)


if __name__ == "__main__":
    main()
