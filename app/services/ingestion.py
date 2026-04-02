from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import ImportJob, Conversation, Message, Chunk, utcnow
from app.schemas.api import PasteImportRequest
from app.services.embeddings import generate_embeddings
from typing import List
import hashlib
import re as _re


def compute_fingerprint(raw_text: str) -> str:
    """Return SHA256 hex digest of the raw text for duplicate detection."""
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def parse_raw_text_to_messages(raw_text: str, source_type: str = "structured") -> List[dict]:
    """
    Deterministically split raw_text into message dicts.

    Step 1 — Speaker-based parsing:
        Detects lines starting with 'User:' or 'Assistant:' (case-insensitive).
        Continuation lines are appended to the current speaker's content.
        Strict order is preserved.

    Step 2 — Fallback (double-newline split):
        Splits on two or more consecutive newlines.
        Assigns 'user' / 'assistant' roles by alternating index (0 → user).

    Guarantees:
        - All content is stripped of leading/trailing whitespace.
        - Empty segments are always discarded.
        - Result is never empty: if all parsing yields nothing, the entire
          raw_text is wrapped as a single {"role": "user"} message.

    Output format: [{"role": "user"|"assistant", "content": str}, ...]
    """
    # Only match 'User:' or 'Assistant:' at the very start of a line.
    speaker_pattern = _re.compile(
        r"^(user|assistant)\s*:\s*(.*)$",
        _re.IGNORECASE
    )

    raw = raw_text.strip()
    lines = raw.splitlines()

    has_speakers = False
    if source_type != "raw":
        has_speakers = any(
            speaker_pattern.match(line.strip())
            for line in lines
            if line.strip()
        )

    messages: list[dict] = []

    if has_speakers:
        current_role: str = "user"
        current_lines: list[str] = []

        for line in lines:
            m = speaker_pattern.match(line.strip())
            if m:
                # Flush the current buffer before starting a new speaker block
                if current_lines:
                    content = "\n".join(current_lines).strip()
                    if content:
                        messages.append({"role": current_role, "content": content})
                    current_lines = []

                raw_role = m.group(1).lower()
                current_role = "assistant" if raw_role == "assistant" else "user"

                # The first line of a speaker block may already have inline content
                inline = m.group(2).strip()
                if inline:
                    current_lines.append(inline)
            else:
                # Continuation line — strip but keep (including blank lines as spacing)
                current_lines.append(line.rstrip())

        # Flush any remaining buffer
        if current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                messages.append({"role": current_role, "content": content})

    else:
        # Fallback: split on two or more consecutive newlines (paragraphs).
        paragraphs = _re.split(r"\n{2,}", raw)
        for i, para in enumerate(paragraphs):
            content = para.strip()
            if content:
                # Manual raw-text imports MUST NOT alternate roles.
                # Use 'user' as a generic container for all semantic paragraphs.
                if source_type == "raw":
                    role = "user"
                else:
                    # Dynamic alternation only occurs for default structured fallback.
                    role = "user" if (len(messages) % 2 == 0) else "assistant"
                messages.append({"role": role, "content": content})

    # Final safety guarantee: never return an empty list
    if not messages:
        messages = [{"role": "user", "content": raw}]

    return messages


async def ingest_paste_direct(
    title: str,
    raw_text: str,
    db: AsyncSession,
    category_id: str | None = None,
    source_type: str = "structured"
) -> tuple[bool, str | None]:
    """
    Synchronously ingest a single pasted conversation.
    Returns (was_ingested: bool, conversation_id: str | None).
    Returns (False, None) if the content is a duplicate.
    """
    fingerprint = compute_fingerprint(raw_text)

    # Duplicate check
    existing = await db.execute(
        select(Conversation).where(Conversation.content_fingerprint == fingerprint)
    )
    if existing.scalars().first():
        return False, None

    # Parse messages
    messages = parse_raw_text_to_messages(raw_text, source_type)
    if not messages:
        messages = [{"role": "user", "content": raw_text.strip()}]

    # Create conversation
    conv = Conversation(
        title=title,
        source_type=source_type,
        raw_text=raw_text,
        content_fingerprint=fingerprint,
        category_id=category_id,
    )
    db.add(conv)
    await db.flush()

    # Process messages → chunks → embeddings
    all_chunks_metadata = []
    flat_text_chunks = []
    
    for idx, msg_data in enumerate(messages):
        msg = Message(
            conversation_id=conv.id,
            role=msg_data["role"],
            message_index=idx,
            content=msg_data["content"],
        )
        db.add(msg)
        await db.flush()

        text_chunks = split_message_into_chunks(msg.content)
        if not text_chunks:
            continue
            
        for i, text_chunk in enumerate(text_chunks):
            flat_text_chunks.append(text_chunk)
            all_chunks_metadata.append({
                "message_index": msg.message_index,
                "chunk_position_sub": i,
                "text_chunk": text_chunk
            })

    if flat_text_chunks:
        embeddings = await generate_embeddings(flat_text_chunks)
        
        for chunk_index_counter, (meta, emb) in enumerate(zip(all_chunks_metadata, embeddings)):
            chunk = Chunk(
                conversation_id=conv.id,
                message_start_index=meta["message_index"],
                message_end_index=meta["message_index"],
                chunk_index=chunk_index_counter,
                chunk_position_sub=meta["chunk_position_sub"],
                chunk_text=meta["text_chunk"],
                embedding=emb,
            )
            db.add(chunk)

    await db.commit()
    return True, str(conv.id)

