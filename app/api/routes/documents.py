from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.extraction.requirements import build_requirements_report
from app.extraction.tables import build_table_evidence_report
from app.schemas.api import (
    AskRequest,
    AskResponse,
    CorpusStatsResponse,
    DocumentListItem,
    ManifestRecordResponse,
    ProcessResponse,
    ReindexResponse,
    RequirementsResponse,
    SearchRequest,
    SearchResponse,
    TableEvidenceResponse,
)
from app.search.index import CorpusSearchEngine
from app.services.document_service import DocumentService


router = APIRouter(tags=["documents"])
service = DocumentService()
search_engine = CorpusSearchEngine(service.storage)


@router.post("/documents/process", response_model=ProcessResponse)
async def process_document(file: UploadFile = File(...)) -> ProcessResponse:
    suffix = Path(file.filename or "document.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        payload = await file.read()
        tmp.write(payload)
        temp_path = Path(tmp.name)

    try:
        document = service.process_path(temp_path)
        document.source.filename = file.filename or temp_path.name
        service.storage.save_result(document)
        return ProcessResponse(document=document)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)


@router.get("/documents/{document_id}", response_model=ProcessResponse)
def get_document(document_id: str) -> ProcessResponse:
    try:
        document = service.get_document(document_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    return ProcessResponse(document=document)


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents() -> list[DocumentListItem]:
    documents = service.list_documents()
    return [
        DocumentListItem(
            document_id=document.metadata.document_id,
            title=document.metadata.title,
            filename=document.source.filename,
            processed_at=document.metadata.processed_at.isoformat(),
            page_count=document.metadata.page_count,
        )
        for document in documents
    ]


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    hits = search_engine.search(request.query, request.top_k)
    return SearchResponse(query=request.query, hits=hits)


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    return search_engine.ask(
        question=request.question,
        top_k=request.top_k,
        max_sentences=request.max_sentences,
    )


@router.get("/corpus/stats", response_model=CorpusStatsResponse)
def corpus_stats() -> CorpusStatsResponse:
    return CorpusStatsResponse(**service.corpus_stats())


@router.post("/corpus/reindex", response_model=ReindexResponse)
def corpus_reindex() -> ReindexResponse:
    index = service.rebuild_corpus_index()
    return ReindexResponse(
        status="reindexed",
        document_count=index.document_count,
        chunk_count=index.chunk_count,
        updated_at=index.updated_at,
    )


@router.get("/corpus/manifest", response_model=list[ManifestRecordResponse])
def corpus_manifest() -> list[ManifestRecordResponse]:
    return [ManifestRecordResponse(**record) for record in service.manifest_records()]


@router.get("/corpus/requirements", response_model=RequirementsResponse)
def corpus_requirements(
    min_score: float = 0.45,
    max_per_document: int | None = None,
    query: str | None = None,
) -> RequirementsResponse:
    documents = service.list_documents()
    report = build_requirements_report(
        documents=documents,
        results_dir=service.storage.results_dir,
        min_score=min_score,
        max_per_document=max_per_document,
        query=query,
    )
    return RequirementsResponse(**report)


@router.get("/corpus/tables", response_model=TableEvidenceResponse)
def corpus_tables(
    min_score: float = 0.25,
    max_tables: int | None = None,
    category: str | None = None,
) -> TableEvidenceResponse:
    documents = service.list_documents()
    report = build_table_evidence_report(
        documents=documents,
        results_dir=service.storage.results_dir,
        min_score=min_score,
        max_tables=max_tables,
        category=category,
    )
    return TableEvidenceResponse(**report)
