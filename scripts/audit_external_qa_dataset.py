from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPORT_VERSION = "stage26_external_qa_dataset_audit_v1"
DEFAULT_MAX_EXAMPLES = 10
DELIMITER_FALLBACKS = ("\t", ";", ",", "|")

QUESTION_COLUMNS = ("вопрос", "question", "query")
ANSWER_COLUMNS = ("ответ", "answer", "expected_answer", "gold_answer")
DOCUMENT_COLUMNS = ("документ", "источник", "source", "document", "expected_document", "file", "filename")

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".rtf",
    ".txt",
    ".xlsx",
    ".xls",
    ".jpg",
    ".jpeg",
    ".png",
}
UNSUPPORTED_IMAGE_EXTENSIONS = {".heic", ".heif", ".tiff", ".tif", ".bmp", ".webp"}
DOCUMENT_EXTENSION_RE = re.compile(r"\.(pdf|docx?|rtf|txt|xlsx?|jpe?g|png)$", flags=re.IGNORECASE)
PUNCT_SPACE_RE = re.compile(r"[^\w]+", flags=re.UNICODE)

NO_SOURCE_PLACEHOLDERS = {
    "",
    "-",
    "—",
    "n/a",
    "na",
    "none",
    "null",
    "нет",
    "не указан",
    "не указано",
    "отсутствует",
}

TABLE_STRONG_TERMS = {
    "таблица",
    "строка",
    "столбец",
    "графа",
    "ячейка",
    "значение",
    "показатель",
    "концентрация",
    "концентрации",
    "координаты",
}
TABLE_STRONG_PHRASES = (
    "расчетная точка",
    "изав №",
    "изав no",
    "изав n",
    "параметры выбросов",
)
TABLE_UNITS = ("г/с", "т/год", "мг/м3", "мг/м³")
SOURCE_REFERENCE_STOPWORDS = {
    "book",
    "chapter",
    "section",
    "table",
    "книга",
    "раздел",
    "таблица",
    "том",
}


@dataclass(frozen=True)
class QARow:
    row_number: int
    question: str
    answer: str
    document: str


@dataclass(frozen=True)
class FileRecord:
    relative_path: str
    filename: str
    stem: str
    extension: str
    size_bytes: int
    supported: bool
    category: str
    filename_key: str
    stem_key: str


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).replace("\u00a0", " ")).strip()


def normalize_column_name(name: str) -> str:
    normalized = normalize_text(name.lstrip("\ufeff")).lower().replace("ё", "е")
    return normalize_text(normalized)


def normalize_document_key(text: str) -> str:
    normalized = normalize_text(text).lower().replace("ё", "е")
    normalized = DOCUMENT_EXTENSION_RE.sub("", normalized)
    normalized = PUNCT_SPACE_RE.sub(" ", normalized)
    return normalize_text(normalized)


def document_key_variants(text: str) -> list[str]:
    variants = [normalize_document_key(text)]
    if "," in text:
        variants.append(normalize_document_key(text.split(",", maxsplit=1)[0]))
    return [variant for index, variant in enumerate(variants) if variant and variant not in variants[:index]]


def document_key_tokens(key: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", key, flags=re.UNICODE)
        if token and token not in SOURCE_REFERENCE_STOPWORDS
    }


def normalize_expected_source(text: str) -> str:
    normalized = normalize_text(text).lower().replace("ё", "е")
    return normalized.rstrip(".!?,;: ")


def is_no_source_placeholder(text: str) -> bool:
    return normalize_expected_source(text) in NO_SOURCE_PLACEHOLDERS


def resolve_delimiter_override(delimiter: str | None) -> str | None:
    if delimiter is None:
        return None
    normalized = delimiter.strip().lower()
    if normalized in {"\\t", "tab", "tsv", "t"}:
        return "\t"
    if normalized in {";", "semicolon", "scsv"}:
        return ";"
    if normalized in {",", "comma", "csv"}:
        return ","
    if normalized in {"|", "pipe"}:
        return "|"
    return delimiter


def score_delimiter(raw_text: str, delimiter: str, field_candidates: Sequence[str]) -> tuple[int, int, int]:
    reader = csv.reader(raw_text.splitlines(), delimiter=delimiter)
    rows = [row for row in reader if row]
    if not rows:
        return (0, 0, 0)
    headers = rows[0]
    normalized_headers = [normalize_column_name(header) for header in headers]
    candidate_headers = {normalize_column_name(candidate) for candidate in field_candidates}
    recognized = sum(1 for header in normalized_headers if header in candidate_headers)
    widest_row = max((len(row) for row in rows[:5]), default=0)
    return (recognized, widest_row, len(headers))


