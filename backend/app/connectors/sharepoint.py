"""
SharePoint / Office 365 Connector.

Provides integration with Microsoft SharePoint and OneDrive for Business
using Microsoft Graph API.

Required credentials in config:
- client_id: Azure AD App Registration client ID
- client_secret: Azure AD App Registration client secret
- tenant_id: Azure AD tenant ID
- site_url: SharePoint site URL (optional, for specific site)
"""

import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
import json

from .base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorType,
    FileInfo,
    ProgressCallback,
    SyncResult,
)
from .registry import register_connector


@register_connector(ConnectorType.SHAREPOINT)
class SharePointConnector(BaseConnector):
    """
    Connector for Microsoft SharePoint / OneDrive for Business.
    
    Uses Microsoft Graph API for authentication and file operations.
    Supports:
    - SharePoint Document Libraries
    - OneDrive for Business
    - Microsoft 365 Groups
    """
    
    GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"
    AUTH_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._session: aiohttp.ClientSession | None = None
        self._site_id: str | None = None
        self._drive_id: str | None = None
    
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def _get_access_token(self) -> str:
        """
        Get or refresh the access token.
        
        Uses client credentials flow for app-only authentication.
        """
        # Check if current token is still valid
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        await self._ensure_session()
        
        tenant_id = self.config.credentials.get("tenant_id")
        client_id = self.config.credentials.get("client_id")
        client_secret = self.config.credentials.get("client_secret")
        
        if not all([tenant_id, client_id, client_secret]):
            raise ValueError("Missing SharePoint credentials: tenant_id, client_id, client_secret required")
        
        auth_url = self.AUTH_URL.format(tenant_id=tenant_id)
        
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        
        async with self._session.post(auth_url, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Authentication failed: {error_text}")
            
            result = await response.json()
            self._access_token = result["access_token"]
            expires_in = result.get("expires_in", 3600)
            self._token_expires_at = datetime.now().replace(
                second=datetime.now().second + expires_in - 60  # 1 min buffer
            )
            
            return self._access_token
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict | bytes:
        """
        Make an authenticated API request to Microsoft Graph.
        
        Args:
            method: HTTP method
            endpoint: API endpoint (relative to GRAPH_API_BASE)
            **kwargs: Additional arguments for aiohttp request
            
        Returns:
            JSON response or bytes for file downloads
        """
        await self._ensure_session()
        token = await self._get_access_token()
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        url = f"{self.GRAPH_API_BASE}{endpoint}"
        
        async with self._session.request(method, url, headers=headers, **kwargs) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise Exception(f"API request failed ({response.status}): {error_text}")
            
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return await response.json()
            else:
                return await response.read()
    
    async def _get_site_and_drive(self):
        """Get site ID and default drive ID."""
        if self._site_id and self._drive_id:
            return
        
        site_url = self.config.credentials.get("site_url")
        
        if site_url:
            # Parse site URL to get site ID
            # Format: https://tenant.sharepoint.com/sites/sitename
            hostname = site_url.split("//")[1].split("/")[0]
            site_path = "/".join(site_url.split("//")[1].split("/")[1:])
            
            result = await self._api_request(
                "GET",
                f"/sites/{hostname}:/{site_path}",
            )
            self._site_id = result["id"]
            
            # Get default document library
            drives = await self._api_request(
                "GET",
                f"/sites/{self._site_id}/drives",
            )
            if drives.get("value"):
                self._drive_id = drives["value"][0]["id"]
        else:
            # Use user's OneDrive (for delegated auth)
            # For app-only, this requires additional setup
            result = await self._api_request("GET", "/me/drive")
            self._drive_id = result["id"]
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test the SharePoint connection."""
        try:
            await self._get_access_token()
            await self._get_site_and_drive()
            
            # Try to list root folder
            await self._api_request(
                "GET",
                f"/drives/{self._drive_id}/root/children?$top=1",
            )
            
            self._is_connected = True
            return True, "Successfully connected to SharePoint"
            
        except Exception as e:
            self._is_connected = False
            return False, f"Connection failed: {str(e)}"
    
    async def list_files(
        self,
        path: str = "/",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """List files in SharePoint folder."""
        await self._get_site_and_drive()
        
        files = []
        await self._list_files_recursive(path, files, recursive)
        return files
    
    async def _list_files_recursive(
        self,
        path: str,
        files: list[FileInfo],
        recursive: bool,
    ):
        """Recursively list files in a folder."""
        # Build endpoint
        if path == "/" or path == "":
            endpoint = f"/drives/{self._drive_id}/root/children"
        else:
            # URL encode the path
            encoded_path = path.replace("/", ":/").rstrip(":/")
            endpoint = f"/drives/{self._drive_id}/root:/{encoded_path}:/children"
        
        # Handle pagination
        while endpoint:
            result = await self._api_request("GET", endpoint)
            
            for item in result.get("value", []):
                file_info = self._parse_drive_item(item, path)
                files.append(file_info)
                
                # Recurse into folders
                if recursive and file_info.is_folder:
                    await self._list_files_recursive(
                        f"{path}/{file_info.name}".lstrip("/"),
                        files,
                        recursive,
                    )
            
            # Check for next page
            next_link = result.get("@odata.nextLink")
            if next_link:
                # Extract just the path part
                endpoint = next_link.replace(self.GRAPH_API_BASE, "")
            else:
                endpoint = None
    
    def _parse_drive_item(self, item: dict, parent_path: str) -> FileInfo:
        """Parse Graph API drive item to FileInfo."""
        name = item["name"]
        item_path = f"{parent_path}/{name}".lstrip("/")
        
        # Parse dates
        modified_at = None
        created_at = None
        if "lastModifiedDateTime" in item:
            modified_at = datetime.fromisoformat(
                item["lastModifiedDateTime"].replace("Z", "+00:00")
            )
        if "createdDateTime" in item:
            created_at = datetime.fromisoformat(
                item["createdDateTime"].replace("Z", "+00:00")
            )
        
        return FileInfo(
            id=item["id"],
            name=name,
            path=item_path,
            size=item.get("size", 0),
            mime_type=item.get("file", {}).get("mimeType"),
            modified_at=modified_at,
            created_at=created_at,
            is_folder="folder" in item,
            source_url=item.get("webUrl"),
            metadata={
                "etag": item.get("eTag"),
                "cTag": item.get("cTag"),
                "parentReference": item.get("parentReference"),
            },
        )
    
    async def get_file_info(self, file_id: str) -> FileInfo | None:
        """Get info for a specific file."""
        try:
            await self._get_site_and_drive()
            
            item = await self._api_request(
                "GET",
                f"/drives/{self._drive_id}/items/{file_id}",
            )
            
            parent_path = ""
            if "parentReference" in item and "path" in item["parentReference"]:
                # Path format: /drives/xxx/root:/folder/subfolder
                parent_path = item["parentReference"]["path"].split("root:")[-1]
            
            return self._parse_drive_item(item, parent_path)
            
        except Exception:
            return None
    
    async def download_file(
        self,
        file_id: str,
        target_path: Path,
        on_progress: ProgressCallback | None = None,
    ) -> bool:
        """Download a file from SharePoint."""
        try:
            await self._get_site_and_drive()
            
            # Get download URL
            item = await self._api_request(
                "GET",
                f"/drives/{self._drive_id}/items/{file_id}",
            )
            
            download_url = item.get("@microsoft.graph.downloadUrl")
            if not download_url:
                return False
            
            total_size = item.get("size", 0)
            
            # Download file
            await self._ensure_session()
            async with self._session.get(download_url) as response:
                if response.status != 200:
                    return False
                
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                downloaded = 0
                with open(target_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if on_progress and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            on_progress(progress, 100, f"Downloading: {item['name']}")
            
            return True
            
        except Exception as e:
            print(f"Download error: {e}")
            return False
    
    async def stream_file(
        self,
        file_id: str,
        chunk_size: int = 8192,
    ) -> AsyncGenerator[bytes, None]:
        """Stream file content from SharePoint."""
        await self._get_site_and_drive()
        
        # Get download URL
        item = await self._api_request(
            "GET",
            f"/drives/{self._drive_id}/items/{file_id}",
        )
        
        download_url = item.get("@microsoft.graph.downloadUrl")
        if not download_url:
            raise Exception("No download URL available")
        
        await self._ensure_session()
        async with self._session.get(download_url) as response:
            async for chunk in response.content.iter_chunked(chunk_size):
                yield chunk
    
    async def upload_file(
        self,
        local_path: Path,
        remote_path: str,
        on_progress: ProgressCallback | None = None,
    ) -> FileInfo | None:
        """
        Upload a file to SharePoint.
        
        Args:
            local_path: Local file path
            remote_path: Remote path in SharePoint
            on_progress: Progress callback
            
        Returns:
            FileInfo of uploaded file or None on failure
        """
        try:
            await self._get_site_and_drive()
            
            file_size = local_path.stat().st_size
            
            # For small files (< 4MB), use simple upload
            if file_size < 4 * 1024 * 1024:
                with open(local_path, "rb") as f:
                    content = f.read()
                
                encoded_path = remote_path.replace("/", ":/").strip(":/")
                result = await self._api_request(
                    "PUT",
                    f"/drives/{self._drive_id}/root:/{encoded_path}:/content",
                    data=content,
                    headers={"Content-Type": "application/octet-stream"},
                )
                
                return self._parse_drive_item(result, "/".join(remote_path.split("/")[:-1]))
            
            else:
                # For large files, use upload session
                # This is a simplified implementation
                # Full implementation would use chunked upload
                return await self._upload_large_file(local_path, remote_path, on_progress)
                
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    async def _upload_large_file(
        self,
        local_path: Path,
        remote_path: str,
        on_progress: ProgressCallback | None = None,
    ) -> FileInfo | None:
        """Upload large file using upload session."""
        await self._get_site_and_drive()
        
        encoded_path = remote_path.replace("/", ":/").strip(":/")
        
        # Create upload session
        session = await self._api_request(
            "POST",
            f"/drives/{self._drive_id}/root:/{encoded_path}:/createUploadSession",
            json={"item": {"@microsoft.graph.conflictBehavior": "rename"}},
        )
        
        upload_url = session["uploadUrl"]
        file_size = local_path.stat().st_size
        chunk_size = 10 * 1024 * 1024  # 10MB chunks
        
        await self._ensure_session()
        
        with open(local_path, "rb") as f:
            uploaded = 0
            while uploaded < file_size:
                chunk = f.read(chunk_size)
                chunk_end = min(uploaded + len(chunk), file_size)
                
                headers = {
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {uploaded}-{chunk_end - 1}/{file_size}",
                }
                
                async with self._session.put(
                    upload_url,
                    data=chunk,
                    headers=headers,
                ) as response:
                    result = await response.json()
                    
                    if on_progress:
                        progress = int((chunk_end / file_size) * 100)
                        on_progress(progress, 100, f"Uploading: {local_path.name}")
                
                uploaded = chunk_end
        
        # Get the final item
        return await self.get_file_info(result["id"])
    
    async def create_folder(self, path: str) -> FileInfo | None:
        """Create a folder in SharePoint."""
        try:
            await self._get_site_and_drive()
            
            parts = path.strip("/").split("/")
            folder_name = parts[-1]
            parent_path = "/".join(parts[:-1])
            
            if parent_path:
                encoded_parent = parent_path.replace("/", ":/")
                endpoint = f"/drives/{self._drive_id}/root:/{encoded_parent}:/children"
            else:
                endpoint = f"/drives/{self._drive_id}/root/children"
            
            result = await self._api_request(
                "POST",
                endpoint,
                json={
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "fail",
                },
            )
            
            return self._parse_drive_item(result, parent_path)
            
        except Exception as e:
            print(f"Create folder error: {e}")
            return None
    
    async def delete_item(self, file_id: str) -> bool:
        """Delete a file or folder."""
        try:
            await self._get_site_and_drive()
            
            await self._api_request(
                "DELETE",
                f"/drives/{self._drive_id}/items/{file_id}",
            )
            
            return True
            
        except Exception:
            return False
    
    async def search(self, query: str, max_results: int = 25) -> list[FileInfo]:
        """Search for files in SharePoint."""
        await self._get_site_and_drive()
        
        result = await self._api_request(
            "GET",
            f"/drives/{self._drive_id}/root/search(q='{query}')?$top={max_results}",
        )
        
        files = []
        for item in result.get("value", []):
            parent_path = ""
            if "parentReference" in item and "path" in item["parentReference"]:
                parent_path = item["parentReference"]["path"].split("root:")[-1]
            
            files.append(self._parse_drive_item(item, parent_path))
        
        return files
    
    async def close(self):
        """Close the connector and release resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        
        self._is_connected = False
        self._access_token = None
        self._token_expires_at = None
