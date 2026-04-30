from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.extraction.requirements import build_requirements_report, load_documents_from_results


DISCLAIMER = (
    "Note: deterministic source-backed candidate extraction only; "
    "not a legal/compliance guarantee, no generation."
)


def print_report(report: dict, top_k: int = 10) -> None:
    summary = report["summary"]
    print("Stage 22 requirements extraction v1")
    print(DISCLAIMER)
    print(f"Results dir: {report['results_dir']}")
    print(
        "Documents seen={documents_seen} documents_with_candidates={documents_with_candidates} candidates={total_candidates}".format(
            **summary
        )
    )
    categories = summary.get("categories") or {}
    if categories:
        print("Categories: " + ", ".join(f"{category}={count}" for category, count in sorted(categories.items())))
    else:
        print("Categories: none")

    candidates = report.get("candidates") or []
    if not candidates:
        print("Top candidates: none")
        return

    print("Top candidates:")
    for index, candidate in enumerate(candidates[:top_k], start=1):
        location = (
            candidate.get("section_title")
            or candidate.get("section_id")
            or candidate.get("source_type")
            or "unknown"
        )
        print(
            "{rank}. {filename} [{category}] score={score} source={source_type}/{location}".format(
                rank=index,
                filename=candidate.get("filename") or "",
                category=candidate.get("category") or "unknown",
                score=candidate.get("score"),
                source_type=candidate.get("source_type") or "unknown",
                location=location,
            )
        )
        print(f"   {candidate.get('snippet') or ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only source-backed requirements extraction v1")
    parser.add_argument("--results-dir", help="Directory with processed StructuredDocument JSON files")
    parser.add_argument("--json-report-path", help="Optional path to save the JSON report")
    parser.add_argument("--min-score", type=float, default=0.45, help="Minimum candidate score")
    parser.add_argument("--min-confidence", type=float, dest="min_confidence", help="Alias for --min-score")
    parser.add_argument("--max-per-document", type=int, help="Limit candidates per document")
    parser.add_argument("--query", help="Optional substring filter over extracted text/category/source")
    parser.add_argument("--top-k", type=int, default=10, help="Number of candidates to print")
    args = parser.parse_args()

    settings = get_settings()
    results_dir = Path(args.results_dir).resolve() if args.results_dir else settings.resolved_storage_dir / "results"
    min_score = args.min_confidence if args.min_confidence is not None else args.min_score
    documents = load_documents_from_results(results_dir)
    report = build_requirements_report(
        documents=documents,
        results_dir=results_dir,
        min_score=min_score,
        max_per_document=args.max_per_document,
        query=args.query,
    )
    print_report(report, top_k=args.top_k)

    if args.json_report_path:
        report_path = Path(args.json_report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved requirements report to {report_path}")


if __name__ == "__main__":
    main()
