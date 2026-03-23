from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.schemas.api import ConversationOut, ConversationCategoryUpdate
from app.models.models import Conversation, Category

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db), limit: int = 50):
    stmt = select(Conversation).options(selectinload(Conversation.category)).order_by(Conversation.imported_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(selectinload(Conversation.messages), selectinload(Conversation.category)).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@router.patch("/{conversation_id}/category", response_model=ConversationOut)
async def update_conversation_category(conversation_id: UUID, payload: ConversationCategoryUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category)
    ).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if payload.category_id is not None:
        cat_stmt = select(Category).where(Category.id == payload.category_id)
        cat_result = await db.execute(cat_stmt)
        cat = cat_result.scalars().first()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
            
    conv.category_id = payload.category_id
    await db.commit()
    await db.refresh(conv)
    
    return conv
