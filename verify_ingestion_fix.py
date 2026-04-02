
import asyncio
import os
import sys
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv

# Path setup
sys.path.append(os.getcwd())

from app.services.ingestion import ingest_raw_text
from app.db.models import Conversation, Message

async def run_verification():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    print(f"Connecting to: {db_url}")
    
    # We MUST disable SSL because of the local Docker/Windows setup bug
    engine = create_async_engine(db_url, connect_args={"ssl": False})
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    title = "PIRATE-TEST-STEP-128C"
    # Raw pirate text (no speaker markers)
    raw_text = """Ahoy there! What be the plan for the treasure?
We should head to the Skull Island.
Aye, but the map shows a reef in the way!
We have a steady ship, we can pass it."""

    async with AsyncSessionLocal() as db:
        # 1. Clean up old test data to ensure isolation
        print(f"Cleaning up old {title}...")
        existing = await db.execute(select(Conversation).where(Conversation.title == title))
        conv = existing.scalar_one_or_none()
        if conv:
            await db.execute(delete(Conversation).where(Conversation.id == conv.id))
            await db.commit()
            print("Old data deleted.")

        # 2. Perform Fresh Import
        print(f"Importing fresh {title}...")
        conv_id = await ingest_raw_text(db, raw_text, title=title)
        await db.commit()
        print(f"Import complete. Conv ID: {conv_id}")

        # 3. Verify Roles at the Data Layer
        print("\nVerifying roles...")
        stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.message_index.asc())
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        print(f"Total messages imported: {len(messages)}")
        for m in messages:
            print(f"INDEX {m.message_index:02} | ROLE: {m.role:10} | CONTENT: {m.content[:40]}...")
            
        # 4. Success Check
        roles = [m.role for m in messages]
        is_alternating = True
        for i in range(len(roles)-1):
            if roles[i] == roles[i+1]:
                is_alternating = False
                break
        
        if is_alternating and len(messages) >= 2:
            print("\nRESULT: [SUCCESS] Roles alternate correctly (user/assistant).")
        else:
            print(f"\nRESULT: [FAIL] Roles are not alternating correctly. Roles: {roles}")

if __name__ == "__main__":
    try:
        asyncio.run(run_verification())
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {type(e).__name__}: {str(e)}")
        sys.exit(1)
