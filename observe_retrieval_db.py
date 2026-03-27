import asyncio
import os
import sys

# Add current directory to path for imports
sys.path.append(os.getcwd())

from app.db.session import AsyncSessionLocal
from app.services.search import search_chunks

QUERIES = [
    "bedroom riddle",
    "Captain's Code",
    "Location Sheets",
    "pirate theme",
    "structural flaws",
    "convergence logic",
    "fragment distribution",
    "printable assets"
]

async def observe():
    async with AsyncSessionLocal() as db:
        for q in QUERIES:
            print(f"\n--- QUERY: {q} ---")
            results = await search_chunks(q, db, limit=5)
            if not results:
                print("  No results found.")
                continue
            
            for i, res in enumerate(results, 1):
                text = res.get("matched_chunk_text", "")
                obs_text = text.replace("[[", "").replace("]]", "")
                print(f"  Result {i}:")
                print(f"    Length: {len(obs_text)} chars")
                print(f"    Chunk Idx: {res.get('chunk_index')}")
                print(f"    Conversation: {res.get('conversation_title')}")
                print(f"    Text: {obs_text[:200]}...")
                if len(obs_text) > 200:
                    print(f"          ...{obs_text[-100:]}")

if __name__ == "__main__":
    asyncio.run(observe())
