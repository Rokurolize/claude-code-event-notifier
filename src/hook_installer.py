#!/usr/bin/env python3
"""
Hook Installer for Claude Code Event Notifier

This module handles the installation and configuration of Claude Code hooks
to enable event notifications through Discord.
"""

import argparse
import json
import logging
import os
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class ClaudeHookInstaller:
    """Manages the installation of Claude Code hooks for event notifications."""

    def __init__(self, log_file: Optional[Path] = None):
        """Initialize the hook installer."""
        self.claude_config_dir = Path.home() / ".claude"
        self.claude_hooks_dir = self.claude_config_dir / "hooks"
        self.settings_file = self.claude_config_dir / "settings.json"

        # Set up logging
        self.log_file = log_file or self.claude_hooks_dir / "logs" / "installation.log"
        self._setup_logging()

    def _setup_logging(self):
        """Set up comprehensive logging for the installation process."""
        # Create logs directory if it doesn't exist
        log_dir = self.log_file.parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Installation log started at {datetime.now().isoformat()}")
        self.logger.info(f"Log file: {self.log_file}")

    def _log_file_operation(
        self, operation: str, path: Path, details: Optional[Dict[str, Any]] = None
    ):
        """Log file operations with detailed information."""
        log_entry = {
            "operation": operation,
            "path": str(path),
            "timestamp": datetime.now().isoformat(),
            "exists": path.exists(),
        }

        if path.exists():
            try:
                stat_info = path.stat()
                log_entry.update(
                    {
                        "size": stat_info.st_size,
                        "mode": oct(stat_info.st_mode),
                        "is_file": path.is_file(),
                        "is_dir": path.is_dir(),
                    }
                )
            except Exception as e:
                log_entry["stat_error"] = str(e)

        if details:
            log_entry.update(details)

        self.logger.info(f"File operation: {json.dumps(log_entry, indent=2)}")

    def get_notifier_script_path(self) -> Path:
        """Get the target path for the event notifier script in Claude's hooks directory."""
        return self.claude_hooks_dir / "claude_event_notifier.py"

    def get_source_script_path(self) -> Path:
        """Get the source path of the event notifier script."""
        # Assume the script is in the parent directory during development
        module_dir = Path(__file__).parent.parent.absolute()
        return module_dir / "src" / "event_notifier.py"

    def load_claude_settings(self) -> Dict[str, Any]:
        """Load existing Claude Code settings configuration."""
        self._log_file_operation("READ_ATTEMPT", self.settings_file)

        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    content = f.read()
                    settings = json.loads(content)
                    self._log_file_operation(
                        "READ_SUCCESS",
                        self.settings_file,
                        {"content_length": len(content), "keys": list(settings.keys())},
                    )
                    # Ensure hooks section exists
                    if "hooks" not in settings:
                        settings["hooks"] = {}
                        self.logger.info("Added missing 'hooks' section to settings")
                    return settings
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Could not read existing settings.json: {e}")
                self._log_file_operation(
                    "READ_FAILURE", self.settings_file, {"error": str(e)}
                )
                return {"hooks": {}}
        else:
            self.logger.info("settings.json does not exist, creating new configuration")
            return {"hooks": {}}

    def save_claude_settings(self, settings: Dict[str, Any]) -> bool:
        """Save the Claude Code settings configuration."""
        # Create directory if it doesn't exist
        if not self.claude_config_dir.exists():
            self.logger.info(f"Creating directory: {self.claude_config_dir}")
            self._log_file_operation("MKDIR", self.claude_config_dir)
        self.claude_config_dir.mkdir(exist_ok=True)

        try:
            # Create backup if file exists
            if self.settings_file.exists():
                backup_path = self.settings_file.with_suffix(".json.backup")
                shutil.copy2(self.settings_file, backup_path)
                self._log_file_operation("BACKUP_CREATE", backup_path)
                self.logger.info(f"Created backup at {backup_path}")

            # Write new settings
            self._log_file_operation("WRITE_ATTEMPT", self.settings_file)
            with open(self.settings_file, "w") as f:
                content = json.dumps(settings, indent=2)
                f.write(content)
                self._log_file_operation(
                    "WRITE_SUCCESS",
                    self.settings_file,
                    {
                        "content_length": len(content),
                        "hooks_count": len(settings.get("hooks", {})),
                    },
                )
            self.logger.info("Successfully saved settings.json")
            return True
        except IOError as e:
            self.logger.error(f"Could not write settings.json: {e}")
            self._log_file_operation(
                "WRITE_FAILURE", self.settings_file, {"error": str(e)}
            )
            return False

    def copy_notifier_script(self) -> bool:
        """Copy the event notifier script to Claude's hooks directory."""
        source_script = self.get_source_script_path()
        target_script = self.get_notifier_script_path()

        self._log_file_operation("COPY_CHECK_SOURCE", source_script)
        if not source_script.exists():
            self.logger.error(f"Source script not found at {source_script}")
            return False

        # Create hooks directory if it doesn't exist
        if not self.claude_hooks_dir.exists():
            self.logger.info(f"Creating hooks directory: {self.claude_hooks_dir}")
            self._log_file_operation("MKDIR", self.claude_hooks_dir)
        self.claude_hooks_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy the main script
            self._log_file_operation(
                "COPY_ATTEMPT", source_script, {"target": str(target_script)}
            )
            shutil.copy2(source_script, target_script)
            self._log_file_operation("COPY_SUCCESS", target_script)

            # Make it executable
            st = os.stat(target_script)
            new_mode = st.st_mode | stat.S_IEXEC
            os.chmod(target_script, new_mode)
            self._log_file_operation(
                "CHMOD",
                target_script,
                {"old_mode": oct(st.st_mode), "new_mode": oct(new_mode)},
            )

            # Also copy the module files
            copied_modules = []
            for module_file in [
                "message_formatter.py",
                "discord_sender.py",
                "__init__.py",
            ]:
                source_module = source_script.parent / module_file
                target_module = target_script.parent / module_file

                self._log_file_operation("MODULE_CHECK", source_module)
                if source_module.exists():
                    self._log_file_operation(
                        "MODULE_COPY_ATTEMPT",
                        source_module,
                        {"target": str(target_module)},
                    )
                    shutil.copy2(source_module, target_module)
                    self._log_file_operation("MODULE_COPY_SUCCESS", target_module)
                    copied_modules.append(module_file)
                else:
                    self.logger.warning(f"Module file not found: {module_file}")

            self.logger.info(f"✅ Copied event notifier to {target_script}")
            self.logger.info(f"✅ Copied modules: {', '.join(copied_modules)}")
            return True

        except Exception as e:
            self.logger.error(f"Error copying script: {e}")
            self._log_file_operation("COPY_FAILURE", target_script, {"error": str(e)})
            return False

    def create_hook_command(
        self, event_type: str, webhook_url: Optional[str] = None
    ) -> str:
        """Create the command string for the Claude Code hook."""
        script_path = self.get_notifier_script_path()

        # Set environment variable for event type
        env_prefix = f"CLAUDE_HOOK_EVENT={event_type}"

        # Add webhook URL if provided
        if webhook_url:
            env_prefix += f" DISCORD_WEBHOOK_URL='{webhook_url}'"

        return f"{env_prefix} python3 {script_path}"

    def add_notification_hooks(
        self, settings: Dict[str, Any], webhook_url: Optional[str] = None
    ) -> bool:
        """Add Discord notification hooks to all supported events."""
        self.logger.info("Adding notification hooks to settings")
        self.logger.info(f"Webhook URL provided: {'Yes' if webhook_url else 'No'}")

        # Define hook events and their configurations
        hook_events = {
            "PreToolUse": {
                "matcher": "",  # Empty string matches all tools
                "hooks": [
                    {
                        "type": "command",
                        "command": self.create_hook_command("PreToolUse", webhook_url),
                    }
                ],
            },
            "PostToolUse": {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": self.create_hook_command("PostToolUse", webhook_url),
                    }
                ],
            },
            "Notification": {
                "hooks": [
                    {
                        "type": "command",
                        "command": self.create_hook_command(
                            "Notification", webhook_url
                        ),
                    }
                ]
            },
            "Stop": {
                "hooks": [
                    {
                        "type": "command",
                        "command": self.create_hook_command("Stop", webhook_url),
                    }
                ]
            },
            "SubagentStop": {
                "hooks": [
                    {
                        "type": "command",
                        "command": self.create_hook_command(
                            "SubagentStop", webhook_url
                        ),
                    }
                ]
            },
        }

        # Add hooks to settings
        hooks_added = []
        for event_type, event_config in hook_events.items():
            if event_type not in settings["hooks"]:
                settings["hooks"][event_type] = []
                self.logger.info(f"Created new hook category: {event_type}")

            # Count existing hooks before removal
            existing_count = len(settings["hooks"][event_type])

            # Remove any existing Claude event notifier hooks first
            settings["hooks"][event_type] = [
                hook
                for hook in settings["hooks"][event_type]
                if not any(
                    "claude_event_notifier" in cmd.get("command", "")
                    for cmd in hook.get("hooks", [])
                )
            ]

            removed_count = existing_count - len(settings["hooks"][event_type])
            if removed_count > 0:
                self.logger.info(
                    f"Removed {removed_count} existing notifier hook(s) from {event_type}"
                )

            # Add new hook configuration
            settings["hooks"][event_type].append(event_config)
            hooks_added.append(event_type)
            self.logger.info(f"Added hook for event: {event_type}")
            self.logger.debug(f"Hook command: {event_config['hooks'][0]['command']}")

        self.logger.info(f"Successfully added hooks for: {', '.join(hooks_added)}")
        return True

    def remove_notification_hooks(self, settings: Dict[str, Any]) -> None:
        """Remove all Claude event notification hooks."""
        for event_type in settings["hooks"]:
            settings["hooks"][event_type] = [
                hook
                for hook in settings["hooks"][event_type]
                if not any(
                    "claude_event_notifier" in cmd.get("command", "")
                    for cmd in hook.get("hooks", [])
                )
            ]

        # Remove empty event types
        settings["hooks"] = {
            event_type: hooks
            for event_type, hooks in settings["hooks"].items()
            if hooks
        }

    def check_discord_config(self) -> List[str]:
        """Check if Discord configuration is available."""
        config_sources = []
        self.logger.info("Checking Discord configuration...")

        # Check environment variables
        if os.environ.get("DISCORD_WEBHOOK_URL"):
            config_sources.append("DISCORD_WEBHOOK_URL environment variable")
            self.logger.info("Found DISCORD_WEBHOOK_URL in environment")
        if os.environ.get("DISCORD_TOKEN") and os.environ.get("DISCORD_CHANNEL_ID"):
            config_sources.append(
                "DISCORD_TOKEN and DISCORD_CHANNEL_ID environment variables"
            )
            self.logger.info(
                "Found DISCORD_TOKEN and DISCORD_CHANNEL_ID in environment"
            )

        # Check .env.discord file
        env_file = self.claude_hooks_dir / ".env.discord"
        self._log_file_operation("ENV_CHECK", env_file)
        if env_file.exists():
            config_sources.append(f".env.discord file at {env_file}")
            self.logger.info(f"Found .env.discord file at {env_file}")
            try:
                with open(env_file, "r") as f:
                    lines = f.readlines()
                    self.logger.debug(f".env.discord has {len(lines)} lines")
            except Exception as e:
                self.logger.warning(f"Could not read .env.discord: {e}")

        self.logger.info(f"Found {len(config_sources)} Discord configuration source(s)")
        return config_sources

    def install(self, webhook_url: Optional[str] = None, dry_run: bool = False) -> bool:
        """Install Claude Code hooks for Discord notifications."""
        self.logger.info("=" * 60)
        self.logger.info("Starting installation process")
        self.logger.info(f"Dry run: {dry_run}")
        self.logger.info(f"Webhook URL provided: {'Yes' if webhook_url else 'No'}")
        self.logger.info("=" * 60)

        if not dry_run:
            # Copy the notifier script
            self.logger.info("Step 1: Copying notifier scripts...")
            if not self.copy_notifier_script():
                self.logger.error("Failed to copy notifier script")
                return False

            # Load existing settings
            self.logger.info("Step 2: Loading existing settings...")
            settings = self.load_claude_settings()

            # Add notification hooks
            self.logger.info("Step 3: Adding notification hooks...")
            if self.add_notification_hooks(settings, webhook_url):
                self.logger.info("Step 4: Saving updated settings...")
                if self.save_claude_settings(settings):
                    self.logger.info("✅ Hooks installed successfully!")
                    self._log_installation_summary()
                    return True
                else:
                    self.logger.error("❌ Failed to save settings")
                    return False
            else:
                self.logger.error("❌ Failed to configure hooks")
                return False
        else:
            self.logger.info("Would install Claude Code Event Notifier hooks (dry run)")
            self.logger.info("Run without --dry-run to perform actual installation")
            return True

    def _log_installation_summary(self):
        """Log a summary of the installation."""
        self.logger.info("=" * 60)
        self.logger.info("Installation Summary:")
        self.logger.info(f"  - Hooks directory: {self.claude_hooks_dir}")
        self.logger.info(f"  - Settings file: {self.settings_file}")
        self.logger.info(f"  - Event notifier: {self.get_notifier_script_path()}")

        # List installed files
        if self.claude_hooks_dir.exists():
            files = list(self.claude_hooks_dir.glob("*.py"))
            self.logger.info(f"  - Installed Python files: {len(files)}")
            for f in files:
                self.logger.info(f"    - {f.name}")

        self.logger.info("=" * 60)

    def uninstall(self, dry_run: bool = False) -> bool:
        """Remove Claude Code hooks for Discord notifications."""
        print("Removing Claude Code Event Notifier hooks...")

        if not dry_run:
            # Load existing settings
            settings = self.load_claude_settings()

            # Remove notification hooks
            self.remove_notification_hooks(settings)

            if self.save_claude_settings(settings):
                print("✅ Hooks removed successfully!")

                # Optionally remove the script file
                script_path = self.get_notifier_script_path()
                if script_path.exists():
                    try:
                        script_path.unlink()
                        print(f"✅ Removed {script_path}")
                    except Exception as e:
                        print(f"Warning: Could not remove script: {e}")

                return True
            else:
                print("❌ Failed to save settings")
                return False
        else:
            print("Would remove Claude Code Event Notifier hooks (dry run)")
            return True


