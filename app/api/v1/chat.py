from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db import crud
from app.db.models import DocumentStatus
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse, SourceReference
from app.services import retrieval_service, llm_service, validation_service
from app.core.exceptions import DocumentNotFoundError, ConversationNotFoundError, AppBaseException
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Chat"])

@router.post("/{doc_id}/chat", response_model=ChatResponse)
async def chat_with_document(
    doc_id: str,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Conversational Q&A.
    - If conversation_id is provided, fetches history.
    - If not, starts a new conversation.
    - Updates history after every turn.
    """
    try:
        doc = await crud.get_document(db, doc_id)
        if not doc:
            raise DocumentNotFoundError(doc_id)

        # 1. Get or Create Conversation
        if payload.conversation_id:
            conv = await crud.get_conversation(db, payload.conversation_id)
            if not conv:
                raise ConversationNotFoundError(payload.conversation_id)
            conv_id = str(conv.id)
            history = conv.messages
        else:
            conv = await crud.create_conversation(db, doc_id)
            conv_id = str(conv.id)
            history = []

        # 2. Retrieval + Rerank
        raw_results = retrieval_service.retrieve_chunks(doc_id, payload.question)
        db_chunks = await crud.get_chunks_by_doc(db, doc_id)
        chunk_map = {str(c.id): c for c in db_chunks}
        
        candidates = []
        for cid, score in raw_results:
            if cid in chunk_map:
                c = chunk_map[cid]
                candidates.append({"chunk_id": cid, "text": c.text, "page": c.page, "score": score})

        ranked_chunks = retrieval_service.rerank_results(payload.question, candidates)

        # 3. LLM Call with History
        llm_out = await llm_service.call_llm(payload.question, ranked_chunks, history=history)

        # 4. Validation
        final_answer, confidence, is_fallback = validation_service.validate_and_score(
            llm_out["answer"], ranked_chunks, ranked_chunks[0].get("rerank_score", 0.5) if ranked_chunks else 0.0
        )

        # 5. Persist History
        await crud.append_message(db, conv_id, role="user", content=payload.question)
        await crud.append_message(
            db, conv_id, role="assistant", content=final_answer, 
            sources=[c["chunk_id"] for c in ranked_chunks[:3]], 
            confidence=confidence
        )
        await db.commit()

        return ChatResponse(
            answer=final_answer,
            confidence=confidence,
            sources=[SourceReference(chunk_id=c["chunk_id"], doc_id=doc_id, page=c["page"], text_snippet=c["text"][:200]) for c in ranked_chunks[:3]],
            fallback=is_fallback,
            conversation_id=conv_id,
            question=payload.question
        )

    except AppBaseException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
