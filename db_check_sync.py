import os
import sys
from sqlalchemy import create_engine, text

# Get DATABASE_URL from .env
db_url = "postgresql://postgres:postgres@localhost:5432/thoughtreach"
# Replace async driver if present
db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

engine = create_engine(db_url)

def run_query(query, params=None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row._mapping) for row in result]

def validate():
    print(f"Connecting to: {db_url}")
    
    # 1. Identify conversation
    convs = run_query("SELECT id, title, source_type, created_at FROM conversations ORDER BY created_at DESC LIMIT 5")
    if not convs:
        print("No conversations found.")
        return
    
    print("\n--- RECENT CONVERSATIONS ---")
    for c in convs:
        print(f"ID: {c['id']} | Title: {c['title']} | Source: {c['source_type']}")

    # Pick the most interesting one (likely containing 'Pirate' or 'Smoke Test')
    target_conv = convs[0] # Default to latest
    for c in convs:
        if "Manual" in c['title'] or "Pirate" in c['title']:
            target_conv = c
            break
            
    conv_id = target_conv['id']
    print(f"\n--- TARGET CONVERSATION INTEGRITY: {target_conv['title']} ---")
    
    # 2. Verify messages
    messages = run_query("SELECT id, role, message_index, content FROM messages WHERE conversation_id = :cid ORDER BY message_index", {"cid": conv_id})
    print(f"Total Messages: {len(messages)}")
    for m in messages:
        print(f"  [{m['message_index']}] Role: {m['role']} | Len: {len(m['content'])}")

    # 3. Verify chunks
    chunks = run_query("SELECT id, chunk_index, chunk_position_sub, message_start_index, chunk_text FROM chunks WHERE conversation_id = :cid ORDER BY chunk_index", {"cid": conv_id})
    print(f"\n--- CHUNK INTEGRITY ---")
    print(f"Total Chunks: {len(chunks)}")
    
    # Check sequences
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
    test_term = "bedroom"
    search_res = run_query("SELECT chunk_text FROM chunks WHERE chunk_text ILIKE :term AND conversation_id = :cid LIMIT 3", {"term": f"%{test_term}%", "cid": conv_id})
    print(f"Searching for '{test_term}' in Conversation {conv_id}...")
    if not search_res:
        print("  No direct match found. (Trying broader search)")
        search_res = run_query("SELECT chunk_text FROM chunks WHERE chunk_text ILIKE :term LIMIT 3", {"term": f"%{test_term}%"})
        
    for r in search_res:
        print(f"  Found: {repr(r['chunk_text'][:80])}...")

if __name__ == "__main__":
    try:
        validate()
    except Exception as e:
        print(f"ERROR: {e}")
