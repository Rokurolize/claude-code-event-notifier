#!/usr/bin/env python3
"""
Setup Discord Hooks for Claude Code

This script configures Claude Code hooks to send all events to Discord.
It creates or updates the hooks.json configuration file to include
Discord notifications for all supported hook events.

Usage: python3 setup_discord_hooks.py [--webhook-url URL] [--remove]
"""

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path


def get_claude_config_dir():
    """Get the Claude configuration directory."""
    return Path.home() / ".claude"


def get_claude_hooks_dir():
    """Get the Claude hooks directory."""
    return get_claude_config_dir() / "hooks"


def get_script_path():
    """Get the absolute path to the Discord event logger script in the secure hooks directory."""
    return get_claude_hooks_dir() / "discord_event_logger.py"


def get_source_script_path():
    """Get the source Discord event logger script path."""
    script_dir = Path(__file__).parent.absolute()
    return script_dir / "discord_event_logger.py"


def load_existing_settings():
    """Load existing settings configuration."""
    claude_dir = get_claude_config_dir()
    settings_file = claude_dir / "settings.json"

    if settings_file.exists():
        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)
                # Ensure hooks section exists
                if "hooks" not in settings:
                    settings["hooks"] = {}
                return settings
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read existing settings.json: {e}")
            return {"hooks": {}}

    return {"hooks": {}}


def create_discord_hook_command(event_type, webhook_url=None):
    """Create the command string for the Discord hook."""
    script_path = get_script_path()

    # Set environment variable for event type
    env_prefix = f"CLAUDE_HOOK_EVENT={event_type}"

    # Add webhook URL if provided
    if webhook_url:
        env_prefix += f" DISCORD_WEBHOOK_URL='{webhook_url}'"

    return f"{env_prefix} python3 {script_path}"


def copy_script_to_hooks_dir():
    """Copy the Discord event logger script to the secure hooks directory."""
    source_path = get_source_script_path()
    target_path = get_script_path()
    hooks_dir = get_claude_hooks_dir()

    # Create hooks directory if it doesn't exist
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Check directory permissions
    dir_stat = hooks_dir.stat()
    if dir_stat.st_mode & 0o022:  # Check if group or others have write permission
        print(f"Warning: Hooks directory {hooks_dir} has insecure permissions")
        print("Consider running: chmod 755", hooks_dir)

    # Copy the script
    if source_path.exists():
        try:
            shutil.copy2(source_path, target_path)
            # Make the script executable for the owner only
            os.chmod(target_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            print(f"✅ Copied discord_event_logger.py to {target_path}")
            return True
        except Exception as e:
            print(f"Error copying script: {e}")
            return False
    else:
        print(f"Error: Source script not found at {source_path}")
        return False


def setup_discord_credentials():
    """Setup .env.discord file in the secure hooks directory."""
    hooks_dir = get_claude_hooks_dir()
    env_file = hooks_dir / ".env.discord"

    # Check if credentials file already exists
    if env_file.exists():
        print(f"ℹ️  Discord credentials file already exists at {env_file}")
        return True

    # Look for existing credentials to migrate
    existing_creds = {}

    # Check environment variables
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        existing_creds["DISCORD_WEBHOOK_URL"] = os.environ.get("DISCORD_WEBHOOK_URL")
    if os.environ.get("DISCORD_TOKEN"):
        existing_creds["DISCORD_TOKEN"] = os.environ.get("DISCORD_TOKEN")
    if os.environ.get("DISCORD_CHANNEL_ID"):
        existing_creds["DISCORD_CHANNEL_ID"] = os.environ.get("DISCORD_CHANNEL_ID")

    # Check .env.test file
    test_env_file = Path(__file__).parent / ".env.test"
    if test_env_file.exists():
        try:
            with open(test_env_file) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        if key in [
                            "DISCORD_WEBHOOK_URL",
                            "DISCORD_TOKEN",
                            "DISCORD_CHANNEL_ID",
                        ]:
                            existing_creds[key] = value
        except Exception:
            pass

    # Create .env.discord with existing credentials or template
    try:
        content = ["# Discord Configuration for Claude Code Hooks", ""]

        if existing_creds:
            print("📋 Migrating existing Discord credentials...")
            if "DISCORD_WEBHOOK_URL" in existing_creds:
                content.append(
                    f"DISCORD_WEBHOOK_URL={existing_creds['DISCORD_WEBHOOK_URL']}"
                )
            if "DISCORD_TOKEN" in existing_creds:
                content.append(f"DISCORD_TOKEN={existing_creds['DISCORD_TOKEN']}")
            if "DISCORD_CHANNEL_ID" in existing_creds:
                content.append(
                    f"DISCORD_CHANNEL_ID={existing_creds['DISCORD_CHANNEL_ID']}"
                )
        else:
            # Copy from template
            template_path = Path(__file__).parent / ".env.discord.template"
            if template_path.exists():
                with open(template_path) as f:
                    content = f.read().splitlines()
            else:
                content.extend(
                    [
                        "# Option 1: Discord Webhook (Recommended)",
                        "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN",
                        "",
                        "# Option 2: Discord Bot (Alternative)",
                        "# DISCORD_TOKEN=YOUR_BOT_TOKEN",
                        "# DISCORD_CHANNEL_ID=YOUR_CHANNEL_ID",
                    ]
                )

        # Write the file
        with open(env_file, "w") as f:
            f.write("\n".join(content) + "\n")

        # Set secure permissions
        os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)  # 600

        if existing_creds:
            print(f"✅ Created {env_file} with migrated credentials")
        else:
            print(f"✅ Created {env_file} template")
            print(f"⚠️  Please edit {env_file} and add your Discord credentials")

        return True
    except Exception as e:
        print(f"Error creating .env.discord: {e}")
        return False


