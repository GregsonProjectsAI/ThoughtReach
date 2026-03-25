from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.api import SearchRequest, SearchResultOut
from app.services.search import search_chunks
from app.models.models import Category

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", response_model=list[SearchResultOut])
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    if req.category_id:
        stmt = select(Category).where(Category.id == req.category_id)
        cat = (await db.execute(stmt)).scalar()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
            
    results = await search_chunks(req.query, db, limit=req.limit, category_id=req.category_id)
    return results
