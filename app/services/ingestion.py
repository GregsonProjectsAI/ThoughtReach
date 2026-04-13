from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from app.models.models import ImportJob, Conversation, Message, Chunk, utcnow
from app.schemas.api import PasteImportRequest
from app.services.embeddings import generate_embeddings
from typing import List
import hashlib
import logging
import re as _re
import time
import uuid

logger = logging.getLogger(__name__)


def compute_fingerprint(raw_text: str) -> str:
    """Return SHA256 hex digest of the raw text for duplicate detection."""
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def detect_source_family(raw_text: str) -> str:
    """
    Detect the deterministic source family from surface format patterns.
    Does not infer roles or modify content.
    """
    if not raw_text:
        return "unknown"
        
    preview = raw_text[:2000]
    
    # WhatsApp timestamp/name markers: e.g. [12/31/23, 11:59 PM] Name: 
    if _re.search(r"^\[?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}[, ]+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\]?\s+[^:]+:", preview, flags=_re.MULTILINE):
        return "whatsapp"
        
    # Generic timestamped chat logs
    # e.g. "2024-01-31 14:22 - Alice:", "31 Jan 2024, 14:22 - Bob:"
    ts_chat_pattern = r"^(?:\d{1,4}[A-Za-z0-9\-\./, ]{2,20}\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|am|pm))?)\s*(?:-\s*)?([A-Z][A-Za-z0-9\.\-]{0,20}(?: [A-Za-z0-9\.\-]{1,20}){0,2}):\s+(?=\S)"
    ts_chat_matches = _re.findall(ts_chat_pattern, preview, flags=_re.MULTILINE)
    if len(ts_chat_matches) >= 2:
        return "timestamp_chat"
        
    # Email thread headers
    if _re.search(r"^(From|To|Date|Subject):\s", preview, flags=_re.MULTILINE):
        return "email_thread"
        
    # ChatGPT export/copy-paste markers
    if _re.search(r"(?i)^(user|chatgpt)\n", preview, flags=_re.MULTILINE):
        return "chatgpt"

    # Claude transcript markers
    if _re.search(r"(?i)^(human|assistant):\s", preview, flags=_re.MULTILINE):
        return "claude"

    # Named generic transcripts (e.g. "Speaker 1:", "Alice:")
    # Requires capitalized start, up to 2 words, total name length <= 25, colon and a space
    # Threshold increased to 3 to ensure genuinely repeated structure.
    transcript_pattern = r"^([A-Z][A-Za-z0-9\.\-]{0,15}(?: [A-Za-z0-9\.\-]{1,15}){0,1}):\s+(?=\S)"
    transcript_matches = _re.findall(transcript_pattern, preview, flags=_re.MULTILINE)
    if len(transcript_matches) >= 3:
        return "transcript"
        
    return "unknown"


def parse_chatgpt_export(raw_text: str) -> list[dict]:
    lines = raw_text.strip().splitlines()
    messages = []
    current_role = "unknown"
    current_lines = []
    for line in lines:
        lower_line = line.strip().lower()
        if lower_line in ("user", "chatgpt", "assistant"):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append({"role": current_role, "content": content})
                current_lines = []
            current_role = "user" if lower_line == "user" else "assistant"
        else:
            current_lines.append(line.rstrip())
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"role": current_role, "content": content})
    return messages

def parse_claude_export(raw_text: str) -> list[dict]:
    lines = raw_text.strip().splitlines()
    messages = []
    current_role = "unknown"
    current_lines = []
    for line in lines:
        stripped = line.strip()
        lower_line = stripped.lower()
        if lower_line.startswith("human:") or lower_line.startswith("assistant:"):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append({"role": current_role, "content": content})
                current_lines = []
            if lower_line.startswith("human:"):
                current_role = "user"
                inline = stripped[6:].strip()
            else:
                current_role = "assistant"
                inline = stripped[10:].strip()
            if inline:
                current_lines.append(inline)
        else:
            current_lines.append(line.rstrip())
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"role": current_role, "content": content})
    return messages

