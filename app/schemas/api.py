from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

# Input Schemas
class MessageIn(BaseModel):
    role: str
    content: str
    created_at: Optional[datetime] = None
    message_index: Optional[int] = None

class ConversationIn(BaseModel):
    title: str
    source_type: str = "paste"
    external_id: Optional[str] = None
    created_at: Optional[datetime] = None
    messages: List[MessageIn] = Field(default_factory=list)
    raw_text: Optional[str] = None

class PasteImportRequest(BaseModel):
    conversations: List[ConversationIn]
    notes: Optional[str] = None

# Output Schemas
class PasteImportResponse(BaseModel):
    job_id: UUID
    status: str

class MessageOut(BaseModel):
    id: UUID
    role: str
    message_index: int
    content: str
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class CategoryCreate(BaseModel):
    name: str

class CategoryOut(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class TagCreate(BaseModel):
    name: str

class TagOut(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class ConversationCategoryUpdate(BaseModel):
    category_id: Optional[UUID] = None

class ConversationTagsUpdate(BaseModel):
    tag_ids: List[UUID]

class ConversationSummaryOut(BaseModel):
    id: UUID
    title: str
    summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ConversationSummariesResponse(BaseModel):
    summaries: List[ConversationSummaryOut]
    total_count: Optional[int] = None
    top_words: Optional[List[dict]] = None
    grouped_summaries: Optional[dict] = None
    insight: Optional[str] = None

class ConversationOut(BaseModel):
    id: UUID
    title: str
    source_type: str
    external_id: Optional[str]
    created_at: Optional[datetime]
    imported_at: datetime
    summary: Optional[str] = None
    category_id: Optional[UUID] = None
    category: Optional[CategoryOut] = None
    tags: List[TagOut] = Field(default_factory=list)
    messages: Optional[List[MessageOut]] = None
    content_fingerprint: Optional[str] = None

    @computed_field
    @property
    def has_summary(self) -> bool:
        return bool(self.summary is not None and self.summary.strip())

    model_config = ConfigDict(from_attributes=True)

class ImportJobOut(BaseModel):
    id: UUID
    import_mode: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

class SearchResultOut(BaseModel):
    conversation_id: UUID
    conversation_title: str
    conversation_summary: Optional[str] = None
    matched_chunk_text: str
    similarity_score: float
    message_start_index: int
    message_end_index: int
    surrounding_messages: Optional[List[dict]] = None

    @computed_field
    @property
    def has_summary(self) -> bool:
        return bool(self.conversation_summary is not None and self.conversation_summary.strip())