def add_discord_hooks(settings_config, webhook_url=None):
    """Add Discord notification hooks to all events."""
    script_path = get_script_path()

    # Ensure the script is in the secure hooks directory
    if not script_path.exists():
        print("Discord event logger not found in hooks directory, copying...")
        if not copy_script_to_hooks_dir():
            return False

    # Define hook events and their configurations
    hook_events = {
        "PreToolUse": [
            {
                "matcher": "*",  # All tools
                "hooks": [
                    {
                        "type": "command",
                        "command": create_discord_hook_command(
                            "PreToolUse", webhook_url
                        ),
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "*",  # All tools
                "hooks": [
                    {
                        "type": "command",
                        "command": create_discord_hook_command(
                            "PostToolUse", webhook_url
                        ),
                    }
                ],
            }
        ],
        "Notification": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": create_discord_hook_command(
                            "Notification", webhook_url
                        ),
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": create_discord_hook_command("Stop", webhook_url),
                    }
                ]
            }
        ],
        "SubagentStop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": create_discord_hook_command(
                            "SubagentStop", webhook_url
                        ),
                    }
                ]
            }
        ],
    }

    # Add Discord hooks to existing configuration
    for event_type, event_hooks in hook_events.items():
        if event_type not in settings_config["hooks"]:
            settings_config["hooks"][event_type] = []

        # Remove any existing Discord hooks first
        settings_config["hooks"][event_type] = [
            hook
            for hook in settings_config["hooks"][event_type]
            if not any(
                "discord_event_logger.py" in cmd.get("command", "")
                for cmd in hook.get("hooks", [])
            )
        ]

        # Add new Discord hooks
        settings_config["hooks"][event_type].extend(event_hooks)

    return True


def remove_discord_hooks(settings_config):
    """Remove all Discord notification hooks."""
    if "hooks" not in settings_config:
        return

    for event_type in settings_config["hooks"]:
        settings_config["hooks"][event_type] = [
            hook
            for hook in settings_config["hooks"][event_type]
            if not any(
                "discord_event_logger.py" in cmd.get("command", "")
                for cmd in hook.get("hooks", [])
            )
        ]

    # Remove empty event types
    settings_config["hooks"] = {
        event_type: hooks
        for event_type, hooks in settings_config["hooks"].items()
        if hooks
    }


