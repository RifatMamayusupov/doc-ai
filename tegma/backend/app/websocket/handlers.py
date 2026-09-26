"""WebSocket message handlers."""

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from app.schemas.websocket import WSEventType
from app.websocket.manager import ConnectionInfo, manager


class WSMessageHandler:
    """Handles incoming WebSocket messages."""

    async def handle_message(
        self,
        conn_info: ConnectionInfo,
        message: dict[str, Any],
    ) -> None:
        """
        Route incoming WebSocket messages to appropriate handlers.
        
        Args:
            conn_info: The connection info
            message: The parsed message dict
        """
        event_type = message.get("event")
        data = message.get("data", {})
        
        handlers = {
            "switch_chat": self._handle_switch_chat,
            "send_message": self._handle_send_message,
            "hitl_response": self._handle_hitl_response,
            "template_selected": self._handle_template_selected,
            "cancel_generation": self._handle_cancel_generation,
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(conn_info, data)
        else:
            await manager.send_to_connection(
                conn_info,
                WSEventType.ERROR,
                {"message": f"Unknown event type: {event_type}"},
            )

    async def _handle_switch_chat(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle chat switching."""
        new_chat_id = data.get("chat_id")
        if new_chat_id:
            await manager.switch_chat(conn_info.websocket, new_chat_id)
            await manager.send_to_connection(
                conn_info,
                WSEventType.CONNECTED,
                {"chat_id": new_chat_id, "message": "Switched to chat"},
            )

    async def _handle_send_message(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """
        Handle user message - triggers agent processing.
        
        This is the main entry point for agent interaction.
        The actual agent processing is handled by the agent adapter.
        """
        # Delegate to agent handler (will be connected separately)
        # For now, just acknowledge
        await manager.send_to_connection(
            conn_info,
            WSEventType.AGENT_THINKING,
            {"message": "Processing your message..."},
        )

    async def _handle_hitl_response(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle human-in-the-loop response (approve/reject)."""
        request_id = data.get("request_id")
        response = data.get("response")  # "approve", "reject", "modify"
        modifications = data.get("modifications")
        
        await manager.send_to_connection(
            conn_info,
            WSEventType.HITL_RESPONSE,
            {
                "request_id": request_id,
                "response": response,
                "acknowledged": True,
            },
        )

    async def _handle_template_selected(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle template selection from user."""
        template_id = data.get("template_id")
        
        await manager.send_to_connection(
            conn_info,
            WSEventType.TEMPLATE_SELECTED,
            {
                "template_id": template_id,
                "acknowledged": True,
            },
        )

    async def _handle_cancel_generation(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle request to cancel ongoing generation."""
        await manager.send_to_connection(
            conn_info,
            WSEventType.AGENT_COMPLETE,
            {"cancelled": True, "message": "Generation cancelled"},
        )


# Global handler instance
ws_handler = WSMessageHandler()
