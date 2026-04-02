import asyncio
import sys
import os

# Add the project root to sys.path so we can import app
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.models.models import Conversation, Message, Chunk
from app.db.session import AsyncSessionLocal
from app.services.ingestion import split_message_into_chunks
from app.services.embeddings import generate_embeddings

async def chunk_pirate():
    async with AsyncSessionLocal() as db:
        conv_id = 'da05e964-e422-4e7b-a3bd-5f8dbcfa73c4'
        stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.message_index)
        res = await db.execute(stmt)
        messages = res.scalars().all()
        
        if not messages:
            print("No messages found for pirate conversation.")
            return

        print(f"Found {len(messages)} messages. Chunking...")

        all_chunks_metadata = []
        flat_text_chunks = []
        
        for msg in messages:
            text_chunks = split_message_into_chunks(msg.content)
            for i, text_chunk in enumerate(text_chunks):
                flat_text_chunks.append(text_chunk)
                all_chunks_metadata.append({
                    "message_index": msg.message_index,
                    "chunk_position_sub": i,
                    "text_chunk": text_chunk
                })

        if flat_text_chunks:
            print(f"Generating embeddings for {len(flat_text_chunks)} chunks...")
            embeddings = await generate_embeddings(flat_text_chunks)
            
            if not embeddings:
                print("Failed to generate embeddings. (Check OpenAI keys or network)")
                return

            for i, (meta, emb) in enumerate(zip(all_chunks_metadata, embeddings)):
                chunk = Chunk(
                    conversation_id=conv_id,
                    message_start_index=meta["message_index"],
                    message_end_index=meta["message_index"],
                    chunk_index=i,
                    chunk_position_sub=meta["chunk_position_sub"],
                    chunk_text=meta["text_chunk"],
                    embedding=emb
                )
                db.add(chunk)
            await db.commit()
            print(f"Successfully created and committed {len(flat_text_chunks)} chunks for pirate conversation.")
        else:
            print("No chunks were generated from messages.")

if __name__ == "__main__":
    asyncio.run(chunk_pirate())
