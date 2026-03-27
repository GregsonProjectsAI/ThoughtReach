import asyncio
import asyncpg
import os

dsn = "postgresql://postgres:postgres@localhost:5432/thoughtreach"

async def validate():
    print(f"Connecting to: {dsn}")
    conn = await asyncpg.connect(dsn)
    try:
        # Find the'pirate hunt' conversation (search for 'Island' or 'Pirate')
        search_q = "%PIRATE HUNT%"
        rows = await conn.fetch("SELECT id, title, raw_text FROM conversations WHERE raw_text ILIKE $1 LIMIT 1", search_q)
        if not rows:
            print("Pirate hunt conversation not found by content search.")
            # Fallback to latest
            rows = await conn.fetch("SELECT id, title, raw_text FROM conversations ORDER BY created_at DESC LIMIT 1")
            
        if not rows:
            print("No conversations found.")
            return

        conv = rows[0]
        conv_id = conv['id']
        print(f"\n--- VALIDATING CONVERSATION: {conv['title']} ---")
        print(f"ID: {conv_id}")

        # Message check
        msgs = await conn.fetch("SELECT id, role, message_index, content FROM messages WHERE conversation_id = $1 ORDER BY message_index", conv_id)
        print(f"Messages: {len(msgs)}")
        for i, m in enumerate(msgs):
            print(f"  [{m['message_index']}] Role: {m['role']} | Len: {len(m['content'])} | First 20: {repr(m['content'][:20])}")

        # Chunk check
        chunks = await conn.fetch("SELECT id, chunk_index, chunk_position_sub, message_start_index, chunk_text FROM chunks WHERE conversation_id = $1 ORDER BY chunk_index", conv_id)
        print(f"\n--- CHUNK CHECK ---")
        print(f"Total Chunks: {len(chunks)}")
        
        # Check if they have sub-positions
        has_sub = any(c['chunk_position_sub'] is not None for c in chunks)
        print(f"Contains sub-position indices: {has_sub}")
        
        # Retrieval Check
        print("\n--- RETRIEVAL CONFIRMATION ---")
        query = "Captain's Code"
        matches = await conn.fetch("SELECT chunk_text FROM chunks WHERE chunk_text ILIKE $1 LIMIT 3", f"%{query}%")
        print(f"Query '{query}' found {len(matches)} result(s).")
        for m in matches:
             print(f"  Result: {repr(m['chunk_text'][:100])}...")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(validate())
