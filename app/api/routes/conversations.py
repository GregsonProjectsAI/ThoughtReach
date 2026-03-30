from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.schemas.api import ConversationOut, ConversationCategoryUpdate, ConversationTagsUpdate, ConversationSummaryOut, ConversationSummariesResponse
from app.models.models import Conversation, Category, Tag, conversation_tags
from app.services.embeddings import generate_summary

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    tag_ids: list[UUID] = Query(default=[]),
    category_ids: list[UUID] = Query(default=[])
):
    stmt = select(Conversation).options(
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    )
    
    if category_ids:
        stmt = stmt.where(Conversation.category_id.in_(category_ids))
    
    if tag_ids:
        stmt = stmt.join(conversation_tags).where(conversation_tags.c.tag_id.in_(tag_ids)).distinct()
    
    stmt = stmt.order_by(Conversation.imported_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.get("/summaries", response_model=ConversationSummariesResponse)
async def list_conversation_summaries(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    tag_ids: list[UUID] = Query(default=[]),
    category_ids: list[UUID] = Query(default=[]),
    include_count: bool = False,
    sort_by: str = Query(default="recent", pattern="^(recent|length)$"),
    include_top_words: bool = False,
    top_words_limit: int = Query(default=10, le=50, ge=1),
    group_by_top_word: bool = False,
    group_only: bool = False,
    include_insight: bool = False,
    max_group_insights: int = Query(default=5, le=10, ge=1)
):
    base_stmt = select(Conversation).where(Conversation.summary.isnot(None))
    
    if category_ids:
        base_stmt = base_stmt.where(Conversation.category_id.in_(category_ids))
    
    if tag_ids:
        base_stmt = base_stmt.join(conversation_tags).where(conversation_tags.c.tag_id.in_(tag_ids)).distinct()
    
    total_count = None
    if include_count:
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_count = (await db.execute(count_stmt)).scalar() or 0
    
    if sort_by == "length":
        stmt = base_stmt.order_by(func.length(Conversation.summary).desc()).offset(offset).limit(limit)
    else:
        stmt = base_stmt.order_by(Conversation.imported_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    summaries = list(result.scalars().all())
    
    top_words = None
    grouped = None
    
    if (include_top_words or group_by_top_word) and summaries:
        import re
        from collections import Counter, defaultdict
        stop_words = {
            "the", "and", "was", "for", "that", "with", "this", "from",
            "are", "were", "been", "has", "had", "have", "not", "but",
            "its", "also", "about", "into", "more", "their", "they",
            "which", "would", "could", "should", "will", "can", "how",
            "than", "then", "what", "when", "where", "who", "your",
            "you", "all", "some", "any", "each", "both", "one", "two",
        }
        word_counts = Counter()
        per_summary_words = {}
        for s in summaries:
            if s.summary:
                words = re.findall(r"[a-z]+", s.summary.lower())
                filtered = [w for w in words if len(w) >= 3 and w not in stop_words]
                word_counts.update(filtered)
                per_summary_words[s.id] = Counter(filtered)
        
        sorted_words = sorted(word_counts.items(), key=lambda x: (-x[1], x[0]))[:top_words_limit]
        if include_top_words:
            top_words = [{"word": w, "count": c} for w, c in sorted_words]
        
        if group_by_top_word and sorted_words:
            top_word_set = [w for w, _ in sorted_words]
            groups: dict[str, list] = defaultdict(list)
            for s in summaries:
                sw = per_summary_words.get(s.id, Counter())
                best_word = None
                best_count = 0
                for tw in top_word_set:
                    if sw[tw] > best_count:
                        best_count = sw[tw]
                        best_word = tw
                group_key = best_word if best_word else "other"
                groups[group_key].append(ConversationSummaryOut.model_validate(s, from_attributes=True))
            grouped = dict(groups)
    
    # Shared async helper to call LLM for a list of summary strings
    async def _generate_insight(texts: list[str]) -> str | None:
        from app.services.embeddings import client as openai_client
        import asyncio
        
        # Guard: max 20 summaries for cost/context control
        if len(texts) > 20:
            texts = texts[:20]
            
        combined = "\n".join(f"- {t}" for t in texts if t and t.strip())
        if len(combined) < 100:
            return None
        if len(combined) > 8000:
            combined = combined[:8000] + "\n...[truncated]"
        try:
            resp = await asyncio.wait_for(
                openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You summarize themes across multiple conversation summaries in 2-4 concise sentences."},
                        {"role": "user", "content": f"Identify the main themes across these conversation summaries:\n\n{combined}"}
                    ],
                    max_tokens=200,
                ),
                timeout=10.0
            )
            result = resp.choices[0].message.content.strip()
            return result[:497] + "..." if len(result) > 500 else result
        except Exception:
            # Fallback for timeout, rate-limits, or API errors
            return None
    
    insight = None
    if include_insight and summaries:
        all_texts = [s.summary for s in summaries if s.summary and s.summary.strip()]
        insight = await _generate_insight(all_texts)
    
    # When grouping is active, optionally generate per-group insights and restructure
    if grouped is not None and include_insight:
        enriched: dict[str, dict] = {}
        # Deterministic ordering: largest groups first, then name ascending as tiebreaker
        ordered_keys = sorted(grouped.keys(), key=lambda k: (-len(grouped[k]), k))
        for i, group_key in enumerate(ordered_keys):
            items = grouped[group_key]
            if i < max_group_insights:
                group_texts = [item.summary for item in items if item.summary and item.summary.strip()]
                group_insight = await _generate_insight(group_texts)
            else:
                group_insight = None  # Beyond limit — skip LLM call
            enriched[group_key] = {"items": items, "insight": group_insight, "count": len(items)}
        grouped = enriched  # type: ignore
    elif grouped is not None:
        # No per-group insight — keep simple {items: [...]} structure for consistency
        grouped = {k: {"items": v, "insight": None, "count": len(v)} for k, v in grouped.items()}
    
    if group_only and grouped is not None:
        return ConversationSummariesResponse(summaries=[], grouped_summaries=grouped, insight=insight, total_count=total_count)
    
    return ConversationSummariesResponse(summaries=summaries, total_count=total_count, top_words=top_words, grouped_summaries=grouped, insight=insight)

