"""FastAPI main application entry point with full features."""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.chats import router as chats_router
from app.api.files import router as files_router
from app.api.templates import router as templates_router
from app.api.admin_templates import router as admin_templates_router
from app.api.connectors import router as connectors_router
from app.api.preview import router as preview_router
from app.api.workflow import router as workflow_router
from app.config import settings
from app.database import close_db, init_db
from app.services.auth import decode_token
from app.services.rate_limit import rate_limit_api, rate_limit_websocket
from app.websocket.handlers import ws_handler
from app.websocket.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings.ensure_directories()
    await init_db()
    
    # Initialize Redis if available
    try:
        from app.services.redis import redis_client
        await redis_client.connect()
        print("Redis connected")
    except Exception as e:
        print(f"Redis not available: {e}")
    
    # Initialize background task queue if available
    try:
        from app.services.tasks import TaskQueue
        await TaskQueue.connect()
        print("Task queue connected")
    except Exception as e:
        print(f"Task queue not available: {e}")
    
    # Initialize sync scheduler
    try:
        from app.services.scheduler import init_scheduler, sync_scheduler
        
        # Set up WebSocket callback for real-time sync updates
        async def sync_callback(event_type: str, data: dict):
            await manager.broadcast(event_type, data)
        
        sync_scheduler.set_websocket_callback(sync_callback)
        await init_scheduler()
        print("Sync scheduler initialized")
    except Exception as e:
        print(f"Sync scheduler not available: {e}")
    
    # Initialize document workflow WebSocket integration
    try:
        from app.services.workflow import doc_workflow
        
        async def workflow_callback(chat_id: str, event_type: str, data: dict):
            await manager.send_to_chat(chat_id, event_type, data)
        
        doc_workflow.set_emit_callback(workflow_callback)
        print("Document workflow initialized")
    except Exception as e:
        print(f"Document workflow not available: {e}")
    
    yield
    
    # Shutdown
    try:
        from app.services.scheduler import shutdown_scheduler
        await shutdown_scheduler()
    except Exception:
        pass
    
    try:
        from app.services.redis import redis_client
        await redis_client.disconnect()
    except Exception:
        pass
    
    try:
        from app.services.tasks import TaskQueue
        await TaskQueue.disconnect()
    except Exception:
        pass
    
    await close_db()




