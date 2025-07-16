#!/usr/bin/env python3
"""Main entry point for new architecture Discord Notifier.

This module serves as the entry point for the modularized Discord notification
system, integrating all components from the new architecture.

Usage:
    CLAUDE_HOOK_EVENT=PreToolUse python3 main.py < event.json

Architecture Integration:
    - Configuration: src.core.config
    - HTTP Client: src.core.http_client
    - Event Processing: src.handlers.event_registry
    - Discord Messaging: src.handlers.discord_sender
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import new architecture components
from src.core.config import Config, ConfigLoader, ConfigValidator, ConfigFileWatcher, setup_logging, should_process_event, should_process_tool
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
            event_data.get("session_id") or
            event_data.get("Session") or
            event_data.get("session") or
            "unknown"
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
                # For notifications, extract meaningful content from embed
                display_message = embed.get("description", "System notification")[:100]
            else:  # Stop event
                display_message = "Session ended"
                
            message["content"] = f"<@{config['mention_user_id']}> {display_message}"
            
        return message
        
    except Exception as e:
        raise EventProcessingError(f"Failed to format {event_type} event: {e}") from e


def send_config_notification(message: str, is_error: bool = False) -> None:
    """Send configuration change notification to Discord.
    
    Args:
        message: Notification message to send
        is_error: Whether this is an error notification
    """
    try:
        # Create a simple notification message
        notification_data = {
            "session_id": "config-watcher",
            "message": message
        }
        
        # Load basic config for sending notification
        basic_config = ConfigLoader.load()
        if not ConfigValidator.validate_credentials(basic_config):
            return  # No valid Discord config, skip notification
            
        # Initialize HTTP client for notification
        http_client = HTTPClient(None)  # No logger for notifications
        
        # Create Discord context for notification
        discord_context = DiscordContext(
            config=basic_config,
            logger=None,
            http_client=http_client
        )
        
        # Create embed for config change notification
        embed = {
            "title": "⚙️ Configuration Update" if not is_error else "⚠️ Configuration Error",
            "description": message,
            "color": DiscordColors.BLUE if not is_error else DiscordColors.RED,
            "timestamp": datetime.now(UTC).isoformat(),
            "footer": {"text": "Discord Notifier • Hot Reload System"}
        }
        
        notification_message = {"embeds": [embed]}
        
        # Send notification
        send_to_discord(
            message=notification_message,
            ctx=discord_context,
            session_id="config-watcher",
            event_type="ConfigUpdate"
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
        discord_context = DiscordContext(
            config=config,
            logger=logger,
            http_client=http_client
        )
        
        try:
            # Read event data from stdin
            raw_input = sys.stdin.read()
            if not raw_input.strip():
                if logger:
                    logger.debug("No input data received")
                sys.exit(0)
                
            event_data = json.loads(raw_input)
            
            # Get event type from environment
            event_type = os.environ.get(ENV_HOOK_EVENT, "Unknown")
            
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
                event_data.get("session_id") or
                event_data.get("Session") or
                event_data.get("session") or
                ""
            )
            
            # Send to Discord using new architecture
            success = send_to_discord(
                message=message,
                ctx=discord_context,
                session_id=session_id,
                event_type=event_type
            )
            
            if success:
                if logger:
                    logger.info("%s notification sent successfully", event_type)
            else:
                if logger:
                    logger.error("Failed to send %s notification", event_type)
                    
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