def choose_delimiter(raw_text: str, override: str | None, field_candidates: Sequence[str]) -> str:
    resolved_override = resolve_delimiter_override(override)
    if resolved_override:
        return resolved_override

    candidate_delimiters: list[str] = []
    try:
        sniffed = csv.Sniffer().sniff(raw_text[:4096], delimiters="\t;,|")
        candidate_delimiters.append(sniffed.delimiter)
    except csv.Error:
        pass
    for delimiter in DELIMITER_FALLBACKS:
        if delimiter not in candidate_delimiters:
            candidate_delimiters.append(delimiter)

    scored = [(score_delimiter(raw_text, delimiter, field_candidates), delimiter) for delimiter in candidate_delimiters]
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_delimiter = scored[0]
    if best_score == (0, 0, 0):
        return "\t" if "\t" in raw_text else ";"
    return best_delimiter


def read_csv_rows(path: Path, encoding: str, delimiter: str | None) -> tuple[list[dict[str, str]], list[str], str]:
    raw_text = path.read_text(encoding=encoding)
    selected_delimiter = choose_delimiter(raw_text, delimiter, QUESTION_COLUMNS + ANSWER_COLUMNS + DOCUMENT_COLUMNS)
    reader = csv.DictReader(raw_text.splitlines(), delimiter=selected_delimiter)
    fieldnames = list(reader.fieldnames or [])
    rows = [
        {str(key): normalize_text(value or "") for key, value in row.items() if key is not None}
        for row in reader
    ]
    return rows, fieldnames, selected_delimiter


def resolve_column(fieldnames: Sequence[str], override: str | None, candidates: Sequence[str], label: str) -> str:
    if override:
        override_key = normalize_column_name(override)
        for fieldname in fieldnames:
            if normalize_column_name(fieldname) == override_key:
                return fieldname
        raise ValueError(
            f"Column '{override}' for {label} not found. Available columns: {', '.join(fieldnames) or 'none'}"
        )

    normalized_map = {normalize_column_name(name): name for name in fieldnames}
    for candidate in candidates:
        found = normalized_map.get(normalize_column_name(candidate))
        if found:
            return found
    raise ValueError(
        "Cannot detect {label} column. Available columns: {columns}. "
        "Use --question-column / --answer-column / --document-column.".format(
            label=label,
            columns=", ".join(fieldnames) or "none",
        )
    )


def load_qa_rows(
    qa_path: Path,
    encoding: str = "utf-8-sig",
    delimiter: str | None = None,
    question_column: str | None = None,
    answer_column: str | None = None,
    document_column: str | None = None,
) -> tuple[list[QARow], dict[str, Any]]:
    raw_rows, fieldnames, selected_delimiter = read_csv_rows(qa_path, encoding=encoding, delimiter=delimiter)
    question_col = resolve_column(fieldnames, question_column, QUESTION_COLUMNS, "question")
    answer_col = resolve_column(fieldnames, answer_column, ANSWER_COLUMNS, "answer")
    document_col = resolve_column(fieldnames, document_column, DOCUMENT_COLUMNS, "document/source")

    rows: list[QARow] = []
    for index, raw in enumerate(raw_rows, start=2):
        rows.append(
            QARow(
                row_number=index,
                question=normalize_text(raw.get(question_col, "")),
                answer=normalize_text(raw.get(answer_col, "")),
                document=normalize_text(raw.get(document_col, "")),
            )
        )

    return rows, {
        "encoding": encoding,
        "delimiter": selected_delimiter,
        "columns": {
            "question": question_col,
            "answer": answer_col,
            "document": document_col,
        },
        "raw_row_count": len(raw_rows),
    }


def classify_extension(extension: str) -> tuple[bool, str]:
    if extension in SUPPORTED_EXTENSIONS:
        return True, "supported"
    if extension in UNSUPPORTED_IMAGE_EXTENSIONS:
        return False, "unsupported_image"
    return False, "unknown_unsupported"