def save_settings_config(settings_config):
    """Save the settings configuration."""
    claude_dir = get_claude_config_dir()
    settings_file = claude_dir / "settings.json"

    # Create directory if it doesn't exist
    claude_dir.mkdir(exist_ok=True)

    try:
        with open(settings_file, "w") as f:
            json.dump(settings_config, f, indent=2)
        return True
    except IOError as e:
        print(f"Error: Could not write settings.json: {e}")
        return False


def validate_webhook_url(url):
    """Validate Discord webhook URL format."""
    if not url:
        return True  # Empty URL is valid (not required)

    if not url.startswith(
        ("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")
    ):
        return False

    # Basic length check
    if len(url) < 70 or len(url) > 200:
        return False

    return True


def check_discord_config():
    """Check if Discord configuration is available."""
    config_sources = []

    # Check secure .env.discord file first
    secure_env_file = get_claude_hooks_dir() / ".env.discord"
    if secure_env_file.exists():
        config_sources.append(f"Secure credentials at {secure_env_file}")

    # Check environment variables
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        config_sources.append("DISCORD_WEBHOOK_URL environment variable")
    if os.environ.get("DISCORD_TOKEN") and os.environ.get("DISCORD_CHANNEL_ID"):
        config_sources.append(
            "DISCORD_TOKEN and DISCORD_CHANNEL_ID environment variables"
        )

    # Check .env.test file
    env_file = Path(__file__).parent / ".env.test"
    if env_file.exists():
        config_sources.append(f".env.test file at {env_file}")

    return config_sources


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Setup Discord hooks for Claude Code")
    parser.add_argument("--webhook-url", help="Discord webhook URL for notifications")
    parser.add_argument("--remove", action="store_true", help="Remove Discord hooks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    print("Claude Code Discord Hooks Setup")
    print("=" * 35)

    # Validate webhook URL if provided
    if args.webhook_url and not validate_webhook_url(args.webhook_url):
        print("Error: Invalid Discord webhook URL format")
        print("Expected format: https://discord.com/api/webhooks/...")
        sys.exit(1)

    # Check Discord configuration
    config_sources = check_discord_config()
    if not config_sources and not args.webhook_url:
        print("Warning: No Discord configuration found!")
        print("Please set up one of the following:")
        print("- DISCORD_WEBHOOK_URL environment variable")
        print("- DISCORD_TOKEN and DISCORD_CHANNEL_ID environment variables")
        print("- Create a .env.test file with Discord credentials")
        print("- Use --webhook-url argument")
        print()
    else:
        print("Discord configuration found in:")
        for source in config_sources:
            print(f"  - {source}")
        if args.webhook_url:
            print(f"  - Webhook URL provided as argument")
        print()

    # Load existing settings
    settings_config = load_existing_settings()

    if args.remove:
        print("Removing Discord hooks...")
        if not args.dry_run:
            remove_discord_hooks(settings_config)
            if save_settings_config(settings_config):
                print("✅ Discord hooks removed successfully!")
            else:
                print("❌ Failed to save settings configuration")
                sys.exit(1)
        else:
            print("Would remove Discord hooks from settings.json")
    else:
        print("Adding Discord hooks for all events...")
        if not args.dry_run:
            # Setup credentials file first
            setup_discord_credentials()

            if add_discord_hooks(settings_config, args.webhook_url):
                if save_settings_config(settings_config):
                    print("✅ Discord hooks configured successfully!")
                    print()
                    print("Discord notifications will now be sent for:")
                    print("  - PreToolUse: Before tool execution")
                    print("  - PostToolUse: After tool completion")
                    print("  - Notification: System notifications")
                    print("  - Stop: Session end")
                    print("  - SubagentStop: Subagent completion")
                    print()
                    print(f"Hook script location: {get_script_path()}")
                    print(
                        f"Credentials location: {get_claude_hooks_dir() / '.env.discord'}"
                    )
                    print(
                        f"Configuration saved to: {get_claude_config_dir() / 'settings.json'}"
                    )
                else:
                    print("❌ Failed to save settings configuration")
                    sys.exit(1)
            else:
                print("❌ Failed to configure Discord hooks")
                sys.exit(1)
        else:
            print("Would add Discord hooks to settings.json for all events")

    if args.dry_run:
        print()
        print("Dry run completed. Use --dry-run=false to apply changes.")


if __name__ == "__main__":
    main()
