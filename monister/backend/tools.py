"""
Monister Custom Tools - Additional tools specific to Monister.

Note: The deepagents_cli framework already provides:
- shell: Execute shell commands
- write_file: Create/overwrite files  
- edit_file: Edit existing files
- read_file: Read file contents
- list_directory: List directory contents
- http_request: Make HTTP requests
- fetch_url: Fetch and parse URL content
- web_search: Search the web (if Tavily configured)

This file contains Monister-specific tools for document processing.
"""

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


# ============== OCR Tool ==============
@tool
async def ocr_extract(file_path: str) -> dict:
    """
    Extract text from PDF or image files using OCR.
    
    Args:
        file_path: Path to the PDF or image file
    
    Returns:
        Dictionary with extracted text and metadata
    """
    import asyncio
    from functools import partial
    
    def _sync_ocr(path_str):
        path = Path(path_str)
        if not path.exists():
            return {"error": f"File not found: {path_str}"}
        
        try:
            # Try to import OCR libraries
            import pytesseract
            from PIL import Image
            
            if path.suffix.lower() == ".pdf":
                try:
                    from pdf2image import convert_from_path
                    
                    images = convert_from_path(path_str)
                    text_parts = []
                    
                    for i, image in enumerate(images):
                        page_text = pytesseract.image_to_string(image)
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                    
                    return {
                        "success": True,
                        "text": "\n\n".join(text_parts),
                        "pages": len(images),
                        "file": str(path.name),
                    }
                except ImportError:
                    return {"error": "pdf2image not installed. Run: pip install pdf2image"}
            
            elif path.suffix.lower() in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
                image = Image.open(path_str)
                text = pytesseract.image_to_string(image)
                
                return {
                    "success": True,
                    "text": text,
                    "file": str(path.name),
                }
            else:
                return {"error": f"Unsupported file type: {path.suffix}"}
                
        except ImportError:
            return {"error": "pytesseract not installed. Run: pip install pytesseract Pillow"}
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_sync_ocr, file_path))


# ============== Data Cleaner Tool ==============
@tool
async def clean_data(
    file_path: str,
    null_strategy: str = "mean",
    remove_duplicates: bool = True,
) -> dict:
    """
    Clean data from CSV or Excel files.
    
    Args:
        file_path: Path to CSV or Excel file
        null_strategy: How to handle null values - "mean", "median", "mode", "drop", "zero"
        remove_duplicates: Whether to remove duplicate rows
    
    Returns:
        Dictionary with cleaning statistics and output path
    """
    import asyncio
    from functools import partial

    def _sync_clean(fpath, strategy, dedup):
        path = Path(fpath)
        if not path.exists():
            return {"error": f"File not found: {fpath}"}
        
        try:
            import pandas as pd
            
            # Load data
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(fpath)
            elif path.suffix.lower() in [".xlsx", ".xls"]:
                df = pd.read_excel(fpath)
            else:
                return {"error": f"Unsupported file type: {path.suffix}"}
            
            original_rows = len(df)
            original_nulls = df.isnull().sum().sum()
            
            # Handle null values
            if strategy == "mean":
                numeric_cols = df.select_dtypes(include=["number"]).columns
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
            elif strategy == "median":
                numeric_cols = df.select_dtypes(include=["number"]).columns
                df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
            elif strategy == "mode":
                for col in df.columns:
                    if df[col].isnull().any():
                        mode_val = df[col].mode()
                        if len(mode_val) > 0:
                            df[col] = df[col].fillna(mode_val[0])
            elif strategy == "drop":
                df = df.dropna()
            elif strategy == "zero":
                df = df.fillna(0)
            
            # Remove duplicates
            duplicates_removed = 0
            if dedup:
                before_dedup = len(df)
                df = df.drop_duplicates()
                duplicates_removed = before_dedup - len(df)
            
            # Save cleaned data
            output_path = path.parent / f"{path.stem}_cleaned{path.suffix}"
            
            if path.suffix.lower() == ".csv":
                df.to_csv(output_path, index=False)
            else:
                df.to_excel(output_path, index=False)
            
            return {
                "success": True,
                "original_rows": original_rows,
                "cleaned_rows": len(df),
                "nulls_handled": int(original_nulls),
                "duplicates_removed": duplicates_removed,
                "output_path": str(output_path),
                "null_strategy": strategy,
            }
            
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_sync_clean, file_path, null_strategy, remove_duplicates))


