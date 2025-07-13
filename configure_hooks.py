#!/usr/bin/env python3
"""Configure Claude Code hooks for Discord notifications.

This script sets up the integration between Claude Code's hook system
and Discord notifications by modifying Claude Code's settings.json.

Usage:
    uv run --no-sync --python 3.13 python configure_hooks.py [--remove]
    # Or if you have Python 3.13+:
    python3.13 configure_hooks.py [--remove]
"""

# Python version check - must be first before any imports that might fail
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

# Import AstolfoLogger for structured logging
from src.utils.astolfo_logger import AstolfoLogger, setup_astolfo_logger

if TYPE_CHECKING:
    from src.settings_types import ClaudeSettings

HookEventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]

# Initialize logger globally for the module
logger: AstolfoLogger = setup_astolfo_logger(__name__)


def check_uv_available() -> bool:
    """Check if uv is available in the system PATH."""
    logger.debug("Checking uv availability")
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=False)  # noqa: S607
        logger.debug("uv command executed", context={
            "returncode": result.returncode,
            "stdout": result.stdout.strip() if result.stdout else "",
            "stderr": result.stderr.strip() if result.stderr else ""
        })
        return result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        logger.debug("uv command failed", context={
            "error_type": type(e).__name__,
            "error": str(e)
        })
        return False


def atomic_write(filepath: str | Path, content: str) -> None:
    """Write content to file atomically using temp file + rename."""
    filepath = Path(filepath)
    logger.debug("Starting atomic write", context={
        "target_file": str(filepath),
        "content_size": len(content),
        "parent_dir": str(filepath.parent)
    })

    # Create temp file in same directory for same filesystem
    fd, temp_path = tempfile.mkstemp(dir=filepath.parent, text=True)
    logger.debug("Temporary file created", context={
        "temp_path": temp_path,
        "file_descriptor": fd
    })

    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        logger.debug("Content written to temp file", context={
            "temp_path": temp_path,
            "bytes_written": len(content.encode())
        })

        # Atomic rename
        Path(temp_path).rename(filepath)
        logger.info("Atomic write completed successfully", context={
            "target_file": str(filepath),
            "content_size": len(content)
        })
    except OSError as e:
        # Clean up temp file on error - catch filesystem-related exceptions
        logger.exception("Atomic write failed", exception=e, context={
            "target_file": str(filepath),
            "temp_path": temp_path,
            "content_size": len(content)
        })
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
    logger.debug("Finding project root", context={
        "current_dir": str(current)
    })

    # Look for project indicators
    for parent in [current, *current.parents]:
        logger.debug("Checking parent directory", context={
            "parent": str(parent),
            "pyproject_exists": (parent / "pyproject.toml").exists()
        })

        # Check for pyproject.toml first
        if (parent / "pyproject.toml").exists():
            # Use full_match to verify it's our project
            notifier_path = parent / "src" / "discord_notifier.py"
            if notifier_path.exists() and notifier_path.full_match("**/src/discord_notifier.py"):
                logger.info("Project root found via pyproject.toml", context={
                    "project_root": str(parent),
                    "notifier_path": str(notifier_path)
                })
                return parent

        # Also check for the notifier script directly
        for path in parent.rglob("discord_notifier.py"):
            if path.full_match("**/src/discord_notifier.py"):
                project_root = path.parent.parent
                logger.info("Project root found via notifier script", context={
                    "project_root": str(project_root),
                    "notifier_path": str(path)
                })
                return project_root

    logger.warning("Project root not found", context={
        "searched_from": str(current),
        "fallback_strategy": "Will use script parent directory"
    })
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
    """Get the appropriate Python command, requiring Python 3.13+."""
    logger.debug("Determining Python command", context={
        "script_path": str(script_path)
    })

    if check_uv_available():
        # Use uv to ensure Python 3.13+ is used
        command = f"uv run --no-sync --python 3.13 python {script_path}"
        logger.info("Using uv for Python 3.13+", context={
            "command": command
        })
        return command

    # Check if python3.13 is available
    try:
        result = subprocess.run(["python3.13", "--version"], capture_output=True, text=True, check=True)
        if result.returncode == 0:
            print("✓ Using python3.13")
            command = f"python3.13 {script_path}"
            logger.info("Using system python3.13", context={
                "command": command,
                "version_output": result.stdout.strip()
            })
            return command
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.exception("python3.13 not available", exception=e, context={
            "script_path": str(script_path)
        })

    # Fatal error - Python 3.13+ is required
    logger.error("Python 3.13+ requirement not met", context={
        "script_path": str(script_path),
        "uv_available": False,
        "python313_available": False,
        "ai_todo": "User needs to install Python 3.13+ or uv to proceed"
    })

    print("❌ Error: Python 3.13+ is required but not found!")
    print("   This project uses Python 3.13 features (TypeIs, ReadOnly).")
    print("   Please install Python 3.13+ or use uv:")
    print("   - Install uv: https://github.com/astral-sh/uv")
    print("   - Or install Python 3.13+: https://www.python.org/downloads/")
    sys.exit(1)


