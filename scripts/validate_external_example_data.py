from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from app.evaluation.rag_chunk_quality import (
    COMPACT_TAXONOMY_BUCKETS,
    build_quality_audit_report,
    write_quality_audit_report,
)
from scripts import audit_external_qa_dataset, evaluate_external_qa_workspace


REPORT_VERSION = "stage35_external_example_data_validation_v1"

DEFAULT_WORKSPACE_DIR = ".runtime_eval/stage35_external_workspace"
DEFAULT_DATASET_AUDIT_REPORT = ".runtime_eval/stage35_external_dataset_audit.json"
DEFAULT_WORKSPACE_REPORT = ".runtime_eval/stage35_external_workspace_eval.json"
DEFAULT_QA_REPORT = ".runtime_eval/stage35_external_qa_eval.json"
DEFAULT_CHUNK_QUALITY_REPORT = ".runtime_eval/stage35_external_chunk_quality.json"
DEFAULT_WORKFLOW_REPORT = ".runtime_eval/stage35_external_validation_summary.json"

RERUN_RECOMMENDATION = "rerun_with_ambiguous_policy_all_or_all_supported_scope_for_exploratory_chunk_validation"


def _resolve(path: str | Path) -> Path:
    return Path(path).resolve()


def _workspace_results_dir(workspace_dir: Path) -> Path:
    return workspace_dir / "results"


