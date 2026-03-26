import asyncio
import sys
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.models import Conversation, Message, Chunk
from app.core.config import settings

async def verify_ingestion(conversation_id_str: str):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        conv_id = uuid.UUID(conversation_id_str)
    except ValueError:
        print(f"Invalid UUID: {conversation_id_str}")
        return

    async with AsyncSessionLocal() as db:
        # Check conversation
        stmt = select(Conversation).where(Conversation.id == conv_id)
        result = await db.execute(stmt)
        conv = result.scalars().first()
        
        if not conv:
            print(f"Conversation {conv_id} not found.")
            return

        print(f"--- Conversation Verification ---")
        print(f"ID: {conv.id}")
        print(f"Title: {conv.title}")
        print(f"Source: {conv.source_type}")
        print(f"Fingerprint: {conv.content_fingerprint}")
        print(f"Created At: {conv.created_at}")

        # Check messages
        stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.message_index)
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        print(f"\n--- Message Verification ---")
        print(f"Count: {len(messages)}")
        for i, msg in enumerate(messages):
            print(f"[{i}] Role: {msg.role}, Index: {msg.message_index}, Length: {len(msg.content)}")
            if not msg.content.strip():
                print(f"  WARNING: Empty message at index {i}")

        # Check chunks
        stmt = select(Chunk).where(Chunk.conversation_id == conv_id).order_by(Chunk.chunk_index)
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        print(f"\n--- Chunk Verification ---")
        print(f"Count: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]): # Show first 3
            safe_text = chunk.chunk_text[:50].replace("\n", " ") + "..."
            print(f"Chunk {chunk.chunk_index}: {safe_text}")

        for chunk in chunks:
            if not chunk.chunk_text.strip():
                print(f"  WARNING: Empty chunk at index {chunk.chunk_index}")

    await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_step_84.py <conversation_id>")
        sys.exit(1)
    
    asyncio.run(verify_ingestion(sys.argv[1]))
