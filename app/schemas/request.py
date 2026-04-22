from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000, description="Natural language question about the document")
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")

    model_config = {"json_schema_extra": {"example": {"question": "What is the refund policy?", "top_k": 5}}}


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    conversation_id: Optional[str] = Field(default=None, description="Pass to continue a conversation. Omit to start new.")

    model_config = {"json_schema_extra": {"example": {"question": "What did you just say about refunds?", "conversation_id": "uuid-here"}}}
