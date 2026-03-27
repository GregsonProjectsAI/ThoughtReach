import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.db.session import AsyncSessionLocal
from app.models.models import Conversation, Message, Chunk

async def validate():
    print("Connecting to database...")
    async with AsyncSessionLocal() as db:
        print("Querying conversations...")
        # Get the most recent conversation (likely the manual test one)
        stmt = select(Conversation).order_by(Conversation.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        conv = result.scalars().first()
        
        if not conv:
            print("No conversations found in database.")
            return

        print(f"\n--- CONVERSATION INTEGRITY ---")
        print(f"ID: {conv.id}")
        print(f"Title: {conv.title}")
        print(f"Source: {conv.source_type}")
        print(f"Created: {conv.created_at}")
        
        # Verify messages
        print(f"\n--- MESSAGE INTEGRITY ---")
        msg_stmt = select(Message).where(Message.conversation_id == conv.id).order_by(Message.message_index)
        msg_result = await db.execute(msg_stmt)
        messages = msg_result.scalars().all()
        print(f"Total Messages: {len(messages)}")
        for m in messages:
            print(f"  [{m.message_index}] Role: {m.role} | Content Length: {len(m.content)}")
            
        # Verify chunks
        print(f"\n--- CHUNK INTEGRITY ---")
        chunk_stmt = select(Chunk).where(Chunk.conversation_id == conv.id).order_by(Chunk.chunk_index)
        chunk_result = await db.execute(chunk_stmt)
        chunks = chunk_result.scalars().all()
        print(f"Total Chunks: {len(chunks)}")
        
        # Check sub-position sequences
        pos_by_msg = {}
        for c in chunks:
            msg_idx = c.message_start_index
            if msg_idx not in pos_by_msg: pos_by_msg[msg_idx] = []
            pos_by_msg[msg_idx].append(c.chunk_position_sub)
            
        for msg_idx, pos in pos_by_msg.items():
            is_seq = all(pos[i] == i for i in range(len(pos)))
            print(f"  Msg {msg_idx}: {len(pos)} chunks | Sequential: {is_seq}")

        # Basic retrieval check (Search for a specific term from the conversation)
        print(f"\n--- RETRIEVAL SANITY ---")
        from app.services.search import search_chunks
        
        # Look for a term in the first message
        test_query = "treasure hunt" # Common in the pirate conversation
        print(f"Searching for: '{test_query}'...")
        search_results = await search_chunks(test_query, db, limit=3)
        print(f"Results Found: {len(search_results)}")
        for r in search_results:
            text = r.get("matched_chunk_text", "").replace("[[", "").replace("]]", "")
            print(f"  - [{r.get('conversation_title')}] {text[:60]}...")

if __name__ == "__main__":
    try:
        asyncio.run(validate())
    except Exception as e:
        print(f"ERROR: {e}")
