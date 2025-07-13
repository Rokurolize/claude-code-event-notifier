#!/usr/bin/env python3
"""Claude Code Discord Notifier - Comprehensive event notification system.

This module provides a complete Discord notification system for Claude Code hook events.
It processes events from stdin, formats them into rich Discord embeds, and sends them
via webhook or bot API with support for threads and user mentions.

Key Features:
    - Zero external dependencies (Python standard library only)
    - Hierarchical TypedDict type system for type safety
    - Comprehensive event formatting with tool-specific details
    - Thread support for session organization
    - User mention system for important notifications
    - Robust error handling and graceful degradation
    - Debug logging with file output

Architecture:
    The module uses a pipeline architecture:
    1. Configuration loading with environment override precedence
    2. Event data validation using TypedDict hierarchies
    3. Tool-specific formatting via registry pattern
    4. HTTP client with retry logic and error handling
    5. Thread management with session caching

Usage:
    This module is designed to be called by Claude Code's hook system:

    $ CLAUDE_HOOK_EVENT=PreToolUse python3 discord_notifier.py < event.json

    Configuration is loaded from:
    1. Environment variables (highest priority)
    2. ~/.claude/hooks/.env.discord file
    3. Built-in defaults

Type System:
    The module uses extensive TypedDict hierarchies for type safety:
    - BaseField: Common properties across all types
    - TimestampedField: Fields with timestamp support
    - SessionAware: Session-aware fields
    - Tool-specific input/output types
    - Event data structures with validation

Error Handling:
    Custom exception hierarchy provides specific error types:
    - ConfigurationError: Configuration issues
    - DiscordAPIError: Discord API failures
    - EventProcessingError: Event processing issues
    - InvalidEventTypeError: Invalid event types

Thread Safety:
    The module maintains thread-safe session caching using a global dictionary.
    Each session gets a unique thread ID that persists for the session duration.

Authors:
    Claude Code Team

Version:
    2.0.0 - Enhanced with comprehensive type system and thread support
"""

# Python version check - must be first before any imports that might fail
import sys

# Add parent directory to Python path when run as a script
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import contextlib
import json
import os
from datetime import UTC, datetime

# TypeGuard and NotRequired are now available in Python 3.12+ typing module
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Protocol,
    cast,
)

# Import constants and enums
from src.constants import (
    ENV_HOOK_EVENT,
    EVENT_COLORS,
    DiscordColors,
    DiscordLimits,
    EventTypes,
)
from src.core.config_loader import ConfigLoader
from src.core.http_client import HTTPClient
from src.core.message_sender import (
    send_to_discord,
)

# Import custom exceptions
from src.exceptions import (
    ConfigurationError,
    EventProcessingError,
)
from src.formatters.base import (
    truncate_string,
)
from src.handlers.event_registry import FormatterRegistry

# Import base types from new module
# Import config types from new module
from src.type_defs.config import (
    Config,
)

# Import datetime utilities
from src.utils.datetime_utils import get_discord_embed_timestamp, get_completed_at_display

# Import Discord types from new module
from src.type_defs.discord import (
    DiscordEmbed,
    DiscordMessage,
)

# Import event types from new module
from src.type_defs.events import (
    EventData,
)

# Import tool types from new module
from src.utils.astolfo_logger import AstolfoLogger, setup_astolfo_logger
from src.utils.discord_utils import should_process_event
from src.utils.session_logger import SessionLogger
from src.utils.validation import (
    is_valid_event_type,
)

if TYPE_CHECKING:
    from src.core.http_client import DiscordMessage as HTTPClientDiscordMessage
    from src.formatters.event_formatters import NotificationEventData as FormatterNotificationEventData
    from src.formatters.event_formatters import StopEventData as FormatterStopEventData
    from src.formatters.event_formatters import SubagentStopEventData as FormatterSubagentStopEventData
    from src.formatters.event_formatters import ToolEventData as FormatterToolEventData
    from src.type_defs.discord import DiscordEmbed as TypeDefDiscordEmbed

# Type aliases for better code clarity
EventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]
ToolName = Literal[
    "Bash",
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
    "LS",
    "Task",
    "WebFetch",
]