def inventory_files(dataset_dir: Path) -> list[FileRecord]:
    records: list[FileRecord] = []
    for path in sorted(dataset_dir.rglob("*")):
        if not path.is_file():
            continue
        extension = path.suffix.lower()
        supported, category = classify_extension(extension)
        relative_path = path.relative_to(dataset_dir).as_posix()
        records.append(
            FileRecord(
                relative_path=relative_path,
                filename=path.name,
                stem=path.stem,
                extension=extension,
                size_bytes=path.stat().st_size,
                supported=supported,
                category=category,
                filename_key=normalize_document_key(path.name),
                stem_key=normalize_document_key(path.stem),
            )
        )
    return records


def record_example(record: FileRecord) -> dict[str, Any]:
    return {
        "relative_path": record.relative_path,
        "filename": record.filename,
        "extension": record.extension,
        "supported": record.supported,
        "category": record.category,
        "size_bytes": record.size_bytes,
    }


def build_match_indexes(records: Sequence[FileRecord]) -> dict[str, dict[str, list[FileRecord]]]:
    exact_filename: dict[str, list[FileRecord]] = defaultdict(list)
    normalized_name: dict[str, list[FileRecord]] = defaultdict(list)
    normalized_stem: dict[str, list[FileRecord]] = defaultdict(list)
    for record in records:
        exact_filename[record.filename.lower()].append(record)
        normalized_name[record.filename_key].append(record)
        normalized_stem[record.stem_key].append(record)
    return {
        "exact_filename": dict(exact_filename),
        "normalized_name": dict(normalized_name),
        "normalized_stem": dict(normalized_stem),
    }


def unique_records(records: Sequence[FileRecord]) -> list[FileRecord]:
    seen: set[str] = set()
    unique: list[FileRecord] = []
    for record in records:
        if record.relative_path in seen:
            continue
        seen.add(record.relative_path)
        unique.append(record)
    return unique


def match_expected_document(expected_document: str, records: Sequence[FileRecord], indexes: dict[str, dict[str, list[FileRecord]]]) -> dict[str, Any]:
    expected_clean = normalize_text(expected_document)
    exact_matches = indexes["exact_filename"].get(expected_clean.lower(), [])
    if exact_matches:
        matches = unique_records(exact_matches)
        return {"status": "matched" if len(matches) == 1 else "ambiguous", "method": "exact_filename", "matches": matches}

    expected_keys = document_key_variants(expected_clean)
    if not expected_keys:
        return {"status": "missing", "method": "empty", "matches": []}

    normalized_matches = unique_records(
        [
            record
            for expected_key in expected_keys
            for record in indexes["normalized_name"].get(expected_key, []) + indexes["normalized_stem"].get(expected_key, [])
        ]
    )
    if normalized_matches:
        return {
            "status": "matched" if len(normalized_matches) == 1 else "ambiguous",
            "method": "normalized_filename_or_stem",
            "matches": normalized_matches,
        }

    if any(len(expected_key) >= 8 for expected_key in expected_keys):
        contains_matches = unique_records(
            [
                record
                for record in records
                for expected_key in expected_keys
                if expected_key in record.filename_key
                or expected_key in record.stem_key
                or record.filename_key in expected_key
                or record.stem_key in expected_key
            ]
        )
        if contains_matches:
            return {
                "status": "matched" if len(contains_matches) == 1 else "ambiguous",
                "method": "bounded_contains",
                "matches": contains_matches,
            }

    token_subset_matches = unique_records(
        [
            record
            for record in records
            for expected_key in expected_keys
            if len(document_key_tokens(expected_key)) >= 3
            and document_key_tokens(expected_key).issubset(document_key_tokens(record.filename_key))
        ]
    )
    if token_subset_matches:
        return {
            "status": "matched" if len(token_subset_matches) == 1 else "ambiguous",
            "method": "token_subset",
            "matches": token_subset_matches,
        }

    return {"status": "missing", "method": "none", "matches": []}


def is_table_like_question(question: str) -> bool:
    haystack = normalize_text(question).lower().replace("ё", "е")
    token_haystack = set(re.findall(r"\w+", haystack, flags=re.UNICODE))
    if token_haystack & TABLE_STRONG_TERMS:
        return True
    if any(phrase in haystack for phrase in TABLE_STRONG_PHRASES):
        return True
    if any(unit in haystack for unit in TABLE_UNITS):
        return True
    if "источник" in token_haystack and ("№" in haystack or "номер" in token_haystack):
        return True
    return False


