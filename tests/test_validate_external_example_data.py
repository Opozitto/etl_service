from __future__ import annotations

import importlib
import json
from pathlib import Path

from app.core.config import get_settings


def _load_module():
    module = importlib.import_module("scripts.validate_external_example_data")
    return importlib.reload(module)


def _write_tsv(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    lines = ["№ п/п\tВопрос\tОтвет\tДокумент"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines), encoding="utf-8")


def _prepare_dataset(tmp_path: Path) -> tuple[Path, Path]:
    dataset_dir = tmp_path / "Example_data"
    dataset_dir.mkdir()
    qa_path = dataset_dir / "test_with_answers.csv"
    _write_tsv(qa_path, [("1", "Что указано в report?", "alpha", "report.txt")])
    (dataset_dir / "report.txt").write_text(
        "alpha beta gamma. Достаточный текст для синтетической Stage 35 проверки.",
        encoding="utf-8",
    )
    return dataset_dir, qa_path


def _prepare_ambiguous_dataset(tmp_path: Path) -> tuple[Path, Path]:
    dataset_dir = tmp_path / "Example_data"
    (dataset_dir / "a").mkdir(parents=True)
    (dataset_dir / "b").mkdir(parents=True)
    qa_path = dataset_dir / "test_with_answers.csv"
    _write_tsv(qa_path, [("1", "Что указано в report?", "alpha", "report.txt")])
    (dataset_dir / "a" / "report.txt").write_text("alpha", encoding="utf-8")
    (dataset_dir / "b" / "report.txt").write_text("beta", encoding="utf-8")
    return dataset_dir, qa_path


def test_stage35_dry_run_writes_audit_and_workspace_reports_without_processing(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)

    summary = module.run_validation(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=tmp_path / ".runtime_eval" / "stage35_workspace",
        dataset_audit_report_path=tmp_path / ".runtime_eval" / "stage35_external_dataset_audit.json",
        workspace_report_path=tmp_path / ".runtime_eval" / "stage35_external_workspace_eval.json",
        qa_report_path=tmp_path / ".runtime_eval" / "stage35_external_qa_eval.json",
        chunk_quality_report_path=tmp_path / ".runtime_eval" / "stage35_external_chunk_quality.json",
        workflow_report_path=tmp_path / ".runtime_eval" / "stage35_external_validation_summary.json",
    )

    assert summary["report_version"] == "stage35_external_example_data_validation_v1"
    assert summary["status"] == "ok"
    assert summary["dataset_audit_status"] == "ok"
    assert summary["workspace_status"] == "ok"
    assert summary["chunk_quality_status"] == "not_requested"
    assert Path(summary["dataset_audit_report_path"]).exists()
    assert Path(summary["workspace_report_path"]).exists()
    assert Path(summary["workflow_report_path"]).exists()
    assert summary["chunk_quality_report_path"] is None
    assert not (tmp_path / ".runtime_eval" / "stage35_workspace" / "results").exists()
    assert not (tmp_path / "storage").exists()
    get_settings.cache_clear()


def test_stage35_process_eval_and_chunk_quality_use_workspace_results(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    workspace_dir = tmp_path / ".runtime_eval" / "stage35_workspace"
    chunk_report_path = tmp_path / ".runtime_eval" / "stage35_external_chunk_quality.json"

    summary = module.run_validation(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        dataset_audit_report_path=tmp_path / ".runtime_eval" / "stage35_external_dataset_audit.json",
        workspace_report_path=tmp_path / ".runtime_eval" / "stage35_external_workspace_eval.json",
        qa_report_path=tmp_path / ".runtime_eval" / "stage35_external_qa_eval.json",
        chunk_quality_report_path=chunk_report_path,
        workflow_report_path=tmp_path / ".runtime_eval" / "stage35_external_validation_summary.json",
        process=True,
        run_eval=True,
        run_chunk_quality=True,
        max_documents=1,
        max_questions=1,
        clean_workspace=True,
    )

    assert list((workspace_dir / "results").glob("*.json"))
    assert summary["status"] == "ok"
    assert summary["chunk_quality_status"] == "ok"
    assert Path(summary["qa_report_path"]).exists()
    assert summary["chunk_quality_report_path"] == str(chunk_report_path.resolve())
    assert Path(summary["workflow_report_path"]).exists()
    chunk_report = json.loads(chunk_report_path.read_text(encoding="utf-8"))
    assert chunk_report["audit_version"] == "stage34_3_chunk_quality_taxonomy_reporting_v1"
    assert chunk_report["stage35_report_version"] == "stage35_external_example_data_validation_v1"
    assert "raw_content_type_counts" in chunk_report
    assert "compact_text_taxonomy" in chunk_report
    assert chunk_report["summary"]["audited_chunks"] >= 1
    assert not (tmp_path / "storage").exists()
    get_settings.cache_clear()


def test_stage35_chunk_quality_requested_with_zero_processed_docs_is_attention(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    dataset_dir, qa_path = _prepare_ambiguous_dataset(tmp_path)
    chunk_report_path = tmp_path / ".runtime_eval" / "stage35_external_chunk_quality.json"

    summary = module.run_validation(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=tmp_path / ".runtime_eval" / "stage35_workspace",
        dataset_audit_report_path=tmp_path / ".runtime_eval" / "stage35_external_dataset_audit.json",
        workspace_report_path=tmp_path / ".runtime_eval" / "stage35_external_workspace_eval.json",
        qa_report_path=tmp_path / ".runtime_eval" / "stage35_external_qa_eval.json",
        chunk_quality_report_path=chunk_report_path,
        workflow_report_path=tmp_path / ".runtime_eval" / "stage35_external_validation_summary.json",
        process=True,
        run_chunk_quality=True,
    )

    assert summary["status"] == "needs_attention"
    assert summary["selected_documents"] == 0
    assert summary["processed_documents"] == 0
    assert summary["skipped_ambiguous"] == 1
    assert summary["chunk_quality_status"] == "skipped_no_processed_documents"
    assert summary["chunk_quality_report_path"] is None
    assert not chunk_report_path.exists()
    assert "rerun_with_ambiguous_policy_all_or_all_supported_scope_for_exploratory_chunk_validation" in summary[
        "recommendations"
    ]
    workflow_report = json.loads(Path(summary["workflow_report_path"]).read_text(encoding="utf-8"))
    assert workflow_report["chunk_quality_status"] == "skipped_no_processed_documents"
    assert workflow_report["status"] == "needs_attention"
    assert not (tmp_path / "storage").exists()
    get_settings.cache_clear()
