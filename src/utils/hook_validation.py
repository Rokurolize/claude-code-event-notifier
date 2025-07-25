#!/usr/bin/env python3
"""Hook validation utilities for Discord Notifier.

This module provides functions to validate that the hook system is calling
the latest version of the code and detect any version mismatches.
"""

import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

# Try different import methods
try:
    from src.utils.version_info import get_version_info
except ImportError:
    try:
        from .version_info import get_version_info
    except ImportError:
        # Fallback for when run as script
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.version_info import get_version_info


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


def validate_hook_version() -> HookValidationResult:
    """Validate that the hook is using the latest version.

    Returns:
        Validation result with version information and issues
    """
    issues: list[str] = []
    current_time = datetime.now(timezone.utc).isoformat()

    # Get current version info
    version_info = get_version_info()

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

    # Look for multiple main.py modules in potential Discord notifier locations
    main_py_paths = []
    seen_paths = set()
    for path in python_path:
        potential_main = Path(path) / "src" / "main.py"
        if potential_main.exists():
            main_path_str = str(potential_main.resolve())
            if main_path_str not in seen_paths:
                main_py_paths.append(main_path_str)
                seen_paths.add(main_path_str)

    if len(main_py_paths) > 1:
        issues.append(f"Multiple Discord notifier main.py modules found: {main_py_paths}")

    # Get file modification time
    try:
        main_module_path = Path(module_path) / "main.py"
        if main_module_path.exists():
            mtime = main_module_path.stat().st_mtime
            last_modified = datetime.fromtimestamp(mtime, timezone.utc).isoformat()
        else:
            last_modified = "file_not_found"
            issues.append("Main src/main.py not found")
    except OSError as e:
        last_modified = f"error: {e}"
        issues.append(f"Could not get file modification time: {e}")

    # Check for module cache issues (main.py architecture)
    main_module_in_cache = "src.main" in sys.modules
    if main_module_in_cache:
        cached_module = sys.modules["src.main"]
        cached_file = getattr(cached_module, "__file__", "unknown")
        if cached_file != str(main_module_path):
            issues.append(f"Cached module path mismatch: {cached_file} vs {main_module_path}")
    
    # Legacy check - warn if old discord_notifier is still cached
    if "discord_notifier" in sys.modules:
        issues.append("Legacy discord_notifier module still in cache - should use new main.py architecture")

    # Determine if we're using the latest version
    is_latest = len(issues) == 0

    return HookValidationResult(
        is_latest_version=is_latest,
        hook_version=version_info["version_tag"],
        expected_version=version_info["version_tag"],
        module_path=module_path,
        last_modified=last_modified,
        python_path=python_path,
        validation_timestamp=current_time,
        issues=issues,
    )


def clear_module_cache() -> bool:
    """Clear Python module cache for Discord notifier modules.

    Returns:
        True if cache was cleared successfully
    """
    try:
        modules_to_clear = [
            # Legacy modules (for cleanup)
            "discord_notifier",
            "src.discord_notifier",
            # New architecture modules
            "src.main",
            "src.core.config",
            "src.handlers.discord_sender",
            "src.formatters.event_formatters",
            "src.utils.version_info",
            "src.utils.hook_validation",
        ]

        for module_name in modules_to_clear:
            if module_name in sys.modules:
                del sys.modules[module_name]

        return True
    except Exception:
        return False


def force_reload_modules() -> bool:
    """Force reload of Discord notifier modules.

    Returns:
        True if reload was successful
    """
    try:
        # Clear cache first
        clear_module_cache()

        # Force reimport of new architecture modules
        for module_name in ["src.main", "src.core.config", "src.handlers.discord_sender"]:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])

        return True
    except Exception:
        return False


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
