"""Chat API endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DB, CurrentUser
from app.schemas.chat import ChatCreate, ChatListResponse, ChatResponse, ChatUpdate
from app.schemas.message import MessageResponse
from app.services.chat import (
    add_message,
    create_chat,
    delete_chat,
    get_chat,
    get_chat_messages,
    get_user_chats,
    update_chat,
)

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("", response_model=ChatListResponse)
async def list_chats(
    current_user: CurrentUser,
    db: DB,
    page: int = 1,
    per_page: int = 20,
    include_archived: bool = False,
) -> ChatListResponse:
    """List user's chats with pagination."""
    return await get_user_chats(
        db,
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        include_archived=include_archived,
    )


@router.post("", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_new_chat(
    current_user: CurrentUser,
    db: DB,
    data: ChatCreate,
) -> ChatResponse:
    """Create a new chat."""
    chat = await create_chat(db, current_user.id, data)
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        thread_id=chat.thread_id,
        is_archived=chat.is_archived,
        is_pinned=chat.is_pinned,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=0,
        last_message=None,
    )


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat_details(
    chat_id: str,
    current_user: CurrentUser,
    db: DB,
) -> ChatResponse:
    """Get chat details by ID."""
    chat = await get_chat(db, chat_id, current_user.id)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        thread_id=chat.thread_id,
        is_archived=chat.is_archived,
        is_pinned=chat.is_pinned,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=len(chat.messages),
        last_message=chat.messages[-1] if chat.messages else None,
    )


@router.patch("/{chat_id}", response_model=ChatResponse)
async def update_chat_info(
    chat_id: str,
    current_user: CurrentUser,
    db: DB,
    data: ChatUpdate,
) -> ChatResponse:
    """Update chat title or status."""
    chat = await update_chat(db, chat_id, current_user.id, data)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    
    return ChatResponse(
        id=chat.id,
        title=chat.title,
        thread_id=chat.thread_id,
        is_archived=chat.is_archived,
        is_pinned=chat.is_pinned,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=0,
        last_message=None,
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_endpoint(
    chat_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    """Delete a chat."""
    deleted = await delete_chat(db, chat_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )


@router.get("/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    chat_id: str,
    current_user: CurrentUser,
    db: DB,
    limit: int = 100,
) -> list[MessageResponse]:
    """Get messages for a chat."""
    # Verify user owns the chat
    chat = await get_chat(db, chat_id, current_user.id)
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )
    
    messages = await get_chat_messages(db, chat_id, limit)
    return [MessageResponse.model_validate(m) for m in messages]
