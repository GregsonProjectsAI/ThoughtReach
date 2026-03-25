import asyncio
import json
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import Conversation, Message

async def fetch_evidence():
    async with AsyncSessionLocal() as db:
        res = {}
        for title in ['Test 1 Final', 'Test 3', 'Test 4']:
            conv = (await db.execute(select(Conversation).where(Conversation.title == title).order_by(Conversation.imported_at.desc()))).scalars().first()
            if not conv:
                res[title] = "Not found"
                continue
            
            msgs = (await db.execute(select(Message).where(Message.conversation_id == conv.id).order_by(Message.message_index))).scalars().all()
            
            res[title] = {
                "id": str(conv.id),
                "messages": [{"role": m.role, "content": m.content[:50]} for m in msgs]
            }
        
        with open("ev2.json", "w") as f:
            json.dump(res, f, indent=2)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(fetch_evidence())
