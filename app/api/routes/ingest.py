from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from app.db.session import get_db
from app.services.ingestion import ingest_paste_direct

router = APIRouter(prefix="/ingest", tags=["Ingest"])


class PasteIngestRequest(BaseModel):
    title: Optional[str] = "Untitled Conversation"
    raw_text: str
    category_id: Optional[str] = None
    source_type: str = "structured"


class PasteIngestResponse(BaseModel):
    status: str
    conversation_id: Optional[str] = None
    message: str


@router.post("/paste", response_model=PasteIngestResponse)
async def ingest_paste(
    request: PasteIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    if not request.raw_text or not request.raw_text.strip():
        raise HTTPException(status_code=422, detail="raw_text cannot be empty")

    title = (request.title or "Untitled Conversation").strip() or "Untitled Conversation"
    was_ingested, conversation_id = await ingest_paste_direct(
        title=title, 
        raw_text=request.raw_text, 
        db=db,
        category_id=request.category_id,
        source_type=request.source_type
    )

    if not was_ingested:
        return PasteIngestResponse(
            status="skipped",
            conversation_id=None,
            message="Duplicate content — ingestion skipped"
        )

    return PasteIngestResponse(
        status="ingested",
        conversation_id=conversation_id,
        message="Conversation ingested successfully"
    )
