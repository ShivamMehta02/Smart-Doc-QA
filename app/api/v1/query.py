from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db import crud
from app.db.models import DocumentStatus
from app.schemas.request import QueryRequest
from app.schemas.response import QueryResponse, SourceReference
from app.services import retrieval_service, llm_service, validation_service
from app.core.exceptions import DocumentNotFoundError, DocumentNotReadyError, NoAnswerFoundError, AppBaseException
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Query"])

@router.post("/{doc_id}/query", response_model=QueryResponse)
async def query_document(
    doc_id: str,
    payload: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a one-shot question about a specific document.
    
    1. Retrieval: Finds semantically similar chunks.
    2. Re-ranking: Optimizes the order of chunks.
    3. LLM Call: Generates a grounded answer.
    4. Validation: Checks for hallucinations and computes confidence.
    """
    try:
        doc = await crud.get_document(db, doc_id)
        if not doc:
            raise DocumentNotFoundError(doc_id)
        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyError(doc_id, doc.status)

        # Step 1 & 2: Retrieval + Re-ranking
        raw_results = retrieval_service.retrieve_chunks(doc_id, payload.question, top_k=payload.top_k)
        
        # Hydrate results with text from DB
        db_chunks = await crud.get_chunks_by_doc(db, doc_id)
        chunk_map = {str(c.id): c for c in db_chunks}
        
        candidates = []
        for cid, score in raw_results:
            if cid in chunk_map:
                c = chunk_map[cid]
                candidates.append({
                    "chunk_id": cid,
                    "text": c.text,
                    "page": c.page,
                    "score": score
                })

        if not candidates:
            raise NoAnswerFoundError()

        # Step 2: Re-ranking
        ranked_chunks = retrieval_service.rerank_results(payload.question, candidates)

        # Step 3: LLM Call
        llm_out = await llm_service.call_llm(payload.question, ranked_chunks)
        
        # Step 4: Validation & Confidence
        final_answer, confidence, is_fallback = validation_service.validate_and_score(
            llm_out["answer"], ranked_chunks, ranked_chunks[0].get("rerank_score", ranked_chunks[0]["score"])
        )

        # Format sources
        sources = [
            SourceReference(
                chunk_id=c["chunk_id"],
                doc_id=doc_id,
                page=c["page"],
                text_snippet=c["text"][:200] + "..."
            ) for c in ranked_chunks[:3]
        ]

        logger.info("query_completed", doc_id=doc_id, confidence=confidence)
        return QueryResponse(
            answer=final_answer,
            confidence=confidence,
            sources=sources,
            fallback=is_fallback,
            question=payload.question
        )

    except AppBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error("query_failed", doc_id=doc_id, error=str(e))
        raise HTTPException(status_code=500, detail="An internal error occurred during query processing.")
