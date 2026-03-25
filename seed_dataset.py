import urllib.request
import json

BASE_URL = "http://localhost:8001"

conversations = [
    {
        "title": "Understanding Vector Embeddings",
        "raw_text": """User: Can you explain how vector databases work? I'm building a RAG application.
Assistant: A vector database stores data as high-dimensional vectors, which are mathematical representations of the data's semantic meaning. When you run a query, the database compares the mathematical distance (like cosine similarity) between your query's vector and the stored vectors to find the most conceptually similar items, even if they don't share exact keywords.
User: Oh, so it's not just checking if a word exists in the text.
Assistant: Exactly. If you search for 'puppy', it might return documents about 'dogs' or 'golden retrievers' because their vectors are grouped close together in the embedding space. This is what makes RAG (Retrieval-Augmented Generation) so powerful for LLMs.
User: What model should I use for generating these vectors?
Assistant: OpenAI's text-embedding-3-small is a great default for balancing cost and performance. If you need local privacy, sentence-transformers models like all-MiniLM-L6-v2 are excellent open-source alternatives."""
    },
    {
        "title": "LLM Memory and Context Windows",
        "raw_text": """User: I'm trying to make my chatbot remember things across long sessions but the context window keeps filling up.
Assistant: Managing long-term memory is a common challenge. Instead of passing the entire chat history every time, most architectures use a retrieval system. They chunk past conversations, embed them, and only retrieve the 3-5 most relevant chunks to inject into the active prompt.
User: That sounds like what people call semantic search.
Assistant: Yes, that's exactly semantic search. By finding text that shares the underlying meaning of the user's current question, you can give the LLM just the information it needs without exceeding its token limits.
User: Are there other ways besides embeddings?
Assistant: You can also have the LLM periodically summarize the chat history into a dense prompt payload, or use structured knowledge graphs to store explicit facts about the user."""
    },
    {
        "title": "Japan Travel Itinerary - Autumn",
        "raw_text": """User: I'm planning a 10-day trip to Japan in late November. I want to see autumn leaves. Where should I go?
Assistant: Late November is peak season for autumn foliage (koyo) in central Japan! For a 10-day trip, a classic route is Tokyo, Kyoto, and Hakone. Kyoto is particularly famous for its autumn colors.
User: What are the best spots in Kyoto for the leaves?
Assistant: Tofukuji Temple offers breathtaking views from its Tsutenkyo Bridge. Kiyomizu-dera is also stunning, especially during its special evening illuminations. Arashiyama, with its forested hills changing colors, is another must-visit.
User: Should I get a JR Pass for that route?
Assistant: With the recent price increases for the Japan Rail Pass, a 7-day pass might not pay off for just a Tokyo-Kyoto round trip. It's often cheaper to buy individual Shinkansen tickets unless you plan side trips to places like Hiroshima or Kanazawa."""
    },
    {
        "title": "Personal Finance: Index Funds vs Stock Picking",
        "raw_text": """User: Is it better to pick individual stocks or just buy an S&P 500 index fund?
Assistant: For the vast majority of retail investors, buying a broad-market index fund like the S&P 500 is the optimal strategy. Index funds offer immediate diversification, extremely low fees, and historically outperform active stock pickers over long time horizons.
User: But what if I really research the companies?
Assistant: Even professional fund managers with massive teams and resources fail to beat the market benchmark over a 10-year period about 90% of the time. Individual stock picking carries 'idiosyncratic risk'—the risk that a specific company fails—without proportionally higher expected returns to justify it.
User: What's a good allocation strategy then?
Assistant: A common, simple approach is a two- or three-fund portfolio (often called the Boglehead method): a total domestic stock market ETF (like VTI), a total international stock ETF (like VXUS), and a bond fund tailored to your age and risk tolerance."""
    },
    {
        "title": "Building a Zone 2 Running Base",
        "raw_text": """User: I want to run a half marathon but I get out of breath so quickly when I jog. How do I fix this?
Assistant: The key to building endurance is spending 80% of your training volume in 'Zone 2'. This is an easy, conversational pace where your heart rate is roughly 60-70% of your maximum. It might feel frustratingly slow at first, and you might even need to run/walk.
User: Why slow down to get faster? That seems backwards.
Assistant: Running slowly in Zone 2 specifically targets your aerobic energy system. It increases mitochondrial density, capillary growth, and fat oxidation. Over weeks of consistent Zone 2 training, your body becomes vastly more efficient, allowing you to run faster while maintaining that same low heart rate.
User: How often should I run?
Assistant: Start with 3-4 days a week for 30-40 minutes at that easy pace. Consistency is far more important than intensity when building your aerobic base."""
    },
    {
        "title": "PKM: Organizing Digital Notes",
        "raw_text": """User: My digital notes are a mess. I have documents in Google Drive, Apple Notes, and random text files. How do I build a better system?
Assistant: A good Personal Knowledge Management (PKM) system reduces friction. You might want to look into the 'Zettelkasten' method or the 'PARA' framework. The most important step is centralizing. Choose one robust tool, like Obsidian, Notion, or Logseq, as your single source of truth.
User: What's the PARA method?
Assistant: PARA stands for Projects, Areas, Resources, and Archives. It's an actionability-based organization system developed by Tiago Forte. Instead of sorting by topic (like 'Psychology'), you sort by how actionable the item is (e.g., 'Project: Write Psychology Essay').
User: Should I use folders or tags?
Assistant: Modern PKM heavily favors tags and bi-directional linking over rigid folders. Links mimic how your brain naturally associates ideas, allowing a single note to seamlessly connect to multiple contexts without being trapped in a single folder hierarchy."""
    }
]

def req_post(path, data):
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode())

print("Seeding Validation Dataset...")
success_count = 0
for conv in conversations:
    print(f"\nIngesting: {conv['title']}")
    try:
        res = req_post("/ingest/paste", conv)
        status = res.get("status")
        conv_id = res.get("conversation_id")
        print(f"  Status: {status}")
        if status == "ingested":
            print(f"  ID: {conv_id}")
            success_count += 1
        elif status == "skipped":
            print("  Skipped (Duplicate text).")
    except Exception as e:
        print(f"  Error: {e}")

print(f"\nSeeding complete. Successfully ingested {success_count}/{len(conversations)} conversations.")
