from __future__ import annotations

import argparse
from pathlib import Path

from app.schemas.document import StructuredDocument
from app.storage.filesystem import FileStorage


def main() -> None:
    parser = argparse.ArgumentParser(description="Удалить дубликаты сохранённых ETL results по checksum и filename")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Фактически удалить duplicate JSON result files. Без флага выполняется dry-run.",
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
        print("Дубликаты сохранённых results не найдены.")
        return

    print(f"Найдено duplicate result files: {len(duplicates)}")
    for path in duplicates:
        print(path)

    if not args.apply:
        print("Только dry-run. Повторите с --apply, чтобы удалить дубликаты.")
        return

    for path in duplicates:
        path.unlink(missing_ok=True)
    print(f"Удалено duplicate result files: {len(duplicates)}")


if __name__ == "__main__":
    main()
