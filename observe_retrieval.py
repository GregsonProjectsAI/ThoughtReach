import urllib.request
import json
import os

BASE_URL = "http://localhost:8000"

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

def run_query(query):
    print(f"\n--- QUERY: {query} ---")
    req = urllib.request.Request(
        f"{BASE_URL}/search",
        data=json.dumps({"query": query, "limit": 5}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())
            if not data:
                print("  No results found.")
                return
            for i, result in enumerate(data, 1):
                text = result.get("matched_chunk_text", "")
                # Remove [[ ]] markers for readability in console observation
                obs_text = text.replace("[[", "").replace("]]", "")
                print(f"  Result {i}:")
                print(f"    Length: {len(obs_text)} chars")
                print(f"    Sub-Pos: {result.get('chunk_index')} (index)")
                print(f"    Text: {obs_text[:200]}...")
                if len(obs_text) > 200:
                    print(f"          ...{obs_text[-100:]}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    for q in QUERIES:
        run_query(q)
