import asyncio
from sqlalchemy import select
from app.models.models import Chunk, Conversation
from app.db.session import AsyncSessionLocal

async def explore():
    async with AsyncSessionLocal() as db:
        stmt = select(Chunk, Conversation).join(Conversation).limit(20)
        result = await db.execute(stmt)
        rows = result.all()
        
        for chunk, conv in rows:
            print(f"ID: {chunk.id}")
            print(f"CONV: {conv.title}")
            print(f"TEXT: {chunk.chunk_text[:150]}...")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(explore())
