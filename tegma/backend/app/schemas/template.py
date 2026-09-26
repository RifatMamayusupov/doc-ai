"""Template schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TemplateFieldSchema(BaseModel):
    """Schema for template field definition."""
    name: str
    type: str  # string, number, date, etc.
    required: bool = False
    description: str | None = None


class TemplateSchema(BaseModel):
    """Schema for template field definitions."""
    fields: list[TemplateFieldSchema]


class TemplateResponse(BaseModel):
    """Schema for template response."""
    id: str
    name: str
    description: str | None
    organization: str
    category: str
    preview_image: str | None
    schema: dict[str, Any] | None
    tags: list[str] | None
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Schema for template list with filters."""
    templates: list[TemplateResponse]
    total: int
    organizations: list[str]  # Available orgs for filtering
    categories: list[str]  # Available categories for filtering
