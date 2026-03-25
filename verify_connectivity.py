import os
import sys
import json
import urllib.request
import urllib.error
from app.core.config import settings
import ssl
import socket

def mask(s):
    if not s: return str(s)
    s = str(s)
    if len(s) > 15:
        return s[:10] + "..." + s[-5:]
    return "***"

def main():
    print("--- 1. Environment Source Check ---")
    env_sh_key = os.getenv("OPENAI_API_KEY")
    print(f"OS Env OPENAI_API_KEY: {mask(env_sh_key)}")
    print(f"App Settings OPENAI_API_KEY: {mask(settings.OPENAI_API_KEY)}")
    print(f"App Settings ALLOW_MOCK: {settings.ALLOW_MOCK_EMBEDDINGS}")
    
    print("\n--- 2. Basic HTTPS Connectivity ---")
    try:
        context = ssl.create_default_context()
        with socket.create_connection(('api.openai.com', 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname='api.openai.com') as ssock:
                print("Socket connection to api.openai.com:443 SUCCESS")
    except Exception as e:
        print(f"Socket connection FAILED: {e}")
        
    print("\n--- 3. Minimal Non-App API Check ---")
    url = "https://api.openai.com/v1/models"
    auth_key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else env_sh_key
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {auth_key}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            models = len(data.get("data", []))
            print(f"API /v1/models success. Fetched {models} models (Code: {res.status})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"API /v1/models HTTP ERROR: {e.code} {e.reason}")
        print(f"Response Body: {body}")
    except Exception as e:
        print(f"API /v1/models FAILED: {e}")

if __name__ == "__main__":
    main()
