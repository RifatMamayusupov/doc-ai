"""API endpoints for data source connectors."""

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DB
from app.config import settings
from app.connectors import (
    ConnectorConfig,
    ConnectorType,
    get_connector,
    registry,
)
from app.connectors.registry import list_available_connectors
from app.models.connector import Connector, SyncHistory


router = APIRouter(prefix="/connectors", tags=["connectors"])


# Pydantic schemas
class ConnectorCreate(BaseModel):
    """Schema for creating a connector."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    connector_type: str = Field(..., description="sharepoint, google_drive, s3, azure_blob, database")
    credentials: dict[str, Any] = Field(default_factory=dict)
    sync_path: str = "/"
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    schedule: str | None = None


class ConnectorUpdate(BaseModel):
    """Schema for updating a connector."""
    name: str | None = None
    description: str | None = None
    credentials: dict[str, Any] | None = None
    sync_path: str | None = None
    include_patterns: list[str] | None = None
    exclude_patterns: list[str] | None = None
    schedule: str | None = None
    is_active: bool | None = None


class ConnectorResponse(BaseModel):
    """Schema for connector response."""
    id: str
    name: str
    description: str | None
    connector_type: str
    sync_path: str
    schedule: str | None
    is_active: bool
    last_sync_at: datetime | None
    last_sync_status: str | None
    files_synced: int
    created_at: datetime


class SyncHistoryResponse(BaseModel):
    """Schema for sync history response."""
    id: str
    started_at: datetime
    completed_at: datetime | None
    status: str
    files_synced: int
    files_skipped: int
    files_failed: int
    bytes_transferred: int
    error_message: str | None


# Helper functions
def connector_to_response(connector: Connector) -> ConnectorResponse:
    """Convert connector model to response schema."""
    return ConnectorResponse(
        id=connector.id,
        name=connector.name,
        description=connector.description,
        connector_type=connector.connector_type,
        sync_path=connector.sync_path,
        schedule=connector.schedule,
        is_active=connector.is_active,
        last_sync_at=connector.last_sync_at,
        last_sync_status=connector.last_sync_status,
        files_synced=connector.files_synced,
        created_at=connector.created_at,
    )


# Endpoints
@router.get("/types")
async def list_connector_types():
    """List available connector types."""
    return {"types": list_available_connectors()}


@router.post("", response_model=ConnectorResponse)
async def create_connector(
    data: ConnectorCreate,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """Create a new data source connector."""
    # Validate connector type
    try:
        connector_type = ConnectorType(data.connector_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid connector type: {data.connector_type}",
        )
    
    # Create connector model
    connector = Connector(
        name=data.name,
        description=data.description,
        connector_type=data.connector_type,
        user_id=current_user.id,
        credentials=data.credentials,
        sync_path=data.sync_path,
        include_patterns=data.include_patterns,
        exclude_patterns=data.exclude_patterns,
        schedule=data.schedule,
    )
    
    db.add(connector)
    await db.commit()
    await db.refresh(connector)
    
    return connector_to_response(connector)


@router.get("", response_model=list[ConnectorResponse])
async def list_connectors(
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """List all connectors for the current user."""
    result = await db.execute(
        select(Connector).where(Connector.user_id == current_user.id)
    )
    connectors = result.scalars().all()
    
    return [connector_to_response(c) for c in connectors]


@router.get("/{connector_id}", response_model=ConnectorResponse)
async def get_connector_by_id(
    connector_id: str,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """Get a specific connector."""
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.user_id == current_user.id,
        )
    )
    connector = result.scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    return connector_to_response(connector)


@router.put("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: str,
    data: ConnectorUpdate,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """Update a connector."""
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.user_id == current_user.id,
        )
    )
    connector = result.scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connector, field, value)
    
    await db.commit()
    await db.refresh(connector)
    
    return connector_to_response(connector)


@router.delete("/{connector_id}")
async def delete_connector(
    connector_id: str,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """Delete a connector."""
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.user_id == current_user.id,
        )
    )
    connector = result.scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    await db.delete(connector)
    await db.commit()
    
    return {"status": "deleted", "id": connector_id}


@router.post("/{connector_id}/test")
async def test_connector(
    connector_id: str,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """Test a connector's connection."""
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.user_id == current_user.id,
        )
    )
    connector = result.scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    # Create connector instance
    config = ConnectorConfig(
        id=connector.id,
        name=connector.name,
        connector_type=ConnectorType(connector.connector_type),
        credentials=connector.credentials,
        sync_path=connector.sync_path,
    )
    
    try:
        conn = get_connector(config)
        success, message = await conn.test_connection()
        await conn.close()
        
        return {
            "success": success,
            "message": message,
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


@router.post("/{connector_id}/sync")
async def trigger_sync(
    connector_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """Trigger a manual sync for a connector."""
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.user_id == current_user.id,
        )
    )
    connector = result.scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    # Create sync history entry
    sync_history = SyncHistory(
        connector_id=connector_id,
        started_at=datetime.now(),
        status="running",
    )
    db.add(sync_history)
    await db.commit()
    await db.refresh(sync_history)
    
    # Start background sync
    background_tasks.add_task(
        run_sync,
        connector_id=connector_id,
        sync_history_id=sync_history.id,
        user_id=current_user.id,
    )
    
    return {
        "status": "started",
        "sync_id": sync_history.id,
    }


