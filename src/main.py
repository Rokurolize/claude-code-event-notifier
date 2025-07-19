#!/usr/bin/env python3
"""Main entry point for new architecture Discord Notifier.

This module serves as the entry point for the modularized Discord notification
system, integrating all components from the new architecture.

Usage:
    CLAUDE_HOOK_EVENT=PreToolUse uv run python main.py < event.json

Architecture Integration:
    - Configuration: src.core.config
    - HTTP Client: src.core.http_client
    - Event Processing: src.handlers.event_registry
    - Discord Messaging: src.handlers.discord_sender
"""

import sys

# Check Python version before any other imports
if sys.version_info < (3, 13):
    print(f"""
ERROR: This project requires Python 3.13 or higher.
Current Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}

Please run with Python 3.13+:
  Option 1: Use uv (recommended)
    CLAUDE_HOOK_EVENT=PreToolUse uv run python src/main.py
    
  Option 2: Install Python 3.13
    Visit https://www.python.org/downloads/
    
  Option 3: Use uv to install Python 3.13
    uv python install 3.13
""", file=sys.stderr)
    sys.exit(1)

import json
import os
from datetime import UTC, datetime
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import new architecture components
from src.core.config import (
    Config,
    ConfigLoader,
    ConfigValidator,
    ConfigFileWatcher,
    setup_logging,
    should_process_event,
    should_process_tool,
)
from src.core.constants import ENV_HOOK_EVENT, EventTypes, EVENT_COLORS, DiscordColors
from src.core.exceptions import ConfigurationError, DiscordAPIError, EventProcessingError
from src.core.http_client import DiscordMessage, HTTPClient
from src.formatters.event_formatters import format_version_footer
from src.handlers.discord_sender import DiscordContext, send_to_discord
from src.handlers.event_registry import EventData, FormatterRegistry
from src.type_guards import is_event_type
from src.formatters.base import truncate_string


def format_event_message(
    event_type: str,
    event_data: EventData,
    registry: FormatterRegistry,
    config: Config,
) -> DiscordMessage:
    """Format Claude Code event into Discord message using new architecture.

    Args:
        event_type: Type of event being processed
        event_data: Event data from Claude Code
        registry: Formatter registry for event-specific formatting
        config: Configuration dictionary

    Returns:
        Formatted Discord message with embeds

    Raises:
        EventProcessingError: If event formatting fails
    """
    try:
        timestamp = datetime.now(UTC).isoformat()

        # Enhanced Session ID extraction with multiple fallback options
        session_id = str(
            event_data.get("session_id") or event_data.get("Session") or event_data.get("session") or "unknown"
        )

        # Get formatter for event type
        formatter = registry.get_formatter(event_type)
        embed = formatter(event_data, session_id)

        # Enforce Discord's length limits
        if "title" in embed and len(embed["title"]) > 256:
            embed["title"] = truncate_string(embed["title"], 256)

        if "description" in embed and len(embed["description"]) > 4096:
            embed["description"] = truncate_string(embed["description"], 4096)

        # Add common fields
        embed["timestamp"] = timestamp

        # Get color for event type
        if is_event_type(event_type):
            embed["color"] = EVENT_COLORS.get(event_type, DiscordColors.DEFAULT)  # type: ignore[arg-type]
        else:
            embed["color"] = DiscordColors.DEFAULT

        # Enhanced footer with version information
        version_footer = format_version_footer()
        embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type} | {version_footer}"}

        # Create message with embeds
        message: DiscordMessage = {"embeds": [embed]}

        # Add user mention for Notification and Stop events if configured
        if event_type in [
            EventTypes.NOTIFICATION.value,
            EventTypes.STOP.value,
        ] and config.get("mention_user_id"):
            # Extract appropriate message based on event type
            if event_type == EventTypes.NOTIFICATION.value:
                # For notifications, extract the actual message content
                # The description format is: "**Message:** {message}\n**Session:** ..."
                description = embed.get("description", "System notification")
                # Extract the message content after "**Message:** "
                if "**Message:** " in description:
                    message_start = description.find("**Message:** ") + len("**Message:** ")
                    message_end = description.find("\n", message_start)
                    if message_end == -1:
                        display_message = description[message_start:]
                    else:
                        display_message = description[message_start:message_end]
                else:
                    # Fallback: use first line of description
                    first_line = description.split("\n")[0]
                    display_message = first_line[:100]
            else:  # Stop event
                display_message = "Session ended"

            message["content"] = f"<@{config['mention_user_id']}> {display_message}"

        return message

    except Exception as e:
        raise EventProcessingError(f"Failed to format {event_type} event: {e}") from e


