
-- Fresh Pirate Import for Step 128C
-- This script manually performs the ingestion to verify role alternation at the data layer
BEGIN;

INSERT INTO conversations (id, title, source_type, content_fingerprint, imported_at)
VALUES ('da05e964-e422-4e7b-a3bd-5f8dbcfa73c4', 'PIRATE-FRESH-128C', 'paste', 'pirate-hash-128c', NOW())
ON CONFLICT (id) DO NOTHING;

-- Message 0: User (even)
INSERT INTO messages (id, conversation_id, message_index, role, content)
VALUES (gen_random_uuid(), 'da05e964-e422-4e7b-a3bd-5f8dbcfa73c4', 0, 'user', 'Ahoy there! What be the plan for the treasure?');

-- Message 1: Assistant (odd)
INSERT INTO messages (id, conversation_id, message_index, role, content)
VALUES (gen_random_uuid(), 'da05e964-e422-4e7b-a3bd-5f8dbcfa73c4', 1, 'assistant', 'We should head to the Skull Island.');

-- Message 2: User (even)
INSERT INTO messages (id, conversation_id, message_index, role, content)
VALUES (gen_random_uuid(), 'da05e964-e422-4e7b-a3bd-5f8dbcfa73c4', 2, 'user', 'Aye, but the map shows a reef in the way!');

-- Message 3: Assistant (odd)
INSERT INTO messages (id, conversation_id, message_index, role, content)
VALUES (gen_random_uuid(), 'da05e964-e422-4e7b-a3bd-5f8dbcfa73c4', 3, 'assistant', 'We have a steady ship, we can pass it.');

COMMIT;