def _main_impl() -> int:
    """Main implementation split from main() to reduce complexity."""
    parser = argparse.ArgumentParser(description="Configure Claude Code hooks for Discord notifications")
    parser.add_argument("--remove", action="store_true", help="Remove the notifier from Claude Code")
    args = parser.parse_args()

    logger.info("Configure hooks started", context={
        "operation": "remove" if args.remove else "install",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    })

    # Paths
    claude_dir = Path.home() / ".claude"
    hooks_dir = claude_dir / "hooks"
    settings_file = claude_dir / "settings.json"

    logger.debug("Environment paths", context={
        "claude_dir": str(claude_dir),
        "hooks_dir": str(hooks_dir),
        "settings_file": str(settings_file),
        "settings_exists": settings_file.exists()
    })

    # Find project root using Path.full_match()
    project_root = find_project_root()
    if project_root is None:
        # Fallback to script parent
        project_root = Path(__file__).parent
        logger.warning("Using fallback project root", context={
            "fallback_root": str(project_root)
        })

    # Source script in the project directory
    source_script = project_root / "src" / "discord_notifier.py"

    logger.debug("Project structure", context={
        "project_root": str(project_root),
        "source_script": str(source_script),
        "source_exists": source_script.exists()
    })

    if args.remove:
        return _handle_remove_command(settings_file)
    return _handle_install_command(hooks_dir, settings_file, source_script)


def main() -> int:
    """Configure Claude Code hooks for Discord notifications."""
    try:
        # Split into smaller functions to reduce complexity
        result = _main_impl()
        logger.info("Configure hooks completed", context={
            "exit_code": result,
            "success": result == 0
        })
        return result
    except Exception as e:
        logger.exception("Configure hooks failed unexpectedly", exception=e, context={
            "ai_todo": "Critical error in configure_hooks.py - review stack trace"
        })
        print(f"❌ Unexpected error: {e}")
        return 1
    finally:
        # Ensure logs are saved before exit
        logger.stop()


def _handle_remove_command(settings_file: Path) -> int:
    """Handle remove command to uninstall the notifier."""
    logger.info("Starting notifier removal process")
    print("Removing Claude Code Discord Notifier...")

    # Note: Script removal not needed since we're using source directly
    print("✓ Notifier hooks will be removed from settings.json")
    logger.debug("Removal strategy", context={
        "method": "filter_hooks from settings.json",
        "preserve_other_hooks": True
    })

    # Remove from settings.json
    if settings_file.exists():
        logger.debug("Reading existing settings file", context={
            "settings_file": str(settings_file)
        })

        try:
            with settings_file.open() as f:
                settings_data = json.load(f)

            logger.debug("Settings file loaded", context={
                "has_hooks": "hooks" in settings_data,
                "total_keys": len(settings_data.keys()) if isinstance(settings_data, dict) else 0
            })

            # Type cast to ensure proper typing
            settings = cast("ClaudeSettings", settings_data)

            # Remove discord notifier hooks
            if "hooks" in settings:
                hooks_removed = 0
                for event_type in cast("list[HookEventType]", list(settings["hooks"].keys())):
                    original_count = len(settings["hooks"][event_type])
                    settings["hooks"][event_type] = filter_hooks(settings["hooks"][event_type])
                    removed_count = original_count - len(settings["hooks"][event_type])
                    hooks_removed += removed_count

                    logger.debug("Filtered hooks for event", context={
                        "event_type": event_type,
                        "original_count": original_count,
                        "remaining_count": len(settings["hooks"][event_type]),
                        "removed_count": removed_count
                    })

                logger.info("Discord notifier hooks removed", context={
                    "total_hooks_removed": hooks_removed
                })

            atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")
            print("✓ Removed hooks from settings.json")
            logger.info("Settings file updated successfully")

        except (json.JSONDecodeError, OSError) as e:
            logger.exception("Failed to update settings file", exception=e, context={
                "settings_file": str(settings_file),
                "ai_todo": "Settings file corruption or permission issue"
            })
            print(f"❌ Error updating settings file: {e}")
            return 1
    else:
        logger.warning("Settings file does not exist", context={
            "settings_file": str(settings_file),
            "action": "Nothing to remove"
        })

    print("\nRemoval complete!")
    logger.info("Notifier removal completed successfully")
    return 0