# Formatter base class
class EventFormatter(Protocol):
    """Protocol for event formatters."""

    def format(self, event_data: EventData, session_id: str) -> DiscordEmbed:
        """Format event data into Discord embed."""
        ...

def setup_logging(debug: bool) -> AstolfoLogger:
    """Set up logging with optional debug mode."""
    print("[DEBUG] Using AstolfoLogger", file=sys.stderr)
    print(f"[DEBUG] Debug level will be: {os.environ.get('DISCORD_DEBUG_LEVEL', '1')}", file=sys.stderr)
    return setup_astolfo_logger(__name__)

def format_event(
    event_type: str,
    event_data: EventData,
    registry: FormatterRegistry,
    config: Config,
) -> DiscordMessage:
    """Format Claude Code event into Discord embed with length limits."""
    timestamp = get_discord_embed_timestamp()
    session_id_raw = event_data.get("session_id", "unknown")
    session_id = str(session_id_raw)[:8] if session_id_raw else "unknown"

    # Get formatter for event type
    formatter = registry.get_formatter(event_type)
    # Cast to the expected type for the formatter
    from typing import cast as typing_cast
    if event_type in ["PreToolUse", "PostToolUse"]:
        embed = formatter(typing_cast("FormatterToolEventData", event_data), session_id)
    elif event_type == "Notification":
        embed = formatter(typing_cast("FormatterNotificationEventData", event_data), session_id)
    elif event_type == "Stop":
        embed = formatter(typing_cast("FormatterStopEventData", event_data), session_id)
    elif event_type == "SubagentStop":
        embed = formatter(typing_cast("FormatterSubagentStopEventData", event_data), session_id)
    else:
        # For unknown event types, cast to generic dict format
        embed = formatter(cast("dict[str, Any]", event_data), session_id)

    # Enforce Discord's length limits
    if "title" in embed and embed["title"] and len(embed["title"]) > DiscordLimits.MAX_TITLE_LENGTH:
        embed["title"] = truncate_string(embed["title"], DiscordLimits.MAX_TITLE_LENGTH)

    if "description" in embed and embed["description"] and len(embed["description"]) > DiscordLimits.MAX_DESCRIPTION_LENGTH:
        embed["description"] = truncate_string(embed["description"], DiscordLimits.MAX_DESCRIPTION_LENGTH)

    # Add common fields
    embed["timestamp"] = timestamp

    # Get color for event type
    if is_valid_event_type(event_type):
        embed["color"] = EVENT_COLORS.get(event_type, DiscordColors.DEFAULT)
    else:
        embed["color"] = DiscordColors.DEFAULT

    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type}"}

    # Create message with embeds - cast to expected type
    message: DiscordMessage = {"embeds": [cast("TypeDefDiscordEmbed", embed)]}

    # Add user mention for Notification and Stop events if configured
    if event_type in [
        EventTypes.NOTIFICATION.value,
        EventTypes.STOP.value,
    ] and config.get("mention_user_id"):
        # Extract appropriate message based on event type
        if event_type == EventTypes.NOTIFICATION.value:
            display_message = event_data.get("message", "System notification")
        else:  # Stop event
            display_message = "Session ended"
        # Include both mention and message for better Windows notification visibility
        message["content"] = f"<@{config['mention_user_id']}> {display_message}"

    return message

# Global session loggers for persistence
_session_loggers: dict[str, SessionLogger] = {}

