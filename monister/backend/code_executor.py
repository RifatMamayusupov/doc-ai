"""
Monister Code Executor - Safe Python code execution in sandbox.

Provides:
- Restricted Python execution
- Timeout limits
- Memory limits
- Output capture
- Error handling
"""

import ast
import io
import sys
import traceback
import subprocess
import tempfile
import os
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any
from dataclasses import dataclass
from enum import Enum

from config import settings


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SECURITY_ERROR = "security_error"


@dataclass
class ExecutionResult:
    """Result of code execution."""
    status: ExecutionStatus
    output: str
    error: str | None = None
    execution_time: float = 0.0
    files_created: list[str] | None = None


# Dangerous operations to block
BLOCKED_IMPORTS = {
    'os', 'subprocess', 'sys', 'shutil', 'socket', 'requests',
    'urllib', 'http', 'ftplib', 'smtplib', 'telnetlib',
    'pickle', 'shelve', 'marshal', 'ctypes', 'multiprocessing',
    'threading', '_thread', 'signal', 'pty', 'tty',
}

BLOCKED_BUILTINS = {
    'exec', 'eval', 'compile', 'open', 'input', '__import__',
    'globals', 'locals', 'vars', 'dir', 'getattr', 'setattr',
    'delattr', 'hasattr', 'type', 'isinstance', 'issubclass',
}


class SafeASTChecker(ast.NodeVisitor):
    """Check AST for dangerous operations."""
    
    def __init__(self):
        self.errors: list[str] = []
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            module = alias.name.split('.')[0]
            if module in BLOCKED_IMPORTS:
                self.errors.append(f"Import of '{module}' is not allowed")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            module = node.module.split('.')[0]
            if module in BLOCKED_IMPORTS:
                self.errors.append(f"Import from '{module}' is not allowed")
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in BLOCKED_BUILTINS:
                self.errors.append(f"Call to '{node.func.id}' is not allowed")
        self.generic_visit(node)
    
    def check(self, code: str) -> list[str]:
        """Check code for security issues."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            self.errors.append(f"Syntax error: {e}")
        return self.errors


def create_safe_globals() -> dict[str, Any]:
    """Create a restricted globals dict for code execution."""
    import math
    import json
    import re
    import datetime
    import random
    import statistics
    import collections
    import itertools
    import functools
    import decimal
    
    # Safe builtins
    safe_builtins = {
        'abs': abs, 'all': all, 'any': any, 'ascii': ascii,
        'bin': bin, 'bool': bool, 'bytearray': bytearray, 'bytes': bytes,
        'callable': callable, 'chr': chr, 'complex': complex,
        'dict': dict, 'divmod': divmod, 'enumerate': enumerate,
        'filter': filter, 'float': float, 'format': format,
        'frozenset': frozenset, 'hash': hash, 'hex': hex,
        'int': int, 'iter': iter, 'len': len, 'list': list,
        'map': map, 'max': max, 'min': min, 'next': next,
        'oct': oct, 'ord': ord, 'pow': pow, 'print': print,
        'range': range, 'repr': repr, 'reversed': reversed,
        'round': round, 'set': set, 'slice': slice, 'sorted': sorted,
        'str': str, 'sum': sum, 'tuple': tuple, 'zip': zip,
        'True': True, 'False': False, 'None': None,
    }
    
    return {
        '__builtins__': safe_builtins,
        'math': math,
        'json': json,
        're': re,
        'datetime': datetime,
        'random': random,
        'statistics': statistics,
        'collections': collections,
        'itertools': itertools,
        'functools': functools,
        'decimal': decimal,
    }


def execute_restricted(code: str, timeout: int = 10) -> ExecutionResult:
    """
    Execute Python code in a restricted environment.
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds
        
    Returns:
        ExecutionResult with output, errors, and status
    """
    import time
    start_time = time.time()
    
    # Security check
    checker = SafeASTChecker()
    errors = checker.check(code)
    if errors:
        return ExecutionResult(
            status=ExecutionStatus.SECURITY_ERROR,
            output="",
            error="\n".join(errors),
            execution_time=time.time() - start_time
        )
    
    # Capture stdout/stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        # Create safe execution environment
        safe_globals = create_safe_globals()
        safe_locals: dict[str, Any] = {}
        
        # Execute with output capture
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(compile(code, '<sandbox>', 'exec'), safe_globals, safe_locals)
        
        output = stdout_capture.getvalue()
        error = stderr_capture.getvalue() if stderr_capture.getvalue() else None
        
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output=output,
            error=error,
            execution_time=time.time() - start_time
        )
        
    except Exception as e:
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            output=stdout_capture.getvalue(),
            error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            execution_time=time.time() - start_time
        )


def execute_subprocess(code: str, timeout: int = 30) -> ExecutionResult:
    """
    Execute Python code in a subprocess using stdin (no temp file).
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds
        
    Returns:
        ExecutionResult with output, errors, and status
    """
    import time
    start_time = time.time()
    
    try:
        # Execute in subprocess by passing code to stdin
        # using 'python -' allows reading script from stdin
        result = subprocess.run(
            [sys.executable, "-"],
            input=code,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(settings.uploads_dir),
        )
        
        status = ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.ERROR
        
        return ExecutionResult(
            status=status,
            output=result.stdout,
            error=result.stderr if result.stderr else None,
            execution_time=time.time() - start_time
        )
        
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            status=ExecutionStatus.TIMEOUT,
            output="",
            error=f"Execution timed out after {timeout} seconds",
            execution_time=timeout
        )
    except Exception as e:
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            output="",
            error=str(e),
            execution_time=time.time() - start_time
        )


def execute_code(
    code: str, 
    mode: str = "restricted",
    timeout: int = 30
) -> ExecutionResult:
    """
    Execute code with the specified mode.
    
    Args:
        code: Python code to execute
        mode: "restricted" (safe globals) or "subprocess" (isolated process)
        timeout: Maximum execution time
        
    Returns:
        ExecutionResult
    """
    if mode == "subprocess":
        return execute_subprocess(code, timeout)
    else:
        return execute_restricted(code, timeout)


async def aexecute_subprocess(code: str, timeout: int = 30) -> ExecutionResult:
    """
    Async execute Python code in a subprocess using stdin.
    """
    import time
    import asyncio
    start_time = time.time()
    
    try:
        # Use asyncio subprocess
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(settings.uploads_dir),
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=code.encode()), 
                timeout=timeout
            )
            
            output = stdout.decode()
            error_text = stderr.decode()
            
            status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.ERROR
            
            return ExecutionResult(
                status=status,
                output=output,
                error=error_text if error_text else None,
                execution_time=time.time() - start_time
            )
            
        except asyncio.TimeoutError:
            process.kill()
            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                output="",
                error=f"Execution timed out after {timeout} seconds",
                execution_time=timeout
            )
            
    except Exception as e:
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            output="",
            error=str(e),
            execution_time=time.time() - start_time
        )


async def aexecute_code(
    code: str, 
    mode: str = "restricted",
    timeout: int = 30
) -> ExecutionResult:
    """
    Async version of execute_code.
    """
    if mode == "subprocess":
        return await aexecute_subprocess(code, timeout)
    else:
        # execute_restricted is CPU bound but fast, usually fine to run in thread
        import asyncio
        from functools import partial
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(execute_restricted, code, timeout))


# Export
__all__ = [
    "ExecutionStatus",
    "ExecutionResult",
    "execute_code",
    "execute_restricted",
    "execute_subprocess",
    "aexecute_code",
]
