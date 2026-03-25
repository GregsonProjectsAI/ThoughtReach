import asyncio
import json
from app.services.search import search_chunks
from app.db.session import AsyncSessionLocal

async def run_tests():
    async with AsyncSessionLocal() as db:
        LIMIT = 5
        results_log = {}
        
        # 1. Direct match query
        q1 = "chatbot remember things across long sessions but the context window keeps filling up"
        res1 = await search_chunks(q1, db, limit=LIMIT)
        results_log["test1"] = {
            "query": q1,
            "results": [{"title": r['conversation_title'], "score": r['similarity_score'], "match": r['matched_chunk_text'][:100]} for r in res1],
            "pass": len(res1) > 0 and res1[0]['conversation_title'] == "LLM Memory and Context Windows"
        }

        # 2. Semantic match query
        q2 = "how to overcome context limits in LLMs"
        res2 = await search_chunks(q2, db, limit=LIMIT)
        results_log["test2"] = {
            "query": q2,
            "results": [{"title": r['conversation_title'], "score": r['similarity_score'], "match": r['matched_chunk_text'][:100]} for r in res2],
            "pass": len(res2) > 0 and "LLM Memory" in res2[0]['conversation_title']
        }

        # 3. Multi-result relevance
        q3 = "AI and machine learning techniques for memory"
        res3 = await search_chunks(q3, db, limit=LIMIT)
        rel_count = sum(1 for r in res3 if "LLM Memory" in r['conversation_title'] or "AI" in r['conversation_title'])
        results_log["test3"] = {
            "query": q3,
            "results": [{"title": r['conversation_title'], "score": r['similarity_score'], "match": r['matched_chunk_text'][:100]} for r in res3],
            "pass": rel_count >= 2
        }

        # 4. Topic separation
        q4 = "Kyoto and Osaka autumn foliage"
        res4 = await search_chunks(q4, db, limit=LIMIT)
        results_log["test4"] = {
            "query": q4,
            "results": [{"title": r['conversation_title'], "score": r['similarity_score'], "match": r['matched_chunk_text'][:100]} for r in res4],
            "pass": len(res4) > 0 and "Japan Travel" in res4[0]['conversation_title']
        }

        # 5. Context integrity
        if res4:
            ctx = res4[0]['surrounding_messages']
            positions = [m['position'] for m in ctx]
            results_log["test5"] = {
                "title": res4[0]['conversation_title'],
                "context": ctx,
                "pass": positions == sorted(positions)
            }
        else:
            results_log["test5"] = {"pass": False, "note": "No results for Test 4"}

        # 6. Deterministic consistency
        q6 = "vector embeddings"
        res1a = await search_chunks(q6, db, limit=LIMIT)
        res1b = await search_chunks(q6, db, limit=LIMIT)
        results_log["test6"] = {
            "query": q6,
            "pass": [str(r['conversation_id']) for r in res1a] == [str(r['conversation_id']) for r in res1b]
        }
        
        with open("validation_results.json", "w") as f:
            json.dump(results_log, f, indent=2)
        print("Validation results saved to validation_results.json")

if __name__ == "__main__":
    asyncio.run(run_tests())
