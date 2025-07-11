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
if sys.version_info < (3, 13):
    print(f"ERROR: This project requires Python 3.13 or higher. You are using Python {sys.version}", file=sys.stderr)
    print("Please run with: uv run --no-sync --python 3.13 python src/discord_notifier.py", file=sys.stderr)
    sys.exit(1)

# Add parent directory to Python path when run as a script
from pathlib import Path
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

# TypeGuard and NotRequired are now available in Python 3.12+ typing module
from enum import Enum
from typing import (
    Any,
    Final,
    Literal,
    NotRequired,
    Protocol,
    TypedDict,
    TypeGuard,
    Union,
    cast,
)

# Try to import ThreadStorage - handle both module and script execution
try:
    # When run as a module
    from src.thread_storage import ThreadStorage

    THREAD_STORAGE_AVAILABLE = True
except ImportError:
    try:
        # When run as a script - try absolute import
        from thread_storage import ThreadStorage

        THREAD_STORAGE_AVAILABLE = True
    except ImportError:
        # ThreadStorage not available
        THREAD_STORAGE_AVAILABLE = False

# Try to import AstolfoLogger
try:
    # When run as a module
    from src.utils.astolfo_logger import setup_astolfo_logger, AstolfoLogger

    ASTOLFO_LOGGER_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from utils.astolfo_logger import setup_astolfo_logger, AstolfoLogger

        ASTOLFO_LOGGER_AVAILABLE = True
    except ImportError:
        # AstolfoLogger not available
        ASTOLFO_LOGGER_AVAILABLE = False
        AstolfoLogger = None  # Define as None when not available

        class ThreadStorage:  # type: ignore[no-redef]
            """Dummy ThreadStorage class when imports fail."""

            def __init__(self, *args: object, **kwargs: object) -> None:
                """Initialize dummy ThreadStorage that always raises ImportError."""
                _ = args, kwargs  # Mark as used
                raise ImportError("ThreadStorage module not available")

            def get_thread(self, session_id: str) -> None:
                """Get thread - always raises ImportError."""
                _ = session_id  # Mark as used
                raise ImportError("ThreadStorage module not available")

            def store_thread(self, **kwargs: object) -> None:
                """Store thread - always raises ImportError."""
                _ = kwargs  # Mark as used
                raise ImportError("ThreadStorage module not available")

            def remove_thread(self, session_id: str) -> None:
                """Remove thread - always raises ImportError."""
                _ = session_id  # Mark as used
                raise ImportError("ThreadStorage module not available")

# Try to import HTTPClient
try:
    # When run as a module
    from src.core.http_client import HTTPClient
    
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from core.http_client import HTTPClient
        
        HTTP_CLIENT_AVAILABLE = True
    except ImportError:
        # HTTPClient not available - this should not happen!
        HTTP_CLIENT_AVAILABLE = False
        raise ImportError("HTTPClient is required but could not be imported")

# Import SessionLogger for event persistence
try:
    # Add parent directory to path for imports
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from src.utils.session_logger import SessionLogger
    SESSION_LOGGER_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import SessionLogger: {e}")
    SESSION_LOGGER_AVAILABLE = False

# Import formatting utilities from base module
try:
    from src.formatters.base import (
        truncate_string,
        format_file_path,
        get_truncation_suffix,
        add_field,
        format_json_field,
    )
    FORMATTERS_BASE_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from formatters.base import (
            truncate_string,
            format_file_path,
            get_truncation_suffix,
            add_field,
            format_json_field,
        )
        FORMATTERS_BASE_AVAILABLE = True
    except ImportError:
        # Formatters base not available - use local definitions
        FORMATTERS_BASE_AVAILABLE = False

