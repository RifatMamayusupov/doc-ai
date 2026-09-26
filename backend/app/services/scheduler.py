"""
Scheduled Sync Service - Automated connector synchronization.

Uses APScheduler for background task scheduling with cron expressions.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Callable, Any
from dataclasses import dataclass, field

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    AsyncIOScheduler = None

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import ConnectorConfig, ConnectorType, get_connector
from app.config import settings


@dataclass
class ScheduledJob:
    """Represents a scheduled sync job."""
    job_id: str
    connector_id: str
    connector_name: str
    schedule: str  # Cron expression or interval
    next_run: datetime | None = None
    last_run: datetime | None = None
    status: str = "scheduled"  # scheduled, running, paused
    error_count: int = 0


class SyncScheduler:
    """
    Manages scheduled synchronization jobs for connectors.
    
    Supports:
    - Cron expressions for complex schedules
    - Interval-based schedules (e.g., every 5 minutes)
    - Real-time status updates via WebSocket
    """
    
    def __init__(self):
        self._scheduler: AsyncIOScheduler | None = None
        self._jobs: dict[str, ScheduledJob] = {}
        self._ws_callback: Callable | None = None
        self._running = False
    
    def set_websocket_callback(self, callback: Callable):
        """Set callback for real-time WebSocket updates."""
        self._ws_callback = callback
    
    async def start(self):
        """Start the scheduler."""
        if not HAS_APSCHEDULER:
            print("WARNING: APScheduler not installed. Scheduled syncs disabled.")
            return
        
        if self._scheduler is not None:
            return
        
        self._scheduler = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 60,
            },
        )
        
        self._scheduler.start()
        self._running = True
        print("Sync scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        self._running = False
        print("Sync scheduler stopped")
    
    async def add_sync_job(
        self,
        connector_id: str,
        connector_name: str,
        schedule: str,
        user_id: str,
    ) -> ScheduledJob:
        """
        Add a new sync job.
        
        Args:
            connector_id: ID of the connector
            connector_name: Display name
            schedule: Cron expression or interval (e.g., "*/5 * * * *" or "5m")
            user_id: Owner user ID
            
        Returns:
            ScheduledJob instance
        """
        job_id = f"sync_{connector_id}"
        
        # Parse schedule
        trigger = self._parse_schedule(schedule)
        
        if self._scheduler and trigger:
            self._scheduler.add_job(
                self._run_sync,
                trigger=trigger,
                id=job_id,
                args=[connector_id, user_id],
                replace_existing=True,
            )
            
            # Get next run time
            job = self._scheduler.get_job(job_id)
            next_run = job.next_run_time if job else None
        else:
            next_run = None
        
        scheduled_job = ScheduledJob(
            job_id=job_id,
            connector_id=connector_id,
            connector_name=connector_name,
            schedule=schedule,
            next_run=next_run,
        )
        
        self._jobs[job_id] = scheduled_job
        
        # Notify via WebSocket
        await self._notify("sync_job_added", {
            "job_id": job_id,
            "connector_id": connector_id,
            "schedule": schedule,
            "next_run": next_run.isoformat() if next_run else None,
        })
        
        return scheduled_job
    
    async def remove_sync_job(self, connector_id: str):
        """Remove a sync job."""
        job_id = f"sync_{connector_id}"
        
        if self._scheduler:
            try:
                self._scheduler.remove_job(job_id)
            except Exception:
                pass
        
        if job_id in self._jobs:
            del self._jobs[job_id]
        
        await self._notify("sync_job_removed", {"connector_id": connector_id})
    
    async def pause_sync_job(self, connector_id: str):
        """Pause a sync job."""
        job_id = f"sync_{connector_id}"
        
        if self._scheduler:
            self._scheduler.pause_job(job_id)
        
        if job_id in self._jobs:
            self._jobs[job_id].status = "paused"
        
        await self._notify("sync_job_paused", {"connector_id": connector_id})
    
    async def resume_sync_job(self, connector_id: str):
        """Resume a paused sync job."""
        job_id = f"sync_{connector_id}"
        
        if self._scheduler:
            self._scheduler.resume_job(job_id)
        
        if job_id in self._jobs:
            self._jobs[job_id].status = "scheduled"
        
        await self._notify("sync_job_resumed", {"connector_id": connector_id})
    
    async def trigger_sync_now(self, connector_id: str, user_id: str):
        """Trigger immediate sync (outside schedule)."""
        await self._run_sync(connector_id, user_id)
    
    def get_jobs(self) -> list[ScheduledJob]:
        """Get all scheduled jobs."""
        # Update next run times
        if self._scheduler:
            for job_id, scheduled_job in self._jobs.items():
                job = self._scheduler.get_job(job_id)
                if job:
                    scheduled_job.next_run = job.next_run_time
        
        return list(self._jobs.values())
    
    def get_job(self, connector_id: str) -> ScheduledJob | None:
        """Get a specific job."""
        return self._jobs.get(f"sync_{connector_id}")
    
    def _parse_schedule(self, schedule: str):
        """Parse schedule string into APScheduler trigger."""
        if not HAS_APSCHEDULER:
            return None
        
        # Check for interval format (e.g., "5m", "1h", "30s")
        if schedule.endswith("s"):
            try:
                seconds = int(schedule[:-1])
                return IntervalTrigger(seconds=seconds)
            except ValueError:
                pass
        elif schedule.endswith("m"):
            try:
                minutes = int(schedule[:-1])
                return IntervalTrigger(minutes=minutes)
            except ValueError:
                pass
        elif schedule.endswith("h"):
            try:
                hours = int(schedule[:-1])
                return IntervalTrigger(hours=hours)
            except ValueError:
                pass
        
        # Try as cron expression
        try:
            parts = schedule.split()
            if len(parts) == 5:
                return CronTrigger.from_crontab(schedule)
        except Exception:
            pass
        
        # Default: every hour
        return IntervalTrigger(hours=1)
    
    async def _run_sync(self, connector_id: str, user_id: str):
        """Execute sync for a connector."""
        job_id = f"sync_{connector_id}"
        job = self._jobs.get(job_id)
        
        if job:
            job.status = "running"
            job.last_run = datetime.now()
        
        # Notify start
        await self._notify("sync_started", {
            "connector_id": connector_id,
            "started_at": datetime.now().isoformat(),
        })
        
        try:
            from app.database import async_session_maker
            from app.models.connector import Connector, SyncHistory
            
            async with async_session_maker() as db:
                # Get connector
                result = await db.execute(
                    select(Connector).where(Connector.id == connector_id)
                )
                connector = result.scalar_one_or_none()
                
                if not connector:
                    raise ValueError(f"Connector not found: {connector_id}")
                
                # Create sync history
                sync_history = SyncHistory(
                    connector_id=connector_id,
                    started_at=datetime.now(),
                    status="running",
                )
                db.add(sync_history)
                await db.commit()
                await db.refresh(sync_history)
                
                # Create connector instance
                config = ConnectorConfig(
                    id=connector.id,
                    name=connector.name,
                    connector_type=ConnectorType(connector.connector_type),
                    credentials=connector.credentials,
                    sync_path=connector.sync_path,
                    include_patterns=connector.include_patterns or [],
                    exclude_patterns=connector.exclude_patterns or [],
                )
                
                conn = get_connector(config)
                
                # Run sync with progress callback
                target_dir = settings.upload_dir / "synced" / user_id / connector_id
                
                async def progress_callback(current: int, total: int, filename: str):
                    await self._notify("sync_progress", {
                        "connector_id": connector_id,
                        "current": current,
                        "total": total,
                        "filename": filename,
                        "percent": round(current / total * 100) if total > 0 else 0,
                    })
                
                # Perform sync
                result = await conn.sync_files(target_dir, on_progress=progress_callback)
                
                # Update sync history
                sync_history.status = result.status.value
                sync_history.completed_at = result.completed_at
                sync_history.files_synced = result.files_synced
                sync_history.files_skipped = result.files_skipped
                sync_history.files_failed = result.files_failed
                sync_history.bytes_transferred = result.bytes_transferred
                sync_history.synced_files = result.synced_files[:100]
                sync_history.failed_files = result.failed_files[:50]
                
                if result.errors:
                    sync_history.error_message = "\n".join(result.errors[:10])
                
                # Update connector
                connector.last_sync_at = datetime.now()
                connector.last_sync_status = result.status.value
                connector.files_synced = result.files_synced
                
                await db.commit()
                await conn.close()
                
                # Notify completion
                await self._notify("sync_completed", {
                    "connector_id": connector_id,
                    "status": result.status.value,
                    "files_synced": result.files_synced,
                    "files_failed": result.files_failed,
                    "completed_at": datetime.now().isoformat(),
                })
                
                if job:
                    job.status = "scheduled"
                    job.error_count = 0
                
        except Exception as e:
            # Notify error
            await self._notify("sync_error", {
                "connector_id": connector_id,
                "error": str(e),
            })
            
            if job:
                job.status = "scheduled"
                job.error_count = job.error_count + 1
    
    async def _notify(self, event_type: str, data: dict):
        """Send WebSocket notification."""
        if self._ws_callback:
            try:
                await self._ws_callback(event_type, data)
            except Exception as e:
                print(f"WebSocket notification error: {e}")


# Global scheduler instance
sync_scheduler = SyncScheduler()


async def init_scheduler():
    """Initialize the sync scheduler on app startup."""
    await sync_scheduler.start()
    
    # Load existing scheduled jobs from database
    try:
        from app.database import async_session_maker
        from app.models.connector import Connector
        
        async with async_session_maker() as db:
            result = await db.execute(
                select(Connector).where(
                    Connector.is_active == True,
                    Connector.schedule.isnot(None),
                )
            )
            connectors = result.scalars().all()
            
            for connector in connectors:
                await sync_scheduler.add_sync_job(
                    connector_id=connector.id,
                    connector_name=connector.name,
                    schedule=connector.schedule,
                    user_id=connector.user_id,
                )
            
            print(f"Loaded {len(connectors)} scheduled sync jobs")
    except Exception as e:
        print(f"Error loading scheduled jobs: {e}")


async def shutdown_scheduler():
    """Shutdown the sync scheduler on app shutdown."""
    await sync_scheduler.stop()
