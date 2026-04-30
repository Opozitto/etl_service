from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from app.evaluation.qa_failure_taxonomy import (
    build_report_from_paths,
    print_console_summary,
    write_diagnostic_report,
)


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be greater than or equal to 0")
    return parsed


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only QA failure taxonomy diagnostics")
    parser.add_argument("--qa-report-path", required=True, help="Path to Stage 24/25 QA eval JSON report")
    parser.add_argument("--external-audit-report-path", help="Optional path to Stage 26 audit JSON report")
    parser.add_argument("--workspace-report-path", help="Optional path to Stage 27 workspace manifest JSON report")
    parser.add_argument("--output-path", help="Optional path to save Stage 28 JSON diagnostics")
    parser.add_argument("--answer-overlap-threshold", type=non_negative_float, default=0.15)
    parser.add_argument("--failures-limit", type=non_negative_int, default=50)
    args = parser.parse_args(argv)

    try:
        report = build_report_from_paths(
            qa_report_path=Path(args.qa_report_path).resolve(),
            external_audit_report_path=Path(args.external_audit_report_path).resolve()
            if args.external_audit_report_path
            else None,
            workspace_report_path=Path(args.workspace_report_path).resolve()
            if args.workspace_report_path
            else None,
            answer_overlap_threshold=args.answer_overlap_threshold,
            failures_limit=args.failures_limit,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output_path = Path(args.output_path).resolve() if args.output_path else None
    if output_path:
        write_diagnostic_report(output_path, report)
    print_console_summary(report, output_path=output_path)


if __name__ == "__main__":
    main()
