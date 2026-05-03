from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from app.evaluation.splitter_cleanup_validation import (
    build_fresh_validation_report,
    print_console_summary,
    write_validation_report,
)


SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx", ".rtf", ".txt", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"}


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def collect_input_paths(
    input_paths: list[str] | None,
    input_dir: str | None,
    *,
    max_documents: int | None,
) -> list[Path]:
    paths: list[Path] = []
    for raw_path in input_paths or []:
        path = Path(raw_path).resolve()
        if path.is_dir():
            paths.extend(_iter_supported_files(path))
        else:
            paths.append(path)
    if input_dir:
        paths.extend(_iter_supported_files(Path(input_dir).resolve()))
    unique_paths = list(dict.fromkeys(paths))
    if max_documents is not None:
        unique_paths = unique_paths[:max_documents]
    return unique_paths


def _iter_supported_files(path: Path) -> list[Path]:
    if not path.exists():
        raise ValueError(f"input dir not found: {path}")
    if not path.is_dir():
        raise ValueError(f"input path is not a directory: {path}")
    return sorted(item for item in path.iterdir() if item.is_file() and item.suffix.lower() in SUPPORTED_SUFFIXES)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fresh splitter cleanup validation on a temporary workspace")
    parser.add_argument("--input-path", action="append", help="Input file path; can be passed more than once")
    parser.add_argument("--input-dir", help="Input directory with supported documents")
    parser.add_argument("--workspace-dir", required=True, help="Temporary workspace root for fresh processing")
    parser.add_argument("--output-path", help="Optional path to save JSON validation report")
    parser.add_argument("--max-documents", type=non_negative_int, help="Limit collected input documents")
    parser.add_argument("--text-preview-chars", type=non_negative_int, default=300)
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 when hard warning/error counters are non-zero",
    )
    args = parser.parse_args(argv)

    try:
        paths = collect_input_paths(args.input_path, args.input_dir, max_documents=args.max_documents)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if not paths:
        raise SystemExit("At least one --input-path or supported file from --input-dir is required")

    report = build_fresh_validation_report(
        paths,
        Path(args.workspace_dir).resolve(),
        text_preview_chars=args.text_preview_chars,
    )

    output_path = Path(args.output_path).resolve() if args.output_path else None
    if output_path:
        write_validation_report(output_path, report)
    print_console_summary(report, output_path=output_path)

    summary = report["summary"]
    if args.fail_on_regression and (
        summary["toc_parent_violations"]
        or summary["duplicate_heading_violations"]
        or summary["service_table_suspects"]
        or any(issue["issue_type"] == "processing_error" for issue in report["issues"])
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
