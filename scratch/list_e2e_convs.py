import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.db.session import AsyncSessionLocal
from app.models.models import Conversation
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Conversation).where(Conversation.title.like("E2E %")))
        convs = res.scalars().all()
        for c in convs:
            print(f"ID: {c.id} | Title: {c.title} | Type: {c.source_type}")

if __name__ == "__main__":
    asyncio.run(main())
