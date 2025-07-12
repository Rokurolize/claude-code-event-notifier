"""Discord utility functions.

This module contains utility functions for Discord operations
including parsing, event filtering, and formatting helpers.
"""

from pathlib import Path
from typing import cast

# Try to import types
try:
    from src.type_defs.config import Config
except ImportError:
    from discord_notifier import Config  # type: ignore

# Try to import validators
try:
    from src.validators import is_valid_event_type
except ImportError:
    from discord_notifier import is_valid_event_type  # type: ignore

# Try to import exceptions
try:
    from src.exceptions import ConfigurationError
except ImportError:
    from discord_notifier import ConfigurationError  # type: ignore

# Try to import AstolfoLogger
try:
    from src.utils.astolfo_logger import AstolfoLogger
except ImportError:
    # Create a dummy logger if import fails
    class AstolfoLogger:  # type: ignore
        @staticmethod
        def info(msg: str, **kwargs) -> None:
            pass
        @staticmethod
        def debug(msg: str, **kwargs) -> None:
            pass
        @staticmethod
        def warning(msg: str, **kwargs) -> None:
            pass
        @staticmethod
        def error(msg: str, **kwargs) -> None:
            pass

# Initialize logger for this module
logger = AstolfoLogger("discord_utils")


def parse_env_file(file_path: Path) -> dict[str, str]:
    """Parse environment file and return key-value pairs.

    Parses .env format files containing KEY=VALUE pairs, with support for
    comments and quoted values. Used to load Discord configuration from
    the ~/.claude/hooks/.env.discord file.

    Args:
        file_path: Path to the environment file to parse

    Returns:
        dict[str, str]: Dictionary mapping environment variable names to values

    Raises:
        ConfigurationError: If file cannot be read or parsed

    File Format:
        - KEY=VALUE pairs, one per line
        - Comments start with # and are ignored
        - Values can be quoted with single or double quotes
        - Quotes are stripped from values
        - Empty lines are ignored

    Example File Content:
        ```
        # Discord configuration
        DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123/abc
        DISCORD_TOKEN="your_bot_token_here"
        DISCORD_CHANNEL_ID='123456789012345678'
        # Thread settings
        DISCORD_USE_THREADS=1
        ```

    Example Usage:
        >>> env_vars = parse_env_file(Path(".env.discord"))
        >>> webhook_url = env_vars.get("DISCORD_WEBHOOK_URL")

    Error Handling:
        - IOError: File access issues (permissions, file not found)
        - ValueError: Line parsing issues (malformed KEY=VALUE pairs)
        - Both result in ConfigurationError being raised
    """
    logger.debug(f"Parsing environment file", file_path=str(file_path))
    env_vars: dict[str, str] = {}

    try:
        with open(file_path) as f:
            line_count = 0
            for line in f:
                line_count += 1
                stripped_line = line.strip()
                if "=" in stripped_line and not stripped_line.startswith("#"):
                    key, value = stripped_line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_vars[key] = value
                    logger.debug(f"Parsed environment variable", key=key, has_value=bool(value))
            
            logger.info(f"Successfully parsed environment file", 
                       file_path=str(file_path), 
                       total_lines=line_count,
                       parsed_vars=len(env_vars))
    except (OSError, ValueError) as e:
        logger.error(f"Failed to parse environment file", 
                    file_path=str(file_path), 
                    error_type=type(e).__name__, 
                    error_msg=str(e))
        raise ConfigurationError(f"Error reading {file_path}: {e}") from e

    return env_vars


def parse_event_list(event_list_str: str) -> list[str]:
    """Parse comma-separated event list string into validated list.

    Parses environment variable values like "Stop,Notification" into a list
    of valid event type strings. Invalid event types are filtered out with
    debug logging.

    Args:
        event_list_str: Comma-separated string of event types

    Returns:
        list[str]: List of valid event type strings

    Example:
        >>> parse_event_list("Stop,Notification,InvalidEvent")
        ['Stop', 'Notification']
        >>> parse_event_list("")
        []
        >>> parse_event_list("  PreToolUse  ,  PostToolUse  ")
        ['PreToolUse', 'PostToolUse']
    """
    if not event_list_str:
        logger.debug("Empty event list string provided")
        return []

    logger.debug(f"Parsing event list", event_list_str=event_list_str)
    
    # Split and clean up event names
    events = [event.strip() for event in event_list_str.split(",")]
    valid_events = []
    invalid_events = []

    # Filter to only valid event types
    for event in events:
        if event and is_valid_event_type(event):
            valid_events.append(event)
            logger.debug(f"Valid event type found", event=event)
        elif event:  # Non-empty but invalid
            invalid_events.append(event)
            logger.warning(f"Invalid event type filtered out", event=event)

    logger.info(f"Event list parsed", 
               total_events=len(events),
               valid_events=len(valid_events),
               invalid_events=len(invalid_events),
               valid_list=valid_events)
    
    return valid_events


def should_process_event(event_type: str, config: Config) -> bool:
    """Determine if an event should be processed based on filtering configuration.

    Implements event filtering logic with the following precedence:
    1. If enabled_events is configured, only process events in that list
    2. If disabled_events is configured, skip events in that list
    3. If both are configured, enabled_events takes precedence
    4. If neither is configured, process all events (default behavior)

    Args:
        event_type: The type of event to check
        config: Discord configuration containing filter settings

    Returns:
        bool: True if event should be processed, False if it should be skipped

    Example:
        >>> config = {"enabled_events": ["Stop", "Notification"]}
        >>> should_process_event("Stop", config)  # True
        >>> should_process_event("PreToolUse", config)  # False

        >>> config = {"disabled_events": ["PreToolUse", "PostToolUse"]}
        >>> should_process_event("Stop", config)  # True
        >>> should_process_event("PreToolUse", config)  # False

    Configuration Priority:
        - enabled_events has higher priority than disabled_events
        - Empty lists are treated as unconfigured (no filtering)
        - Invalid event types in lists are ignored
    """
    enabled_events = config.get("enabled_events")
    disabled_events = config.get("disabled_events")
    
    logger.debug(f"Checking if event should be processed", 
                event_type=event_type,
                has_enabled_filter=bool(enabled_events),
                has_disabled_filter=bool(disabled_events))

    # If enabled_events is configured, only process events in that list
    if enabled_events:
        should_process = event_type in enabled_events
        logger.info(f"Event filtering decision (enabled list)",
                   event_type=event_type,
                   should_process=should_process,
                   enabled_events=enabled_events)
        return should_process

    # If disabled_events is configured, skip events in that list
    if disabled_events:
        should_process = event_type not in disabled_events
        logger.info(f"Event filtering decision (disabled list)",
                   event_type=event_type,
                   should_process=should_process,
                   disabled_events=disabled_events)
        return should_process

    # Default: process all events
    logger.info(f"Event filtering decision (no filters)",
               event_type=event_type,
               should_process=True)
    return True


# Export all public functions
__all__ = ['parse_env_file', 'parse_event_list', 'should_process_event']