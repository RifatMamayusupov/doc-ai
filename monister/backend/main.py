"""
Monister Backend - FastAPI server with WebSocket, file context, and data preview.
Refactored with preview_service, industry_modules, workflow_engine, deadline_tracker.
"""

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any
from datetime import datetime

# Add parent path for deepagents_cli imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File as UploadFileParam, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import aiofiles
import shutil

from config import settings
from agent_engine import MonisterAgent, create_agent
from tools import get_all_tools

# Auth and Admin
from database import get_db, User, File as FileModel, get_file_category, init_db
from auth import (
    UserCreate, UserLogin, Token,
    create_user, authenticate_user, create_access_token,
    get_current_user, get_current_user_optional, create_admin_if_not_exists,
    get_or_create_system_user, decode_token,
    ProfileUpdate, update_user_profile,
)
from admin import router as admin_router
from admin_config import router as admin_config_router
from sqlalchemy.orm import Session

# NEW: Core modules
from preview_service import (
    process_tool_preview, process_text_preview,
    FILE_GENERATING_TOOLS, detect_file_type,
)
from industry_modules import (
    get_all_modules, get_module, get_module_documents,
    detect_industry, build_industry_context,
)
from workflow_engine import workflow_manager, create_document_generation_workflow, create_batch_workflow
from deadline_tracker import deadline_tracker, Deadline