# Import validators
try:
    from src.validators import (
        # Validator classes
        ConfigValidator, EventDataValidator, ToolInputValidator,
        # Type guards
        is_tool_event_data, is_notification_event_data, is_stop_event_data,
        is_bash_tool_input, is_file_tool_input, is_search_tool_input,
        is_valid_event_type, is_bash_tool, is_file_tool, is_search_tool,
        is_list_tool, validate_thread_exists,
    )
    VALIDATORS_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from validators import (
            ConfigValidator, EventDataValidator, ToolInputValidator,
            is_tool_event_data, is_notification_event_data, is_stop_event_data,
            is_bash_tool_input, is_file_tool_input, is_search_tool_input,
            is_valid_event_type, is_bash_tool, is_file_tool, is_search_tool,
            is_list_tool, validate_thread_exists,
        )
        VALIDATORS_AVAILABLE = True
    except ImportError:
        # Validators not available - use local definitions
        VALIDATORS_AVAILABLE = False

# Import utils helpers
try:
    from src.utils_helpers import (
        truncate_string as utils_truncate_string,
        format_file_path as utils_format_file_path,
        ensure_thread_is_usable,
        SESSION_THREAD_CACHE,
    )
    UTILS_HELPERS_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from utils_helpers import (
            truncate_string as utils_truncate_string,
            format_file_path as utils_format_file_path,
            ensure_thread_is_usable,
            SESSION_THREAD_CACHE,
        )
        UTILS_HELPERS_AVAILABLE = True
    except ImportError:
        # Utils helpers not available - use local definitions
        UTILS_HELPERS_AVAILABLE = False
        SESSION_THREAD_CACHE = {}  # Initialize empty cache

# Import ConfigLoader
try:
    from src.core.config_loader import ConfigLoader
    CONFIG_LOADER_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from core.config_loader import ConfigLoader
        CONFIG_LOADER_AVAILABLE = True
    except ImportError:
        # ConfigLoader not available - will be defined later
        CONFIG_LOADER_AVAILABLE = False

# Import discord utils
try:
    from src.utils.discord_utils import (
        parse_env_file, parse_event_list, should_process_event
    )
    DISCORD_UTILS_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from utils.discord_utils import (
            parse_env_file, parse_event_list, should_process_event
        )
        DISCORD_UTILS_AVAILABLE = True
    except ImportError:
        # Discord utils not available - will be defined later
        DISCORD_UTILS_AVAILABLE = False

# Import FormatterRegistry
try:
    from src.handlers.event_registry import FormatterRegistry
    FORMATTER_REGISTRY_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from handlers.event_registry import FormatterRegistry
        FORMATTER_REGISTRY_AVAILABLE = True
    except ImportError:
        # FormatterRegistry not available - will be defined later
        FORMATTER_REGISTRY_AVAILABLE = False

# Import thread management functions
try:
    from src.core.thread_manager import (
        validate_thread_exists,
        find_existing_thread_by_name,
        ensure_thread_is_usable,
        get_or_create_thread,
        _check_thread_state,
        _try_unarchive_thread,
    )
    THREAD_MANAGER_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from core.thread_manager import (
            validate_thread_exists,
            find_existing_thread_by_name,
            ensure_thread_is_usable,
            get_or_create_thread,
            _check_thread_state,
            _try_unarchive_thread,
        )
        THREAD_MANAGER_AVAILABLE = True
    except ImportError:
        # Thread manager not available - will be defined later
        THREAD_MANAGER_AVAILABLE = False

# Import message sender functions
try:
    from src.core.message_sender import (
        send_to_discord,
        _split_embed_if_needed,
        _send_single_message,
        _send_stop_or_notification_event,
        _send_to_thread,
        _send_to_regular_channel,
    )
    MESSAGE_SENDER_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from core.message_sender import (
            send_to_discord,
            _split_embed_if_needed,
            _send_single_message,
            _send_stop_or_notification_event,
            _send_to_thread,
            _send_to_regular_channel,
        )
        MESSAGE_SENDER_AVAILABLE = True
    except ImportError:
        # Message sender not available - will be defined later
        MESSAGE_SENDER_AVAILABLE = False

