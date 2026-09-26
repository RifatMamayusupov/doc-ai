"""Background task queue using ARQ (async Redis queue)."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import settings


class TaskQueue:
    """
    Background task queue for heavy processing.
    
    Uses ARQ for async Redis-based task queue.
    Suitable for:
    - Document processing
    - PDF generation
    - Email sending
    - Report generation
    """

    _pool: ArqRedis | None = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize ARQ connection pool."""
        if cls._pool is not None:
            return

        # Parse Redis URL
        # Format: redis://user:pass@host:port/db
        url = settings.redis_url
        if url.startswith("redis://"):
            url = url[8:]

        host = "localhost"
        port = 6379
        password = None

        if "@" in url:
            auth, url = url.split("@")
            if ":" in auth:
                _, password = auth.split(":")
        if "/" in url:
            url, _ = url.split("/")
        if ":" in url:
            host, port = url.split(":")
            port = int(port)

        cls._pool = await create_pool(
            RedisSettings(
                host=host,
                port=port,
                password=password,
            )
        )

    @classmethod
    async def disconnect(cls) -> None:
        """Close ARQ pool."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None

    @classmethod
    async def enqueue(
        cls,
        func_name: str,
        *args,
        _defer_by: timedelta | None = None,
        _job_id: str | None = None,
        **kwargs,
    ) -> str:
        """
        Enqueue a task for background execution.
        
        Args:
            func_name: Name of the worker function to call
            *args: Positional arguments for the function
            _defer_by: Optional delay before execution
            _job_id: Optional custom job ID
            **kwargs: Keyword arguments for the function
            
        Returns:
            Job ID
        """
        if cls._pool is None:
            await cls.connect()

        job = await cls._pool.enqueue_job(
            func_name,
            *args,
            _defer_by=_defer_by,
            _job_id=_job_id,
            **kwargs,
        )
        return job.job_id

    @classmethod
    async def get_job_status(cls, job_id: str) -> dict[str, Any]:
        """Get status of a queued job."""
        if cls._pool is None:
            await cls.connect()

        job = await cls._pool.job(job_id)
        if job is None:
            return {"status": "not_found", "job_id": job_id}

        info = await job.info()
        return {
            "job_id": job_id,
            "status": info.status if info else "unknown",
            "result": info.result if info else None,
        }


# Worker functions (to be run by ARQ worker process)
async def process_document_task(
    ctx: dict,
    user_id: str,
    file_path: str,
    chat_id: str,
) -> dict:
    """
    Background task to process a document.
    
    Args:
        ctx: ARQ context
        user_id: User ID
        file_path: Path to the document
        chat_id: Chat ID for progress updates
    """
    from pathlib import Path
    from app.services.document import DocumentProcessor
    from app.websocket.manager import manager
    from app.schemas.websocket import WSEventType

    processor = DocumentProcessor(user_id)

    async def on_progress(progress: int, message: str):
        await manager.broadcast_to_chat(
            chat_id,
            WSEventType.PROCESS_STATUS,
            {
                "type": "document",
                "status": "processing",
                "progress": progress,
                "message": message,
            },
        )

    result = await processor.analyze_document(Path(file_path), on_progress)

    await manager.broadcast_to_chat(
        chat_id,
        WSEventType.PROCESS_STATUS,
        {
            "type": "document",
            "status": "complete",
            "progress": 100,
            "message": "Processing complete",
        },
    )

    return result


async def fill_template_task(
    ctx: dict,
    user_id: str,
    template_id: str,
    data: dict,
    chat_id: str,
) -> str:
    """
    Background task to fill a template.
    
    Returns:
        Path to filled document
    """
    from app.services.document import TemplateProcessor
    from app.websocket.manager import manager
    from app.schemas.websocket import WSEventType

    processor = TemplateProcessor()

    async def on_progress(progress: int, message: str):
        await manager.broadcast_to_chat(
            chat_id,
            WSEventType.PROCESS_STATUS,
            {
                "type": "template",
                "status": "processing",
                "progress": progress,
                "message": message,
            },
        )

    output_path = await processor.fill_template(template_id, data, on_progress)

    await manager.broadcast_to_chat(
        chat_id,
        WSEventType.PROCESS_STATUS,
        {
            "type": "template",
            "status": "complete",
            "progress": 100,
            "message": "Template filled",
            "preview_url": f"/uploads/output/{output_path.name}",
        },
    )

    return str(output_path)


async def execute_code_task(
    ctx: dict,
    user_id: str,
    code: str,
    chat_id: str,
) -> dict:
    """
    Background task to execute code.
    """
    from app.services.extra_tools import CodeExecutor
    from app.websocket.manager import manager
    from app.schemas.websocket import WSEventType

    executor = CodeExecutor(user_id)

    async def on_output(line: str):
        await manager.broadcast_to_chat(
            chat_id,
            WSEventType.CODE_EXECUTE_OUTPUT,
            {"output": line},
        )

    result = await executor.execute(code, on_output=on_output)

    await manager.broadcast_to_chat(
        chat_id,
        WSEventType.CODE_EXECUTE_COMPLETE,
        {
            "status": "success" if result["success"] else "error",
            "output": result["stdout"] or result["stderr"],
        },
    )

    return result


# ARQ worker configuration
class WorkerSettings:
    """Settings for ARQ worker."""

    functions = [
        process_document_task,
        fill_template_task,
        execute_code_task,
    ]

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Worker startup hook."""
        from app.database import init_db
        await init_db()

    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Worker shutdown hook."""
        from app.database import close_db
        await close_db()
