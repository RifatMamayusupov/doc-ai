"""
Monister Database - SQLite + SQLAlchemy models for users and files.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pathlib import Path

# Database location
DATABASE_PATH = Path(__file__).parent.parent / "data" / "monister.db"
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    telegram_username = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "telegram_username": self.telegram_username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "files_count": len(self.files) if self.files else 0,
        }


class File(Base):
    """File model for tracking user uploads."""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # images, documents, spreadsheets, generated, other
    mime_type = Column(String(100), nullable=True)
    path = Column(String(500), nullable=False)
    size = Column(BigInteger, default=0)  # bytes
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="files")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.owner.username if self.owner else None,
            "filename": self.filename,
            "original_name": self.original_name,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "path": self.path,
            "size": self.size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Database dependency for FastAPI
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and migrate missing columns."""
    Base.metadata.create_all(bind=engine)
    _migrate_missing_columns()


def _migrate_missing_columns():
    """Auto-add missing columns to existing tables (lightweight migration)."""
    import sqlalchemy
    inspector = sqlalchemy.inspect(engine)
    
    for table_name, model in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            continue
        existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
        for column in model.columns:
            if column.name not in existing_columns:
                col_type = column.type.compile(dialect=engine.dialect)
                nullable = "" if column.nullable else " NOT NULL"
                default = ""
                if column.default is not None:
                    default = f" DEFAULT {column.default.arg!r}"
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{nullable}{default}"
                try:
                    with engine.begin() as conn:
                        conn.execute(sqlalchemy.text(sql))
                    print(f"✅ Migrated: {table_name}.{column.name} ({col_type})")
                except Exception as e:
                    print(f"⚠️ Migration skip {table_name}.{column.name}: {e}")


# File type categorization
def get_file_category(filename: str, mime_type: str = None) -> str:
    """Determine file category based on extension or mime type."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    image_exts = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico'}
    document_exts = {'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'}
    spreadsheet_exts = {'xlsx', 'xls', 'csv', 'ods'}
    code_exts = {'py', 'js', 'ts', 'html', 'css', 'json', 'xml', 'md'}
    
    if ext in image_exts:
        return 'images'
    elif ext in document_exts:
        return 'documents'
    elif ext in spreadsheet_exts:
        return 'spreadsheets'
    elif ext in code_exts:
        return 'code'
    else:
        return 'other'


# NOTE: init_db() is called explicitly from main.py startup, not at import time.
