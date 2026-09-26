"""Connector model for storing connector configurations."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, Boolean, Integer, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Connector(Base):
    """Data source connector configuration."""

    __tablename__ = "connectors"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Connector type
    connector_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # sharepoint, google_drive, s3, azure_blob, database
    
    # Organization/User
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Credentials (encrypted in production)
    credentials: Mapped[dict[str, Any]] = mapped_column(JSON, default={})
    
    # Sync configuration
    sync_path: Mapped[str] = mapped_column(String(500), default="/")
    include_patterns: Mapped[list[str] | None] = mapped_column(JSON, default=[])
    exclude_patterns: Mapped[list[str] | None] = mapped_column(JSON, default=[])
    
    # Scheduling
    schedule: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Cron expression
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Status
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_sync_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_synced: Mapped[int] = mapped_column(default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Connector {self.name} ({self.connector_type})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary (without sensitive credentials)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "connector_type": self.connector_type,
            "organization_id": self.organization_id,
            "sync_path": self.sync_path,
            "schedule": self.schedule,
            "is_active": self.is_active,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "files_synced": self.files_synced,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SyncHistory(Base):
    """History of sync operations."""

    __tablename__ = "sync_history"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # running, completed, failed, cancelled
    
    # Statistics
    files_synced: Mapped[int] = mapped_column(default=0)
    files_skipped: Mapped[int] = mapped_column(default=0)
    files_failed: Mapped[int] = mapped_column(default=0)
    bytes_transferred: Mapped[int] = mapped_column(default=0)
    
    # Details
    synced_files: Mapped[list[str] | None] = mapped_column(JSON, default=[])
    failed_files: Mapped[list[dict] | None] = mapped_column(JSON, default=[])
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SyncHistory {self.connector_id} - {self.status}>"
