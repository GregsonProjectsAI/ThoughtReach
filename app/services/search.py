from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Chunk, Conversation, Message, Category
from app.services.embeddings import generate_embeddings

from uuid import UUID

async def search_chunks(query: str, db: AsyncSession, limit: int = 10, category_id: Optional[UUID] = None):
    query_embs = await generate_embeddings([query])
    if not query_embs:
        return []
    query_vector = query_embs[0]
    
    distance_expr = Chunk.embedding.cosine_distance(query_vector).label('distance')
    
    stmt = (
        select(Chunk, Conversation, Category, distance_expr)
        .join(Conversation, Chunk.conversation_id == Conversation.id)
        .outerjoin(Category, Conversation.category_id == Category.id)
        .where(Chunk.embedding.isnot(None))
    )
    
    if category_id:
        stmt = stmt.where(Conversation.category_id == category_id)
        
    stmt = stmt.order_by(distance_expr).limit(limit)
    
    result = await db.execute(stmt)
    rows = result.all()
    
    import math
    out = []
    message_counts_cache = {}
    
    for chunk, conversation, category, distance in rows:
        sim_score = 0.0
        if distance is not None and not math.isnan(distance):
            sim_score = 1.0 - distance
            
        surrounding = []
        s_idx = chunk.message_start_index
        e_idx = chunk.message_end_index
        
        if conversation.id not in message_counts_cache:
            count_stmt = select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id)
            total_msgs = (await db.execute(count_stmt)).scalar() or 0
            message_counts_cache[conversation.id] = total_msgs
        else:
            total_msgs = message_counts_cache[conversation.id]
            
        rel_pos = round(s_idx / total_msgs, 2) if total_msgs > 0 else 0.0
        
        stmt_msgs = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.message_index >= s_idx - 1)
            .where(Message.message_index <= e_idx + 1)
            .order_by(Message.message_index)
        )
        msg_result = await db.execute(stmt_msgs)
        msgs = msg_result.scalars().all()
        
        for m in msgs:
            pos = m.message_index - s_idx
            surrounding.append({
                "position": pos,
                "text": f"{m.role}: {m.content}"
            })
            
        out.append({
            "conversation_id": conversation.id,
            "conversation_title": conversation.title,
            "conversation_summary": conversation.summary,
            "category_id": conversation.category_id,
            "category_name": category.name if category else None,
            "matched_chunk_text": chunk.chunk_text,
            "similarity_score": sim_score,
            "message_start_index": chunk.message_start_index,
            "message_end_index": chunk.message_end_index,
            "chunk_index": chunk.chunk_index,
            "message_count": total_msgs,
            "relative_position": rel_pos,
            "surrounding_messages": surrounding
        })
    return out

def format_search_results_for_llm(results: list[dict]) -> str:
    """
    INTERNAL ONLY: Prepares raw search results as a deterministic text block mapped 
    strictly for downstream LLM inference/RAG context windows.
    This does NOT perform ranking, similarity scoring, or user-facing UI formatting.
    Treats the matched chunk as primary evidence and includes the summary as auxiliary context.
    """
    if not results:
        return "No relevant results found."
        
    formatted_blocks = []
    for i, res in enumerate(results, 1):
        title = res.get("conversation_title", "Unknown")
        summary = res.get("conversation_summary", "")
        chunk_text = res.get("matched_chunk_text", "")
        
        block = f"[Result {i}]\nSOURCE:\n{title}\n"
        if summary:
            block += f"\nSUMMARY:\n{summary}\n"
        block += f"\nEVIDENCE:\n{chunk_text}"
        
        formatted_blocks.append(block)
        
    return "\n\n---\n\n".join(formatted_blocks)

async def get_formatted_search_context(db: AsyncSession, query: str, limit: int = 10) -> str:
    """
    INTERNAL ONLY: Executes a semantic search and strictly bundles the output into 
    a ready-to-use structured context block for downstream LLM agents.
    It delegates exclusively to semantic layout constraints and serves solely as internal RAG wiring.
    """
    raw_results = await search_chunks(query, db, limit)
    return format_search_results_for_llm(raw_results)

def assemble_rag_prompt(query: str, formatted_context: str) -> str:
    """
    INTERNAL ONLY: Combines a user query with securely formatted retrieval context 
    into a deterministic, final prompt string for downstream LLM evaluation.
    """
    return (
        f"USER QUERY:\n{query}\n\n"
        f"RETRIEVED CONTEXT:\n{formatted_context}\n\n"
        f"INSTRUCTIONS:\n"
        f"Use the retrieved context to answer the query. If the context is insufficient, "
        f"say you do not have enough information."
    )

async def build_rag_prompt_for_query(db: AsyncSession, query: str, limit: int = 10) -> str:
    """
    INTERNAL ONLY: Orchestrates the full retrieval and assembly pipeline,
    taking a raw user query and generating a final, structured LLM prompt string.
    """
    formatted_context = await get_formatted_search_context(db, query, limit)
    return assemble_rag_prompt(query, formatted_context)
