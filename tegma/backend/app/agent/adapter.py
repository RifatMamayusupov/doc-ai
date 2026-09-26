"""WebSocket adapter for agent execution - mirrors textual_adapter.py pattern."""

import asyncio
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncGenerator

# Add deepagents_cli to path
# We need to add the project root to sys.path so we can import deepagents_cli package
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.config import settings
from app.schemas.websocket import WSEventType
from app.websocket.manager import manager


class WebSocketUIAdapter:
    """
    Adapter for rendering agent output to WebSocket clients.
    
    This mirrors TextualUIAdapter from deepagents_cli but sends events
    via WebSocket instead of mounting Textual widgets.
    """

    def __init__(self, chat_id: str, user_id: str) -> None:
        """
        Initialize the adapter.
        
        Args:
            chat_id: Chat session ID for WebSocket targeting
            user_id: User ID for connection routing
        """
        self.chat_id = chat_id
        self.user_id = user_id
        
        # State tracking
        self._current_tool_calls: dict[str, dict] = {}  # tool_id -> info
        self._pending_text = ""
        self._pending_hitl: dict[str, asyncio.Future] = {}
        self._token_count = 0

    async def send_event(self, event_type: WSEventType, data: dict) -> None:
        """Send event via WebSocket."""
        await manager.broadcast_to_chat(self.chat_id, event_type, data)

    async def show_thinking(self) -> None:
        """Show thinking indicator."""
        await self.send_event(
            WSEventType.AGENT_THINKING,
            {"message": "Thinking..."}
        )

    async def hide_thinking(self) -> None:
        """Hide thinking indicator."""
        await self.send_event(
            WSEventType.AGENT_STEP,
            {"step": "thinking_complete", "description": "Processing complete"}
        )

    async def stream_text(self, message_id: str, chunk: str) -> None:
        """Stream text chunk to client."""
        await self.send_event(
            WSEventType.MESSAGE_CHUNK,
            {
                "message_id": message_id,
                "chunk": chunk,
                "is_complete": False,
            }
        )

    async def complete_text(self, message_id: str, full_content: str) -> None:
        """Mark text streaming complete."""
        await self.send_event(
            WSEventType.MESSAGE_COMPLETE,
            {
                "message_id": message_id,
                "content": full_content,
                "is_complete": True,
            }
        )

    async def start_tool_call(
        self,
        tool_id: str,
        tool_name: str,
        args: dict,
    ) -> None:
        """Notify about tool call start."""
        self._current_tool_calls[tool_id] = {
            "name": tool_name,
            "args": args,
            "started_at": datetime.now(UTC).isoformat(),
        }
        await self.send_event(
            WSEventType.TOOL_CALL_START,
            {
                "tool_id": tool_id,
                "tool_name": tool_name,
                "arguments": args,
                "description": f"Executing {tool_name}...",
            }
        )

    async def complete_tool_call(
        self,
        tool_id: str,
        result: str,
        status: str = "success",
    ) -> None:
        """Notify about tool call completion."""
        tool_info = self._current_tool_calls.pop(tool_id, {})
        await self.send_event(
            WSEventType.TOOL_CALL_RESULT,
            {
                "tool_id": tool_id,
                "tool_name": tool_info.get("name", "unknown"),
                "result": result,
                "status": status,
            }
        )

    async def request_approval(
        self,
        tool_id: str,
        tool_name: str,
        description: str,
        args: dict | None = None,
    ) -> dict:
        """
        Request HITL approval from user.
        
        Returns dict with 'type': 'approve' or 'reject'
        """
        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self._pending_hitl[request_id] = future

        await self.send_event(
            WSEventType.HITL_REQUEST,
            {
                "request_id": request_id,
                "tool_id": tool_id,
                "tool_name": tool_name,
                "description": description,
                "arguments": args,
                "options": ["approve", "reject"],
            }
        )

        try:
            # Wait for response with timeout (5 minutes)
            result = await asyncio.wait_for(future, timeout=300.0)
            return result
        except asyncio.TimeoutError:
            return {"type": "timeout"}
        finally:
            self._pending_hitl.pop(request_id, None)

    def resolve_hitl(self, request_id: str, response: str) -> bool:
        """Resolve a pending HITL request."""
        future = self._pending_hitl.get(request_id)
        if future and not future.done():
            future.set_result({"type": response})
            return True
        return False

    async def send_system_message(self, message: str) -> None:
        """Send a system message."""
        await self.send_event(
            WSEventType.AGENT_STEP,
            {"step": "system", "description": message}
        )


