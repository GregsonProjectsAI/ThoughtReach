import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

async def repair_legacy_conversations():
    async with AsyncSessionLocal() as session:
        # Find conversations with > 1 message and 0 assistant messages
        query = text("""
            SELECT conversation_id 
            FROM messages 
            GROUP BY conversation_id 
            HAVING count(*) > 1 AND sum(case when role = 'assistant' then 1 else 0 end) = 0
        """)
        result = await session.execute(query)
        conversation_ids = [row[0] for row in result.fetchall()]
        
        print(f"Found {len(conversation_ids)} conversations to repair.")
        
        repaired_count = 0
        for cid in conversation_ids:
            # Update odd message_index to 'assistant'
            # Assuming message_index is 0-based: 0=user, 1=assistant, 2=user...
            # So if message_index % 2 == 1, set to assistant
            update_query = text("""
                UPDATE messages 
                SET role = 'assistant' 
                WHERE conversation_id = :cid AND (message_index % 2) = 1
            """)
            await session.execute(update_query, {"cid": cid})
            repaired_count += 1
            
        await session.commit()
        print(f"Repaired {repaired_count} conversations.")

if __name__ == "__main__":
    asyncio.run(repair_legacy_conversations())
