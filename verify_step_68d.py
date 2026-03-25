import asyncio
import os
import sys
from app.core.config import settings
from app.services.embeddings import generate_embeddings
from app.services.search import search_chunks
from app.db.session import AsyncSessionLocal

def mask_key(key: str) -> str:
    if not key:
        return "MISSING"
    if len(key) <= 12:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"

async def verify():
    print("--- Step 68D: Environment Validation ---")
    
    print("\n--- 1. Live Embedding Generation ---")
    test_text = "Verification of real embeddings for Step 68D (Post-Quota)."
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
                print("CRITICAL: Application is generating mock/zero embeddings! (Quota maybe still hit?)")
                sys.exit(1)
            else:
                print("CONFIRMED: Real, non-zero embeddings are being generated.")
        else:
            print("ERROR: generate_embeddings returned empty or None.")
            sys.exit(1)
    except Exception as e:
        print(f"EXCEPTION during embedding: {str(e)}")
        sys.exit(1)

    print("\n--- 2. Search Verification ---")
    async with AsyncSessionLocal() as db:
        query1 = "vector embeddings meaning"
        print(f"Running search for: '{query1}'")
        results1 = await search_chunks(query1, db, limit=3)
        
        if results1:
            best = results1[0]
            print(f"Top Result Similarity: {best['similarity_score']:.4f}")
            print(f"Top Result Title: {best['conversation_title']}")
            print(f"Top Result Text: {best['matched_chunk_text'][:100]}...")
            
            if best['similarity_score'] > 0:
                print(f"CONFIRMED: Non-zero similarity for '{query1}'")
            else:
                print(f"WARNING: Zero similarity score for '{query1}' (Still failing?)")
        else:
            print(f"No results found for query '{query1}'.")

        print("\n--- 3. Query Sensitivity ---")
        query2 = "Japan travel Kyoto"
        print(f"Running search for: '{query2}'")
        results2 = await search_chunks(query2, db, limit=3)
        
        if results2:
            best2 = results2[0]
            print(f"Top Result Similarity: {best2['similarity_score']:.4f}")
            print(f"Top Result Title: {best2['conversation_title']}")
            
            if results1 and best['conversation_id'] != best2['conversation_id']:
                print("CONFIRMED: Different queries return different top results (Sensitivity OK).")
            else:
                print("INFO: Queries returned the same top result. Checking score changes.")
                if math.isclose(best['similarity_score'], best2['similarity_score'], rel_tol=1e-5):
                     print("WARNING: Identical similarity scores. Results may be static.")
                else:
                     print(f"Score 1: {best['similarity_score']:.4f}, Score 2: {best2['similarity_score']:.4f}")
        else:
            print(f"No results found for query '{query2}'.")

if __name__ == "__main__":
    import math # added import for query sensitivity check
    asyncio.run(verify())
