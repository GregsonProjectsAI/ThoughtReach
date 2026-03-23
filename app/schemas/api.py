from pydantic import BaseModel, ConfigDict, Field
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

class ConversationOut(BaseModel):
    id: UUID
    title: str
    source_type: str
    external_id: Optional[str]
    created_at: Optional[datetime]
    imported_at: datetime
    messages: Optional[List[MessageOut]] = None

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
    matched_chunk_text: str
    similarity_score: float
    message_start_index: int
    message_end_index: int