# ============== PII Redactor Tool ==============
@tool
def redact_pii(text: str) -> dict:
    """
    Detect and redact Personally Identifiable Information (PII) from text.
    
    Detects: phone numbers, emails, passport numbers, credit cards, SSN
    
    Args:
        text: Text to redact PII from
    
    Returns:
        Dictionary with redacted text and detected PII types
    """
    patterns = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone_uz": r"\+998[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}",
        "phone_intl": r"\+\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,9}",
        "phone_local": r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "passport": r"\b[A-Z]{2}\d{7}\b",
        "inn_uz": r"\b[0-9]{3}[\s-]?[0-9]{3}[\s-]?[0-9]{3}\b",  # Uzbekistan INN (xxx-xxx-xxx format)
    }
    
    redacted_text = text
    detected = {}
    
    for pii_type, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            detected[pii_type] = len(matches)
            mask = f"[{pii_type.upper()}_REDACTED]"
            redacted_text = re.sub(pattern, mask, redacted_text, flags=re.IGNORECASE)
    
    return {
        "success": True,
        "redacted_text": redacted_text,
        "detected_pii": detected,
        "pii_count": sum(detected.values()) if detected else 0,
    }


# ============== Template Filler Tool ==============
@tool
def fill_template(template_path: str, data: dict) -> dict:
    """
    Fill a document template with provided data.
    
    Supports: .docx (python-docx), .jinja2, .html
    
    Args:
        template_path: Path to the template file
        data: Dictionary of field names and values to fill
    
    Returns:
        Dictionary with output file path and filled fields
    """
    path = Path(template_path)
    
    if not path.exists():
        return {"error": f"Template not found: {template_path}"}
    
    try:
        if path.suffix.lower() == ".docx":
            from docxtpl import DocxTemplate
            
            doc = DocxTemplate(template_path)
            doc.render(data)
            
            output_path = path.parent / f"{path.stem}_filled.docx"
            doc.save(output_path)
            
            return {
                "success": True,
                "output": str(output_path),
                "filled_fields": list(data.keys()),
                "type": "docx",
            }
        
        elif path.suffix.lower() in [".jinja2", ".html", ".j2"]:
            from jinja2 import Template
            
            template_content = path.read_text(encoding="utf-8")
            template = Template(template_content)
            rendered = template.render(**data)
            
            output_suffix = ".html" if path.suffix.lower() == ".jinja2" else path.suffix
            output_path = path.parent / f"{path.stem}_filled{output_suffix}"
            output_path.write_text(rendered, encoding="utf-8")
            
            return {
                "success": True,
                "output": str(output_path),
                "filled_fields": list(data.keys()),
                "type": "jinja2",
            }
        
        else:
            return {"error": f"Unsupported template type: {path.suffix}"}
            
    except Exception as e:
        return {"error": str(e)}


# ============== Excel Parser Tool ==============
@tool
async def parse_excel(file_path: str, sheet_name: str | None = None) -> dict:
    """
    Parse Excel file and extract data as structured JSON.
    
    Args:
        file_path: Path to Excel file
        sheet_name: Specific sheet to parse (optional, defaults to first sheet)
    
    Returns:
        Dictionary with parsed data, columns, and statistics
    """
    import asyncio
    from functools import partial
    
    def _sync_parse(fpath, sname):
        path = Path(fpath)
        if not path.exists():
            return {"error": f"File not found: {fpath}"}
        
        try:
            import pandas as pd
            
            # Read Excel file
            if sname:
                df = pd.read_excel(fpath, sheet_name=sname)
            else:
                df = pd.read_excel(fpath)
            
            # Get statistics
            stats = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "null_counts": df.isnull().sum().to_dict(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            }
            
            # Return preview (first 10 rows)
            # handle NaN/Infinity for JSON serialization
            df = df.fillna("")
            preview = df.head(10).to_dict(orient="records")
            
            return {
                "success": True,
                "statistics": stats,
                "preview": preview,
                "file": path.name,
            }
            
        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_sync_parse, file_path, sheet_name))


# ============== Code Execution Tool ==============
@tool
async def execute_code_tool(code: str) -> dict:
    """
    Execute Python code in a safe sandbox environment.
    Use this to perform calculations, data analysis, or process files.
    
    Args:
        code: Python code to execute
    
    Returns:
        Dictionary with output, error, and status
    """
    from code_executor import aexecute_code
    
    try:
        result = await aexecute_code(code, mode="subprocess")
        
        return {
            "success": result.status == "success",
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time
        }
    except Exception as e:
        return {"error": str(e)}


