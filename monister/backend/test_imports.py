#!/usr/bin/env python3
"""Quick syntax check for modified backend modules."""
import ast, sys

files = [
    "preview_service.py",
    "main.py",
]

ok = True
for f in files:
    try:
        with open(f) as fh:
            ast.parse(fh.read())
        print(f"  OK: {f}")
    except SyntaxError as e:
        print(f"FAIL: {f} - {e}")
        ok = False

if ok:
    print("All files parse OK")
else:
    sys.exit(1)
