"""
Monister Template Engine - Document template management and auto-fill.

Supports:
- DOCX templates with {{placeholders}}
- PDF generation
- Excel templates
- Smart field extraction
"""

import re
from pathlib import Path
from typing import Any

from config import settings


def get_template_fields(template_path: str) -> list[str]:
    """
    Extract placeholder fields from a template.
    
    Looks for {{field_name}} patterns in the document.
    """
    path = Path(template_path)
    fields = []
    
    if not path.exists():
        return fields
    
    try:
        if path.suffix.lower() == '.docx':
            try:
                from docx import Document
                doc = Document(path)
                
                # Extract from paragraphs
                for para in doc.paragraphs:
                    matches = re.findall(r'\{\{(\w+)\}\}', para.text)
                    fields.extend(matches)
                
                # Extract from tables
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            matches = re.findall(r'\{\{(\w+)\}\}', cell.text)
                            fields.extend(matches)
            except ImportError:
                pass
        
        elif path.suffix.lower() in ['.jinja2', '.html', '.txt']:
            content = path.read_text(encoding='utf-8')
            matches = re.findall(r'\{\{(\w+)\}\}', content)
            fields.extend(matches)
        
        elif path.suffix.lower() == '.xlsx':
            try:
                import openpyxl
                wb = openpyxl.load_workbook(path)
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows():
                        for cell in row:
                            if cell.value and isinstance(cell.value, str):
                                matches = re.findall(r'\{\{(\w+)\}\}', cell.value)
                                fields.extend(matches)
            except ImportError:
                pass
    
    except Exception as e:
        print(f"Error extracting fields: {e}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_fields = []
    for f in fields:
        if f not in seen:
            seen.add(f)
            unique_fields.append(f)
    
    return unique_fields


def fill_docx_template(template_path: str, data: dict[str, Any], output_path: str) -> str:
    """
    Fill a DOCX template with data.
    
    Args:
        template_path: Path to the .docx template
        data: Dictionary of field_name: value pairs
        output_path: Path for the output file
        
    Returns:
        Path to the filled document
    """
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError("python-docx is required: pip install python-docx")
    
    doc = Document(template_path)
    
    # Replace in paragraphs
    for para in doc.paragraphs:
        for field, value in data.items():
            placeholder = f"{{{{{field}}}}}"
            if placeholder in para.text:
                para.text = para.text.replace(placeholder, str(value))
    
    # Replace in tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for field, value in data.items():
                    placeholder = f"{{{{{field}}}}}"
                    if placeholder in cell.text:
                        cell.text = cell.text.replace(placeholder, str(value))
    
    doc.save(output_path)
    return output_path


def fill_excel_template(template_path: str, data: dict[str, Any], output_path: str) -> str:
    """
    Fill an Excel template with data.
    """
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl is required: pip install openpyxl")
    
    wb = openpyxl.load_workbook(template_path)
    
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    for field, value in data.items():
                        placeholder = f"{{{{{field}}}}}"
                        if placeholder in cell.value:
                            cell.value = cell.value.replace(placeholder, str(value))
    
    wb.save(output_path)
    return output_path


def fill_jinja_template(template_path: str, data: dict[str, Any], output_path: str) -> str:
    """
    Fill a Jinja2/HTML template with data.
    """
    try:
        from jinja2 import Template
    except ImportError:
        raise RuntimeError("jinja2 is required: pip install jinja2")
    
    template_content = Path(template_path).read_text(encoding='utf-8')
    template = Template(template_content)
    result = template.render(**data)
    
    Path(output_path).write_text(result, encoding='utf-8')
    return output_path


def fill_template(template_path: str, data: dict[str, Any], output_dir: str | None = None) -> dict:
    """
    Fill any supported template with data.
    
    Args:
        template_path: Path to the template file
        data: Dictionary of field_name: value pairs
        output_dir: Output directory (defaults to uploads_dir)
        
    Returns:
        Dictionary with output path and filled fields
    """
    path = Path(template_path)
    suffix = path.suffix.lower()
    
    if output_dir is None:
        output_dir = str(settings.uploads_dir)
    
    output_path = Path(output_dir) / f"filled_{path.stem}_{int(__import__('time').time())}{suffix}"
    
    filled_fields = list(data.keys())
    
    try:
        if suffix == '.docx':
            fill_docx_template(template_path, data, str(output_path))
        elif suffix == '.xlsx':
            fill_excel_template(template_path, data, str(output_path))
        elif suffix in ['.jinja2', '.html', '.txt']:
            fill_jinja_template(template_path, data, str(output_path))
        else:
            return {
                "success": False,
                "error": f"Unsupported template format: {suffix}"
            }
        
        return {
            "success": True,
            "output_path": str(output_path),
            "filled_fields": filled_fields,
            "template": path.name,
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def list_templates() -> list[dict]:
    """
    List all available templates with their fields.
    """
    templates = []
    templates_dir = settings.templates_dir
    
    if not templates_dir.exists():
        return templates
    
    for category_dir in templates_dir.iterdir():
        if category_dir.is_dir():
            category = category_dir.name
            for template_file in category_dir.iterdir():
                if template_file.suffix in ['.docx', '.xlsx', '.jinja2', '.html']:
                    fields = get_template_fields(str(template_file))
                    templates.append({
                        "id": f"{category}-{template_file.stem}",
                        "name": template_file.stem.replace("_", " ").title(),
                        "category": category,
                        "path": str(template_file),
                        "type": template_file.suffix[1:],
                        "fields": fields,
                    })
    
    return templates


# Export
__all__ = [
    "get_template_fields",
    "fill_template",
    "fill_docx_template",
    "fill_excel_template",
    "fill_jinja_template",
    "list_templates",
]
