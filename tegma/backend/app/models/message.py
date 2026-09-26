"""Message model for chat history."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.chat import Chat


class MessageRole(str, Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(Base):
    """Individual message in a chat."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Parent chat
    chat_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Message content
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MessageRole.USER.value,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Metadata for tool calls, file attachments, etc.
    message_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # File attachments (list of file IDs/paths)
    attachments: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    
    # For tool messages
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.role}: {self.content[:50]}...>"
