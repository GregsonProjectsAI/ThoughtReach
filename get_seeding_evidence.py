import asyncio
import json
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import Conversation, Message

async def fetch_seeding_evidence():
    async with AsyncSessionLocal() as db:
        titles = [
            "Understanding Vector Embeddings",
            "LLM Memory and Context Windows",
            "Japan Travel Itinerary - Autumn",
            "Personal Finance: Index Funds vs Stock Picking",
            "Building a Zone 2 Running Base",
            "PKM: Organizing Digital Notes"
        ]
        
        # 1. Confirm all 6 exist
        existence = {}
        for t in titles:
            conv = (await db.execute(select(Conversation).where(Conversation.title == t).order_by(Conversation.imported_at.desc()))).scalars().first()
            existence[t] = str(conv.id) if conv else "MISSING"

        # 2. Spot-check 2 of them
        spot_checks = {}
        for t in ["Understanding Vector Embeddings", "Japan Travel Itinerary - Autumn"]:
            conv_id = existence.get(t)
            if conv_id == "MISSING":
                continue
            
            msgs = (await db.execute(select(Message).where(Message.conversation_id == conv_id).order_by(Message.message_index))).scalars().all()
            
            spot_checks[t] = {
                "id": conv_id,
                "first_3_messages": [
                    {"role": m.role, "content": m.content[:100]} for m in msgs[:3]
                ]
            }
        
        result = {
            "existence": existence,
            "spot_checks": spot_checks
        }
        
        with open("seeding_evidence.json", "w") as f:
            json.dump(result, f, indent=2)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(fetch_seeding_evidence())
    finally:
        loop.close()
