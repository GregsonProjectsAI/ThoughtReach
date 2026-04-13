# ThoughtReach V1

## Scope (Phase 1 Only)
Archive + search core.

- Import pasted chats or uploaded files
- Store conversations, messages, and chunks
- Generate embeddings for chunks
- Semantic search over chunks
- Return search results with source context (provenance)

## Constraints
- Keep implementation simple and modular
- Do not invent future abstractions
- Do not add features outside Phase 1
- Preserve chunk provenance in the eventual design
- **Embedding provider — development default**: Embedding generation for ingestion, query retrieval, and evaluation must default to a local or self-hosted provider during development. Paid external embedding APIs (e.g. OpenAI) may remain as optional fallback or future runtime choices but must not be required for ordinary development and validation work. This constraint does not authorise new user-facing AI behaviour; any runtime AI calls remain a separate future decision.

## Out of Scope (Do NOT build yet)
- Categories
- Summaries
- Extraction
- Auth
- Billing
- Setup import vs normal import split
- Refresh structure
- Advanced UI polish

## Build Phases
1. **Phase 1**: Archive + search core (Current Phase).
2. **Future Phases**: Categories, summaries, auth, UI polish, multi-import types.
