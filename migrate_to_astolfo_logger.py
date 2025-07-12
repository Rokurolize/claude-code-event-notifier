#!/usr/bin/env python3
"""
AstolfoLogger Migration Script
Automatically migrates standard logging to AstolfoLogger across the codebase.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Files to skip (already migrated or special cases)
SKIP_FILES = {
    'astolfo_logger.py',
    'astolfo_logger_types.py',
    'discord_notifier.py',
    'thread_storage.py',
    'discord_sender.py',
    'configure_hooks.py',  # CLI tool, keep print statements
    'session_log_viewer.py',  # CLI tool, keep print statements
}

# Directories to process
TARGET_DIRS = ['src', 'tests', 'utils']

# Import patterns to replace
IMPORT_PATTERNS = [
    # Standard import logging
    (r'^import logging\s*$', 'from src.utils.astolfo_logger import AstolfoLogger\n'),
    # From logging import specific items
    (r'^from logging import (.+)$', 'from src.utils.astolfo_logger import AstolfoLogger\n'),
]

# Logger creation patterns
LOGGER_PATTERNS = [
    # logger = logging.getLogger(__name__)
    (r'(\s*)logger\s*=\s*logging\.getLogger\(([^)]+)\)', r'\1logger = AstolfoLogger(\2)'),
    # self.logger = logging.getLogger(...)
    (r'(\s*)self\.logger\s*=\s*logging\.getLogger\(([^)]+)\)', r'\1self.logger = AstolfoLogger(\2)'),
    # logging.getLogger(...) in expressions
    (r'logging\.getLogger\(([^)]+)\)', r'AstolfoLogger(\1)'),
]

# Type annotation patterns
TYPE_PATTERNS = [
    # logging.Logger in function signatures
    (r':\s*logging\.Logger', ': AstolfoLogger'),
    # Optional[logging.Logger]
    (r'Optional\[logging\.Logger\]', 'Optional[AstolfoLogger]'),
    # Union[..., logging.Logger, ...]
    (r'Union\[([^]]*?)logging\.Logger([^]]*?)\]', r'Union[\1AstolfoLogger\2]'),
]

# BasicConfig patterns
BASICCONFIG_PATTERNS = [
    # logging.basicConfig(...)
    (r'logging\.basicConfig\([^)]+\)', '# BasicConfig removed - AstolfoLogger handles configuration'),
]


def process_file(filepath: Path) -> Tuple[bool, List[str]]:
    """Process a single Python file for migration."""
    if filepath.name in SKIP_FILES:
        return False, ["Skipped (in skip list)"]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, [f"Error reading file: {e}"]
    
    original_content = content
    changes = []
    
    # Check if file uses logging
    if not ('import logging' in content or 'from logging' in content):
        return False, ["No logging imports found"]
    
    # Apply import replacements
    for pattern, replacement in IMPORT_PATTERNS:
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content != content:
            changes.append(f"Replaced import pattern: {pattern}")
            content = new_content
    
    # Apply logger creation replacements
    for pattern, replacement in LOGGER_PATTERNS:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes.append(f"Replaced logger creation: {pattern}")
            content = new_content
    
    # Apply type annotation replacements
    for pattern, replacement in TYPE_PATTERNS:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes.append(f"Replaced type annotation: {pattern}")
            content = new_content
    
    # Apply basicConfig replacements
    for pattern, replacement in BASICCONFIG_PATTERNS:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes.append(f"Replaced basicConfig: {pattern}")
            content = new_content
    
    # Check if any changes were made
    if content == original_content:
        return False, ["No changes needed"]
    
    # Write back the modified content
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes
    except Exception as e:
        return False, [f"Error writing file: {e}"]


def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in the given directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files


def main():
    """Main migration function."""
    print("🚀 Starting AstolfoLogger migration...")
    
    total_files = 0
    migrated_files = 0
    
    for target_dir in TARGET_DIRS:
        if not os.path.exists(target_dir):
            print(f"⚠️  Directory {target_dir} not found, skipping...")
            continue
        
        print(f"\n📁 Processing {target_dir}/...")
        python_files = find_python_files(target_dir)
        
        for filepath in python_files:
            total_files += 1
            success, details = process_file(filepath)
            
            if success:
                migrated_files += 1
                print(f"✅ {filepath}")
                for detail in details:
                    print(f"   - {detail}")
            else:
                if details[0] != "No logging imports found" and details[0] != "Skipped (in skip list)":
                    print(f"❌ {filepath}: {details[0]}")
    
    print(f"\n📊 Migration Summary:")
    print(f"   Total files scanned: {total_files}")
    print(f"   Files migrated: {migrated_files}")
    print(f"   Migration rate: {migrated_files/total_files*100:.1f}%")
    
    print("\n⚠️  Important: Please run the following commands to verify:")
    print("   1. uv run --python 3.13 python -m mypy src/")
    print("   2. uv run --python 3.13 python -m unittest discover")
    print("   3. Review the changes with: git diff")


if __name__ == "__main__":
    main()