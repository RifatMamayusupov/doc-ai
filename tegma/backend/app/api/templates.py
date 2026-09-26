"""Template API endpoints."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB
from app.models.template import Template
from app.schemas.template import TemplateListResponse, TemplateResponse

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    db: DB,
    organization: str | None = None,
    category: str | None = None,
    search: str | None = None,
) -> TemplateListResponse:
    """List templates with optional filters."""
    query = select(Template).where(Template.is_active == True)
    
    if organization:
        query = query.where(Template.organization == organization)
    if category:
        query = query.where(Template.category == category)
    if search:
        query = query.where(Template.name.ilike(f"%{search}%"))
    
    query = query.order_by(Template.organization, Template.name)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    # Get distinct organizations and categories
    orgs_result = await db.execute(
        select(distinct(Template.organization))
        .where(Template.is_active == True)
    )
    organizations = [r[0] for r in orgs_result.fetchall()]
    
    cats_result = await db.execute(
        select(distinct(Template.category))
        .where(Template.is_active == True)
    )
    categories = [r[0] for r in cats_result.fetchall()]
    
    return TemplateListResponse(
        templates=[TemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
        organizations=organizations,
        categories=categories,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, db: DB) -> TemplateResponse:
    """Get template by ID."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    return TemplateResponse.model_validate(template)


@router.get("/search/{query}", response_model=TemplateListResponse)
async def search_templates(query: str, db: DB) -> TemplateListResponse:
    """Search templates by name, organization, or tags."""
    search_query = select(Template).where(
        Template.is_active == True,
        (
            Template.name.ilike(f"%{query}%") |
            Template.organization.ilike(f"%{query}%") |
            Template.category.ilike(f"%{query}%") |
            Template.description.ilike(f"%{query}%")
        )
    )
    
    result = await db.execute(search_query)
    templates = result.scalars().all()
    
    # Get all orgs and categories
    orgs_result = await db.execute(
        select(distinct(Template.organization)).where(Template.is_active == True)
    )
    organizations = [r[0] for r in orgs_result.fetchall()]
    
    cats_result = await db.execute(
        select(distinct(Template.category)).where(Template.is_active == True)
    )
    categories = [r[0] for r in cats_result.fetchall()]
    
    return TemplateListResponse(
        templates=[TemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
        organizations=organizations,
        categories=categories,
    )
