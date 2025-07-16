#!/usr/bin/env python3
"""Hook validation utilities for Discord Notifier - Standalone version.

This module provides functions to validate that the hook system is calling
the latest version of the code and detect any version mismatches.
"""

import subprocess
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict


class HookValidationResult(TypedDict):
    """Hook validation result structure."""

    is_latest_version: bool
    hook_version: str
    expected_version: str
    module_path: str
    last_modified: str
    python_path: list[str]
    validation_timestamp: str
    issues: list[str]


def get_git_commit_hash() -> str:
    """Get current Git commit hash."""
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=5)
        return result.stdout.strip()[:8]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return "unknown"


def validate_hook_version() -> HookValidationResult:
    """Validate that the hook is using the latest version.

    Returns:
        Validation result with version information and issues
    """
    issues: list[str] = []
    current_time = datetime.now(timezone.utc).isoformat()

    # Get current commit hash
    commit_hash = get_git_commit_hash()
    version_tag = f"v2025.07.15-{commit_hash}"

    # Get the actual path of this module
    module_path = str(Path(__file__).parent.parent)

    # Check if we're running from the expected location
    expected_paths = [
        "/home/ubuntu/workbench/projects/claude-code-event-notifier-bugfix/src",
        "/home/ubuntu/workbench/projects/claude-code-event-notifier/src",
    ]

    is_expected_path = any(module_path.startswith(path) for path in expected_paths)
    if not is_expected_path:
        issues.append(f"Module running from unexpected path: {module_path}")

    # Check Python path for potential conflicts
    python_path = sys.path.copy()

    # Look for multiple discord_notifier modules
    discord_notifier_paths = []
    for path in python_path:
        potential_notifier = Path(path) / "discord_notifier.py"
        if potential_notifier.exists():
            discord_notifier_paths.append(str(potential_notifier))

    if len(discord_notifier_paths) > 1:
        issues.append(f"Multiple discord_notifier modules found: {discord_notifier_paths}")

    # Get file modification time
    try:
        main_module_path = Path(module_path) / "discord_notifier.py"
        if main_module_path.exists():
            mtime = main_module_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, timezone.utc).isoformat()
        else:
            last_modified = "file_not_found"
            issues.append("Main discord_notifier.py not found")
    except OSError as e:
        last_modified = f"error: {e}"
        issues.append(f"Could not get file modification time: {e}")

    # Check for module cache issues
    discord_notifier_in_cache = "discord_notifier" in sys.modules
    if discord_notifier_in_cache:
        cached_module = sys.modules["discord_notifier"]
        cached_file = getattr(cached_module, "__file__", "unknown")
        if cached_file != str(main_module_path):
            issues.append(f"Cached module path mismatch: {cached_file} vs {main_module_path}")

    # Determine if we're using the latest version
    is_latest = len(issues) == 0

    return HookValidationResult(
        is_latest_version=is_latest,
        hook_version=version_tag,
        expected_version=version_tag,
        module_path=module_path,
        last_modified=last_modified,
        python_path=python_path,
        validation_timestamp=current_time,
        issues=issues,
    )


def get_hook_diagnostic_info() -> dict[str, str | list[str] | bool]:
    """Get comprehensive diagnostic information for hook debugging.

    Returns:
        Diagnostic information dictionary
    """
    validation = validate_hook_version()

    return {
        "validation_result": validation,
        "current_working_directory": str(Path.cwd()),
        "script_file_location": str(Path(__file__)),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "environment_variables": {
            key: value for key, value in os.environ.items() if key.startswith(("DISCORD_", "CLAUDE_", "PYTHON"))
        },
        "sys_path_relevant": [
            path
            for path in sys.path
            if "claude" in path.lower() or "discord" in path.lower() or "workbench" in path.lower()
        ],
        "loaded_modules_relevant": [
            module
            for module in sys.modules.keys()
            if "discord" in module or "claude" in module or module.startswith("src.")
        ],
    }


if __name__ == "__main__":
    # Test hook validation
    import json

    print("🔍 Hook Validation Results:")
    validation = validate_hook_version()
    print(json.dumps(validation, indent=2))

    if not validation["is_latest_version"]:
        print("\n⚠️  Issues found:")
        for issue in validation["issues"]:
            print(f"  - {issue}")
    else:
        print("\n✅ Hook is using the latest version!")

    print(f"\n📊 Diagnostic Info:")
    diagnostic = get_hook_diagnostic_info()
    print(json.dumps(diagnostic, indent=2, default=str))
