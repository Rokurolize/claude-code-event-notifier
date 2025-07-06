#!/usr/bin/env python3
"""
Claude Code Event Notifier

Main module that receives Claude Code hook events and sends notifications to Discord.
This replaces the misleadingly named 'discord_event_logger.py'.
"""

import argparse
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    # Try relative imports first (for package usage)
    from .message_formatter import EventMessageFormatter
    from .discord_sender import DiscordNotificationSender
except ImportError:
    # Fall back to absolute imports (for direct execution)
    from message_formatter import EventMessageFormatter
    from discord_sender import DiscordNotificationSender


class ClaudeEventNotifier:
    """Main class for handling Claude Code event notifications."""

    def __init__(self, config: Dict[str, Any], debug: bool = False):
        """
        Initialize the Claude Code event notifier.

        Args:
            config: Configuration dictionary with Discord credentials
            debug: Enable debug logging
        """
        self.config = config
        self.debug = debug
        self.logger = self._setup_logging(debug)

        # Initialize components
        self.formatter = EventMessageFormatter()
        self.sender = DiscordNotificationSender(
            webhook_url=config.get("webhook_url"),
            bot_token=config.get("bot_token"),
            channel_id=config.get("channel_id"),
        )

    def _setup_logging(self, debug: bool) -> logging.Logger:
        """Configure logging with optional debug mode."""
        log_dir = Path("/home/ubuntu/.claude/hooks/logs")
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log filename with date
        log_file = (
            log_dir / f"claude_event_notifier_{datetime.now().strftime('%Y-%m-%d')}.log"
        )

        # Configure logging format
        log_format = "%(asctime)s - %(levelname)s - %(name)s.%(funcName)s:%(lineno)d - %(message)s"

        # Set up both file and console logging
        handlers = []

        # File handler - always logs at DEBUG level
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)

        # Console handler - only for errors unless debug mode
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG if debug else logging.ERROR)
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)

        # Configure root logger
        logging.basicConfig(level=logging.DEBUG, handlers=handlers)

        return logging.getLogger(__name__)

    def process_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Process a Claude Code hook event and send notification.

        Args:
            event_type: Type of the event (PreToolUse, PostToolUse, etc.)
            event_data: Event data from Claude Code

        Returns:
            True if notification was sent successfully
        """
        self.logger.info(f"Processing {event_type} event")
        self.logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")

        try:
            # Format the event into a Discord message
            message_data = self.formatter.format_event_notification(
                event_type, event_data
            )

            # Send the notification
            success = self.sender.send_notification(message_data)

            if success:
                self.logger.info(f"{event_type} notification sent successfully")
            else:
                self.logger.error(f"Failed to send {event_type} notification")

            return success

        except Exception as e:
            self.logger.error(f"Error processing event: {type(e).__name__}: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    def run(self):
        """Main entry point - read event from stdin and process."""
        self.logger.info("=" * 60)
        self.logger.info("Claude Code Event Notifier Started")
        self.logger.info(f"Debug mode: {self.debug}")
        self.logger.info(f"Working directory: {os.getcwd()}")

        try:
            # Read JSON input from stdin
            self.logger.debug("Reading JSON from stdin...")
            raw_input = sys.stdin.read()
            self.logger.debug(f"Raw input length: {len(raw_input)} chars")
            self.logger.debug(f"Raw input preview: {raw_input[:200]}...")

            try:
                event_data = json.loads(raw_input)
                self.logger.info(
                    f"Successfully parsed JSON with keys: {list(event_data.keys())}"
                )
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON input: {e}")
                self.logger.debug(f"Failed to parse: {raw_input[:500]}")
                sys.exit(1)

            # Determine event type from environment
            event_type = os.environ.get("CLAUDE_HOOK_EVENT", "Unknown")
            self.logger.info(f"Event type: {event_type}")

            # Process the event
            success = self.process_event(event_type, event_data)

            # Always exit 0 to not block Claude Code
            sys.exit(0)

        except Exception as e:
            # Log error but don't block Claude Code
            self.logger.error(f"Notifier error: {type(e).__name__}: {e}")
            self.logger.debug(traceback.format_exc())
            sys.exit(0)


def load_notification_config() -> Dict[str, Any]:
    """Load notification configuration from environment or files."""
    logger = logging.getLogger(__name__)
    logger.debug("Loading notification configuration")

    config = {}

    # Try environment variables first
    config["webhook_url"] = os.environ.get("DISCORD_WEBHOOK_URL")
    config["bot_token"] = os.environ.get("DISCORD_TOKEN")
    config["channel_id"] = os.environ.get("DISCORD_CHANNEL_ID")

    logger.debug(
        f"Environment variables loaded: webhook_url={bool(config['webhook_url'])}, "
        f"bot_token={bool(config['bot_token'])}, channel_id={config['channel_id']}"
    )

    # Primary configuration file in secure hooks directory
    secure_env_file = Path("/home/ubuntu/.claude/hooks/.env.discord")

    # Try loading from secure .env.discord file
    if not all(config.values()) and secure_env_file.exists():
        logger.debug(f"Loading config from {secure_env_file}")
        try:
            with open(secure_env_file) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        # Remove quotes if present
                        value = value.strip('"').strip("'")

                        if key == "DISCORD_WEBHOOK_URL" and not config["webhook_url"]:
                            config["webhook_url"] = value
                            logger.debug("Loaded webhook URL from .env.discord")
                        elif key == "DISCORD_TOKEN" and not config["bot_token"]:
                            config["bot_token"] = value
                            logger.debug("Loaded bot token from .env.discord")
                        elif key == "DISCORD_CHANNEL_ID" and not config["channel_id"]:
                            config["channel_id"] = value
                            logger.debug(
                                f"Loaded channel ID from .env.discord: {value}"
                            )
        except Exception as e:
            logger.error(f"Error reading {secure_env_file}: {e}")

    # Fallback to other locations if still not configured
    if not all(config.values()):
        possible_env_files = [
            Path.home() / "human-in-the-loop" / ".env.test",  # Project directory
            Path.cwd() / ".env.test",  # Current working directory
        ]

        for env_file in possible_env_files:
            if env_file.exists():
                logger.debug(f"Trying fallback config from {env_file}")
                try:
                    with open(env_file) as f:
                        for line in f:
                            if "=" in line and not line.startswith("#"):
                                key, value = line.strip().split("=", 1)
                                value = value.strip('"').strip("'")

                                if key == "DISCORD_TOKEN" and not config["bot_token"]:
                                    config["bot_token"] = value
                                    logger.debug(f"Loaded bot token from {env_file}")
                                elif (
                                    key == "DISCORD_CHANNEL_ID"
                                    and not config["channel_id"]
                                ):
                                    config["channel_id"] = value
                                    logger.debug(
                                        f"Loaded channel ID from {env_file}: {value}"
                                    )
                                elif (
                                    key == "DISCORD_WEBHOOK_URL"
                                    and not config["webhook_url"]
                                ):
                                    config["webhook_url"] = value
                                    logger.debug(f"Loaded webhook URL from {env_file}")

                    if all(config.values()):
                        logger.info(f"All config loaded from {env_file}")
                        break
                except Exception as e:
                    logger.error(f"Error reading {env_file}: {e}")

    # Log final configuration status
    logger.info(
        f"Final config status: webhook_url={bool(config['webhook_url'])}, "
        f"bot_token={bool(config['bot_token'])}, channel_id={config['channel_id']}"
    )

    return config


def main():
    """Main entry point for the Claude Code event notifier."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Claude Code Event Notifier - Send Claude Code events to Discord"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging to console"
    )
    args = parser.parse_args()

    # Check for debug environment variable too
    debug_mode = args.debug or os.environ.get("DISCORD_DEBUG") == "1"

    # Load configuration
    config = load_notification_config()

    if not config["webhook_url"] and not (config["bot_token"] and config["channel_id"]):
        print("No Discord configuration found - exiting gracefully", file=sys.stderr)
        sys.exit(0)  # Exit gracefully, don't block Claude

    # Create and run notifier
    notifier = ClaudeEventNotifier(config, debug=debug_mode)
    notifier.run()


if __name__ == "__main__":
    main()
