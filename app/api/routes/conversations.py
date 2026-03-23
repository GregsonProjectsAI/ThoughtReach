from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.schemas.api import ConversationOut
from app.models.models import Conversation

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db), limit: int = 50):
    stmt = select(Conversation).order_by(Conversation.imported_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv
