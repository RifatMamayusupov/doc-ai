"""
Document Generation Agent Tool.

Provides document generation capability to the AI agent.
Enables natural language document creation workflow.
"""

import asyncio
import json
from typing import Any
from pathlib import Path
from dataclasses import dataclass

from app.services.workflow import doc_workflow, WorkflowSession, WorkflowState
from app.services.document import TemplateProcessor
from app.config import settings


@dataclass
class GenerationResult:
    """Result of document generation."""
    success: bool
    session_id: str | None = None
    message: str = ""
    documents: list[dict] | None = None
    suggested_templates: list[dict] | None = None
    requires_selection: bool = False
    error: str | None = None


class DocumentGenerationTool:
    """
    Agent tool for document generation.
    
    Capabilities:
    - Analyze data and suggest matching templates
    - Generate documents from templates
    - Support multi-template batch generation
    - Handle field extraction and filling
    """
    
    def __init__(self):
        self._template_processor = TemplateProcessor()
        self._pending_sessions: dict[str, WorkflowSession] = {}
    
    @property
    def name(self) -> str:
        return "generate_documents"
    
    @property
    def description(self) -> str:
        return """Hujjatlarni avtomatik yaratish va shablonlarni to'ldirish uchun ishlatiladi.
        
Imkoniyatlar:
- Foydalanuvchi ma'lumotlarini tahlil qilish
- Mos shablonlarni topish va tavsiya qilish
- Bir nechta hujjatni bir vaqtda yaratish
- Maydonlarni avtomatik to'ldirish

Parametrlar:
- action: "analyze", "suggest_templates", "generate", "fill_template"
- data: Ma'lumotlar (matn, json, fayl yo'li)
- template_ids: Shablon ID lari (generate uchun)
- user_id: Foydalanuvchi ID
- chat_id: Chat ID (WebSocket uchun)

Qaytaradi: Yaratilgan hujjatlar ro'yxati yoki shablon tavsiyalari"""
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["analyze", "suggest_templates", "generate", "fill_template", "list_templates"],
                    "description": "Bajariladigan amal",
                },
                "data": {
                    "type": "object",
                    "description": "Ma'lumotlar - matn, json yoki fayl yo'llari",
                    "properties": {
                        "text": {"type": "string"},
                        "fields": {"type": "object"},
                        "files": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "template_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tanlangan shablon ID lari",
                },
                "session_id": {
                    "type": "string",
                    "description": "Mavjud sessiya ID (agar bor bo'lsa)",
                },
            },
            "required": ["action"],
        }
    
    async def execute(
        self,
        action: str,
        user_id: str,
        chat_id: str | None = None,
        data: dict | None = None,
        template_ids: list[str] | None = None,
        session_id: str | None = None,
        **kwargs,
    ) -> GenerationResult:
        """
        Execute the document generation tool.
        
        Args:
            action: Action to perform
            user_id: User ID
            chat_id: Chat ID for WebSocket updates
            data: Input data (text, fields, files)
            template_ids: Template IDs for generation
            session_id: Existing session ID
            
        Returns:
            GenerationResult with status and documents
        """
        try:
            if action == "list_templates":
                return await self._list_templates(user_id)
            
            elif action == "analyze":
                return await self._analyze_data(user_id, chat_id, data)
            
            elif action == "suggest_templates":
                return await self._suggest_templates(user_id, data)
            
            elif action == "generate":
                return await self._generate_documents(
                    user_id, chat_id, data, template_ids, session_id
                )
            
            elif action == "fill_template":
                return await self._fill_single_template(
                    user_id, template_ids[0] if template_ids else None, data
                )
            
            else:
                return GenerationResult(
                    success=False,
                    error=f"Noto'g'ri amal: {action}",
                )
                
        except Exception as e:
            return GenerationResult(
                success=False,
                error=str(e),
            )
    
    async def _list_templates(self, user_id: str) -> GenerationResult:
        """List available templates."""
        templates = await self._template_processor.get_user_templates(user_id)
        
        return GenerationResult(
            success=True,
            message=f"{len(templates)} ta shablon topildi",
            suggested_templates=[
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                }
                for t in templates
            ],
        )
    
    async def _analyze_data(
        self,
        user_id: str,
        chat_id: str | None,
        data: dict | None,
    ) -> GenerationResult:
        """Analyze input data and start workflow."""
        if not data:
            return GenerationResult(
                success=False,
                error="Ma'lumotlar berilmagan",
            )
        
        # Start workflow
        files = [Path(f) for f in data.get("files", []) if Path(f).exists()]
        
        session = await doc_workflow.start_workflow(
            user_id=user_id,
            chat_id=chat_id,
            input_files=files if files else None,
            input_text=data.get("text"),
            input_data=data.get("fields"),
        )
        
        self._pending_sessions[session.session_id] = session
        
        # Wait for analysis to complete
        await asyncio.sleep(0.5)  # Allow async processing
        
        # Check session state
        if session.state == WorkflowState.WAITING_SELECTION:
            return GenerationResult(
                success=True,
                session_id=session.session_id,
                message="Ma'lumotlar tahlil qilindi. Shablon tanlang.",
                suggested_templates=session.suggested_templates,
                requires_selection=True,
            )
        elif session.state == WorkflowState.ERROR:
            return GenerationResult(
                success=False,
                session_id=session.session_id,
                error="Tahlil qilishda xatolik",
            )
        else:
            return GenerationResult(
                success=True,
                session_id=session.session_id,
                message="Ma'lumotlar tahlil qilinmoqda...",
            )
    
    async def _suggest_templates(
        self,
        user_id: str,
        data: dict | None,
    ) -> GenerationResult:
        """Get template suggestions based on data."""
        if not data:
            return GenerationResult(
                success=False,
                error="Ma'lumotlar berilmagan",
            )
        
        # Extract fields from data
        fields = data.get("fields", {})
        if data.get("text"):
            from app.services.document import DocumentProcessor
            processor = DocumentProcessor()
            extracted = await processor.extract_from_text(data["text"])
            fields.update(extracted or {})
        
        # Match templates
        matches = await self._template_processor.match_templates(fields, user_id)
        
        return GenerationResult(
            success=True,
            message=f"{len(matches)} ta mos shablon topildi",
            suggested_templates=[
                {
                    "id": m["template"].id,
                    "name": m["template"].name,
                    "description": m["template"].description,
                    "category": m["template"].category,
                    "match_score": m["score"],
                    "matched_fields": m.get("matched_fields", []),
                }
                for m in matches
            ],
        )
    
    async def _generate_documents(
        self,
        user_id: str,
        chat_id: str | None,
        data: dict | None,
        template_ids: list[str] | None,
        session_id: str | None,
    ) -> GenerationResult:
        """Generate documents for selected templates."""
        if not template_ids:
            return GenerationResult(
                success=False,
                error="Shablon tanlanmagan",
            )
        
        # Use existing session or create new
        if session_id:
            session = self._pending_sessions.get(session_id)
            if not session:
                session = doc_workflow.get_session(session_id)
        else:
            # Create new session
            files = [Path(f) for f in (data or {}).get("files", []) if Path(f).exists()]
            
            session = await doc_workflow.start_workflow(
                user_id=user_id,
                chat_id=chat_id,
                input_files=files if files else None,
                input_text=(data or {}).get("text"),
                input_data=(data or {}).get("fields"),
            )
            
            # Wait for analysis
            await asyncio.sleep(1)
        
        if not session:
            return GenerationResult(
                success=False,
                error="Sessiya topilmadi",
            )
        
        # Select templates and generate
        await doc_workflow.select_templates(session.session_id, template_ids)
        
        # Wait for generation (with timeout)
        max_wait = 60  # seconds
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(1)
            waited += 1
            
            current_session = doc_workflow.get_session(session.session_id)
            if current_session and current_session.state in [
                WorkflowState.PREVIEWING,
                WorkflowState.COMPLETED,
                WorkflowState.ERROR,
            ]:
                break
        
        # Get results
        current_session = doc_workflow.get_session(session.session_id)
        if not current_session:
            return GenerationResult(
                success=False,
                session_id=session.session_id,
                error="Sessiya yo'qoldi",
            )
        
        if current_session.state == WorkflowState.ERROR:
            return GenerationResult(
                success=False,
                session_id=session.session_id,
                error="Hujjat yaratishda xatolik",
            )
        
        documents = [
            {
                "id": doc.id,
                "template_name": doc.template_name,
                "file_path": str(doc.file_path) if doc.file_path else None,
                "status": doc.status,
            }
            for doc in current_session.generated_documents
        ]
        
        return GenerationResult(
            success=True,
            session_id=session.session_id,
            message=f"{len(documents)} ta hujjat yaratildi",
            documents=documents,
        )
    
    async def _fill_single_template(
        self,
        user_id: str,
        template_id: str | None,
        data: dict | None,
    ) -> GenerationResult:
        """Fill a single template with provided data."""
        if not template_id:
            return GenerationResult(
                success=False,
                error="Shablon ID berilmagan",
            )
        
        if not data or not data.get("fields"):
            return GenerationResult(
                success=False,
                error="Ma'lumotlar berilmagan",
            )
        
        # Get template
        template = await self._template_processor.get_template(template_id)
        if not template:
            return GenerationResult(
                success=False,
                error=f"Shablon topilmadi: {template_id}",
            )
        
        # Generate output path
        output_dir = settings.upload_dir / "generated" / user_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import uuid
        doc_id = str(uuid.uuid4())[:8]
        output_file = output_dir / f"{doc_id}_{template.name.replace(' ', '_')}.docx"
        
        # Fill template
        await self._template_processor.fill_template(
            template=template,
            data=data["fields"],
            output_path=output_file,
        )
        
        return GenerationResult(
            success=True,
            message=f"Hujjat yaratildi: {template.name}",
            documents=[
                {
                    "id": doc_id,
                    "template_name": template.name,
                    "file_path": str(output_file),
                    "status": "approved",
                }
            ],
        )
    
    def to_tool_definition(self) -> dict:
        """Convert to LLM tool definition format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# Global tool instance
doc_gen_tool = DocumentGenerationTool()
