"""
Document Workflow API Endpoints.

REST API endpoints for document generation workflow management.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services.workflow import doc_workflow, WorkflowState
from app.config import settings


router = APIRouter(prefix="/workflow", tags=["Document Workflow"])


# Request/Response Models
class StartWorkflowRequest(BaseModel):
    """Request to start a document generation workflow."""
    text: str | None = None
    data: dict[str, Any] | None = None
    file_ids: list[str] | None = None


class SelectTemplatesRequest(BaseModel):
    """Request to select templates for generation."""
    session_id: str
    template_ids: list[str]


class UpdateFieldRequest(BaseModel):
    """Request to update a document field."""
    session_id: str
    document_id: str
    field_id: str
    value: Any


class DocumentActionRequest(BaseModel):
    """Request for document actions (approve, skip, regenerate)."""
    session_id: str
    document_id: str


class FinalizeRequest(BaseModel):
    """Request to finalize workflow."""
    session_id: str
    approved_document_ids: list[str] | None = None


class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""
    session_id: str
    state: str
    extracted_fields: list[str] | None = None
    suggested_templates: list[dict] | None = None
    generated_documents: list[dict] | None = None
    current_index: int = 0
    created_at: str | None = None


# Endpoints

@router.post("/start")
async def start_workflow(
    request: StartWorkflowRequest,
    current_user=Depends(CurrentUser),
):
    """
    Start a new document generation workflow.
    
    The workflow will analyze the provided data and return
    template suggestions via WebSocket.
    """
    # Get files from file_ids if provided
    files = []
    if request.file_ids:
        for file_id in request.file_ids:
            file_path = settings.upload_dir / current_user.id / file_id
            if file_path.exists():
                files.append(file_path)
    
    session = await doc_workflow.start_workflow(
        user_id=current_user.id,
        chat_id=None,  # No chat context for REST API
        input_files=files if files else None,
        input_text=request.text,
        input_data=request.data,
    )
    
    return {
        "session_id": session.session_id,
        "state": session.state.value,
        "message": "Workflow boshlandi",
    }


@router.post("/upload-and-start")
async def upload_and_start_workflow(
    file: UploadFile = File(...),
    current_user=Depends(CurrentUser),
):
    """
    Upload a file and start document generation workflow.
    """
    # Save uploaded file
    user_dir = settings.upload_dir / current_user.id
    user_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = user_dir / file.filename
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Start workflow
    session = await doc_workflow.start_workflow(
        user_id=current_user.id,
        chat_id=None,
        input_files=[file_path],
    )
    
    return {
        "session_id": session.session_id,
        "state": session.state.value,
        "file_name": file.filename,
        "message": "Fayl yuklandi va workflow boshlandi",
    }


@router.post("/select-templates")
async def select_templates(
    request: SelectTemplatesRequest,
    current_user=Depends(CurrentUser),
):
    """
    Select templates for document generation.
    
    This triggers the actual document generation process.
    """
    session = doc_workflow.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session topilmadi",
        )
    
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ruxsat yo'q",
        )
    
    await doc_workflow.select_templates(
        request.session_id,
        request.template_ids,
    )
    
    return {
        "session_id": request.session_id,
        "template_count": len(request.template_ids),
        "message": "Shablonlar tanlandi, hujjatlar yaratilmoqda",
    }


@router.post("/update-field")
async def update_field(
    request: UpdateFieldRequest,
    current_user=Depends(CurrentUser),
):
    """Update a field value in a generated document."""
    session = doc_workflow.get_session(request.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session topilmadi")
    
    await doc_workflow.update_document_field(
        request.session_id,
        request.document_id,
        request.field_id,
        request.value,
    )
    
    return {"success": True}


@router.post("/approve")
async def approve_document(
    request: DocumentActionRequest,
    current_user=Depends(CurrentUser),
):
    """Mark a document as approved."""
    session = doc_workflow.get_session(request.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session topilmadi")
    
    await doc_workflow.approve_document(
        request.session_id,
        request.document_id,
    )
    
    return {"success": True, "status": "approved"}


@router.post("/skip")
async def skip_document(
    request: DocumentActionRequest,
    current_user=Depends(CurrentUser),
):
    """Mark a document as skipped."""
    session = doc_workflow.get_session(request.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session topilmadi")
    
    await doc_workflow.skip_document(
        request.session_id,
        request.document_id,
    )
    
    return {"success": True, "status": "skipped"}


@router.post("/regenerate")
async def regenerate_document(
    request: DocumentActionRequest,
    current_user=Depends(CurrentUser),
):
    """Regenerate a document with updated field values."""
    session = doc_workflow.get_session(request.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session topilmadi")
    
    await doc_workflow.regenerate_document(
        request.session_id,
        request.document_id,
    )
    
    return {"success": True, "message": "Hujjat qayta yaratilmoqda"}


@router.post("/finalize")
async def finalize_workflow(
    request: FinalizeRequest,
    current_user=Depends(CurrentUser),
):
    """
    Finalize the workflow and get download links.
    
    Returns a list of approved documents with download URLs.
    """
    session = doc_workflow.get_session(request.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session topilmadi")
    
    result = await doc_workflow.finalize_workflow(
        request.session_id,
        request.approved_document_ids,
    )
    
    return result


@router.get("/status/{session_id}")
async def get_workflow_status(
    session_id: str,
    current_user=Depends(CurrentUser),
):
    """
    Get current workflow status.
    
    Returns the current state and all session data.
    """
    session = doc_workflow.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session topilmadi")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
    
    return WorkflowStatusResponse(
        session_id=session.session_id,
        state=session.state.value,
        extracted_fields=list(session.extracted_data.keys()) if session.extracted_data else None,
        suggested_templates=session.suggested_templates if session.suggested_templates else None,
        generated_documents=[
            {
                "id": doc.id,
                "template_id": doc.template_id,
                "template_name": doc.template_name,
                "status": doc.status,
                "error": doc.error,
            }
            for doc in session.generated_documents
        ] if session.generated_documents else None,
        current_index=session.current_document_index,
        created_at=session.created_at.isoformat() if session.created_at else None,
    )


@router.delete("/cancel/{session_id}")
async def cancel_workflow(
    session_id: str,
    current_user=Depends(CurrentUser),
):
    """Cancel an active workflow."""
    session = doc_workflow.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session topilmadi")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
    
    await doc_workflow.cancel_workflow(session_id)
    
    return {"success": True, "message": "Workflow bekor qilindi"}
