"""WebSocket message handlers with real-time automation support."""

import asyncio
import json
from typing import Any
from pathlib import Path

from fastapi import WebSocket

from app.schemas.websocket import WSEventType
from app.websocket.manager import ConnectionInfo, manager


class WSMessageHandler:
    """Handles incoming WebSocket messages with full automation support."""

    def __init__(self):
        self._workflow_sessions: dict[str, str] = {}  # chat_id -> session_id

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
            # Chat management
            "switch_chat": self._handle_switch_chat,
            "send_message": self._handle_send_message,
            
            # HITL
            "hitl_response": self._handle_hitl_response,
            
            # Document workflow
            "start_workflow": self._handle_start_workflow,
            "template_selected": self._handle_template_selected,
            "update_field": self._handle_update_field,
            "regenerate_doc": self._handle_regenerate_doc,
            "approve_doc": self._handle_approve_doc,
            "skip_doc": self._handle_skip_doc,
            "finalize_workflow": self._handle_finalize_workflow,
            "cancel_workflow": self._handle_cancel_workflow,
            
            # Sync control
            "trigger_sync": self._handle_trigger_sync,
            "pause_sync": self._handle_pause_sync,
            "resume_sync": self._handle_resume_sync,
            
            # Generation control
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
        message = data.get("message", "")
        files = data.get("files", [])
        
        # Notify that we're processing
        await manager.send_to_connection(
            conn_info,
            WSEventType.AGENT_THINKING,
            {"message": "Xabaringiz qayta ishlanmoqda..."},
        )
        
        # Check if this is a document generation request
        doc_keywords = ["hujjat", "document", "shablon", "template", "yaratish", "generate", "to'ldirish", "fill"]
        is_doc_request = any(kw in message.lower() for kw in doc_keywords)
        
        if is_doc_request and files:
            # Start document workflow
            await self._start_document_workflow(conn_info, message, files)
        else:
            # Regular agent processing - delegate to agent adapter
            from app.agent.adapter import agent_adapter
            await agent_adapter.process_message(conn_info, message, files)

    async def _start_document_workflow(
        self,
        conn_info: ConnectionInfo,
        message: str,
        files: list[str],
    ):
        """Start document generation workflow."""
        from app.services.workflow import doc_workflow
        
        # Set up WebSocket emit callback
        async def emit_to_chat(chat_id: str, event: str, data: dict):
            await manager.send_to_chat(chat_id, event, data)
        
        doc_workflow.set_emit_callback(emit_to_chat)
        
        # Convert file paths
        file_paths = [Path(f) for f in files if Path(f).exists()]
        
        # Start workflow
        session = await doc_workflow.start_workflow(
            user_id=conn_info.user_id,
            chat_id=conn_info.chat_id,
            input_files=file_paths,
            input_text=message,
        )
        
        # Track session
        self._workflow_sessions[conn_info.chat_id] = session.session_id

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

    async def _handle_start_workflow(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle explicit workflow start request."""
        from app.services.workflow import doc_workflow
        
        async def emit_to_chat(chat_id: str, event: str, event_data: dict):
            await manager.send_to_chat(chat_id, event, event_data)
        
        doc_workflow.set_emit_callback(emit_to_chat)
        
        files = data.get("files", [])
        text = data.get("text", "")
        input_data = data.get("data", {})
        
        file_paths = [Path(f) for f in files if Path(f).exists()]
        
        session = await doc_workflow.start_workflow(
            user_id=conn_info.user_id,
            chat_id=conn_info.chat_id,
            input_files=file_paths if file_paths else None,
            input_text=text if text else None,
            input_data=input_data if input_data else None,
        )
        
        self._workflow_sessions[conn_info.chat_id] = session.session_id

    async def _handle_template_selected(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle template selection from user."""
        from app.services.workflow import doc_workflow
        
        template_ids = data.get("template_ids", [])
        session_id = self._workflow_sessions.get(conn_info.chat_id)
        
        if not session_id:
            await manager.send_to_connection(
                conn_info,
                WSEventType.ERROR,
                {"message": "Faol sessiya topilmadi"},
            )
            return
        
        if isinstance(template_ids, str):
            template_ids = [template_ids]
        
        await doc_workflow.select_templates(session_id, template_ids)

    async def _handle_update_field(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle field update in generated document."""
        from app.services.workflow import doc_workflow
        
        session_id = self._workflow_sessions.get(conn_info.chat_id)
        document_id = data.get("document_id")
        field_id = data.get("field_id")
        value = data.get("value")
        
        if session_id and document_id and field_id:
            await doc_workflow.update_document_field(
                session_id, document_id, field_id, value
            )

    async def _handle_regenerate_doc(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle document regeneration request."""
        from app.services.workflow import doc_workflow
        
        session_id = self._workflow_sessions.get(conn_info.chat_id)
        document_id = data.get("document_id")
        
        if session_id and document_id:
            await doc_workflow.regenerate_document(session_id, document_id)

    async def _handle_approve_doc(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle document approval."""
        from app.services.workflow import doc_workflow
        
        session_id = self._workflow_sessions.get(conn_info.chat_id)
        document_id = data.get("document_id")
        
        if session_id and document_id:
            await doc_workflow.approve_document(session_id, document_id)

    async def _handle_skip_doc(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle document skip."""
        from app.services.workflow import doc_workflow
        
        session_id = self._workflow_sessions.get(conn_info.chat_id)
        document_id = data.get("document_id")
        
        if session_id and document_id:
            await doc_workflow.skip_document(session_id, document_id)

    async def _handle_finalize_workflow(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle workflow finalization."""
        from app.services.workflow import doc_workflow
        
        session_id = self._workflow_sessions.get(conn_info.chat_id)
        approved_ids = data.get("approved_document_ids")
        
        if session_id:
            result = await doc_workflow.finalize_workflow(session_id, approved_ids)
            
            # Clean up
            if conn_info.chat_id in self._workflow_sessions:
                del self._workflow_sessions[conn_info.chat_id]

    async def _handle_cancel_workflow(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle workflow cancellation."""
        from app.services.workflow import doc_workflow
        
        session_id = self._workflow_sessions.get(conn_info.chat_id)
        
        if session_id:
            await doc_workflow.cancel_workflow(session_id)
            del self._workflow_sessions[conn_info.chat_id]

    async def _handle_trigger_sync(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle manual sync trigger."""
        from app.services.scheduler import sync_scheduler
        
        connector_id = data.get("connector_id")
        
        if connector_id:
            await sync_scheduler.trigger_sync_now(connector_id, conn_info.user_id)
            
            await manager.send_to_connection(
                conn_info,
                "sync_triggered",
                {"connector_id": connector_id, "message": "Sinxronlash boshlandi"},
            )

    async def _handle_pause_sync(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle sync pause request."""
        from app.services.scheduler import sync_scheduler
        
        connector_id = data.get("connector_id")
        
        if connector_id:
            await sync_scheduler.pause_sync_job(connector_id)

    async def _handle_resume_sync(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle sync resume request."""
        from app.services.scheduler import sync_scheduler
        
        connector_id = data.get("connector_id")
        
        if connector_id:
            await sync_scheduler.resume_sync_job(connector_id)

    async def _handle_cancel_generation(
        self,
        conn_info: ConnectionInfo,
        data: dict[str, Any],
    ) -> None:
        """Handle request to cancel ongoing generation."""
        await manager.send_to_connection(
            conn_info,
            WSEventType.AGENT_COMPLETE,
            {"cancelled": True, "message": "Generatsiya bekor qilindi"},
        )


# Global handler instance
ws_handler = WSMessageHandler()