from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and create admin user on startup."""
    init_db()
    db = next(get_db())
    create_admin_if_not_exists(db)
    get_or_create_system_user(db)
    db.close()
    print("\u2705 Database initialized, admin user ready!")
    yield


# ============== FastAPI App ==============
app = FastAPI(
    title="Monister Agentic AI",
    description="Enterprise-grade AI workspace with deepagents framework",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include admin router
app.include_router(admin_router)
app.include_router(admin_config_router)

# Mount static files AFTER routes to prevent path conflicts
app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")
if settings.templates_dir.exists():
    app.mount("/templates", StaticFiles(directory=settings.templates_dir), name="templates")

# Mount data directory for user files
settings.data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/data", StaticFiles(directory=settings.data_dir), name="data")



# ============== Connection Manager ==============
class ConnectionManager:
    """Manage WebSocket connections, agents, and file contexts."""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.agents: dict[str, MonisterAgent] = {}
        self.thread_ids: dict[str, str] = {}
        # NEW: File context per client
        self.file_contexts: dict[str, list[dict]] = {}
        # NEW: User context per client
        self.users: dict[str, dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, user: dict | None = None):
        """Accept connection and create agent."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.file_contexts[client_id] = []
        if user:
            self.users[client_id] = user
        
        # Create agent for this client
        custom_tools = get_all_tools()
        agent = create_agent(
            assistant_id=f"monister-{client_id[:8]}",
            tools=custom_tools,
            auto_approve=True,  # TEMP: Gemini HITL resume issue - auto-approve all tools
        )
        
        # Initialize agent
        await agent.initialize()
        
        self.agents[client_id] = agent
        self.thread_ids[client_id] = agent.thread_id
        
        # Send connected message with available tools
        await self.send_json(client_id, {
            "type": "connected",
            "client_id": client_id,
            "thread_id": agent.thread_id,
            "tools": agent.get_available_tools(),
        })
    
    def disconnect(self, client_id: str):
        """Clean up on disconnect."""
        self.active_connections.pop(client_id, None)
        self.agents.pop(client_id, None)
        self.thread_ids.pop(client_id, None)
        self.file_contexts.pop(client_id, None)
        self.users.pop(client_id, None)
    
    async def send_json(self, client_id: str, data: dict):
        """Send JSON to a specific client. Emits dual-format for frontend compat."""
        if client_id in self.active_connections:
            try:
                # Build dual-format message:
                # Keep original 'type' key for monister frontend
                # Add 'event' + 'data' envelope for real frontend
                outgoing = dict(data)
                
                # Map backend type → real frontend event name
                type_to_event = {
                    "token": "message_chunk",
                    "stream": "message_chunk",
                    "complete": "message_complete",
                    "error": "error",
                    "connected": "connected",
                    "tool_start": "tool_call_start",
                    "tool_end": "tool_call_result",
                    "hitl_request": "hitl_request",
                    "status": "process_status",
                    "log": "agent_step",
                    "data_preview": "document_ready",
                }
                
                msg_type = data.get("type", "")
                if "event" not in outgoing:
                    outgoing["event"] = type_to_event.get(msg_type, msg_type)
                
                # Build data payload for real frontend
                if "data" not in outgoing or not isinstance(outgoing.get("data"), dict):
                    # Extract all non-meta keys as data
                    payload = {k: v for k, v in data.items() if k not in ("type", "event")}
                    # Special mappings
                    if msg_type in ("token", "stream"):
                        payload["chunk"] = data.get("content", data.get("data", ""))
                        payload["message_id"] = data.get("message_id", f"msg-{client_id}")
                    elif msg_type == "complete":
                        payload["content"] = data.get("content", data.get("message", ""))
                    outgoing["data"] = payload
                
                await self.active_connections[client_id].send_json(outgoing)
            except Exception:
                self.disconnect(client_id)
    
    def get_agent(self, client_id: str) -> MonisterAgent | None:
        """Get agent for a client."""
        return self.agents.get(client_id)
        
    def get_user(self, client_id: str) -> dict | None:
        """Get user for a client."""
        return self.users.get(client_id)
    
    def add_file_context(self, client_id: str, file_info: dict):
        """Add file to client's context."""
        if client_id in self.file_contexts:
            self.file_contexts[client_id].append(file_info)
    
    def get_file_context(self, client_id: str) -> list[dict]:
        """Get files in client's context."""
        return self.file_contexts.get(client_id, [])
    
    def build_context_prompt(self, client_id: str) -> str:
        """Build context prompt with file information."""
        files = self.get_file_context(client_id)
        if not files:
            return ""
        
        context = "\n\n[YUKLANGAN FAYLLAR - Bu fayllarni tahlil qilish uchun tegishli toollarni ishlat]\n"
        for f in files:
            fpath = f.get('path', '')
            ftype = f.get('type', 'unknown')
            fname = f.get('filename', 'file')
            
            # Give explicit instructions based on file type
            if '.pdf' in fname.lower() or 'pdf' in ftype.lower():
                context += f"📄 PDF FAYL: {fname}\n"
                context += f"   To'liq yo'li: {fpath}\n"
                context += f"   ➡️ ISHLATILISHI KERAK: ocr_extract(file_path=\"{fpath}\")\n\n"
            elif any(ext in fname.lower() for ext in ['.xlsx', '.xls', '.csv']):
                context += f"📊 EXCEL/CSV FAYL: {fname}\n"
                context += f"   To'liq yo'li: {fpath}\n"
                context += f"   ➡️ ISHLATILISHI KERAK: parse_excel(file_path=\"{fpath}\")\n\n"
            elif any(ext in fname.lower() for ext in ['.png', '.jpg', '.jpeg']):
                context += f"🖼️ RASM: {fname}\n"
                context += f"   To'liq yo'li: {fpath}\n"
                context += f"   ➡️ ISHLATILISHI KERAK: ocr_extract(file_path=\"{fpath}\")\n\n"
            else:
                context += f"📁 FAYL: {fname} (path: {fpath})\n"
        
        context += "MUHIM: Foydalanuvchi fayl haqida so'rasa, USHBU fayllardan foydalaning!\n"
        return context


manager = ConnectionManager()


# ============== WebSocket Endpoint ==============
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, token: str = Query(None)):
    """WebSocket endpoint for real-time agent communication."""
    await _handle_websocket(websocket, client_id, token)


