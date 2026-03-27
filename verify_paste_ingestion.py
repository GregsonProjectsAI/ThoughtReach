import asyncio
import os
import sys
from sqlalchemy import select

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.db.session import AsyncSessionLocal
from app.services.ingestion import ingest_paste_direct
from app.models.models import Conversation, Message, Chunk
from sqlalchemy import text as sa_text

TEST_CONTENT = """User: Hello, I'm starting a new pirate adventure.
Can you help me?

Assistant: 🎬 HOOK — THE PIRATE'S CHALLENGE
The wind blows hard, the sails pull tight.

Search the bedroom for the first clue.

User: I am in the bedroom. What do I do?

Assistant: 🗝️ KEY PATH
You must find the Captain's Code near the table.
"""

async def validate():
    print("Connecting to database...")
    async with AsyncSessionLocal() as db:
        # Cleanup old test
        await db.execute(sa_text("DELETE FROM chunks WHERE chunk_text LIKE '%PIRATE%' OR chunk_text LIKE '%HOOK%'"))
        await db.execute(sa_text("DELETE FROM messages WHERE content LIKE '%PIRATE%' OR content LIKE '%HOOK%'"))
        await db.execute(sa_text("DELETE FROM conversations WHERE title = 'Step 105 Validation'"))
        await db.commit()

        print("Executing ingest_paste_direct...")
        success, conv_id = await ingest_paste_direct("Step 105 Validation", TEST_CONTENT, db)
        if not success:
            print("  Ingestion failed (likely duplicate).")
            return
        
        await db.commit()
        print(f"  Ingested successfully. Conv ID: {conv_id}")

        # 1. Verify Conversation
        conv = await db.get(Conversation, conv_id)
        print(f"\n--- CONVERSATION CHECK ---")
        print(f"Title: {conv.title}")
        print(f"Fingerprint: {conv.content_fingerprint[:16]}...")

        # 2. Verify Messages
        msg_stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.message_index)
        msg_result = await db.execute(msg_stmt)
        messages = msg_result.scalars().all()
        print(f"\n--- MESSAGE CHECK ---")
        print(f"Total Messages: {len(messages)} (Expected: 4)")
        for m in messages:
            print(f"  [{m.message_index}] Role: {m.role} | First 30: {repr(m.content[:30])}")

        # 3. Verify Chunks
        chunk_stmt = select(Chunk).where(Chunk.conversation_id == conv_id).order_by(Chunk.chunk_index)
        chunk_result = await db.execute(chunk_stmt)
        chunks = chunk_result.scalars().all()
        print(f"\n--- CHUNK CHECK ---")
        print(f"Total Chunks: {len(chunks)}")
        
        # Detail check for Header-Aware Merge
        # Msg 1 (Assistant) should have 2 chunks now because of \n\n split, 
        # but the FIRST paragraph has a header that should be merged with its following text.
        # Wait, Paragraph 1 is "🎬 HOOK — THE PIRATE'S CHALLENGE\nThe wind blows hard..."
        # Rule 1 (Paragraphs) splits on \n\n.
        # Segments for Msg 1:
        # 1. "🎬 HOOK — THE PIRATE'S CHALLENGE\nThe wind blows hard, the sails pull tight."
        # 2. "Search the bedroom for the first clue."
        #
        # Rule 2 (Line split) fires if len > 400. Not here.
        # Merge phase: Segment 1 (60+ chars likely).
        # "🎬 HOOK — THE PIRATE'S CHALLENGE" is 35 chars.
        # But wait, Rule 1 in ingestion.py splits on \n\n.
        # So Segment 1 IS "🎬 HOOK — THE PIRATE'S CHALLENGE\nThe wind blows hard...". 
        # This segment is ALREADY combined because it was only a SINGLE newline.
        #
        # Let's check Msg 3: "🗝️ KEY PATH\nYou must find the Captain's Code near the table."
        # Segment 1 for Msg 3 is one block.
        #
        # Actually, let's use DOUBLE newline in the test text to force R1 merge check.
        
        for c in chunks:
            print(f"  Chunk {c.chunk_index} (Msg {c.message_start_index}, Sub {c.chunk_position_sub}):")
            print(f"    Text: {repr(c.chunk_text)}")

        # 4. Retrieval Sanity
        from app.services.search import search_chunks
        print(f"\n--- RETRIEVAL SANITY ---")
        query = "PIRATE'S CHALLENGE"
        results = await search_chunks(query, db, limit=1)
        if results:
             text = results[0].get("matched_chunk_text", "").replace("[[", "").replace("]]", "")
             print(f"Search for '{query}' returned: {repr(text)}")
        else:
             print(f"Search for '{query}' returned NO results.")

if __name__ == "__main__":
    asyncio.run(validate())
