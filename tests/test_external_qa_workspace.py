from __future__ import annotations

import importlib
import json
from pathlib import Path

from app.core.config import get_settings


def _load_module():
    module = importlib.import_module("scripts.evaluate_external_qa_workspace")
    return importlib.reload(module)


def _write_tsv(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    lines = ["№ п/п\tВопрос\tОтвет\tДокумент"]
    lines.extend("\t".join(row) for row in rows)
    path.write_text("\n".join(lines), encoding="utf-8")


def _prepare_dataset(tmp_path: Path) -> tuple[Path, Path]:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    qa_path = dataset_dir / "qa.csv"
    _write_tsv(qa_path, [("1", "Что сказано в report?", "alpha", "report.txt")])
    (dataset_dir / "report.txt").write_text("alpha beta gamma", encoding="utf-8")
    return dataset_dir, qa_path


def test_dry_run_builds_manifest_without_storage_or_workspace_writes(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    workspace_dir = tmp_path / ".runtime_eval" / "stage27"

    manifest = module.run_workspace(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        dry_run=True,
        process=False,
        run_eval=False,
        source_scope="expected",
        ambiguous_policy="skip",
        max_documents=None,
        qa_report_path=None,
        workspace_report_path=None,
        clean_workspace=False,
        top_k=5,
        max_questions=None,
        skip_answer_overlap=True,
        report_detail_level="summary",
    )

    assert manifest["dry_run"] is True
    assert manifest["selected_document_count"] == 1
    assert manifest["processed_document_count"] == 0
    assert not workspace_dir.exists()
    assert not (tmp_path / "storage").exists()


def test_ambiguous_expected_source_skip_is_not_selected(tmp_path: Path) -> None:
    module = _load_module()
    dataset_dir = tmp_path / "dataset"
    (dataset_dir / "a").mkdir(parents=True)
    (dataset_dir / "b").mkdir(parents=True)
    qa_path = dataset_dir / "qa.csv"
    _write_tsv(qa_path, [("1", "Где report?", "alpha", "report.txt")])
    (dataset_dir / "a" / "report.txt").write_text("alpha", encoding="utf-8")
    (dataset_dir / "b" / "report.txt").write_text("beta", encoding="utf-8")

    plan = module.build_workspace_plan(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        source_scope="expected",
        ambiguous_policy="skip",
    )

    assert plan["selected_documents"] == []
    assert plan["skipped_examples"][0]["reason"] == "ambiguous_skipped"


def test_all_supported_scope_selects_only_supported_formats(tmp_path: Path) -> None:
    module = _load_module()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    (dataset_dir / "notes.docx").write_text("docx", encoding="utf-8")
    (dataset_dir / "image.heic").write_text("heic", encoding="utf-8")
    (dataset_dir / "archive.zip").write_text("zip", encoding="utf-8")

    plan = module.build_workspace_plan(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        source_scope="all-supported",
        ambiguous_policy="skip",
    )

    selected = plan["selected_documents"]
    assert {item.relative_path for item in selected} == {"notes.docx", "report.txt"}
    assert all(item.extension in {".docx", ".txt"} for item in selected)


def test_max_documents_limits_selected_documents(tmp_path: Path) -> None:
    module = _load_module()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    (dataset_dir / "b.txt").write_text("beta", encoding="utf-8")
    (dataset_dir / "c.txt").write_text("gamma", encoding="utf-8")

    plan = module.build_workspace_plan(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        source_scope="all-supported",
        ambiguous_policy="skip",
        max_documents=2,
    )

    assert plan["selected_before_limit"] == 3
    assert len(plan["selected_documents"]) == 2


def test_workspace_paths_are_created_only_inside_tmp_workspace(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    workspace_dir = tmp_path / ".runtime_eval" / "stage27"

    manifest = module.run_workspace(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        dry_run=False,
        process=True,
        run_eval=False,
        source_scope="expected",
        ambiguous_policy="skip",
        max_documents=None,
        qa_report_path=None,
        workspace_report_path=None,
        clean_workspace=False,
        top_k=5,
        max_questions=None,
        skip_answer_overlap=True,
        report_detail_level="summary",
    )

    assert manifest["processed_document_count"] == 1
    assert (workspace_dir / "uploads").is_dir()
    assert (workspace_dir / "results").is_dir()
    assert (workspace_dir / "index").is_dir()
    assert list((workspace_dir / "results").glob("*.json"))
    assert (workspace_dir / "workspace_manifest.json").exists()
    assert not (tmp_path / "storage").exists()
    get_settings.cache_clear()


def test_explicit_workspace_report_path_is_used_in_processing_mode(tmp_path: Path) -> None:
    module = _load_module()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    workspace_dir = tmp_path / ".runtime_eval" / "stage27"
    report_path = workspace_dir / "workspace_process_report.json"

    manifest = module.run_workspace(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        dry_run=False,
        process=True,
        run_eval=False,
        source_scope="expected",
        ambiguous_policy="skip",
        max_documents=1,
        qa_report_path=None,
        workspace_report_path=report_path,
        clean_workspace=True,
        top_k=5,
        max_questions=None,
        skip_answer_overlap=True,
        report_detail_level="summary",
    )

    assert manifest["workspace_manifest_path"] == str(report_path.resolve())
    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8"))["processed_document_count"] == 1
    assert not (workspace_dir / "workspace_manifest.json").exists()


def test_run_eval_without_processed_results_returns_friendly_status(tmp_path: Path) -> None:
    module = _load_module()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    workspace_dir = tmp_path / ".runtime_eval" / "stage27"

    manifest = module.run_workspace(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        dry_run=False,
        process=False,
        run_eval=True,
        source_scope="expected",
        ambiguous_policy="skip",
        max_documents=None,
        qa_report_path=None,
        workspace_report_path=None,
        clean_workspace=False,
        top_k=5,
        max_questions=None,
        skip_answer_overlap=True,
        report_detail_level="summary",
    )

    report_path = workspace_dir / "reports" / "qa_eval_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "needs_attention"
    assert "workspace results are empty" in " ".join(manifest["notes"])
    assert report["status"] == "no_documents"


def test_processing_smoke_writes_processed_json_to_workspace_results(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    dataset_dir, qa_path = _prepare_dataset(tmp_path)
    workspace_dir = tmp_path / ".runtime_eval" / "stage27"

    manifest = module.run_workspace(
        dataset_dir=dataset_dir,
        qa_path=qa_path,
        workspace_dir=workspace_dir,
        dry_run=False,
        process=True,
        run_eval=True,
        source_scope="expected",
        ambiguous_policy="skip",
        max_documents=1,
        qa_report_path=None,
        workspace_report_path=None,
        clean_workspace=True,
        top_k=5,
        max_questions=1,
        skip_answer_overlap=True,
        report_detail_level="summary",
    )

    result_files = list((workspace_dir / "results").glob("*.json"))
    qa_report = json.loads((workspace_dir / "reports" / "qa_eval_report.json").read_text(encoding="utf-8"))
    assert manifest["selected_document_count"] == 1
    assert manifest["processed_document_count"] == 1
    assert len(result_files) == 1
    assert qa_report["status"] == "ok"
    assert not (tmp_path / "storage").exists()
    get_settings.cache_clear()
