"""File upload/download API endpoints."""

import shutil
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.config import settings

router = APIRouter(prefix="/files", tags=["Files"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".txt", ".rtf", ".odt", ".ods", ".odp",
    # Images
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
    # Data
    ".csv", ".json", ".xml",
}


def get_user_upload_dir(user_id: str) -> Path:
    """Get user's upload directory."""
    user_dir = settings.upload_dir / "users" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


@router.post("/upload")
async def upload_file(
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> dict:
    """Upload a file."""
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {ext} not allowed",
        )
    
    # Check file size
    if file.size and file.size > settings.max_upload_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {settings.max_upload_size // 1024 // 1024}MB",
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{ext}"
    user_dir = get_user_upload_dir(current_user.id)
    file_path = user_dir / safe_filename
    
    # Save file
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)
    
    return {
        "id": file_id,
        "filename": file.filename,
        "size": len(content),
        "type": ext[1:],  # Remove leading dot
        "path": str(file_path.relative_to(settings.upload_dir)),
    }


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: CurrentUser,
) -> FileResponse:
    """Download a file by ID."""
    user_dir = get_user_upload_dir(current_user.id)
    
    # Find file with matching ID (any extension)
    matching_files = list(user_dir.glob(f"{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    
    file_path = matching_files[0]
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )


@router.get("/{file_id}/preview")
async def get_file_preview(
    file_id: str,
    current_user: CurrentUser,
) -> dict:
    """Get file preview/metadata."""
    user_dir = get_user_upload_dir(current_user.id)
    
    matching_files = list(user_dir.glob(f"{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    
    file_path = matching_files[0]
    stat = file_path.stat()
    
    return {
        "id": file_id,
        "filename": file_path.name,
        "size": stat.st_size,
        "type": file_path.suffix[1:],
        "created_at": stat.st_ctime,
        "modified_at": stat.st_mtime,
    }


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: CurrentUser,
) -> dict:
    """Delete a file."""
    user_dir = get_user_upload_dir(current_user.id)
    
    matching_files = list(user_dir.glob(f"{file_id}.*"))
    
    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    
    for f in matching_files:
        f.unlink()
    
    return {"message": "File deleted"}
