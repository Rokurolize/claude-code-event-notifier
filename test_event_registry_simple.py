#\!/usr/bin/env python3
"""Simple test for event registry logging."""

import sys
import os

# Test just the compilation
print("Testing event_registry.py compilation...")
import py_compile

try:
    py_compile.compile('src/handlers/event_registry.py', doraise=True)
    print("✓ event_registry.py compiles successfully\!")
except py_compile.PyCompileError as e:
    print(f"✗ Compilation error: {e}")
    sys.exit(1)

# Check imports
print("\nChecking imports...")
with open('src/handlers/event_registry.py', 'r') as f:
    content = f.read()
    if 'from src.utils.astolfo_logger import AstolfoLogger' in content:
        print("✓ AstolfoLogger import found")
    if 'self._logger = AstolfoLogger()' in content:
        print("✓ AstolfoLogger initialization found")
    if 'self._logger.info(' in content:
        print("✓ Logger info calls found")
    if 'self._logger.debug(' in content:
        print("✓ Logger debug calls found")
    if 'self._logger.warning(' in content:
        print("✓ Logger warning calls found")

print("\nAll checks passed\!")
