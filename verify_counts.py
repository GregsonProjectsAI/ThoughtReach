import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.models import Chunk

async def main():
    async with AsyncSessionLocal() as db:
        total = (await db.execute(select(func.count(Chunk.id)))).scalar()
        null_count = (await db.execute(select(func.count(Chunk.id)).where(Chunk.embedding.is_(None)))).scalar()
        pop_count = (await db.execute(select(func.count(Chunk.id)).where(Chunk.embedding.isnot(None)))).scalar()
        print(f"TOTAL: {total} NULL: {null_count} POPULATED: {pop_count}")

if __name__ == "__main__":
    asyncio.run(main())
