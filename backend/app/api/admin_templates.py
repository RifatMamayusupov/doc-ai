"""Template CRUD API endpoints."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.config import settings
from app.models.template import Template
from app.schemas.template import TemplateResponse

router = APIRouter(prefix="/admin/templates", tags=["Admin - Templates"])


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    current_user: CurrentUser,
    db: DB,
    name: str = Form(...),
    description: str = Form(None),
    organization: str = Form(...),
    category: str = Form(...),
    template_schema_json: str = Form(None),
    tags: str = Form(None),
    file: UploadFile = File(...),
    preview: UploadFile = File(None),
) -> TemplateResponse:
    """Create a new template (admin only)."""
    import json
    import uuid
    from pathlib import Path

    # Validate file type
    allowed_extensions = {'.docx', '.xlsx', '.xls', '.doc'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template file type: {file_ext}",
        )

    # Save template file
    template_id = str(uuid.uuid4())
    templates_dir = settings.upload_dir / "templates"
    templates_dir.mkdir(exist_ok=True)

    file_path = templates_dir / f"{template_id}{file_ext}"
    content = await file.read()
    file_path.write_bytes(content)

    # Save preview image if provided
    preview_path = None
    if preview:
        preview_ext = Path(preview.filename).suffix.lower()
        if preview_ext in {'.jpg', '.jpeg', '.png', '.webp'}:
            preview_file = templates_dir / f"{template_id}_preview{preview_ext}"
            preview_content = await preview.read()
            preview_file.write_bytes(preview_content)
            preview_path = f"/uploads/templates/{template_id}_preview{preview_ext}"

    # Parse schema and tags
    parsed_schema = None
    if template_schema_json:
        try:
            parsed_schema = json.loads(template_schema_json)
        except json.JSONDecodeError:
            pass

    parsed_tags = None
    if tags:
        parsed_tags = [t.strip() for t in tags.split(',')]

    # Create template record
    template = Template(
        id=template_id,
        name=name,
        description=description,
        organization=organization,
        category=category,
        file_path=str(file_path),
        preview_image=preview_path,
        schema=parsed_schema,
        tags=parsed_tags,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return TemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    current_user: CurrentUser,
    db: DB,
    name: str = Form(None),
    description: str = Form(None),
    organization: str = Form(None),
    category: str = Form(None),
    template_schema_json: str = Form(None),
    tags: str = Form(None),
    is_active: bool = Form(None),
) -> TemplateResponse:
    """Update a template (admin only)."""
    import json

    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Update fields
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if organization is not None:
        template.organization = organization
    if category is not None:
        template.category = category
    if is_active is not None:
        template.is_active = is_active

    if template_schema_json is not None:
        try:
            template.schema = json.loads(template_schema_json)
        except json.JSONDecodeError:
            pass

    if tags is not None:
        template.tags = [t.strip() for t in tags.split(',')]

    await db.commit()
    await db.refresh(template)

    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    """Delete a template (admin only)."""
    from pathlib import Path

    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Delete files
    if template.file_path:
        file_path = Path(template.file_path)
        if file_path.exists():
            file_path.unlink()

    if template.preview_image:
        preview_path = settings.upload_dir / "templates" / Path(template.preview_image).name
        if preview_path.exists():
            preview_path.unlink()

    # Delete record
    await db.delete(template)
    await db.commit()


@router.post("/match")
async def match_templates_to_document(
    current_user: CurrentUser,
    file_id: str,
    organization: str | None = None,
) -> dict:
    """Find templates that match an uploaded document."""
    from pathlib import Path
    from app.services.document import DocumentProcessor, TemplateProcessor

    # Get file path
    user_dir = settings.upload_dir / "users" / current_user.id
    matching_files = list(user_dir.glob(f"{file_id}.*"))

    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file_path = matching_files[0]

    # Analyze document
    doc_processor = DocumentProcessor(current_user.id)
    extracted_data = await doc_processor.analyze_document(file_path)

    # Match templates
    template_processor = TemplateProcessor()
    matches = await template_processor.match_templates(extracted_data, organization)

    return {
        "file_id": file_id,
        "matches": matches,
        "extracted_keys": list(extracted_data.get('extracted_data', {}).keys()),
    }
