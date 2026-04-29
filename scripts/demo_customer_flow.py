from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.search.index import CorpusSearchEngine
from app.search.store import CorpusIndex, SearchIndexStore
from app.services.document_service import DocumentService
from scripts.audit_corpus import build_audit_report


REPORT_VERSION = "stage17_customer_demo_smoke_v1"

SUPPORTED_FORMATS = ["pdf", "doc", "docx", "rtf", "txt", "xlsx", "xls"]
METADATA_ONLY_IMAGE_FORMATS = ["jpg", "jpeg", "png"]
UNSUPPORTED_IMAGE_LIKE_FORMATS = ["heic", "heif", "tiff", "tif", "bmp", "webp"]

DEFAULT_QUERIES = [
    "экология проект",
    "ПДВ",
    "выброс",
    "затраты на сырье",
]


def _empty_index() -> CorpusIndex:
    return CorpusIndex(
        version="1",
        updated_at="",
        document_count=0,
        chunk_count=0,
        avg_chunk_length=0.0,
        doc_frequencies={},
        entries=[],
    )


class ReadOnlySearchIndexStore(SearchIndexStore):
    def load(self) -> CorpusIndex:
        if not self.exists():
            return _empty_index()
        try:
            return CorpusIndex.model_validate(self.storage.read_json(self.storage.corpus_index_path))
        except Exception:
            return _empty_index()

    def rebuild(self) -> CorpusIndex:
        return self.load()


def _build_search_engine(storage) -> CorpusSearchEngine:
    engine = CorpusSearchEngine(storage)
    engine.index_store = ReadOnlySearchIndexStore(storage)
    return engine