@app.websocket("/ws/chat/{chat_id}/{token}")
async def websocket_chat_endpoint(websocket: WebSocket, chat_id: str, token: str):
    """WebSocket endpoint for the real frontend (token in URL path)."""
    await _handle_websocket(websocket, chat_id, token)


async def _handle_websocket(websocket: WebSocket, client_id: str, token: str = None):
    """WebSocket endpoint for real-time agent communication."""
    # Authenticate user from token
    user = None
    if token:
        payload = decode_token(token)
        if payload:
            user = {"id": payload.get("sub"), "username": payload.get("username"), "is_admin": payload.get("is_admin")}
            
    await manager.connect(websocket, client_id, user)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # === Normalize message format ===
            # Real frontend sends: {event: 'send_message', data: {content, attachments}}
            # Monister frontend sends: {type: 'message', content: '...'}
            if "event" in data and "data" in data:
                event_name = data["event"]
                event_data = data["data"] or {}
                # Map real frontend events to internal types
                event_map = {
                    "send_message": "message",
                    "hitl_response": "hitl_response",
                    "cancel_generation": "stop",
                    "template_selected": "template_selected",
                }
                msg_type = event_map.get(event_name, event_name)
                # Flatten data into top-level for compatibility
                data = {"type": msg_type, **event_data}
                # Map 'response' to 'decision' for HITL
                if msg_type == "hitl_response" and "response" in data:
                    data["decision"] = data.pop("response")
                    data["interrupt_id"] = data.get("request_id", data.get("interrupt_id"))
            
            msg_type = data.get("type", "")
            
            agent = manager.get_agent(client_id)
            if not agent:
                await manager.send_json(client_id, {
                    "type": "error",
                    "message": "Agent not initialized"
                })
                continue
            
            # Handle message types
            if msg_type == "message":
                content = data.get("content", "")
                active_tools = data.get("active_tools")
                
                # ALWAYS add file context if files are uploaded
                file_context = manager.build_context_prompt(client_id)
                if file_context:
                    content = file_context + "\n\nFoydalanuvchi so'rovi: " + content
                
                thread_id = manager.thread_ids.get(client_id, agent.thread_id)
                
                try:
                    # DB save helper for preview_service
                    def _save_file_to_db(move_result: dict):
                        db = next(get_db())
                        try:
                            db_file = FileModel(
                                user_id=move_result["user_id"],
                                filename=move_result["new_filename"],
                                original_name=move_result["new_filename"],
                                file_type=move_result["category"],
                                mime_type="application/octet-stream",
                                path=move_result["new_path"],
                                size=move_result["size"],
                            )
                            db.add(db_file)
                            db.commit()
                        except Exception as db_e:
                            print(f"DB save error: {db_e}")
                        finally:
                            db.close()

                    async for event in agent.astream_events(
                        content,
                        thread_id=thread_id,
                        active_tools=active_tools,
                    ):
                        # === Tool output → auto-preview ===
                        if event.get("type") == "tool_end":
                            tool_name = event.get("name")
                            output = event.get("output", "")
                            current_user = manager.get_user(client_id)
                            file_contexts = manager.get_file_context(client_id)

                            preview_event = await process_tool_preview(
                                tool_name=tool_name,
                                output=output,
                                client_id=client_id,
                                file_contexts=file_contexts,
                                user=current_user,
                                send_fn=manager.send_json,
                                db_save_fn=_save_file_to_db,
                            )
                            await manager.send_json(client_id, preview_event.to_dict())

                        # === Agent text → scan for file references ===
                        if event.get("type") in ("stream", "message"):
                            text_content = event.get("content", "") or event.get("data", "")
                            await process_text_preview(
                                text_content=str(text_content),
                                client_id=client_id,
                                send_fn=manager.send_json,
                            )

                        await manager.send_json(client_id, event)
                except Exception as e:
                    await manager.send_json(client_id, {
                        "type": "error",
                        "message": str(e)
                    })
            
            elif msg_type == "file_upload":
                # Handle file upload notification from frontend
                file_info = {
                    "file_id": data.get("file_id"),
                    "filename": data.get("filename"),
                    "path": data.get("path"),
                    "type": data.get("file_type"),
                    "size": data.get("size"),
                }
                manager.add_file_context(client_id, file_info)
                
                # Notify frontend that file is ready
                await manager.send_json(client_id, {
                    "type": "file_ready",
                    "filename": file_info["filename"],
                    "message": f"File '{file_info['filename']}' is ready. Ask me to analyze it!"
                })
                
                # Add log
                await manager.send_json(client_id, {
                    "type": "log",
                    "level": "info",
                    "message": f"File uploaded: {file_info['filename']}"
                })
            
            elif msg_type == "hitl_response":
                interrupt_id = data.get("interrupt_id")
                decision = data.get("decision", "reject")
                thread_id = data.get("thread_id") or manager.thread_ids.get(client_id)
                
                try:
                    async for event in agent.handle_hitl_response(
                        thread_id=thread_id,
                        interrupt_id=interrupt_id,
                        decision=decision,
                    ):
                        # Use same preview logic as main message handler
                        if event.get("type") == "tool_end":
                            tool_name = event.get("name")
                            output = event.get("output", "")
                            current_user = manager.get_user(client_id)
                            file_contexts = manager.get_file_context(client_id)

                            preview_event = await process_tool_preview(
                                tool_name=tool_name,
                                output=output,
                                client_id=client_id,
                                file_contexts=file_contexts,
                                user=current_user,
                                send_fn=manager.send_json,
                                db_save_fn=None,
                            )
                            await manager.send_json(client_id, preview_event.to_dict())

                        await manager.send_json(client_id, event)
                except Exception as e:
                    await manager.send_json(client_id, {
                        "type": "error",
                        "message": str(e)
                    })
            
            elif msg_type == "get_tools":
                tools = agent.get_available_tools()
                await manager.send_json(client_id, {
                    "type": "tools",
                    "tools": tools,
                })
            
            elif msg_type == "get_files":
                files = manager.get_file_context(client_id)
                await manager.send_json(client_id, {
                    "type": "files",
                    "files": files,
                })
            
            elif msg_type == "stop":
                # Handle stop generation request
                # Note: Currently we can't actually cancel LangGraph execution mid-stream
                # but we acknowledge the stop and the frontend handles UI state
                await manager.send_json(client_id, {
                    "type": "log",
                    "level": "warn",
                    "message": "Generation stop requested"
                })
            
            elif msg_type == "ping":
                await manager.send_json(client_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        await manager.send_json(client_id, {
            "type": "error",
            "message": str(e)
        })
        manager.disconnect(client_id)


# ============== REST Endpoints ==============
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": ["file_context", "data_preview", "real_time_pipeline", "auth", "admin"]
    }


