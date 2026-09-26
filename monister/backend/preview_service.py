"""
Monister Preview Service - Unified document preview and auto-display system.

Handles:
- File path detection from tool outputs
- URL generation for different storage locations
- File type detection and classification
- Auto-preview triggering for generated documents
- Conflict-free preview queue management
"""

import ast
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field

from config import settings


# ============== Data Classes ==============

@dataclass
class PreviewResult:
    """Result of preview processing."""
    has_file: bool = False
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_type: str = "file"
    tool_name: str = ""
    data_summary: str = ""
    description: str = ""
    was_moved: bool = False
    new_path: Optional[str] = None
    db_file_info: Optional[dict] = None


@dataclass
class PreviewEvent:
    """WebSocket event for preview display."""
    type: str = "data_preview"
    tool_name: str = ""
    data: str = ""
    node_id: str = ""
    url: Optional[str] = None
    file_type: Optional[str] = None
    description: str = ""
    auto_open: bool = False
    has_file: bool = False

    def to_dict(self) -> dict:
        d = {
            "type": self.type,
            "tool_name": self.tool_name,
            "data": self.data,
            "node_id": self.node_id,
            "description": self.description,
            "auto_open": self.auto_open,
        }
        if self.url:
            d["url"] = self.url
        if self.file_type:
            d["file_type"] = self.file_type
        return d


# ============== File Type Detection ==============

# Extension → type mapping
FILE_TYPE_MAP = {
    # Images
    '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
    '.bmp': 'image', '.webp': 'image', '.svg': 'image',
    # Documents
    '.pdf': 'pdf', '.doc': 'docx', '.docx': 'docx',
    '.txt': 'text', '.md': 'text', '.rtf': 'text',
    # Spreadsheets
    '.xlsx': 'excel', '.xls': 'excel', '.csv': 'excel', '.ods': 'excel',
    # Web
    '.html': 'html', '.htm': 'html', '.jinja2': 'html',
    # Code
    '.py': 'code', '.js': 'code', '.ts': 'code', '.css': 'code',
    '.json': 'code', '.xml': 'code', '.yaml': 'code', '.yml': 'code',
    '.sql': 'code',
    # Presentations
    '.ppt': 'presentation', '.pptx': 'presentation',
    # Video
    '.mp4': 'video', '.avi': 'video', '.mov': 'video', '.webm': 'video',
    # Audio
    '.mp3': 'audio', '.wav': 'audio', '.ogg': 'audio',
    # Archives
    '.zip': 'archive', '.rar': 'archive', '.7z': 'archive',
    '.tar': 'archive', '.gz': 'archive',
}

# File extensions regex pattern
FILE_EXT_PATTERN = '|'.join(
    ext.lstrip('.') for ext in FILE_TYPE_MAP.keys()
)
FILE_PATH_REGEX = re.compile(
    rf'[\w\-\.\\//:]+\.(?:{FILE_EXT_PATTERN})',
    re.IGNORECASE
)

# Category mapping for file organization
FILE_CATEGORY_MAP = {
    'image': 'images', 'pdf': 'documents', 'docx': 'documents',
    'text': 'documents', 'excel': 'spreadsheets', 'html': 'documents',
    'code': 'code', 'presentation': 'documents', 'video': 'media',
    'audio': 'media', 'archive': 'other', 'file': 'other',
}

# Tools that generate files (auto-open preview)
FILE_GENERATING_TOOLS = {
    'fill_template', 'clean_data', 'parse_excel', 'ocr_extract',
    'batch_generate', 'translate_document', 'compare_documents',
    'write_file', 'shell',
}

# Tool descriptions for chat display
TOOL_DESCRIPTIONS = {
    'fill_template': '📝 Shablon to\'ldirildi',
    'clean_data': '🧹 Ma\'lumotlar tozalandi',
    'parse_excel': '📊 Excel tahlil qilindi',
    'ocr_extract': '🔍 Matn ajratib olindi (OCR)',
    'redact_pii': '🔒 Shaxsiy ma\'lumotlar yashirildi',
    'batch_generate': '📦 Ommaviy hujjatlar yaratildi',
    'translate_document': '🌍 Hujjat tarjima qilindi',
    'compare_documents': '📊 Hujjatlar solishtirildi',
    'check_compliance': '✅ Muvofiqlik tekshirildi',
    'execute_code': '🐍 Kod bajarildi',
    'write_file': '💾 Fayl yaratildi',
    'shell': '⚡ Buyruq bajarildi',
}


def detect_file_type(file_path: str) -> str:
    """Detect file type from extension."""
    ext = Path(file_path).suffix.lower()
    return FILE_TYPE_MAP.get(ext, 'file')


def get_file_category(file_type: str) -> str:
    """Get storage category for a file type."""
    return FILE_CATEGORY_MAP.get(file_type, 'other')


