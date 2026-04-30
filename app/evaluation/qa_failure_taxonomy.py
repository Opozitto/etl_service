from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


TAXONOMY_VERSION = "stage28_qa_failure_taxonomy_v1"

FAILURE_CATEGORIES = (
    "no_expected_source_in_qa_row",
    "expected_document_missing_in_dataset",
    "expected_document_ambiguous_in_dataset",
    "expected_document_unsupported_format",
    "expected_document_not_processed",
    "processed_but_not_retrieved",
    "retrieved_different_document",
    "answer_overlap_low",
    "table_like_question_no_table_evidence",
    "scanned_pdf_or_ocr_out_of_scope",
    "evaluator_no_hits",
    "unknown_or_needs_manual_review",
)

NO_SOURCE_REASONS = {"missing_expected_source", "no_expected_source", "missing_source"}
NO_HIT_REASONS = {"no_results", "no_hits", "evaluator_no_hits"}
EXPECTED_NOT_FOUND_REASONS = {"expected_source_not_found", "expected_document_not_found"}
TABLE_TERMS = (
    "таблиц",
    "строк",
    "столб",
    "граф",
    "ячейк",
    "значени",
    "показател",
    "концентрац",
    "координат",
    "г/с",
    "т/год",
    "мг/м",
    "м3/с",
    "м3/ч",
)
OCR_TERMS = ("скан", "ocr", "распознаван", "изображени", "pdf-скан", "scanned")


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def normalize_document_key(value: Any) -> str:
    text = normalize_text(value).lower().replace("ё", "е")
    text = re.sub(r"\.(pdf|docx?|rtf|txt|xlsx?|jpe?g|png)$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return normalize_text(text)


def read_json_report(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ValueError(f"report file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"cannot read report as UTF-8 JSON: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"cannot parse JSON report {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON report must be an object: {path}")
    return payload


def load_optional_json_report(path: Path | None) -> dict[str, Any] | None:
    return read_json_report(path) if path else None


def compact_hits(item: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    hits = item.get("top_hits")
    if isinstance(hits, list) and hits:
        compact: list[dict[str, Any]] = []
        for rank, hit in enumerate(hits[:limit], start=1):
            if not isinstance(hit, dict):
                continue
            compact.append(
                {
                    "rank": hit.get("rank", rank),
                    "filename": hit.get("filename"),
                    "document_id": hit.get("document_id"),
                    "score": hit.get("score"),
                    "section_title": hit.get("section_title"),
                }
            )
        return compact
    retrieved = item.get("retrieved_documents") or []
    if not isinstance(retrieved, list):
        return []
    return [{"rank": index, "filename": filename} for index, filename in enumerate(retrieved[:limit], start=1)]


def audit_indexes(audit_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    indexes = {
        "missing": {},
        "ambiguous": {},
        "unsupported": {},
        "matched": {},
    }
    if not audit_report:
        return indexes
    expected_sources = audit_report.get("expected_sources") or {}
    for key, field in (
        ("missing", "missing_examples"),
        ("ambiguous", "ambiguous_examples"),
        ("unsupported", "unsupported_matched_examples"),
        ("matched", "matched_examples"),
    ):
        examples = expected_sources.get(field) or []
        if not isinstance(examples, list):
            continue
        for example in examples:
            if not isinstance(example, dict):
                continue
            document = normalize_text(example.get("document"))
            if document:
                indexes[key][normalize_document_key(document)] = example
    return indexes


def workspace_indexes(workspace_report: dict[str, Any] | None) -> dict[str, Any]:
    processed_relative_paths = set()
    selected_by_document: dict[str, dict[str, Any]] = {}
    skipped_by_document: dict[str, dict[str, Any]] = {}
    processing_errors_by_relative_path: dict[str, dict[str, Any]] = {}
    if not workspace_report:
        return {
            "processed_relative_paths": processed_relative_paths,
            "selected_by_document": selected_by_document,
            "skipped_by_document": skipped_by_document,
            "processing_errors_by_relative_path": processing_errors_by_relative_path,
        }

    for item in workspace_report.get("processed_documents") or []:
        if not isinstance(item, dict):
            continue
        relative_path = normalize_text(item.get("relative_path"))
        status = normalize_text(item.get("status"))
        if relative_path and status in {"processed", "duplicate"}:
            processed_relative_paths.add(relative_path)

    for item in workspace_report.get("selected_documents") or []:
        if not isinstance(item, dict):
            continue
        document = normalize_text(item.get("expected_document"))
        if document:
            selected_by_document[normalize_document_key(document)] = item

    for item in workspace_report.get("skipped_examples") or []:
        if not isinstance(item, dict):
            continue
        document = normalize_text(item.get("document"))
        if document:
            skipped_by_document[normalize_document_key(document)] = item

    for item in workspace_report.get("processing_errors") or []:
        if not isinstance(item, dict):
            continue
        relative_path = normalize_text(item.get("relative_path"))
        if relative_path:
            processing_errors_by_relative_path[relative_path] = item

    return {
        "processed_relative_paths": processed_relative_paths,
        "selected_by_document": selected_by_document,
        "skipped_by_document": skipped_by_document,
        "processing_errors_by_relative_path": processing_errors_by_relative_path,
    }


def is_expected_document_processed(expected_document: str, workspace: dict[str, Any]) -> bool:
    selected = workspace["selected_by_document"].get(normalize_document_key(expected_document))
    if not selected:
        return False
    return normalize_text(selected.get("relative_path")) in workspace["processed_relative_paths"]


def is_table_like(item: dict[str, Any]) -> bool:
    if item.get("table_like_question") is True:
        return True
    haystack = " ".join(
        [
            normalize_text(item.get("question")),
            normalize_text(item.get("expected_answer_preview")),
            normalize_text(item.get("expected_document")),
        ]
    ).lower().replace("ё", "е")
    return any(term in haystack for term in TABLE_TERMS)


def is_ocr_out_of_scope(item: dict[str, Any], audit_evidence: dict[str, Any] | None) -> bool:
    haystack = " ".join(
        [
            normalize_text(item.get("question")),
            normalize_text(item.get("expected_document")),
            json.dumps(audit_evidence or {}, ensure_ascii=False),
        ]
    ).lower().replace("ё", "е")
    return any(term in haystack for term in OCR_TERMS)


def no_table_evidence(item: dict[str, Any]) -> bool:
    if item.get("table_evidence_found") is False:
        return True
    hits = item.get("top_hits") or []
    if isinstance(hits, list) and hits:
        combined = json.dumps(hits, ensure_ascii=False).lower()
        return "table" not in combined and "табли" not in combined
    return True


def document_in_hits(expected_document: str, item: dict[str, Any]) -> bool:
    expected_key = normalize_document_key(expected_document)
    if not expected_key:
        return False
    candidates: list[str] = []
    retrieved = item.get("retrieved_documents")
    if isinstance(retrieved, list):
        candidates.extend(normalize_text(value) for value in retrieved)
    for hit in item.get("top_hits") or []:
        if not isinstance(hit, dict):
            continue
        candidates.extend(
            normalize_text(hit.get(field))
            for field in ("filename", "title", "document_id")
            if hit.get(field)
        )
    for candidate in candidates:
        candidate_key = normalize_document_key(candidate)
        if candidate_key and (expected_key == candidate_key or expected_key in candidate_key or candidate_key in expected_key):
            return True
    return False


def has_hits(item: dict[str, Any]) -> bool:
    retrieved = item.get("retrieved_documents")
    if isinstance(retrieved, list) and retrieved:
        return True
    hits = item.get("top_hits")
    return isinstance(hits, list) and bool(hits)


def collect_diagnosis_candidates(qa_report: dict[str, Any]) -> list[dict[str, Any]]:
    results = qa_report.get("results")
    if isinstance(results, list) and results:
        return [item for item in results if isinstance(item, dict) and item.get("status") != "pass"]

    candidates: list[dict[str, Any]] = []
    for field in ("top_failures", "missing_source_examples"):
        values = qa_report.get(field)
        if isinstance(values, list):
            candidates.extend(item for item in values if isinstance(item, dict))
    return candidates


def row_identifier(item: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    if item.get("row_id") is not None:
        return {"row_id": item.get("row_id")}
    if item.get("row_number") is not None:
        return {"row_number": item.get("row_number")}
    if item.get("question_index") is not None:
        return {"question_index": item.get("question_index")}
    return {"question_index": fallback_index}


def customer_message(category: str) -> str:
    messages = {
        "no_expected_source_in_qa_row": "В строке QA не указан ожидаемый документ-источник, поэтому проверить попадание в источник нельзя.",
        "expected_document_missing_in_dataset": "Ожидаемый документ не найден в инвентаризации внешнего dataset.",
        "expected_document_ambiguous_in_dataset": "Ссылка на ожидаемый документ неоднозначна: в dataset найдено несколько возможных файлов.",
        "expected_document_unsupported_format": "Ожидаемый документ найден, но его формат сейчас не поддержан текущим baseline.",
        "expected_document_not_processed": "Ожидаемый документ есть в dataset/workspace, но не был успешно обработан в temporary workspace.",
        "processed_but_not_retrieved": "Ожидаемый документ обработан, но не попал в top-k результатов retrieval.",
        "retrieved_different_document": "Retrieval вернул документы, но среди них нет ожидаемого источника.",
        "answer_overlap_low": "Источник может быть найден, но overlap ожидаемого ответа с текущим extractive answer низкий.",
        "table_like_question_no_table_evidence": "Вопрос похож на табличный/числовой, но в отчете нет подтвержденного table evidence.",
        "scanned_pdf_or_ocr_out_of_scope": "Похоже на OCR/scanned PDF ограничение, которое не входит в текущий QA/retrieval baseline.",
        "evaluator_no_hits": "Evaluator не нашел ни одного retrieval hit для вопроса.",
        "unknown_or_needs_manual_review": "Недостаточно данных в reports для уверенной автоматической классификации; нужна ручная проверка.",
    }
    return messages.get(category, messages["unknown_or_needs_manual_review"])


def classify_item(
    item: dict[str, Any],
    *,
    audit: dict[str, dict[str, Any]],
    workspace: dict[str, Any],
    answer_overlap_threshold: float,
) -> tuple[str, list[str], dict[str, Any]]:
    expected_document = normalize_text(item.get("expected_document") or item.get("expected_source"))
    expected_key = normalize_document_key(expected_document)
    reason = normalize_text(item.get("reason"))
    reason_codes: list[str] = []
    evidence: dict[str, Any] = {
        "qa_reason": reason or None,
        "qa_status": item.get("status"),
        "expected_document": expected_document or None,
        "retrieved_documents": item.get("retrieved_documents"),
        "hit_at_1": item.get("hit_at_1"),
        "hit_at_3": item.get("hit_at_3"),
        "hit_at_5": item.get("hit_at_5"),
        "answer_overlap": item.get("answer_overlap"),
        "answer_overlap_evaluated": item.get("answer_overlap_evaluated"),
        "table_like_question": item.get("table_like_question"),
    }

    if reason in NO_SOURCE_REASONS or not expected_document:
        return "no_expected_source_in_qa_row", ["qa_expected_source_missing"], evidence

    audit_evidence = None
    for category, code in (
        ("missing", "audit_expected_document_missing"),
        ("ambiguous", "audit_expected_document_ambiguous"),
        ("unsupported", "audit_expected_document_unsupported_format"),
    ):
        if expected_key in audit[category]:
            audit_evidence = audit[category][expected_key]
            evidence["audit_evidence"] = audit_evidence
            mapped = {
                "missing": "expected_document_missing_in_dataset",
                "ambiguous": "expected_document_ambiguous_in_dataset",
                "unsupported": "expected_document_unsupported_format",
            }[category]
            return mapped, [code], evidence

    skipped = workspace["skipped_by_document"].get(expected_key)
    if skipped:
        evidence["workspace_skipped"] = skipped
        skipped_reason = normalize_text(skipped.get("reason"))
        if skipped_reason == "missing":
            return "expected_document_missing_in_dataset", ["workspace_expected_document_missing"], evidence
        if skipped_reason in {"ambiguous_skipped", "ambiguous_no_supported_matches"}:
            return "expected_document_ambiguous_in_dataset", ["workspace_expected_document_ambiguous"], evidence
        if "unsupported" in skipped_reason:
            return "expected_document_unsupported_format", ["workspace_expected_document_unsupported_format"], evidence

    selected = workspace["selected_by_document"].get(expected_key)
    if selected and not is_expected_document_processed(expected_document, workspace):
        evidence["workspace_selected"] = selected
        relative_path = normalize_text(selected.get("relative_path"))
        if relative_path in workspace["processing_errors_by_relative_path"]:
            evidence["workspace_processing_error"] = workspace["processing_errors_by_relative_path"][relative_path]
            reason_codes.append("workspace_processing_error")
        return "expected_document_not_processed", reason_codes + ["workspace_expected_document_not_processed"], evidence

    if is_ocr_out_of_scope(item, audit_evidence):
        return "scanned_pdf_or_ocr_out_of_scope", ["ocr_or_scanned_pdf_marker"], evidence

    if is_table_like(item) and no_table_evidence(item):
        answer_overlap = item.get("answer_overlap")
        if answer_overlap is None or answer_overlap < answer_overlap_threshold or not document_in_hits(expected_document, item):
            return "table_like_question_no_table_evidence", ["table_like_question", "no_table_evidence_in_report"], evidence

    if reason in NO_HIT_REASONS or not has_hits(item):
        return "evaluator_no_hits", ["qa_evaluator_no_hits"], evidence

    answer_overlap = item.get("answer_overlap")
    answer_overlap_evaluated = item.get("answer_overlap_evaluated", answer_overlap is not None)
    if (
        answer_overlap_evaluated
        and isinstance(answer_overlap, (int, float))
        and answer_overlap < answer_overlap_threshold
        and document_in_hits(expected_document, item)
    ):
        return "answer_overlap_low", ["answer_overlap_below_threshold"], evidence

    if reason in EXPECTED_NOT_FOUND_REASONS or not document_in_hits(expected_document, item):
        if is_expected_document_processed(expected_document, workspace):
            evidence["workspace_selected"] = selected
            return "processed_but_not_retrieved", ["expected_processed", "expected_not_in_top_k"], evidence
        if has_hits(item):
            return "retrieved_different_document", ["retrieval_hits_from_other_documents"], evidence

    return "unknown_or_needs_manual_review", ["insufficient_report_fields"], evidence


def build_customer_summary(category_counts: Counter[str], total_questions: int, diagnosed_items: int) -> str:
    if diagnosed_items == 0:
        return f"Проанализировано вопросов: {total_questions}. Явных failures/limitations в доступных деталях report не найдено."
    top = category_counts.most_common(3)
    parts = ", ".join(f"{category}: {count}" for category, count in top)
    return f"Проанализировано вопросов: {total_questions}. Диагностировано failures/limitations: {diagnosed_items}. Основные категории: {parts}."


def recommended_actions(category_counts: Counter[str]) -> list[str]:
    actions: list[str] = []
    if category_counts["expected_document_ambiguous_in_dataset"]:
        actions.append("Разобрать неоднозначные ссылки на документы / уточнить mapping expected document -> file.")
    if category_counts["expected_document_missing_in_dataset"]:
        actions.append("Проверить поставку dataset: добавить отсутствующие ожидаемые документы или исправить ссылки в QA.")
    if category_counts["expected_document_unsupported_format"]:
        actions.append("Отдельно решить поддержку форматов, которые сейчас не входят в baseline.")
    if category_counts["expected_document_not_processed"]:
        actions.append("Сначала обработать нужные документы во temporary workspace и повторить QA eval.")
    if category_counts["evaluator_no_hits"]:
        actions.append("Проверить, что нужные документы обработаны и доступны evaluator; затем отдельно разбирать retrieval coverage.")
    if category_counts["processed_but_not_retrieved"] or category_counts["retrieved_different_document"]:
        actions.append("Улучшать retrieval/evidence в отдельном stage, не меняя это внутри diagnostics.")
    if category_counts["scanned_pdf_or_ocr_out_of_scope"]:
        actions.append("Запланировать отдельный OCR/scanned PDF stage для таких источников.")
    if category_counts["table_like_question_no_table_evidence"]:
        actions.append("Запланировать отдельный table evidence / table retrieval improvement stage.")
    if category_counts["answer_overlap_low"]:
        actions.append("Проверить extractive answer/evidence overlap на full QA report; это не показатель готового LLM/RAG ответа.")
    if not actions:
        actions.append("Проверить items с unknown_or_needs_manual_review вручную и при необходимости расширить reports деталями.")
    return actions[:5]


def build_diagnostic_report(
    qa_report: dict[str, Any],
    *,
    external_audit_report: dict[str, Any] | None = None,
    workspace_report: dict[str, Any] | None = None,
    answer_overlap_threshold: float = 0.15,
    failures_limit: int = 50,
) -> dict[str, Any]:
    if failures_limit < 0:
        raise ValueError("failures_limit must be greater than or equal to 0")
    if answer_overlap_threshold < 0:
        raise ValueError("answer_overlap_threshold must be greater than or equal to 0")

    audit = audit_indexes(external_audit_report)
    workspace = workspace_indexes(workspace_report)
    candidates = collect_diagnosis_candidates(qa_report)
    items: list[dict[str, Any]] = []

    for index, item in enumerate(candidates[:failures_limit], start=1):
        category, reason_codes, evidence = classify_item(
            item,
            audit=audit,
            workspace=workspace,
            answer_overlap_threshold=answer_overlap_threshold,
        )
        diagnosed = {
            **row_identifier(item, index),
            "question": normalize_text(item.get("question")),
            "expected_source": normalize_text(item.get("expected_source") or item.get("expected_document")),
            "expected_document": normalize_text(item.get("expected_document") or item.get("expected_source")),
            "primary_category": category,
            "reason_codes": sorted(set(reason_codes)),
            "customer_message": customer_message(category),
            "technical_evidence": {key: value for key, value in evidence.items() if value is not None},
        }
        top_hits = compact_hits(item)
        if top_hits:
            diagnosed["top_hits"] = top_hits
        items.append(diagnosed)

    category_counts = Counter(item["primary_category"] for item in items)
    summary = qa_report.get("summary") or {}
    total_questions = int(summary.get("questions_total") or summary.get("total_questions") or len(candidates))
    output_counts = {category: category_counts.get(category, 0) for category in FAILURE_CATEGORIES}
    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "mode": "read-only",
        "input_reports": {
            "qa_report_version": qa_report.get("report_version"),
            "external_audit_report_version": (external_audit_report or {}).get("report_version"),
            "workspace_report_version": (workspace_report or {}).get("report_version"),
        },
        "config": {
            "answer_overlap_threshold": answer_overlap_threshold,
            "failures_limit": failures_limit,
        },
        "summary": {
            "total_questions": total_questions,
            "diagnosed_items": len(items),
            "category_counts": output_counts,
            "customer_summary_ru": build_customer_summary(category_counts, total_questions, len(items)),
            "recommended_next_actions_ru": recommended_actions(category_counts),
        },
        "items": items,
    }


def write_diagnostic_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def print_console_summary(report: dict[str, Any], output_path: Path | None = None) -> None:
    summary = report["summary"]
    print("Stage 28 QA failure diagnostics")
    print(f"taxonomy_version={report['taxonomy_version']}")
    print(f"questions_analyzed={summary['total_questions']}")
    print(f"failures_or_limitations={summary['diagnosed_items']}")
    print("category_counts:")
    for category, count in summary["category_counts"].items():
        if count:
            print(f"  {category}: {count}")
    print("recommended_next_actions:")
    for action in summary["recommended_next_actions_ru"]:
        print(f"  - {action}")
    if output_path:
        print(f"json_report_path={output_path}")


def build_report_from_paths(
    *,
    qa_report_path: Path,
    external_audit_report_path: Path | None = None,
    workspace_report_path: Path | None = None,
    answer_overlap_threshold: float = 0.15,
    failures_limit: int = 50,
) -> dict[str, Any]:
    return build_diagnostic_report(
        read_json_report(qa_report_path),
        external_audit_report=load_optional_json_report(external_audit_report_path),
        workspace_report=load_optional_json_report(workspace_report_path),
        answer_overlap_threshold=answer_overlap_threshold,
        failures_limit=failures_limit,
    )
