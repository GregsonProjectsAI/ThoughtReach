import asyncio
import os
import sys

# Ensure the root project directory is in the path for absolute imports
sys.path.append(os.getcwd())

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal
from app.models.models import Conversation
from app.services.embeddings import generate_summary

async def backfill_summaries():
    async with AsyncSessionLocal() as db:
        # Fetch conversations where summary is None
        stmt = select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.summary.is_(None))
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        
        if not conversations:
            print("No conversations need backfilling.")
            return

        print(f"Found {len(conversations)} conversations missing summaries. Starting backfill...")
        
        success_count = 0
        for conv in conversations:
            try:
                # Reconstruct text matching ingestion logic exactly
                full_text = conv.raw_text
                if not full_text and conv.messages:
                    # Sort by message sequence indexing to perfectly recreate source context
                    msgs = sorted(conv.messages, key=lambda m: m.message_index)
                    full_text = "\n".join(f"{m.role}: {m.content}" for m in msgs)
                    
                if not full_text:
                    print(f"Skipping {conv.id}: No text content.")
                    continue
                    
                summary = await generate_summary(full_text)
                
                if summary:
                    # Assign and commit each one individually
                    conv.summary = summary
                    await db.commit()
                    print(f"Updated {conv.id}")
                    success_count += 1
                else:
                    print(f"Skipping {conv.id}: generate_summary yielded None.")
            except Exception as e:
                # Catch silently on an individual record basis & rollback poisoned transaction state
                print(f"Failed {conv.id}: {e}")
                await db.rollback()

        print(f"Backfill complete. Successfully updated {success_count} conversations.")

if __name__ == "__main__":
    urllib3_suppress = True
    try:
        import urllib3
        urllib3.disable_warnings()
    except ImportError:
        pass
        
    asyncio.run(backfill_summaries())