@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(conversation_id: UUID, db: AsyncSession = Depends(get_db), highlight_query: Optional[str] = None):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    ).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    out = ConversationOut.model_validate(conv)
    if highlight_query and out.messages:
        import re
        terms = [re.escape(t) for t in highlight_query.split() if t]
        if terms:
            pattern = "|".join(terms)
            highlight_regex = re.compile(f"({pattern})", re.IGNORECASE)
            for msg in out.messages:
                msg.content = highlight_regex.sub(r"[[\1]]", msg.content)
    return out

@router.patch("/{conversation_id}/category", response_model=ConversationOut)
async def update_conversation_category(conversation_id: UUID, payload: ConversationCategoryUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    ).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if payload.category_id is not None:
        cat_stmt = select(Category).where(Category.id == payload.category_id)
        cat_result = await db.execute(cat_stmt)
        cat = cat_result.scalars().first()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
            
    conv.category_id = payload.category_id
    await db.commit()
    await db.refresh(conv)
    
    return conv

@router.put("/{conversation_id}/tags", response_model=ConversationOut)
async def update_conversation_tags(conversation_id: UUID, payload: ConversationTagsUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    ).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    tags = []
    if payload.tag_ids:
        tags_stmt = select(Tag).where(Tag.id.in_(payload.tag_ids))
        tags_result = await db.execute(tags_stmt)
        tags = list(tags_result.scalars().all())
        
        # Verify all provided tag IDs exist natively
        if len(tags) != len(set(payload.tag_ids)):
            raise HTTPException(status_code=404, detail="One or more tags not found")
            
    conv.tags = tags
    await db.commit()
    await db.refresh(conv)
    
    return conv

@router.post("/{conversation_id}/generate-summary", response_model=ConversationOut)
async def generate_conversation_summary(conversation_id: UUID, force: bool = False, db: AsyncSession = Depends(get_db)):
    stmt = select(Conversation).options(
        selectinload(Conversation.messages),
        selectinload(Conversation.category),
        selectinload(Conversation.tags)
    ).where(Conversation.id == conversation_id)
    result = await db.execute(stmt)
    conv = result.scalars().first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Skip regeneration if summary already exists and force is not set
    if conv.summary and not force:
        return conv
    
    if not conv.messages:
        raise HTTPException(status_code=422, detail="Conversation has no messages to summarize")
    
    # Assemble message text from conversation messages
    sorted_messages = sorted(conv.messages, key=lambda m: m.message_index)
    text = "\n".join(f"{m.role}: {m.content}" for m in sorted_messages)
    
    summary = await generate_summary(text)
    if not summary:
        raise HTTPException(status_code=500, detail="Summary generation failed")
    
    conv.summary = summary
    await db.commit()
    await db.refresh(conv)
    
    return conv