def _load_json_file(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _build_corpus_snapshot(storage_dir: Path) -> dict:
    results_dir = storage_dir / "results"
    index_path = storage_dir / "index" / "corpus_index.json"
    manifest_path = storage_dir / "index" / "ingestion_manifest.json"

    audit_report = build_audit_report(storage_dir)
    index_payload = _load_json_file(index_path)
    manifest_payload = _load_json_file(manifest_path)
    index = CorpusIndex.model_validate(index_payload) if isinstance(index_payload, dict) else _empty_index()

    result_documents = []
    if results_dir.exists():
        for path in sorted(results_dir.glob("*.json")):
            payload = _load_json_file(path)
            if isinstance(payload, dict):
                result_documents.append(payload)

    table_documents = 0
    image_documents = 0
    warning_documents = 0
    for document in result_documents:
        metadata = document.get("metadata") or {}
        processing_info = document.get("processing_info") or {}
        if isinstance(metadata.get("table_count"), int) and metadata.get("table_count", 0) > 0:
            table_documents += 1
        if isinstance(metadata.get("image_count"), int) and metadata.get("image_count", 0) > 0:
            image_documents += 1
        if processing_info.get("warnings"):
            warning_documents += 1

    summary = audit_report["summary"]
    return {
        "storage_dir": str(storage_dir),
        "saved_results_documents": len(result_documents),
        "indexed_documents": index.document_count,
        "indexed_chunks": index.chunk_count,
        "documents_with_tables": table_documents,
        "documents_with_images": image_documents,
        "documents_with_warnings": warning_documents,
        "manifest_records": len((manifest_payload or {}).get("records", [])) if isinstance(manifest_payload, dict) else 0,
        "audit_summary": summary,
        "problem_documents": audit_report["problem_documents"],
    }


def _scenario_checks() -> list[dict]:
    return [
        {
            "id": "S1",
            "name": "Source-backed search",
            "status": "supported-now",
            "note": "Local lexical retrieval over saved chunks with explicit source snippets.",
        },
        {
            "id": "S2",
            "name": "Source-backed extractive QA readiness",
            "status": "supported-now",
            "note": "ask stays source-backed and extractive; no generation layer is added.",
        },
        {
            "id": "S3",
            "name": "Requirements extraction",
            "status": "supported-now",
            "note": "Search/snippet discovery only; generated requirements remain out of scope.",
        },
        {
            "id": "S4",
            "name": "Calculation inputs discovery with tables",
            "status": "supported-now",
            "note": "Spreadsheet row/value retrieval is lexical with row-level context, not analytics.",
        },
        {
            "id": "S5",
            "name": "Audit visibility",
            "status": "supported-now",
            "note": "Corpus audit surfaces problem documents, missing chunks, warnings, and index drift.",
        },
        {
            "id": "S6",
            "name": "OCR / image limitation",
            "status": "limited",
            "note": "jpg/jpeg/png are metadata-only; OCR is not implemented and HEIC/HEIF/TIFF/TIF/BMP/WEBP stay unsupported.",
        },
        {
            "id": "S7",
            "name": "Summarization / draft limitation",
            "status": "limited",
            "note": "No summarization or draft generation is implemented in this baseline.",
        },
    ]


def _query_hits(engine: CorpusSearchEngine, query: str, top_k: int = 3) -> dict:
    hits = engine.search(query, top_k=top_k)
    return {
        "query": query,
        "status": "hit" if hits else "no-hit",
        "hit_count": len(hits),
        "top_hits": [
            {
                "rank": rank,
                "document_id": hit.document_id,
                "filename": hit.filename,
                "chunk_id": hit.chunk_id,
                "section_id": hit.section_id,
                "section_title": hit.section_title,
                "score": hit.score,
                "snippet": hit.snippet,
            }
            for rank, hit in enumerate(hits, start=1)
        ],
    }


def build_demo_report(storage_dir: Path, refresh_index: bool = False, top_k: int = 3) -> dict:
    storage_dir = storage_dir.resolve()
    service = DocumentService()

    if refresh_index:
        service.rebuild_corpus_index()

    search_engine = _build_search_engine(service.storage)
    corpus_snapshot = _build_corpus_snapshot(storage_dir)
    queries = [_query_hits(search_engine, query, top_k=top_k) for query in DEFAULT_QUERIES]

    return {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "refresh-index" if refresh_index else "read-only",
        "storage_dir": str(storage_dir),
        "capabilities": {
            "supported_formats": SUPPORTED_FORMATS,
            "metadata_only_image_formats": METADATA_ONLY_IMAGE_FORMATS,
            "unsupported_image_like_formats": UNSUPPORTED_IMAGE_LIKE_FORMATS,
            "limits": [
                "OCR is not implemented.",
                "LLM generation is not implemented.",
                "summarization is not implemented.",
                "vector DB / semantic retrieval / full RAG are not implemented.",
            ],
        },
        "corpus": corpus_snapshot,
        "scenarios": _scenario_checks(),
        "queries": queries,
    }


def print_demo_report(report: dict) -> None:
    corpus = report["corpus"]
    capabilities = report["capabilities"]
    print(f"Customer demo smoke runner: {report['report_version']}")
    print(f"Mode: {report['mode']}")
    print(f"Storage: {report['storage_dir']}")
    print(
        "Corpus: saved_results={saved} indexed_documents={indexed} indexed_chunks={chunks} tables={tables} images={images}".format(
            saved=corpus["saved_results_documents"],
            indexed=corpus["indexed_documents"],
            chunks=corpus["indexed_chunks"],
            tables=corpus["documents_with_tables"],
            images=corpus["documents_with_images"],
        )
    )
    print(
        "Audit: problems={problems} warnings={warnings} missing_from_index={missing}".format(
            problems=len(corpus["problem_documents"]),
            warnings=corpus["audit_summary"]["warnings_documents"],
            missing=corpus["audit_summary"]["missing_from_index_documents"],
        )
    )
    print(
        "Capabilities: supported={supported} metadata_only_images={images} unsupported_image_like={unsupported}".format(
            supported=", ".join(capabilities["supported_formats"]),
            images=", ".join(capabilities["metadata_only_image_formats"]),
            unsupported=", ".join(capabilities["unsupported_image_like_formats"]),
        )
    )
    for scenario in report["scenarios"]:
        print(f"{scenario['id']} {scenario['name']}: {scenario['status']} - {scenario['note']}")
    print("Queries:")
    for item in report["queries"]:
        print(f"- {item['query']}: {item['status']} hits={item['hit_count']}")
        if item["top_hits"]:
            hit = item["top_hits"][0]
            print(f"  top file={hit['filename']} score={hit['score']}")
            print(f"  snippet={hit['snippet']}")
    print("Limits:")
    for item in capabilities["limits"]:
        print(f"- {item}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Customer demo / scenario smoke runner")
    parser.add_argument("--refresh-index", action="store_true", help="Rebuild storage/index before reporting")
    parser.add_argument("--json-report-path", help="Optional path to save the demo JSON report")
    parser.add_argument("--top-k", type=int, default=3, help="Number of hits to collect per demo query")
    args = parser.parse_args()

    storage_dir = get_settings().resolved_storage_dir
    report = build_demo_report(storage_dir=storage_dir, refresh_index=args.refresh_index, top_k=args.top_k)
    print_demo_report(report)

    if args.json_report_path:
        report_path = Path(args.json_report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved demo report to {report_path}")


if __name__ == "__main__":
    main()
