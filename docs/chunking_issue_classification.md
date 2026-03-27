# Chunking Issue Classification

This document classifies recurring retrieval issues identified after the implementation of deterministic sub-message chunking.

## 1. Semantic Fragmentation
* **Description**: Short, isolated segments such as session headers, stage titles, or metadata markers (e.g., "The Captain's Code", "🎬 HOOK") are retrieved as independent search results.
* **Root Cause**: The deterministic rule to split on double line breaks (`\n\n`) correctly identifies these as distinct units, but they lack sufficient semantic density to provide value without their following content.

## 2. Structural Isolation
* **Description**: Very short bullet points, fragments, or list items (e.g., "👉 Fragment F2") appear in results as extremely low-information snippets (~10-30 characters).
* **Root Cause**: The fragment merge rule (merging chunks < 20 characters) is limited to the current message's scope. If a message is inherently short or consists of a single isolated line, it remains an undersized chunk.

## 3. Teaser Retrieval
* **Description**: Retreived chunks often feel like "teasers" or incomplete thoughts that require the user to manually expand the result to find actual utility.
* **Root Cause**: While deterministic boundaries are cleaner than word-count splits, they often isolate individual sentences that are semantically dependent on the broader context of the conversation thread.

---
**Status**: Classification complete based on Step 96 observations. No fixes or modifications proposed in this phase.
