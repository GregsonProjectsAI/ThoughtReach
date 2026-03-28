from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import Chunk, Conversation, Message, Category
from app.services.embeddings import generate_embeddings

from uuid import UUID

async def search_chunks(query: str, db: AsyncSession, limit: int = 10, category_id: Optional[UUID] = None):
    import re
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
        
    stmt = stmt.order_by(distance_expr).limit(50)
    
    result = await db.execute(stmt)
    rows = result.all()
    
    # Filter out low-information single-word chunks
    filtered_rows = []
    for chunk, conversation, category, distance in rows:
        text = chunk.chunk_text or ""
        if len(text.split()) == 1:
            continue
        filtered_rows.append((chunk, conversation, category, distance))
    rows = filtered_rows
    
    # 2. Conversation-level deduplication (Max 2 results per conversation)
    from collections import defaultdict
    conv_counts = defaultdict(int)
    deduped_rows = []
    for chunk, conversation, category, distance in rows:
        if conv_counts[conversation.id] < 2:
            deduped_rows.append((chunk, conversation, category, distance))
            conv_counts[conversation.id] += 1
    
    # Final truncation to requested limit
    rows = deduped_rows[:limit]
    
    # Prepare highlighting regex for individual terms
    highlight_regex = None
    terms = [re.escape(t) for t in query.split() if t]
    if terms:
        pattern = "|".join(terms)
        highlight_regex = re.compile(f"({pattern})", re.IGNORECASE)
    
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
                "role": m.role,
                "content": m.content
            })
            
        source_user_message = None
        source_assistant_message = None
        
        l2_start_idx = s_idx
        l2_end_idx = e_idx

        # Collect all messages covered by the chunk [s_idx, e_idx]
        # We use a fresh query to ensure we have the full content and indices
        stmt_chunk_msgs = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.message_index >= s_idx)
            .where(Message.message_index <= e_idx)
            .order_by(Message.message_index)
        )
        chunk_msgs = (await db.execute(stmt_chunk_msgs)).scalars().all()
        
        user_parts = []
        assistant_parts = []
        for m in chunk_msgs:
            if m.role == "user":
                user_parts.append(m.content)
            else:
                assistant_parts.append(m.content)
        
        source_user_is_match = bool(user_parts)
        source_assistant_is_match = bool(assistant_parts)

        # Determine current state and fill gaps to form exactly one exchange
        if user_parts:
            source_user_message = "\n\n".join(user_parts)
        if assistant_parts:
            source_assistant_message = "\n\n".join(assistant_parts)
            
        # Ensure we have an Assistant response if we matched a User thought
        if not source_assistant_message:
            stmt_next_a = (
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .where(Message.message_index > e_idx)
                .where(Message.role == "assistant")
                .order_by(Message.message_index.asc())
                .limit(1)
            )
            next_a = (await db.execute(stmt_next_a)).scalar()
            if next_a:
                source_assistant_message = next_a.content
                l2_end_idx = next_a.message_index

        # Ensure we have a User query if we matched an Assistant thought
        if not source_user_message:
            stmt_prev_u = (
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .where(Message.message_index < s_idx)
                .where(Message.role == "user")
                .order_by(Message.message_index.desc())
                .limit(1)
            )
            prev_u = (await db.execute(stmt_prev_u)).scalar()
            if prev_u:
                source_user_message = prev_u.content
                l2_start_idx = prev_u.message_index
            
        # Layer 3 Context - Previous Exchange
        prev_exchange_user_message = None
        prev_exchange_assistant_message = None
        stmt_prev2 = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.message_index < l2_start_idx)
            .order_by(Message.message_index.desc())
            .limit(2)
        )
        prev2_msgs = (await db.execute(stmt_prev2)).scalars().all()
        if prev2_msgs:
            m1 = prev2_msgs[0]
            if m1.role == "assistant":
                prev_exchange_assistant_message = m1.content
                if len(prev2_msgs) > 1 and prev2_msgs[1].role == "user":
                    prev_exchange_user_message = prev2_msgs[1].content
            elif m1.role == "user":
                prev_exchange_user_message = m1.content

        # Layer 3 Context - Next Exchange
        next_exchange_user_message = None
        next_exchange_assistant_message = None
        stmt_next2 = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.message_index > l2_end_idx)
            .order_by(Message.message_index.asc())
            .limit(2)
        )
        next2_msgs = (await db.execute(stmt_next2)).scalars().all()
        if next2_msgs:
            n1 = next2_msgs[0]
            if n1.role == "user":
                next_exchange_user_message = n1.content
                if len(next2_msgs) > 1 and next2_msgs[1].role == "assistant":
                    next_exchange_assistant_message = next2_msgs[1].content
            elif n1.role == "assistant":
                next_exchange_assistant_message = n1.content
            
        raw_text = chunk.chunk_text or ""
        highlighted_text = raw_text
        if highlight_regex:
            highlighted_text = highlight_regex.sub(r"[[\1]]", raw_text)
            
            # Highlight all exchange content strings
            if source_user_message:
                source_user_message = highlight_regex.sub(r"[[\1]]", source_user_message)
            if source_assistant_message:
                source_assistant_message = highlight_regex.sub(r"[[\1]]", source_assistant_message)
            if prev_exchange_user_message:
                prev_exchange_user_message = highlight_regex.sub(r"[[\1]]", prev_exchange_user_message)
            if prev_exchange_assistant_message:
                prev_exchange_assistant_message = highlight_regex.sub(r"[[\1]]", prev_exchange_assistant_message)
            if next_exchange_user_message:
                next_exchange_user_message = highlight_regex.sub(r"[[\1]]", next_exchange_user_message)
            if next_exchange_assistant_message:
                next_exchange_assistant_message = highlight_regex.sub(r"[[\1]]", next_exchange_assistant_message)

        out.append({
            "conversation_id": conversation.id,
            "conversation_title": conversation.title,
            "conversation_summary": conversation.summary,
            "category_id": conversation.category_id,
            "category_name": category.name if category else None,
            "matched_chunk_text": highlighted_text,
            "similarity_score": sim_score,
            "message_start_index": chunk.message_start_index,
            "message_end_index": chunk.message_end_index,
            "chunk_index": chunk.chunk_index,
            "message_count": total_msgs,
            "relative_position": rel_pos,
            "surrounding_messages": surrounding,
            "source_user_message": source_user_message,
            "source_assistant_message": source_assistant_message,
            "source_user_is_match": source_user_is_match,
            "source_assistant_is_match": source_assistant_is_match,
            "previous_exchange_user_message": prev_exchange_user_message,
            "previous_exchange_assistant_message": prev_exchange_assistant_message,
            "next_exchange_user_message": next_exchange_user_message,
            "next_exchange_assistant_message": next_exchange_assistant_message
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
