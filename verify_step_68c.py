import asyncio
import os
import sys
import math
from app.core.config import settings
from app.services.embeddings import generate_embeddings
from app.services.search import search_chunks
from app.db.session import AsyncSessionLocal

def mask_key(key: str) -> str:
    if not key:
        return "MISSING"
    if len(key) <= 12:
        return "*" * len(key)
    # Masking more aggressively to be safe
    return f"{key[:6]}...{key[-4:]}"

async def verify():
    print("--- 1. Runtime Key Source Check ---")
    os_key = os.environ.get("OPENAI_API_KEY")
    settings_key = settings.OPENAI_API_KEY
    
    # Pydantic Settings precedence: 
    # 1. Environment variables
    # 2. .env file
    # 3. Defaults
    
    print(f"Active OPENAI_API_KEY (from Settings): {mask_key(settings_key)}")
    
    if os_key:
        print(f"OS-level Environment Variable found: {mask_key(os_key)}")
        if os_key == settings_key:
            print("STATUS: OS environment variable is currently driving the application.")
        else:
            # This would be strange for Pydantic Settings unless manually overridden
            print("STATUS: OS environment variable is present but does NOT match active settings.")
    else:
        print("OS-level Environment Variable: NOT DETECTED")
        if settings_key:
            print("STATUS: Key is successfully loaded from .env (or internal config).")
        else:
            print("STATUS: No key found in environment or .env.")

    print("\n--- 2. Embedding Verification ---")
    test_text = "Verification of real embeddings for Step 68C."
    print(f"Generating embedding for: '{test_text}'")
    
    try:
        embs = await generate_embeddings([test_text])
        if embs and len(embs) > 0:
            vec = embs[0]
            is_zero = all(v == 0.0 for v in vec)
            print(f"Embedding Status: SUCCESS")
            print(f"Vector Dimension: {len(vec)}")
            print(f"Is Zero-Vector: {is_zero}")
            print(f"First 5 numeric values: {vec[:5]}")
            
            if is_zero:
                print("CRITICAL: Application is generating mock/zero embeddings!")
            else:
                print("CONFIRMED: Real, non-zero embeddings are being generated.")
        else:
            print("ERROR: generate_embeddings returned empty or None.")
    except Exception as e:
        print(f"EXCEPTION during embedding: {str(e)}")

    print("\n--- 3. Live Search Verification ---")
    async with AsyncSessionLocal() as db:
        # We'll try some general terms to see if we get hits
        queries = ["AI machine learning", "database schema"]
        
        results_map = {}
        
        for q in queries:
            print(f"\nRunning search for: '{q}'")
            results = await search_chunks(q, db, limit=3)
            results_map[q] = results
            
            if results:
                best = results[0]
                print(f"Top Result Similarity: {best['similarity_score']:.4f}")
                print(f"Top Result Context: {best['matched_chunk_text'][:80]}...")
                if best['similarity_score'] > 0:
                    print(f"CONFIRMED: Non-zero similarity for '{q}'")
                else:
                    print(f"WARNING: Zero similarity score for '{q}'")
            else:
                print(f"No results found for query '{q}'. (Database might be empty or unindexed)")

        print("\n--- 4. Query Sensitivity ---")
        if len(results_map[queries[0]]) > 0 and len(results_map[queries[1]]) > 0:
            top1_id = results_map[queries[0]][0]['conversation_id']
            top2_id = results_map[queries[1]][0]['conversation_id']
            
            if top1_id != top2_id:
                print("CONFIRMED: Different queries return different top results (Sensitivity OK).")
            else:
                print("INFO: Queries returned the same top result. This is acceptable if the dataset is small.")
                # Look at scores
                score1 = results_map[queries[0]][0]['similarity_score']
                score2 = results_map[queries[1]][0]['similarity_score']
                print(f"Score 1: {score1:.4f}, Score 2: {score2:.4f}")
        else:
            print("SKIP: Not enough results to verify sensitivity.")

if __name__ == "__main__":
    asyncio.run(verify())
