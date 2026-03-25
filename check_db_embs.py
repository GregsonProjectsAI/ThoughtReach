import asyncio
from sqlalchemy import select
from app.models.models import Chunk
from app.db.session import AsyncSessionLocal

async def check_db_embeddings():
    async with AsyncSessionLocal() as db:
        stmt = select(Chunk).where(Chunk.embedding.isnot(None)).limit(20)
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            print("No chunks with embeddings found in the database.")
            return

        print(f"Checking {len(chunks)} chunks for real embeddings...")
        for i, chunk in enumerate(chunks):
            emb = chunk.embedding
            if emb is not None:
                # Check for list or array-like
                try:
                    is_zero = all(v == 0.0 for v in emb)
                    print(f"Chunk {chunk.id}: Is Zero={is_zero}, First 5={emb[:5]}")
                    if not is_zero:
                        print("FOUND REAL EMBEDDING!")
                        return
                except Exception as e:
                    print(f"Error checking chunk {chunk.id}: {e}")

if __name__ == "__main__":
    asyncio.run(check_db_embeddings())