# Import tool formatters
try:
    from src.formatters.tool_formatters import (
        format_bash_pre_use as tool_format_bash_pre_use,
        format_file_operation_pre_use as tool_format_file_operation_pre_use,
        format_search_tool_pre_use as tool_format_search_tool_pre_use,
        format_task_pre_use as tool_format_task_pre_use,
        format_web_fetch_pre_use as tool_format_web_fetch_pre_use,
        format_unknown_tool_pre_use as tool_format_unknown_tool_pre_use,
        format_bash_post_use as tool_format_bash_post_use,
        format_read_operation_post_use as tool_format_read_operation_post_use,
        format_write_operation_post_use as tool_format_write_operation_post_use,
        format_task_post_use as tool_format_task_post_use,
        format_web_fetch_post_use as tool_format_web_fetch_post_use,
        format_unknown_tool_post_use as tool_format_unknown_tool_post_use,
    )
    TOOL_FORMATTERS_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from formatters.tool_formatters import (
            format_bash_pre_use as tool_format_bash_pre_use,
            format_file_operation_pre_use as tool_format_file_operation_pre_use,
            format_search_tool_pre_use as tool_format_search_tool_pre_use,
            format_task_pre_use as tool_format_task_pre_use,
            format_web_fetch_pre_use as tool_format_web_fetch_pre_use,
            format_unknown_tool_pre_use as tool_format_unknown_tool_pre_use,
            format_bash_post_use as tool_format_bash_post_use,
            format_read_operation_post_use as tool_format_read_operation_post_use,
            format_write_operation_post_use as tool_format_write_operation_post_use,
            format_task_post_use as tool_format_task_post_use,
            format_web_fetch_post_use as tool_format_web_fetch_post_use,
            format_unknown_tool_post_use as tool_format_unknown_tool_post_use,
        )
        TOOL_FORMATTERS_AVAILABLE = True
    except ImportError:
        # Tool formatters not available
        TOOL_FORMATTERS_AVAILABLE = False

# Import event formatters
try:
    from src.formatters.event_formatters import (
        format_pre_tool_use,
        format_post_tool_use,
        format_notification,
        format_stop,
        format_subagent_stop,
        format_default_event,
        format_event,
    )
    EVENT_FORMATTERS_AVAILABLE = True
except ImportError:
    try:
        # When run as a script
        from formatters.event_formatters import (
            format_pre_tool_use,
            format_post_tool_use,
            format_notification,
            format_stop,
            format_subagent_stop,
            format_default_event,
            format_event,
        )
        EVENT_FORMATTERS_AVAILABLE = True
    except ImportError:
        # Event formatters not available - will be defined later
        EVENT_FORMATTERS_AVAILABLE = False


# Import custom exceptions
from src.exceptions import (
    DiscordNotifierError, ConfigurationError, DiscordAPIError,
    EventProcessingError, InvalidEventTypeError,
    ThreadManagementError, ThreadStorageError
)
# Import constants and enums
from src.constants import (
    ToolNames, EventTypes, TruncationLimits, DiscordLimits,
    DiscordColors, EVENT_TYPE_COLORS, EVENT_COLORS, TOOL_EMOJIS,
    ENV_WEBHOOK_URL, ENV_BOT_TOKEN, ENV_CHANNEL_ID, ENV_DEBUG,
    ENV_USE_THREADS, ENV_CHANNEL_TYPE, ENV_THREAD_PREFIX,
    ENV_MENTION_USER_ID, ENV_ENABLED_EVENTS, ENV_DISABLED_EVENTS,
    ENV_THREAD_STORAGE_PATH, ENV_THREAD_CLEANUP_DAYS, ENV_HOOK_EVENT,
    USER_AGENT, DEFAULT_TIMEOUT, TRUNCATION_SUFFIX,
    THREAD_CACHE_EXPIRY, CONFIG_FILE_NAME
)