def get_tool_description(tool_name: str, output_data: dict = None) -> str:
    """Generate a human-readable description for tool output."""
    base = TOOL_DESCRIPTIONS.get(tool_name, f'🔧 {tool_name} bajarildi')

    if not output_data:
        return base

    # Add details based on output
    details = []
    if 'output_path' in output_data:
        fname = Path(str(output_data['output_path'])).name
        details.append(f"→ {fname}")
    if 'filled_fields' in output_data:
        count = len(output_data['filled_fields'])
        details.append(f"({count} ta maydon to'ldirildi)")
    if 'rows_cleaned' in output_data:
        details.append(f"({output_data['rows_cleaned']} qator tozalandi)")
    if 'text' in output_data and len(str(output_data['text'])) > 0:
        text_len = len(str(output_data['text']))
        details.append(f"({text_len} belgi ajratildi)")

    if details:
        return f"{base} {' '.join(details)}"
    return base


# ============== Path Resolution ==============

def normalize_path(raw_path: str) -> str:
    """Normalize a file path, handling WSL paths on Windows."""
    clean = raw_path.strip()
    if sys.platform == 'win32' and clean.startswith('/mnt/'):
        parts = clean.split('/')
        if len(parts) > 2 and len(parts[2]) == 1:
            clean = f"{parts[2]}:/{'/'.join(parts[3:])}"
    return str(Path(clean))


def find_file_path(raw_output: str, output_data: dict = None,
                   file_contexts: list[dict] = None) -> Optional[str]:
    """
    Find a valid file path from tool output.

    Strategy:
    1. Check dict keys (path, file_path, output_path, output)
    2. Regex scan of raw output for file paths
    3. Check known directories (uploads, templates, data)
    4. Fallback: check file context references
    """
    # 1. Direct dict key check
    if output_data and isinstance(output_data, dict):
        for key in ('output_path', 'path', 'file_path', 'output'):
            val = output_data.get(key)
            if val and isinstance(val, str):
                normalized = normalize_path(val)
                if os.path.exists(normalized):
                    return normalized

    # 2. Regex scan for file paths
    candidates = FILE_PATH_REGEX.findall(raw_output)
    for cand in candidates:
        cand = cand.strip().rstrip('.')
        normalized = normalize_path(cand)

        if os.path.exists(normalized):
            return normalized

        # Check in known directories
        fname = Path(cand).name
        for search_dir in [settings.uploads_dir, settings.templates_dir, settings.data_dir]:
            if (search_dir / fname).exists():
                return str(search_dir / fname)
            # Recursive search in templates
            try:
                found = list(search_dir.rglob(fname))
                if found:
                    return str(found[0])
            except Exception:
                pass

    # 3. Check file context references
    if file_contexts:
        output_lower = raw_output.lower()
        for fc in file_contexts:
            fc_filename = fc.get("filename", "").lower()
            fc_path = fc.get("path", "")
            if fc_filename and fc_filename in output_lower:
                if fc_path and os.path.exists(fc_path):
                    return fc_path

    return None


def generate_file_url(file_path: str, base_url: str = "http://localhost:8000") -> Optional[str]:
    """Generate a URL for serving a file."""
    try:
        file_str = str(file_path).replace('\\', '/')
        fname = Path(file_path).name

        # Try relative_to with resolved paths first
        try:
            f_path = Path(file_path).resolve()
            dir_mappings = [
                (settings.data_dir.resolve(), "/data/"),
                (settings.uploads_dir.resolve(), "/uploads/"),
                (settings.templates_dir.resolve(), "/templates/"),
            ]
            for dir_path, url_prefix in dir_mappings:
                try:
                    if str(dir_path) in str(f_path):
                        rel = f_path.relative_to(dir_path).as_posix()
                        return f"{base_url}{url_prefix}{rel}"
                except (ValueError, TypeError):
                    continue
        except Exception:
            pass

        # Fallback: string-based detection (handles WSL paths, mixed slashes, etc.)
        if "uploads" in file_str.lower():
            return f"{base_url}/uploads/{fname}"
        if "templates" in file_str.lower():
            return f"{base_url}/templates/{fname}"
        if "data" in file_str.lower():
            return f"{base_url}/data/{fname}"

        # Last resort: serve from uploads
        if os.path.exists(file_path):
            return f"{base_url}/uploads/{fname}"

    except Exception as e:
        print(f"URL generation error: {e}")

    return None


# ============== File Organization ==============

def move_to_user_folder(
    file_path: str,
    username: str,
    user_id: int,
) -> Optional[dict]:
    """
    Move a generated file to the user's organized folder.

    Returns dict with new path info, or None if failed.
    """
    if not os.path.exists(file_path):
        return None

    try:
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_type = detect_file_type(file_path)
        category = get_file_category(file_type)

        user_dir = settings.data_dir / username / date_str / "generated" / category
        user_dir.mkdir(parents=True, exist_ok=True)

        new_filename = f"gen_{uuid.uuid4().hex[:8]}_{Path(file_path).name}"
        new_path = user_dir / new_filename

        shutil.move(file_path, new_path)

        return {
            "new_path": str(new_path),
            "new_filename": new_filename,
            "category": category,
            "file_type": file_type,
            "size": os.path.getsize(new_path),
            "url": f"/data/{username}/{date_str}/generated/{category}/{new_filename}",
            "user_id": user_id,
        }
    except Exception as e:
        print(f"File move error: {e}")
        return None


