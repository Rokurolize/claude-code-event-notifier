#!/usr/bin/env python3
"""Simple, beautiful main entry point for Discord Event Notifier.

This is the thin dispatcher that ties everything together.
"""

import sys

# Check Python version before any other imports
if sys.version_info < (3, 13):
    print(
        f"""
ERROR: This project requires Python 3.13 or higher.
Current Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}

Please run with Python 3.13+:
  uv run --python 3.13 python src/simple/main.py
""",
        file=sys.stderr,
    )
    sys.exit(1)

import json
import logging
import os
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from debug_logger import save_debug_data
from discord_client import send_routed_message

from handlers import get_handler, should_process_event, should_process_tool

try:
    from __version__ import __git_commit__, __version__
except ImportError:
    __version__ = "unknown"
    __git_commit__ = None

# Python 3.13+ required


def get_git_commit_hash():
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False, capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]
    except Exception:
        pass
    return "(not available)"


def log_environment_info(logger):
    """Log complete environment information at startup."""
    logger.info("=" * 60)
    logger.info("Discord Event Notifier - Environment Information")
    logger.info("=" * 60)
    logger.info(f"Version: {__version__}")
    logger.info(f"Git Commit: {get_git_commit_hash()}")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Python Executable: {sys.executable}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info(f"Script Path: {Path(__file__).resolve()}")
    logger.info("=" * 60)


# Setup simple architecture logging
def setup_logging():
    """Setup logging for simple architecture."""
    log_dir = Path.home() / ".claude" / "hooks" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"simple_notifier_{datetime.now(UTC).strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - SIMPLE - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr),  # Also log to stderr for immediate debugging
        ],
    )

    logger = logging.getLogger(__name__)

    # Log environment info on startup
    log_environment_info(logger)

    return logger


def main() -> None:
    """Main entry point - read event, process, send to Discord."""
    logger = setup_logging()

    try:
        logger.debug("Simple Discord Notifier starting")

        # Load configuration
        config = load_config()
        if not config:
            logger.debug("No valid Discord config - exiting gracefully")
            sys.exit(0)

        logger.debug("Config loaded successfully: %s", list(config.keys()))

        # Additional debug logging based on config
        if config.get("debug"):
            logger.debug("Debug mode enabled in config")

        # Read event data from stdin
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            logger.debug("No input data - exiting")
            sys.exit(0)

        logger.debug("Received input: %s...", raw_input[:200])

        # Parse JSON
        try:
            event_data = json.loads(raw_input)
            logger.debug("Parsed JSON event: %s", event_data.get("hook_event_name", "Unknown"))
        except json.JSONDecodeError as e:
            logger.debug("Invalid JSON - exiting gracefully: %s", e)
            sys.exit(0)

        # Get event type
        event_type = event_data.get("hook_event_name", "Unknown")
        # Sanitize for logging (remove newlines and control characters)
        safe_event_type = event_type.replace("\n", "\\n").replace("\r", "\\r")
        logger.debug("Processing event type: %s", safe_event_type)

        # Save raw input for debugging if debug mode is enabled
        if config.get("debug"):
            logger.debug("Debug mode: Saving raw input data")
            # Extract tool name for PreToolUse/PostToolUse events
            tool_name_for_debug = None
            if event_type in ["PreToolUse", "PostToolUse"]:
                tool_name_for_debug = event_data.get("tool_name", "")
            save_debug_data(raw_input, None, safe_event_type, tool_name_for_debug)

        # Check if event should be processed
        if not should_process_event(event_type, config):
            logger.debug("Event %s filtered out by configuration", safe_event_type)
            sys.exit(0)

        logger.debug("Event %s passed filter checks", safe_event_type)

        # For tool events, check if tool should be processed
        if event_type in ["PreToolUse", "PostToolUse"]:
            tool_name = event_data.get("tool_name", "")
            # Sanitize tool name for logging
            safe_tool_name = tool_name.replace("\n", "\\n").replace("\r", "\\r")
            logger.debug("Checking tool filter for: %s", safe_tool_name)
            if not should_process_tool(tool_name, config):
                logger.debug("Tool %s filtered out by configuration", safe_tool_name)
                sys.exit(0)
            logger.debug("Tool %s passed filter checks", safe_tool_name)

        # Get handler
        handler = get_handler(event_type)
        if not handler:
            logger.debug("No handler found for event type: %s", safe_event_type)
            sys.exit(0)

        logger.debug("Handler found for %s", safe_event_type)

        # Process event
        message = handler(event_data, config)
        if not message:
            logger.debug("Handler returned None - skipping Discord")
            sys.exit(0)

        logger.debug("Message generated, sending to Discord")

        # Save formatted output for debugging if debug mode is enabled
        if config.get("debug"):
            logger.debug("Debug mode: Saving formatted output data")
            # Extract tool name for PreToolUse/PostToolUse events
            tool_name_for_debug = None
            if event_type in ["PreToolUse", "PostToolUse"]:
                tool_name_for_debug = event_data.get("tool_name", "")
            save_debug_data(raw_input, message, safe_event_type, tool_name_for_debug)

        # Send to Discord with routing
        tool_name = event_data.get("tool_name") if event_type in ["PreToolUse", "PostToolUse"] else None
        success = send_routed_message(message, config, event_type, tool_name)
        if success:
            logger.debug("Message sent successfully to Discord")
        else:
            logger.debug("Failed to send message to Discord")

    except Exception:
        # Never let exceptions block Claude Code
        logger.exception("Unexpected error occurred")

    sys.exit(0)


if __name__ == "__main__":
    main()