def _handle_install_command(hooks_dir: Path, settings_file: Path, source_script: Path) -> int:
    """Handle install command to setup the notifier."""
    logger.info("Starting notifier installation process", context={
        "hooks_dir": str(hooks_dir),
        "settings_file": str(settings_file),
        "source_script": str(source_script)
    })
    print("Installing Claude Code Discord Notifier...")

    # Check source exists
    if not source_script.exists():
        logger.error("Source script not found", context={
            "source_script": str(source_script),
            "ai_todo": "Source script missing - check project structure"
        })
        print(f"Error: Source script not found at {source_script}")
        return 1

    logger.debug("Source script validated", context={
        "source_script": str(source_script),
        "file_size": source_script.stat().st_size if source_script.exists() else 0
    })

    # Create directories
    hooks_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Hooks directory ensured", context={
        "hooks_dir": str(hooks_dir),
        "already_existed": hooks_dir.exists()
    })

    # Make source script executable
    old_mode = source_script.stat().st_mode if source_script.exists() else 0
    source_script.chmod(0o755)
    logger.debug("Source script permissions updated", context={
        "source_script": str(source_script),
        "old_mode": oct(old_mode),
        "new_mode": "0o755"
    })
    print(f"✓ Using source script at {source_script}")

    # Update settings.json
    try:
        if settings_file.exists():
            logger.debug("Loading existing settings file")
            with settings_file.open() as f:
                settings_data = json.load(f)
        else:
            logger.debug("Creating new settings file")
            settings_data = {}

        logger.debug("Settings data loaded", context={
            "has_hooks": "hooks" in settings_data,
            "settings_keys": list(settings_data.keys()) if isinstance(settings_data, dict) else []
        })

        # Type cast to ensure proper typing
        settings = cast("ClaudeSettings", settings_data)

        if "hooks" not in settings:
            settings["hooks"] = {}
            logger.debug("Initialized hooks section in settings")

        # Define hooks for each event type
        events: list[HookEventType] = [
            "PreToolUse",
            "PostToolUse",
            "Notification",
            "Stop",
            "SubagentStop",
        ]

        logger.debug("Processing hook events", context={
            "events": events,
            "total_events": len(events)
        })

        hooks_added = 0
        for event in events:
            if event not in settings["hooks"]:
                settings["hooks"][event] = []
                logger.debug(f"Initialized {event} hook list")

            # Remove any existing discord notifier hooks
            hooks_list: list[HookConfig] = settings["hooks"][event]
            original_count = len(hooks_list)
            settings["hooks"][event] = filter_hooks(hooks_list)
            removed_count = original_count - len(settings["hooks"][event])

            logger.debug("Filtered existing hooks", context={
                "event": event,
                "original_count": original_count,
                "removed_count": removed_count,
                "remaining_count": len(settings["hooks"][event])
            })

            # Add new hook using imported helper functions
            # Use absolute path to source script with uv for Python 3.13+
            python_cmd = get_python_command(source_script.absolute())
            command = f"CLAUDE_HOOK_EVENT={event} {python_cmd}"
            hook_config = create_hook_config(event, command, ".*")

            logger.debug("Created hook config", context={
                "event": event,
                "command": command,
                "config_type": type(hook_config).__name__
            })

            # Append the new config - now properly typed
            settings["hooks"][event].append(hook_config)  # type: ignore[arg-type]
            hooks_added += 1

        logger.info("Hook configuration completed", context={
            "hooks_added": hooks_added,
            "events_configured": len(events)
        })

        # Save settings
        settings_file.parent.mkdir(exist_ok=True)
        atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")

        print(f"✓ Updated {settings_file}")
        logger.info("Settings file updated successfully")

        # Create .env from template if it doesn't exist
        env_file = Path.cwd() / ".env"
        env_example = Path.cwd() / ".env.example"

        logger.debug("Checking environment files", context={
            "env_file": str(env_file),
            "env_exists": env_file.exists(),
            "env_example": str(env_example),
            "example_exists": env_example.exists()
        })

        if not env_file.exists() and env_example.exists():
            # Copy .env.example to .env
            env_content = env_example.read_text()
            env_file.write_text(env_content)
            print("✓ Created .env from template")
            logger.info("Environment file created from template", context={
                "source": str(env_example),
                "target": str(env_file),
                "content_size": len(env_content)
            })
        elif not env_file.exists():
            print("⚠️  Warning: No .env file found. Copy .env.example to .env and configure")
            logger.warning("No environment file or template found", context={
                "env_file": str(env_file),
                "env_example": str(env_example)
            })

        print("\n✅ Installation complete!")
        logger.info("Installation completed successfully")

        # Inform about Python version handling
        if check_uv_available():
            print("\n✓ Using uv to ensure Python 3.13+ for hook execution")
            logger.info("uv available for Python version management")
        else:
            print("\n⚠️  Warning: uv not found. Install uv to ensure Python 3.13+ is used:")
            print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
            print("  Using system python3 - requires Python 3.13+ to be installed")
            logger.warning("uv not available", context={
                "recommendation": "Install uv for Python version management"
            })

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

    except (json.JSONDecodeError, OSError) as e:
        logger.exception("Failed to update settings during installation", exception=e, context={
            "settings_file": str(settings_file),
            "source_script": str(source_script),
            "ai_todo": "Installation failed due to settings file issue"
        })
        print(f"❌ Error updating settings file: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
