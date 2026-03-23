from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import ImportJob, Conversation, Message, Chunk, utcnow
from app.schemas.api import PasteImportRequest
from app.services.embeddings import generate_embeddings
from typing import List

def simple_chunk_text(text: str, max_words: int = 250) -> List[str]:
    """Basic chunking by words to preserve some semantics."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i:i + max_words]))
    return chunks

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
            
            import logging
            logger = logging.getLogger(__name__)

            full_text = conv_data.raw_text
            if not full_text and conv_data.messages:
                full_text = "\n".join(f"{m.role}: {m.content}" for m in conv_data.messages)
                
            if conv.summary:
                logger.info(f"Skipped summary generation for {conv.id}: already exists")
            elif not full_text:
                logger.info(f"Skipped summary generation for {conv.id}: no usable source text")
            else:
                from app.services.embeddings import generate_summary
                conv.summary = await generate_summary(full_text)
                if conv.summary:
                    logger.info(f"Completed summary generation successfully for {conv.id}")
                else:
                    logger.warning(f"Failed summary generation for {conv.id}: ignored")
            
            chunk_index_counter = 0
            
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
                
                # Chunking
                text_chunks = simple_chunk_text(msg.content)
                if not text_chunks:
                    continue
                
                embeddings = await generate_embeddings(text_chunks)
                
                from app.core.config import settings
                if embeddings and settings.ALLOW_MOCK_EMBEDDINGS and embeddings[0][0] == 0.0:
                    job.notes = "Mock embeddings were used for local development."
                
                for i, (text_chunk, emb) in enumerate(zip(text_chunks, embeddings)):
                    chunk = Chunk(
                        conversation_id=conv.id,
                        message_start_index=msg.message_index or 0,
                        message_end_index=msg.message_index or 0,
                        chunk_index=chunk_index_counter,
                        chunk_text=text_chunk,
                        embedding=emb
                    )
                    db.add(chunk)
                    chunk_index_counter += 1
        
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