def limited(items: Sequence[Any], max_examples: int) -> list[Any]:
    return list(items[: max(0, max_examples)])


def duplicate_examples(groups: dict[str, list[FileRecord]], max_examples: int) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for key, records in sorted(groups.items()):
        if key and len(records) > 1:
            examples.append(
                {
                    "key": key,
                    "count": len(records),
                    "files": [record.relative_path for record in records[:max_examples]],
                }
            )
        if len(examples) >= max_examples:
            break
    return examples


def build_audit_report(
    dataset_dir: Path,
    qa_path: Path,
    encoding: str = "utf-8-sig",
    delimiter: str | None = None,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
    question_column: str | None = None,
    answer_column: str | None = None,
    document_column: str | None = None,
) -> dict[str, Any]:
    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise ValueError(f"dataset dir not found or not a directory: {dataset_dir}")
    if not qa_path.exists() or not qa_path.is_file():
        raise ValueError(f"QA file not found: {qa_path}")

    qa_rows, qa_info = load_qa_rows(
        qa_path=qa_path,
        encoding=encoding,
        delimiter=delimiter,
        question_column=question_column,
        answer_column=answer_column,
        document_column=document_column,
    )
    files = inventory_files(dataset_dir)
    indexes = build_match_indexes(files)

    question_rows = [row for row in qa_rows if row.question]
    answer_count = sum(1 for row in qa_rows if row.answer)
    no_source_rows = [row for row in qa_rows if is_no_source_placeholder(row.document)]
    expected_rows = [row for row in qa_rows if not is_no_source_placeholder(row.document)]
    unique_expected_docs = sorted({normalize_text(row.document) for row in expected_rows if normalize_text(row.document)})

    matched_examples: list[dict[str, Any]] = []
    missing_examples: list[dict[str, Any]] = []
    ambiguous_examples: list[dict[str, Any]] = []
    unsupported_matched_examples: list[dict[str, Any]] = []

    matched_count = 0
    missing_count = 0
    ambiguous_count = 0
    unsupported_matched_count = 0

    for expected_doc in unique_expected_docs:
        match = match_expected_document(expected_doc, files, indexes)
        match_status = match["status"]
        match_records: list[FileRecord] = match["matches"]
        if match_status == "missing":
            missing_count += 1
            missing_examples.append({"document": expected_doc, "method": match["method"]})
            continue
        if match_status == "ambiguous":
            ambiguous_count += 1
            ambiguous_examples.append(
                {
                    "document": expected_doc,
                    "method": match["method"],
                    "matches": [record_example(record) for record in match_records[:max_examples]],
                }
            )
            continue

        matched_count += 1
        matched_record = match_records[0]
        matched_examples.append(
            {
                "document": expected_doc,
                "method": match["method"],
                "match": record_example(matched_record),
            }
        )
        if not matched_record.supported:
            unsupported_matched_count += 1
            unsupported_matched_examples.append(
                {
                    "document": expected_doc,
                    "method": match["method"],
                    "match": record_example(matched_record),
                }
            )

    by_extension = Counter(record.extension or "<no_extension>" for record in files)
    supported_by_extension = Counter((record.extension or "<no_extension>") for record in files if record.supported)
    unsupported_by_extension = Counter((record.extension or "<no_extension>") for record in files if not record.supported)

    duplicate_filename_examples = duplicate_examples(indexes["exact_filename"], max_examples)
    duplicate_stem_examples = duplicate_examples(indexes["normalized_stem"], max_examples)
    notes: list[str] = [
        "Read-only audit only: no ingestion, no production storage writes, no LLM/RAG/generation.",
        "External dataset files are referenced by path and are not copied into the repository.",
    ]
    if duplicate_filename_examples or duplicate_stem_examples:
        notes.append("Duplicate filenames/stems exist and may make expected source matching ambiguous.")
    if unsupported_matched_count:
        notes.append("Some expected documents match files with unsupported formats.")
    if missing_count:
        notes.append("Some expected documents were not found in the dataset inventory.")

    status = "needs_attention" if missing_count or ambiguous_count or unsupported_matched_count else "ok"
    examples = [
        {
            "row_number": row.row_number,
            "question": row.question,
            "answer": row.answer,
            "document": row.document,
            "has_expected_source": not is_no_source_placeholder(row.document),
            "table_like_question": is_table_like_question(row.question),
        }
        for row in qa_rows[:max_examples]
    ]

    return {
        "report_version": REPORT_VERSION,
        "status": status,
        "dataset_dir": str(dataset_dir),
        "qa_path": str(qa_path),
        "qa": {
            "row_count": len(qa_rows),
            "question_count": len(question_rows),
            "answer_count": answer_count,
            "expected_source_count": len(expected_rows),
            "missing_expected_source_count": len(no_source_rows),
            "table_like_question_count": sum(1 for row in question_rows if is_table_like_question(row.question)),
            "encoding": qa_info["encoding"],
            "delimiter": qa_info["delimiter"],
            "columns": qa_info["columns"],
            "examples": examples,
        },
        "files": {
            "total_count": len(files),
            "supported_count": sum(1 for record in files if record.supported),
            "unsupported_count": sum(1 for record in files if not record.supported),
            "by_extension": dict(sorted(by_extension.items())),
            "supported_by_extension": dict(sorted(supported_by_extension.items())),
            "unsupported_by_extension": dict(sorted(unsupported_by_extension.items())),
            "duplicate_filename_examples": duplicate_filename_examples,
            "duplicate_stem_examples": duplicate_stem_examples,
        },
        "expected_sources": {
            "unique_count": len(unique_expected_docs),
            "matched_count": matched_count,
            "missing_count": missing_count,
            "ambiguous_count": ambiguous_count,
            "unsupported_matched_count": unsupported_matched_count,
            "missing_examples": limited(missing_examples, max_examples),
            "ambiguous_examples": limited(ambiguous_examples, max_examples),
            "matched_examples": limited(matched_examples, max_examples),
            "unsupported_matched_examples": limited(unsupported_matched_examples, max_examples),
        },
        "notes": notes,
    }


