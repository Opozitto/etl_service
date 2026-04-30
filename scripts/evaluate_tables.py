from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.extraction.tables import (
    SCOPE_NOTE,
    build_table_evidence_report,
    load_documents_from_results,
)


def print_report(report: dict, top_k: int = 10) -> None:
    summary = report["summary"]
    print("Stage 23 table-aware evidence evaluation")
    print(SCOPE_NOTE[0].lower() + SCOPE_NOTE[1:])
    print(f"Results dir: {report['results_dir']}")
    print(f"documents_seen={summary['documents_seen']}")
    print(f"documents_with_tables={summary['documents_with_tables']}")
    print(f"tables_seen={summary['tables_seen']}")
    print(f"candidate_tables={summary['candidate_tables']}")

    categories = summary.get("categories") or {}
    if categories:
        print("Category breakdown: " + ", ".join(f"{category}={count}" for category, count in sorted(categories.items())))
    else:
        print("Category breakdown: none")

    tables = report.get("tables") or []
    if not tables:
        print("Top table candidates: none")
        return

    print("Top table candidates:")
    for index, table in enumerate(tables[:top_k], start=1):
        headers = ", ".join(table.get("headers") or []) or "n/a"
        tags = ", ".join(table.get("tags") or []) or table.get("category") or "unknown"
        print(
            "{rank}. {filename} [{tags}] score={score} rows={rows} cols={cols} section={section}".format(
                rank=index,
                filename=table.get("filename") or "",
                tags=tags,
                score=table.get("score"),
                rows=table.get("row_count"),
                cols=table.get("column_count"),
                section=table.get("section_title") or table.get("section_id") or "unknown",
            )
        )
        print(f"   headers: {headers}")
        print(f"   preview: {table.get('snippet') or ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only table-aware evidence evaluation")
    parser.add_argument("--results-dir", help="Directory with processed StructuredDocument JSON files")
    parser.add_argument("--json-report-path", help="Optional path to save the JSON report")
    parser.add_argument("--min-score", type=float, default=0.25, help="Minimum table candidate score")
    parser.add_argument("--max-tables", type=int, help="Limit table candidates")
    parser.add_argument("--category", help="Optional category/tag filter")
    parser.add_argument("--top-k", type=int, default=10, help="Number of table candidates to print")
    args = parser.parse_args()

    settings = get_settings()
    results_dir = Path(args.results_dir).resolve() if args.results_dir else settings.resolved_storage_dir / "results"
    documents = load_documents_from_results(results_dir)
    report = build_table_evidence_report(
        documents=documents,
        results_dir=results_dir,
        min_score=args.min_score,
        max_tables=args.max_tables,
        category=args.category,
    )
    print_report(report, top_k=args.top_k)

    if args.json_report_path:
        report_path = Path(args.json_report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved table evidence report to {report_path}")


if __name__ == "__main__":
    main()
