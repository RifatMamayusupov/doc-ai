"""
Document Generation Workflow - Real-time document generation with WebSocket events.

Handles the complete document generation pipeline:
1. Analyze input data
2. Match/suggest templates
3. Generate documents
4. Preview and edit
5. Finalize and download
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from app.services.document import DocumentProcessor, TemplateProcessor
from app.services.preview import preview_service
from app.config import settings


class WorkflowState(Enum):
    """Document generation workflow states."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    MATCHING_TEMPLATES = "matching_templates"
    WAITING_SELECTION = "waiting_selection"
    GENERATING = "generating"
    PREVIEWING = "previewing"
    EDITING = "editing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class GeneratedDocument:
    """Represents a generated document."""
    id: str
    template_id: str
    template_name: str
    file_path: Path | None = None
    preview_data: dict | None = None
    editable_fields: list[dict] = field(default_factory=list)
    field_values: dict[str, Any] = field(default_factory=dict)
    status: str = "draft"  # draft, approved, skipped, error
    error: str | None = None


@dataclass
class WorkflowSession:
    """Represents an active document generation session."""
    session_id: str
    user_id: str
    chat_id: str | None
    state: WorkflowState
    input_data: dict = field(default_factory=dict)
    extracted_data: dict = field(default_factory=dict)
    suggested_templates: list[dict] = field(default_factory=list)
    selected_template_ids: list[str] = field(default_factory=list)
    generated_documents: list[GeneratedDocument] = field(default_factory=list)
    current_document_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class DocumentGenerationWorkflow:
    """
    Manages the document generation workflow with real-time updates.
    
    WebSocket Events emitted:
    - workflow_started: Workflow initialized
    - analysis_started: Data analysis in progress
    - analysis_completed: Data extraction done
    - template_suggestions: Template recommendations
    - generation_started: Document generation started
    - generation_progress: Progress update
    - document_ready: Single document ready for preview
    - all_documents_ready: All documents generated
    - document_updated: Document edited
    - workflow_completed: All done
    - workflow_error: Error occurred
    """
    
    def __init__(self):
        self._sessions: dict[str, WorkflowSession] = {}
        self._emit: Callable | None = None
        self._template_processor = TemplateProcessor()
    
    def _get_document_processor(self, user_id: str) -> DocumentProcessor:
        """Get or create a document processor for a user."""
        return DocumentProcessor(user_id)
    
    def set_emit_callback(self, callback: Callable):
        """Set the callback for emitting WebSocket events."""
        self._emit = callback
    
    async def start_workflow(
        self,
        user_id: str,
        chat_id: str | None,
        input_files: list[Path] | None = None,
        input_text: str | None = None,
        input_data: dict | None = None,
    ) -> WorkflowSession:
        """
        Start a new document generation workflow.
        
        Args:
            user_id: User ID
            chat_id: Chat/conversation ID for WebSocket routing
            input_files: List of input files to analyze
            input_text: Text input to analyze
            input_data: Pre-extracted data dictionary
            
        Returns:
            WorkflowSession instance
        """
        session_id = str(uuid.uuid4())
        
        session = WorkflowSession(
            session_id=session_id,
            user_id=user_id,
            chat_id=chat_id,
            state=WorkflowState.ANALYZING,
            input_data={
                "files": [str(f) for f in input_files] if input_files else [],
                "text": input_text,
                "data": input_data or {},
            },
        )
        
        self._sessions[session_id] = session
        
        await self._emit_event(chat_id, "workflow_started", {
            "session_id": session_id,
            "state": session.state.value,
        })
        
        # Start analysis in background
        asyncio.create_task(self._analyze_input(session))
        
        return session
    
    async def _analyze_input(self, session: WorkflowSession):
        """Analyze input data and extract information."""
        await self._emit_event(session.chat_id, "analysis_started", {
            "session_id": session.session_id,
        })
        
        try:
            extracted_data = {}
            doc_processor = self._get_document_processor(session.user_id)
            
            # Process files
            if session.input_data.get("files"):
                for file_path in session.input_data["files"]:
                    file_data = await doc_processor.analyze_document(
                        Path(file_path)
                    )
                    if file_data:
                        extracted_data.update(file_data)
            
            # Process text input - store as raw context
            if session.input_data.get("text"):
                extracted_data["_input_text"] = session.input_data["text"]
            
            # Merge with provided data (this is the primary data source)
            if session.input_data.get("data"):
                extracted_data.update(session.input_data["data"])
            
            session.extracted_data = extracted_data
            session.state = WorkflowState.MATCHING_TEMPLATES
            session.updated_at = datetime.now()
            
            await self._emit_event(session.chat_id, "analysis_completed", {
                "session_id": session.session_id,
                "extracted_fields": list(extracted_data.keys()),
                "field_count": len(extracted_data),
            })
            
            # Continue to template matching
            await self._match_templates(session)
            
        except Exception as e:
            session.state = WorkflowState.ERROR
            await self._emit_event(session.chat_id, "workflow_error", {
                "session_id": session.session_id,
                "error": str(e),
                "stage": "analysis",
            })
    
    async def _match_templates(self, session: WorkflowSession):
        """Match extracted data to available templates."""
        try:
            # Get matching templates
            matches = await self._template_processor.match_templates(
                session.extracted_data,
                user_id=session.user_id,
            )
            
            session.suggested_templates = matches
            session.state = WorkflowState.WAITING_SELECTION
            session.updated_at = datetime.now()
            
            await self._emit_event(session.chat_id, "template_suggestions", {
                "session_id": session.session_id,
                "templates": [
                    {
                        "id": t["template"].id,
                        "name": t["template"].name,
                        "description": t["template"].description,
                        "category": t["template"].category,
                        "match_score": t["score"],
                        "matched_fields": t.get("matched_fields", []),
                        "missing_fields": t.get("missing_fields", []),
                        "preview_image": t["template"].preview_image,
                    }
                    for t in matches
                ],
                "extracted_data": session.extracted_data,
            })
            
        except Exception as e:
            session.state = WorkflowState.ERROR
            await self._emit_event(session.chat_id, "workflow_error", {
                "session_id": session.session_id,
                "error": str(e),
                "stage": "template_matching",
            })
    
    async def select_templates(
        self,
        session_id: str,
        template_ids: list[str],
    ):
        """
        User selects templates for document generation.
        
        Args:
            session_id: Session ID
            template_ids: List of selected template IDs
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.selected_template_ids = template_ids
        session.state = WorkflowState.GENERATING
        session.updated_at = datetime.now()
        
        await self._emit_event(session.chat_id, "templates_selected", {
            "session_id": session_id,
            "template_ids": template_ids,
            "count": len(template_ids),
        })
        
        # Start document generation
        asyncio.create_task(self._generate_documents(session))
    
    async def _generate_documents(self, session: WorkflowSession):
        """Generate documents for selected templates."""
        await self._emit_event(session.chat_id, "generation_started", {
            "session_id": session.session_id,
            "total": len(session.selected_template_ids),
        })
        
        try:
            for i, template_id in enumerate(session.selected_template_ids):
                # Progress update
                await self._emit_event(session.chat_id, "generation_progress", {
                    "session_id": session.session_id,
                    "current": i + 1,
                    "total": len(session.selected_template_ids),
                    "template_id": template_id,
                })
                
                # Generate document
                try:
                    doc = await self._generate_single_document(
                        session=session,
                        template_id=template_id,
                    )
                    session.generated_documents.append(doc)
                    
                    # Emit document ready event
                    await self._emit_event(session.chat_id, "document_ready", {
                        "session_id": session.session_id,
                        "document": {
                            "id": doc.id,
                            "template_id": doc.template_id,
                            "template_name": doc.template_name,
                            "preview": doc.preview_data,
                            "editable_fields": doc.editable_fields,
                            "status": doc.status,
                        },
                        "index": i,
                        "total": len(session.selected_template_ids),
                    })
                    
                except Exception as e:
                    error_doc = GeneratedDocument(
                        id=str(uuid.uuid4()),
                        template_id=template_id,
                        template_name=f"Template {template_id}",
                        status="error",
                        error=str(e),
                    )
                    session.generated_documents.append(error_doc)
            
            session.state = WorkflowState.PREVIEWING
            session.updated_at = datetime.now()
            
            await self._emit_event(session.chat_id, "all_documents_ready", {
                "session_id": session.session_id,
                "documents": [
                    {
                        "id": doc.id,
                        "template_id": doc.template_id,
                        "template_name": doc.template_name,
                        "status": doc.status,
                        "error": doc.error,
                    }
                    for doc in session.generated_documents
                ],
                "total": len(session.generated_documents),
                "successful": len([d for d in session.generated_documents if d.status != "error"]),
            })
            
        except Exception as e:
            session.state = WorkflowState.ERROR
            await self._emit_event(session.chat_id, "workflow_error", {
                "session_id": session.session_id,
                "error": str(e),
                "stage": "generation",
            })
    
    async def _generate_single_document(
        self,
        session: WorkflowSession,
        template_id: str,
    ) -> GeneratedDocument:
        """Generate a single document from template."""
        # Get template
        template = await self._template_processor.get_template(template_id)
        
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Generate document
        output_path = settings.upload_dir / "generated" / session.user_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        doc_id = str(uuid.uuid4())[:8]
        output_file = output_path / f"{doc_id}_{template.name.replace(' ', '_')}.docx"
        
        # Fill template
        await self._template_processor.fill_template(
            template=template,
            data=session.extracted_data,
            output_path=output_file,
        )
        
        # Generate preview
        preview_result = await preview_service.generate_preview(output_file)
        
        # Get editable fields from template schema
        editable_fields = []
        if template.schema:
            for field_name, field_info in template.schema.get("fields", {}).items():
                editable_fields.append({
                    "field_id": field_name,
                    "label": field_info.get("label", field_name),
                    "value": session.extracted_data.get(field_name, ""),
                    "type": field_info.get("type", "text"),
                    "editable": True,
                    "options": field_info.get("options"),
                })
        
        return GeneratedDocument(
            id=doc_id,
            template_id=template_id,
            template_name=template.name,
            file_path=output_file,
            preview_data=preview_result.to_dict(),
            editable_fields=editable_fields,
            field_values=session.extracted_data.copy(),
        )
    
    async def update_document_field(
        self,
        session_id: str,
        document_id: str,
        field_id: str,
        value: Any,
    ):
        """Update a field value in a generated document."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        doc = next((d for d in session.generated_documents if d.id == document_id), None)
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
        
        doc.field_values[field_id] = value
        session.updated_at = datetime.now()
        
        await self._emit_event(session.chat_id, "document_field_updated", {
            "session_id": session_id,
            "document_id": document_id,
            "field_id": field_id,
            "value": value,
        })
    
    async def regenerate_document(
        self,
        session_id: str,
        document_id: str,
    ):
        """Regenerate a document with updated field values."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        doc_index = next(
            (i for i, d in enumerate(session.generated_documents) if d.id == document_id),
            None
        )
        if doc_index is None:
            raise ValueError(f"Document not found: {document_id}")
        
        old_doc = session.generated_documents[doc_index]
        
        await self._emit_event(session.chat_id, "document_regenerating", {
            "session_id": session_id,
            "document_id": document_id,
        })
        
        try:
            # Update extracted data with new values
            updated_data = session.extracted_data.copy()
            updated_data.update(old_doc.field_values)
            
            # Save temporarily
            original_data = session.extracted_data
            session.extracted_data = updated_data
            
            # Regenerate
            new_doc = await self._generate_single_document(
                session=session,
                template_id=old_doc.template_id,
            )
            
            # Restore
            session.extracted_data = original_data
            new_doc.field_values = old_doc.field_values
            
            # Replace old document
            session.generated_documents[doc_index] = new_doc
            
            await self._emit_event(session.chat_id, "document_regenerated", {
                "session_id": session_id,
                "document": {
                    "id": new_doc.id,
                    "template_id": new_doc.template_id,
                    "template_name": new_doc.template_name,
                    "preview": new_doc.preview_data,
                    "editable_fields": new_doc.editable_fields,
                    "status": new_doc.status,
                },
            })
            
        except Exception as e:
            await self._emit_event(session.chat_id, "workflow_error", {
                "session_id": session_id,
                "error": str(e),
                "stage": "regeneration",
            })
    
    async def approve_document(self, session_id: str, document_id: str):
        """Mark a document as approved."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        doc = next((d for d in session.generated_documents if d.id == document_id), None)
        if doc:
            doc.status = "approved"
            
            await self._emit_event(session.chat_id, "document_approved", {
                "session_id": session_id,
                "document_id": document_id,
            })
    
    async def skip_document(self, session_id: str, document_id: str):
        """Mark a document as skipped."""
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        doc = next((d for d in session.generated_documents if d.id == document_id), None)
        if doc:
            doc.status = "skipped"
            
            await self._emit_event(session.chat_id, "document_skipped", {
                "session_id": session_id,
                "document_id": document_id,
            })
    
    async def finalize_workflow(
        self,
        session_id: str,
        approved_document_ids: list[str] | None = None,
    ) -> dict:
        """
        Finalize the workflow and prepare downloads.
        
        Args:
            session_id: Session ID
            approved_document_ids: Optional list of approved document IDs
            
        Returns:
            Dictionary with download information
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session.state = WorkflowState.FINALIZING
        
        await self._emit_event(session.chat_id, "finalizing_started", {
            "session_id": session_id,
        })
        
        # Get approved documents
        if approved_document_ids:
            approved_docs = [
                d for d in session.generated_documents 
                if d.id in approved_document_ids
            ]
        else:
            approved_docs = [
                d for d in session.generated_documents 
                if d.status == "approved"
            ]
        
        # Prepare download info
        downloads = []
        for doc in approved_docs:
            if doc.file_path and doc.file_path.exists():
                downloads.append({
                    "id": doc.id,
                    "name": doc.file_path.name,
                    "template_name": doc.template_name,
                    "path": str(doc.file_path),
                    "download_url": f"/api/files/download/{doc.file_path.name}",
                })
        
        session.state = WorkflowState.COMPLETED
        session.updated_at = datetime.now()
        
        await self._emit_event(session.chat_id, "workflow_completed", {
            "session_id": session_id,
            "documents": downloads,
            "total": len(downloads),
        })
        
        return {
            "session_id": session_id,
            "documents": downloads,
            "total": len(downloads),
        }
    
    async def cancel_workflow(self, session_id: str):
        """Cancel an active workflow."""
        session = self._sessions.get(session_id)
        if session:
            session.state = WorkflowState.IDLE
            await self._emit_event(session.chat_id, "workflow_cancelled", {
                "session_id": session_id,
            })
            del self._sessions[session_id]
    
    def get_session(self, session_id: str) -> WorkflowSession | None:
        """Get a workflow session by ID."""
        return self._sessions.get(session_id)
    
    async def _emit_event(self, chat_id: str | None, event_type: str, data: dict):
        """Emit a WebSocket event."""
        if self._emit and chat_id:
            try:
                await self._emit(chat_id, event_type, data)
            except Exception as e:
                print(f"Error emitting event {event_type}: {e}")


# Global workflow manager
doc_workflow = DocumentGenerationWorkflow()