@router.get("/{connector_id}/files")
async def list_connector_files(
    connector_id: str,
    path: str = "/",
    recursive: bool = False,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """List files from a connector source."""
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.user_id == current_user.id,
        )
    )
    connector = result.scalar_one_or_none()
    
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    # Create connector instance
    config = ConnectorConfig(
        id=connector.id,
        name=connector.name,
        connector_type=ConnectorType(connector.connector_type),
        credentials=connector.credentials,
        sync_path=connector.sync_path,
    )
    
    try:
        conn = get_connector(config)
        files = await conn.list_files(path, recursive)
        await conn.close()
        
        return {
            "files": [
                {
                    "id": f.id,
                    "name": f.name,
                    "path": f.path,
                    "size": f.size,
                    "is_folder": f.is_folder,
                    "mime_type": f.mime_type,
                    "modified_at": f.modified_at.isoformat() if f.modified_at else None,
                }
                for f in files
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{connector_id}/history", response_model=list[SyncHistoryResponse])
async def get_sync_history(
    connector_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(DB),
    current_user = Depends(CurrentUser),
):
    """Get sync history for a connector."""
    # Verify connector ownership
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Connector not found")
    
    # Get history
    result = await db.execute(
        select(SyncHistory)
        .where(SyncHistory.connector_id == connector_id)
        .order_by(SyncHistory.started_at.desc())
        .limit(limit)
    )
    history = result.scalars().all()
    
    return [
        SyncHistoryResponse(
            id=h.id,
            started_at=h.started_at,
            completed_at=h.completed_at,
            status=h.status,
            files_synced=h.files_synced,
            files_skipped=h.files_skipped,
            files_failed=h.files_failed,
            bytes_transferred=h.bytes_transferred,
            error_message=h.error_message,
        )
        for h in history
    ]


# Background task for sync
async def run_sync(connector_id: str, sync_history_id: str, user_id: str):
    """Run sync in background."""
    from app.database import async_session_maker
    
    async with async_session_maker() as db:
        # Get connector
        result = await db.execute(
            select(Connector).where(Connector.id == connector_id)
        )
        connector = result.scalar_one_or_none()
        
        if not connector:
            return
        
        # Get sync history
        result = await db.execute(
            select(SyncHistory).where(SyncHistory.id == sync_history_id)
        )
        sync_history = result.scalar_one_or_none()
        
        if not sync_history:
            return
        
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
        
        try:
            conn = get_connector(config)
            
            # Create target directory
            target_dir = settings.upload_dir / "synced" / user_id / connector_id
            
            # Run sync
            result = await conn.sync_files(target_dir)
            
            # Update sync history
            sync_history.status = result.status.value
            sync_history.completed_at = result.completed_at
            sync_history.files_synced = result.files_synced
            sync_history.files_skipped = result.files_skipped
            sync_history.files_failed = result.files_failed
            sync_history.bytes_transferred = result.bytes_transferred
            sync_history.synced_files = result.synced_files[:100]  # Limit stored files
            sync_history.failed_files = result.failed_files[:50]
            
            if result.errors:
                sync_history.error_message = "\n".join(result.errors[:10])
            
            # Update connector status
            connector.last_sync_at = datetime.now()
            connector.last_sync_status = result.status.value
            connector.files_synced = result.files_synced
            
            await conn.close()
            
        except Exception as e:
            sync_history.status = "failed"
            sync_history.completed_at = datetime.now()
            sync_history.error_message = str(e)
            
            connector.last_sync_at = datetime.now()
            connector.last_sync_status = "failed"
            connector.last_sync_message = str(e)
        
        await db.commit()
