from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import datetime
import os
import time
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.document import StructuredDocument
from app.storage.filesystem import FileStorage


class IndexedChunk(BaseModel):
    document_id: str
    source_checksum: str
    filename: str
    title: str
    chunk_id: str
    section_id: Optional[str] = None
    section_title: Optional[str] = None
    text: str
    tokens: list[str] = Field(default_factory=list)
    normalized_tokens: list[str] = Field(default_factory=list)
    token_count: int


class CorpusIndex(BaseModel):
    version: str = "1"
    updated_at: str
    document_count: int
    chunk_count: int
    avg_chunk_length: float
    doc_frequencies: dict[str, int] = Field(default_factory=dict)
    entries: list[IndexedChunk] = Field(default_factory=list)


class SearchIndexStore:
    def __init__(self, storage: Optional[FileStorage] = None) -> None:
        self.storage = storage or FileStorage()
        self.lock_path = self.storage.index_dir / "corpus_index.lock"

    def exists(self) -> bool:
        return self.storage.corpus_index_path.exists()

    def load(self) -> CorpusIndex:
        if not self.exists():
            return self.rebuild()
        try:
            return CorpusIndex.model_validate(self.storage.read_json(self.storage.corpus_index_path))
        except Exception:
            return self.rebuild()

    def save(self, index: CorpusIndex) -> CorpusIndex:
        self.storage.write_json(self.storage.corpus_index_path, index.model_dump(mode="json"))
        return index

    def rebuild(self) -> CorpusIndex:
        with self._locked():
            documents = [
                StructuredDocument.model_validate_json(path.read_text(encoding="utf-8"))
                for path in self.storage.list_results()
            ]
            entries: list[IndexedChunk] = []
            seen_chunks: set[tuple[str, str, Optional[str], str]] = set()

            for document in documents:
                section_titles = {section.section_id: section.title for section in document.sections}
                for chunk in document.chunks:
                    tokens = self._tokenize(chunk.text)
                    normalized_tokens = self._normalize_tokens(chunk.text)
                    if not tokens:
                        continue
                    dedupe_key = (
                        document.source.filename.lower(),
                        document.source.checksum_sha256,
                        chunk.section_id,
                        self._normalize_for_match(chunk.text[:200]),
                    )
                    if dedupe_key in seen_chunks:
                        continue
                    seen_chunks.add(dedupe_key)
                    entries.append(
                        IndexedChunk(
                            document_id=document.metadata.document_id,
                            source_checksum=document.source.checksum_sha256,
                            filename=document.source.filename,
                            title=document.metadata.title,
                            chunk_id=chunk.chunk_id,
                            section_id=chunk.section_id,
                            section_title=section_titles.get(chunk.section_id),
                            text=chunk.text,
                            tokens=tokens,
                            normalized_tokens=normalized_tokens,
                            token_count=len(tokens),
                        )
                    )

            doc_frequencies: Counter[str] = Counter()
            for entry in entries:
                doc_frequencies.update(set(entry.normalized_tokens))

            unique_sources = {(entry.source_checksum, entry.filename.lower()) for entry in entries}
            avg_chunk_length = sum(entry.token_count for entry in entries) / max(len(entries), 1)
            index = CorpusIndex(
                updated_at=datetime.utcnow().isoformat(),
                document_count=len(unique_sources),
                chunk_count=len(entries),
                avg_chunk_length=avg_chunk_length,
                doc_frequencies=dict(doc_frequencies),
                entries=entries,
            )
            return self.save(index)

    def upsert_document(self, document: StructuredDocument) -> CorpusIndex:
        with self._locked():
            if self.exists():
                try:
                    index = CorpusIndex.model_validate(self.storage.read_json(self.storage.corpus_index_path))
                except Exception:
                    index = CorpusIndex(
                        updated_at=datetime.utcnow().isoformat(),
                        document_count=0,
                        chunk_count=0,
                        avg_chunk_length=0.0,
                        doc_frequencies={},
                        entries=[],
                    )
            else:
                index = CorpusIndex(
                    updated_at=datetime.utcnow().isoformat(),
                    document_count=0,
                    chunk_count=0,
                    avg_chunk_length=0.0,
                    doc_frequencies={},
                    entries=[],
                )

            remaining = [
                entry
                for entry in index.entries
                if not (
                    entry.source_checksum == document.source.checksum_sha256
                    and entry.filename.lower() == document.source.filename.lower()
                )
            ]

            section_titles = {section.section_id: section.title for section in document.sections}
            new_entries: list[IndexedChunk] = []
            for chunk in document.chunks:
                tokens = self._tokenize(chunk.text)
                normalized_tokens = self._normalize_tokens(chunk.text)
                if not tokens:
                    continue
                new_entries.append(
                    IndexedChunk(
                        document_id=document.metadata.document_id,
                        source_checksum=document.source.checksum_sha256,
                        filename=document.source.filename,
                        title=document.metadata.title,
                        chunk_id=chunk.chunk_id,
                        section_id=chunk.section_id,
                        section_title=section_titles.get(chunk.section_id),
                        text=chunk.text,
                        tokens=tokens,
                        normalized_tokens=normalized_tokens,
                        token_count=len(tokens),
                    )
                )

            index.entries = remaining + new_entries
            index.updated_at = datetime.utcnow().isoformat()
            index.chunk_count = len(index.entries)
            unique_sources = {(entry.source_checksum, entry.filename.lower()) for entry in index.entries}
            index.document_count = len(unique_sources)
            index.avg_chunk_length = sum(entry.token_count for entry in index.entries) / max(len(index.entries), 1)

            doc_frequencies: Counter[str] = Counter()
            for entry in index.entries:
                doc_frequencies.update(set(entry.normalized_tokens))
            index.doc_frequencies = dict(doc_frequencies)
            return self.save(index)

    @contextmanager
    def _locked(self, timeout_seconds: float = 10.0):
        start = time.time()
        handle = None
        while handle is None:
            try:
                handle = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except FileExistsError:
                if time.time() - start > timeout_seconds:
                    raise TimeoutError("Timed out waiting for corpus index lock")
                time.sleep(0.1)
        try:
            yield
        finally:
            os.close(handle)
            self.lock_path.unlink(missing_ok=True)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        from app.search.index import tokenize

        return tokenize(text)

    @staticmethod
    def _normalize_for_match(text: str) -> str:
        from app.search.index import normalize_for_match

        return normalize_for_match(text)

    @staticmethod
    def _normalize_tokens(text: str) -> list[str]:
        from app.search.index import normalize_search_tokens

        return normalize_search_tokens(text)