def run_validation(
    *,
    dataset_dir: Path,
    qa_path: Path,
    workspace_dir: Path = Path(DEFAULT_WORKSPACE_DIR),
    dataset_audit_report_path: Path = Path(DEFAULT_DATASET_AUDIT_REPORT),
    workspace_report_path: Path = Path(DEFAULT_WORKSPACE_REPORT),
    qa_report_path: Path = Path(DEFAULT_QA_REPORT),
    chunk_quality_report_path: Path = Path(DEFAULT_CHUNK_QUALITY_REPORT),
    workflow_report_path: Path = Path(DEFAULT_WORKFLOW_REPORT),
    process: bool = False,
    run_eval: bool = False,
    run_chunk_quality: bool = False,
    source_scope: str = "expected",
    ambiguous_policy: str = "skip",
    max_documents: int | None = None,
    max_questions: int | None = None,
    clean_workspace: bool = False,
    top_k: int = 5,
    skip_answer_overlap: bool = True,
    report_detail_level: str = "summary",
    encoding: str | None = None,
    delimiter: str | None = None,
    include_chunk_samples: bool = False,
    chunk_quality_sample_limit: int | None = None,
    chunk_quality_sample_buckets: set[str] | None = None,
) -> dict[str, Any]:
    dataset_dir = _resolve(dataset_dir)
    qa_path = _resolve(qa_path)
    workspace_dir = _resolve(workspace_dir)
    dataset_audit_report_path = _resolve(dataset_audit_report_path)
    workspace_report_path = _resolve(workspace_report_path)
    qa_report_path = _resolve(qa_report_path)
    chunk_quality_report_path = _resolve(chunk_quality_report_path)
    workflow_report_path = _resolve(workflow_report_path)
    evaluate_external_qa_workspace._reject_production_storage_path(
        dataset_audit_report_path,
        "dataset audit report path",
    )
    evaluate_external_qa_workspace._reject_production_storage_path(
        chunk_quality_report_path,
        "chunk quality report path",
    )
    evaluate_external_qa_workspace._reject_production_storage_path(
        workflow_report_path,
        "workflow report path",
    )

    audit_report = evaluate_external_qa_workspace._build_audit_report(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        max_examples=audit_external_qa_dataset.DEFAULT_MAX_EXAMPLES,
        encoding=encoding,
        delimiter=delimiter,
    )
    audit_report["stage35_report_version"] = REPORT_VERSION
    audit_report["json_report_path"] = str(dataset_audit_report_path)
    dataset_audit_report_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_audit_report_path.write_text(
        json.dumps(audit_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    workspace_manifest = evaluate_external_qa_workspace.run_workspace(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        dry_run=not (process or run_eval),
        process=process,
        run_eval=run_eval,
        source_scope=source_scope,
        ambiguous_policy=ambiguous_policy,
        max_documents=max_documents,
        qa_report_path=qa_report_path if run_eval else None,
        workspace_report_path=workspace_report_path,
        clean_workspace=clean_workspace,
        top_k=top_k,
        max_questions=max_questions,
        skip_answer_overlap=skip_answer_overlap,
        report_detail_level=report_detail_level,
        encoding=encoding,
        delimiter=delimiter,
    )
    workspace_manifest["stage35_report_version"] = REPORT_VERSION
    evaluate_external_qa_workspace.write_json(workspace_report_path, workspace_manifest)

    chunk_quality_report: dict[str, Any] | None = None
    warnings: list[str] = []
    recommendations: list[str] = []
    limitations: list[str] = [
        "Stage 35 validates and classifies external ETL/chunk handoff evidence only; it does not run cleanup.",
        "External dataset files are referenced by path only and are not copied into the repository.",
        "Strict expected-source mode can select zero documents when expected sources are ambiguous.",
    ]
    processed_document_count = int(workspace_manifest.get("processed_document_count") or 0)
    selected_document_count = int(workspace_manifest.get("selected_document_count") or 0)
    skipped_ambiguous_count = int(workspace_manifest.get("skipped_ambiguous_count") or 0)
    chunk_quality_status = "not_requested"
    if run_chunk_quality:
        results_dir = _workspace_results_dir(workspace_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        has_result_json = any(results_dir.glob("*.json"))
        if processed_document_count <= 0 or not has_result_json:
            chunk_quality_status = "skipped_no_processed_documents"
            warnings.append(
                "Chunk quality validation was requested, but the Stage 35 workspace has no processed documents."
            )
            recommendations.append(RERUN_RECOMMENDATION)
        else:
            chunk_quality_report = build_quality_audit_report(
                results_dir,
                max_documents=max_documents,
                include_samples=include_chunk_samples,
                sample_limit=chunk_quality_sample_limit,
                sample_buckets=chunk_quality_sample_buckets,
            )
            chunk_quality_report["stage35_report_version"] = REPORT_VERSION
            write_quality_audit_report(chunk_quality_report_path, chunk_quality_report)
            audited_chunks = int(chunk_quality_report["summary"]["audited_chunks"])
            if audited_chunks <= 0:
                chunk_quality_status = "needs_attention_no_processed_chunks"
                warnings.append(
                    "Chunk quality report was produced, but no chunks were audited from the Stage 35 workspace."
                )
                recommendations.append(RERUN_RECOMMENDATION)
            else:
                chunk_quality_status = "ok"

    qa_eval_status = None
    qa_report_path_value = workspace_manifest["reports"].get("qa_report_path")
    if qa_report_path_value:
        qa_report_file = Path(qa_report_path_value)
        if qa_report_file.exists():
            try:
                qa_eval_status = json.loads(qa_report_file.read_text(encoding="utf-8")).get("status")
            except (OSError, json.JSONDecodeError):
                qa_eval_status = "unreadable_report"
        else:
            qa_eval_status = "missing_report"

    workflow_status = "ok"
    if (
        audit_report["status"] != "ok"
        or workspace_manifest["status"] != "ok"
        or chunk_quality_status.startswith(("skipped_", "needs_attention"))
        or qa_eval_status in {"no_documents", "missing_report", "unreadable_report"}
    ):
        workflow_status = "needs_attention"

    summary = {
        "report_version": REPORT_VERSION,
        "workflow_version": REPORT_VERSION,
        "stage": "Stage 35 External Example_data validation v1",
        "status": workflow_status,
        "dataset_audit_report_path": str(dataset_audit_report_path),
        "workspace_report_path": str(workspace_report_path),
        "workflow_report_path": str(workflow_report_path),
        "qa_report_path": qa_report_path_value,
        "chunk_quality_report_path": str(chunk_quality_report_path) if chunk_quality_report else None,
        "dataset_audit_status": audit_report["status"],
        "workspace_status": workspace_manifest["status"],
        "processed_documents": processed_document_count,
        "selected_documents": selected_document_count,
        "skipped_ambiguous": skipped_ambiguous_count,
        "qa_eval_status": qa_eval_status,
        "chunk_quality_status": chunk_quality_status,
        "chunk_quality_audited_chunks": (
            chunk_quality_report["summary"]["audited_chunks"] if chunk_quality_report else None
        ),
        "generated_reports": {
            "dataset_audit": str(dataset_audit_report_path),
            "workspace": str(workspace_report_path),
            "qa_eval": qa_report_path_value,
            "chunk_quality": str(chunk_quality_report_path) if chunk_quality_report else None,
            "workflow": str(workflow_report_path),
        },
        "warnings": warnings,
        "recommendations": recommendations,
        "limitations": limitations,
        "notes": [
            "Stage 35 validation uses external dataset paths only; files are not copied into the repository.",
            "Processing, QA eval, and chunk quality reports are intended for .runtime_eval or another explicit temporary workspace.",
            "Production storage/index, storage/results, and storage/uploads are not intended targets.",
            "Stage 35 validates and classifies evidence only; it does not run cleanup.",
        ],
    }
    evaluate_external_qa_workspace.write_json(workflow_report_path, summary)
    return summary


def positive_int(value: str) -> int:
    return evaluate_external_qa_workspace.positive_int(value)


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


def print_summary(summary: dict[str, Any]) -> None:
    print("Stage 35 External Example_data validation")
    print(f"report_version={summary['report_version']}")
    print(f"status={summary['status']}")
    print(f"dataset_audit_status={summary['dataset_audit_status']}")
    print(f"workspace_status={summary['workspace_status']}")
    print(
        "selected={selected_documents} processed={processed_documents} skipped_ambiguous={skipped_ambiguous}".format(
            **summary,
        )
    )
    print(f"chunk_quality_status={summary['chunk_quality_status']}")
    print(f"dataset_audit_report_path={summary['dataset_audit_report_path']}")
    print(f"workspace_report_path={summary['workspace_report_path']}")
    print(f"workflow_report_path={summary['workflow_report_path']}")
    if summary.get("qa_report_path"):
        print(f"qa_report_path={summary['qa_report_path']}")
    if summary.get("chunk_quality_report_path"):
        print(f"chunk_quality_report_path={summary['chunk_quality_report_path']}")
        print(f"chunk_quality_audited_chunks={summary['chunk_quality_audited_chunks']}")
    if summary.get("warnings"):
        print("warnings:")
        for warning in summary["warnings"]:
            print(f"- {warning}")
    if summary.get("recommendations"):
        print("recommendations:")
        for recommendation in summary["recommendations"]:
            print(f"- {recommendation}")
    print("notes:")
    for note in summary["notes"]:
        print(f"- {note}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Stage 35 External Example_data validation workflow")
    parser.add_argument("--dataset-dir", required=True, help="External Example_data directory")
    parser.add_argument("--qa-path", required=True, help="External QA CSV/TSV file")
    parser.add_argument("--workspace-dir", default=DEFAULT_WORKSPACE_DIR)
    parser.add_argument("--dataset-audit-report-path", default=DEFAULT_DATASET_AUDIT_REPORT)
    parser.add_argument("--workspace-report-path", default=DEFAULT_WORKSPACE_REPORT)
    parser.add_argument("--qa-report-path", default=DEFAULT_QA_REPORT)
    parser.add_argument("--chunk-quality-report-path", default=DEFAULT_CHUNK_QUALITY_REPORT)
    parser.add_argument("--workflow-report-path", default=DEFAULT_WORKFLOW_REPORT)
    parser.add_argument("--process", action="store_true", help="Process selected external documents into workspace")
    parser.add_argument("--run-eval", action="store_true", help="Run QA/retrieval readiness eval on workspace results")
    parser.add_argument("--run-chunk-quality", action="store_true", help="Run Stage 34.3 chunk taxonomy over workspace results")
    parser.add_argument("--source-scope", choices=evaluate_external_qa_workspace.SOURCE_SCOPES, default="expected")
    parser.add_argument("--ambiguous-policy", choices=evaluate_external_qa_workspace.AMBIGUOUS_POLICIES, default="skip")
    parser.add_argument("--max-documents", type=positive_int)
    parser.add_argument("--max-questions", type=positive_int)
    parser.add_argument("--clean-workspace", action="store_true")
    parser.add_argument("--top-k", type=positive_int, default=5)
    parser.add_argument("--skip-answer-overlap", action="store_true", default=True)
    parser.add_argument("--include-answer-overlap", action="store_false", dest="skip_answer_overlap")
    parser.add_argument("--report-detail-level", choices=evaluate_external_qa_workspace.evaluate_qa_dataset.REPORT_DETAIL_LEVELS, default="summary")
    parser.add_argument("--encoding", help="Optional QA CSV/TSV encoding override")
    parser.add_argument("--delimiter", help="Optional QA CSV/TSV delimiter override: tab/tsv/t/\\t, semicolon, comma, pipe")
    parser.add_argument("--include-chunk-samples", action="store_true")
    parser.add_argument("--chunk-quality-include-samples", action="store_true")
    parser.add_argument("--chunk-quality-sample-limit", type=non_negative_int)
    parser.add_argument(
        "--chunk-quality-sample-buckets",
        type=sample_buckets,
        help="Comma-separated compact taxonomy buckets to sample, for example real_low_value_tail,other_compact_text",
    )
    args = parser.parse_args(argv)

    try:
        summary = run_validation(
            dataset_dir=Path(args.dataset_dir),
            qa_path=Path(args.qa_path),
            workspace_dir=Path(args.workspace_dir),
            dataset_audit_report_path=Path(args.dataset_audit_report_path),
            workspace_report_path=Path(args.workspace_report_path),
            qa_report_path=Path(args.qa_report_path),
            chunk_quality_report_path=Path(args.chunk_quality_report_path),
            workflow_report_path=Path(args.workflow_report_path),
            process=args.process,
            run_eval=args.run_eval,
            run_chunk_quality=args.run_chunk_quality,
            source_scope=args.source_scope,
            ambiguous_policy=args.ambiguous_policy,
            max_documents=args.max_documents,
            max_questions=args.max_questions,
            clean_workspace=args.clean_workspace,
            top_k=args.top_k,
            skip_answer_overlap=args.skip_answer_overlap,
            report_detail_level=args.report_detail_level,
            encoding=args.encoding,
            delimiter=args.delimiter,
            include_chunk_samples=args.include_chunk_samples or args.chunk_quality_include_samples,
            chunk_quality_sample_limit=args.chunk_quality_sample_limit,
            chunk_quality_sample_buckets=args.chunk_quality_sample_buckets,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print_summary(summary)


if __name__ == "__main__":
    main()
