from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.schemas.document import StructuredDocument


class FileStorage:
    def __init__(self, base_dir: Path | None = None, storage_root: Path | None = None) -> None:
        if base_dir is not None and storage_root is not None:
            raise ValueError("Use either base_dir or storage_root, not both")
        self.settings = get_settings()
        requested_base_dir = storage_root if storage_root is not None else base_dir
        self.base_dir = requested_base_dir.resolve() if requested_base_dir is not None else self.settings.resolved_storage_dir
        self.uploads_dir = self.base_dir / self.settings.uploads_dir_name
        self.results_dir = self.base_dir / self.settings.results_dir_name
        self.index_dir = self.base_dir / self.settings.index_dir_name
        self.corpus_index_path = self.index_dir / "corpus_index.json"
        for path in (self.base_dir, self.uploads_dir, self.results_dir, self.index_dir):
            path.mkdir(parents=True, exist_ok=True)

    def compute_checksum(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with path.open("rb") as file_obj:
            while chunk := file_obj.read(1024 * 1024):
                sha256.update(chunk)
        return sha256.hexdigest()

    def save_source(self, source_path: Path, document_id: str) -> Path:
        target = self.uploads_dir / f"{document_id}{source_path.suffix.lower()}"
        shutil.copy2(source_path, target)
        return target

    def save_result(self, document: StructuredDocument) -> Path:
        target = self.results_dir / f"{document.metadata.document_id}.json"
        target.write_text(
            json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def load_result(self, document_id: str) -> StructuredDocument:
        path = self.results_dir / f"{document_id}.json"
        return StructuredDocument.model_validate_json(path.read_text(encoding="utf-8"))

    def list_results(self) -> list[Path]:
        return sorted(self.results_dir.glob("*.json"))

    def find_by_checksum(self, checksum: str) -> Optional[StructuredDocument]:
        for path in self.list_results():
            document = StructuredDocument.model_validate_json(path.read_text(encoding="utf-8"))
            if document.source.checksum_sha256 == checksum:
                return document
        return None

    def write_json(self, path: Path, payload: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=path.parent,
            suffix=".tmp",
        ) as tmp:
            json.dump(payload, tmp, ensure_ascii=False, indent=2)
            temp_path = Path(tmp.name)
        last_error = None
        for _ in range(10):
            try:
                os.replace(temp_path, path)
                return path
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.1)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if last_error is not None:
            raise last_error
        return path

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
