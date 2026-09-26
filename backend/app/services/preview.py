"""
Universal Document Preview Service.

Supports preview generation for all document types:
- PDF
- Word (DOCX, DOC)
- Excel (XLSX, XLS)
- PowerPoint (PPTX, PPT)
- Images (PNG, JPG, GIF, BMP, WebP)
- Text files (TXT, MD, JSON, XML, CSV)
- Code files (PY, JS, HTML, CSS, etc.)
"""

import asyncio
import base64
import io
import json
import mimetypes
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field

# Initialize mimetypes
mimetypes.init()


@dataclass
class PreviewResult:
    """Result of preview generation."""
    success: bool
    preview_type: str  # image, pdf, html, text, json, office
    content: str | bytes | None = None  # Base64 for binary, raw for text
    content_url: str | None = None  # URL if stored as file
    pages: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "preview_type": self.preview_type,
            "content": self.content if isinstance(self.content, str) else None,
            "content_url": self.content_url,
            "pages": self.pages,
            "metadata": self.metadata,
            "error": self.error,
        }


class UniversalPreviewService:
    """
    Generate previews for any document type.
    
    Strategy:
    - Images: Send directly or resize
    - PDF: Send directly for browser rendering
    - Office docs: Convert to PDF or extract images
    - Text/Code: Syntax highlight and return HTML
    - JSON: Pretty print
    - Excel: Convert to HTML table
    """
    
    # File type mappings
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', '.ico'}
    PDF_EXTENSIONS = {'.pdf'}
    WORD_EXTENSIONS = {'.doc', '.docx', '.odt', '.rtf'}
    EXCEL_EXTENSIONS = {'.xls', '.xlsx', '.ods', '.csv'}
    POWERPOINT_EXTENSIONS = {'.ppt', '.pptx', '.odp'}
    TEXT_EXTENSIONS = {'.txt', '.md', '.log', '.ini', '.cfg', '.env'}
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.htm', '.css', '.scss',
        '.json', '.xml', '.yaml', '.yml', '.toml', '.sql', '.sh', '.bash',
        '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb',
        '.php', '.swift', '.kt', '.r', '.m', '.mm',
    }
    
    def __init__(self, preview_cache_dir: Path | None = None):
        self.cache_dir = preview_cache_dir or Path(tempfile.gettempdir()) / "doc_previews"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_preview(
        self,
        file_path: Path | str,
        max_width: int = 1200,
        max_height: int = 1600,
        page: int = 1,
    ) -> PreviewResult:
        """
        Generate a preview for any supported file type.
        
        Args:
            file_path: Path to the file
            max_width: Maximum width for image previews
            max_height: Maximum height for image previews
            page: Page number for multi-page documents
            
        Returns:
            PreviewResult with preview data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return PreviewResult(
                success=False,
                preview_type="error",
                error=f"File not found: {file_path}",
            )
        
        ext = file_path.suffix.lower()
        
        try:
            if ext in self.IMAGE_EXTENSIONS:
                return await self._preview_image(file_path, max_width, max_height)
            
            elif ext in self.PDF_EXTENSIONS:
                return await self._preview_pdf(file_path, page)
            
            elif ext in self.WORD_EXTENSIONS:
                return await self._preview_word(file_path, page)
            
            elif ext in self.EXCEL_EXTENSIONS:
                return await self._preview_excel(file_path)
            
            elif ext in self.POWERPOINT_EXTENSIONS:
                return await self._preview_powerpoint(file_path, page)
            
            elif ext in self.TEXT_EXTENSIONS:
                return await self._preview_text(file_path)
            
            elif ext in self.CODE_EXTENSIONS:
                return await self._preview_code(file_path)
            
            elif ext == '.json':
                return await self._preview_json(file_path)
            
            else:
                # Try to detect type from content
                return await self._preview_unknown(file_path)
                
                
        except Exception as e:
            print(f"DEBUG: Preview generation error for {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return PreviewResult(
                success=False,
                preview_type="error",
                error=str(e),
            )
    
    async def _preview_image(
        self,
        file_path: Path,
        max_width: int,
        max_height: int,
    ) -> PreviewResult:
        """Preview image files."""
        try:
            from PIL import Image
            
            with Image.open(file_path) as img:
                # Get original dimensions
                orig_width, orig_height = img.size
                
                # Resize if needed
                if orig_width > max_width or orig_height > max_height:
                    img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Convert to base64
                buffer = io.BytesIO()
                
                # Handle format
                format = img.format or 'PNG'
                if format == 'JPEG':
                    img.save(buffer, format='JPEG', quality=85)
                elif format == 'GIF':
                    img.save(buffer, format='GIF')
                else:
                    img.save(buffer, format='PNG')
                
                buffer.seek(0)
                content = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                mime_type = mimetypes.guess_type(file_path)[0] or 'image/png'
                
                return PreviewResult(
                    success=True,
                    preview_type="image",
                    content=f"data:{mime_type};base64,{content}",
                    metadata={
                        "original_width": orig_width,
                        "original_height": orig_height,
                        "width": img.size[0],
                        "height": img.size[1],
                        "format": format,
                    },
                )
                
        except ImportError:
            # Fallback: return file as-is
            with open(file_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            
            mime_type = mimetypes.guess_type(file_path)[0] or 'image/png'
            
            return PreviewResult(
                success=True,
                preview_type="image",
                content=f"data:{mime_type};base64,{content}",
            )
    
    async def _preview_pdf(self, file_path: Path, page: int = 1) -> PreviewResult:
        """Preview PDF files."""
        try:
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            total_pages = len(doc)
            
            # Clamp page number
            page_idx = max(0, min(page - 1, total_pages - 1))
            
            # Render page as image
            pdf_page = doc[page_idx]
            mat = fitz.Matrix(2, 2)  # 2x zoom for quality
            pix = pdf_page.get_pixmap(matrix=mat)
            
            img_data = pix.tobytes("png")
            content = base64.b64encode(img_data).decode('utf-8')
            
            doc.close()
            
            return PreviewResult(
                success=True,
                preview_type="pdf",
                content=f"data:image/png;base64,{content}",
                pages=total_pages,
                metadata={
                    "current_page": page,
                    "width": pix.width,
                    "height": pix.height,
                },
            )
            
        except ImportError:
            # Fallback: return PDF as-is for browser rendering
            with open(file_path, 'rb') as f:
                content = base64.b64encode(f.read()).decode('utf-8')
            
            return PreviewResult(
                success=True,
                preview_type="pdf",
                content=f"data:application/pdf;base64,{content}",
                metadata={"note": "Direct PDF, install PyMuPDF for page rendering"},
            )
    
    async def _preview_word(self, file_path: Path, page: int = 1) -> PreviewResult:
        """Preview Word documents."""
        try:
            from docx import Document
            from docx.shared import Inches
            
            doc = Document(file_path)
            
            # Extract content as HTML
            html_parts = ['<div class="word-preview">']
            
            for para in doc.paragraphs:
                style = para.style.name.lower() if para.style else ''
                
                if 'heading 1' in style:
                    html_parts.append(f'<h1>{para.text}</h1>')
                elif 'heading 2' in style:
                    html_parts.append(f'<h2>{para.text}</h2>')
                elif 'heading 3' in style:
                    html_parts.append(f'<h3>{para.text}</h3>')
                else:
                    if para.text.strip():
                        html_parts.append(f'<p>{para.text}</p>')
            
            # Handle tables
            for table in doc.tables:
                html_parts.append('<table class="word-table">')
                for row in table.rows:
                    html_parts.append('<tr>')
                    for cell in row.cells:
                        html_parts.append(f'<td>{cell.text}</td>')
                    html_parts.append('</tr>')
                html_parts.append('</table>')
            
            html_parts.append('</div>')
            
            return PreviewResult(
                success=True,
                preview_type="html",
                content='\n'.join(html_parts),
                metadata={
                    "paragraphs": len(doc.paragraphs),
                    "tables": len(doc.tables),
                },
            )
            
            
        except ImportError:
            print(f"DEBUG: python-docx not installed")
            return PreviewResult(
                success=False,
                preview_type="error",
                error="python-docx library not installed",
            )
        except Exception as e:
            print(f"DEBUG: Word preview error: {e}")
            import traceback
            traceback.print_exc()
            return PreviewResult(
                success=False,
                preview_type="error",
                error=str(e),
            )
    
    async def _preview_excel(self, file_path: Path) -> PreviewResult:
        """Preview Excel/CSV files as HTML table."""
        ext = file_path.suffix.lower()
        
        try:
            if ext == '.csv':
                import csv
                
                rows = []
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    reader = csv.reader(f)
                    for i, row in enumerate(reader):
                        if i >= 100:  # Limit rows
                            break
                        rows.append(row)
                
                sheets = [{"name": "Sheet1", "rows": rows}]
                
            else:
                try:
                    import openpyxl
                    
                    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
                    sheets = []
                    
                    for sheet_name in wb.sheetnames[:5]:  # Limit sheets
                        sheet = wb[sheet_name]
                        rows = []
                        
                        for i, row in enumerate(sheet.iter_rows(values_only=True)):
                            if i >= 100:  # Limit rows
                                break
                            rows.append([str(cell) if cell is not None else '' for cell in row[:20]])  # Limit columns
                        
                        sheets.append({"name": sheet_name, "rows": rows})
                    
                    wb.close()
                    
                except ImportError:
                    return PreviewResult(
                        success=False,
                        preview_type="error",
                        error="openpyxl library not installed",
                    )
            
            # Convert to HTML
            html_parts = ['<div class="excel-preview">']
            
            for sheet in sheets:
                html_parts.append(f'<h4 class="sheet-name">{sheet["name"]}</h4>')
                html_parts.append('<table class="excel-table">')
                
                for i, row in enumerate(sheet["rows"]):
                    html_parts.append('<tr>')
                    tag = 'th' if i == 0 else 'td'
                    for cell in row:
                        html_parts.append(f'<{tag}>{cell}</{tag}>')
                    html_parts.append('</tr>')
                
                html_parts.append('</table>')
            
            html_parts.append('</div>')
            
            return PreviewResult(
                success=True,
                preview_type="html",
                content='\n'.join(html_parts),
                metadata={
                    "sheets": len(sheets),
                    "total_rows": sum(len(s["rows"]) for s in sheets),
                },
            )
            
        except Exception as e:
            return PreviewResult(
                success=False,
                preview_type="error",
                error=str(e),
            )
    
    async def _preview_powerpoint(self, file_path: Path, page: int = 1) -> PreviewResult:
        """Preview PowerPoint files."""
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt
            
            prs = Presentation(file_path)
            total_slides = len(prs.slides)
            
            slide_idx = max(0, min(page - 1, total_slides - 1))
            slide = prs.slides[slide_idx]
            
            # Extract text content
            content_parts = ['<div class="pptx-slide">']
            
            for shape in slide.shapes:
                if hasattr(shape, 'text') and shape.text.strip():
                    # Check if it's a title
                    if shape.is_placeholder and hasattr(shape, 'placeholder_format'):
                        if shape.placeholder_format.type == 1:  # Title
                            content_parts.append(f'<h2 class="slide-title">{shape.text}</h2>')
                        else:
                            content_parts.append(f'<p>{shape.text}</p>')
                    else:
                        content_parts.append(f'<p>{shape.text}</p>')
                
                # Handle images
                if shape.shape_type == 13:  # Picture
                    try:
                        image = shape.image
                        img_data = base64.b64encode(image.blob).decode('utf-8')
                        content_type = image.content_type
                        content_parts.append(
                            f'<img src="data:{content_type};base64,{img_data}" '
                            f'style="max-width: 100%; height: auto;" />'
                        )
                    except Exception:
                        pass
            
            content_parts.append('</div>')
            
            # Get slide notes if available
            notes = ""
            if slide.has_notes_slide:
                notes = slide.notes_slide.notes_text_frame.text
            
            return PreviewResult(
                success=True,
                preview_type="html",
                content='\n'.join(content_parts),
                pages=total_slides,
                metadata={
                    "current_slide": page,
                    "notes": notes,
                    "total_shapes": len(slide.shapes),
                },
            )
            
        except ImportError:
            return PreviewResult(
                success=False,
                preview_type="error",
                error="python-pptx library not installed",
            )
    
    async def _preview_text(self, file_path: Path) -> PreviewResult:
        """Preview text files."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(100000)  # Limit to 100KB
            
            # Check if truncated
            full_size = file_path.stat().st_size
            truncated = full_size > 100000
            
            return PreviewResult(
                success=True,
                preview_type="text",
                content=content,
                metadata={
                    "size": full_size,
                    "truncated": truncated,
                    "lines": content.count('\n') + 1,
                },
            )
            
        except Exception as e:
            return PreviewResult(
                success=False,
                preview_type="error",
                error=str(e),
            )
    
    async def _preview_code(self, file_path: Path) -> PreviewResult:
        """Preview code files with syntax highlighting."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(100000)
            
            ext = file_path.suffix.lower()
            
            # Map extension to language
            lang_map = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.jsx': 'jsx', '.tsx': 'tsx', '.html': 'html', '.htm': 'html',
                '.css': 'css', '.scss': 'scss', '.json': 'json', '.xml': 'xml',
                '.yaml': 'yaml', '.yml': 'yaml', '.sql': 'sql', '.sh': 'bash',
                '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.go': 'go',
                '.rs': 'rust', '.rb': 'ruby', '.php': 'php', '.swift': 'swift',
            }
            
            language = lang_map.get(ext, 'text')
            
            try:
                from pygments import highlight
                from pygments.lexers import get_lexer_by_name
                from pygments.formatters import HtmlFormatter
                
                lexer = get_lexer_by_name(language)
                formatter = HtmlFormatter(linenos=True, cssclass="code-preview")
                
                highlighted = highlight(content, lexer, formatter)
                css = formatter.get_style_defs('.code-preview')
                
                html_content = f'<style>{css}</style>{highlighted}'
                
                return PreviewResult(
                    success=True,
                    preview_type="html",
                    content=html_content,
                    metadata={
                        "language": language,
                        "lines": content.count('\n') + 1,
                    },
                )
                
            except ImportError:
                # Fallback: plain text with line numbers
                lines = content.split('\n')
                html_lines = []
                for i, line in enumerate(lines, 1):
                    escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html_lines.append(f'<span class="line-no">{i:4d}</span> {escaped}')
                
                html_content = f'<pre class="code-preview">{chr(10).join(html_lines)}</pre>'
                
                return PreviewResult(
                    success=True,
                    preview_type="html",
                    content=html_content,
                    metadata={"language": language},
                )
                
        except Exception as e:
            return PreviewResult(
                success=False,
                preview_type="error",
                error=str(e),
            )
    
    async def _preview_json(self, file_path: Path) -> PreviewResult:
        """Preview JSON files with pretty formatting."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Apply syntax highlighting if available
            try:
                from pygments import highlight
                from pygments.lexers import JsonLexer
                from pygments.formatters import HtmlFormatter
                
                formatter = HtmlFormatter(cssclass="json-preview")
                highlighted = highlight(pretty, JsonLexer(), formatter)
                css = formatter.get_style_defs('.json-preview')
                
                html_content = f'<style>{css}</style>{highlighted}'
                
                return PreviewResult(
                    success=True,
                    preview_type="html",
                    content=html_content,
                    metadata={
                        "type": type(data).__name__,
                        "keys": list(data.keys())[:10] if isinstance(data, dict) else None,
                        "length": len(data) if isinstance(data, (list, dict)) else None,
                    },
                )
                
            except ImportError:
                return PreviewResult(
                    success=True,
                    preview_type="json",
                    content=pretty,
                    metadata={
                        "type": type(data).__name__,
                    },
                )
                
        except json.JSONDecodeError as e:
            return PreviewResult(
                success=False,
                preview_type="error",
                error=f"Invalid JSON: {e}",
            )
    
    async def _preview_unknown(self, file_path: Path) -> PreviewResult:
        """Try to preview unknown file types."""
        # Try to read as text
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1024)
            
            # Check if it's likely text
            try:
                sample.decode('utf-8')
                # Seems like text, preview as text
                return await self._preview_text(file_path)
            except UnicodeDecodeError:
                pass
            
            # Check for common binary signatures
            if sample.startswith(b'%PDF'):
                return await self._preview_pdf(file_path)
            elif sample.startswith(b'PK'):
                # Could be DOCX, XLSX, PPTX, ZIP
                if file_path.suffix.lower() in self.WORD_EXTENSIONS:
                    return await self._preview_word(file_path)
                elif file_path.suffix.lower() in self.EXCEL_EXTENSIONS:
                    return await self._preview_excel(file_path)
                elif file_path.suffix.lower() in self.POWERPOINT_EXTENSIONS:
                    return await self._preview_powerpoint(file_path)
            
            # Return basic info
            return PreviewResult(
                success=True,
                preview_type="binary",
                content=None,
                metadata={
                    "size": file_path.stat().st_size,
                    "mime_type": mimetypes.guess_type(file_path)[0],
                    "message": "Binary file - no preview available",
                },
            )
            
        except Exception as e:
            return PreviewResult(
                success=False,
                preview_type="error",
                error=str(e),
            )
    
    async def get_editable_content(self, file_path: Path) -> dict:
        """
        Get editable content for a document.
        
        Returns structured data that can be edited and saved back.
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext in self.TEXT_EXTENSIONS | self.CODE_EXTENSIONS | {'.json'}:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "type": "text",
                "content": content,
                "editable": True,
            }
        
        elif ext in self.WORD_EXTENSIONS:
            try:
                from docx import Document
                
                doc = Document(file_path)
                paragraphs = []
                
                for para in doc.paragraphs:
                    paragraphs.append({
                        "text": para.text,
                        "style": para.style.name if para.style else "Normal",
                    })
                
                return {
                    "type": "word",
                    "paragraphs": paragraphs,
                    "editable": True,
                }
                
            except ImportError:
                return {"type": "error", "error": "python-docx not installed", "editable": False}
        
        elif ext in self.EXCEL_EXTENSIONS:
            try:
                import openpyxl
                
                wb = openpyxl.load_workbook(file_path)
                sheets = {}
                
                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    cells = {}
                    
                    for row in sheet.iter_rows():
                        for cell in row:
                            if cell.value is not None:
                                cells[f"{cell.column_letter}{cell.row}"] = {
                                    "value": cell.value,
                                    "formula": cell.value if str(cell.value).startswith('=') else None,
                                }
                    
                    sheets[sheet_name] = cells
                
                return {
                    "type": "excel",
                    "sheets": sheets,
                    "editable": True,
                }
                
            except ImportError:
                return {"type": "error", "error": "openpyxl not installed", "editable": False}
        
        return {
            "type": "unsupported",
            "editable": False,
        }
    
    async def save_editable_content(
        self,
        file_path: Path,
        content: dict,
    ) -> bool:
        """Save edited content back to file."""
        file_path = Path(file_path)
        content_type = content.get("type")
        
        try:
            if content_type == "text":
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content.get("content", ""))
                return True
            
            elif content_type == "word":
                from docx import Document
                
                doc = Document()
                for para in content.get("paragraphs", []):
                    p = doc.add_paragraph(para.get("text", ""))
                    # Could apply styles here
                
                doc.save(file_path)
                return True
            
            elif content_type == "excel":
                import openpyxl
                
                wb = openpyxl.Workbook()
                
                for i, (sheet_name, cells) in enumerate(content.get("sheets", {}).items()):
                    if i == 0:
                        ws = wb.active
                        ws.title = sheet_name
                    else:
                        ws = wb.create_sheet(sheet_name)
                    
                    for cell_ref, cell_data in cells.items():
                        ws[cell_ref] = cell_data.get("value")
                
                wb.save(file_path)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error saving content: {e}")
            return False


# Global instance
preview_service = UniversalPreviewService()