async def execute_task_websocket(
    user_input: str,
    agent: Any,
    assistant_id: str | None,
    thread_id: str,
    adapter: WebSocketUIAdapter,
    auto_approve: bool = False,
) -> AsyncGenerator[dict, None]:
    """
    Execute a task with output directed to WebSocket.
    
    This is the WebSocket-compatible version of execute_task_textual().
    
    Args:
        user_input: User's message
        agent: LangGraph agent instance
        assistant_id: Agent identifier
        thread_id: Thread ID for conversation persistence
        adapter: WebSocket adapter for events
        auto_approve: Whether to auto-approve HITL requests
        
    Yields:
        Event dictionaries for streaming
    """
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langgraph.types import Command, Interrupt
    
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "assistant_id": assistant_id,
            "agent_name": assistant_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if assistant_id
        else {},
    }

    message_id = str(uuid.uuid4())
    pending_text = ""
    tool_call_buffers: dict[str | int, dict] = {}
    displayed_tool_ids: set[str] = set()

    # Show thinking
    yield {
        "event": WSEventType.AGENT_THINKING,
        "data": {"message": "Processing your request..."},
    }

    stream_input: dict | Command = {
        "messages": [{"role": "user", "content": user_input}]
    }

    try:
        while True:
            interrupt_occurred = False
            hitl_response: dict[str, Any] = {}
            pending_interrupts: dict[str, Any] = {}

            async for chunk in agent.astream(
                stream_input,
                stream_mode=["messages", "updates"],
                subgraphs=True,
                config=config,
            ):
                if not isinstance(chunk, tuple) or len(chunk) != 3:
                    continue

                namespace, stream_mode, data = chunk
                ns_key = tuple(namespace) if namespace else ()
                is_main_agent = ns_key == ()

                # Handle UPDATES stream - for interrupts
                if stream_mode == "updates":
                    if not isinstance(data, dict):
                        continue

                    if "__interrupt__" in data:
                        interrupts: list[Interrupt] = data["__interrupt__"]
                        for interrupt_obj in interrupts:
                            try:
                                pending_interrupts[interrupt_obj.id] = interrupt_obj.value
                                interrupt_occurred = True
                            except Exception:
                                pass

                # Handle MESSAGES stream
                elif stream_mode == "messages":
                    if not is_main_agent:
                        continue

                    if not isinstance(data, tuple) or len(data) != 2:
                        continue

                    message, _metadata = data

                    if isinstance(message, ToolMessage):
                        tool_id = getattr(message, "tool_call_id", None)
                        tool_status = getattr(message, "status", "success")
                        tool_content = str(message.content) if message.content else ""

                        yield {
                            "event": WSEventType.TOOL_CALL_RESULT,
                            "data": {
                                "tool_id": tool_id,
                                "result": tool_content[:500],  # Truncate long outputs
                                "status": tool_status,
                            }
                        }
                        continue

                    # Check for AIMessageChunk with content_blocks
                    if not hasattr(message, "content_blocks"):
                        continue

                    for block in message.content_blocks:
                        block_type = block.get("type")

                        if block_type == "text":
                            text = block.get("text", "")
                            if text:
                                pending_text += text
                                yield {
                                    "event": WSEventType.MESSAGE_CHUNK,
                                    "data": {
                                        "message_id": message_id,
                                        "chunk": text,
                                        "is_complete": False,
                                    }
                                }

                        elif block_type in ("tool_call_chunk", "tool_call"):
                            chunk_name = block.get("name")
                            chunk_args = block.get("args")
                            chunk_id = block.get("id")
                            chunk_index = block.get("index")

                            buffer_key = chunk_index if chunk_index is not None else (chunk_id or f"unknown-{len(tool_call_buffers)}")

                            buffer = tool_call_buffers.setdefault(
                                buffer_key,
                                {"name": None, "id": None, "args": None, "args_parts": []},
                            )

                            if chunk_name:
                                buffer["name"] = chunk_name
                            if chunk_id:
                                buffer["id"] = chunk_id

                            if isinstance(chunk_args, dict):
                                buffer["args"] = chunk_args
                            elif isinstance(chunk_args, str):
                                if chunk_args:
                                    parts = buffer.setdefault("args_parts", [])
                                    if not parts or chunk_args != parts[-1]:
                                        parts.append(chunk_args)
                                    buffer["args"] = "".join(parts)

                            buffer_name = buffer.get("name")
                            buffer_id = buffer.get("id")
                            if buffer_name is None:
                                continue

                            parsed_args = buffer.get("args")
                            if isinstance(parsed_args, str):
                                if not parsed_args:
                                    continue
                                try:
                                    parsed_args = json.loads(parsed_args)
                                except json.JSONDecodeError:
                                    continue
                            elif parsed_args is None:
                                continue

                            if not isinstance(parsed_args, dict):
                                parsed_args = {"value": parsed_args}

                            if buffer_id is not None and buffer_id not in displayed_tool_ids:
                                displayed_tool_ids.add(buffer_id)
                                yield {
                                    "event": WSEventType.TOOL_CALL_START,
                                    "data": {
                                        "tool_id": buffer_id,
                                        "tool_name": buffer_name,
                                        "arguments": parsed_args,
                                    }
                                }
                                tool_call_buffers.pop(buffer_key, None)

            # Handle HITL after stream completes
            if interrupt_occurred and pending_interrupts:
                if auto_approve:
                    # Auto-approve all
                    for interrupt_id, hitl_request in pending_interrupts.items():
                        action_requests = hitl_request.get("action_requests", [])
                        decisions = [{"type": "approve"} for _ in action_requests]
                        hitl_response[interrupt_id] = {"decisions": decisions}
                else:
                    # Request approval for each
                    for interrupt_id, hitl_request in pending_interrupts.items():
                        action_requests = hitl_request.get("action_requests", [])
                        decisions = []

                        for action_request in action_requests:
                            tool_name = action_request.get("name", "unknown")
                            tool_id = action_request.get("id")
                            args = action_request.get("args", {})

                            # Build description
                            description = f"Tool: {tool_name}"
                            if tool_name == "shell":
                                cmd = args.get("command", "")
                                description = f"Shell command: {cmd}"
                            elif tool_name == "write_file":
                                path = args.get("file_path", "")
                                description = f"Write file: {path}"

                            # Send HITL request and wait
                            yield {
                                "event": WSEventType.HITL_REQUEST,
                                "data": {
                                    "request_id": interrupt_id,
                                    "tool_id": tool_id,
                                    "tool_name": tool_name,
                                    "description": description,
                                    "arguments": args,
                                }
                            }

                            # For now, we'll pause here - the adapter handles the waiting
                            decision = await adapter.request_approval(
                                tool_id, tool_name, description, args
                            )
                            decisions.append(decision)

                            if decision.get("type") == "reject":
                                yield {
                                    "event": WSEventType.AGENT_STEP,
                                    "data": {"step": "rejected", "description": f"User rejected {tool_name}"}
                                }
                                break

                        hitl_response[interrupt_id] = {"decisions": decisions}

                # Continue with HITL response
                if hitl_response and not any(
                    d.get("type") == "reject" 
                    for resp in hitl_response.values() 
                    for d in resp.get("decisions", [])
                ):
                    stream_input = Command(resume=hitl_response)
                    continue

            # If no interrupt or processing complete, break
            break

        # Send completion
        if pending_text:
            yield {
                "event": WSEventType.MESSAGE_COMPLETE,
                "data": {
                    "message_id": message_id,
                    "content": pending_text,
                    "is_complete": True,
                }
            }

    except asyncio.CancelledError:
        yield {
            "event": WSEventType.AGENT_STEP,
            "data": {"step": "cancelled", "description": "Interrupted by user"}
        }
        raise

    except Exception as e:
        yield {
            "event": WSEventType.ERROR,
            "data": {"message": str(e)}
        }


