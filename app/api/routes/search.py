from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.api import SearchRequest, SearchResultOut
from app.services.search import search_chunks

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", response_model=list[SearchResultOut])
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    results = await search_chunks(req.query, db, limit=req.limit)
    return results