def parse_whatsapp_export(raw_text: str) -> list[dict]:
    pattern = _re.compile(r"^\[?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}[, ]+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\]?\s+([^:]+):\s*(.*)$")
    lines = raw_text.strip().splitlines()
    messages = []
    current_role = "unknown"
    current_lines = []
    for line in lines:
        m = pattern.match(line.strip())
        if m:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append({"role": current_role, "content": content})
                current_lines = []
            current_role = m.group(1).strip()
            inline = m.group(2).strip()
            if inline:
                current_lines.append(inline)
        else:
            current_lines.append(line.rstrip())
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"role": current_role, "content": content})
    return messages

def parse_email_thread(raw_text: str) -> list[dict]:
    lines = raw_text.strip().splitlines()
    messages = []
    current_role = "unknown"
    current_lines = []
    header_pattern = _re.compile(r"^(From|To|Date|Subject|Sent|Cc):\s*(.*)", _re.IGNORECASE)
    was_header = False
    
    for line in lines:
        m = header_pattern.match(line)
        if m:
            header_name = m.group(1).lower()
            header_value = m.group(2).strip()
            if not was_header:
                if current_lines:
                    content = "\n".join(current_lines).strip()
                    if content:
                        messages.append({"role": current_role, "content": content})
                    current_lines = []
                current_role = "unknown"
            
            if header_name == "from" and current_role == "unknown":
                current_role = header_value
                
            current_lines.append(line)
            was_header = True
        else:
            if line.strip() != "":
                was_header = False
            current_lines.append(line)
            
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"role": current_role, "content": content})
            
    return messages

def parse_transcript_export(raw_text: str) -> list[dict]:
    pattern = _re.compile(r"^([A-Z][A-Za-z0-9\.\-]{0,20}(?: [A-Za-z0-9\.\-]{1,20}){0,2}):\s+(.*)$")
    lines = raw_text.strip().splitlines()
    messages = []
    current_role = "unknown"
    current_lines = []
    
    for line in lines:
        m = pattern.match(line.strip())
        if m:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append({"role": current_role, "content": content})
                current_lines = []
            
            role_candidate = m.group(1).strip()
            # Explicit USER / ASSISTANT preserved if identical to those markers
            if role_candidate.lower() == "user":
                current_role = "user"
            elif role_candidate.lower() == "assistant":
                current_role = "assistant"
            else:
                current_role = role_candidate
                
            inline = m.group(2).strip()
            if inline:
                current_lines.append(inline)
        else:
            current_lines.append(line.rstrip())
            
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"role": current_role, "content": content})
            
    return messages

def parse_timestamp_chat_export(raw_text: str) -> list[dict]:
    pattern = _re.compile(r"^(?:\d{1,4}[A-Za-z0-9\-\./, ]{2,20}\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|am|pm))?)\s*(?:-\s*)?([A-Z][A-Za-z0-9\.\-]{0,20}(?: [A-Za-z0-9\.\-]{1,20}){0,2}):\s+(.*)$")
    lines = raw_text.strip().splitlines()
    messages = []
    current_role = "unknown"
    current_lines = []
    
    for line in lines:
        m = pattern.match(line.strip())
        if m:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    messages.append({"role": current_role, "content": content})
                current_lines = []
            
            role_candidate = m.group(1).strip()
            # Explicit USER / ASSISTANT preserved if identical to those markers
            if role_candidate.lower() == "user":
                current_role = "user"
            elif role_candidate.lower() == "assistant":
                current_role = "assistant"
            else:
                current_role = role_candidate
                
            inline = m.group(2).strip()
            if inline:
                current_lines.append(inline)
        else:
            current_lines.append(line.rstrip())
            
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            messages.append({"role": current_role, "content": content})
            
    return messages

