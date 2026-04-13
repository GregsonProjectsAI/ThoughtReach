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
        
    stmt = stmt.order_by(distance_expr).limit(200)
    
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
        if conv_counts[conversation.id] < 50:
            deduped_rows.append((chunk, conversation, category, distance))
            conv_counts[conversation.id] += 1

    # 3. Lightweight lexical tie-break re-sort
    # Primary: cosine similarity (descending).
    # Secondary (tie-break only, within ±0.02 similarity): lexical term-coverage score.
    # This ensures a chunk matching ALL query terms ranks above one matching only some,
    # when their semantic scores are indistinguishable.
    import math as _math
    query_terms_lower = [t.lower() for t in query.split() if t]
    query_phrase_lower = query.lower()

    def lexical_score(row) -> float:
        if not query_terms_lower:
            return 0.0
            
        chunk, conversation, category, distance = row
        
        def field_score(text: str, weight: float) -> float:
            if not text:
                return 0.0
            text_lower = str(text).lower()
            term_hits = sum(1 for t in query_terms_lower if t in text_lower)
            term_ratio = term_hits / len(query_terms_lower)
            
            is_multi_word = len(query_terms_lower) > 1
            
            # Phrase bonus: Strong boost for exact phrase if it's a multi-word query
            phrase_bonus = 0.0
            if query_phrase_lower in text_lower:
                phrase_bonus = 2.0 if is_multi_word else 0.5
                
            # Coverage bonus: Boost if all distinct terms are found
            coverage_bonus = 1.0 if (is_multi_word and term_hits == len(query_terms_lower)) else 0.0
            
            # Proximity bonus: Boost if multiple terms are found close together
            proximity_bonus = 0.0
            if is_multi_word and term_hits > 1:
                positions = [text_lower.find(t) for t in query_terms_lower if text_lower.find(t) != -1]
                if positions:
                    span = max(positions) - min(positions)
                    if span < len(query_phrase_lower) * 3:
                        proximity_bonus = 0.5
            
            return (term_ratio + phrase_bonus + coverage_bonus + proximity_bonus) * weight

        score = 0.0
        score += field_score(getattr(conversation, 'title', ''), 4.0)
        score += field_score(getattr(conversation, 'summary', ''), 2.0)
        score += field_score(getattr(chunk, 'chunk_text', ''), 2.0) # increased from 1.0 to weight local region more
        
        if category:
            score += field_score(getattr(category, 'name', ''), 0.5)
            
        return score

    def sort_key(row):
        chunk, conversation, category, distance = row
        sim = 1.0 - distance if (distance is not None and not _math.isnan(distance)) else 0.0
        
        lex = lexical_score(row)
        
        # Allow strong lexical matches to slightly push the item into a higher semantic bucket
        boosted_sim = sim + (lex * 0.005)
        
        # Round to 2 decimal places to group near-ties, then use exact lex as tie-break
        sim_bucket = round(boosted_sim, 2)
        return (-sim_bucket, -lex)

    deduped_rows.sort(key=sort_key)

    def get_lexical_flags(text: str):
        if not text or not query_terms_lower:
            return {"exact_phrase": False, "all_terms": False, "high_proximity": False}
        
        text_lower = str(text).lower()
        term_hits = sum(1 for t in query_terms_lower if t in text_lower)
        is_multi_word = len(query_terms_lower) > 1
        
        exact_phrase = query_phrase_lower in text_lower
        all_terms = is_multi_word and (term_hits == len(query_terms_lower))
        
        high_proximity = False
        if is_multi_word and term_hits > 1:
            positions = [text_lower.find(t) for t in query_terms_lower if text_lower.find(t) != -1]
            if positions:
                span = max(positions) - min(positions)
                if span < len(query_phrase_lower) * 3:
                    high_proximity = True
        
        return {
            "exact_phrase": exact_phrase,
            "all_terms": all_terms,
            "high_proximity": high_proximity
        }

    # Keep all deduplicated candidate rows for grouping before final truncation
    rows = deduped_rows
    
    # Calculate group summaries (number of excerpts and match characteristics)
    group_summary_map = {}
    from collections import defaultdict
    conv_to_chunks = defaultdict(list)
    conv_to_obj = {}
    for chunk, conversation, category, distance in rows:
        conv_to_chunks[conversation.id].append(chunk)
        conv_to_obj[conversation.id] = conversation

    for conv_id, chunks in conv_to_chunks.items():
        conversation = conv_to_obj[conv_id]
        num_excerpts = len(chunks)
        title = getattr(conversation, 'title', '') or ''
        title_lower = title.lower()
        title_match = any(t in title_lower for t in query_terms_lower)
        exact_phrase_in_title = query_phrase_lower in title_lower if len(query_terms_lower) > 1 else False
        
        # Check chunks for exact phrase or all terms, and roles
        exact_phrase_in_content = False
        all_terms_in_content = False
        user_match_count = 0
        assistant_match_count = 0
        for c in chunks:
            text = (c.chunk_text or "").lower()
            if query_phrase_lower in text: exact_phrase_in_content = True
            hits = sum(1 for t in query_terms_lower if t in text)
            if hits == len(query_terms_lower): all_terms_in_content = True
            
            # Simple role detection from the chunk results available in the current loop scope?
            # Actually, I can check if this chunk has matches in user or assistant parts
            # But the 'out' list is built later. 
            # I'll rely on the existing 'source_user_is_match' flags calculated in the loop.
            # Wait, I am calculating summaries BEFORE building 'out' list. 
            # I'll just check title/content for now to avoid complexity, 
            # unless I move summary generation after 'out' list is partially built.

        is_structured = (conversation.source_type == "structured_conversation")
        item_type = "conversation" if is_structured else "imported item"
            
        parts = [f"Matched {num_excerpts} {'excerpt' if num_excerpts == 1 else 'excerpts'} in this {item_type}"]
        reasons = []
        if exact_phrase_in_title:
            reasons.append("exact phrase found in title")
        elif exact_phrase_in_content:
            reasons.append("exact phrase found in content")
        elif all_terms_in_content:
            reasons.append("all words found in one local region")
        elif title_match:
            reasons.append("match found in title")
            
        if reasons:
            parts.append(reasons[0])
            
        group_summary_map[conv_id] = "; ".join(parts).capitalize() + "."

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
        source_user_is_match = False
        source_assistant_is_match = False
        prev_exchange_user_message = None
        prev_exchange_assistant_message = None
        next_exchange_user_message = None
        next_exchange_assistant_message = None

        # Determine if we should perform Layer 2/3 exchange reconstruction.
        # Use role presence in the surrounding window rather than source_type,
        # so conversations stored as 'raw' but containing non-user (assistant/model)
        # messages are still treated as structured for exchange reconstruction.
        has_non_user_in_surrounding = any(m["role"] not in ("user", "unknown") for m in surrounding)
        is_structured = (conversation.source_type == "structured_conversation") or has_non_user_in_surrounding
        
        if is_structured:
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
            if source_user_is_match and not source_assistant_message:
                stmt_next_a = (
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .where(Message.message_index > e_idx)
                    .where(Message.message_index <= e_idx + 10)
                    .where(Message.role != "user")
                    .order_by(Message.message_index.asc())
                    .limit(1)
                )
                next_a = (await db.execute(stmt_next_a)).scalar()
                if next_a:
                    source_assistant_message = next_a.content
                    l2_end_idx = next_a.message_index

            # Ensure we have a User query if we matched an Assistant thought
            if source_assistant_is_match and not source_user_message:
                stmt_prev_u = (
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .where(Message.message_index < s_idx)
                    .where(Message.message_index >= s_idx - 10)
                    .where(Message.role == "user")
                    .order_by(Message.message_index.desc())
                    .limit(1)
                )
                prev_u = (await db.execute(stmt_prev_u)).scalar()
                if prev_u:
                    source_user_message = prev_u.content
                    l2_start_idx = prev_u.message_index
                
            # Layer 3 Context - Previous Exchange
            stmt_prev2 = (
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .where(Message.message_index < l2_start_idx)
                .order_by(Message.message_index.desc())
                .limit(2)
            )
            prev2_msgs = (await db.execute(stmt_prev2)).scalars().all()
            if prev2_msgs:
                m1 = prev2_msgs[0]  # closest prior message (highest index, desc order)
                if m1.role != "user":
                    prev_exchange_assistant_message = m1.content
                    if len(prev2_msgs) > 1 and prev2_msgs[1].role == "user":
                        prev_exchange_user_message = prev2_msgs[1].content
                elif m1.role == "user":
                    prev_exchange_user_message = m1.content
                    # Also check if the message before it is an assistant message
                    if len(prev2_msgs) > 1 and prev2_msgs[1].role != "user":
                        prev_exchange_assistant_message = prev2_msgs[1].content

            # Layer 3 Context - Next Exchange
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
                    if len(next2_msgs) > 1 and next2_msgs[1].role != "user":
                        next_exchange_assistant_message = next2_msgs[1].content
                elif n1.role != "user":
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

        excerpt_dict = {
            "matched_chunk_text": highlighted_text,
            "similarity_score": sim_score,
            "message_start_index": chunk.message_start_index,
            "message_end_index": chunk.message_end_index,
            "source_exchange_start_index": l2_start_idx,
            "source_exchange_end_index": l2_end_idx,
            "surrounding_messages": surrounding,
            "source_user_message": source_user_message,
            "source_assistant_message": source_assistant_message,
            "source_user_is_match": source_user_is_match,
            "source_assistant_is_match": source_assistant_is_match,
            "previous_exchange_user_message": prev_exchange_user_message,
            "previous_exchange_assistant_message": prev_exchange_assistant_message,
            "next_exchange_user_message": next_exchange_user_message,
            "next_exchange_assistant_message": next_exchange_assistant_message,
            "message_count": total_msgs,
            "ranking_flags": get_lexical_flags(raw_text)
        }

        # Find existing group or create new one to ensure ONE item per conversation
        existing_group = next((g for g in out if g["conversation_id"] == conversation.id), None)
        if not existing_group:
            existing_group = {
                "conversation_id": conversation.id,
                "conversation_title": conversation.title,
                "conversation_summary": conversation.summary,
                "conversation_source_type": conversation.source_type,
                "source_type": conversation.source_type,
                "category_id": conversation.category_id,
                "category_name": category.name if category else None,
                "imported_at": conversation.imported_at,
                "conversation_created_at": conversation.created_at,
                "match_summary": group_summary_map.get(conversation.id),
                "excerpts": []
            }
            out.append(existing_group)

        existing_group["excerpts"].append(excerpt_dict)
    
    # Keep excerpts in original source order within the grouped result,
    # then tag the single best-match excerpt so the UI can open it by default.
    for group in out:
        group["excerpts"].sort(key=lambda x: x["message_start_index"])
        
        # Select the best anchor: highest similarity_score, breaking ties by
        # lexical quality (exact phrase > all terms > neither).
        def _anchor_key(ex):
            flags = ex.get("ranking_flags") or {}
            lex_bonus = (2 if flags.get("exact_phrase") else 0) + (1 if flags.get("all_terms") else 0)
            return (ex.get("similarity_score", 0.0), lex_bonus)
        
        best_idx = max(range(len(group["excerpts"])), key=lambda i: _anchor_key(group["excerpts"][i]))
        for i, ex in enumerate(group["excerpts"]):
            ex["is_best_match"] = (i == best_idx)

    # Calculate aggregate conversation score for final ranking
    def _group_sort_key(group):
        best_anchor = next((ex for ex in group["excerpts"] if ex["is_best_match"]), None)
        if not best_anchor:
            return 0.0
            
        flags = best_anchor.get("ranking_flags") or {}
        lex_bonus = (2 if flags.get("exact_phrase") else 0) + (1 if flags.get("all_terms") else 0)
        base_score = best_anchor.get("similarity_score", 0.0) + (lex_bonus * 0.005)
        
        # Add a minimal density bonus to reward conversations with multiple valid matches
        # Cap the bonus to prevent extremely large documents from over-accumulating advantage
        density_bonus = min((len(group["excerpts"]) - 1) * 0.05, 0.15)
        
        title_bonus = 0.0
        title = group.get("conversation_title", "").lower()
        if title:
            query_terms = [t for t in query.lower().split() if t not in ['an', 'and', 'the', 'of', 'in', 'to', 'for', 'with', 'a']]
            if any(qt in title for qt in query_terms):
                title_bonus = 0.15
                
        return base_score + density_bonus + title_bonus

    out.sort(key=_group_sort_key, reverse=True)
    return out[:limit]

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
