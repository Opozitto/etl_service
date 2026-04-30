from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from app.core.config import get_settings
from app.services.document_service import DocumentService
from scripts import audit_external_qa_dataset as audit
from scripts import evaluate_qa_dataset


REPORT_VERSION = "stage27_external_qa_workspace_v1"
SOURCE_SCOPES = ("expected", "all-supported")
AMBIGUOUS_POLICIES = ("skip", "all")
DEFAULT_WORKSPACE_DIR = ".runtime_eval/external_qa_workspace"
DEFAULT_MAX_EXAMPLES = 10
DEFAULT_QA_ENCODING = "utf-8-sig"
REAL_RUSSIAN_COLUMNS = {
    "question_column": "Вопрос",
    "answer_column": "Ответ",
    "document_column": "Документ",
}


@dataclass(frozen=True)
class SelectedDocument:
    relative_path: str
    filename: str
    extension: str
    size_bytes: int
    reason: str
    expected_document: str | None = None
    match_method: str | None = None


def _record_to_selected(
    record: audit.FileRecord,
    *,
    reason: str,
    expected_document: str | None = None,
    match_method: str | None = None,
) -> SelectedDocument:
    return SelectedDocument(
        relative_path=record.relative_path,
        filename=record.filename,
        extension=record.extension,
        size_bytes=record.size_bytes,
        reason=reason,
        expected_document=expected_document,
        match_method=match_method,
    )


def _selected_to_json(document: SelectedDocument) -> dict[str, Any]:
    return {
        "relative_path": document.relative_path,
        "filename": document.filename,
        "extension": document.extension,
        "size_bytes": document.size_bytes,
        "reason": document.reason,
        "expected_document": document.expected_document,
        "match_method": document.match_method,
    }