# ============== Auth Endpoints ==============
@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
    )
    
    # Create user directory
    user_dir = settings.data_dir / user.username
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Create access token
    token = create_access_token(user.id, user.username, user.is_admin)
    
    return Token(
        access_token=token,
        user=user.to_dict(),
    )


@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token."""
    user = authenticate_user(db, credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )
    
    token = create_access_token(user.id, user.username, user.is_admin)
    
    return Token(
        access_token=token,
        user=user.to_dict(),
    )


@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user.to_dict()


@app.put("/api/auth/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile (telegram_username, email)."""
    updated_user = update_user_profile(db, current_user, profile_data)
    return {"success": True, "user": updated_user.to_dict()}


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = UploadFileParam(...),
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Upload a file - saves to user folder if authenticated, or uploads folder if not."""
    file_id = str(uuid.uuid4())[:8]
    original_name = file.filename or "unknown"
    extension = Path(original_name).suffix.lower()
    
    # Determine file category
    file_category = get_file_category(original_name, file.content_type)
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    if current_user:
        # Authenticated user - save to data/{username}/{date}/{file_type}/
        date_str = datetime.now().strftime("%Y-%m-%d")
        user_dir = settings.data_dir / current_user.username / date_str / file_category
        user_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = user_dir / f"{file_id}_{original_name}"
        relative_url = f"/data/{current_user.username}/{date_str}/{file_category}/{file_id}_{original_name}"
        
        # Save to database
        db_file = FileModel(
            user_id=current_user.id,
            filename=f"{file_id}_{original_name}",
            original_name=original_name,
            file_type=file_category,
            mime_type=file.content_type,
            path=str(file_path),
            size=file_size,
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
    else:
        # Unauthenticated - use legacy uploads folder
        uploads_dir = settings.uploads_dir
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = uploads_dir / f"{file_id}{extension}"
        relative_url = f"/uploads/{file_id}{extension}"
    
    # Write file
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)
    
    return {
        "file_id": file_id,
        "filename": original_name,
        "path": str(file_path),
        "url": relative_url,
        "size": file_size,
        "type": file.content_type,
        "category": file_category,
    }


@app.get("/api/templates")
async def get_templates():
    """Get list of available document templates."""
    templates = []
    templates_dir = settings.templates_dir
    
    if templates_dir.exists():
        for category_dir in templates_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                for template_file in category_dir.iterdir():
                    if template_file.suffix in [".docx", ".jinja2", ".html"]:
                        templates.append({
                            "id": f"{category}-{template_file.stem}",
                            "name": template_file.stem.replace("_", " ").title(),
                            "category": category,
                            "path": str(template_file),
                            "type": template_file.suffix[1:],
                        })
    
    return {"templates": templates}


@app.get("/api/tools")
async def get_tools():
    """Get list of available tools."""
    tools = get_all_tools()
    tool_info = []
    
    for t in tools:
        name = getattr(t, "name", None) or getattr(t, "__name__", "unknown")
        description = getattr(t, "description", None) or getattr(t, "__doc__", "") or ""
        tool_info.append({"name": name, "description": description})
    
    tool_info.extend([
        {"name": "shell", "description": "Execute shell commands (local)"},
        {"name": "write_file", "description": "Create or overwrite files"},
        {"name": "edit_file", "description": "Edit existing files"},
        {"name": "read_file", "description": "Read file contents"},
        {"name": "list_directory", "description": "List directory contents"},
        {"name": "http_request", "description": "Make HTTP requests"},
        {"name": "fetch_url", "description": "Fetch and parse URL content"},
        {"name": "web_search", "description": "Search the web using Tavily"},
        {"name": "execute_code", "description": "Execute Python code in sandbox"},
    ])
    
    return {"tools": tool_info}


# ============== Industry Module Endpoints ==============
@app.get("/api/industries")
async def list_industries():
    """Get all available industry modules."""
    return {"industries": get_all_modules()}


@app.get("/api/industries/{module_id}")
async def get_industry(module_id: str):
    """Get a specific industry module with its documents."""
    module = get_module(module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Industry module not found")
    return {
        "id": module.id,
        "name": module.name,
        "name_uz": module.name_uz,
        "icon": module.icon,
        "description": module.description,
        "description_uz": module.description_uz,
        "documents": get_module_documents(module_id),
    }


@app.post("/api/industries/detect")
async def detect_industry_endpoint(request: dict = None):
    """Detect relevant industry modules from text."""
    text = (request or {}).get("text", "")
    if not text:
        return {"matches": []}
    return {"matches": detect_industry(text)}


# ============== Workflow Endpoints ==============
@app.get("/api/workflows")
async def list_workflows():
    """List all workflows."""
    return {"workflows": workflow_manager.list_all()}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow."""
    wf = workflow_manager.get(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf.to_dict()


@app.post("/api/workflows")
async def create_workflow(request: dict):
    """Create a new workflow."""
    wf_type = request.get("type", "document")
    name = request.get("name", "Yangi workflow")
    template = request.get("template_path", "")
    fields = request.get("fields", {})
    data_source = request.get("data_source", "")
    industry = request.get("industry", "")

    if wf_type == "batch":
        wf = create_batch_workflow(name, template, data_source)
    else:
        wf = create_document_generation_workflow(name, template, fields, industry)

    workflow_manager.create(wf)
    return wf.to_dict()


# ============== Deadline Endpoints ==============
@app.get("/api/deadlines")
async def list_deadlines(user_id: int = None):
    """Get all active deadlines."""
    return {"deadlines": deadline_tracker.get_all(user_id)}


@app.get("/api/deadlines/alerts")
async def get_deadline_alerts(user_id: int = None):
    """Get urgent deadline alerts."""
    return {"alerts": deadline_tracker.get_alerts(user_id)}


@app.get("/api/deadlines/upcoming")
async def get_upcoming_deadlines(days: int = 30, user_id: int = None):
    """Get deadlines due within N days."""
    return {"deadlines": deadline_tracker.get_upcoming(days, user_id)}


@app.post("/api/deadlines")
async def create_deadline(request: dict):
    """Create a new deadline."""
    dl = Deadline(
        id=f"dl-{uuid.uuid4().hex[:8]}",
        title=request.get("title", ""),
        title_uz=request.get("title_uz", request.get("title", "")),
        description=request.get("description", ""),
        document_type=request.get("document_type", ""),
        industry_module=request.get("industry_module", ""),
        due_date=request.get("due_date", ""),
        user_id=request.get("user_id", 0),
        tags=request.get("tags", []),
        auto_renew=request.get("auto_renew", False),
        renew_days=request.get("renew_days", 0),
    )
    deadline_tracker.add(dl)
    return dl.to_dict()


@app.put("/api/deadlines/{deadline_id}/complete")
async def complete_deadline(deadline_id: str):
    """Mark a deadline as complete."""
    dl = deadline_tracker.complete(deadline_id)
    if not dl:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return dl.to_dict()


# ============== AI Endpoints ==============
@app.post("/api/sessions/{session_id}/title/generate")
async def generate_session_title(session_id: str):
    """Generate a title for the session using AI."""
    session = session_manager.get_session(session_id)
    if not session or not session.messages:
        return {"title": session.title if session else "Yangi chat"}
    
    # helper to get messages text
    conversation = "\n".join([f"{m.role}: {m.content}" for m in session.messages[:5]])
    
    try:
        from deepagents_cli.config import create_model
        from langchain_core.messages import HumanMessage
        
        model = create_model()
        
        prompt = f"""Summarize the following conversation into a short, concise title (max 5 words).
        Language: Uzbek.
        Do not use quotes.
        
        Conversation:
        {conversation}
        
        Title:"""
        
        response = await model.ainvoke([HumanMessage(content=prompt)])
        title = response.content.strip().replace('"', '')
        
        # Update session
        session_manager.update_session_title(session_id, title)
        
        return {"title": title}
    except Exception as e:
        print(f"Title generation error: {e}")
        return {"title": session.title, "error": str(e)}


@app.post("/api/templates/recommend")
async def recommend_templates(request: dict = None):
    """Recommend templates based on user query."""
    query = (request or {}).get("query", "")
    if not query:
        return {"recommendations": []}
        
    try:
        from template_engine import list_templates
        from deepagents_cli.config import create_model
        from langchain_core.messages import HumanMessage
        import json
        
        templates = list_templates()
        templates_info = "\n".join([f"- ID: {t['id']}, Name: {t['name']}, Category: {t['category']}" for t in templates])
        
        model = create_model()
        
        prompt = f"""User query: "{query}"
        
        Available templates:
        {templates_info}
        
        Task: Recommend the top 3 most relevant templates for this query.
        Return ONLY a JSON array of template IDs. Example: ["category-name1", "category-name2"]
        If none are relevant, return empty list [].
        """
        
        response = await model.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        # Clean markdown code blocks if present
        if "```" in content:
            content = content.replace("```json", "").replace("```", "")
        
        recommended_ids = json.loads(content)
        
        # Filter full template objects
        recommendations = [t for t in templates if t['id'] in recommended_ids]
        
        return {"recommendations": recommendations}
        
    except Exception as e:
        print(f"Recommendation error: {e}")
        # Fallback: simple keyword match
        rec = []
        templates = list_templates()
        for t in templates:
            if query.lower() in t['name'].lower() or query.lower() in t['category'].lower():
                rec.append(t)
        return {"recommendations": rec[:3]}


# ============== Session Endpoints ==============
from sessions import session_manager, ChatMessage
from code_executor import execute_code, ExecutionResult
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    title: str = "Yangi chat"


class UpdateTitleRequest(BaseModel):
    title: str


class AddMessageRequest(BaseModel):
    role: str
    content: str


class ExecuteCodeRequest(BaseModel):
    code: str
    mode: str = "restricted"  # "restricted" or "subprocess"
    timeout: int = 30


@app.get("/api/sessions")
async def get_sessions():
    """Get all chat sessions."""
    sessions = session_manager.get_all_sessions()
    return {
        "sessions": [s.model_dump() for s in sessions]
    }


@app.post("/api/sessions")
async def create_session(request: CreateSessionRequest):
    """Create a new chat session."""
    session = session_manager.create_session(request.title)
    return session.model_dump()


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session by ID."""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@app.put("/api/sessions/{session_id}/title")
async def update_session_title(session_id: str, request: UpdateTitleRequest):
    """Update session title."""
    session = session_manager.update_session_title(session_id, request.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@app.post("/api/sessions/{session_id}/messages")
async def add_session_message(session_id: str, request: AddMessageRequest):
    """Add a message to a session."""
    import datetime
    message = ChatMessage(
        id=f"msg-{int(datetime.datetime.now().timestamp() * 1000)}",
        role=request.role,
        content=request.content,
        timestamp=datetime.datetime.now().isoformat()
    )
    session = session_manager.add_message(session_id, message)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump()


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    success = session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}


# ============== Code Execution Endpoint ==============
@app.post("/api/execute")
async def execute_python_code(request: ExecuteCodeRequest):
    """
    Execute Python code in a sandbox environment.
    
    Modes:
    - restricted: Safe execution with limited builtins
    - subprocess: Isolated process execution
    """
    result = execute_code(
        code=request.code,
        mode=request.mode,
        timeout=request.timeout
    )
    
    return {
        "status": result.status.value,
        "output": result.output,
        "error": result.error,
        "execution_time": result.execution_time,
    }


# ============== /api/chats Endpoints (real frontend compatibility) ==============
@app.get("/api/chats")
async def get_chats():
    """Return all chats in the format the frontend expects: {chats: [...], total: N}."""
    sessions = session_manager.get_all_sessions()
    chats = []
    for s in sessions:
        d = s.model_dump()
        # Frontend expects 'id', 'title', 'created_at', 'updated_at'
        chats.append(d)
    return {"chats": chats, "total": len(chats)}

@app.post("/api/chats")
async def create_chat(request: CreateSessionRequest):
    """Create a new chat and return it."""
    session = session_manager.create_session(request.title)
    return session.model_dump()

@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: str):
    """Get a single chat by ID."""
    session = session_manager.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat not found")
    return session.model_dump()

@app.patch("/api/chats/{chat_id}")
async def update_chat(chat_id: str, request: dict):
    """Update chat properties (title, is_archived, etc)."""
    session = session_manager.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat not found")
    if "title" in request:
        session_manager.update_session_title(chat_id, request["title"])
    return session_manager.get_session(chat_id).model_dump()

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat."""
    success = session_manager.delete_session(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"deleted": True}

@app.get("/api/chats/{chat_id}/messages")
async def get_chat_messages(chat_id: str):
    """Return messages for a chat."""
    session = session_manager.get_session(chat_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat not found")
    return [m.model_dump() for m in session.messages]


# ============== Main ==============
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
