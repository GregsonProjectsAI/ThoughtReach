# Chunking Observation Log

This log documents retrieval quality and chunk usability after the implementation of deterministic sub-message chunking (Step 94).

## Query Observations

| Query | Observed Behaviour | Classification | Brief Note |
|-------|--------------------|----------------|------------|
| "bedroom riddle" | Returns specific short segments mentioning the riddle. | Acceptable | Chunks are readable but very brief (~30 chars). |
| "Captain's Code" | Result 1 is just the header "The Captain's Code". | Issue | Header-only chunks provide zero semantic value without following text. |
| "Location Sheets" | Returns multiple relevant segments describing the sheets. | Good | Effective at pulling specific details about the mechanic. |
| "pirate theme" | Returns headers ("HOOK") and unrelated planning lines. | Acceptable | Highlights that vague topic searches pull metadata/headers more often. |
| "structural flaws" | Returns clear sentences about structural problems. | Good | Shows that "thought units" are very effective for complete sentences. |
| "convergence logic" | Pulls headers and short "lead to SAME place" indicators. | Acceptable | Functional, but borders on being too fragmented. |
| "fragment distribution" | Result 2 is just "👉 Fragment F2". | Issue | Very short chunks (13 chars) feel like noise in search results. |
| "printable assets" | Returns specific conversion options. | Good | High utility for specific feature discovery. |

## Recurring Patterns & Systematic Weaknesses

1. **Header Fragmentation (Issue)**:
   - **Pattern**: Titles, headers, and short labels (e.g., "The Captain's Code", "🎬 HOOK") are being stored as independent chunks.
   - **Impact**: These chunks appear in results as low-information snippets that require expanding to understand.

2. **Bullet Point Fragmentation (Issue)**:
   - **Pattern**: Single-line bullet points shorter than 20 characters (but perhaps part of a list) are sometimes left as fragments if they don't have a NEXT/PREVIOUS in the same message.
   - **Impact**: Results like "👉 Fragment F2" provide very little search value.

3. **High Context Dependency (Acceptable/Observation)**:
   - **Pattern**: Due to smaller chunk sizes, the "matched_chunk_text" often feels like a "teaser" rather than a full answer.
   - **Impact**: Relying on the `surrounding_messages` (context hydration) is now critical for usability.

## Conclusion
The deterministic chunking is successfully creating "thought units," but it is also creating high-frequency "noise units" (headers/short bullets). Future refinements might consider merging headers with their following content or increasing the minimum length threshold.
