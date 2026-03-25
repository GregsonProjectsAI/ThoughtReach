# Search API Contract (Category-Aware Retrieval)

This document outlines the request and response structure for the ThoughtReach retrieval API, specifically focusing on category-aware search and discovery.

## 1. Search Endpoint

**Path**: `POST /search`  
**Description**: Performs a semantic search across conversations, with optional category scoping.

### Request Body
The request body must be a JSON object with the following fields:

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `query` | `string` | **Yes** | The semantic search query (e.g., "vector embeddings"). |
| `limit` | `integer` | No | Maximum number of results to return (default: 10). |
| `category_id` | `UUID` / `null` | No | Optional. If provided as a UUID string, restricts results to conversations in that category. If `null` or omitted, performs a global search. |

### Error Behaviour
- **404 Category not found**: If a `category_id` is provided but does not exist in the database, the API returns a 404 error.

### Response Shape
Returns a list of search result objects:

```json
[
  {
    "conversation_id": "uuid",
    "conversation_title": "string",
    "conversation_summary": "string | null",
    "category_id": "uuid | null",
    "category_name": "string | null",
    "matched_chunk_text": "string",
    "similarity_score": 0.85,
    "message_start_index": 0,
    "message_end_index": 2,
    "surrounding_messages": [
      {
        "role": "user",
        "content": "..."
      },
      ...
    ]
  }
]
```

---

## 2. Category Discovery

**Path**: `GET /categories`  
**Description**: Returns a list of all available categories for discovery and ID mapping.

### Request
No request body or parameters required.

### Response Shape
Returns a list of category objects:

```json
[
  {
    "id": "uuid",
    "name": "string"
  },
  ...
]
```

If no categories are defined, returns an empty list `[]`.

---

## 3. Usage Examples

### Example 1: Global Search
Search across the entire archive (no category filter).

**Request**:
`POST /search`
```json
{
  "query": "vector database benefits",
  "limit": 5
}
```

**Response**:
```json
[
  {
    "conversation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "conversation_title": "Notes on Vector Search",
    "conversation_summary": "Discussion about indexing and retrieval using vector embeddings.",
    "category_id": null,
    "category_name": null,
    "matched_chunk_text": "...vector databases provide significant benefits for sparse high-dimensional data...",
    "similarity_score": 0.89,
    "message_start_index": 2,
    "message_end_index": 4,
    "surrounding_messages": [ ... ]
  }
]
```

### Example 2: Category-Scoped Search
Search restricted to a specific category.

**Request**:
`POST /search`
```json
{
  "query": "index funds",
  "category_id": "9968aa43-d67b-400c-990a-83f759532503"
}
```

**Response**:
```json
[
  {
    "conversation_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "conversation_title": "Personal Finance Discussion",
    "conversation_summary": "Advice on long-term investing and market tracking.",
    "category_id": "9968aa43-d67b-400c-990a-83f759532503",
    "category_name": "Finance",
    "matched_chunk_text": "Low-cost index funds are often recommended for diversified portfolios.",
    "similarity_score": 0.92,
    "message_start_index": 10,
    "message_end_index": 10,
    "surrounding_messages": [ ... ]
  }
]
```

### Example 3: Invalid Category Error
Providing a `category_id` that does not exist.

**Request**:
`POST /search`
```json
{
  "query": "any query",
  "category_id": "ffffffff-ffff-ffff-ffff-ffffffffffff"
}
```

**Response (Status: 404)**:
```json
{
  "detail": "Category not found"
}
```

### Example 4: Category Discovery
Discover active categories before performing a scoped search.

**Request**:
`GET /categories`

**Response**:
```json
[
  {
    "id": "9968aa43-d67b-400c-990a-83f759532503",
    "name": "Finance"
  },
  {
    "id": "c710470e-1e90-48f1-aa33-52fa8a4b3726",
    "name": "Technical"
  }
]
```
