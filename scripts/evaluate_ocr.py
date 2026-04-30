from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Sequence

from app.pipeline.ocr import LocalOCRAdapter
from app.pipeline.transform.normalizer import normalize_text
from app.pipeline.extractors.registry import (
    KNOWN_UNSUPPORTED_IMAGE_SUFFIXES,
    SUPPORTED_STANDALONE_IMAGE_SUFFIXES,
)


REPORT_VERSION = "stage21_ocr_smoke_eval_v1"
SUPPORTED_SUFFIXES = tuple(SUPPORTED_STANDALONE_IMAGE_SUFFIXES)
UNSUPPORTED_SUFFIXES = tuple(KNOWN_UNSUPPORTED_IMAGE_SUFFIXES)
IMAGE_LIKE_SUFFIXES = set(SUPPORTED_SUFFIXES) | set(UNSUPPORTED_SUFFIXES)
PDF_SUFFIX = ".pdf"
PREVIEW_LENGTH = 96


def _default_input_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "first_test_data"


def _candidate_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_LIKE_SUFFIXES.union({PDF_SUFFIX})
    )


def _preview_text(text: str, limit: int = PREVIEW_LENGTH) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: max(0, limit - 3)].rstrip()}..."


def _build_unsupported_record(path: Path, engine_name: str) -> dict:
    suffix = path.suffix.lower()
    if suffix == PDF_SUFFIX:
        status = "skipped_pdf_out_of_scope"
        notes = "scanned_pdf_ocr_out_of_scope_stage21"
    else:
        status = "unsupported_image_like"
        notes = "unsupported_image_like_format"

    return {
        "filename": path.name,
        "path": str(path),
        "extension": suffix,
        "ocr_status": status,
        "ocr_used": False,
        "text_length": 0,
        "text_preview": "",
        "engine": engine_name,
        "elapsed_ms": None,
        "notes": notes,
    }


def _build_ocr_record(path: Path, adapter: LocalOCRAdapter) -> dict:
    started = time.perf_counter()
    result = adapter.run(path)
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    text = normalize_text(result.text or "")
    text_length = len(text)
    text_preview = _preview_text(text) if text else ""
    notes = result.reason or result.error or None

    return {
        "filename": path.name,
        "path": str(path),
        "extension": path.suffix.lower(),
        "ocr_status": result.status,
        "ocr_used": bool(result.success and text),
        "text_length": text_length,
        "text_preview": text_preview,
        "engine": result.engine or adapter.engine_name,
        "elapsed_ms": elapsed_ms,
        "notes": notes,
    }


def build_report(input_dir: Path, adapter: LocalOCRAdapter | None = None) -> dict:
    adapter = adapter or LocalOCRAdapter()
    input_dir = input_dir.resolve()
    files = _candidate_files(input_dir)

    records: list[dict] = []
    supported_count = 0
    unsupported_count = 0
    pdf_count = 0

    for path in files:
        suffix = path.suffix.lower()
        if suffix in SUPPORTED_SUFFIXES:
            supported_count += 1
            records.append(_build_ocr_record(path, adapter))
        elif suffix in UNSUPPORTED_SUFFIXES:
            unsupported_count += 1
            records.append(_build_unsupported_record(path, adapter.engine_name))
        elif suffix == PDF_SUFFIX:
            pdf_count += 1
            records.append(_build_unsupported_record(path, adapter.engine_name))

    success_text_lengths = [record["text_length"] for record in records if record["ocr_status"] == "success" and record["ocr_used"]]
    status_counts = Counter(record["ocr_status"] for record in records)

    summary = {
        "total_images_seen": supported_count + unsupported_count,
        "supported_images": supported_count,
        "unsupported_image_like_files": unsupported_count,
        "pdf_files_out_of_scope": pdf_count,
        "ocr_success_count": status_counts.get("success", 0),
        "ocr_empty_count": status_counts.get("empty_text", 0),
        "ocr_failed_count": status_counts.get("failed", 0) + status_counts.get("timeout", 0),
        "ocr_unavailable_count": status_counts.get("engine_unavailable", 0),
        "avg_text_length_success": round(sum(success_text_lengths) / len(success_text_lengths), 2) if success_text_lengths else 0.0,
        "engine_available": adapter.is_available(),
    }

    return {
        "report_version": REPORT_VERSION,
        "input_dir": str(input_dir),
        "engine": adapter.engine_name,
        "engine_available": summary["engine_available"],
        "stage": "Stage 21 OCR smoke evaluation",
        "scope_note": (
            "Read-only smoke/eval layer for OCR readiness, not a production OCR quality guarantee. "
            "Scanned PDF OCR is out of scope for Stage 21."
        ),
        "summary": summary,
        "files": records,
    }


def print_report(report: dict) -> None:
    summary = report["summary"]
    print("OCR smoke/eval report")
    print(f"Input dir: {report['input_dir']}")
    print(f"Engine: {report['engine']} | available: {'yes' if report['engine_available'] else 'no'}")
    print(
        "Summary: total_images_seen={total} supported_images={supported} unsupported_image_like_files={unsupported} "
        "pdf_out_of_scope={pdf} success={success} empty={empty} failed={failed} unavailable={unavailable} "
        "avg_text_length_success={avg}".format(
            total=summary["total_images_seen"],
            supported=summary["supported_images"],
            unsupported=summary["unsupported_image_like_files"],
            pdf=summary["pdf_files_out_of_scope"],
            success=summary["ocr_success_count"],
            empty=summary["ocr_empty_count"],
            failed=summary["ocr_failed_count"],
            unavailable=summary["ocr_unavailable_count"],
            avg=summary["avg_text_length_success"],
        )
    )
    print(report["scope_note"])
    print("Per-file results:")
    for record in report["files"]:
        print(
            "- {filename} | ext={extension} | status={ocr_status} | used={ocr_used} | text_length={text_length} "
            "| preview={text_preview!r} | engine={engine} | elapsed_ms={elapsed_ms} | notes={notes}".format(
                **record
            )
        )
    print("Scanned PDF OCR is out of scope for Stage 21.")
    print("This is a smoke/eval layer, not a production OCR quality guarantee.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a read-only OCR smoke evaluation")
    parser.add_argument(
        "--input-dir",
        help="Directory with sample image files. Defaults to first_test_data when available.",
    )
    parser.add_argument("--json-report-path", help="Optional path to save the JSON OCR smoke report")
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir).resolve() if args.input_dir else _default_input_dir()
    report = build_report(input_dir)
    print_report(report)

    if args.json_report_path:
        report_path = Path(args.json_report_path).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved JSON report to {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
