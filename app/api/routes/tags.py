from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.api import TagOut, TagCreate
from app.models.models import Tag

router = APIRouter(prefix="/tags", tags=["Tags"])

@router.get("", response_model=list[TagOut])
async def list_tags(db: AsyncSession = Depends(get_db)):
    stmt = select(Tag).order_by(Tag.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.post("", response_model=TagOut, status_code=201)
async def create_tag(payload: TagCreate, db: AsyncSession = Depends(get_db)):
    name = payload.name.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="Tag name cannot be empty")
        
    tag = Tag(name=name)
    db.add(tag)
    try:
        await db.commit()
        await db.refresh(tag)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tag already exists")
        
    return tag

@router.delete("/{tag_id}", status_code=204)
async def delete_tag(tag_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(Tag).where(Tag.id == tag_id)
    result = await db.execute(stmt)
    tag = result.scalars().first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
        
    await db.delete(tag)
    await db.commit()
    return
