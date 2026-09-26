"""Template module for document templates."""

from app.templates.bank_templates import (
    ALL_TEMPLATES,
    BANK_TEMPLATES,
    GOVERNMENT_TEMPLATES,
    CONTRACT_TEMPLATES,
    HR_TEMPLATES,
    get_all_template_definitions,
    get_template_by_id,
    get_templates_by_organization,
    get_templates_by_category,
    get_template_field_names,
)

__all__ = [
    "ALL_TEMPLATES",
    "BANK_TEMPLATES",
    "GOVERNMENT_TEMPLATES",
    "CONTRACT_TEMPLATES",
    "HR_TEMPLATES",
    "get_all_template_definitions",
    "get_template_by_id",
    "get_templates_by_organization",
    "get_templates_by_category",
    "get_template_field_names",
]
