"""Message schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str
    attachments: list[Any] | None = None  # File objects or IDs


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: str
    chat_id: str
    role: str
    content: str
    message_metadata: dict[str, Any] | None = None
    attachments: list[Any] | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageStreamChunk(BaseModel):
    """Schema for streaming message chunks."""
    chat_id: str
    message_id: str
    chunk: str
    is_complete: bool = False
