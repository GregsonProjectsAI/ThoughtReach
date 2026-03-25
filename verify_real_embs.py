import asyncio
import os
import json
import sys
from app.services.embeddings import generate_embeddings
from app.core.config import settings

# Verification script for Step 68A: Direct Service Validation
async def verify_service():
    print(f"OPENAI_API_KEY: {settings.OPENAI_API_KEY[:10]}...")
    print(f"ALLOW_MOCK_EMBEDDINGS: {settings.ALLOW_MOCK_EMBEDDINGS}")
    
    text = "Confirming that real embeddings are being generated."
    print(f"Generating embedding for: '{text}'...")
    
    try:
        embs = await generate_embeddings([text])
        if embs and len(embs) > 0:
            vec = embs[0]
            is_zero = all(v == 0.0 for v in vec)
            print(f"VEC_LEN: {len(vec)}")
            print(f"IS_ZERO: {is_zero}")
            print(f"FIRST_5: {vec[:5]}")
            sys.exit(0 if not is_zero else 1)
        else:
            print("ERROR: Empty embedding list returned.")
            sys.exit(1)
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify_service())
