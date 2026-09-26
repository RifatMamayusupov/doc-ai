"""
Template Database Seeder - Populates database with sample templates.
"""

import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.template import Template
from app.templates.bank_templates import ALL_TEMPLATES
from app.config import settings


async def seed_templates(db: AsyncSession) -> int:
    """
    Seed the database with template definitions.
    
    Returns:
        Number of templates created
    """
    created_count = 0
    
    for tmpl_def in ALL_TEMPLATES:
        # Check if already exists
        result = await db.execute(
            select(Template).where(Template.id == tmpl_def["id"])
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing template
            existing.name = tmpl_def["name"]
            existing.description = tmpl_def["description"]
            existing.organization = tmpl_def["organization"]
            existing.category = tmpl_def["category"]
            existing.file_path = tmpl_def["file_path"]
            existing.preview_image = tmpl_def.get("preview_image")
            existing.schema = tmpl_def.get("schema")
            existing.tags = tmpl_def.get("tags")
            existing.is_active = True
        else:
            # Create new template
            template = Template(
                id=tmpl_def["id"],
                name=tmpl_def["name"],
                description=tmpl_def["description"],
                organization=tmpl_def["organization"],
                category=tmpl_def["category"],
                file_path=tmpl_def["file_path"],
                preview_image=tmpl_def.get("preview_image"),
                schema=tmpl_def.get("schema"),
                tags=tmpl_def.get("tags"),
                is_active=True,
            )
            db.add(template)
            created_count += 1
    
    await db.commit()
    return created_count


async def create_template_directories():
    """Create directories for template storage."""
    templates_base = Path(settings.upload_dir) / "templates"
    
    dirs = [
        templates_base / "bank",
        templates_base / "government",
        templates_base / "contracts",
        templates_base / "hr",
    ]
    
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    
    return templates_base


async def run_seeder():
    """Run the template seeder."""
    print("Creating template directories...")
    templates_base = await create_template_directories()
    print(f"Template directories created at: {templates_base}")
    
    print("Seeding templates to database...")
    async with async_session_maker() as db:
        count = await seed_templates(db)
        print(f"Created {count} new templates")
    
    print("Template seeding complete!")


if __name__ == "__main__":
    asyncio.run(run_seeder())
