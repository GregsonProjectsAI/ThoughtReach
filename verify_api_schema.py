import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.models.models import Chunk, Conversation

# Verification script for Step 66A
def verify_schema_with_testclient():
    client = TestClient(app)
    
    # We mock the generate_embeddings service to return a dummy vector immediately
    # This allow us to bypass the OpenAI network hang and verify the FastAPI serialization
    with patch("app.services.search.generate_embeddings", new_callable=AsyncMock) as mock_emb:
        mock_emb.return_value = [[0.0] * 1536]
        
        print("Executing Mock Search Request via TestClient...")
        response = client.post("/search", json={"query": "test", "limit": 1})
        
        if response.status_code == 200:
            data = response.json()
            if data:
                first = data[0]
                print(f"TITLE: {first.get('conversation_title')}")
                print(f"HAS 'surrounding_messages': {'surrounding_messages' in first}")
                msgs = first.get('surrounding_messages', [])
                print(f"NUM_MESSAGES: {len(msgs)}")
                if len(msgs) >= 2:
                    print(f"MSG[0]: {msgs[0].get('text')[:50]}...")
                    print(f"MSG[1]: {msgs[1].get('text')[:50]}...")
                
                import json
                with open("api_verification.json", "w") as f:
                    json.dump(data, f, indent=2)
            else:
                print("Search returned no results (DB might be empty or filter too strict).")
        else:
            print(f"ERROR: Received Status Code {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    verify_schema_with_testclient()