def main():
    """Main entry point for the hook installer."""
    parser = argparse.ArgumentParser(
        description="Install Claude Code hooks for Discord notifications"
    )
    parser.add_argument("--webhook-url", help="Discord webhook URL for notifications")
    parser.add_argument("--remove", action="store_true", help="Remove Discord hooks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    print("Claude Code Event Notifier - Hook Installer")
    print("=" * 45)

    # Set up log file path
    log_file = (
        Path.home()
        / ".claude"
        / "hooks"
        / "logs"
        / f"installation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    installer = ClaudeHookInstaller(log_file=log_file)

    # Check Discord configuration
    config_sources = installer.check_discord_config()
    if not config_sources and not args.webhook_url:
        print("⚠️  Warning: No Discord configuration found!")
        print("Please set up one of the following:")
        print("- DISCORD_WEBHOOK_URL environment variable")
        print("- DISCORD_TOKEN and DISCORD_CHANNEL_ID environment variables")
        print("- Create a .env.discord file with Discord credentials")
        print("- Use --webhook-url argument")
        print()
    else:
        print("Discord configuration found in:")
        for source in config_sources:
            print(f"  - {source}")
        if args.webhook_url:
            print(f"  - Webhook URL provided as argument")
        print()

    # Perform installation or removal
    if args.remove:
        success = installer.uninstall(dry_run=args.dry_run)
    else:
        success = installer.install(webhook_url=args.webhook_url, dry_run=args.dry_run)

    if args.dry_run:
        print("\nDry run completed. Use without --dry-run to apply changes.")

    # Log final status
    installer.logger.info("=" * 60)
    installer.logger.info(
        f"Installation completed with status: {'SUCCESS' if success else 'FAILURE'}"
    )
    installer.logger.info(f"Log file saved to: {installer.log_file}")
    installer.logger.info("=" * 60)

    print(f"\n📄 Installation log saved to: {installer.log_file}")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
