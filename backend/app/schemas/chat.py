"""Chat schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    """Schema for creating a new chat."""
    title: str = Field(default="New Chat", max_length=255)


class ChatUpdate(BaseModel):
    """Schema for updating a chat."""
    title: str | None = Field(None, max_length=255)
    is_archived: bool | None = None
    is_pinned: bool | None = None


class MessagePreview(BaseModel):
    """Preview of last message in chat list."""
    content: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Schema for chat response."""
    id: str
    title: str
    thread_id: str
    is_archived: bool
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message: MessagePreview | None = None

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    """Schema for paginated chat list."""
    chats: list[ChatResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
