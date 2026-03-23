import openai
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generates embeddings using text-embedding-3-small in batch."""
    if not texts:
        return []
    try:
        response = await client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        # Ensure they are in correct order based on input array
        response.data.sort(key=lambda x: x.index)
        return [item.embedding for item in response.data]
    except openai.AuthenticationError:
        if settings.ALLOW_MOCK_EMBEDDINGS:
            # Smallest fix for the local validation without a valid key
            return [[0.0] * 1536 for _ in texts]
        raise

async def generate_summary(text: str) -> str | None:
    if not text.strip():
        return None
        
    # Pre-generation bounding: strict 12,000 char cap (~3k tokens)
    if len(text) > 12000:
        text = text[:12000] + "\n...[truncated]"
        
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations concisely in 2-4 sentences max."},
                {"role": "user", "content": f"Please summarize the following conversation:\n\n{text}"}
            ],
            max_tokens=150,
        )
        content = response.choices[0].message.content.strip()
        
        # Normalize and clip for UI safety (max 300 chars)
        if len(content) > 300:
            content = content[:297] + "..."
            
        return content
    except openai.AuthenticationError:
        from app.core.config import settings
        if settings.ALLOW_MOCK_EMBEDDINGS:
            return "This is a mock summary for local development."
        return None
    except Exception:
        return None
