# Search Result Interaction Specification

This document defines the behavioral and display rules for individual items in the ThoughtReach search results list.

## 1. Item States

### Collapsed State (Default)
- **Purpose**: Minimal summary for rapid scanning.
- **Visible Elements**:
  - `conversation_title`
  - `category_name` (or "Uncategorized")
  - `similarity_score`
  - Truncated `matched_chunk_text`

### Expanded State
- **Purpose**: Provide full context for a specific match.
- **Visible Elements**:
  - All "Collapsed State" elements.
  - Full (untruncated) `matched_chunk_text`.
  - `surrounding_messages` list.

---

## 2. Interaction Rules

### Expand/Collapse Trigger
- **Action**: Clicking anywhere on the result item (card/row) toggles between states.
- **Multiple Expansion**: Users can expand multiple results simultaneously (independent state per item).

### Text Truncation
- **Collapsed**: `matched_chunk_text` should be truncated to **200 characters** with an ellipsis (`...`).
- **Expanded**: Displays the full text length without truncation.

---

## 3. Field Display Logic

### Category Name
- **If value is present**: Display the name inside a distinct UI badge.
- **If null**: Display "Uncategorized" in a subtle, neutral badge.

### Similarity Score
- **Format**: Display as a percentage.
- **Calculation**: `Math.round(similarity_score * 100) + "%"`
- **Vibe**: High scores (>= 80%) can optionally use a positive accent color (e.g., green tint).

### Surrounding Messages
- **Structure**: Display as a vertical list of messages.
- **Role Display**:
  - `user` -> Label as "User" or "You".
  - `assistant` -> Label as "Assistant" or "AI".
- **Highlighting**: The specific message containing the match can optionally be highlighted to draw the eye.

---

## 4. Summary Table

| Requirement | Rule |
| :--- | :--- |
| **Trigger** | Card Click (Toggle) |
| **Concurrency** | Multiple items can be expanded at once |
| **Truncation** | 200 chars (Collapsed only) |
| **Null Category** | "Uncategorized" |
| **Score Format** | Rounded Percentage (e.g. 85%) |
| **Context View** | List of roles + message content |
