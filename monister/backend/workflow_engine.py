"""
Monister Workflow Engine - Multi-step document automation workflows.

A workflow is a sequence of steps that process documents:
1. Extract data from source document
2. Fill template with extracted data
3. Validate compliance
4. Generate output document
5. Track deadline

Each step can have conditions, transformations, and HITL checkpoints.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from config import settings


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_HITL = "waiting_hitl"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    name_uz: str
    step_type: str  # "extract", "fill", "validate", "generate", "transform", "notify"
    tool_name: str = ""
    params: dict = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    output: Any = None
    error: str = ""
    requires_hitl: bool = False
    condition: str = ""  # Simple expression like "step_1.output.has_data == true"
    started_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_uz": self.name_uz,
            "step_type": self.step_type,
            "tool_name": self.tool_name,
            "params": self.params,
            "status": self.status.value,
            "output": str(self.output)[:500] if self.output else None,
            "error": self.error,
            "requires_hitl": self.requires_hitl,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class Workflow:
    """A complete document workflow."""
    id: str
    name: str
    name_uz: str
    description: str
    industry_module: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    current_step: int = 0
    created_at: str = ""
    updated_at: str = ""
    input_data: dict = field(default_factory=dict)
    output_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "name_uz": self.name_uz,
            "description": self.description,
            "industry_module": self.industry_module,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "current_step": self.current_step,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "input_data": self.input_data,
            "output_files": self.output_files,
        }


# ============== Predefined Workflows ==============

def create_document_generation_workflow(
    name: str,
    template_path: str,
    fields: dict,
    industry: str = "",
) -> Workflow:
    """Create a standard document generation workflow."""
    wf_id = f"wf-{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    return Workflow(
        id=wf_id,
        name=name,
        name_uz=name,
        description=f"Generate {name} from template",
        industry_module=industry,
        created_at=now,
        updated_at=now,
        input_data={"template": template_path, "fields": fields},
        steps=[
            WorkflowStep(
                id=f"{wf_id}-s1",
                name="Validate Fields",
                name_uz="Maydonlarni tekshirish",
                step_type="validate",
                tool_name="check_compliance",
                params={"fields": fields, "template": template_path},
            ),
            WorkflowStep(
                id=f"{wf_id}-s2",
                name="Fill Template",
                name_uz="Shablonni to'ldirish",
                step_type="fill",
                tool_name="fill_template",
                params={"template_path": template_path, "data": fields},
            ),
            WorkflowStep(
                id=f"{wf_id}-s3",
                name="Review Output",
                name_uz="Natijani ko'rib chiqish",
                step_type="generate",
                requires_hitl=True,
            ),
        ],
    )


def create_batch_workflow(
    name: str,
    template_path: str,
    data_source: str,  # Excel/CSV path
) -> Workflow:
    """Create a batch document generation workflow."""
    wf_id = f"wf-{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    return Workflow(
        id=wf_id,
        name=name,
        name_uz=f"Ommaviy: {name}",
        description=f"Batch generate {name} from data source",
        created_at=now,
        updated_at=now,
        input_data={"template": template_path, "data_source": data_source},
        steps=[
            WorkflowStep(
                id=f"{wf_id}-s1",
                name="Parse Data Source",
                name_uz="Ma'lumotlarni o'qish",
                step_type="extract",
                tool_name="parse_excel",
                params={"file_path": data_source},
            ),
            WorkflowStep(
                id=f"{wf_id}-s2",
                name="Validate Data",
                name_uz="Ma'lumotlarni tekshirish",
                step_type="validate",
            ),
            WorkflowStep(
                id=f"{wf_id}-s3",
                name="Generate Documents",
                name_uz="Hujjatlarni yaratish",
                step_type="fill",
                tool_name="batch_generate",
                params={"template_path": template_path},
            ),
            WorkflowStep(
                id=f"{wf_id}-s4",
                name="Package Output",
                name_uz="Natijalarni jamlash",
                step_type="generate",
            ),
        ],
    )


def create_ocr_workflow(
    name: str,
    source_file: str,
    target_template: str = "",
) -> Workflow:
    """Create an OCR → template fill workflow."""
    wf_id = f"wf-{uuid.uuid4().hex[:8]}"
    now = datetime.now().isoformat()

    steps = [
        WorkflowStep(
            id=f"{wf_id}-s1",
            name="Extract Text (OCR)",
            name_uz="Matnni ajratish (OCR)",
            step_type="extract",
            tool_name="ocr_extract",
            params={"file_path": source_file},
        ),
        WorkflowStep(
            id=f"{wf_id}-s2",
            name="Parse Fields",
            name_uz="Maydonlarni ajratish",
            step_type="transform",
            params={"extract_fields": True},
        ),
    ]

    if target_template:
        steps.extend([
            WorkflowStep(
                id=f"{wf_id}-s3",
                name="Fill Target Template",
                name_uz="Yangi shablonni to'ldirish",
                step_type="fill",
                tool_name="fill_template",
                params={"template_path": target_template},
            ),
            WorkflowStep(
                id=f"{wf_id}-s4",
                name="Review",
                name_uz="Ko'rib chiqish",
                step_type="generate",
                requires_hitl=True,
            ),
        ])

    return Workflow(
        id=wf_id,
        name=name,
        name_uz=f"OCR: {name}",
        description=f"Extract data from {source_file} and fill template",
        created_at=now,
        updated_at=now,
        input_data={"source_file": source_file, "target_template": target_template},
        steps=steps,
    )


# ============== Workflow Manager ==============

class WorkflowManager:
    """Manages workflow instances and persistence."""

    def __init__(self):
        self.workflows: dict[str, Workflow] = {}
        self._ensure_dir()

    def _ensure_dir(self):
        """Ensure workflows directory exists."""
        wf_dir = settings.data_dir / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)

    def create(self, workflow: Workflow) -> Workflow:
        """Register a new workflow."""
        self.workflows[workflow.id] = workflow
        self._save(workflow)
        return workflow

    def get(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)

    def list_all(self) -> list[dict]:
        """List all workflows."""
        return [wf.to_dict() for wf in self.workflows.values()]

    def advance_step(self, workflow_id: str) -> WorkflowStep | None:
        """Move to the next step in a workflow."""
        wf = self.workflows.get(workflow_id)
        if not wf:
            return None

        # Mark current step as completed
        if wf.current_step < len(wf.steps):
            step = wf.steps[wf.current_step]
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now().isoformat()

        # Move to next step
        wf.current_step += 1
        wf.updated_at = datetime.now().isoformat()

        if wf.current_step >= len(wf.steps):
            wf.status = WorkflowStatus.COMPLETED
            self._save(wf)
            return None

        # Start next step
        next_step = wf.steps[wf.current_step]
        next_step.status = StepStatus.RUNNING
        next_step.started_at = datetime.now().isoformat()

        self._save(wf)
        return next_step

    def fail_step(self, workflow_id: str, error: str):
        """Mark current step as failed."""
        wf = self.workflows.get(workflow_id)
        if not wf or wf.current_step >= len(wf.steps):
            return

        step = wf.steps[wf.current_step]
        step.status = StepStatus.FAILED
        step.error = error
        step.completed_at = datetime.now().isoformat()
        wf.status = WorkflowStatus.FAILED
        wf.updated_at = datetime.now().isoformat()
        self._save(wf)

    def set_step_output(self, workflow_id: str, output: Any):
        """Set output data for current step."""
        wf = self.workflows.get(workflow_id)
        if not wf or wf.current_step >= len(wf.steps):
            return

        step = wf.steps[wf.current_step]
        step.output = output

    def _save(self, workflow: Workflow):
        """Persist workflow to disk."""
        try:
            wf_dir = settings.data_dir / "workflows"
            wf_file = wf_dir / f"{workflow.id}.json"
            with open(wf_file, "w", encoding="utf-8") as f:
                json.dump(workflow.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Workflow save error: {e}")

    def _load_all(self):
        """Load all workflows from disk."""
        wf_dir = settings.data_dir / "workflows"
        if not wf_dir.exists():
            return
        for wf_file in wf_dir.glob("*.json"):
            try:
                with open(wf_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Reconstruct workflow (simplified)
                    wf = Workflow(
                        id=data["id"],
                        name=data["name"],
                        name_uz=data.get("name_uz", data["name"]),
                        description=data.get("description", ""),
                        status=WorkflowStatus(data.get("status", "draft")),
                        current_step=data.get("current_step", 0),
                        created_at=data.get("created_at", ""),
                        updated_at=data.get("updated_at", ""),
                    )
                    self.workflows[wf.id] = wf
            except Exception as e:
                print(f"Workflow load error: {e}")


# Global instance
workflow_manager = WorkflowManager()


# ============== Exports ==============
__all__ = [
    "WorkflowStep",
    "Workflow",
    "WorkflowStatus",
    "StepStatus",
    "WorkflowManager",
    "workflow_manager",
    "create_document_generation_workflow",
    "create_batch_workflow",
    "create_ocr_workflow",
]
