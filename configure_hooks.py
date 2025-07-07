#!/usr/bin/env python3
"""Configure Claude Code hooks for Discord notifications.

This script sets up the integration between Claude Code's hook system
and Discord notifications by modifying Claude Code's settings.json.

Usage: python3 configure_hooks.py [--remove]
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, TypeGuard, cast

# Import all types from settings_types module
from src.settings_types import (
    ClaudeSettings,
    HookConfig,
    HookEventType,
    create_hook_config,
)


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
        os.rename(temp_path, filepath)
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise e


def is_hook_config(value: Any) -> TypeGuard[HookConfig]:
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
    if "matcher" in value and not isinstance(value["matcher"], str):
        return False

    return True


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

    # Check if it's a discord notifier command
    return "discord_notifier.py" not in command


def filter_hooks(event_hooks: list[HookConfig]) -> list[HookConfig]:
    """Filter out discord notifier hooks from a list of hooks."""
    return [hook for hook in event_hooks if should_keep_hook(hook)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Configure Claude Code hooks for Discord notifications"
    )
    parser.add_argument(
        "--remove", action="store_true", help="Remove the notifier from Claude Code"
    )
    args = parser.parse_args()

    # Paths
    claude_dir = Path.home() / ".claude"
    hooks_dir = claude_dir / "hooks"
    settings_file = claude_dir / "settings.json"

    # Source and target for the notifier script
    source_script = Path(__file__).parent / "src" / "discord_notifier.py"
    target_script = hooks_dir / "discord_notifier.py"

    if args.remove:
        print("Removing Claude Code Discord Notifier...")

        # Remove script
        if target_script.exists():
            target_script.unlink()
            print(f"✓ Removed {target_script}")

        # Remove from settings.json
        if settings_file.exists():
            with open(settings_file) as f:
                settings_data = json.load(f)

            # Type cast to ensure proper typing
            settings = cast("ClaudeSettings", settings_data)

            # Remove discord notifier hooks
            if "hooks" in settings:
                for event_type in list(settings["hooks"].keys()):
                    settings["hooks"][event_type] = filter_hooks(
                        settings["hooks"][event_type]
                    )

            atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")
            print("✓ Removed hooks from settings.json")

        print("\nRemoval complete!")
        return 0

    # Install mode
    print("Installing Claude Code Discord Notifier...")

    # Check source exists
    if not source_script.exists():
        print(f"Error: Source script not found at {source_script}")
        return 1

    # Create directories
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Copy script
    shutil.copy2(source_script, target_script)
    target_script.chmod(0o755)  # Make executable
    print(f"✓ Copied notifier to {target_script}")

    # Update settings.json
    if settings_file.exists():
        with open(settings_file) as f:
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
        command = f"CLAUDE_HOOK_EVENT={event} python3 {target_script}"
        hook_config = create_hook_config(event, command, ".*")

        # Append the new config - now properly typed
        settings["hooks"][event].append(hook_config)  # type: ignore[arg-type]

    # Save settings
    claude_dir.mkdir(exist_ok=True)
    atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")

    print("✓ Updated settings.json")

    # Create example config if it doesn't exist
    env_example = hooks_dir / ".env.discord.example"
    if not env_example.exists():
        env_example.write_text("""# Discord Configuration
# Option 1: Webhook (recommended)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN

# Option 2: Bot Token
# DISCORD_TOKEN=your_bot_token_here
# DISCORD_CHANNEL_ID=your_channel_id_here

# Optional: Enable debug logging
# DISCORD_DEBUG=1

# Optional: Thread support for session organization
# DISCORD_USE_THREADS=1
# DISCORD_CHANNEL_TYPE=text          # "text" or "forum"
# DISCORD_THREAD_PREFIX=Session      # Custom thread name prefix

# Optional: User mention for notifications
# DISCORD_MENTION_USER_ID=123456789012345678  # Your Discord user ID

# Optional: Event filtering (choose one approach)
# Only send specific events (comma-separated list)
# DISCORD_ENABLED_EVENTS=Stop,Notification
# Skip specific events (comma-separated list)
# DISCORD_DISABLED_EVENTS=PreToolUse,PostToolUse
# Valid events: PreToolUse, PostToolUse, Notification, Stop, SubagentStop
""")
        print(f"✓ Created example config at {env_example}")

    print("\n✅ Installation complete!")
    print("\nNext steps:")
    print(f"1. Copy {env_example} to {hooks_dir / '.env.discord'}")
    print("2. Edit .env.discord with your Discord credentials")
    print("3. Restart Claude Code")

    return 0


if __name__ == "__main__":
    sys.exit(main())
