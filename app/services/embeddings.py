import asyncio
from app.core.config import settings

# ---------------------------------------------------------------------------
# Local provider — lazily initialized sentence-transformers model.
# The model is loaded only on the first call so startup is not penalized and
# processes that never call generate_embeddings pay zero cost.
# ---------------------------------------------------------------------------
_local_model = None

def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    return _local_model


# Target dimension — must match the Vector(1536) DB column exactly.
_TARGET_DIM = 1536

def _encode_local(texts: list[str]) -> list[list[float]]:
    """Synchronous local encoding — called via asyncio.to_thread.

    BAAI/bge-large-en-v1.5 outputs 1024-dim vectors. Each vector is
    zero-padded to _TARGET_DIM (1536) so callers and the database schema
    remain unchanged without an Alembic migration.
    """
    model = _get_local_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    result = []
    for v in vectors:
        lst = v.tolist()
        if len(lst) < _TARGET_DIM:
            lst = lst + [0.0] * (_TARGET_DIM - len(lst))
        result.append(lst)
    return result


async def _embed_local(texts: list[str]) -> list[list[float]]:
    """Async wrapper: runs synchronous encoding on a thread-pool executor."""
    return await asyncio.to_thread(_encode_local, texts)


# ---------------------------------------------------------------------------
# OpenAI provider — lazily initialized client.
# The client is constructed only when the openai provider is selected, so an
# absent API key does not cause an import-time failure.
# ---------------------------------------------------------------------------
_openai_client = None

def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


async def _embed_openai(texts: list[str]) -> list[list[float]]:
    """Batch embedding via OpenAI text-embedding-3-small (1536 dims)."""
    is_placeholder = (
        not settings.OPENAI_API_KEY
        or settings.OPENAI_API_KEY.strip() in ("", "your_openai_api_key_here")
    )
    if is_placeholder:
        raise RuntimeError(
            "Embedding generation failed: EMBEDDING_PROVIDER is 'openai' but "
            "OPENAI_API_KEY is missing or is a placeholder."
        )

    client = _get_openai_client()
    BATCH_SIZE = 500  # Conservative — well below the 2048 cap.
    all_embeddings: list[list[float]] = []

    try:
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = await asyncio.wait_for(
                client.embeddings.create(input=batch, model="text-embedding-3-small"),
                timeout=12.0,
            )
            batch_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([item.embedding for item in batch_data])
        return all_embeddings
    except Exception as e:
        error_msg = f"Embedding provider error (openai): {e}"
        print(f"CRITICAL_EMB_ERROR: {error_msg}")
        raise RuntimeError(error_msg) from e


# ---------------------------------------------------------------------------
# Public interface — unchanged signature used by all callers.
# ---------------------------------------------------------------------------

async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.

    Provider is selected via settings.EMBEDDING_PROVIDER:
      "local"  — sentence-transformers model (no API key required, default)
      "openai" — OpenAI text-embedding-3-small (requires OPENAI_API_KEY)

    Both paths return list[list[float]] with inner length 1536, matching the
    current Vector(1536) database column.
    """
    if not texts:
        return []

    provider = (settings.EMBEDDING_PROVIDER or "local").strip().lower()

    try:
        if provider == "openai":
            return await _embed_openai(texts)
        else:
            # Treat any unrecognised value as "local" for safety.
            return await _embed_local(texts)
    except Exception as e:
        error_msg = f"Embedding provider error ({provider}): {e}"
        print(f"CRITICAL_EMB_ERROR: {error_msg}")
        raise RuntimeError(error_msg) from e


# ---------------------------------------------------------------------------
# Summary generation — OpenAI chat (unchanged).
# Returns None gracefully when the key is absent; callers already handle this.
# ---------------------------------------------------------------------------

async def generate_summary(text: str) -> str | None:
    if not text.strip():
        return None

    # Pre-generation bounding: strict 12,000 char cap (~3k tokens)
    if len(text) > 12000:
        text = text[:12000] + "\n...[truncated]"

    try:
        import openai
        client = _get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes conversations concisely in 2-4 sentences max.",
                },
                {"role": "user", "content": f"Please summarize the following conversation:\n\n{text}"},
            ],
            max_tokens=150,
        )
        content = response.choices[0].message.content.strip()

        # Normalize and clip for UI safety (max 300 chars)
        if len(content) > 300:
            content = content[:297] + "..."

        return content
    except Exception:
        import openai as _openai
        try:
            raise
        except _openai.AuthenticationError:
            if settings.ALLOW_MOCK_EMBEDDINGS:
                return "This is a mock summary for local development."
            return None
        except Exception:
            return None
