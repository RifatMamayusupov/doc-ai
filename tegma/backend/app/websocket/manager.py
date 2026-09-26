"""WebSocket connection manager for real-time updates."""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.schemas.websocket import WSEventType, WSMessage


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    chat_id: str | None = None
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectionManager:
    """
    WebSocket connection manager for handling real-time updates.
    
    Manages connections per user and per chat, enabling:
    - User-specific broadcasts (e.g., new chat created)
    - Chat-specific broadcasts (e.g., agent response streaming)
    """

    def __init__(self) -> None:
        """Initialize the connection manager."""
        # user_id -> list of ConnectionInfo
        self._user_connections: dict[str, list[ConnectionInfo]] = defaultdict(list)
        # chat_id -> list of ConnectionInfo
        self._chat_connections: dict[str, list[ConnectionInfo]] = defaultdict(list)
        # websocket -> ConnectionInfo (for quick lookup)
        self._connection_map: dict[WebSocket, ConnectionInfo] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        chat_id: str | None = None,
    ) -> ConnectionInfo:
        """
        Accept a WebSocket connection and register it.
        
        Args:
            websocket: The WebSocket connection
            user_id: The user's ID
            chat_id: Optional chat ID to subscribe to
            
        Returns:
            ConnectionInfo object
        """
        await websocket.accept()
        
        conn_info = ConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            chat_id=chat_id,
        )
        
        async with self._lock:
            self._user_connections[user_id].append(conn_info)
            if chat_id:
                self._chat_connections[chat_id].append(conn_info)
            self._connection_map[websocket] = conn_info
        
        # Send connected event
        await self.send_to_connection(
            conn_info,
            WSEventType.CONNECTED,
            {"user_id": user_id, "chat_id": chat_id},
        )
        
        return conn_info

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect and unregister a WebSocket connection.
        
        Args:
            websocket: The WebSocket to disconnect
        """
        async with self._lock:
            conn_info = self._connection_map.pop(websocket, None)
            if not conn_info:
                return
            
            # Remove from user connections
            user_conns = self._user_connections.get(conn_info.user_id, [])
            if conn_info in user_conns:
                user_conns.remove(conn_info)
            if not user_conns:
                self._user_connections.pop(conn_info.user_id, None)
            
            # Remove from chat connections
            if conn_info.chat_id:
                chat_conns = self._chat_connections.get(conn_info.chat_id, [])
                if conn_info in chat_conns:
                    chat_conns.remove(conn_info)
                if not chat_conns:
                    self._chat_connections.pop(conn_info.chat_id, None)

    async def switch_chat(
        self,
        websocket: WebSocket,
        new_chat_id: str,
    ) -> None:
        """
        Switch a connection to a different chat.
        
        Args:
            websocket: The WebSocket connection
            new_chat_id: The new chat ID to subscribe to
        """
        async with self._lock:
            conn_info = self._connection_map.get(websocket)
            if not conn_info:
                return
            
            # Remove from old chat
            if conn_info.chat_id:
                old_chat_conns = self._chat_connections.get(conn_info.chat_id, [])
                if conn_info in old_chat_conns:
                    old_chat_conns.remove(conn_info)
            
            # Add to new chat
            conn_info.chat_id = new_chat_id
            self._chat_connections[new_chat_id].append(conn_info)

    async def send_to_connection(
        self,
        conn_info: ConnectionInfo,
        event: WSEventType,
        data: dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            conn_info: The connection to send to
            event: The event type
            data: The event data
            
        Returns:
            True if sent successfully, False otherwise
        """
        message = WSMessage(
            event=event,
            chat_id=conn_info.chat_id,
            data=data,
            timestamp=datetime.now(timezone.utc),
        )
        
        try:
            await conn_info.websocket.send_json(message.model_dump(mode="json"))
            return True
        except Exception:
            return False

    async def broadcast_to_user(
        self,
        user_id: str,
        event: WSEventType,
        data: dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all of a user's connections.
        
        Args:
            user_id: The user's ID
            event: The event type
            data: The event data
            
        Returns:
            Number of successful sends
        """
        connections = self._user_connections.get(user_id, [])
        sent_count = 0
        
        for conn_info in connections:
            if await self.send_to_connection(conn_info, event, data):
                sent_count += 1
        
        return sent_count

    async def broadcast_to_chat(
        self,
        chat_id: str,
        event: WSEventType,
        data: dict[str, Any],
    ) -> int:
        """
        Broadcast a message to all connections in a chat.
        
        Args:
            chat_id: The chat ID
            event: The event type
            data: The event data
            
        Returns:
            Number of successful sends
        """
        connections = self._chat_connections.get(chat_id, [])
        sent_count = 0
        
        for conn_info in connections:
            if await self.send_to_connection(conn_info, event, data):
                sent_count += 1
        
        return sent_count

    async def stream_to_chat(
        self,
        chat_id: str,
        message_id: str,
        content_generator,
    ) -> str:
        """
        Stream content chunks to all connections in a chat.
        
        Args:
            chat_id: The chat ID
            message_id: The message ID being streamed
            content_generator: Async generator yielding content chunks
            
        Returns:
            The complete accumulated content
        """
        full_content = ""
        
        async for chunk in content_generator:
            full_content += chunk
            await self.broadcast_to_chat(
                chat_id,
                WSEventType.MESSAGE_CHUNK,
                {
                    "message_id": message_id,
                    "chunk": chunk,
                    "is_complete": False,
                },
            )
        
        # Send completion event
        await self.broadcast_to_chat(
            chat_id,
            WSEventType.MESSAGE_COMPLETE,
            {
                "message_id": message_id,
                "content": full_content,
                "is_complete": True,
            },
        )
        
        return full_content

    def get_user_connection_count(self, user_id: str) -> int:
        """Get the number of active connections for a user."""
        return len(self._user_connections.get(user_id, []))

    def get_chat_connection_count(self, chat_id: str) -> int:
        """Get the number of active connections in a chat."""
        return len(self._chat_connections.get(chat_id, []))

    def get_total_connections(self) -> int:
        """Get the total number of active connections."""
        return len(self._connection_map)


# Global connection manager instance
manager = ConnectionManager()