def split_message_into_chunks(text: str) -> List[str]:
    """
    Spec-compliant deterministic chunking for a single message.
    1. Split on double line breaks (paragraphs).
    2. Split on single line breaks if segment > 400 chars and contains '\n'.
    3. Trim whitespace and discard empty segments.
    4. Merge fragments < 20 chars with NEXT (default) or PREVIOUS (fallback).
    """
    if not text:
        return []
    
    # 1. Paragraph splits
    base_segments = [s.strip() for s in text.split('\n\n') if s.strip()]
    
    # 2. Line splits fallback
    intermediate_chunks = []
    for seg in base_segments:
        if len(seg) > 400 and '\n' in seg:
            # split on single newlines
            lines = [l.strip() for l in seg.split('\n') if l.strip()]
            intermediate_chunks.extend(lines)
        else:
            intermediate_chunks.append(seg)
            
    if not intermediate_chunks:
        return []
    
    # Phase 3: Single-pass, left-to-right merge.
    # Rule order (spec precedence):
    #   R1 (P1): Header-aware — len < 60 AND no terminal punctuation → merge with NEXT
    #   R2: Short fragment  — len < 20 → merge with NEXT (or PREVIOUS as fallback)
    # Each merge is applied immediately; the resulting segment is NOT re-evaluated.
    TERMINAL_PUNCT = ('.', '!', '?')
    merged_chunks = []
    temp_chunks = intermediate_chunks[:]
    i = 0
    while i < len(temp_chunks):
        chunk = temp_chunks[i]

        # R1 (P1 header-aware): short, no terminal punctuation — merge into NEXT,
        # append merged result immediately without re-evaluation, then advance past both.
        if len(chunk) < 60 and not chunk.rstrip().endswith(TERMINAL_PUNCT):
            if i + 1 < len(temp_chunks):
                merged = (chunk + " " + temp_chunks[i+1]).strip()
                merged_chunks.append(merged)
                i += 2  # advance past current and next; merged segment is NOT re-evaluated
                continue

        # R2: very short fragment — merge with NEXT or PREVIOUS
        if len(chunk) < 20:
            if i + 1 < len(temp_chunks):
                temp_chunks[i+1] = chunk + " " + temp_chunks[i+1]
            elif merged_chunks:
                merged_chunks[-1] = merged_chunks[-1] + " " + chunk
            else:
                merged_chunks.append(chunk)
        else:
            merged_chunks.append(chunk)

        i += 1

    return [c.strip() for c in merged_chunks if c.strip()]

async def process_paste_import(job_id, request: PasteImportRequest, db: AsyncSession):
    job = await db.get(ImportJob, job_id)
    if not job:
        return
    
    try:
        job.status = "processing"
        await db.commit()

        for conv_data in request.conversations:
            conv = Conversation(
                title=conv_data.title,
                source_type=conv_data.source_type,
                external_id=conv_data.external_id,
                created_at=conv_data.created_at,
                raw_text=conv_data.raw_text,
                summary=getattr(conv_data, "summary", None)
            )
            
            db.add(conv)
            await db.flush() # get conv.id

            # Process messages → chunks → embeddings
            conv_all_chunks_metadata = []
            conv_flat_text_chunks = []
            
            for idx, msg_data in enumerate(conv_data.messages):
                msg = Message(
                    conversation_id=conv.id,
                    role=msg_data.role,
                    message_index=msg_data.message_index if msg_data.message_index is not None else idx,
                    content=msg_data.content,
                    created_at=msg_data.created_at
                )
                db.add(msg)
                await db.flush() # get msg.id
                
                # Split message into chunks
                text_chunks = split_message_into_chunks(msg.content)
                if not text_chunks:
                    continue
                
                for i, text_chunk in enumerate(text_chunks):
                    conv_flat_text_chunks.append(text_chunk)
                    conv_all_chunks_metadata.append({
                        "message_index": msg.message_index,
                        "chunk_position_sub": i,
                        "text_chunk": text_chunk
                    })
            
            if conv_flat_text_chunks:
                embeddings = await generate_embeddings(conv_flat_text_chunks)
                
                from app.core.config import settings
                if embeddings and settings.ALLOW_MOCK_EMBEDDINGS and embeddings[0][0] == 0.0:
                    job.notes = "Mock embeddings were used for local development."
                
                for i, (meta, emb) in enumerate(zip(conv_all_chunks_metadata, embeddings)):
                    chunk = Chunk(
                        conversation_id=conv.id,
                        message_start_index=meta["message_index"],
                        message_end_index=meta["message_index"],
                        chunk_index=i,
                        chunk_position_sub=meta["chunk_position_sub"],
                        chunk_text=meta["text_chunk"],
                        embedding=emb
                    )
                    db.add(chunk)
        
        job.status = "completed"
        job.completed_at = utcnow()
        await db.commit()
    except Exception as e:
        await db.rollback()
        # Fetch the job again as rollback detached it
        job = await db.get(ImportJob, job_id)
        job.status = "failed"
        job.notes = str(e)
        job.completed_at = utcnow()
        await db.commit()
