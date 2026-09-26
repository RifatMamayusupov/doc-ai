"""
AWS S3 and Azure Blob Storage Connector.

Provides integration with cloud object storage services.

For AWS S3:
- access_key_id: AWS Access Key ID
- secret_access_key: AWS Secret Access Key
- region: AWS Region (default: us-east-1)
- bucket: S3 Bucket name

For Azure Blob:
- connection_string: Azure Storage connection string
OR
- account_name: Storage account name
- account_key: Storage account key
- container: Container name
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
import aiohttp

from .base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorType,
    FileInfo,
    ProgressCallback,
    SyncResult,
)
from .registry import register_connector


@register_connector(ConnectorType.S3)
class S3Connector(BaseConnector):
    """
    Connector for AWS S3.
    
    Uses boto3 for S3 operations with async wrapper.
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None
        self._bucket = config.credentials.get("bucket", "")
    
    async def _ensure_client(self):
        """Ensure we have an S3 client."""
        if self._client is None:
            try:
                import aiobotocore.session
                
                session = aiobotocore.session.get_session()
                self._client = await session.create_client(
                    "s3",
                    region_name=self.config.credentials.get("region", "us-east-1"),
                    aws_access_key_id=self.config.credentials.get("access_key_id"),
                    aws_secret_access_key=self.config.credentials.get("secret_access_key"),
                ).__aenter__()
                
            except ImportError:
                # Fallback to sync boto3
                import boto3
                
                self._client = boto3.client(
                    "s3",
                    region_name=self.config.credentials.get("region", "us-east-1"),
                    aws_access_key_id=self.config.credentials.get("access_key_id"),
                    aws_secret_access_key=self.config.credentials.get("secret_access_key"),
                )
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test the S3 connection."""
        try:
            await self._ensure_client()
            
            # Try to head the bucket
            if hasattr(self._client, "head_bucket"):
                await self._client.head_bucket(Bucket=self._bucket)
            else:
                self._client.head_bucket(Bucket=self._bucket)
            
            self._is_connected = True
            return True, f"Connected to S3 bucket: {self._bucket}"
            
        except Exception as e:
            self._is_connected = False
            return False, f"Connection failed: {str(e)}"
    
    async def list_files(
        self,
        path: str = "/",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """List files in S3 bucket."""
        await self._ensure_client()
        
        prefix = path.strip("/")
        if prefix:
            prefix += "/"
        
        files = []
        continuation_token = None
        
        while True:
            params = {
                "Bucket": self._bucket,
                "Prefix": prefix,
            }
            
            if not recursive:
                params["Delimiter"] = "/"
            
            if continuation_token:
                params["ContinuationToken"] = continuation_token
            
            # Handle async vs sync client
            if hasattr(self._client, "list_objects_v2"):
                if asyncio.iscoroutinefunction(self._client.list_objects_v2):
                    result = await self._client.list_objects_v2(**params)
                else:
                    result = self._client.list_objects_v2(**params)
            
            # Process files
            for obj in result.get("Contents", []):
                key = obj["Key"]
                if key == prefix:  # Skip the prefix itself
                    continue
                
                files.append(FileInfo(
                    id=key,
                    name=key.split("/")[-1],
                    path=key,
                    size=obj.get("Size", 0),
                    modified_at=obj.get("LastModified"),
                    checksum=obj.get("ETag", "").strip('"'),
                    metadata={
                        "storage_class": obj.get("StorageClass"),
                    },
                ))
            
            # Process common prefixes (folders)
            for prefix_obj in result.get("CommonPrefixes", []):
                folder_path = prefix_obj["Prefix"].rstrip("/")
                files.append(FileInfo(
                    id=folder_path,
                    name=folder_path.split("/")[-1],
                    path=folder_path,
                    size=0,
                    is_folder=True,
                ))
            
            # Check for more results
            if result.get("IsTruncated"):
                continuation_token = result.get("NextContinuationToken")
            else:
                break
        
        return files
    
    async def get_file_info(self, file_id: str) -> FileInfo | None:
        """Get info for a specific file."""
        try:
            await self._ensure_client()
            
            if asyncio.iscoroutinefunction(self._client.head_object):
                result = await self._client.head_object(Bucket=self._bucket, Key=file_id)
            else:
                result = self._client.head_object(Bucket=self._bucket, Key=file_id)
            
            return FileInfo(
                id=file_id,
                name=file_id.split("/")[-1],
                path=file_id,
                size=result.get("ContentLength", 0),
                mime_type=result.get("ContentType"),
                modified_at=result.get("LastModified"),
                checksum=result.get("ETag", "").strip('"'),
            )
            
        except Exception:
            return None
    
    async def download_file(
        self,
        file_id: str,
        target_path: Path,
        on_progress: ProgressCallback | None = None,
    ) -> bool:
        """Download a file from S3."""
        try:
            await self._ensure_client()
            
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get file size for progress
            file_info = await self.get_file_info(file_id)
            total_size = file_info.size if file_info else 0
            
            if asyncio.iscoroutinefunction(self._client.get_object):
                response = await self._client.get_object(Bucket=self._bucket, Key=file_id)
                body = response["Body"]
                
                downloaded = 0
                with open(target_path, "wb") as f:
                    async for chunk in body.iter_chunks():
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if on_progress and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            on_progress(progress, 100, f"Downloading: {file_id}")
            else:
                # Sync fallback
                self._client.download_file(self._bucket, file_id, str(target_path))
            
            return True
            
        except Exception as e:
            print(f"S3 download error: {e}")
            return False
    
    async def stream_file(
        self,
        file_id: str,
        chunk_size: int = 8192,
    ) -> AsyncGenerator[bytes, None]:
        """Stream file content from S3."""
        await self._ensure_client()
        
        if asyncio.iscoroutinefunction(self._client.get_object):
            response = await self._client.get_object(Bucket=self._bucket, Key=file_id)
            body = response["Body"]
            
            async for chunk in body.iter_chunks(chunk_size=chunk_size):
                yield chunk
        else:
            # Sync fallback - read entire file
            response = self._client.get_object(Bucket=self._bucket, Key=file_id)
            body = response["Body"]
            
            while True:
                chunk = body.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    async def close(self):
        """Close the connector."""
        if self._client and hasattr(self._client, "__aexit__"):
            await self._client.__aexit__(None, None, None)
        
        self._client = None
        self._is_connected = False


@register_connector(ConnectorType.AZURE_BLOB)
class AzureBlobConnector(BaseConnector):
    """
    Connector for Azure Blob Storage.
    
    Uses azure-storage-blob for blob operations.
    """
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None
        self._container = config.credentials.get("container", "")
    
    async def _ensure_client(self):
        """Ensure we have a blob service client."""
        if self._client is None:
            try:
                from azure.storage.blob.aio import BlobServiceClient
                
                connection_string = self.config.credentials.get("connection_string")
                
                if connection_string:
                    self._client = BlobServiceClient.from_connection_string(connection_string)
                else:
                    account_name = self.config.credentials.get("account_name")
                    account_key = self.config.credentials.get("account_key")
                    
                    account_url = f"https://{account_name}.blob.core.windows.net"
                    self._client = BlobServiceClient(
                        account_url=account_url,
                        credential=account_key,
                    )
                    
            except ImportError:
                raise ImportError("azure-storage-blob library required for Azure Blob connector")
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test the Azure Blob connection."""
        try:
            await self._ensure_client()
            
            container_client = self._client.get_container_client(self._container)
            
            # Check if container exists
            exists = await container_client.exists()
            if not exists:
                return False, f"Container does not exist: {self._container}"
            
            self._is_connected = True
            return True, f"Connected to Azure container: {self._container}"
            
        except Exception as e:
            self._is_connected = False
            return False, f"Connection failed: {str(e)}"
    
    async def list_files(
        self,
        path: str = "/",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """List blobs in Azure container."""
        await self._ensure_client()
        
        container_client = self._client.get_container_client(self._container)
        
        prefix = path.strip("/")
        if prefix:
            prefix += "/"
        
        files = []
        
        if recursive:
            async for blob in container_client.list_blobs(name_starts_with=prefix):
                files.append(self._parse_blob(blob))
        else:
            async for blob in container_client.walk_blobs(name_starts_with=prefix):
                if hasattr(blob, "name"):
                    files.append(self._parse_blob(blob))
                else:
                    # It's a prefix (folder)
                    folder_name = blob.prefix.rstrip("/")
                    files.append(FileInfo(
                        id=folder_name,
                        name=folder_name.split("/")[-1],
                        path=folder_name,
                        size=0,
                        is_folder=True,
                    ))
        
        return files
    
    def _parse_blob(self, blob) -> FileInfo:
        """Parse Azure blob to FileInfo."""
        return FileInfo(
            id=blob.name,
            name=blob.name.split("/")[-1],
            path=blob.name,
            size=blob.size or 0,
            mime_type=blob.content_settings.content_type if blob.content_settings else None,
            modified_at=blob.last_modified,
            created_at=blob.creation_time,
            checksum=blob.etag.strip('"') if blob.etag else None,
            metadata={
                "blob_type": blob.blob_type,
                "access_tier": blob.blob_tier,
            },
        )
    
    async def get_file_info(self, file_id: str) -> FileInfo | None:
        """Get info for a specific blob."""
        try:
            await self._ensure_client()
            
            blob_client = self._client.get_blob_client(self._container, file_id)
            props = await blob_client.get_blob_properties()
            
            return FileInfo(
                id=file_id,
                name=file_id.split("/")[-1],
                path=file_id,
                size=props.size,
                mime_type=props.content_settings.content_type,
                modified_at=props.last_modified,
                created_at=props.creation_time,
                checksum=props.etag.strip('"') if props.etag else None,
            )
            
        except Exception:
            return None
    
    async def download_file(
        self,
        file_id: str,
        target_path: Path,
        on_progress: ProgressCallback | None = None,
    ) -> bool:
        """Download a blob from Azure."""
        try:
            await self._ensure_client()
            
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            blob_client = self._client.get_blob_client(self._container, file_id)
            
            # Get size for progress
            props = await blob_client.get_blob_properties()
            total_size = props.size
            
            downloaded = 0
            with open(target_path, "wb") as f:
                stream = await blob_client.download_blob()
                async for chunk in stream.chunks():
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if on_progress and total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        on_progress(progress, 100, f"Downloading: {file_id}")
            
            return True
            
        except Exception as e:
            print(f"Azure download error: {e}")
            return False
    
    async def stream_file(
        self,
        file_id: str,
        chunk_size: int = 8192,
    ) -> AsyncGenerator[bytes, None]:
        """Stream blob content from Azure."""
        await self._ensure_client()
        
        blob_client = self._client.get_blob_client(self._container, file_id)
        stream = await blob_client.download_blob()
        
        async for chunk in stream.chunks():
            yield chunk
    
    async def close(self):
        """Close the connector."""
        if self._client:
            await self._client.close()
        
        self._client = None
        self._is_connected = False
