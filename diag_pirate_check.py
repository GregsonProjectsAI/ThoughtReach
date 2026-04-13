"""
Diagnostic: Check if pirate poetry conversation exists and has embeddings.
READ-ONLY — no mutations.
"""
import asyncio
import os
import sys

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.models import Conversation, Chunk, Message

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/thoughtreach")

async def diagnose():
    print(f"Connecting to database...", flush=True)
    engine = create_async_engine(
        DATABASE_URL, 
        echo=False, 
        connect_args={"ssl": False, "timeout": 10}
    )
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as db:
            # Quick connectivity check
            await db.execute(text("SELECT 1"))
            print("Connected successfully.\n", flush=True)

            search_terms = ["pirate", "jingle", "shanty", "poetry"]

            # 1. Search conversations by title
            print("=== SEARCH BY CONVERSATION TITLE ===", flush=True)
            for term in search_terms:
                stmt = select(Conversation.id, Conversation.title, Conversation.source_type).where(
                    Conversation.title.ilike(f"%{term}%")
                )
                rows = (await db.execute(stmt)).all()
                if rows:
                    for r in rows:
                        print(f"  MATCH (title, term='{term}'): id={r[0]}, title='{r[1]}', source_type='{r[2]}'", flush=True)
                else:
                    print(f"  No title match for '{term}'", flush=True)

            # 2. Search chunk text for pirate-related content
            print("\n=== SEARCH BY CHUNK TEXT (first 5 matches per term) ===", flush=True)
            for term in search_terms:
                stmt = (
                    select(Chunk.conversation_id, Chunk.id, func.left(Chunk.chunk_text, 120))
                    .where(Chunk.chunk_text.ilike(f"%{term}%"))
                    .limit(5)
                )
                rows = (await db.execute(stmt)).all()
                if rows:
                    for r in rows:
                        print(f"  CHUNK MATCH (term='{term}'): conv_id={r[0]}, chunk_id={r[1]}", flush=True)
                        print(f"    text preview: {r[2]!r}", flush=True)
                else:
                    print(f"  No chunk text match for '{term}'", flush=True)

            # 3. Search message content
            print("\n=== SEARCH BY MESSAGE CONTENT (first 5 matches per term) ===", flush=True)
            for term in search_terms:
                stmt = (
                    select(Message.conversation_id, Message.id, Message.role, func.left(Message.content, 120))
                    .where(Message.content.ilike(f"%{term}%"))
                    .limit(5)
                )
                rows = (await db.execute(stmt)).all()
                if rows:
                    for r in rows:
                        print(f"  MSG MATCH (term='{term}'): conv_id={r[0]}, msg_id={r[1]}, role={r[2]}", flush=True)
                        print(f"    text preview: {r[3]!r}", flush=True)
                else:
                    print(f"  No message content match for '{term}'", flush=True)

            # 4. Full conversation listing with chunk/embedding counts
            print("\n=== FULL CONVERSATION LISTING (title + chunk/embedding counts) ===", flush=True)
            stmt = (
                select(
                    Conversation.id,
                    Conversation.title,
                    Conversation.source_type,
                    func.count(Chunk.id).label("total_chunks"),
                    func.count(Chunk.embedding).label("embedded_chunks")
                )
                .outerjoin(Chunk, Chunk.conversation_id == Conversation.id)
                .group_by(Conversation.id, Conversation.title, Conversation.source_type)
                .order_by(Conversation.title)
            )
            rows = (await db.execute(stmt)).all()
            print(f"  Total conversations in DB: {len(rows)}", flush=True)
            for r in rows:
                emb_status = "ALL" if r[3] == r[4] and r[3] > 0 else ("NONE" if r[4] == 0 else "PARTIAL")
                print(f"  [{emb_status:7s}] {r[1]:50s} | chunks={r[3]:3d} | embedded={r[4]:3d} | type={r[2]} | id={r[0]}", flush=True)

    except Exception as e:
        print(f"ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

    print("\n=== DIAGNOSIS COMPLETE ===", flush=True)

if __name__ == "__main__":
    asyncio.run(diagnose())