# Import base types from new module
from src.type_defs.base import BaseField, TimestampedField, SessionAware, PathAware
# Import Discord types from new module
from src.type_defs.discord import (
    DiscordFooter, DiscordFieldBase, DiscordField,
    DiscordEmbedBase, DiscordEmbed, DiscordMessageBase,
    DiscordMessage, DiscordChannel, DiscordThread,
    DiscordThreadMessage
)
# Import config types from new module
from src.type_defs.config import (
    DiscordCredentials, ThreadConfiguration,
    NotificationConfiguration, EventFilterConfiguration,
    Config
)
# Import tool types from new module
from src.type_defs.tools import (
    ToolInputBase, BashToolInput, FileEditOperation,
    FileToolInputBase, ReadToolInput, WriteToolInput,
    EditToolInput, MultiEditToolInput, ListToolInput,
    SearchToolInputBase, GlobToolInput, GrepToolInput,
    TaskToolInput, WebToolInput, FileToolInput, SearchToolInput,
    ToolInput, ToolResponseBase, BashToolResponse,
    FileOperationResponse, SearchResponse, ToolResponse
)
# Import event types from new module
from src.type_defs.events import (
    BaseEventData, ToolEventDataBase, PreToolUseEventData,
    PostToolUseEventData, NotificationEventData,
    StopEventDataBase, StopEventData, SubagentStopEventData,
    EventData
)

# ==============================================================================
# TYPE DEFINITIONS: HIERARCHICAL TYPEDDICT STRUCTURE
# ==============================================================================









# ------------------------------------------------------------------------------
# 7. ENHANCED TYPE SAFETY FEATURES
# ------------------------------------------------------------------------------


# Type guard functions are now imported from validators module


# Validators are now imported from validators module




# ==============================================================================
# END OF TYPE DEFINITIONS
# ==============================================================================

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



# Thread management is now imported from utils_helpers module


# Type guards are now imported from validators module


# Utility functions
# Define truncate_string only if both formatters.base and utils_helpers import failed
# Define format_file_path only if formatters.base and utils_helpers import failed
# parse_env_file and parse_event_list are now imported from discord_utils module

# Define should_process_event only if discord_utils import failed
# Define get_truncation_suffix only if formatters.base import failed
# Define add_field only if formatters.base import failed
# Define format_json_field only if formatters.base import failed
# Formatter base class
class EventFormatter(Protocol):
    """Protocol for event formatters."""

    def format(self, event_data: EventData, session_id: str) -> DiscordEmbed:
        """Format event data into Discord embed."""
        ...


# Conditionally define thread management functions if not imported
# ConfigLoader is now imported from core.config_loader module


def setup_logging(debug: bool) -> logging.Logger:
    """Set up logging with optional debug mode."""
    if ASTOLFO_LOGGER_AVAILABLE:
        # Use AstolfoLogger for structured logging
        print(f"[DEBUG] Using AstolfoLogger (ASTOLFO_LOGGER_AVAILABLE={ASTOLFO_LOGGER_AVAILABLE})", file=sys.stderr)
        print(f"[DEBUG] Debug level will be: {os.environ.get('DISCORD_DEBUG_LEVEL', '1')}", file=sys.stderr)
        return setup_astolfo_logger(__name__)
    else:
        # Fallback to standard logging
        print(f"[DEBUG] Using standard logger (ASTOLFO_LOGGER_AVAILABLE={ASTOLFO_LOGGER_AVAILABLE})", file=sys.stderr)
        logger = logging.getLogger(__name__)

        if debug:
            log_dir = Path.home() / ".claude" / "hooks" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"discord_notifier_{datetime.now(UTC).strftime('%Y-%m-%d')}.log"

            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.FileHandler(log_file, mode="a"),
                    logging.StreamHandler(sys.stderr),
                ],
            )
        else:
            # Only log errors to stderr in non-debug mode
            logging.basicConfig(
                level=logging.ERROR,
                format="%(levelname)s: %(message)s",
                handlers=[logging.StreamHandler(sys.stderr)],
            )

        return logger


