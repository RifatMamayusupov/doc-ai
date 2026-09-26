"""Template model for document templates."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Template(Base):
    """Document template for organizations."""

    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    
    # Template info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Organization/category
    organization: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # e.g., "bank", "government", "company"
    
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )  # e.g., "report", "invoice", "contract"
    
    # File paths
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    preview_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Template schema (field definitions for auto-fill)
    schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    # Example schema:
    # {
    #     "fields": [
    #         {"name": "company_name", "type": "string", "required": true},
    #         {"name": "date", "type": "date", "required": true},
    #         {"name": "amount", "type": "number", "required": false}
    #     ]
    # }
    
    # Tags for search
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Template {self.name} ({self.organization})>"
