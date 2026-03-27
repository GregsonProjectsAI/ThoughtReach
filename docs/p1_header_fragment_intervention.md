# P1 Minimal Intervention: Header Fragment Merging

This document defines a minimal, deterministic design intervention for addressed the "Semantic Fragmentation" (P1) issue identified in sub-message chunking.

## 1. The Problem
Short, isolated segments like headers, stage titles, or metadata markers (e.g., "The Captain's Code", "🎬 HOOK — THE ESCAPE") are stored as independent chunks. These rank high due to keyword density but offer zero standalone utility in search results.

## 2. Impact on Retrieval Usefulness
- **Search Clutter**: High-ranking headers push actual information chunks ("evidence") further down the results.
- **Cognitive Load**: Users must expand header results to see any actual content, defeating the goal of "meaningful thought units."
- **Broken Semantic Unity**: Headers are semantically bound to the following content. Separating them creates "orphaned" headers and "unlabeled" content chunks.

## 3. Minimal Deterministic Intervention
**"Header-Aware Merging" Rule**:
Extend the `split_message_into_chunks` process during ingestion to merge any paragraph-level segment (`\n\n` split) with the NEXT segment if it satisfies two conditions:
1. **Length**: Segment is less than 60 characters.
2. **Lack of Terminal Punctuation**: Segment does NOT end in `.`, `!`, or `?`.

This rule would catch "🎬 STEP 1 — HOOK" and "The Captain's Code" while preserving actual short sentences like "Hello." or "Yes!".

## 4. Layer Placement & Justification
- **Layer**: **Ingestion** (within `split_message_into_chunks`).
- **Justification**: 
    - This is the **correct layer** because it addresses the issue at the source. 
    - It ensures headers and their content are indexed and retrieved as a single, coherent thought unit.
    - It avoids the complexity of post-retrieval filtering or UI-side "stitching" logic.

## 5. Non-Goals
- **No Semantic Parsing**: No AI-based header detection or NLP classification.
- **No Cross-Message Merging**: No attempt to merge across distinct conversation messages.
- **No P2/P3 Fixes**: This does NOT address bullet point fragmentation or context dependency.

## 6. Risks & Tradeoffs
- **Risk**: A very short message (e.g., "Help me") that happens to be the only thing in a message would still be a chunk (safeguard: check if `NEXT` exists).
- **Tradeoff**: Chunks containing both a header and content will be slightly larger, but still well within target bounds (typically < 400 chars).

## 7. Compliance and Integrity
- **Determinism**: The rule uses only length and simple character checks.
- **Retrieval-First**: Specifically designed to remove high-rank, low-value noise.
- **Low-Cost**: No additional API calls or heavy processing required.