def print_report(report: dict[str, Any]) -> None:
    qa = report["qa"]
    files = report["files"]
    expected_sources = report["expected_sources"]
    print("External QA dataset coverage audit")
    print(f"status={report['status']}")
    print(f"dataset_dir={report['dataset_dir']}")
    print(f"qa_path={report['qa_path']}")
    print(f"total_files={files['total_count']}")
    print(f"qa_rows={qa['row_count']} questions={qa['question_count']} answers={qa['answer_count']}")
    print(
        "expected_source_rows={expected} no_source_rows={missing}".format(
            expected=qa["expected_source_count"],
            missing=qa["missing_expected_source_count"],
        )
    )
    print(
        "expected_docs: unique={unique_count} matched={matched_count} missing={missing_count} "
        "ambiguous={ambiguous_count} unsupported_matched={unsupported_matched_count}".format(**expected_sources)
    )
    print(
        "files: supported={supported_count} unsupported={unsupported_count}".format(
            **files,
        )
    )
    print(f"table_like_question_count={qa['table_like_question_count']}")
    if report.get("json_report_path"):
        print(f"json_report_path={report['json_report_path']}")
    if report["status"] != "ok":
        print("Diagnostic: dataset coverage needs attention before Stage 27 processing/eval.")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Read-only external QA dataset coverage audit")
    parser.add_argument("--dataset-dir", required=True, help="External dataset directory to inventory")
    parser.add_argument("--qa-path", required=True, help="Path to QA CSV/TSV file")
    parser.add_argument("--json-report-path", help="Optional path for bounded JSON report")
    parser.add_argument("--encoding", default="utf-8-sig", help="QA file encoding")
    parser.add_argument("--delimiter", help="Delimiter override: tab/tsv/t/\\t, semicolon, comma, pipe")
    parser.add_argument("--max-examples", type=positive_int, default=DEFAULT_MAX_EXAMPLES)
    parser.add_argument("--question-column", help="Override question column name")
    parser.add_argument("--answer-column", help="Override answer column name")
    parser.add_argument("--document-column", help="Override expected document/source column name")
    args = parser.parse_args(argv)

    report = build_audit_report(
        dataset_dir=Path(args.dataset_dir).resolve(),
        qa_path=Path(args.qa_path).resolve(),
        encoding=args.encoding,
        delimiter=args.delimiter,
        max_examples=args.max_examples,
        question_column=args.question_column,
        answer_column=args.answer_column,
        document_column=args.document_column,
    )

    if args.json_report_path:
        report_path = Path(args.json_report_path).resolve()
        report["json_report_path"] = str(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(report)


if __name__ == "__main__":
    main()
