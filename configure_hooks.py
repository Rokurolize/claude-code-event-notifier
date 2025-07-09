#!/usr/bin/env python3
"""Configure Claude Code hooks for Discord notifications.

This script sets up the integration between Claude Code's hook system
and Discord notifications by modifying Claude Code's settings.json.

Usage: python3 configure_hooks.py [--remove]
"""

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeGuard, cast

# Import all types from settings_types module
from src.settings_types import HookConfig, create_hook_config

if TYPE_CHECKING:
    from src.settings_types import ClaudeSettings

HookEventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]


def check_uv_available() -> bool:
    """Check if uv is available in the system PATH."""
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=False)  # noqa: S607
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    else:
        return result.returncode == 0


def atomic_write(filepath: str | Path, content: str) -> None:
    """Write content to file atomically using temp file + rename."""
    filepath = Path(filepath)
    # Create temp file in same directory for same filesystem
    fd, temp_path = tempfile.mkstemp(dir=filepath.parent, text=True)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic rename
        Path(temp_path).rename(filepath)
    except OSError:
        # Clean up temp file on error - catch filesystem-related exceptions
        with contextlib.suppress(OSError):
            Path(temp_path).unlink()
        raise


def is_hook_config(value: object) -> TypeGuard[HookConfig]:
    """Type guard to check if a value is a valid HookConfig."""
    if not isinstance(value, dict):
        return False

    hooks_list = value.get("hooks")
    if not isinstance(hooks_list, list) or not hooks_list:
        return False

    # Check if all entries in hooks list are valid HookEntry
    for hook in hooks_list:
        if not isinstance(hook, dict):
            return False
        if not isinstance(hook.get("type"), str):
            return False
        if not isinstance(hook.get("command"), str):
            return False

    # Check optional matcher field for tool events
    return not ("matcher" in value and not isinstance(value["matcher"], str))


def find_project_root() -> Path | None:
    """Find project root using Path.full_match() for better pattern matching.

    Returns:
        Path to project root directory, or None if not found
    """
    current = Path.cwd()

    # Look for project indicators
    for parent in [current, *current.parents]:
        # Check for pyproject.toml first
        if (parent / "pyproject.toml").exists():
            # Use full_match to verify it's our project
            notifier_path = parent / "src" / "discord_notifier.py"
            if notifier_path.exists() and notifier_path.full_match("**/src/discord_notifier.py"):
                return parent

        # Also check for the notifier script directly
        for path in parent.rglob("discord_notifier.py"):
            if path.full_match("**/src/discord_notifier.py"):
                return path.parent.parent

    return None


def should_keep_hook(hook: HookConfig) -> bool:
    """Check if a hook should be kept (i.e., it's not a discord notifier hook).

    This function safely navigates the hook structure to check if it contains
    a discord_notifier.py command, using type guards at each level.
    """
    if not is_hook_config(hook):
        return True

    # Now we know hook is a valid HookConfig, so we can safely access fields
    first_hook = hook["hooks"][0]
    command = first_hook["command"]

    # Check if it's a discord notifier command using Path operations
    # Extract script path from command
    parts = command.split()
    for part in parts:
        if part.endswith(".py"):
            try:
                script_path = Path(part)
                # Use full_match for pattern checking
                if script_path.full_match("**/discord_notifier.py"):
                    return False
            except (ValueError, TypeError):
                # Invalid path, continue checking other parts
                continue

    # Fallback to simple string check
    return "discord_notifier.py" not in command


def filter_hooks(event_hooks: list[HookConfig]) -> list[HookConfig]:
    """Filter out discord notifier hooks from a list of hooks."""
    return [hook for hook in event_hooks if should_keep_hook(hook)]


def get_python_command(script_path: Path) -> str:
    """Get the appropriate Python command, preferring uv with Python 3.13+."""
    if check_uv_available():
        # Use uv to ensure Python 3.13+ is used
        return f"uv run --no-sync --python 3.13 python {script_path}"
    # Fall back to system python3
    print("⚠️  Warning: uv not found, using system python3. Python 3.13+ required.")
    return f"python3 {script_path}"