class AgentAdapter:
    """
    Full adapter integrating DeepAgents CLI with WebSocket interface.
    
    This replaces the simulated adapter with real agent integration.
    """

    def __init__(self, user_id: str, chat_id: str, thread_id: str) -> None:
        """Initialize the adapter."""
        self.user_id = user_id
        self.chat_id = chat_id
        self.thread_id = thread_id
        self._agent = None
        self._backend = None
        self._running = False
        self._cancel_event = asyncio.Event()
        self._ws_adapter = WebSocketUIAdapter(chat_id, user_id)
        self._auto_approve = False

    async def initialize(self) -> None:
        """Initialize the DeepAgents agent."""
        try:
            # Inject API keys into environment for deepagents_cli
            import os
            if settings.openai_api_key:
                os.environ["OPENAI_API_KEY"] = settings.openai_api_key
            if settings.anthropic_api_key:
                os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
            if settings.google_api_key:
                os.environ["GOOGLE_API_KEY"] = settings.google_api_key
            if settings.tavily_api_key:
                os.environ["TAVILY_API_KEY"] = settings.tavily_api_key

            from deepagents_cli.agent import create_cli_agent
            from deepagents_cli.config import create_model
            from deepagents_cli.tools import fetch_url, http_request, web_search
            
            model = create_model(settings.deepagents_model)
            
            tools = [http_request, fetch_url]
            if settings.tavily_api_key:
                tools.append(web_search)
            
            # Load user's extra tools
            extra_tools = await self._load_extra_tools()
            tools.extend(extra_tools)
            
            self._agent, self._backend = create_cli_agent(
                model=model,
                assistant_id=f"user_{self.user_id}",
                tools=tools,
                auto_approve=False,  # We handle HITL via WebSocket
            )
        except (ImportError, SystemExit, Exception) as e:
            import traceback
            traceback.print_exc()
            print(f"DeepAgents CLI not available or configuration error: {e}")
            self._agent = None
            self._backend = None

    async def _load_extra_tools(self) -> list:
        """Load user's extra tools."""
        try:
            from app.services.extra_tools import ExtraToolsManager
            mgr = ExtraToolsManager(self.user_id)
            tools_list = mgr.list_tools()
            
            loaded = []
            for tool_info in tools_list:
                func = mgr.load_tool(tool_info['name'])
                if func:
                    loaded.append(func)
            return loaded
        except Exception:
            return []

    async def process_message(
        self,
        message: str,
        attachments: list[str] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process user message with real agent streaming.
        """
        self._running = True
        self._cancel_event.clear()

        if self._agent is None:
            # Fallback to simulated response
            async for event in self._simulate_response(message):
                yield event
            return

        try:
            async for event in execute_task_websocket(
                user_input=message,
                agent=self._agent,
                assistant_id=f"user_{self.user_id}",
                thread_id=self.thread_id,
                adapter=self._ws_adapter,
                auto_approve=self._auto_approve,
            ):
                if self._cancel_event.is_set():
                    yield {
                        "event": WSEventType.AGENT_COMPLETE,
                        "data": {"cancelled": True}
                    }
                    return
                yield event

        except asyncio.CancelledError:
            yield {
                "event": WSEventType.AGENT_COMPLETE,
                "data": {"cancelled": True}
            }
        except Exception as e:
            yield {
                "event": WSEventType.ERROR,
                "data": {"message": str(e)}
            }
        finally:
            self._running = False

    async def _simulate_response(
        self,
        message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Fallback simulation when agent not available."""
        message_id = str(uuid.uuid4())

        yield {
            "event": WSEventType.AGENT_THINKING,
            "data": {"message": "Processing..."},
        }
        await asyncio.sleep(0.5)

        response = f"Sizning so'rovingiz qabul qilindi: '{message[:50]}...'\n\n"
        response += "⚠️ Agent ishga tushmadi. Sababi: API kalitlari topilmadi yoki noto'g'ri konfiguratsiya.\n"
        response += "Iltimos, `.env` faylida `OPENAI_API_KEY` yoki `ANTHROPIC_API_KEY` o'rnatilganligini tekshiring."

        for i in range(0, len(response), 20):
            chunk = response[i:i+20]
            yield {
                "event": WSEventType.MESSAGE_CHUNK,
                "data": {
                    "message_id": message_id,
                    "chunk": chunk,
                    "is_complete": False,
                }
            }
            await asyncio.sleep(0.05)

        yield {
            "event": WSEventType.MESSAGE_COMPLETE,
            "data": {
                "message_id": message_id,
                "content": response,
                "is_complete": True,
            }
        }

    async def cancel(self) -> None:
        """Cancel current generation."""
        self._cancel_event.set()

    async def handle_hitl_response(
        self,
        request_id: str,
        response: str,
        modifications: dict | None = None,
    ) -> bool:
        """Handle HITL response from frontend."""
        return self._ws_adapter.resolve_hitl(request_id, response)

    async def save_extra_tool(
        self,
        tool_name: str,
        code: str,
        description: str,
        parameters: dict | None = None,
    ) -> Path:
        """Save dynamically generated tool."""
        from app.services.extra_tools import ExtraToolsManager
        mgr = ExtraToolsManager(self.user_id)
        return mgr.save_tool(tool_name, code, description, parameters)


# Adapter cache
_adapters: dict[str, AgentAdapter] = {}


async def get_adapter(user_id: str, chat_id: str, thread_id: str) -> AgentAdapter:
    """Get or create adapter for a chat session."""
    key = f"{user_id}:{chat_id}"
    
    if key not in _adapters:
        adapter = AgentAdapter(user_id, chat_id, thread_id)
        await adapter.initialize()
        _adapters[key] = adapter
    
    return _adapters[key]


def remove_adapter(user_id: str, chat_id: str) -> None:
    """Remove adapter from cache."""
    key = f"{user_id}:{chat_id}"
    _adapters.pop(key, None)


async def resolve_hitl_request(user_id: str, chat_id: str, request_id: str, response: str) -> bool:
    """Resolve a HITL request for a chat session.
    
    Args:
        user_id: User ID
        chat_id: Chat ID
        request_id: The HITL request ID
        response: User response ('approve' or 'reject')
        
    Returns:
        True if successfully resolved, False otherwise
    """
    key = f"{user_id}:{chat_id}"
    
    if key not in _adapters:
        return False
    
    adapter = _adapters[key]
    
    # Resolve through the UI adapter
    if adapter.ui_adapter:
        await adapter.ui_adapter.resolve_hitl(request_id, response)
        return True
    
    return False