def split_long_message(message: DiscordMessage, max_length: int = 3800) -> list[DiscordMessage]:
    """Split a long Discord message into multiple messages to avoid Discord limits.
    
    Args:
        message: Original Discord message that may be too long
        max_length: Maximum length for message description (default: 3800)
        
    Returns:
        List of Discord messages, split if necessary
    """
    # If message has no embeds or embed description is short enough, return as-is
    if not message.get("embeds") or len(message["embeds"]) == 0:
        return [message]
    
    embed = message["embeds"][0]
    description = embed.get("description", "")
    
    # If description is within limits, return as-is
    if len(description) <= max_length:
        return [message]
    
    # Split the description into chunks
    chunks = []
    remaining = description
    
    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break
        
        # Find a good split point (prefer splitting at newlines)
        split_point = max_length
        last_newline = remaining.rfind('\n', 0, max_length)
        if last_newline > max_length * 0.7:  # Only use newline if it's not too early
            split_point = last_newline
        
        chunk = remaining[:split_point]
        chunks.append(chunk)
        remaining = remaining[split_point:].lstrip('\n')
    
    # Create multiple messages from chunks
    messages = []
    for i, chunk in enumerate(chunks):
        # Create a copy of the original message
        split_message = message.copy()
        split_embed = embed.copy()
        
        # Add continuation indicators
        if len(chunks) > 1:
            if i == 0:
                split_embed["title"] = f"{embed.get('title', '')} [1/{len(chunks)}]"
                chunk += f"\n\n*[Continued in next message...]*"
            elif i == len(chunks) - 1:
                split_embed["title"] = f"{embed.get('title', '')} [#{i+1}/{len(chunks)} - Final]"
                chunk = f"*[...continued from previous message]*\n\n{chunk}"
            else:
                split_embed["title"] = f"{embed.get('title', '')} [#{i+1}/{len(chunks)}]"
                chunk = f"*[...continued from previous message]*\n\n{chunk}\n\n*[Continued in next message...]*"
        
        split_embed["description"] = chunk
        split_message["embeds"] = [split_embed]
        messages.append(split_message)
    
    return messages


