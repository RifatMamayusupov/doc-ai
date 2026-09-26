"""
Monister Agent Engine - deepagents_cli bilan integratsiya.
Bu versiya deepagents Framework-ning middleware va backenlaridan foydalanadi.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Callable

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import StructuredTool, tool
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.pregel import Pregel

# DeepAgents CLI imports
from deepagents_cli.agent import create_cli_agent
from deepagents_cli.config import (
    console,
    create_model,
    settings,
)
from deepagents_cli.integrations.sandbox_factory import create_sandbox
from deepagents_cli.sessions import (
    generate_thread_id,
    get_checkpointer,
)
# Import raw functions from deepagents_cli
from deepagents_cli.tools import (
    fetch_url as _fetch_url,
    http_request as _http_request,
    web_search as _web_search,
)

from config import settings as monister_settings

# Wrap deepagents tools with StructuredTool for LangChain compatibility
http_request = StructuredTool.from_function(
    func=_http_request,
    name="http_request",
    description="Make HTTP requests to APIs and web services. Use for REST API calls.",
)

fetch_url = StructuredTool.from_function(
    func=_fetch_url,
    name="fetch_url",
    description="Fetch content from a URL and convert HTML to markdown. Use to read web pages.",
)

web_search = StructuredTool.from_function(
    func=_web_search,
    name="web_search",
    description="Search the web using Tavily. Use to find current information from the internet.",
)


# ============== System Prompt ==============
MONISTER_SYSTEM_PROMPT = """Sen Monister AI - hujjatlar va ma'lumotlar bilan ishlash uchun mo'ljallangan professional AI yordamchi.

## Sening vazifalaring:
1. **Hujjatlarni o'qish va tahlil qilish** — PDF, Word, Excel fayllarni qayta ishlash
2. **Ma'lumotlarni tozalash** — duplikatlarni o'chirish, null qiymatlarni to'ldirish
3. **OCR** — rasmlardan va PDF'lardan matn ajratib olish
4. **PII Redaction** — shaxsiy ma'lumotlarni yashirish
5. **Soha modullari** — 10 soha bo'yicha hujjatlarni avtomatik yaratish
6. **Telegramga yuborish** — tayyor hujjatlarni foydalanuvchiga yetkazish

## Soha aniqlash va avtomatlashtirish:
Foydalanuvchi hujjat so'raganda, **soha**ni avval aniqla:
- "shartnoma", "contract" → construction, legal
- "faktura", "invoice" → finance, trade
- "tibbiy", "retsept" → healthcare
- "marketing plan" → marketing
- "o'quv reja" → education
- "audit hisobot" → finance

**Oqim:**
1. Foydalanuvchi buyruq beradi → sohani aniqla
2. `detect_industry` tool bilan sohani tassiqla
3. Tegishli shablonni tanla va `fill_template` bilan to'ldir
4. Natijani preview panelda ko'rsat
5. Agar Telegram username berilsa — `send_to_telegram` bilan yubor

## Qachon qaysi toolni ishlatish:

### Fayl bilan ishlash:
- **PDF/rasm o'qish** → `ocr_extract` toolini ishlat
- **Excel/CSV o'qish** → `parse_excel` toolini ishlat
- **Fayl yaratish** → `write_file` toolini ishlat

### Ma'lumotni tozalash:
- **Null/duplikat o'chirish** → `clean_data` toolini ishlat
- **Shaxsiy ma'lumotlarni yashirish** → `redact_pii` toolini ishlat

### Soha hujjatlari:
- **Sohani aniqlash** → `detect_industry` toolini ishlat
- **Shablonni to'ldirish** → `fill_template` toolini ishlat
- **Ommaviy yaratish** → `batch_generate` toolini ishlat
- **Muvofiqlik tekshirish** → `check_compliance` toolini ishlat

### Qidiruv:
- **Internetdan qidirish** → `web_search` toolini ishlat
- **URL o'qish** → `fetch_url` yoki `http_request` toolini ishlat

### Telegram:
- **Hujjat yuborish** → `send_to_telegram` toolini ishlat
- Foydalanuvchi "@username" yoki "telegram: username" bersa, shu usernamega yubor

## Muhim qoidalar:
1. Foydalanuvchi fayl yuklasa — ALBATTA uni o'qi va tahlil qil
2. Fayl yo'li berilsa — shu yo'lni ishlatib toolni chaqir
3. **Javoblarni Markdown formatda ber** — jadvallar, sarlavhalar, bold/italic ishlat
4. Natijalarni aniq va tushunarli ko'rsatib ber
5. Agar biror tool mavjud bo'lmasa — shell orqali bajar
6. Har doim O'ZBEK tilida javob ber (agar foydalanuvchi boshqa tilda so'ramasa)
7. Natija faylini har doim **preview panel**da ko'rsat

## Fayl konteksti:
Foydalanuvchi fayl yuklagan bo'lsa, uning yo'li xabarda ko'rsatiladi. Masalan:
"[UPLOADED FILES] - path: /path/to/file.pdf"
Bu faylni o'qish uchun tegishli toolni ishlat."""


