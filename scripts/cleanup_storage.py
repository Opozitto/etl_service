from __future__ import annotations

import argparse
from pathlib import Path

from app.schemas.document import StructuredDocument
from app.storage.filesystem import FileStorage


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove duplicate stored ETL results by checksum and filename")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete duplicate JSON result files. Without this flag, runs as dry-run.",
    )
    args = parser.parse_args()

    storage = FileStorage()
    seen: dict[tuple[str, str], Path] = {}
    duplicates: list[Path] = []

    for path in storage.list_results():
        document = StructuredDocument.model_validate_json(path.read_text(encoding="utf-8"))
        key = (document.source.checksum_sha256, document.source.filename.lower())
        if key in seen:
            duplicates.append(path)
        else:
            seen[key] = path

    if not duplicates:
        print("No duplicate stored results found.")
        return

    print(f"Found {len(duplicates)} duplicate result files:")
    for path in duplicates:
        print(path)

    if not args.apply:
        print("Dry-run only. Re-run with --apply to delete duplicates.")
        return

    for path in duplicates:
        path.unlink(missing_ok=True)
    print(f"Deleted {len(duplicates)} duplicate result files.")


if __name__ == "__main__":
    main()