# ============== Batch Document Generator ==============
@tool
async def batch_generate(
    template_path: str,
    data_source: str,
    output_dir: str = "",
) -> dict:
    """
    Generate multiple documents from a template using data from an Excel/CSV file.
    Each row in the data source creates one document.
    
    Args:
        template_path: Path to the template file (.docx, .jinja2, .html)
        data_source: Path to Excel/CSV with data rows
        output_dir: Directory for output files (optional)
    
    Returns:
        Dictionary with generated file paths and statistics
    """
    import asyncio
    from functools import partial

    def _sync_batch(tpl_path, data_path, out_dir):
        tpl = Path(tpl_path)
        data = Path(data_path)

        if not tpl.exists():
            return {"error": f"Template not found: {tpl_path}"}
        if not data.exists():
            return {"error": f"Data source not found: {data_path}"}

        try:
            import pandas as pd

            # Read data
            if data.suffix.lower() == ".csv":
                df = pd.read_csv(data_path)
            else:
                df = pd.read_excel(data_path)

            df = df.fillna("")

            # Output directory
            if out_dir:
                output = Path(out_dir)
            else:
                output = data.parent / f"{tpl.stem}_batch_output"
            output.mkdir(parents=True, exist_ok=True)

            generated = []
            errors = []

            for idx, row in df.iterrows():
                row_data = row.to_dict()
                try:
                    if tpl.suffix.lower() == ".docx":
                        from docxtpl import DocxTemplate
                        doc = DocxTemplate(str(tpl))
                        doc.render(row_data)
                        out_file = output / f"{tpl.stem}_{idx + 1}.docx"
                        doc.save(out_file)
                        generated.append(str(out_file))

                    elif tpl.suffix.lower() in [".jinja2", ".html", ".j2"]:
                        from jinja2 import Template
                        content = tpl.read_text(encoding="utf-8")
                        rendered = Template(content).render(**row_data)
                        ext = ".html" if tpl.suffix.lower() == ".jinja2" else tpl.suffix
                        out_file = output / f"{tpl.stem}_{idx + 1}{ext}"
                        out_file.write_text(rendered, encoding="utf-8")
                        generated.append(str(out_file))
                except Exception as e:
                    errors.append({"row": idx + 1, "error": str(e)})

            return {
                "success": True,
                "total_rows": len(df),
                "generated_count": len(generated),
                "error_count": len(errors),
                "output_dir": str(output),
                "output_path": str(output),
                "generated_files": generated[:10],  # Show first 10
                "errors": errors[:5],
            }

        except Exception as e:
            return {"error": str(e)}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_sync_batch, template_path, data_source, output_dir))


# ============== Document Comparison Tool ==============
@tool
async def compare_documents(
    file_path_1: str,
    file_path_2: str,
) -> dict:
    """
    Compare two documents and show differences.
    Supports text files, DOCX, and CSV/Excel.
    
    Args:
        file_path_1: Path to the first document
        file_path_2: Path to the second document
    
    Returns:
        Dictionary with comparison results, differences, and similarity score
    """
    import asyncio
    from functools import partial
    import difflib

    def _sync_compare(path1, path2):
        p1, p2 = Path(path1), Path(path2)
        if not p1.exists():
            return {"error": f"File not found: {path1}"}
        if not p2.exists():
            return {"error": f"File not found: {path2}"}

        try:
            # Extract text from both files
            text1 = _extract_text(p1)
            text2 = _extract_text(p2)

            if text1 is None:
                return {"error": f"Cannot extract text from: {p1.suffix}"}
            if text2 is None:
                return {"error": f"Cannot extract text from: {p2.suffix}"}

            # Compute diff
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()

            differ = difflib.unified_diff(lines1, lines2,
                                          fromfile=p1.name, tofile=p2.name, lineterm='')
            diff_text = "\n".join(list(differ)[:200])  # Limit diff output

            # Similarity ratio
            matcher = difflib.SequenceMatcher(None, text1, text2)
            similarity = round(matcher.ratio() * 100, 2)

            # Summary
            added = sum(1 for l in diff_text.split('\n') if l.startswith('+') and not l.startswith('+++'))
            removed = sum(1 for l in diff_text.split('\n') if l.startswith('-') and not l.startswith('---'))

            return {
                "success": True,
                "similarity_percent": similarity,
                "lines_added": added,
                "lines_removed": removed,
                "file_1": p1.name,
                "file_2": p2.name,
                "diff": diff_text[:3000],
                "summary": f"{similarity}% o'xshashlik. {added} qator qo'shilgan, {removed} qator o'chirilgan.",
            }

        except Exception as e:
            return {"error": str(e)}

    def _extract_text(path: Path) -> str | None:
        """Extract text from various file formats."""
        ext = path.suffix.lower()
        if ext in ['.txt', '.md', '.csv', '.json', '.xml', '.py', '.js', '.html', '.css']:
            return path.read_text(encoding="utf-8", errors="ignore")
        elif ext == '.docx':
            try:
                from docx import Document
                doc = Document(str(path))
                return "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                return path.read_bytes().decode("utf-8", errors="ignore")
        elif ext in ['.xlsx', '.xls']:
            try:
                import pandas as pd
                df = pd.read_excel(str(path))
                return df.to_string()
            except Exception:
                return None
        return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_sync_compare, file_path_1, file_path_2))


