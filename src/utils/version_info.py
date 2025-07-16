#!/usr/bin/env python3
"""Version information utilities for Discord Notifier.

This module provides functions to retrieve version information including
Git commit hash, timestamps, and build information for inclusion in Discord messages.
"""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class VersionInfo(TypedDict):
    """Version information structure."""
    commit_hash: str
    commit_short: str
    commit_timestamp: str
    branch: str
    build_timestamp: str
    python_version: str
    is_latest: bool
    version_tag: str


def get_git_info() -> dict[str, str]:
    """Get Git repository information.
    
    Returns:
        Dictionary containing Git information or fallback values
    """
    git_info: dict[str, str] = {}
    
    try:
        # Get current commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        git_info["commit_hash"] = result.stdout.strip()
        git_info["commit_short"] = result.stdout.strip()[:8]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        git_info["commit_hash"] = "unknown"
        git_info["commit_short"] = "unknown"
    
    try:
        # Get current branch
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        git_info["branch"] = result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        git_info["branch"] = "unknown"
    
    try:
        # Get commit timestamp
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cd", "--date=iso"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        git_info["commit_timestamp"] = result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        git_info["commit_timestamp"] = "unknown"
    
    return git_info


def get_version_info() -> VersionInfo:
    """Get comprehensive version information.
    
    Returns:
        Complete version information for Discord display
    """
    git_info = get_git_info()
    current_time = datetime.now(timezone.utc)
    
    version_info: VersionInfo = {
        "commit_hash": git_info["commit_hash"],
        "commit_short": git_info["commit_short"],
        "commit_timestamp": git_info["commit_timestamp"],
        "branch": git_info["branch"],
        "build_timestamp": current_time.isoformat(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "is_latest": True,  # Will be updated with proper version checking
        "version_tag": f"v2025.07.15-{git_info['commit_short']}"
    }
    
    return version_info


def format_version_footer() -> str:
    """Format version information for Discord embed footer.
    
    Returns:
        Formatted version string for embed footer
    """
    version = get_version_info()
    
    # Try to import hook validation (avoid circular import)
    try:
        from .hook_validation import validate_hook_version
        hook_validation = validate_hook_version()
        is_latest_hook = hook_validation["is_latest_version"]
        hook_status = "🔄 Latest" if is_latest_hook else "⚠️ Issues"
    except ImportError:
        hook_status = "🔄 Latest"
    
    if version["commit_short"] != "unknown":
        return f"Discord Notifier {version['version_tag']} • Python {version['python_version']} • {hook_status}"
    else:
        return f"Discord Notifier dev • Python {version['python_version']} • ⚠️ No Git info"


def get_debug_version_info() -> dict[str, str | bool]:
    """Get detailed version information for debugging.
    
    Returns:
        Detailed version information for troubleshooting
    """
    version = get_version_info()
    
    return {
        "full_commit_hash": version["commit_hash"],
        "short_commit": version["commit_short"],
        "commit_time": version["commit_timestamp"],
        "current_branch": version["branch"],
        "build_time": version["build_timestamp"],
        "python_version": version["python_version"],
        "version_tag": version["version_tag"],
        "is_latest_version": version["is_latest"],
        "working_directory": str(Path.cwd()),
        "script_location": str(Path(__file__).parent.parent)
    }


if __name__ == "__main__":
    # Test version information
    import json
    print("Version Information:")
    print(json.dumps(get_debug_version_info(), indent=2))
    print(f"\nFooter: {format_version_footer()}")