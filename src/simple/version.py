#!/usr/bin/env python3
"""Version information for Simple Architecture."""

import subprocess
import sys
from pathlib import Path

# Version info
VERSION = "1.1"
RELEASE_DATE = "2025.07.19"

def get_git_commit() -> str:
    """Get current git commit hash (short)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

def get_version_string() -> str:
    """Get full version string."""
    git_commit = get_git_commit()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    return f"Simple Notifier v{RELEASE_DATE}-{git_commit} • Python {python_version}"

# Pre-computed version string for performance
VERSION_STRING = get_version_string()