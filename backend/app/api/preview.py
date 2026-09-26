"""API endpoints for document preview and editing."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser, DB
from app.config import settings
from app.services.preview import preview_service, PreviewResult


router = APIRouter(prefix="/preview", tags=["preview"])


class PreviewRequest(BaseModel):
    """Request for document preview."""
    file_path: str | None = None
    file_id: str | None = None
    page: int = 1
    max_width: int = 1200
    max_height: int = 1600


class EditableContentRequest(BaseModel):
    """Request for editable content."""
    file_path: str


class SaveContentRequest(BaseModel):
    """Request to save edited content."""
    file_path: str
    content: dict[str, Any]


@router.post("")
async def generate_preview(
    request: PreviewRequest,
    current_user = Depends(CurrentUser),
):
    """
    Generate a preview for a document.
    
    Supports all common file types:
    - Images (PNG, JPG, GIF, WebP, SVG)
    - PDF
    - Word (DOCX, DOC)
    - Excel (XLSX, XLS, CSV)
    - PowerPoint (PPTX, PPT)
    - Text files (TXT, MD, LOG)
    - Code files (PY, JS, TS, HTML, CSS, etc.)
    - JSON, XML, YAML
    """
    # Resolve file path
    if request.file_path:
        file_path = Path(request.file_path)
        
        # Security: ensure path is within allowed directories
        allowed_dirs = [
            settings.upload_dir,
            settings.upload_dir / "synced",
        ]
        
        is_allowed = False
        for allowed_dir in allowed_dirs:
            try:
                file_path.resolve().relative_to(allowed_dir.resolve())
                is_allowed = True
                break
            except ValueError:
                continue
        
        if not is_allowed:
            raise HTTPException(
                status_code=403,
                detail="Access to this file is not allowed",
            )
    
    elif request.file_id:
        # Resolve file_id to path (from uploads)
        file_path = settings.upload_dir / current_user.id / request.file_id
        
        if not file_path.exists():
            # Try without user subdirectory
            file_path = settings.upload_dir / request.file_id
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Either file_path or file_id must be provided",
        )
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Generate preview
    result = await preview_service.generate_preview(
        file_path=file_path,
        max_width=request.max_width,
        max_height=request.max_height,
        page=request.page,
    )
    
    return result.to_dict()


@router.get("/file/{file_id}")
async def preview_file_by_id(
    file_id: str,
    page: int = 1,
    current_user = Depends(CurrentUser),
):
    """Generate preview for a file by its ID."""
    # Find file in user's uploads
    user_upload_dir = settings.upload_dir / current_user.id
    
    # Search for file
    file_path = None
    
    if user_upload_dir.exists():
        for f in user_upload_dir.rglob("*"):
            if f.stem == file_id or f.name == file_id:
                file_path = f
                break
    
    if not file_path:
        # Check general uploads
        for f in settings.upload_dir.rglob("*"):
            if f.stem == file_id or f.name == file_id:
                file_path = f
                break
    
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    result = await preview_service.generate_preview(file_path, page=page)
    return result.to_dict()


@router.post("/upload")
async def preview_uploaded_file(
    file: UploadFile = File(...),
    current_user = Depends(CurrentUser),
):
    """
    Upload and preview a file in one step.
    
    The file is saved to a temporary location and previewed.
    """
    import tempfile
    import uuid
    
    # Save to temp location
    suffix = Path(file.filename).suffix if file.filename else ""
    temp_id = str(uuid.uuid4())[:8]
    temp_path = Path(tempfile.gettempdir()) / f"preview_{temp_id}{suffix}"
    
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        result = await preview_service.generate_preview(temp_path)
        response = result.to_dict()
        response["filename"] = file.filename
        response["temp_path"] = str(temp_path)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/editable")
async def get_editable_content(
    request: EditableContentRequest,
    current_user = Depends(CurrentUser),
):
    """
    Get editable content for a document.
    
    Returns structured data that can be edited in the frontend
    and saved back to the file.
    """
    file_path = Path(request.file_path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    content = await preview_service.get_editable_content(file_path)
    return content


@router.post("/save")
async def save_content(
    request: SaveContentRequest,
    current_user = Depends(CurrentUser),
):
    """
    Save edited content back to a file.
    
    Supports text files, Word documents, and Excel spreadsheets.
    """
    file_path = Path(request.file_path)
    
    # Security check
    allowed_dirs = [settings.upload_dir]
    
    is_allowed = False
    for allowed_dir in allowed_dirs:
        try:
            file_path.resolve().relative_to(allowed_dir.resolve())
            is_allowed = True
            break
        except ValueError:
            continue
    
    if not is_allowed:
        raise HTTPException(
            status_code=403,
            detail="Cannot save to this location",
        )
    
    success = await preview_service.save_editable_content(file_path, request.content)
    
    if success:
        return {"status": "saved", "path": str(file_path)}
    else:
        raise HTTPException(status_code=500, detail="Failed to save content")


@router.get("/supported-types")
async def get_supported_types():
    """Get list of supported file types for preview."""
    return {
        "image": list(preview_service.IMAGE_EXTENSIONS),
        "pdf": list(preview_service.PDF_EXTENSIONS),
        "word": list(preview_service.WORD_EXTENSIONS),
        "excel": list(preview_service.EXCEL_EXTENSIONS),
        "powerpoint": list(preview_service.POWERPOINT_EXTENSIONS),
        "text": list(preview_service.TEXT_EXTENSIONS),
        "code": list(preview_service.CODE_EXTENSIONS),
    }
