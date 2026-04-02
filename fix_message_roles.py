"""
fix_message_roles.py
====================
Repairs Message.role values for conversations that were ingested via the
fallback double-newline split, where every message was incorrectly assigned
role='user'. Reassigns alternating user/assistant roles based on message_index.

SAFE: Only fixes conversations where ALL messages have role='user' AND
the conversation has more than 1 message (i.e., clearly a dialogue, not
genuinely a single-speaker raw text).

Usage:
    python fix_message_roles.py [--dry-run] [--conversation-id UUID]
"""

import asyncio
import argparse
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update
from collections import Counter

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings
from app.models.models import Conversation, Message


async def fix_roles(dry_run: bool = True, target_conv_id: str | None = None):
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # Fetch conversations to inspect
        stmt = select(Conversation)
        if target_conv_id:
            stmt = stmt.where(Conversation.id == target_conv_id)
        result = await db.execute(stmt)
        conversations = result.scalars().all()

        print(f"Checking {len(conversations)} conversation(s)...")
        fixed_count = 0

        for conv in conversations:
            # Fetch all messages for this conversation, ordered by index
            msg_stmt = (
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.message_index)
            )
            msgs_result = await db.execute(msg_stmt)
            msgs = msgs_result.scalars().all()

            if not msgs:
                continue

            # Check role distribution
            role_counts = Counter(m.role for m in msgs)
            total = len(msgs)
            all_user = role_counts.get("user", 0) == total
            singular = total == 1

            if not all_user or singular:
                # Skip: already has mixed roles OR is a single-message conv
                continue

            # This conversation appears to be a fallback-ingested dialogue
            # with all-user roles. Re-assign alternating roles.
            print(f"\nConversation: '{conv.title}' (id={conv.id})")
            print(f"  Messages: {total}, all role='user' — fixing...")

            for msg in msgs:
                new_role = "user" if (msg.message_index % 2 == 0) else "assistant"
                if dry_run:
                    print(f"  [DRY-RUN] msg_idx={msg.message_index}: '{msg.role}' → '{new_role}'  | {msg.content[:60]!r}")
                else:
                    msg.role = new_role
                    print(f"  msg_idx={msg.message_index}: '{new_role}'  | {msg.content[:60]!r}")

            if not dry_run:
                await db.commit()
                fixed_count += 1
                print(f"  ✅ Committed role fix for '{conv.title}'")
            else:
                fixed_count += 1

        mode = "DRY-RUN" if dry_run else "APPLIED"
        print(f"\n{mode}: {fixed_count} conversation(s) would be/were fixed.")
        if dry_run:
            print("Run with --apply to commit changes.")


def main():
    parser = argparse.ArgumentParser(description="Fix message roles in DB")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default is dry-run)")
    parser.add_argument("--conversation-id", default=None, help="Target a specific conversation by UUID")
    args = parser.parse_args()

    asyncio.run(fix_roles(dry_run=not args.apply, target_conv_id=args.conversation_id))


if __name__ == "__main__":
    main()
