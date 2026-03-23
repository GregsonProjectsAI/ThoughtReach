from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.schemas.api import ConversationOut, ConversationCategoryUpdate, ConversationTagsUpdate
from app.models.models import Conversation, Category, Tag, conversation_tags

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    tag_ids: list[UUID] = Query(default=[]),
    category_ids: list[UUID] = Query(default=[])
):
    stmt = select(Conversation).options(
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    )
    
    if category_ids:
        stmt = stmt.where(Conversation.category_id.in_(category_ids))
    
    if tag_ids:
        stmt = stmt.join(conversation_tags).where(conversation_tags.c.tag_id.in_(tag_ids)).distinct()
    
    stmt = stmt.order_by(Conversation.imported_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    ).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@router.patch("/{conversation_id}/category", response_model=ConversationOut)
async def update_conversation_category(conversation_id: UUID, payload: ConversationCategoryUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
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

@router.put("/{conversation_id}/tags", response_model=ConversationOut)
async def update_conversation_tags(conversation_id: UUID, payload: ConversationTagsUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    ).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    tags = []
    if payload.tag_ids:
        tags_stmt = select(Tag).where(Tag.id.in_(payload.tag_ids))
        tags_result = await db.execute(tags_stmt)
        tags = list(tags_result.scalars().all())
        
        # Verify all provided tag IDs exist natively
        if len(tags) != len(set(payload.tag_ids)):
            raise HTTPException(status_code=404, detail="One or more tags not found")
            
    conv.tags = tags
    await db.commit()
    await db.refresh(conv)
    
    return conv
