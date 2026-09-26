"""WebSocket message schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class WSEventType(str, Enum):
    """WebSocket event types for real-time updates."""
    
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    
    # Agent events
    AGENT_THINKING = "agent_thinking"
    AGENT_STEP = "agent_step"
    AGENT_COMPLETE = "agent_complete"
    
    # Message events
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_COMPLETE = "message_complete"
    
    # Tool events
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_RESULT = "tool_call_result"
    
    # Code execution events
    CODE_EXECUTE_START = "code_execute_start"
    CODE_EXECUTE_OUTPUT = "code_execute_output"
    CODE_EXECUTE_COMPLETE = "code_execute_complete"
    
    # Human-in-the-loop events
    HITL_REQUEST = "hitl_request"
    HITL_RESPONSE = "hitl_response"
    
    # Template events
    TEMPLATE_SUGGEST = "template_suggest"
    TEMPLATE_SELECTED = "template_selected"
    
    # Process status
    PROCESS_STATUS = "process_status"
    
    # File events
    FILE_UPLOAD_PROGRESS = "file_upload_progress"
    FILE_READY = "file_ready"


class WSMessage(BaseModel):
    """Base WebSocket message schema."""
    event: WSEventType
    chat_id: str | None = None
    data: dict[str, Any] = {}
    timestamp: datetime | None = None


class WSAgentThinking(BaseModel):
    """Agent thinking event data."""
    message: str = "Thinking..."
    step: int = 0


class WSToolCall(BaseModel):
    """Tool call event data."""
    tool_name: str
    tool_id: str
    arguments: dict[str, Any]
    description: str | None = None


class WSToolResult(BaseModel):
    """Tool result event data."""
    tool_name: str
    tool_id: str
    result: Any
    status: str = "success"  # success, error
    duration_ms: int = 0


class WSCodeExecute(BaseModel):
    """Code execution event data."""
    code: str
    language: str = "python"
    output: str | None = None
    status: str = "running"  # running, success, error


class WSProcessStatus(BaseModel):
    """Process status for real-time display."""
    process_type: str  # excel, pdf, image, etc.
    status: str  # processing, analyzing, converting, complete
    progress: int = 0  # 0-100
    message: str = ""
    preview_url: str | None = None


class WSTemplateSuggest(BaseModel):
    """Template suggestion event data."""
    templates: list[dict[str, Any]]  # List of matching templates
    context: str  # Why these templates were suggested


class WSHITLRequest(BaseModel):
    """Human-in-the-loop request data."""
    request_id: str
    tool_name: str
    description: str
    preview: dict[str, Any] | None = None
    options: list[str] = ["approve", "reject", "modify"]
