"""Chat service for managing conversations."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat
from app.models.message import Message
from app.schemas.chat import ChatCreate, ChatListResponse, ChatResponse, ChatUpdate


async def create_chat(db: AsyncSession, user_id: str, data: ChatCreate) -> Chat:
    """Create a new chat for a user."""
    chat = Chat(
        user_id=user_id,
        title=data.title,
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    return chat


async def get_chat(db: AsyncSession, chat_id: str, user_id: str) -> Chat | None:
    """Get a chat by ID, ensuring it belongs to the user."""
    result = await db.execute(
        select(Chat)
        .options(selectinload(Chat.messages))
        .where(Chat.id == chat_id, Chat.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_chats(
    db: AsyncSession,
    user_id: str,
    page: int = 1,
    per_page: int = 20,
    include_archived: bool = False,
) -> ChatListResponse:
    """Get paginated list of user's chats."""
    # Base query
    query = select(Chat).where(Chat.user_id == user_id)
    
    if not include_archived:
        query = query.where(Chat.is_archived == False)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = (
        query
        .order_by(Chat.is_pinned.desc(), Chat.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    chats = result.scalars().all()
    
    # Build response with message counts
    chat_responses = []
    for chat in chats:
        # Get message count
        msg_count_result = await db.execute(
            select(func.count()).where(Message.chat_id == chat.id)
        )
        message_count = msg_count_result.scalar() or 0
        
        # Get last message
        last_msg_result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = last_msg_result.scalar_one_or_none()
        
        chat_responses.append(
            ChatResponse(
                id=chat.id,
                title=chat.title,
                thread_id=chat.thread_id,
                is_archived=chat.is_archived,
                is_pinned=chat.is_pinned,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                message_count=message_count,
                last_message=last_message,
            )
        )
    
    return ChatListResponse(
        chats=chat_responses,
        total=total,
        page=page,
        per_page=per_page,
        has_next=(page * per_page) < total,
    )


async def update_chat(
    db: AsyncSession, chat_id: str, user_id: str, data: ChatUpdate
) -> Chat | None:
    """Update a chat."""
    chat = await get_chat(db, chat_id, user_id)
    if not chat:
        return None
    
    if data.title is not None:
        chat.title = data.title
    if data.is_archived is not None:
        chat.is_archived = data.is_archived
    if data.is_pinned is not None:
        chat.is_pinned = data.is_pinned
    
    chat.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(chat)
    return chat


async def delete_chat(db: AsyncSession, chat_id: str, user_id: str) -> bool:
    """Delete a chat."""
    chat = await get_chat(db, chat_id, user_id)
    if not chat:
        return False
    
    await db.delete(chat)
    await db.commit()
    return True


async def add_message(
    db: AsyncSession,
    chat_id: str,
    role: str,
    content: str,
    message_metadata: dict | None = None,
    attachments: list[str] | None = None,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
) -> Message:
    """Add a message to a chat."""
    message = Message(
        chat_id=chat_id,
        role=role,
        content=content,
        message_metadata=message_metadata,
        attachments=attachments,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
    )
    db.add(message)
    
    # Update chat timestamp
    chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_result.scalar_one_or_none()
    if chat:
        chat.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(message)
    return message


async def get_chat_messages(
    db: AsyncSession, chat_id: str, limit: int = 100
) -> list[Message]:
    """Get messages for a chat."""
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
