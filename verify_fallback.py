import asyncio
import sys
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from unittest.mock import patch

def test_fallback_logic():
    client = TestClient(app)
    
    # Force settings so the code tries to make an OpenAI call but to an invalid endpoint
    # to trigger the exception/timeout block.
    # But actually, asyncio.wait_for with a fake key might take 3 seconds.
    # To test exactly what happens, let's just observe if it takes ~3s and returns successfully.
    settings.ALLOW_MOCK_EMBEDDINGS = False
    settings.OPENAI_API_KEY = "sk-fakekey12345678901234567890123456789012345678901234"
    
    print("Testing search fallback logic (timeout=3.0s expected)...")
    
    import time
    start = time.time()
    
    # Execute the request
    try:
        response = client.post("/search", json={"query": "test", "limit": 1})
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                print(f"SUCCESS: Result fetched in {elapsed:.2f} seconds.")
                print(f"TITLE: {data[0].get('conversation_title')}")
                print(f"SURROUNDING_MESSAGES_COUNT: len({len(data[0].get('surrounding_messages', []))})")
                sys.exit(0)
            else:
                print(f"SUCCESS: Empty result fetched in {elapsed:.2f} seconds.")
                sys.exit(0)
        else:
            print(f"FAILED with status {response.status_code} in {elapsed:.2f} seconds.")
            print(response.text)
            sys.exit(1)
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_fallback_logic()