def main() -> None:
    """Main entry point - read event from stdin and send to Discord."""
    # Load .env file and set environment variables for session logging
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        try:
            with env_file.open() as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Only set SESSION_LOGGING related vars that aren't already set
                        if (key.startswith("DISCORD_SESSION_LOG") or key == "DISCORD_ENABLE_SESSION_LOGGING") and key not in os.environ:
                            os.environ[key] = value
        except Exception:
            pass  # Ignore errors to not block Claude Code

    # Load configuration
    config = ConfigLoader.load()
    logger = setup_logging(config["debug"])

    # Check if Discord is configured
    try:
        ConfigLoader.validate(config)
    except ConfigurationError:
        logger.debug("No Discord configuration found")
        sys.exit(0)  # Exit gracefully

    # Initialize components
    http_client = HTTPClient(logger)
    formatter_registry = FormatterRegistry()

    try:
        # Read event data from stdin
        raw_input = sys.stdin.read()
        event_data = json.loads(raw_input)

        # Get event type from environment
        event_type = os.environ.get(ENV_HOOK_EVENT, "Unknown")

        # Session logging integration (non-blocking)
        session_logging_enabled = os.getenv("DISCORD_ENABLE_SESSION_LOGGING", "0")
        logger.debug(f"DISCORD_ENABLE_SESSION_LOGGING = {session_logging_enabled}")
        if session_logging_enabled == "1":
            logger.debug("Session logging is enabled")
            try:
                session_id = event_data.get("session_id", "")
                if session_id:
                    logger.debug(f"Processing session: {session_id}")
                    # Create logger if not exists
                    if session_id not in _session_loggers:
                        logger.debug(f"Creating new SessionLogger for {session_id}")
                        _session_loggers[session_id] = SessionLogger(
                            session_id,
                            os.getcwd()
                        )

                    # Log event asynchronously
                    if session_id in _session_loggers:
                        # Enrich event data with Claude Code specifics
                        enriched_data = {
                            **event_data,
                            "parent_uuid": event_data.get("parent_uuid"),
                            "is_sidechain": event_data.get("is_sidechain", False),
                        }

                        # Fire-and-forget pattern
                        import asyncio
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)

                        # Create task and ignore result
                        task = loop.create_task(
                            _session_loggers[session_id].log_event(
                                event_type, enriched_data  # type: ignore[arg-type]
                            )
                        )
                        # Prevent uncaught exception warnings
                        task.add_done_callback(lambda t: None)

            except Exception:
                # Silently ignore all session logging errors
                pass

        # Check if this event should be processed based on filtering configuration
        if not should_process_event(event_type, config):
            logger.debug(
                "event_filtered",
                context={"event_type": event_type},
                ai_todo="Event was filtered out by user configuration"
            )
            sys.exit(0)  # Exit gracefully without processing

        # Set session ID for AstolfoLogger
        session_id = event_data.get("session_id", "")
        if session_id:
            logger.set_session_id(session_id)

            logger.info(
                "processing_event",
                context={
                    "event_type": event_type,
                    "tool_name": event_data.get("tool_name", ""),
                    "has_webhook": bool(config.get("webhook_url")),
                    "has_bot_token": bool(config.get("bot_token")),
                    "use_threads": config.get("use_threads", False)
                },
                ai_todo=f"Processing {event_type} event"
            )
            if logger.debug_level >= 2:
                logger.debug(
                    "event_data_details",
                    context={"event_data": event_data},
                    ai_todo="Full event data for debugging"
                )
        else:
            logger.info("Processing %s event", event_type)
            logger.debug("Event data: %s", json.dumps(event_data, indent=2))

        # Format and send message
        message = format_event(event_type, event_data, formatter_registry, config)
        session_id = event_data.get("session_id", "")
        # Use AstolfoLogger's internal logger for send_to_discord compatibility
        logger_for_send = logger.logger  # AstolfoLogger's internal standard logger
        # Cast to the expected type for send_to_discord
        success = send_to_discord(cast("HTTPClientDiscordMessage", message), config, logger_for_send, http_client, session_id, event_type)

        if success:
            logger.info(
                "notification_sent",
                context={"event_type": event_type, "session_id": session_id},
                ai_todo="Notification sent successfully to Discord"
            )
        else:
            logger.error(
                "notification_failed",
                context={"event_type": event_type, "session_id": session_id},
                ai_todo="Failed to send notification. Check Discord configuration and API errors"
            )

    except json.JSONDecodeError:
        logger.exception("JSON decode error")
    except EventProcessingError:
        logger.exception("Event processing error")
    except (SystemExit, KeyboardInterrupt):
        # Re-raise system-level exceptions
        raise
    except BaseException as e:
        # Catch all other errors to ensure we don't block Claude Code
        logger.exception("Unexpected error: %s", type(e).__name__)
    finally:
        # Clean up session loggers
        if _session_loggers:
            import asyncio
            import time
            # Give async tasks a moment to complete
            time.sleep(0.1)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Close all loggers
            for session_logger in _session_loggers.values():
                with contextlib.suppress(Exception):
                    loop.run_until_complete(session_logger.close())

    # Always exit 0 to not block Claude Code
    sys.exit(0)

if __name__ == "__main__":
    main()
