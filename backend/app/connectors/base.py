"""
Base connector abstract class and common data structures.

All data source connectors should inherit from BaseConnector.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Callable


class ConnectorType(str, Enum):
    """Supported connector types."""
    SHAREPOINT = "sharepoint"
    GOOGLE_DRIVE = "google_drive"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    DATABASE = "database"
    LOCAL = "local"


class SyncStatus(str, Enum):
    """Status of sync operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FileInfo:
    """Information about a file from data source."""
    id: str
    name: str
    path: str
    size: int
    mime_type: str | None = None
    modified_at: datetime | None = None
    created_at: datetime | None = None
    is_folder: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # For tracking sync
    checksum: str | None = None
    source_url: str | None = None


@dataclass
class ConnectorConfig:
    """Configuration for a data connector."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    connector_type: ConnectorType = ConnectorType.LOCAL
    
    # Authentication
    credentials: dict[str, Any] = field(default_factory=dict)
    
    # Sync settings
    sync_path: str = "/"  # Root path or folder to sync
    include_patterns: list[str] = field(default_factory=list)  # e.g., ["*.pdf", "*.docx"]
    exclude_patterns: list[str] = field(default_factory=list)  # e.g., ["temp/*"]
    
    # Scheduling
    schedule: str | None = None  # Cron expression
    is_active: bool = True
    
    # Organization
    organization_id: str = ""
    user_id: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_sync_at: datetime | None = None


@dataclass
class SyncResult:
    """Result of a sync operation."""
    connector_id: str
    status: SyncStatus = SyncStatus.COMPLETED
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    
    # Statistics
    files_synced: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    bytes_transferred: int = 0
    
    # Details
    synced_files: list[str] = field(default_factory=list)
    failed_files: list[dict[str, str]] = field(default_factory=list)  # [{path, error}]
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "connector_id": self.connector_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "files_synced": self.files_synced,
            "files_skipped": self.files_skipped,
            "files_failed": self.files_failed,
            "bytes_transferred": self.bytes_transferred,
            "errors": self.errors[:10],  # Limit errors in response
        }


# Type alias for progress callback
ProgressCallback = Callable[[int, int, str], None]  # (current, total, message)


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.
    
    Subclasses must implement:
    - test_connection() - Verify credentials and connectivity
    - list_files() - List files in a path
    - get_file_info() - Get metadata for a specific file
    - download_file() - Download a file to local storage
    - stream_file() - Stream file content
    
    Optional overrides:
    - sync_files() - Full sync with progress tracking (has default implementation)
    """
    
    def __init__(self, config: ConnectorConfig):
        """
        Initialize the connector.
        
        Args:
            config: Connector configuration with credentials and settings
        """
        self.config = config
        self._is_connected = False
        self._cancel_requested = False
    
    @property
    def connector_type(self) -> ConnectorType:
        """Return the connector type."""
        return self.config.connector_type
    
    @property
    def is_connected(self) -> bool:
        """Check if connector is currently connected."""
        return self._is_connected
    
    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """
        Test if the connection is valid.
        
        Returns:
            Tuple of (success, message)
        """
        pass
    
    @abstractmethod
    async def list_files(
        self,
        path: str = "/",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """
        List files and folders in a path.
        
        Args:
            path: Path to list (default: root)
            recursive: If True, list all files recursively
            
        Returns:
            List of FileInfo objects
        """
        pass
    
    @abstractmethod
    async def get_file_info(self, file_id: str) -> FileInfo | None:
        """
        Get metadata for a specific file.
        
        Args:
            file_id: File identifier (path or ID depending on connector)
            
        Returns:
            FileInfo or None if not found
        """
        pass
    
    @abstractmethod
    async def download_file(
        self,
        file_id: str,
        target_path: Path,
        on_progress: ProgressCallback | None = None,
    ) -> bool:
        """
        Download a file to local storage.
        
        Args:
            file_id: File identifier
            target_path: Local path to save the file
            on_progress: Optional progress callback
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def stream_file(
        self,
        file_id: str,
        chunk_size: int = 8192,
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream file content in chunks.
        
        Args:
            file_id: File identifier
            chunk_size: Size of each chunk in bytes
            
        Yields:
            File content chunks
        """
        pass
    
    async def sync_files(
        self,
        target_dir: Path,
        on_progress: ProgressCallback | None = None,
    ) -> SyncResult:
        """
        Sync all files from source to local storage.
        
        This default implementation can be overridden for connector-specific
        optimizations (e.g., delta sync, parallel downloads).
        
        Args:
            target_dir: Local directory to sync files to
            on_progress: Optional progress callback
            
        Returns:
            SyncResult with statistics
        """
        result = SyncResult(connector_id=self.config.id)
        result.started_at = datetime.now()
        result.status = SyncStatus.RUNNING
        
        try:
            # Ensure target directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # List all files
            files = await self.list_files(
                path=self.config.sync_path,
                recursive=True,
            )
            
            # Filter files based on patterns
            files_to_sync = self._filter_files(files)
            total_files = len(files_to_sync)
            
            for i, file_info in enumerate(files_to_sync):
                if self._cancel_requested:
                    result.status = SyncStatus.CANCELLED
                    break
                
                try:
                    # Calculate target path
                    relative_path = file_info.path.lstrip("/")
                    target_path = target_dir / relative_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Check if file needs updating
                    if self._should_sync_file(file_info, target_path):
                        # Download file
                        success = await self.download_file(
                            file_id=file_info.id,
                            target_path=target_path,
                        )
                        
                        if success:
                            result.files_synced += 1
                            result.bytes_transferred += file_info.size
                            result.synced_files.append(str(target_path))
                        else:
                            result.files_failed += 1
                            result.failed_files.append({
                                "path": file_info.path,
                                "error": "Download failed",
                            })
                    else:
                        result.files_skipped += 1
                    
                    # Report progress
                    if on_progress:
                        on_progress(i + 1, total_files, f"Syncing: {file_info.name}")
                        
                except Exception as e:
                    result.files_failed += 1
                    result.failed_files.append({
                        "path": file_info.path,
                        "error": str(e),
                    })
            
            if result.status == SyncStatus.RUNNING:
                result.status = SyncStatus.COMPLETED
                
        except Exception as e:
            result.status = SyncStatus.FAILED
            result.errors.append(str(e))
        
        result.completed_at = datetime.now()
        return result
    
    def _filter_files(self, files: list[FileInfo]) -> list[FileInfo]:
        """Filter files based on include/exclude patterns."""
        import fnmatch
        
        result = []
        for file_info in files:
            if file_info.is_folder:
                continue
            
            # Check exclude patterns
            excluded = False
            for pattern in self.config.exclude_patterns:
                if fnmatch.fnmatch(file_info.path, pattern):
                    excluded = True
                    break
            
            if excluded:
                continue
            
            # Check include patterns (if specified)
            if self.config.include_patterns:
                included = False
                for pattern in self.config.include_patterns:
                    if fnmatch.fnmatch(file_info.name, pattern):
                        included = True
                        break
                if not included:
                    continue
            
            result.append(file_info)
        
        return result
    
    def _should_sync_file(self, file_info: FileInfo, target_path: Path) -> bool:
        """Check if file should be synced (doesn't exist or modified)."""
        if not target_path.exists():
            return True
        
        # Check modification time if available
        if file_info.modified_at:
            local_mtime = datetime.fromtimestamp(target_path.stat().st_mtime)
            if file_info.modified_at > local_mtime:
                return True
        
        # Check size
        if target_path.stat().st_size != file_info.size:
            return True
        
        return False
    
    def cancel_sync(self):
        """Request cancellation of ongoing sync."""
        self._cancel_requested = True
    
    async def close(self):
        """Close the connector and release resources."""
        self._is_connected = False
