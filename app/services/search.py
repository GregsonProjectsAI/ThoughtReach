from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Chunk, Conversation
from app.services.embeddings import generate_embeddings

async def search_chunks(query: str, db: AsyncSession, limit: int = 10):
    query_embs = await generate_embeddings([query])
    if not query_embs:
        return []
    query_vector = query_embs[0]
    
    distance_expr = Chunk.embedding.cosine_distance(query_vector).label('distance')
    
    stmt = (
        select(Chunk, Conversation, distance_expr)
        .join(Conversation, Chunk.conversation_id == Conversation.id)
        .where(Chunk.embedding.isnot(None))
        .order_by(distance_expr)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    import math
    out = []
    for chunk, conversation, distance in rows:
        sim_score = 0.0
        if distance is not None and not math.isnan(distance):
            sim_score = 1.0 - distance
            
        out.append({
            "conversation_id": conversation.id,
            "conversation_title": conversation.title,
            "matched_chunk_text": chunk.chunk_text,
            "similarity_score": sim_score,
            "message_start_index": chunk.message_start_index,
            "message_end_index": chunk.message_end_index
        })
    return out