def _safe_workspace_dir(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.anchor == str(resolved):
        raise ValueError(f"workspace dir is not safe: {resolved}")
    production_storage = get_settings().resolved_storage_dir.resolve()
    if resolved == production_storage or production_storage in resolved.parents:
        raise ValueError(f"workspace dir must not be inside production storage: {resolved}")
    return resolved


def _reject_production_storage_path(path: Path, label: str) -> None:
    resolved = path.resolve()
    production_storage = get_settings().resolved_storage_dir.resolve()
    if resolved == production_storage or production_storage in resolved.parents:
        raise ValueError(f"{label} must not be inside production storage: {resolved}")


def _prepare_workspace(workspace_dir: Path, clean_workspace: bool) -> dict[str, Path]:
    workspace_dir = _safe_workspace_dir(workspace_dir)
    if clean_workspace and workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    paths = {
        "workspace": workspace_dir,
        "uploads": workspace_dir / "uploads",
        "results": workspace_dir / "results",
        "index": workspace_dir / "index",
        "reports": workspace_dir / "reports",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def _dedupe_selected(documents: Sequence[SelectedDocument]) -> list[SelectedDocument]:
    seen: set[str] = set()
    deduped: list[SelectedDocument] = []
    for document in documents:
        if document.relative_path in seen:
            continue
        seen.add(document.relative_path)
        deduped.append(document)
    return deduped


def _audit_kwargs(encoding: str | None, delimiter: str | None) -> dict[str, Any]:
    return {
        "encoding": encoding or DEFAULT_QA_ENCODING,
        "delimiter": delimiter,
    }


def _build_audit_report(
    *,
    dataset_dir: Path,
    qa_path: Path,
    max_examples: int,
    encoding: str | None,
    delimiter: str | None,
) -> dict[str, Any]:
    kwargs = _audit_kwargs(encoding, delimiter)
    try:
        return audit.build_audit_report(
            dataset_dir=dataset_dir,
            qa_path=qa_path,
            max_examples=max_examples,
            **kwargs,
        )
    except ValueError as exc:
        if "Cannot detect" not in str(exc):
            raise
        return audit.build_audit_report(
            dataset_dir=dataset_dir,
            qa_path=qa_path,
            max_examples=max_examples,
            **kwargs,
            **REAL_RUSSIAN_COLUMNS,
        )


def _load_qa_rows(qa_path: Path, encoding: str | None, delimiter: str | None):
    kwargs = _audit_kwargs(encoding, delimiter)
    try:
        return audit.load_qa_rows(qa_path, **kwargs)
    except ValueError as exc:
        if "Cannot detect" not in str(exc):
            raise
        return audit.load_qa_rows(qa_path, **kwargs, **REAL_RUSSIAN_COLUMNS)


def _build_qa_eval_report(
    *,
    qa_path: Path,
    results_dir: Path,
    top_k: int,
    max_questions: int | None,
    encoding: str | None,
    delimiter: str | None,
    skip_answer_overlap: bool,
    report_detail_level: str,
) -> dict[str, Any]:
    try:
        return evaluate_qa_dataset.build_report(
            qa_path=qa_path,
            results_dir=results_dir,
            top_k=top_k,
            max_questions=max_questions,
            encoding=encoding,
            delimiter=delimiter,
            skip_answer_overlap=skip_answer_overlap,
            report_detail_level=report_detail_level,
        )
    except ValueError as exc:
        if "Cannot detect" not in str(exc):
            raise
        return evaluate_qa_dataset.build_report(
            qa_path=qa_path,
            results_dir=results_dir,
            top_k=top_k,
            max_questions=max_questions,
            encoding=encoding,
            delimiter=delimiter,
            skip_answer_overlap=skip_answer_overlap,
            report_detail_level=report_detail_level,
            **REAL_RUSSIAN_COLUMNS,
        )


def build_workspace_plan(
    *,
    dataset_dir: Path,
    qa_path: Path,
    source_scope: str = "expected",
    ambiguous_policy: str = "skip",
    max_documents: int | None = None,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> dict[str, Any]:
    if source_scope not in SOURCE_SCOPES:
        raise ValueError(f"Unsupported source scope: {source_scope}")
    if ambiguous_policy not in AMBIGUOUS_POLICIES:
        raise ValueError(f"Unsupported ambiguous policy: {ambiguous_policy}")
    if max_documents is not None and max_documents < 1:
        raise ValueError("max_documents must be greater than 0")

    audit_report = _build_audit_report(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        max_examples=max_examples,
        encoding=encoding,
        delimiter=delimiter,
    )
    records = audit.inventory_files(dataset_dir)

    selected: list[SelectedDocument] = []
    skipped_examples: list[dict[str, Any]] = []
    unsupported_selected_count = 0

    if source_scope == "all-supported":
        selected = [
            _record_to_selected(record, reason="all_supported")
            for record in records
            if record.supported
        ]
    else:
        qa_rows, _ = _load_qa_rows(qa_path, encoding=encoding, delimiter=delimiter)
        expected_docs = sorted(
            {
                audit.normalize_text(row.document)
                for row in qa_rows
                if row.document and not audit.is_no_source_placeholder(row.document)
            }
        )
        indexes = audit.build_match_indexes(records)
        for expected_doc in expected_docs:
            match = audit.match_expected_document(expected_doc, records, indexes)
            match_records: list[audit.FileRecord] = match["matches"]
            supported_matches = [record for record in match_records if record.supported]
            if match["status"] == "matched":
                if supported_matches:
                    selected.append(
                        _record_to_selected(
                            supported_matches[0],
                            reason="expected_matched",
                            expected_document=expected_doc,
                            match_method=match["method"],
                        )
                    )
                else:
                    unsupported_selected_count += len(match_records)
                    skipped_examples.append(
                        {
                            "document": expected_doc,
                            "reason": "unsupported_matched",
                            "method": match["method"],
                            "matches": [audit.record_example(record) for record in match_records[:max_examples]],
                        }
                    )
                continue
            if match["status"] == "ambiguous":
                if ambiguous_policy == "all":
                    for record in supported_matches:
                        selected.append(
                            _record_to_selected(
                                record,
                                reason="expected_ambiguous_all",
                                expected_document=expected_doc,
                                match_method=match["method"],
                            )
                        )
                    unsupported_selected_count += len(match_records) - len(supported_matches)
                    if not supported_matches:
                        skipped_examples.append(
                            {
                                "document": expected_doc,
                                "reason": "ambiguous_no_supported_matches",
                                "method": match["method"],
                                "matches": [audit.record_example(record) for record in match_records[:max_examples]],
                            }
                        )
                else:
                    skipped_examples.append(
                        {
                            "document": expected_doc,
                            "reason": "ambiguous_skipped",
                            "method": match["method"],
                            "matches": [audit.record_example(record) for record in match_records[:max_examples]],
                        }
                    )
                continue
            skipped_examples.append(
                {
                    "document": expected_doc,
                    "reason": "missing",
                    "method": match["method"],
                    "matches": [],
                }
            )

    selected = _dedupe_selected(selected)
    selected_before_limit = len(selected)
    if max_documents is not None:
        selected = selected[:max_documents]

    return {
        "audit_report": audit_report,
        "selected_documents": selected,
        "selected_before_limit": selected_before_limit,
        "skipped_examples": skipped_examples,
        "unsupported_selected_count": unsupported_selected_count,
    }


def process_documents(dataset_dir: Path, workspace_paths: dict[str, Path], documents: Sequence[SelectedDocument]) -> dict[str, Any]:
    service = DocumentService(storage_root=workspace_paths["workspace"])
    processed = 0
    duplicates = 0
    errors: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for document in documents:
        source_path = dataset_dir / document.relative_path
        try:
            outcome = service.process_path_with_status(source_path)
        except Exception as exc:
            errors.append({"relative_path": document.relative_path, "error": str(exc)})
            continue
        processed += 1 if outcome.status == "processed" else 0
        duplicates += 1 if outcome.status == "duplicate" else 0
        items.append(
            {
                "relative_path": document.relative_path,
                "status": outcome.status,
                "document_id": outcome.document.metadata.document_id,
                "result_json_path": outcome.document.artifacts.result_json_path,
            }
        )
    return {
        "processed_document_count": processed,
        "duplicate_document_count": duplicates,
        "error_count": len(errors),
        "items": items,
        "errors": errors,
    }


def build_manifest(
    *,
    dataset_dir: Path,
    qa_path: Path,
    workspace_dir: Path,
    source_scope: str,
    ambiguous_policy: str,
    dry_run: bool,
    plan: dict[str, Any],
    process_report: dict[str, Any] | None = None,
    qa_report_path: Path | None = None,
    audit_report_path: Path | None = None,
    notes: Sequence[str] = (),
) -> dict[str, Any]:
    selected_documents: list[SelectedDocument] = plan["selected_documents"]
    skipped_examples: list[dict[str, Any]] = plan["skipped_examples"]
    process_report = process_report or {}
    status = "ok"
    manifest_notes = [
        "Temporary workspace workflow only: no production storage writes are intended.",
        "No LLM, RAG generation, embeddings/vector DB, OCR strategy changes, or search ranking changes.",
    ]
    manifest_notes.extend(notes)
    if skipped_examples or process_report.get("error_count"):
        status = "needs_attention"
    return {
        "report_version": REPORT_VERSION,
        "status": status,
        "dataset_dir": str(dataset_dir),
        "qa_path": str(qa_path),
        "workspace_dir": str(workspace_dir),
        "source_scope": source_scope,
        "ambiguous_policy": ambiguous_policy,
        "dry_run": dry_run,
        "selected_document_count": len(selected_documents),
        "selected_before_limit": plan["selected_before_limit"],
        "processed_document_count": process_report.get("processed_document_count", 0),
        "duplicate_document_count": process_report.get("duplicate_document_count", 0),
        "processing_error_count": process_report.get("error_count", 0),
        "skipped_ambiguous_count": sum(1 for item in skipped_examples if item.get("reason") == "ambiguous_skipped"),
        "unsupported_selected_count": plan["unsupported_selected_count"],
        "selected_documents": [_selected_to_json(document) for document in selected_documents],
        "processed_documents": process_report.get("items", []),
        "processing_errors": process_report.get("errors", []),
        "skipped_examples": skipped_examples,
        "audit_summary": {
            "status": plan["audit_report"]["status"],
            "qa": plan["audit_report"]["qa"],
            "files": plan["audit_report"]["files"],
            "expected_sources": plan["audit_report"]["expected_sources"],
        },
        "reports": {
            "qa_report_path": str(qa_report_path) if qa_report_path else None,
            "audit_report_path": str(audit_report_path) if audit_report_path else None,
        },
        "notes": manifest_notes,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_workspace(
    *,
    dataset_dir: Path,
    qa_path: Path,
    workspace_dir: Path,
    dry_run: bool,
    process: bool,
    run_eval: bool,
    source_scope: str,
    ambiguous_policy: str,
    max_documents: int | None,
    qa_report_path: Path | None,
    workspace_report_path: Path | None,
    clean_workspace: bool,
    top_k: int,
    max_questions: int | None,
    skip_answer_overlap: bool,
    report_detail_level: str,
    encoding: str | None = None,
    delimiter: str | None = None,
) -> dict[str, Any]:
    dataset_dir = dataset_dir.resolve()
    qa_path = qa_path.resolve()
    workspace_dir = _safe_workspace_dir(workspace_dir)
    safe_dry_run = dry_run or not process and not run_eval
    plan = build_workspace_plan(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        source_scope=source_scope,
        ambiguous_policy=ambiguous_policy,
        max_documents=max_documents,
        encoding=encoding,
        delimiter=delimiter,
    )

    workspace_paths: dict[str, Path] | None = None
    process_report: dict[str, Any] | None = None
    qa_report_output: Path | None = None
    notes: list[str] = []

    if process or run_eval:
        workspace_paths = _prepare_workspace(workspace_dir, clean_workspace)

    if process:
        process_report = process_documents(
            dataset_dir,
            workspace_paths or _prepare_workspace(workspace_dir, False),
            plan["selected_documents"],
        )

    if run_eval:
        workspace_paths = workspace_paths or _prepare_workspace(workspace_dir, False)
        qa_report_output = qa_report_path.resolve() if qa_report_path else workspace_paths["reports"] / "qa_eval_report.json"
        _reject_production_storage_path(qa_report_output, "qa report path")
        results_dir = workspace_paths["results"]
        if not list(results_dir.glob("*.json")):
            notes.append("QA eval requested, but workspace results are empty; evaluator returned no_documents.")
        qa_report = _build_qa_eval_report(
            qa_path=qa_path,
            results_dir=results_dir,
            top_k=top_k,
            max_questions=max_questions,
            encoding=encoding,
            delimiter=delimiter,
            skip_answer_overlap=skip_answer_overlap,
            report_detail_level=report_detail_level,
        )
        write_json(qa_report_output, qa_report)

    manifest = build_manifest(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        source_scope=source_scope,
        ambiguous_policy=ambiguous_policy,
        dry_run=safe_dry_run,
        plan=plan,
        process_report=process_report,
        qa_report_path=qa_report_output,
        notes=notes,
    )
    if notes:
        manifest["status"] = "needs_attention"

    if process or run_eval:
        workspace_paths = workspace_paths or _prepare_workspace(workspace_dir, False)
        manifest_path = workspace_report_path.resolve() if workspace_report_path else workspace_paths["workspace"] / "workspace_manifest.json"
        _reject_production_storage_path(manifest_path, "workspace report path")
        write_json(manifest_path, manifest)
        manifest["workspace_manifest_path"] = str(manifest_path)
        write_json(manifest_path, manifest)
    elif workspace_report_path:
        report_path = workspace_report_path.resolve()
        _reject_production_storage_path(report_path, "workspace report path")
        write_json(report_path, manifest)
        manifest["workspace_manifest_path"] = str(report_path)
        write_json(report_path, manifest)

    return manifest


def print_manifest_summary(manifest: dict[str, Any]) -> None:
    print("Stage 27 external QA temporary workspace workflow")
    print(f"status={manifest['status']}")
    print(f"dataset_dir={manifest['dataset_dir']}")
    print(f"qa_path={manifest['qa_path']}")
    print(f"workspace_dir={manifest['workspace_dir']}")
    print(f"dry_run={str(manifest['dry_run']).lower()}")
    print(
        "selected={selected_document_count} processed={processed_document_count} duplicates={duplicate_document_count} "
        "skipped_ambiguous={skipped_ambiguous_count} processing_errors={processing_error_count}".format(**manifest)
    )
    if manifest.get("workspace_manifest_path"):
        print(f"workspace_manifest_path={manifest['workspace_manifest_path']}")
    qa_report_path = manifest["reports"].get("qa_report_path")
    if qa_report_path:
        print(f"qa_report_path={qa_report_path}")
    if manifest["status"] != "ok":
        print("Diagnostic: workspace processing/eval needs attention before using results.")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="External QA temporary workspace processing/eval")
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--qa-path", required=True)
    parser.add_argument("--workspace-dir", default=DEFAULT_WORKSPACE_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--process", action="store_true")
    parser.add_argument("--run-eval", action="store_true")
    parser.add_argument("--source-scope", choices=SOURCE_SCOPES, default="expected")
    parser.add_argument("--ambiguous-policy", choices=AMBIGUOUS_POLICIES, default="skip")
    parser.add_argument("--max-documents", type=positive_int)
    parser.add_argument("--qa-report-path")
    parser.add_argument("--workspace-report-path")
    parser.add_argument("--encoding", help="Optional QA CSV/TSV encoding override")
    parser.add_argument("--delimiter", help="Optional QA CSV/TSV delimiter override: tab/tsv/t/\\t, semicolon, comma, pipe")
    parser.add_argument("--clean-workspace", action="store_true")
    parser.add_argument("--top-k", type=positive_int, default=5)
    parser.add_argument("--max-questions", type=positive_int)
    parser.add_argument("--skip-answer-overlap", action="store_true")
    parser.add_argument("--report-detail-level", choices=evaluate_qa_dataset.REPORT_DETAIL_LEVELS, default="summary")
    args = parser.parse_args(argv)

    try:
        manifest = run_workspace(
            dataset_dir=Path(args.dataset_dir),
            qa_path=Path(args.qa_path),
            workspace_dir=Path(args.workspace_dir),
            dry_run=args.dry_run,
            process=args.process,
            run_eval=args.run_eval,
            source_scope=args.source_scope,
            ambiguous_policy=args.ambiguous_policy,
            max_documents=args.max_documents,
            qa_report_path=Path(args.qa_report_path) if args.qa_report_path else None,
            workspace_report_path=Path(args.workspace_report_path) if args.workspace_report_path else None,
            clean_workspace=args.clean_workspace,
            top_k=args.top_k,
            max_questions=args.max_questions,
            skip_answer_overlap=args.skip_answer_overlap,
            report_detail_level=args.report_detail_level,
            encoding=args.encoding,
            delimiter=args.delimiter,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print_manifest_summary(manifest)


if __name__ == "__main__":
    main()
