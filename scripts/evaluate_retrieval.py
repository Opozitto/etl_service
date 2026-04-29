from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.core.config import get_settings
from app.schemas.api import SearchHit
from app.search.index import CorpusSearchEngine
from app.search.store import CorpusIndex


REPORT_VERSION = "stage9_retrieval_quality_eval_v1"


@dataclass(frozen=True)
class QuerySpec:
    id: str
    query: str
    expected_files: list[str]
    expected_document_ids: list[str]
    must_have_results: bool


class ReadOnlyIndexStore:
    def __init__(self, index: CorpusIndex) -> None:
        self._index = index

    def load(self) -> CorpusIndex:
        return self._index


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify_query_id(query: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", query.lower())
    slug = slug.strip("_")
    return slug or "query"


def _normalize_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str) and item:
                result.append(item)
        return result
    if isinstance(value, str) and value:
        return [value]
    return []


def _parse_query_spec(raw: object, fallback_index: int) -> QuerySpec:
    if not isinstance(raw, dict):
        raise ValueError("Each query entry must be an object")

    query = raw.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Each query entry must include a non-empty 'query'")

    query_id = raw.get("id")
    if isinstance(query_id, str) and query_id.strip():
        resolved_id = query_id.strip()
    else:
        resolved_id = _slugify_query_id(query) or f"query_{fallback_index}"

    must_have_results = raw.get("must_have_results", True)
    if not isinstance(must_have_results, bool):
        must_have_results = bool(must_have_results)

    return QuerySpec(
        id=resolved_id,
        query=query,
        expected_files=_normalize_str_list(raw.get("expected_files")),
        expected_document_ids=_normalize_str_list(raw.get("expected_document_ids")),
        must_have_results=must_have_results,
    )


def load_queries(queries_path: Path | None) -> list[QuerySpec]:
    if queries_path is None:
        return [
            QuerySpec(
                id="ecology_project",
                query="экология проект",
                expected_files=[],
                expected_document_ids=[],
                must_have_results=True,
            )
        ]

    payload = _read_json(queries_path)
    if not isinstance(payload, list):
        raise ValueError("Queries file must contain a JSON list")
    return [_parse_query_spec(item, index) for index, item in enumerate(payload, start=1)]


def load_corpus_index(storage_dir: Path) -> CorpusIndex:
    index_path = storage_dir / "index" / "corpus_index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"corpus index not found: {index_path}")

    try:
        payload = _read_json(index_path)
        return CorpusIndex.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - we need a clear CLI error here
        raise ValueError(f"invalid corpus index: {index_path}") from exc


def build_search_engine(index: CorpusIndex) -> CorpusSearchEngine:
    engine = CorpusSearchEngine.__new__(CorpusSearchEngine)
    engine.index_store = ReadOnlyIndexStore(index)  # type: ignore[assignment]
    return engine


def evaluate_queries(engine: CorpusSearchEngine, queries: Sequence[QuerySpec], top_k: int) -> dict:
    results: list[dict] = []
    summary = {
        "queries_count": len(queries),
        "passed": 0,
        "failed": 0,
        "queries_with_results": 0,
        "queries_without_results": 0,
        "expected_hit_queries": 0,
        "expected_hit_passed": 0,
    }

    for query_spec in queries:
        hits = engine.search(query_spec.query, top_k=top_k)
        result_count = len(hits)
        if result_count > 0:
            summary["queries_with_results"] += 1
        else:
            summary["queries_without_results"] += 1

        failure_reasons: list[str] = []
        if query_spec.must_have_results and result_count == 0:
            failure_reasons.append("no_results")

        expected_hit_found = False
        best_expected_rank: int | None = None
        has_expectations = bool(query_spec.expected_files or query_spec.expected_document_ids)
        if has_expectations:
            summary["expected_hit_queries"] += 1
            expected_files = {item.lower() for item in query_spec.expected_files}
            expected_document_ids = set(query_spec.expected_document_ids)
            for rank, hit in enumerate(hits, start=1):
                if hit.filename.lower() in expected_files or hit.document_id in expected_document_ids:
                    expected_hit_found = True
                    best_expected_rank = rank
                    break
            if expected_hit_found:
                summary["expected_hit_passed"] += 1
            else:
                failure_reasons.append("expected_hit_not_found")

        passed = not failure_reasons
        if passed:
            summary["passed"] += 1
        else:
            summary["failed"] += 1

        results.append(
            {
                "id": query_spec.id,
                "query": query_spec.query,
                "passed": passed,
                "failure_reasons": failure_reasons,
                "result_count": result_count,
                "expected_files": query_spec.expected_files,
                "expected_document_ids": query_spec.expected_document_ids,
                "expected_hit_found": expected_hit_found,
                "best_expected_rank": best_expected_rank,
                "top_hits": [_format_hit(hit, rank) for rank, hit in enumerate(hits, start=1)],
            }
        )

    return {"summary": summary, "results": results}


def _format_hit(hit: SearchHit, rank: int) -> dict:
    return {
        "rank": rank,
        "score": hit.score,
        "document_id": hit.document_id,
        "filename": hit.filename,
        "chunk_id": hit.chunk_id,
        "section_title": hit.section_title,
        "title": hit.title,
        "snippet": hit.snippet,
    }


def build_report(storage_dir: Path, top_k: int, queries: Sequence[QuerySpec]) -> dict:
    index = load_corpus_index(storage_dir)
    engine = build_search_engine(index)
    evaluation = evaluate_queries(engine, queries, top_k=top_k)
    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "storage_dir": str(storage_dir),
        "index": {
            "present": True,
            "document_count": index.document_count,
            "chunk_count": index.chunk_count,
        },
        "config": {
            "top_k": top_k,
            "queries_count": len(queries),
        },
        "summary": evaluation["summary"],
        "results": evaluation["results"],
    }


def print_summary(report: dict) -> None:
    summary = report["summary"]
    top_k = report["config"]["top_k"]
    print(
        "Retrieval eval: queries={queries} passed={passed} failed={failed} top_k={top_k}".format(
            queries=summary["queries_count"],
            passed=summary["passed"],
            failed=summary["failed"],
            top_k=top_k,
        )
    )
    print(
        "Results: with_hits={with_hits} without_hits={without_hits} expected_hit_passed={passed}/{total}".format(
            with_hits=summary["queries_with_results"],
            without_hits=summary["queries_without_results"],
            passed=summary["expected_hit_passed"],
            total=summary["expected_hit_queries"],
        )
    )
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        if result["passed"]:
            print(
                f"[{status}] {result['id']} results={result['result_count']} best_expected_rank={result['best_expected_rank']}"
            )
        else:
            reasons = ",".join(result["failure_reasons"]) or "unknown"
            print(f"[{status}] {result['id']} reasons={reasons}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only retrieval quality mini-evaluation")
    parser.add_argument("--queries-path", help="Optional JSON list of retrieval queries")
    parser.add_argument("--top-k", type=int, default=5, help="Number of hits to evaluate")
    parser.add_argument("--report-path", help="Optional path to save the retrieval eval JSON report")
    args = parser.parse_args(argv)

    storage_dir = get_settings().resolved_storage_dir
    queries_path = Path(args.queries_path).resolve() if args.queries_path else None
    queries = load_queries(queries_path)

    try:
        report = build_report(storage_dir=storage_dir, top_k=args.top_k, queries=queries)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print_summary(report)

    if args.report_path:
        report_path = Path(args.report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved retrieval eval report to {report_path}")


if __name__ == "__main__":
    main()