class MonisterAgent:
    """
    Monister agent using deepagents_cli framework.
    Includes FilesystemMiddleware, MemoryMiddleware, SkillsMiddleware, etc.
    """
    
    def __init__(
        self,
        assistant_id: str = "monister",
        model_name: str | None = None,
        custom_tools: list[Callable] | None = None,
        auto_approve: bool = False,
        sandbox_type: str = "none",
    ):
        self.assistant_id = assistant_id
        self.model_name = model_name or monister_settings.default_model
        self.custom_tools = custom_tools or []
        self.auto_approve = auto_approve
        self.sandbox_type = sandbox_type
        
        self.agent: Pregel | None = None
        self.checkpointer = None
        self._thread_id: str | None = None
    
    async def initialize(self) -> None:
        """Initialize the agent with deepagents framework."""
        # Get checkpointer
        self.checkpointer = InMemorySaver()
        
        # Create model
        model = create_model(model_name_override=self.model_name)
        
        # Build tools list
        tools = list(self.custom_tools)
        tools.extend([http_request, fetch_url])
        
        if settings.has_tavily:
            tools.append(web_search)
        
        # Create agent using deepagents framework
        self.agent, self.backend = create_cli_agent(
            model=model,
            assistant_id=self.assistant_id,
            tools=tools,
            sandbox=None,  # Local mode
            sandbox_type=None,
            auto_approve=self.auto_approve,
            enable_memory=True,
            enable_skills=True,
            enable_shell=True,
            checkpointer=self.checkpointer,
            system_prompt=MONISTER_SYSTEM_PROMPT,  # Custom Monister prompt
        )
        
        # Generate thread ID
        self._thread_id = generate_thread_id()
    
    @property
    def thread_id(self) -> str:
        """Get current thread ID."""
        if not self._thread_id:
            self._thread_id = generate_thread_id()
        return self._thread_id
    
    @thread_id.setter
    def thread_id(self, value: str) -> None:
        """Set thread ID."""
        self._thread_id = value
    
    async def astream_events(
        self,
        user_input: str,
        thread_id: str | None = None,
        active_tools: list[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream agent events for real-time UI updates.
        
        Yields events:
        - {"type": "status", "status": "thinking"}
        - {"type": "token", "content": "..."}
        - {"type": "tool_start", "name": "...", "inputs": {...}}
        - {"type": "tool_end", "name": "...", "output": {...}}
        - {"type": "pipeline_update", "nodes": [...]}
        - {"type": "hitl_request", "interrupt_id": "...", "message": "..."}
        - {"type": "complete", "response": "..."}
        - {"type": "error", "message": "..."}
        """
        if not self.agent:
            await self.initialize()
        
        thread_id = thread_id or self.thread_id
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50,
        }
        current_input = {"messages": [HumanMessage(content=user_input)]}
        
        try:
            yield {"type": "status", "status": "thinking"}
            
            while True:
                full_response = ""
                
                async for event in self.agent.astream_events(
                    current_input,
                    config,
                    version="v1"
                ):
                    kind = event.get("event", "")
                    
                    # Tool started
                    if kind == "on_tool_start":
                        tool_name = event.get("name", "unknown")
                        data = event.get("data", {})
                        inputs = data.get("input") if isinstance(data, dict) else str(data)
                        
                        yield {
                            "type": "tool_start",
                            "name": tool_name,
                            "inputs": inputs,
                        }
                        
                        # Update pipeline
                        yield {
                            "type": "pipeline_update",
                            "nodes": [{"id": tool_name, "status": "running"}]
                        }
                    
                    # Tool ended
                    elif kind == "on_tool_end":
                        tool_name = event.get("name", "unknown")
                        data = event.get("data", {})
                        output = data.get("output") if isinstance(data, dict) else str(data)
                        
                        yield {
                            "type": "tool_end",
                            "name": tool_name,
                            "output": str(output)[:500],  # Truncate for UI
                        }
                        
                        # Update pipeline
                        yield {
                            "type": "pipeline_update",
                            "nodes": [{"id": tool_name, "status": "complete"}]
                        }
                    
                    # Token streaming
                    elif kind == "on_chat_model_stream":
                        data = event.get("data", {})
                        if isinstance(data, dict):
                            chunk = data.get("chunk")
                            if hasattr(chunk, "content") and chunk.content:
                                content = chunk.content
                                
                                # Handle list content (Gemini format)
                                if isinstance(content, list):
                                    text_parts = []
                                    for item in content:
                                        if isinstance(item, dict) and "text" in item:
                                            text_parts.append(item["text"])
                                        elif isinstance(item, str):
                                            text_parts.append(item)
                                    content = "".join(text_parts)
                                
                                if content:
                                    full_response += content
                                    yield {"type": "token", "content": content}
                
                # Check for HITL interrupts
                snapshot = await self.agent.aget_state(config)
                
                if snapshot.next:
                    # Agent paused for permission
                    interrupt_id = None
                    interrupt_message = "Agent ruxsat so'ramoqda"
                    
                    try:
                        for task in snapshot.tasks:
                            if task.interrupts:
                                for interrupt in task.interrupts:
                                    interrupt_id = interrupt.id
                                    if hasattr(interrupt, "value"):
                                        val = interrupt.value
                                        if isinstance(val, dict):
                                            interrupt_message = val.get("description", interrupt_message)
                                    break
                            if interrupt_id:
                                break
                    except Exception:
                        pass
                    
                    yield {
                        "type": "hitl_request",
                        "interrupt_id": interrupt_id,
                        "message": interrupt_message,
                        "thread_id": thread_id,
                    }
                    return  # Wait for HITL response
                else:
                    # Agent completed
                    yield {"type": "complete", "response": full_response}
                    return
                    
        except Exception as e:
            yield {"type": "error", "message": str(e)}
    
    async def handle_hitl_response(
        self,
        thread_id: str,
        interrupt_id: str,
        decision: str,  # "approve" or "reject"
    ) -> AsyncGenerator[dict, None]:
        """Handle Human-in-the-Loop response and continue execution."""
        if not self.agent:
            await self.initialize()
        
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 50,
        }
        
        yield {"type": "status", "status": f"Decision: {decision}"}
        
        try:
            # Build HITL response in the same format as textual_adapter.py
            decisions = [{"type": decision}]
            hitl_response = {interrupt_id: {"decisions": decisions}}
            
            # Create Command for resume
            resume_command = Command(resume=hitl_response)
            
            # First try using ainvoke (non-streaming) to ensure it works
            try:
                result = await self.agent.ainvoke(
                    resume_command,
                    config=config,
                )
                
                # Extract response from result
                if isinstance(result, dict) and "messages" in result:
                    messages = result["messages"]
                    full_response = ""
                    for msg in messages:
                        if hasattr(msg, "content"):
                            content = msg.content
                            if isinstance(content, str):
                                full_response += content
                            elif isinstance(content, list):
                                for item in content:
                                    if isinstance(item, dict) and "text" in item:
                                        full_response += item["text"]
                    
                    if full_response:
                        yield {"type": "token", "content": full_response}
                
                # Check for more interrupts
                snapshot = await self.agent.aget_state(config)
                
                if snapshot and snapshot.next:
                    # There's another interrupt
                    new_interrupt_id = None
                    interrupt_message = "Agent yana ruxsat so'ramoqda"
                    
                    try:
                        for task in snapshot.tasks:
                            if hasattr(task, "interrupts") and task.interrupts:
                                for interrupt in task.interrupts:
                                    new_interrupt_id = getattr(interrupt, "id", None)
                                    if hasattr(interrupt, "value"):
                                        val = interrupt.value
                                        if isinstance(val, dict):
                                            interrupt_message = val.get("description", interrupt_message)
                                    break
                            if new_interrupt_id:
                                break
                    except Exception:
                        pass
                    
                    yield {
                        "type": "hitl_request",
                        "interrupt_id": new_interrupt_id,
                        "message": interrupt_message,
                        "thread_id": thread_id,
                    }
                else:
                    yield {"type": "complete", "response": full_response if 'full_response' in dir() else ""}
                    
            except Exception as inner_e:
                # If ainvoke fails, return the error
                error_msg = str(inner_e)
                yield {"type": "error", "message": f"Resume xatosi: {error_msg}"}
                
        except Exception as e:
            yield {"type": "error", "message": str(e)}
    
    def get_available_tools(self) -> list[dict]:
        """Get list of available tools for UI."""
        tools = []
        
        # Add custom tools
        for tool in self.custom_tools:
            # StructuredTool has .name attribute, regular functions have __name__
            name = getattr(tool, "name", None)
            if not name:
                name = getattr(tool, "__name__", "unknown")
            
            description = getattr(tool, "description", None)
            if not description:
                description = getattr(tool, "__doc__", "") or ""
            
            tools.append({
                "name": name,
                "description": description,
            })
        
        # Add deepagents_cli tools
        tools.extend([
            {"name": "http_request", "description": "Make HTTP requests to any URL"},
            {"name": "fetch_url", "description": "Fetch and parse URL content"},
            {"name": "shell", "description": "Execute shell commands"},
            {"name": "write_file", "description": "Create or overwrite files"},
            {"name": "edit_file", "description": "Edit existing files"},
            {"name": "read_file", "description": "Read file contents"},
            {"name": "list_directory", "description": "List directory contents"},
        ])
        
        if settings.has_tavily:
            tools.append({"name": "web_search", "description": "Search the web using Tavily"})
        
        return tools


# ============== Factory Function ==============
def create_agent(
    assistant_id: str = "monister",
    tools: list[Callable] | None = None,
    model_name: str | None = None,
    auto_approve: bool = False,
) -> MonisterAgent:
    """Factory function to create a configured Monister agent."""
    return MonisterAgent(
        assistant_id=assistant_id,
        model_name=model_name,
        custom_tools=tools,
        auto_approve=auto_approve,
    )


# ============== Exports ==============
__all__ = [
    "MonisterAgent",
    "create_agent",
]
