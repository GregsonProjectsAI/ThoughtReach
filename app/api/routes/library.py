from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.db.session import get_db
from app.models.models import Conversation

router = APIRouter(prefix="/library", tags=["Library"])


class LibraryItemOut(BaseModel):
    id: UUID
    title: str
    source_type: str
    imported_at: datetime
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[LibraryItemOut])
async def list_library(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, le=500),
):
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.category))
        .order_by(Conversation.imported_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    convs = result.scalars().all()

    items = []
    for c in convs:
        items.append(LibraryItemOut(
            id=c.id,
            title=c.title,
            source_type=c.source_type,
            imported_at=c.imported_at,
            category_id=c.category_id,
            category_name=c.category.name if c.category else None,
        ))
    return items
