import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        res = await client.get("http://localhost:8000/library")
        items = res.json()
        for item in items:
            if item['title'].startswith("E2E"):
                print(f"Title: {item['title']} | source_type: {item.get('source_type')} | conversation_source_type: {item.get('conversation_source_type')}")
        
        # Check messages for WhatsApp
        wa = next(i for i in items if i['title'] == "E2E WhatsApp")
        res2 = await client.get(f"http://localhost:8000/conversations/{wa['id']}")
        conv = res2.json()
        print("\nWhatsApp messages:")
        for m in conv.get('messages', []):
            print(f"Role: {m.get('role')} | content: {m.get('content')[:20]}")

if __name__ == "__main__":
    asyncio.run(main())
