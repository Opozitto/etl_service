from __future__ import annotations

import importlib
import json
import uuid
from pathlib import Path

import pytest

from app.core.config import get_settings


def _load_module():
    module = importlib.import_module("scripts.inspect_document_structure")
    return importlib.reload(module)


def _write_sample(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "1. Intro\n\n"
        "Inspection baseline text for one document.\n\n"
        "- first item\n"
        "- second item\n\n"
        "2. Details\n\n"
        "More text for chunk preview and structure inspection.",
        encoding="utf-8",
    )


def _case_dir(name: str) -> Path:
    return Path(".runtime_eval") / "test_inspect_document_structure" / f"{name}_{uuid.uuid4().hex}"


def _storage_snapshot() -> dict[str, set[str]]:
    storage = get_settings().resolved_storage_dir
    return {
        child: {str(path.resolve()) for path in (storage / child).glob("**/*") if path.is_file()}
        for child in ("index", "results", "uploads")
        if (storage / child).exists()
    }


def test_builds_json_report_in_temporary_workspace() -> None:
    module = _load_module()
    get_settings.cache_clear()
    case_dir = _case_dir("json_report")
    input_path = case_dir / "input.txt"
    workspace_dir = case_dir / "inspect"
    before_storage = _storage_snapshot()
    _write_sample(input_path)

    report = module.build_inspection_report(
        input_path=input_path,
        workspace_dir=workspace_dir,
        clean_workspace=True,
        max_blocks=10,
        max_chunks=10,
    )

    assert report["report_version"] == module.REPORT_VERSION
    assert report["status"] == "processed"
    assert report["input"]["filename"] == "input.txt"
    assert report["input"]["checksum_sha256"]
    assert report["workspace_dir"] == str(workspace_dir.resolve())
    assert report["document_id"]
    assert report["metadata"]["section_count"] >= 1
    assert report["counts"]["blocks"] >= 1
    assert report["counts"]["chunks"] >= 1
    assert report["sections"]
    assert report["blocks"]
    assert report["chunks"]
    assert Path(report["artifacts"]["result_json_path"]).is_file()
    assert Path(report["artifacts"]["source_file_path"]).is_file()
    assert (workspace_dir / "uploads").is_dir()
    assert (workspace_dir / "results").is_dir()
    assert (workspace_dir / "index").is_dir()
    assert _storage_snapshot() == before_storage
    get_settings.cache_clear()


def test_markdown_and_json_reports_are_written_only_when_requested() -> None:
    module = _load_module()
    get_settings.cache_clear()
    case_dir = _case_dir("reports")
    input_path = case_dir / "input.txt"
    workspace_dir = case_dir / "inspect"
    markdown_path = case_dir / "reports" / "inspect.md"
    json_path = case_dir / "reports" / "inspect.json"
    _write_sample(input_path)

    report = module.build_inspection_report(input_path=input_path, workspace_dir=workspace_dir, clean_workspace=True)
    module.write_markdown_report(markdown_path, report)
    module.write_json_report(json_path, report)

    markdown = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "# Single-file structure inspector" in markdown
    assert "## Chunks" in markdown
    assert payload["document_id"] == report["document_id"]
    get_settings.cache_clear()


def test_preview_and_max_limits_are_respected() -> None:
    module = _load_module()
    case_dir = _case_dir("limits")
    input_path = case_dir / "input.txt"
    workspace_dir = case_dir / "inspect"
    _write_sample(input_path)

    report = module.build_inspection_report(
        input_path=input_path,
        workspace_dir=workspace_dir,
        text_preview_chars=12,
        max_blocks=1,
        max_chunks=1,
        max_tables=0,
        max_images=0,
        clean_workspace=True,
    )

    assert report["limits"]["blocks"]["shown"] == 1
    assert report["limits"]["chunks"]["shown"] == 1
    assert report["limits"]["tables"]["shown"] == 0
    assert report["limits"]["images"]["shown"] == 0
    assert all(len(block["text_preview"]) <= 12 for block in report["blocks"])
    assert all(len(chunk["text_preview"]) <= 12 for chunk in report["chunks"])


def test_dangerous_workspace_guard_rejects_production_storage_path() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="production storage|storage"):
        module.prepare_workspace(Path("storage"), clean_workspace=False)

    with pytest.raises(ValueError, match="production storage"):
        module.prepare_workspace(get_settings().resolved_storage_dir / "results" / "inspect", clean_workspace=False)


def test_console_only_mode_does_not_write_report_files(capsys) -> None:
    module = _load_module()
    get_settings.cache_clear()
    case_dir = _case_dir("console")
    input_path = case_dir / "input.txt"
    workspace_dir = case_dir / "inspect"
    _write_sample(input_path)

    module.main(
        [
            "--input-path",
            str(input_path),
            "--workspace-dir",
            str(workspace_dir),
            "--clean-workspace",
            "--max-blocks",
            "1",
            "--max-chunks",
            "1",
        ]
    )

    captured = capsys.readouterr()
    assert "Stage 38.2 single-file structure inspector" in captured.out
    assert "markdown_report_path=" not in captured.out
    assert "json_report_path=" not in captured.out
    assert list((workspace_dir / "results").glob("*.json"))
    assert not list(case_dir.glob("*.md"))
    assert not list(case_dir.glob("*.json"))
    get_settings.cache_clear()


def test_failed_input_report_is_error_without_false_success() -> None:
    module = _load_module()
    case_dir = _case_dir("failed")
    input_path = case_dir / "input.unsupported"
    workspace_dir = case_dir / "inspect"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text("unsupported", encoding="utf-8")

    report = module.build_inspection_report(
        input_path=input_path,
        workspace_dir=workspace_dir,
        clean_workspace=True,
    )

    assert report["status"] == "error"
    assert report["error_message"]
    assert report["document_id"] is None
    assert report["counts"]["chunks"] == 0
    assert report["chunks"] == []
