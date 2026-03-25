import asyncio
from sqlalchemy import select
from app.models.models import Chunk
from app.db.session import AsyncSessionLocal
from app.services.embeddings import generate_embeddings

async def backfill():
    async with AsyncSessionLocal() as db:
        # Identify chunks with null or zero embeddings
        stmt = select(Chunk)
        result = await db.execute(stmt)
        all_chunks = result.scalars().all()
        
        targets = []
        for c in all_chunks:
            if c.embedding is None:
                targets.append(c)
            else:
                # Handle both list and numpy-like objects
                is_zero = all(v == 0.0 for v in c.embedding)
                if is_zero:
                    targets.append(c)
        
        total_found = len(targets)
        print(f"Total chunks targeted for backfill: {total_found}")
        
        if total_found == 0:
            print("No chunks need backfilling.")
            return

        batch_size = 10 # Small batch for safety
        updated_count = 0
        
        for i in range(0, total_found, batch_size):
            batch = targets[i:i+batch_size]
            texts = [c.chunk_text for c in batch]
            
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} chunks)...")
            
            try:
                new_embs = await generate_embeddings(texts)
                
                if not new_embs or len(new_embs) != len(batch):
                    print(f"Error: generate_embeddings returned {len(new_embs) if new_embs else 0} embeddings for {len(batch)} texts.")
                    continue
                
                for chunk, emb in zip(batch, new_embs):
                    if all(v == 0.0 for v in emb):
                        print(f"Warning: Received zero-vector for chunk {chunk.id}. Quota may be hit again.")
                        continue
                        
                    chunk.embedding = emb
                    updated_count += 1
                
                await db.commit()
                print(f"Batch committed. Total updated: {updated_count}/{total_found}")
                
            except Exception as e:
                print(f"Exception during batch processing: {e}")
                await db.rollback()

        print(f"\n--- Backfill Summary ---")
        print(f"Chunks Targeted: {total_found}")
        print(f"Chunks Successfully Updated: {updated_count}")
        
        if updated_count > 0:
            # Re-fetch one to verify
            verify_stmt = select(Chunk).where(Chunk.id == targets[0].id)
            v_res = await db.execute(verify_stmt)
            v_chunk = v_res.scalar()
            
            is_zero = all(v == 0.0 for v in v_chunk.embedding)
            print(f"Final Verification - Chunk {v_chunk.id}:")
            print(f"  Is Zero: {is_zero}")
            print(f"  First 5: {v_chunk.embedding[:5]}")

if __name__ == "__main__":
    asyncio.run(backfill())
