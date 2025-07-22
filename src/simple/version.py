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
        # Use shutil.which to find git executable
        import shutil

        git_path = shutil.which("git")
        if not git_path:
            return "unknown"

        result = subprocess.run(
            [git_path, "rev-parse", "--short", "HEAD"],
            check=False, capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        # Handle subprocess errors, OS errors, and missing git
        pass
    return "unknown"


def get_version_string() -> str:
    """Get full version string."""
    git_commit = get_git_commit()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return f"Simple Notifier v{RELEASE_DATE}-{git_commit} • Python {python_version}"


# Pre-computed version string for performance
VERSION_STRING = get_version_string()
