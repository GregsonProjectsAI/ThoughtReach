# Chunking Issue Prioritisation

This document prioritises the identified chunking issues based on their impact on the core goal: fast, accurate retrieval of meaningful "thought units."

## 1. Semantic Fragmentation
* **Impact**: Medium-High
* **Priority**: **P1 (Must Address)**
* **Justification**: Headers and titles (e.g., "🎬 HOOK") often rank high due to keyword density but offer zero standalone value. Merging these with their following content is essential for high-quality retrieval results.

## 2. Structural Isolation
* **Impact**: Medium
* **Priority**: **P2 (Should Address)**
* **Justification**: Extremely short bullet points or fragments (e.g., "👉 Fragment F2") are effectively noise. Increasing the minimum length threshold or improving cross-message awareness would raise the "semantic floor" of the results.

## 3. Teaser Retrieval
* **Impact**: Low-Medium
* **Priority**: **P3 (Acceptable Tradeoff)**
* **Justification**: While short "teaser" chunks require expansion, this is a direct byproduct of high-precision retrieval. The existing "context hydration" and UI expansion controls already mitigate this issue effectively.

---
**Status**: Prioritisation complete. This document serves as the roadmap for future chunking refinements.
