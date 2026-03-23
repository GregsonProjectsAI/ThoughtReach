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
