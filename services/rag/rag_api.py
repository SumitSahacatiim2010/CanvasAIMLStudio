"""RAG REST API — endpoints for document management, search, and Q&A.

Exposes the full RAG pipeline: ingest → chunk → index → search → generate.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel, Field

from services.gateway.app.auth import CurrentUser, Role, get_current_user, require_roles
from services.rag.ingestion import DocumentIngestionService
from services.rag.chunking import chunk_document
from services.rag.search import HybridSearchEngine
from services.rag.generation import RAGGenerator

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Knowledge Base"])

# ── Singleton Services ───────────────────────────────────
_ingestion = DocumentIngestionService()
_search_engine = HybridSearchEngine()
_generator = RAGGenerator()


# ── Pydantic Models ──────────────────────────────────────

class TextIngestRequest(BaseModel):
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=10)
    chunking_strategy: str = Field(default="recursive", pattern="^(recursive|semantic|structure)$")
    chunk_size: int = Field(default=1024, ge=128, le=8192)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    methods: list[str] = Field(default=["dense", "sparse"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=20)
    system_prompt: str | None = None


# ── Ingest Endpoints ─────────────────────────────────────


@router.post("/ingest/text", status_code=status.HTTP_201_CREATED)
async def ingest_text(
    req: TextIngestRequest,
    user: CurrentUser = Depends(require_roles(Role.DATA_ENGINEER, Role.PLATFORM_ADMIN)),
) -> dict[str, Any]:
    """Ingest raw text into the RAG knowledge base."""
    # Ingest document
    doc = _ingestion.ingest_text(req.text, req.title, req.metadata)

    # Chunk
    chunks = chunk_document(
        doc.raw_text, doc.doc_id,
        strategy=req.chunking_strategy,
        chunk_size=req.chunk_size,
        metadata={"title": req.title, **req.metadata},
    )

    # Index
    index_result = _search_engine.index_chunks(chunks)

    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "chunks_created": len(chunks),
        "indexed": index_result,
        "total_index_size": _search_engine.index_size,
    }


@router.get("/documents")
async def list_documents(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List all ingested documents."""
    docs = _ingestion.list_documents()
    return {
        "documents": [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "doc_type": d.doc_type.value,
                "word_count": d.metadata.get("word_count", 0),
                "status": d.status.value,
                "ingested_at": d.ingested_at.isoformat(),
            }
            for d in docs
        ],
        "total": len(docs),
    }


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get document details."""
    doc = _ingestion.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "doc_type": doc.doc_type.value,
        "metadata": doc.metadata,
        "page_count": doc.page_count,
        "status": doc.status.value,
        "text_preview": doc.raw_text[:500] + "..." if len(doc.raw_text) > 500 else doc.raw_text,
    }


# ── Search Endpoints ─────────────────────────────────────


@router.post("/search")
async def search_knowledge_base(
    req: SearchRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Search the knowledge base using hybrid retrieval."""
    response = _search_engine.search(
        query=req.query,
        top_k=req.top_k,
        methods=req.methods,
    )
    return {
        "query": response.query,
        "results": [
            {
                "chunk_id": r.chunk_id,
                "doc_id": r.doc_id,
                "text": r.text,
                "score": r.score,
                "rank": r.rank,
                "heading": r.heading,
                "section": r.section,
                "page_number": r.page_number,
            }
            for r in response.results
        ],
        "total_results": response.total_results,
        "methods": response.retrieval_methods_used,
        "fusion": response.fusion_method,
        "search_time_ms": response.search_time_ms,
    }


# ── Q&A Endpoint ─────────────────────────────────────────


@router.post("/ask")
async def ask_question(
    req: AskRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Ask a question and get an AI-generated answer with citations."""
    # Search
    search_response = _search_engine.search(query=req.question, top_k=req.top_k)

    # Generate
    answer = _generator.generate(
        query=req.question,
        search_results=search_response.results,
        system_prompt=req.system_prompt,
    )

    return {
        "question": answer.query,
        "answer": answer.answer,
        "confidence": answer.confidence,
        "citations": [
            {
                "id": c.citation_id,
                "doc_id": c.doc_id,
                "excerpt": c.text_excerpt,
                "heading": c.heading,
                "page": c.page_number,
            }
            for c in answer.citations
        ],
        "follow_up_questions": answer.follow_up_questions,
        "model": answer.model_used,
        "retrieval_count": answer.retrieval_count,
        "generation_time_ms": answer.generation_time_ms,
        "search_time_ms": search_response.search_time_ms,
    }


# ── Index Stats ──────────────────────────────────────────


@router.get("/stats")
async def get_rag_stats(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get RAG system statistics."""
    docs = _ingestion.list_documents()
    return {
        "total_documents": len(docs),
        "total_chunks_indexed": _search_engine.index_size,
        "documents_by_type": _count_by(docs, lambda d: d.doc_type.value),
        "documents_by_status": _count_by(docs, lambda d: d.status.value),
    }


def _count_by(items: list, key_fn: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        k = key_fn(item)
        counts[k] = counts.get(k, 0) + 1
    return counts