# ============== Preview Processing ==============

def parse_tool_output(output: Any) -> dict:
    """Parse tool output string into a dict."""
    if isinstance(output, dict):
        return output
    if isinstance(output, str):
        try:
            return ast.literal_eval(output)
        except Exception:
            try:
                return json.loads(output)
            except Exception:
                return {}
    return {}


async def process_tool_preview(
    tool_name: str,
    output: Any,
    client_id: str,
    file_contexts: list[dict] = None,
    user: dict = None,
    send_fn: Callable[[str, dict], Awaitable[None]] = None,
    db_save_fn: Callable[[dict], None] = None,
) -> PreviewEvent:
    """
    Process a tool's output and generate preview event.

    This is the main entry point for the preview system.
    Returns a PreviewEvent ready to send to the frontend.
    """
    raw_output = str(output)[:2000]
    output_data = parse_tool_output(output)

    print(f"[PREVIEW] Tool: {tool_name}, output_data keys: {list(output_data.keys()) if isinstance(output_data, dict) else 'not-dict'}")

    # Build preview event
    event = PreviewEvent(
        tool_name=tool_name,
        data=raw_output[:1000],
        node_id=tool_name,
        description=get_tool_description(tool_name, output_data),
        auto_open=True,  # Always auto-open — let frontend decide visibility
    )

    # Try to find file path
    file_path = find_file_path(raw_output, output_data, file_contexts)
    print(f"[PREVIEW] Found file_path: {file_path}")

    if file_path and os.path.exists(file_path):
        file_path = str(Path(file_path))  # Normalize
        event.file_type = detect_file_type(file_path)
        event.has_file = True

        # Move to user folder if authenticated
        if user and "uploads" in file_path.replace('\\', '/').lower():
            move_result = move_to_user_folder(
                file_path,
                user.get("username", "anonymous"),
                int(user.get("id", 0)),
            )
            if move_result:
                file_path = move_result["new_path"]
                event.url = f"http://localhost:8000{move_result['url']}"
                print(f"[PREVIEW] Moved to user folder, URL: {event.url}")

                # Save to DB
                if db_save_fn:
                    try:
                        db_save_fn(move_result)
                    except Exception as e:
                        print(f"DB save error: {e}")

                # Notify frontend about new file
                if send_fn:
                    await send_fn(client_id, {
                        "type": "file_upload",
                        "file_id": f"gen-{uuid.uuid4().hex[:8]}",
                        "filename": move_result["new_filename"],
                        "path": move_result["new_path"],
                        "size": move_result["size"],
                        "file_type": move_result["category"],
                    })

        # Generate URL if not already set
        if not event.url:
            event.url = generate_file_url(file_path)
            print(f"[PREVIEW] Generated URL: {event.url}")

    else:
        print(f"[PREVIEW] No file found or doesn't exist: file_path={file_path}")

    print(f"[PREVIEW] Final event: url={event.url}, file_type={event.file_type}, auto_open={event.auto_open}")
    return event


async def process_text_preview(
    text_content: str,
    client_id: str,
    send_fn: Callable[[str, dict], Awaitable[None]] = None,
) -> Optional[PreviewEvent]:
    """
    Scan agent text response for file paths and trigger preview.
    Returns PreviewEvent if a file was found, None otherwise.
    """
    if not text_content or len(text_content) < 10:
        return None

    matches = FILE_PATH_REGEX.findall(text_content)
    for match in matches:
        match = match.strip()
        normalized = normalize_path(match)

        if os.path.exists(normalized):
            file_type = detect_file_type(normalized)
            url = generate_file_url(normalized)

            if url:
                event = PreviewEvent(
                    tool_name="file_display",
                    data=f"Fayl: {Path(normalized).name}",
                    node_id="file_display",
                    url=url,
                    file_type=file_type,
                    description=f"📄 {Path(normalized).name}",
                    auto_open=True,
                )

                if send_fn:
                    await send_fn(client_id, event.to_dict())

                return event

    return None


# ============== Exports ==============
__all__ = [
    "PreviewResult",
    "PreviewEvent",
    "detect_file_type",
    "get_file_category",
    "get_tool_description",
    "normalize_path",
    "find_file_path",
    "generate_file_url",
    "move_to_user_folder",
    "parse_tool_output",
    "process_tool_preview",
    "process_text_preview",
    "FILE_GENERATING_TOOLS",
    "TOOL_DESCRIPTIONS",
]
