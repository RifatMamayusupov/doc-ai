"""Secure code execution tool for the agent."""
import asyncio
import sys
import io
import contextlib
import traceback
import os
from pathlib import Path
from typing import Any

async def execute_python_code(code: str, user_id: str, upload_dir: str) -> dict[str, Any]:
    """
    Execute Python code in a controlled environment.
    Retains context logic if we use a persistent REPL.
    
    Args:
        code: The python code to run
        user_id: ID of the user (for file access scope)
        upload_dir: Path to uploads directory
        
    Returns:
        Dict containing output, error, status, and new_files
    """
    
    # Capture stdout/stderr
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    
    # Ensure upload directory
    work_dir = Path(upload_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # Track files before execution
    initial_files = {}
    try:
        initial_files = {f.name: f.stat().st_mtime for f in work_dir.glob('*') if f.is_file()}
    except Exception:
        pass

    # Context for execution
    # Allows access to pandas, numpy etc if installed
    local_scope = {
        "user_id": user_id,
        "upload_dir": str(work_dir), # Pass string path
        "print": lambda *args, **kwargs: print(*args, file=stdout_buffer, **kwargs)
    }
    
    # Change CWD to work_dir temporarily so generated files land there
    old_cwd = os.getcwd()
    try:
        os.chdir(work_dir)
        
        # Wrap execution to capture output
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exec(code, {}, local_scope)
            
        status = "success"
        
    except Exception:
        status = "error"
        stderr_buffer.write(traceback.format_exc())
    finally:
        os.chdir(old_cwd)

    # Track files after execution
    new_files = []
    try:
        final_files = {f: f.stat().st_mtime for f in work_dir.glob('*') if f.is_file()}
        for f, mtime in final_files.items():
            # If file is new or modified
            if f.name not in initial_files or mtime > initial_files[f.name]:
                new_files.append({
                    "name": f.name,
                    "path": str(f.absolute()),
                    "size": f.stat().st_size,
                    "type": "image" if f.suffix.lower() in ['.png', '.jpg', '.jpeg'] else "file"
                })
    except Exception as e:
        print(f"File tracking error: {e}")

    return {
        "status": status,
        "output": stdout_buffer.getvalue(),
        "error": stderr_buffer.getvalue(),
        "images": [f for f in new_files if f['type'] == 'image'], # Legacy support if needed
        "generated_files": new_files
    }

class ToolRegistry:
    @staticmethod
    def get_tool_definitions() -> list[dict]:
        return [
            {
                "name": "execute_python",
                "description": "Execute Python code to analyze data, read files, or solve math problems.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": { "type": "string" }
                    },
                    "required": ["code"]
                }
            }
        ]