# Tool-specific formatters - these are adapters for the imported tool formatters


def format_event(
    event_type: str,
    event_data: EventData,
    registry: FormatterRegistry,
    config: Config,
) -> DiscordMessage:
    """Format Claude Code event into Discord embed with length limits."""
    timestamp = datetime.now(UTC).isoformat()
    session_id = event_data.get("session_id", "unknown")[:8]

    # Get formatter for event type
    formatter = registry.get_formatter(event_type)
    embed = formatter(event_data, session_id)

    # Enforce Discord's length limits
    if "title" in embed and len(embed["title"]) > DiscordLimits.MAX_TITLE_LENGTH:
        embed["title"] = truncate_string(embed["title"], DiscordLimits.MAX_TITLE_LENGTH)

    if "description" in embed and len(embed["description"]) > DiscordLimits.MAX_DESCRIPTION_LENGTH:
        embed["description"] = truncate_string(embed["description"], DiscordLimits.MAX_DESCRIPTION_LENGTH)

    # Add common fields
    embed["timestamp"] = timestamp

    # Get color for event type
    if is_valid_event_type(event_type):
        embed["color"] = EVENT_COLORS.get(event_type, DiscordColors.DEFAULT)
    else:
        embed["color"] = DiscordColors.DEFAULT

    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type}"}

    # Create message with embeds
    message: DiscordMessage = {"embeds": [embed]}

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


# Conditionally define message sender functions if not imported
# Global session loggers for persistence
if SESSION_LOGGER_AVAILABLE:
    _session_loggers: dict[str, SessionLogger] = {}
else:
    _session_loggers: dict[str, Any] = {}


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
        logger.debug(f"SESSION_LOGGER_AVAILABLE = {SESSION_LOGGER_AVAILABLE}, DISCORD_ENABLE_SESSION_LOGGING = {session_logging_enabled}")
        if SESSION_LOGGER_AVAILABLE and session_logging_enabled == "1":
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
                                event_type, enriched_data
                            )
                        )
                        # Prevent uncaught exception warnings
                        task.add_done_callback(lambda t: None)
                        
            except Exception:
                # Silently ignore all session logging errors
                pass

        # Check if this event should be processed based on filtering configuration
        if not should_process_event(event_type, config):
            if ASTOLFO_LOGGER_AVAILABLE and AstolfoLogger and isinstance(logger, AstolfoLogger):
                logger.debug(
                    "event_filtered",
                    context={"event_type": event_type},
                    ai_todo="Event was filtered out by user configuration"
                )
            else:
                logger.debug("Event %s filtered out by configuration", event_type)
            sys.exit(0)  # Exit gracefully without processing

        # Set session ID for AstolfoLogger
        if ASTOLFO_LOGGER_AVAILABLE and AstolfoLogger and isinstance(logger, AstolfoLogger):
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
        success = send_to_discord(message, config, logger, http_client, session_id, event_type)

        if success:
            if ASTOLFO_LOGGER_AVAILABLE and AstolfoLogger and isinstance(logger, AstolfoLogger):
                logger.info(
                    "notification_sent",
                    context={"event_type": event_type, "session_id": session_id},
                    ai_todo="Notification sent successfully to Discord"
                )
            else:
                logger.info("%s notification sent successfully", event_type)
        else:
            if ASTOLFO_LOGGER_AVAILABLE and AstolfoLogger and isinstance(logger, AstolfoLogger):
                logger.error(
                    "notification_failed",
                    context={"event_type": event_type, "session_id": session_id},
                    ai_todo="Failed to send notification. Check Discord configuration and API errors"
                )
            else:
                logger.error("Failed to send %s notification", event_type)

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
        if SESSION_LOGGER_AVAILABLE and _session_loggers:
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
                try:
                    loop.run_until_complete(session_logger.close())
                except Exception:
                    pass

    # Always exit 0 to not block Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
