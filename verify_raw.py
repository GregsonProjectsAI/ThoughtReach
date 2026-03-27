import asyncio
import asyncpg
import os

# From .env: postgresql+asyncpg://postgres:postgres@localhost:5432/thoughtreach
dsn = "postgresql://postgres:postgres@localhost:5432/thoughtreach"

async def validate():
    print(f"Connecting to: {dsn}")
    conn = await asyncpg.connect(dsn)
    try:
        # 1. Identify conversation
        convs = await conn.fetch("SELECT id, title, source_type, created_at FROM conversations ORDER BY created_at DESC LIMIT 5")
        if not convs:
            print("No conversations found.")
            return

        print("\n--- RECENT CONVERSATIONS ---")
        for c in convs:
            print(f"ID: {c['id']} | Title: {c['title']} | Source: {c['source_type']}")

        # Pick 'Manual Test Conversation' if it exists, else latest
        target_conv = convs[0]
        for c in convs:
            if c['title'] and ("Manual" in c['title'] or "Pirate" in c['title']):
                target_conv = c
                break
        
        conv_id = target_conv['id']
        print(f"\n--- TARGET CONVERSATION INTEGRITY: {target_conv['title']} ---")

        # 2. Verify messages
        msgs = await conn.fetch("SELECT id, role, message_index, content FROM messages WHERE conversation_id = $1 ORDER BY message_index", conv_id)
        print(f"Total Messages: {len(msgs)}")
        for m in msgs:
            print(f"  [{m['message_index']}] Role: {m['role']} | Len: {len(m['content'])}")

        # 3. Verify chunks
        chunks = await conn.fetch("SELECT id, chunk_index, chunk_position_sub, message_start_index, chunk_text FROM chunks WHERE conversation_id = $1 ORDER BY chunk_index", conv_id)
        print(f"\n--- CHUNK INTEGRITY ---")
        print(f"Total Chunks: {len(chunks)}")

        # Check sub-position sequences
        by_msg = {}
        for ch in chunks:
            midx = ch['message_start_index']
            if midx not in by_msg: by_msg[midx] = []
            by_msg[midx].append(ch['chunk_position_sub'])

        for midx, pos_list in by_msg.items():
            is_seq = all(pos_list[i] == i for i in range(len(pos_list)))
            print(f"  Msg {midx}: {len(pos_list)} chunks | Sub-Pos Sequence {pos_list} | Sequential: {is_seq}")

        # 4. Retrieval Sanity (Text Match)
        print("\n--- RETRIEVAL SANITY (TEXT MATCH) ---")
        test_term = "%bedroom%"
        search_res = await conn.fetch("SELECT chunk_text FROM chunks WHERE chunk_text ILIKE $1 AND conversation_id = $2 LIMIT 3", test_term, conv_id)
        if not search_res:
             search_res = await conn.fetch("SELECT chunk_text FROM chunks WHERE chunk_text ILIKE $1 LIMIT 3", test_term)
        
        for r in search_res:
            print(f"  Found: {repr(r['chunk_text'][:80])}...")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(validate())
