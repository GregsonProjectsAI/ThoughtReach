import asyncio, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.models import Conversation, Chunk

DB = os.getenv("DATABASE_URL")
eng = create_async_engine(DB, echo=False, connect_args={"ssl": False})
ses = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with ses() as db:
        # 1. Find chunks containing "Captain" and "Code"
        stmt = (select(Chunk.conversation_id, Conversation.title)
                .join(Conversation, Chunk.conversation_id == Conversation.id)
                .where(Chunk.chunk_text.ilike("%captain%code%"))
                .distinct()
                .limit(10))
        rows = (await db.execute(stmt)).all()
        print("=== CONVERSATIONS WITH 'captain...code' IN CHUNKS ===", flush=True)
        for r in rows:
            print(f"  conv_id={r[0]} | title={r[1]}", flush=True)
        if not rows:
            print("  NONE FOUND", flush=True)

        # 2. Search for "Smuggler"
        stmt2 = (select(Chunk.conversation_id, Conversation.title)
                 .join(Conversation, Chunk.conversation_id == Conversation.id)
                 .where(Chunk.chunk_text.ilike("%smuggler%"))
                 .distinct()
                 .limit(10))
        rows2 = (await db.execute(stmt2)).all()
        print("\n=== CONVERSATIONS WITH 'smuggler' IN CHUNKS ===", flush=True)
        for r in rows2:
            print(f"  conv_id={r[0]} | title={r[1]}", flush=True)
        if not rows2:
            print("  NONE FOUND", flush=True)

        # 3. Search for "fragment F1" or "Fragment F1"
        stmt3q = (select(Chunk.conversation_id, Conversation.title)
                  .join(Conversation, Chunk.conversation_id == Conversation.id)
                  .where(Chunk.chunk_text.ilike("%fragment f1%"))
                  .distinct()
                  .limit(10))
        rows3q = (await db.execute(stmt3q)).all()
        print("\n=== CONVERSATIONS WITH 'fragment f1' IN CHUNKS ===", flush=True)
        for r in rows3q:
            print(f"  conv_id={r[0]} | title={r[1]}", flush=True)
        if not rows3q:
            print("  NONE FOUND", flush=True)

        # 4. Search for "location sheet"
        stmt4q = (select(Chunk.conversation_id, Conversation.title)
                  .join(Conversation, Chunk.conversation_id == Conversation.id)
                  .where(Chunk.chunk_text.ilike("%location sheet%"))
                  .distinct()
                  .limit(10))
        rows4q = (await db.execute(stmt4q)).all()
        print("\n=== CONVERSATIONS WITH 'location sheet' IN CHUNKS ===", flush=True)
        for r in rows4q:
            print(f"  conv_id={r[0]} | title={r[1]}", flush=True)
        if not rows4q:
            print("  NONE FOUND", flush=True)

        # 5. Full conversation listing
        stmt5 = (select(Conversation.id, Conversation.title, Conversation.source_type,
                        func.count(Chunk.id).label("chunks"),
                        func.count(Chunk.embedding).label("embedded"))
                 .outerjoin(Chunk, Chunk.conversation_id == Conversation.id)
                 .group_by(Conversation.id, Conversation.title, Conversation.source_type)
                 .order_by(func.count(Chunk.id).desc()))
        rows5 = (await db.execute(stmt5)).all()
        print(f"\n=== ALL CONVERSATIONS ({len(rows5)} total) ===", flush=True)
        for r in rows5:
            print(f"  [{r[2]:10s}] chunks={r[3]:4d} emb={r[4]:4d} | {r[1]} | {r[0]}", flush=True)

    await eng.dispose()
    print("\nDONE", flush=True)

asyncio.run(main())
