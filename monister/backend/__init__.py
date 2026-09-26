"""
Monister Backend Package

Uses deepagents_cli framework for:
- FilesystemMiddleware (read/write/edit files)
- MemoryMiddleware (persistent agent memory)
- SkillsMiddleware (custom skills support)
- ShellMiddleware (shell command execution)

Plus custom Monister tools for document processing.
"""

from agent_engine import MonisterAgent, create_agent
from tools import (
    ocr_extract,
    clean_data,
    redact_pii,
    fill_template,
    parse_excel,
    get_all_tools,
)
from config import settings


__all__ = [
    # Agent
    "MonisterAgent",
    "create_agent",
    # Tools  
    "ocr_extract",
    "clean_data",
    "redact_pii",
    "fill_template",
    "parse_excel",
    "get_all_tools",
    # Config
    "settings",
]
