"""
Google Drive Connector.

Provides integration with Google Drive using Google Drive API v3.

Required credentials in config:
- service_account_json: Service account JSON key (as dict or path to file)
OR
- credentials_json: OAuth2 credentials JSON
- token_json: OAuth2 token (optional, will be refreshed)
"""

import asyncio
import json
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


# MIME types for Google Workspace files
GOOGLE_MIME_TYPES = {
    "application/vnd.google-apps.document": {
        "export_mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "extension": ".docx",
    },
    "application/vnd.google-apps.spreadsheet": {
        "export_mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "extension": ".xlsx",
    },
    "application/vnd.google-apps.presentation": {
        "export_mime": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "extension": ".pptx",
    },
    "application/vnd.google-apps.drawing": {
        "export_mime": "image/png",
        "extension": ".png",
    },
}


@register_connector(ConnectorType.GOOGLE_DRIVE)
class GoogleDriveConnector(BaseConnector):
    """
    Connector for Google Drive.
    
    Uses Google Drive API v3 for file operations.
    Supports both service account and OAuth2 authentication.
    """
    
    API_BASE = "https://www.googleapis.com/drive/v3"
    UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
    AUTH_URL = "https://oauth2.googleapis.com/token"
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._session: aiohttp.ClientSession | None = None
    
    async def _ensure_session(self):
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
    
    async def _get_access_token(self) -> str:
        """Get or refresh the access token."""
        # Check if current token is still valid
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at:
                return self._access_token
        
        await self._ensure_session()
        
        # Service account authentication
        service_account = self.config.credentials.get("service_account_json")
        if service_account:
            return await self._auth_service_account(service_account)
        
        # OAuth2 refresh token
        refresh_token = self.config.credentials.get("refresh_token")
        client_id = self.config.credentials.get("client_id")
        client_secret = self.config.credentials.get("client_secret")
        
        if refresh_token and client_id and client_secret:
            return await self._auth_oauth2(refresh_token, client_id, client_secret)
        
        raise ValueError("No valid credentials provided for Google Drive")
    
    async def _auth_service_account(self, service_account: dict | str) -> str:
        """Authenticate using service account."""
        import time
        import base64
        import hashlib
        import json as json_module
        
        # Load service account if it's a path
        if isinstance(service_account, str):
            with open(service_account) as f:
                service_account = json_module.load(f)
        
        # Create JWT
        now = int(time.time())
        
        header = {
            "alg": "RS256",
            "typ": "JWT",
        }
        
        claims = {
            "iss": service_account["client_email"],
            "scope": "https://www.googleapis.com/auth/drive",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }
        
        # For production, use proper JWT library
        # This is a simplified placeholder
        try:
            import jwt
            
            token = jwt.encode(
                claims,
                service_account["private_key"],
                algorithm="RS256",
                headers=header,
            )
        except ImportError:
            raise ImportError("PyJWT library required for service account auth")
        
        # Exchange JWT for access token
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": token,
        }
        
        async with self._session.post(self.AUTH_URL, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Service account auth failed: {error_text}")
            
            result = await response.json()
            self._access_token = result["access_token"]
            self._token_expires_at = datetime.now().replace(
                second=datetime.now().second + result.get("expires_in", 3600) - 60
            )
            
            return self._access_token
    
    async def _auth_oauth2(
        self,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> str:
        """Authenticate using OAuth2 refresh token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        
        async with self._session.post(self.AUTH_URL, data=data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"OAuth2 auth failed: {error_text}")
            
            result = await response.json()
            self._access_token = result["access_token"]
            self._token_expires_at = datetime.now().replace(
                second=datetime.now().second + result.get("expires_in", 3600) - 60
            )
            
            return self._access_token
    
    async def _api_request(
        self,
        method: str,
        endpoint: str,
        base_url: str | None = None,
        **kwargs,
    ) -> dict | bytes:
        """Make an authenticated API request."""
        await self._ensure_session()
        token = await self._get_access_token()
        
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        base = base_url or self.API_BASE
        url = f"{base}{endpoint}"
        
        async with self._session.request(method, url, headers=headers, **kwargs) as response:
            if response.status >= 400:
                error_text = await response.text()
                raise Exception(f"API request failed ({response.status}): {error_text}")
            
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return await response.json()
            else:
                return await response.read()
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test the Google Drive connection."""
        try:
            await self._get_access_token()
            
            # Try to get drive info
            result = await self._api_request("GET", "/about?fields=user,storageQuota")
            
            user_email = result.get("user", {}).get("emailAddress", "Unknown")
            self._is_connected = True
            return True, f"Connected to Google Drive as {user_email}"
            
        except Exception as e:
            self._is_connected = False
            return False, f"Connection failed: {str(e)}"
    
    async def list_files(
        self,
        path: str = "/",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """
        List files in Google Drive.
        
        Note: Google Drive uses folder IDs, not paths.
        Path "/" returns root folder contents.
        """
        files = []
        
        # Get folder ID from path
        folder_id = await self._resolve_path_to_id(path)
        
        await self._list_files_in_folder(folder_id, path, files, recursive)
        return files
    
    async def _resolve_path_to_id(self, path: str) -> str:
        """Resolve a path to a folder ID."""
        if path == "/" or path == "":
            return "root"
        
        parts = path.strip("/").split("/")
        current_id = "root"
        
        for part in parts:
            # Search for folder with this name in current folder
            query = f"name='{part}' and '{current_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            result = await self._api_request(
                "GET",
                f"/files?q={query}&fields=files(id,name)",
            )
            
            if not result.get("files"):
                raise Exception(f"Folder not found: {path}")
            
            current_id = result["files"][0]["id"]
        
        return current_id
    
    async def _list_files_in_folder(
        self,
        folder_id: str,
        folder_path: str,
        files: list[FileInfo],
        recursive: bool,
    ):
        """List files in a folder."""
        page_token = None
        
        while True:
            query = f"'{folder_id}' in parents and trashed=false"
            fields = "nextPageToken,files(id,name,mimeType,size,modifiedTime,createdTime,webViewLink,md5Checksum)"
            
            endpoint = f"/files?q={query}&fields={fields}&pageSize=100"
            if page_token:
                endpoint += f"&pageToken={page_token}"
            
            result = await self._api_request("GET", endpoint)
            
            for item in result.get("files", []):
                file_info = self._parse_drive_item(item, folder_path)
                files.append(file_info)
                
                # Recurse into folders
                if recursive and file_info.is_folder:
                    await self._list_files_in_folder(
                        item["id"],
                        f"{folder_path}/{file_info.name}".lstrip("/"),
                        files,
                        recursive,
                    )
            
            page_token = result.get("nextPageToken")
            if not page_token:
                break
    
    def _parse_drive_item(self, item: dict, parent_path: str) -> FileInfo:
        """Parse Drive API item to FileInfo."""
        name = item["name"]
        mime_type = item.get("mimeType", "")
        
        # Handle Google Workspace files
        if mime_type in GOOGLE_MIME_TYPES:
            export_info = GOOGLE_MIME_TYPES[mime_type]
            name = name + export_info["extension"]
        
        item_path = f"{parent_path}/{name}".lstrip("/")
        
        # Parse dates
        modified_at = None
        created_at = None
        if "modifiedTime" in item:
            modified_at = datetime.fromisoformat(
                item["modifiedTime"].replace("Z", "+00:00")
            )
        if "createdTime" in item:
            created_at = datetime.fromisoformat(
                item["createdTime"].replace("Z", "+00:00")
            )
        
        is_folder = mime_type == "application/vnd.google-apps.folder"
        
        return FileInfo(
            id=item["id"],
            name=name,
            path=item_path,
            size=int(item.get("size", 0)),
            mime_type=mime_type,
            modified_at=modified_at,
            created_at=created_at,
            is_folder=is_folder,
            source_url=item.get("webViewLink"),
            checksum=item.get("md5Checksum"),
            metadata={
                "original_name": item["name"],
                "google_mime_type": mime_type if mime_type in GOOGLE_MIME_TYPES else None,
            },
        )
    
    async def get_file_info(self, file_id: str) -> FileInfo | None:
        """Get info for a specific file."""
        try:
            fields = "id,name,mimeType,size,modifiedTime,createdTime,webViewLink,md5Checksum,parents"
            item = await self._api_request("GET", f"/files/{file_id}?fields={fields}")
            
            # Get parent path
            parent_path = ""
            if "parents" in item:
                try:
                    parent_path = await self._get_path_for_id(item["parents"][0])
                except Exception:
                    pass
            
            return self._parse_drive_item(item, parent_path)
            
        except Exception:
            return None
    
    async def _get_path_for_id(self, file_id: str) -> str:
        """Get the path for a file ID."""
        if file_id == "root":
            return ""
        
        parts = []
        current_id = file_id
        
        while current_id != "root":
            item = await self._api_request("GET", f"/files/{current_id}?fields=name,parents")
            parts.insert(0, item["name"])
            
            if "parents" in item:
                current_id = item["parents"][0]
            else:
                break
        
        return "/".join(parts)
    
    async def download_file(
        self,
        file_id: str,
        target_path: Path,
        on_progress: ProgressCallback | None = None,
    ) -> bool:
        """Download a file from Google Drive."""
        try:
            # Get file info first
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return False
            
            # Determine download URL
            mime_type = file_info.metadata.get("google_mime_type")
            
            if mime_type and mime_type in GOOGLE_MIME_TYPES:
                # Export Google Workspace file
                export_mime = GOOGLE_MIME_TYPES[mime_type]["export_mime"]
                endpoint = f"/files/{file_id}/export?mimeType={export_mime}"
            else:
                # Regular file download
                endpoint = f"/files/{file_id}?alt=media"
            
            await self._ensure_session()
            token = await self._get_access_token()
            
            url = f"{self.API_BASE}{endpoint}"
            headers = {"Authorization": f"Bearer {token}"}
            
            async with self._session.get(url, headers=headers) as response:
                if response.status != 200:
                    return False
                
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                total_size = file_info.size or int(response.headers.get("Content-Length", 0))
                downloaded = 0
                
                with open(target_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if on_progress and total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            on_progress(progress, 100, f"Downloading: {file_info.name}")
            
            return True
            
        except Exception as e:
            print(f"Download error: {e}")
            return False
    
    async def stream_file(
        self,
        file_id: str,
        chunk_size: int = 8192,
    ) -> AsyncGenerator[bytes, None]:
        """Stream file content from Google Drive."""
        file_info = await self.get_file_info(file_id)
        if not file_info:
            raise Exception("File not found")
        
        mime_type = file_info.metadata.get("google_mime_type")
        
        if mime_type and mime_type in GOOGLE_MIME_TYPES:
            export_mime = GOOGLE_MIME_TYPES[mime_type]["export_mime"]
            endpoint = f"/files/{file_id}/export?mimeType={export_mime}"
        else:
            endpoint = f"/files/{file_id}?alt=media"
        
        await self._ensure_session()
        token = await self._get_access_token()
        
        url = f"{self.API_BASE}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with self._session.get(url, headers=headers) as response:
            async for chunk in response.content.iter_chunked(chunk_size):
                yield chunk
    
    async def search(self, query: str, max_results: int = 25) -> list[FileInfo]:
        """Search for files in Google Drive."""
        search_query = f"fullText contains '{query}' and trashed=false"
        fields = "files(id,name,mimeType,size,modifiedTime,createdTime,webViewLink,md5Checksum,parents)"
        
        result = await self._api_request(
            "GET",
            f"/files?q={search_query}&fields={fields}&pageSize={max_results}",
        )
        
        files = []
        for item in result.get("files", []):
            parent_path = ""
            if "parents" in item:
                try:
                    parent_path = await self._get_path_for_id(item["parents"][0])
                except Exception:
                    pass
            
            files.append(self._parse_drive_item(item, parent_path))
        
        return files
    
    async def close(self):
        """Close the connector and release resources."""
        if self._session and not self._session.closed:
            await self._session.close()
        
        self._is_connected = False
        self._access_token = None
        self._token_expires_at = None
