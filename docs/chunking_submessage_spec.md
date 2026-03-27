# Specification: Deterministic Sub-Message Chunking

## 1. Objective
Define a deterministic rule set for splitting messages into smaller "thought units" (sub-message chunks) to improve retrieval precision. This ensures that search results point to specific, readable fragments rather than overwhelming the user with entire long messages.

## 2. The "Thought Unit"
A **Thought Unit** is defined as:
- A short, self-contained idea or statement.
- Readable and meaningful when presented in isolation (as a search result).
- Aligned with the UI result card display (focused on concise previews).

## 3. Splitting Rules (Deterministic)
The following rules MUST be applied sequentially to each message:

1. **Paragraph Splits**: Split the message on double line breaks (`\n\n`).
2. **Line Splits (Fallback)**:
Apply line splitting IF:
* segment length > 400 characters
  AND
* segment contains at least one '\n'
3. **Whitespace Management**: Trim leading and trailing whitespace from every resulting chunk.
4. **Empty Segment Suppression**: Discard any chunks that are empty or contain only whitespace.

## 4. Boundaries & Constraints

### Minimum Length:
* Chunks shorter than 20 characters must be merged

Merge behaviour:
* If both adjacent chunks exist:
  → merge with the NEXT chunk (default)
* If NEXT does not exist:
  → merge with PREVIOUS

### Maximum Length (Soft Cap)
- **Soft Cap**: Aim for chunks between **100 and 500 characters**.
- **Constraint**: Do NOT use hard truncation (no cutting words in half). If a single line/paragraph exceeds the soft cap, leave it intact for this version.

## 4. Rule Execution Model

To preserve strict determinism, rules must be applied in a **Single-Pass, Greedy Sequential** model:

1. **Splitting Phase**: Apply Rule 1 (Paragraphs) and then Rule 2 (Lines) in a single top-down pass.
2. **Cleanup Phase**: Trim whitespace and discard empty segments.
3. **Merge Phase**: Scan the results from start to end (left-to-right).
    - If a segment meets a merge criteria (e.g., <20 characters), merge it with the **NEXT** available segment immediately.
    - If a merge occurs, the *resulting* larger segment stays at the current position and is **NOT re-evaluated** in the same pass (this prevents infinite loops or logic fragmentation).
    - **Conflict Resolution**: If a segment meets multiple merge criteria simultaneously, the rule listed first in the specification takes precedence.

**Final Guarantee**: Identical verbatim input strings must always yield identical chunked output regardless of implementation detail.

## 5. Ordering & Metadata
To ensure data integrity and traceability, each sub-chunk must retain its structural context:

- **Order Preservation**: The original sequence of chunks within a message must be strictly preserved.
- **Sub-Positioning**: Each chunk is assigned a `chunk_position_sub` (integer index starting at 0) indicating its relative order within the parent message.
- **Mapping**: Each chunk must always map to its:
  - `conversation_id`
  - `message_id`
  - `message_position` (original sequence number)
  - `chunk_position_sub` (new sub-index)

## 6. Non-Goals
- **No Semantic Splitting**: No usage of NLP, sentence tokenizers, or AI to determine "meaningful" breaks.
- **No LLM Usage**: Splitting must be computationally inexpensive and fully local.
- **No Cross-Message Merging**: Chunks must never span across multiple `message_id` boundaries.
- **No Summarization**: Chunks must contain the verbatim text from the original message.

## 7. Conceptual Output Shape
| Field | Description |
| :--- | :--- |
| `chunk_text` | The verbatim text segment |
| `conversation_id` | Foreign key to Conversation |
| `message_id` | Foreign key to Message |
| `chunk_position_sub` | Sequence index within the message (0, 1, 2...) |
a