# Create FastAPI app
app = FastAPI(
    title="DocAgent API",
    description="Document Processing AI Agent API with real-time WebSocket updates",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api")
app.include_router(chats_router, prefix="/api")
app.include_router(files_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(admin_templates_router, prefix="/api")
app.include_router(connectors_router, prefix="/api")
app.include_router(preview_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")

# Mount static files for uploads (create dir if needed)
from pathlib import Path
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "connections": manager.get_total_connections(),
    }
    
    # Check Redis
    try:
        from app.services.redis import redis_client
        await redis_client.client.ping()
        health["redis"] = "connected"
    except Exception:
        health["redis"] = "disconnected"
    
    return health


@app.get("/api/stats")
async def get_stats():
    """Get system statistics."""
    return {
        "websocket_connections": manager.get_total_connections(),
        "active_chats": len(manager._chat_connections),
        "active_users": len(manager._user_connections),
    }


# Document processing endpoints
@app.post("/api/documents/analyze")
async def analyze_document(
    file_id: str,
    chat_id: str | None = None,
):
    """Analyze an uploaded document."""
    from pathlib import Path
    from app.services.document import DocumentProcessor
    from app.api.deps import CurrentUser, DB
    
    # For background processing with progress updates
    if chat_id:
        from app.services.tasks import TaskQueue
        job_id = await TaskQueue.enqueue(
            "process_document_task",
            user_id="current_user_id",  # Would get from auth
            file_path=f"placeholder/{file_id}",
            chat_id=chat_id,
        )
        return {"job_id": job_id, "status": "queued"}
    
    return {"status": "file_id required"}


@app.post("/api/documents/fill-template")
async def fill_template(
    template_id: str,
    data: dict,
    chat_id: str | None = None,
):
    """Fill a template with provided data."""
    if chat_id:
        from app.services.tasks import TaskQueue
        job_id = await TaskQueue.enqueue(
            "fill_template_task",
            user_id="current_user_id",
            template_id=template_id,
            data=data,
            chat_id=chat_id,
        )
        return {"job_id": job_id, "status": "queued"}
    
    return {"status": "processing without progress"}


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get background job status."""
    from app.services.tasks import TaskQueue
    return await TaskQueue.get_job_status(job_id)


# Extra tools endpoints
@app.get("/api/tools")
async def list_extra_tools(user_id: str = "default"):
    """List user's extra tools."""
    from app.services.extra_tools import ExtraToolsManager
    mgr = ExtraToolsManager(user_id)
    return {"tools": mgr.list_tools()}


@app.post("/api/tools")
async def create_extra_tool(
    name: str,
    code: str,
    description: str,
    user_id: str = "default",
):
    """Create a new extra tool."""
    from app.services.extra_tools import ExtraToolsManager
    mgr = ExtraToolsManager(user_id)
    path = mgr.save_tool(name, code, description)
    return {"status": "created", "path": str(path)}


@app.delete("/api/tools/{name}")
async def delete_extra_tool(name: str, user_id: str = "default"):
    """Delete an extra tool."""
    from app.services.extra_tools import ExtraToolsManager
    mgr = ExtraToolsManager(user_id)
    deleted = mgr.delete_tool(name)
    return {"deleted": deleted}


@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time updates.
    
    Connection URL: ws://host/ws/{jwt_token}
    """
    # Validate token
    payload = decode_token(token)
    if payload is None or payload.type != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    user_id = payload.sub
    
    # Connect
    await websocket.accept()

    conn_info = await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await ws_handler.handle_message(conn_info, message)
            except json.JSONDecodeError:
                await manager.send_to_connection(
                    conn_info,
                    "error",
                    {"message": "Invalid JSON"},
                )
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.websocket("/ws/chat/{chat_id}/{token}")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    chat_id: str,
    token: str,
):
    """
    WebSocket endpoint for a specific chat session.
    
    This endpoint is used for real-time agent interaction in a chat.
    """
    from app.agent.simple_agent import get_simple_agent, remove_simple_agent, generate_chat_title
    from app.database import async_session_maker
    from app.services.chat import add_message, get_chat
    
    # Validate token
    payload = decode_token(token)
    if payload is None or payload.type != "access":
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    user_id = payload.sub
    
    # Verify chat ownership
    async with async_session_maker() as db:
        chat = await get_chat(db, chat_id, user_id)
        if not chat:
            await websocket.close(code=4004, reason="Chat not found")
            return
        thread_id = chat.thread_id
    
    # Connect with chat context
    await websocket.accept()

    conn_info = await manager.connect(websocket, user_id, chat_id)
    
    try:
        # Get simple agent
        agent = await get_simple_agent(thread_id, user_id)
        
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                event_type = message.get("event")
                event_data = message.get("data", {})
                
                if event_type == "send_message":
                    # Save user message to DB
                    try:
                        async with async_session_maker() as db:
                            await add_message(
                                db,
                                chat_id=chat_id,
                                role="user",
                                content=event_data.get("content", ""),
                                attachments=event_data.get("attachments"),
                            )
                    except Exception as e:
                        print(f"Warning: Could not save user message to DB: {e}")
                    
                    # Auto-Title if needed
                    if chat.title in [None, "New Chat", "Untitled Chat", "Untitled"]:
                         import asyncio
                         # Fire and forget
                         asyncio.create_task(generate_chat_title(chat_id, event_data.get("content", ""), user_id))

                    # Process with agent and stream response
                    agent_event = None
                    async for agent_event in agent.process_message(
                        event_data.get("content", ""),
                        event_data.get("attachments"),
                    ):
                        print(f"DEBUG: Sending event: {agent_event['event']}")
                        await manager.send_to_connection(
                            conn_info,
                            agent_event["event"],
                            agent_event["data"],
                        )
                    
                    # Save assistant message to DB
                    if agent_event and agent_event["event"].value == "message_complete":
                        try:
                            async with async_session_maker() as db:
                                await add_message(
                                    db,
                                    chat_id=chat_id,
                                    role="assistant",
                                    content=agent_event["data"].get("content", ""),
                                )
                        except Exception as e:
                            print(f"Warning: Could not save assistant message to DB: {e}")
                
                elif event_type == "cancel_generation":
                    await manager.send_to_connection(
                        conn_info,
                        "generation_cancelled",
                        {"status": "cancelled"},
                    )
                
                else:
                    await ws_handler.handle_message(conn_info, message)
                    
            except json.JSONDecodeError:
                await manager.send_to_connection(
                    conn_info,
                    "error",
                    {"message": "Invalid JSON"},
                )
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        remove_simple_agent(thread_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