def _main_impl() -> int:
    """Main implementation split from main() to reduce complexity."""
    parser = argparse.ArgumentParser(description="Configure Claude Code hooks for Discord notifications")
    parser.add_argument("--remove", action="store_true", help="Remove the notifier from Claude Code")
    args = parser.parse_args()

    # Paths
    claude_dir = Path.home() / ".claude"
    hooks_dir = claude_dir / "hooks"
    settings_file = claude_dir / "settings.json"

    # Find project root using Path.full_match()
    project_root = find_project_root()
    if project_root is None:
        # Fallback to script parent
        project_root = Path(__file__).parent

    # Source script in the project directory
    source_script = project_root / "src" / "discord_notifier.py"

    if args.remove:
        return _handle_remove_command(settings_file)
    return _handle_install_command(hooks_dir, settings_file, source_script)


def main() -> int:
    """Configure Claude Code hooks for Discord notifications."""
    # Split into smaller functions to reduce complexity
    return _main_impl()


def _handle_remove_command(settings_file: Path) -> int:
    """Handle remove command to uninstall the notifier."""
    print("Removing Claude Code Discord Notifier...")

    # Note: Script removal not needed since we're using source directly
    print("✓ Notifier hooks will be removed from settings.json")

    # Remove from settings.json
    if settings_file.exists():
        with settings_file.open() as f:
            settings_data = json.load(f)

        # Type cast to ensure proper typing
        settings = cast("ClaudeSettings", settings_data)

        # Remove discord notifier hooks
        if "hooks" in settings:
            for event_type in cast("list[HookEventType]", list(settings["hooks"].keys())):
                settings["hooks"][event_type] = filter_hooks(settings["hooks"][event_type])

        atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")
        print("✓ Removed hooks from settings.json")

    print("\nRemoval complete!")
    return 0


def _handle_install_command(hooks_dir: Path, settings_file: Path, source_script: Path) -> int:
    """Handle install command to setup the notifier."""
    print("Installing Claude Code Discord Notifier...")

    # Check source exists
    if not source_script.exists():
        print(f"Error: Source script not found at {source_script}")
        return 1

    # Create directories
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Make source script executable
    source_script.chmod(0o755)
    print(f"✓ Using source script at {source_script}")

    # Update settings.json
    if settings_file.exists():
        with settings_file.open() as f:
            settings_data = json.load(f)
    else:
        settings_data = {}

    # Type cast to ensure proper typing
    settings = cast("ClaudeSettings", settings_data)

    if "hooks" not in settings:
        settings["hooks"] = {}

    # Define hooks for each event type
    events: list[HookEventType] = [
        "PreToolUse",
        "PostToolUse",
        "Notification",
        "Stop",
        "SubagentStop",
    ]

    for event in events:
        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        # Remove any existing discord notifier hooks
        hooks_list: list[HookConfig] = settings["hooks"][event]
        settings["hooks"][event] = filter_hooks(hooks_list)

        # Add new hook using imported helper functions
        # Use absolute path to source script with uv for Python 3.13+
        python_cmd = get_python_command(source_script.absolute())
        command = f"CLAUDE_HOOK_EVENT={event} {python_cmd}"
        hook_config = create_hook_config(event, command, ".*")

        # Append the new config - now properly typed
        settings["hooks"][event].append(hook_config)  # type: ignore[arg-type]

    # Save settings
    settings_file.parent.mkdir(exist_ok=True)
    atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")

    print("✓ Updated settings.json")

    # Create .env from template if it doesn't exist
    env_file = Path.cwd() / ".env"
    env_example = Path.cwd() / ".env.example"

    if not env_file.exists() and env_example.exists():
        # Copy .env.example to .env
        env_file.write_text(env_example.read_text())
        print("✓ Created .env from template")
    elif not env_file.exists():
        print("⚠️  Warning: No .env file found. Copy .env.example to .env and configure")

    print("\n✅ Installation complete!")

    # Inform about Python version handling
    if check_uv_available():
        print("\n✓ Using uv to ensure Python 3.13+ for hook execution")
    else:
        print("\n⚠️  Warning: uv not found. Install uv to ensure Python 3.13+ is used:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  Using system python3 - requires Python 3.13+ to be installed")

    print("\nNext steps:")
    if not env_file.exists():
        print("1. Copy .env.example to .env")
        print("2. Edit .env with your Discord credentials")
        print("3. Restart Claude Code")
    else:
        print("1. Edit .env with your Discord credentials (if not already configured)")
        print("2. Restart Claude Code")
    print("\nNote: Environment variables take precedence over .env file.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