def save_raw_json_log(raw_json: str, event_type: str = "Unknown", session_id: str = "unknown") -> None:
    """Save raw JSON input to log file for debugging and analysis.
    
    Args:
        raw_json: Raw JSON string received from Claude Code Hook
        event_type: Type of event (PreToolUse, PostToolUse, etc.)
        session_id: Session identifier for grouping related events
    """
    try:
        # Create logs directory structure
        logs_dir = Path.home() / ".claude" / "hooks" / "logs" / "raw_json"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp for unique filename
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]  # Include milliseconds
        
        # Create filename with timestamp, event type, and session ID
        filename = f"{timestamp}_{event_type}_{session_id}.json"
        filepath = logs_dir / filename
        
        # Write raw JSON to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(raw_json)
            
        # Also save a pretty-formatted version for easier reading
        pretty_filename = f"{timestamp}_{event_type}_{session_id}_pretty.json"
        pretty_filepath = logs_dir / pretty_filename
        
        try:
            parsed_json = json.loads(raw_json)
            with open(pretty_filepath, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # If JSON parsing fails, just save the raw version
            pass
            
    except Exception:
        # Don't let JSON logging failures break the main flow
        # This is purely for debugging and analysis purposes
        pass


def send_config_notification(message: str, is_error: bool = False) -> None:
    """Send configuration change notification to Discord.

    Args:
        message: Notification message to send
        is_error: Whether this is an error notification
    """
    try:
        # Create a simple notification message
        notification_data = {"session_id": "config-watcher", "message": message}

        # Load basic config for sending notification
        basic_config = ConfigLoader.load()
        if not ConfigValidator.validate_credentials(basic_config):
            return  # No valid Discord config, skip notification

        # Initialize HTTP client for notification
        http_client = HTTPClient(None)  # No logger for notifications

        # Create Discord context for notification
        discord_context = DiscordContext(config=basic_config, logger=None, http_client=http_client)

        # Create embed for config change notification
        embed = {
            "title": "⚙️ Configuration Update" if not is_error else "⚠️ Configuration Error",
            "description": message,
            "color": DiscordColors.BLUE if not is_error else DiscordColors.RED,
            "timestamp": datetime.now(UTC).isoformat(),
            "footer": {"text": "Discord Notifier • Hot Reload System"},
        }

        notification_message = {"embeds": [embed]}

        # Send notification
        send_to_discord(
            message=notification_message, ctx=discord_context, session_id="config-watcher", event_type="ConfigUpdate"
        )

    except Exception:
        # Don't let notification failures break the main flow
        pass


def main() -> None:
    """Main entry point for new architecture - read event from stdin and send to Discord."""
    logger = None

    try:
        # Load configuration using new architecture with hot reload support
        config_watcher = ConfigFileWatcher()

        # Set up notification callback for config changes
        config_watcher.set_notification_callback(send_config_notification)

        # Get config with auto-reload and notifications
        config = config_watcher.get_config_with_auto_reload_and_notify()
        logger = setup_logging(config["debug"])

        # Check if Discord is configured
        if not ConfigValidator.validate_all(config):
            if logger:
                logger.debug("No valid Discord configuration found")
            sys.exit(0)  # Exit gracefully

        # Initialize components using new architecture
        http_client = HTTPClient(logger)
        formatter_registry = FormatterRegistry()

        # Create Discord context
        discord_context = DiscordContext(config=config, logger=logger, http_client=http_client)

        try:
            # Read event data from stdin
            raw_input = sys.stdin.read()
            if not raw_input.strip():
                if logger:
                    logger.debug("No input data received")
                sys.exit(0)

            # Parse JSON to extract event type and session ID for logging
            event_data = json.loads(raw_input)
            
            # Extract event type and session ID for raw JSON logging
            event_type_for_log = event_data.get("hook_event_name", "Unknown")
            session_id_for_log = str(
                event_data.get("session_id") or 
                event_data.get("Session") or 
                event_data.get("session") or 
                "unknown"
            )
            
            # Save raw JSON for debugging and analysis (CRITICAL for subagent problems)
            save_raw_json_log(raw_input, event_type_for_log, session_id_for_log)

            # Get event type from JSON data according to official Hook specification
            event_type = event_data.get("hook_event_name", "Unknown")

            # Check if this event should be processed based on filtering configuration
            if not should_process_event(event_type, config):
                if logger:
                    logger.debug("Event %s filtered out by configuration", event_type)
                sys.exit(0)  # Exit gracefully without processing

            # For tool-related events, check if the tool should be processed
            if event_type in ["PreToolUse", "PostToolUse"]:
                tool_name = event_data.get("tool_name", "Unknown")
                if not should_process_tool(tool_name, config):
                    if logger:
                        logger.debug("Tool %s filtered out by configuration", tool_name)
                    sys.exit(0)  # Exit gracefully without processing

            if logger:
                logger.info("Processing %s event", event_type)
                logger.debug("Event data: %s", json.dumps(event_data, indent=2))

            # Format message using new architecture
            message = format_event_message(event_type, event_data, formatter_registry, config)

            # Extract session ID for thread management
            session_id = str(
                event_data.get("session_id") or event_data.get("Session") or event_data.get("session") or ""
            )

            # Split message if it's too long to reduce information loss
            split_messages = split_long_message(message)
            
            # Send all split messages to Discord
            all_success = True
            for i, split_message in enumerate(split_messages):
                success = send_to_discord(
                    message=split_message, ctx=discord_context, session_id=session_id, event_type=event_type
                )
                
                if not success:
                    all_success = False
                    if logger:
                        logger.error("Failed to send %s notification part %d/%d", event_type, i+1, len(split_messages))
                else:
                    if logger and len(split_messages) > 1:
                        logger.info("%s notification part %d/%d sent successfully", event_type, i+1, len(split_messages))

            # Final success/failure logging
            if all_success:
                if logger:
                    if len(split_messages) > 1:
                        logger.info("%s notification sent successfully (split into %d parts)", event_type, len(split_messages))
                    else:
                        logger.info("%s notification sent successfully", event_type)
            else:
                if logger:
                    logger.error("Failed to send %s notification (some parts failed)", event_type)

        except json.JSONDecodeError as e:
            if logger:
                logger.exception("JSON decode error: %s", e)

        except EventProcessingError as e:
            if logger:
                logger.exception("Event processing error: %s", e)

        except DiscordAPIError as e:
            if logger:
                logger.exception("Discord API error: %s", e)

    except ConfigurationError as e:
        if logger:
            logger.debug("Configuration error: %s", e)
        sys.exit(0)  # Exit gracefully

    except (SystemExit, KeyboardInterrupt):
        # Re-raise system-level exceptions
        raise

    except Exception as e:
        # Catch all other errors to ensure we don't block Claude Code
        if logger:
            logger.exception("Unexpected error: %s", type(e).__name__)

    # Always exit 0 to not block Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
