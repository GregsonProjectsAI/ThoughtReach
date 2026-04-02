import asyncio
import openai
from openai import AsyncOpenAI
from app.core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generates embeddings using text-embedding-3-small in bounded batches."""
    if not texts:
        return []
    
    is_placeholder = not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.strip() in ("", "your_openai_api_key_here")
    if is_placeholder:
        raise RuntimeError("Embedding generation failed: OpenAI API key is missing or is set to placeholder.")
        
    BATCH_SIZE = 500  # Conservative batch size below the known 2048 cap
    all_embeddings = []
    
    try:
        # Process in safe request batches
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = await asyncio.wait_for(
                client.embeddings.create(
                    input=batch,
                    model="text-embedding-3-small"
                ),
                timeout=12.0 # Slightly increased timeout for batch resilience
            )
            
            # Sort batch items by their index (0-based for this batch) to guarantee order
            batch_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in batch_data])
            
        return all_embeddings
    except Exception as e:
        error_msg = f"Embedding provider error: {str(e)}"
        print(f"CRITICAL_EMB_ERROR: {error_msg}")
        raise RuntimeError(error_msg) from e

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
