from __future__ import annotations

import importlib
import json
from pathlib import Path


def _load_taxonomy_module():
    module = importlib.import_module("app.evaluation.qa_failure_taxonomy")
    return importlib.reload(module)


def _load_cli_module():
    module = importlib.import_module("scripts.diagnose_qa_failures")
    return importlib.reload(module)


def _qa_report(results: list[dict], total: int | None = None) -> dict:
    return {
        "report_version": "stage24_qa_retrieval_readiness_v1",
        "summary": {"questions_total": total if total is not None else len(results)},
        "results": results,
    }


def _item(**overrides) -> dict:
    base = {
        "row_number": 2,
        "question": "Что указано в документе?",
        "expected_document": "expected.pdf",
        "retrieved_documents": ["other.pdf"],
        "hit_at_1": False,
        "hit_at_3": False,
        "hit_at_5": False,
        "answer_overlap": 0.3,
        "answer_overlap_evaluated": True,
        "table_like_question": False,
        "status": "fail",
        "reason": "expected_source_not_found",
        "top_hits": [{"rank": 1, "filename": "other.pdf", "document_id": "other", "score": 1.0}],
    }
    base.update(overrides)
    return base


def _single_category(report: dict, **kwargs) -> str:
    module = _load_taxonomy_module()
    diagnostic = module.build_diagnostic_report(report, **kwargs)
    return diagnostic["items"][0]["primary_category"]


def test_synthetic_qa_report_with_no_expected_source() -> None:
    category = _single_category(_qa_report([_item(expected_document="", reason="missing_expected_source")]))

    assert category == "no_expected_source_in_qa_row"


def test_synthetic_audit_report_with_ambiguous_expected_document() -> None:
    audit = {"expected_sources": {"ambiguous_examples": [{"document": "expected.pdf", "matches": []}]}}

    category = _single_category(_qa_report([_item()]), external_audit_report=audit)

    assert category == "expected_document_ambiguous_in_dataset"


def test_synthetic_audit_report_with_missing_expected_document() -> None:
    audit = {"expected_sources": {"missing_examples": [{"document": "expected.pdf", "method": "none"}]}}

    category = _single_category(_qa_report([_item()]), external_audit_report=audit)

    assert category == "expected_document_missing_in_dataset"


def test_synthetic_workspace_combination_for_expected_document_not_processed() -> None:
    workspace = {
        "selected_documents": [{"expected_document": "expected.pdf", "relative_path": "expected.pdf"}],
        "processed_documents": [],
    }

    category = _single_category(_qa_report([_item()]), workspace_report=workspace)

    assert category == "expected_document_not_processed"


def test_synthetic_qa_report_with_no_hits() -> None:
    category = _single_category(
        _qa_report([_item(reason="no_results", retrieved_documents=[], top_hits=[])])
    )

    assert category == "evaluator_no_hits"


def test_synthetic_qa_report_with_hits_from_different_doc() -> None:
    category = _single_category(_qa_report([_item()]))

    assert category == "retrieved_different_document"


def test_expected_processed_but_expected_not_in_top_k() -> None:
    workspace = {
        "selected_documents": [{"expected_document": "expected.pdf", "relative_path": "expected.pdf"}],
        "processed_documents": [{"relative_path": "expected.pdf", "status": "processed"}],
    }

    category = _single_category(_qa_report([_item()]), workspace_report=workspace)

    assert category == "processed_but_not_retrieved"


def test_synthetic_qa_report_with_low_answer_overlap() -> None:
    category = _single_category(
        _qa_report(
            [
                _item(
                    retrieved_documents=["expected.pdf"],
                    top_hits=[{"rank": 1, "filename": "expected.pdf"}],
                    hit_at_1=True,
                    hit_at_3=True,
                    hit_at_5=True,
                    reason="ok",
                    answer_overlap=0.05,
                )
            ]
        ),
        answer_overlap_threshold=0.15,
    )

    assert category == "answer_overlap_low"


def test_synthetic_table_like_question_without_table_evidence() -> None:
    category = _single_category(
        _qa_report(
            [
                _item(
                    question="Какое значение указано в таблице выбросов?",
                    table_like_question=True,
                    retrieved_documents=["expected.pdf"],
                    top_hits=[{"rank": 1, "filename": "expected.pdf", "snippet": "plain text"}],
                    answer_overlap=0.01,
                )
            ]
        )
    )

    assert category == "table_like_question_no_table_evidence"


def test_json_output_contains_taxonomy_summary_counts_and_items() -> None:
    module = _load_taxonomy_module()

    diagnostic = module.build_diagnostic_report(_qa_report([_item(reason="no_results", retrieved_documents=[], top_hits=[])]))

    assert diagnostic["taxonomy_version"] == "stage28_qa_failure_taxonomy_v1"
    assert diagnostic["summary"]["total_questions"] == 1
    assert diagnostic["summary"]["diagnosed_items"] == 1
    assert diagnostic["summary"]["category_counts"]["evaluator_no_hits"] == 1
    assert len(diagnostic["items"]) == 1
    assert diagnostic["items"][0]["customer_message"]


def test_cli_does_not_write_output_without_explicit_output_path(tmp_path: Path, capsys) -> None:
    cli = _load_cli_module()
    qa_report_path = tmp_path / "qa_report.json"
    qa_report_path.write_text(
        json.dumps(_qa_report([_item(reason="no_results", retrieved_documents=[], top_hits=[])]), ensure_ascii=False),
        encoding="utf-8",
    )

    cli.main(["--qa-report-path", str(qa_report_path)])
    captured = capsys.readouterr()

    assert "Stage 28 QA failure diagnostics" in captured.out
    assert not list(tmp_path.glob("stage28*.json"))
    assert not (tmp_path / ".runtime_eval").exists()