def parse_raw_text_to_messages(raw_text: str, source_type: str = "structured") -> tuple[List[dict], str]:
    """
    Deterministically split raw_text into message dicts.

    Step 1 — Speaker-based parsing (structured_conversation gate):
        Detects lines starting with 'User:' or 'Assistant:' (case-insensitive).
        Only if such explicit markers are present is the result classified as a
        structured conversation; roles are preserved exactly as marked.
        Continuation lines are appended to the current speaker's content.
        Strict order is preserved.

    Step 2 — Fallback (raw_text_chat):
        Splits on two or more consecutive newlines.
        ALL paragraphs receive role='unknown' — no alternation, no inference.
        Original paragraph boundaries are preserved exactly.

    Guarantees:
        - All content is stripped of leading/trailing whitespace.
        - Empty segments are always discarded.
        - Result is never empty: if all parsing yields nothing, the entire
          raw_text is wrapped as a single {"role": "unknown"} message.

    Output format: ([{"role": "user"|"assistant"|"unknown", "content": str}, ...], final_source_type: str)
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
        # Fallback (raw_text_chat): split on two or more consecutive newlines.
        # No role inference — every paragraph is stored as 'unknown' to avoid
        # inventing speaker attribution for ambiguous imports.
        paragraphs = _re.split(r"\n{2,}", raw)
        for para in paragraphs:
            content = para.strip()
            if content:
                messages.append({"role": "unknown", "content": content})

    # Final safety guarantee: never return an empty list
    if not messages:
        messages = [{"role": "unknown", "content": raw}]


    final_source_type = "structured_conversation" if has_speakers else "raw_text_chat"
    return messages, final_source_type


async def ingest_paste_direct(
    title: str,
    raw_text: str,
    db: AsyncSession,
    category_id: str | None = None,
    source_type: str = "structured"
) -> tuple[bool, str | None, dict | None]:
    """
    Synchronously ingest a single pasted conversation.
    Returns (was_ingested: bool, conversation_id: str | None, perf: dict | None).
    Returns (False, None, None) if the content is a duplicate.
    The perf dict contains per-stage timings and import size metrics;
    all timing values are in seconds, rounded to 3 decimal places.
    """
    t_total_start = time.perf_counter()

    # ── Stage 1: Fingerprint + duplicate check ────────────────────────────────
    t0 = time.perf_counter()
    fingerprint = compute_fingerprint(raw_text)
    existing = await db.execute(
        select(Conversation).where(Conversation.content_fingerprint == fingerprint)
    )
    if existing.scalars().first():
        t_total = time.perf_counter() - t_total_start
        t_duplicate_check = time.perf_counter() - t0
        perf = {
            "import_size_chars": len(raw_text),
            "total_s": round(t_total, 3),
            "stages": {
                "duplicate_check_s": round(t_duplicate_check, 3)
            }
        }
        return False, None, perf
    t_duplicate_check = time.perf_counter() - t0

    # ── Stage 2: Parse raw text into paragraph/message blocks ────────────────
    t0 = time.perf_counter()
    detected_family = detect_source_family(raw_text)
    
    if detected_family == "chatgpt":
        messages = parse_chatgpt_export(raw_text)
        final_source_type = "structured_conversation"
    elif detected_family == "claude":
        messages = parse_claude_export(raw_text)
        final_source_type = "structured_conversation"
    elif detected_family == "whatsapp":
        messages = parse_whatsapp_export(raw_text)
        final_source_type = "structured_conversation"
    elif detected_family == "email_thread":
        messages = parse_email_thread(raw_text)
        final_source_type = "structured_conversation"
    elif detected_family == "transcript":
        messages = parse_transcript_export(raw_text)
        final_source_type = "structured_conversation"
    elif detected_family == "timestamp_chat":
        messages = parse_timestamp_chat_export(raw_text)
        final_source_type = "structured_conversation"
    else:
        messages, final_source_type = parse_raw_text_to_messages(raw_text, source_type)
        
    if not messages:
        messages = [{"role": "unknown", "content": raw_text.strip()}]
    t_parse = time.perf_counter() - t0
    paragraph_count = len(messages)

    # ── Stage 3: Create conversation + messages + build chunk list ────────────
    # Note: per-message DB flushes are interleaved with chunking inside this
    # stage because the current pipeline requires msg.id before building chunks.
    t0 = time.perf_counter()

    conv = Conversation(
        title=title,
        source_type=final_source_type,
        source_family=detected_family,
        raw_text=raw_text,
        content_fingerprint=fingerprint,
        category_id=category_id,
    )
    db.add(conv)
    await db.flush()

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
    t_msg_chunk_build = time.perf_counter() - t0
    chunk_count = len(flat_text_chunks)



    # ── Stage 4: Embedding generation ─────────────────────────────────────────
    t_embed = 0.0
    embedding_count = 0
    if flat_text_chunks:
        t0 = time.perf_counter()
        embeddings = await generate_embeddings(flat_text_chunks)
        t_embed = time.perf_counter() - t0
        embedding_count = len(embeddings)

        # ── Stage 5: Chunk DB inserts + final commit ──────────────────────────
        # Build all chunk rows as plain dicts and execute a single bulk INSERT.
        # This eliminates N ORM object constructions and sends one round-trip
        # to PostgreSQL instead of relying on the ORM flush to batch rows.
        t0 = time.perf_counter()
        chunk_rows = [
            {
                "id": uuid.uuid4(),
                "conversation_id": conv.id,
                "message_start_index": meta["message_index"],
                "message_end_index": meta["message_index"],
                "chunk_index": chunk_index_counter,
                "chunk_position_sub": meta["chunk_position_sub"],
                "chunk_text": meta["text_chunk"],
                "embedding": emb,
                "created_at": utcnow(),
            }
            for chunk_index_counter, (meta, emb) in enumerate(zip(all_chunks_metadata, embeddings))
        ]
        await db.execute(insert(Chunk).values(chunk_rows))
        await db.commit()
        t_db_write = time.perf_counter() - t0
    else:
        await db.commit()
        t_db_write = 0.0

    t_total = time.perf_counter() - t_total_start

    perf: dict = {
        "import_size_chars": len(raw_text),
        "paragraph_count": paragraph_count,
        "chunk_count": chunk_count,
        "embedding_count": embedding_count,
        "total_s": round(t_total, 3),
        "stages": {
            "duplicate_check_s": round(t_duplicate_check, 3),
            "parse_s": round(t_parse, 3),
            "msg_and_chunk_build_s": round(t_msg_chunk_build, 3),
            "embed_s": round(t_embed, 3),
            "db_write_s": round(t_db_write, 3),
        },
    }

    logger.info(
        "[ingest_paste] title=%r source_type=%s chars=%d paras=%d chunks=%d embeds=%d "
        "total=%.3fs  [dup_check=%.3f parse=%.3f msg+chunk=%.3f embed=%.3f db_write=%.3f]",
        title, source_type,
        perf["import_size_chars"], perf["paragraph_count"],
        perf["chunk_count"], perf["embedding_count"],
        perf["total_s"],
        perf["stages"]["duplicate_check_s"],
        perf["stages"]["parse_s"],
        perf["stages"]["msg_and_chunk_build_s"],
        perf["stages"]["embed_s"],
        perf["stages"]["db_write_s"],
    )

    return True, str(conv.id), perf

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
            
            # Detect family deterministic
            detected_family = "unknown"
            if getattr(conv_data, "raw_text", None):
                detected_family = detect_source_family(conv_data.raw_text)

            conv = Conversation(
                title=conv_data.title,
                source_type=conv_data.source_type,
                source_family=detected_family,
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
