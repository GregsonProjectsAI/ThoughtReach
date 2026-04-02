import asyncio
from sqlalchemy import select, delete, func
from app.db.session import AsyncSessionLocal
from app.models.models import Conversation, Message, Chunk, conversation_tags

async def wipe():
    async with AsyncSessionLocal() as db:
        # Count before
        convs = (await db.execute(select(func.count(Conversation.id)))).scalar()
        msgs = (await db.execute(select(func.count(Message.id)))).scalar()
        chunks = (await db.execute(select(func.count(Chunk.id)))).scalar()
        print(f"Before wiping - Conversations: {convs}, Messages: {msgs}, Chunks: {chunks}")

        # Wipe tables
        await db.execute(delete(Chunk))
        await db.execute(delete(Message))
        await db.execute(delete(conversation_tags))
        await db.execute(delete(Conversation))
        await db.commit()

        # Count after
        convs_after = (await db.execute(select(func.count(Conversation.id)))).scalar()
        msgs_after = (await db.execute(select(func.count(Message.id)))).scalar()
        chunks_after = (await db.execute(select(func.count(Chunk.id)))).scalar()
        print(f"After wiping - Conversations: {convs_after}, Messages: {msgs_after}, Chunks: {chunks_after}")

if __name__ == "__main__":
    asyncio.run(wipe())