# ============== Compliance Checker Tool ==============
@tool
def check_compliance(
    document_type: str,
    fields: dict,
    industry: str = "",
) -> dict:
    """
    Check if a document meets compliance requirements for a specific industry.
    Validates required fields, format rules, and industry-specific regulations.
    
    Args:
        document_type: Type of document (e.g., "sick_leave", "invoice", "contract")
        fields: Dictionary of field names and values to validate
        industry: Industry module ID (e.g., "healthcare", "finance")
    
    Returns:
        Dictionary with compliance status, missing fields, and warnings
    """
    from industry_modules import ALL_MODULES

    issues = []
    warnings = []
    passed = []

    # Find the document template
    target_doc = None
    target_module = None

    if industry and industry in ALL_MODULES:
        module = ALL_MODULES[industry]
        for doc in module.documents:
            if doc.id == document_type:
                target_doc = doc
                target_module = module
                break
    else:
        # Search all modules
        for mid, module in ALL_MODULES.items():
            for doc in module.documents:
                if doc.id == document_type:
                    target_doc = doc
                    target_module = module
                    break
            if target_doc:
                break

    if not target_doc:
        # Generic validation
        if not fields:
            issues.append("No fields provided")
        else:
            for k, v in fields.items():
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    issues.append(f"Empty field: {k}")
                else:
                    passed.append(f"✅ {k}: present")

        return {
            "success": len(issues) == 0,
            "document_type": document_type,
            "issues": issues,
            "warnings": ["Document type not found in industry modules"],
            "passed": passed,
            "compliance_score": round(len(passed) / max(len(passed) + len(issues), 1) * 100, 1),
        }

    # Validate required fields
    missing = []
    for req_field in target_doc.required_fields:
        if req_field not in fields or not fields.get(req_field):
            missing.append(req_field)
            issues.append(f"❌ Majburiy maydon yo'q: {req_field}")
        else:
            passed.append(f"✅ {req_field}: bor")

    # Check compliance rules
    for rule in target_doc.compliance_rules:
        warnings.append(f"⚠️ Qoida: {rule}")

    # Date validations
    for field_name in ['start_date', 'end_date', 'date', 'due_date']:
        if field_name in fields and fields[field_name]:
            try:
                from datetime import datetime
                # Try to parse date
                val = str(fields[field_name])
                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']:
                    try:
                        datetime.strptime(val, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    warnings.append(f"⚠️ Sana formati tekshiring: {field_name} = {val}")
            except Exception:
                pass

    total = len(passed) + len(issues)
    score = round(len(passed) / max(total, 1) * 100, 1)

    return {
        "success": len(issues) == 0,
        "document_type": document_type,
        "industry": target_module.name_uz if target_module else "",
        "document_name": target_doc.name_uz,
        "issues": issues,
        "missing_fields": missing,
        "warnings": warnings,
        "passed": passed,
        "compliance_score": score,
        "total_required": len(target_doc.required_fields),
        "total_provided": len(target_doc.required_fields) - len(missing),
    }


# ============== Translate Document Tool ==============
@tool
def translate_document(
    text: str,
    target_language: str = "uz",
    source_language: str = "auto",
) -> dict:
    """
    Translate document text between languages.
    Note: For full translation, the AI agent should do the translation itself.
    This tool provides a structured interface for the agent to return translations.
    
    Args:
        text: Text to translate
        target_language: Target language code (uz, ru, en, etc.)
        source_language: Source language code (auto for auto-detect)
    
    Returns:
        Dictionary with translation info
    """
    lang_names = {
        "uz": "O'zbek", "ru": "Rus", "en": "Ingliz", "de": "Nemis",
        "fr": "Fransuz", "ar": "Arab", "tr": "Turk", "zh": "Xitoy",
        "ja": "Yapon", "ko": "Koreys", "es": "Ispan", "it": "Italyan",
    }

    return {
        "success": True,
        "original_text": text[:500],
        "target_language": target_language,
        "target_language_name": lang_names.get(target_language, target_language),
        "source_language": source_language,
        "text_length": len(text),
        "note": "This is a passthrough tool. The AI agent should translate the text using its own language model and return the result in the target language.",
    }


# ============== Industry Detection Tool ==============
@tool
def detect_industry(query: str) -> dict:
    """
    Detect the industry (soha) based on a user query or document description.
    Returns matching industry info with available document templates.
    
    Args:
        query: User query or description to detect industry from
    
    Returns:
        Dictionary with detected industry, confidence, and available documents
    """
    try:
        from industry_modules import detect_industry as _detect, get_module_documents
        
        matches = _detect(query)  # Returns list of dicts sorted by score
        
        if not matches:
            return {
                "success": True,
                "industry_id": "general",
                "industry_name": "Umumiy",
                "confidence": 0,
                "available_documents": [],
                "total_documents": 0,
                "message": "Soha aniqlanmadi. Iltimos, soha nomini aniqroq kiriting.",
            }
        
        # Pick the top match
        top = matches[0]
        industry_id = top.get("module_id", "general")
        
        # Get available documents for this industry
        docs = get_module_documents(industry_id)
        
        return {
            "success": True,
            "industry_id": industry_id,
            "industry_name": top.get("name_uz") or top.get("name", industry_id),
            "confidence": top.get("score", 0),
            "matched_keywords": top.get("matched_keywords", []),
            "available_documents": [
                {"name": d.get("name"), "description": d.get("description", "")}
                for d in docs[:10]
            ],
            "total_documents": len(docs),
            "all_matches": [
                {"id": m.get("module_id"), "name": m.get("name_uz", m.get("name")), "score": m.get("score", 0)}
                for m in matches[:5]
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Telegram Send Tool ==============
@tool
async def send_to_telegram(recipient: str, file_path: str, caption: str = "") -> dict:
    """
    Send a document file to a Telegram user.
    The recipient can be a @username or a numeric chat_id.
    The user must have started the bot first (/start).
    
    Args:
        recipient: Telegram username (@user) or chat_id
        file_path: Path to the file to send
        caption: Optional caption/message with the file
    
    Returns:
        Dictionary with send status and message
    """
    try:
        from telegram_bot import send_document_to_user
        result = await send_document_to_user(recipient, file_path, caption)
        return result
    except Exception as e:
        return {"status": "error", "message": f"Telegram yuborish xatosi: {str(e)}"}


# ============== Tool Registry ==============
def get_all_tools():
    """Get list of all custom Monister tools."""
    tools = [
        ocr_extract,
        clean_data,
        redact_pii,
        fill_template,
        parse_excel,
        execute_code_tool,
        batch_generate,
        compare_documents,
        check_compliance,
        translate_document,
        detect_industry,
        send_to_telegram,
    ]
    return tools


# ============== Tool Map ==============
TOOL_MAP = {
    "ocr": ocr_extract,
    "ocr_extract": ocr_extract,
    "clean": clean_data,
    "clean_data": clean_data,
    "redact": redact_pii,
    "redact_pii": redact_pii,
    "fill": fill_template,
    "fill_template": fill_template,
    "parse": parse_excel,
    "parse_excel": parse_excel,
    "execute_code": execute_code_tool,
    "python": execute_code_tool,
    "batch": batch_generate,
    "batch_generate": batch_generate,
    "compare": compare_documents,
    "compare_documents": compare_documents,
    "compliance": check_compliance,
    "check_compliance": check_compliance,
    "translate": translate_document,
    "translate_document": translate_document,
    "detect_industry": detect_industry,
    "industry": detect_industry,
    "send_to_telegram": send_to_telegram,
    "telegram": send_to_telegram,
}


def get_tool(name: str):
    """Get a tool by name."""
    return TOOL_MAP.get(name)


# ============== Exports ==============
__all__ = [
    "ocr_extract",
    "clean_data",
    "redact_pii",
    "fill_template",
    "parse_excel",
    "execute_code_tool",
    "batch_generate",
    "compare_documents",
    "check_compliance",
    "translate_document",
    "detect_industry",
    "send_to_telegram",
    "get_all_tools",
    "get_tool",
    "TOOL_MAP",
]
