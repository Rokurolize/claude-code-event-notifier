"""Validators for Discord Notifier.

This module contains all validation logic including type guards,
configuration validators, and event data validators.
"""

from typing import TypeGuard, cast, Any, TYPE_CHECKING
from src.utils.astolfo_logger import setup_astolfo_logger

# Try to import types from type_defs module first
try:
    from src.type_defs.base import BaseField
    from src.type_defs.tools import (
        ToolInput, BashToolInput, FileToolInputBase, SearchToolInputBase,
        WebToolInput
    )
    from src.type_defs.events import (
        EventData, ToolEventDataBase, NotificationEventData, StopEventDataBase
    )
    from src.type_defs.config import Config
except ImportError:
    # Fallback imports from discord_notifier if type_defs not available
    from discord_notifier import (  # type: ignore
        BaseField, ToolInput, BashToolInput, FileToolInputBase,
        SearchToolInputBase, EventData, ToolEventDataBase,
        NotificationEventData, StopEventDataBase, Config
    )
    # Create WebToolInput type if not available
    from typing import TypedDict
    class WebToolInput(TypedDict):  # type: ignore
        url: str
        prompt: str

if TYPE_CHECKING:
    from src.core.http_client import HTTPClient

# Try to import constants
try:
    from src.constants import EventTypes, ToolNames
except ImportError:
    # Fallback imports from discord_notifier if constants not available
    from discord_notifier import EventTypes, ToolNames  # type: ignore

# Initialize logger for validation tracking
logger = setup_astolfo_logger(__name__)


# Type guard functions
def is_tool_event_data(data: EventData) -> TypeGuard[ToolEventDataBase]:
    """Check if event data is tool-related."""
    return "tool_name" in data


def is_notification_event_data(
    data: EventData,
) -> TypeGuard[NotificationEventData]:
    """Check if event data is notification-related."""
    return "message" in data


def is_stop_event_data(data: EventData) -> TypeGuard[StopEventDataBase]:
    """Check if event data is stop-related."""
    return "hook_event_name" in data


def is_bash_tool_input(tool_input: ToolInput) -> TypeGuard[BashToolInput]:
    """Check if tool input is for Bash tool."""
    return "command" in tool_input


def is_file_tool_input(tool_input: ToolInput) -> TypeGuard[FileToolInputBase]:
    """Check if tool input is for file operations."""
    return "file_path" in tool_input


def is_search_tool_input(tool_input: ToolInput) -> TypeGuard[SearchToolInputBase]:
    """Check if tool input is for search operations."""
    return "pattern" in tool_input


def is_web_tool_input(tool_input: ToolInput) -> TypeGuard[WebToolInput]:
    """Check if tool input is for web operations."""
    return "url" in tool_input and "prompt" in tool_input


def is_valid_event_type(event_type: str) -> TypeGuard[str]:
    """Check if event type is valid."""
    return event_type in {e.value for e in EventTypes}


def is_bash_tool(tool_name: str) -> bool:
    """Check if tool is Bash."""
    return tool_name == ToolNames.BASH.value


def is_file_tool(tool_name: str) -> bool:
    """Check if tool is a file operation tool."""
    return tool_name in {
        ToolNames.READ.value,
        ToolNames.WRITE.value,
        ToolNames.EDIT.value,
        ToolNames.MULTI_EDIT.value,
    }


def is_search_tool(tool_name: str) -> bool:
    """Check if tool is a search tool."""
    return tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value}


def is_list_tool(tool_name: str) -> bool:
    """Check if tool returns list results."""
    return tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value, ToolNames.LS.value}


# Configuration validation
class ConfigValidator:
    """Validator for Config TypedDict.

    Provides static methods to validate different aspects of the Discord
    configuration. Used to ensure configuration consistency and completeness
    before attempting to send messages.

    Validation Areas:
        - Credentials: Webhook URL or bot token/channel ID combination
        - Thread configuration: Consistency between channel type and auth method
        - Mention configuration: Valid Discord user ID format

    Usage:
        >>> config = ConfigLoader.load()
        >>> if not ConfigValidator.validate_all(config):
        ...     raise ConfigurationError("Invalid configuration")
    """

    @staticmethod
    def validate_credentials(config: Config) -> bool:
        """Validate that at least one credential method is configured.

        Checks that either webhook URL or bot token/channel ID combination
        is available for Discord API access.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if valid credentials are configured, False otherwise

        Validation Logic:
            - Webhook URL alone is sufficient for basic messaging
            - Bot token + channel ID combination is required for bot API
            - At least one method must be configured

        Example:
            >>> config = {"webhook_url": "https://discord.com/api/webhooks/..."}
            >>> ConfigValidator.validate_credentials(config)  # True
            >>> config = {"bot_token": "token", "channel_id": "123"}
            >>> ConfigValidator.validate_credentials(config)  # True
            >>> config = {"bot_token": "token"}  # Missing channel_id
            >>> ConfigValidator.validate_credentials(config)  # False
        """
        has_webhook = bool(config.get("webhook_url"))
        has_bot_credentials = bool(config.get("bot_token") and config.get("channel_id"))
        
        if not (has_webhook or has_bot_credentials):
            logger.error(
                "credential_validation_failed",
                context={
                    "has_webhook": has_webhook,
                    "has_bot_token": bool(config.get("bot_token")),
                    "has_channel_id": bool(config.get("channel_id"))
                },
                ai_todo="Either webhook_url or both bot_token and channel_id must be configured"
            )
            return False
            
        return True

    @staticmethod
    def validate_thread_config(config: Config) -> bool:
        """Validate thread configuration consistency.

        Ensures that thread configuration is consistent with available
        authentication methods and channel types.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if thread configuration is valid, False otherwise

        Validation Rules:
            - If threads are disabled, configuration is always valid
            - Forum channels require webhook URL for thread creation
            - Text channels require bot token + channel ID for thread creation
            - Invalid channel types are rejected

        Thread Types:
            - Forum channels: Use webhook API with thread_name parameter
            - Text channels: Use bot API to create public threads

        Example:
            >>> # Valid forum channel config
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "forum",
            ...     "webhook_url": "https://discord.com/api/webhooks/..."
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # True

            >>> # Invalid: forum channel without webhook
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "forum",
            ...     "bot_token": "token"
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # False
        """
        if not config.get("use_threads", False):
            return True

        channel_type = cast("str", config.get("channel_type", "text"))
        
        if channel_type == "forum":
            if not config.get("webhook_url"):
                logger.error(
                    "thread_config_validation_failed",
                    context={
                        "channel_type": "forum",
                        "reason": "Forum channels require webhook_url"
                    },
                    ai_todo="Configure webhook_url for forum channel thread creation"
                )
                return False
            return True
            
        if channel_type == "text":
            if not (config.get("bot_token") and config.get("channel_id")):
                logger.error(
                    "thread_config_validation_failed",
                    context={
                        "channel_type": "text",
                        "has_bot_token": bool(config.get("bot_token")),
                        "has_channel_id": bool(config.get("channel_id")),
                        "reason": "Text channels require bot_token and channel_id"
                    },
                    ai_todo="Configure bot_token and channel_id for text channel thread creation"
                )
                return False
            return True
            
        # Invalid channel type
        logger.error(
            "thread_config_validation_failed",
            context={
                "channel_type": channel_type,
                "reason": "Invalid channel type, must be 'forum' or 'text'"
            },
            ai_todo="Set channel_type to either 'forum' or 'text'"
        )
        return False

    @staticmethod
    def validate_mention_config(config: Config) -> bool:
        """Validate mention configuration.

        Validates Discord user ID format for mention functionality.
        Discord user IDs are numeric strings with specific length requirements.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if mention configuration is valid, False otherwise

        Validation Rules:
            - If no mention_user_id is configured, validation passes
            - Discord user IDs must be numeric strings
            - Discord user IDs must be at least 17 characters long
            - User IDs are typically 17-19 characters in length

        Discord User ID Format:
            - Numeric string (e.g., "123456789012345678")
            - Generated using Discord's snowflake algorithm
            - Unique across all Discord users

        Example:
            >>> # Valid user ID
            >>> config = {"mention_user_id": "123456789012345678"}
            >>> ConfigValidator.validate_mention_config(config)  # True

            >>> # Invalid: non-numeric
            >>> config = {"mention_user_id": "invalid_id"}
            >>> ConfigValidator.validate_mention_config(config)  # False

            >>> # Invalid: too short
            >>> config = {"mention_user_id": "12345"}
            >>> ConfigValidator.validate_mention_config(config)  # False
        """
        mention_user_id = config.get("mention_user_id")
        if mention_user_id:
            # Basic validation: Discord user IDs are numeric strings
            if not mention_user_id.isdigit():
                logger.error(
                    "mention_config_validation_failed",
                    context={
                        "mention_user_id": mention_user_id,
                        "reason": "Discord user ID must be numeric"
                    },
                    ai_todo="Provide a valid numeric Discord user ID"
                )
                return False
                
            if len(mention_user_id) < 17:
                logger.error(
                    "mention_config_validation_failed", 
                    context={
                        "mention_user_id_length": len(mention_user_id),
                        "reason": "Discord user ID too short (must be at least 17 characters)"
                    },
                    ai_todo="Provide a valid Discord user ID (17-19 numeric characters)"
                )
                return False
                
            return True
        return True

    @staticmethod
    def validate_all(config: Config) -> bool:
        """Validate all configuration aspects.

        Performs comprehensive validation of all configuration aspects,
        ensuring the configuration is complete and consistent.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if all validation checks pass, False otherwise

        Validation Performed:
            1. Credentials validation (webhook URL or bot token/channel ID)
            2. Thread configuration consistency
            3. Mention configuration format

        Usage:
            This is the recommended method for validating configuration
            before using the Discord notifier.

        Example:
            >>> config = ConfigLoader.load()
            >>> if not ConfigValidator.validate_all(config):
            ...     raise ConfigurationError("Configuration validation failed")
            >>> # Safe to use config for Discord operations

        Failure Scenarios:
            - No authentication method configured
            - Thread configuration mismatch with auth method
            - Invalid Discord user ID format
            - Missing required fields for selected features
        """
        return (
            ConfigValidator.validate_credentials(config)
            and ConfigValidator.validate_thread_config(config)
            and ConfigValidator.validate_mention_config(config)
        )


# Event data validation
class EventDataValidator:
    """Validator for EventData structures."""

    @staticmethod
    def validate_base_event_data(data: EventData) -> bool:
        """Validate base event data requirements."""
        required_fields = {"session_id", "hook_event_name"}
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(
                "event_data_validation_failed",
                context={
                    "missing_fields": ", ".join(missing_fields),
                    "provided_fields": ", ".join(data.keys()) if isinstance(data, dict) else "invalid_data_type"
                },
                ai_todo=f"Ensure event data includes required fields: {', '.join(required_fields)}"
            )
            return False
            
        return True

    @staticmethod
    def validate_tool_event_data(data: EventData) -> bool:
        """Validate tool event data requirements."""
        if not EventDataValidator.validate_base_event_data(data):
            return False

        required_fields = {"tool_name", "tool_input"}
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(
                "tool_event_data_validation_failed",
                context={
                    "missing_fields": ", ".join(missing_fields),
                    "event_type": "tool_event"
                },
                ai_todo=f"Tool events require fields: {', '.join(required_fields)}"
            )
            return False
            
        return True

    @staticmethod
    def validate_notification_event_data(data: EventData) -> bool:
        """Validate notification event data requirements."""
        if not EventDataValidator.validate_base_event_data(data):
            return False

        if "message" not in data:
            logger.error(
                "notification_event_data_validation_failed",
                context={
                    "reason": "Missing 'message' field",
                    "event_type": "notification"
                },
                ai_todo="Notification events require a 'message' field"
            )
            return False
            
        return True

    @staticmethod
    def validate_stop_event_data(data: EventData) -> bool:
        """Validate stop event data requirements."""
        return EventDataValidator.validate_base_event_data(data)


# Tool input validation
class ToolInputValidator:
    """Validator for ToolInput structures."""

    @staticmethod
    def validate_bash_input(tool_input: ToolInput) -> bool:
        """Validate Bash tool input."""
        if not is_bash_tool_input(tool_input):
            logger.error(
                "bash_tool_input_validation_failed",
                context={
                    "reason": "Missing 'command' field",
                    "tool": "Bash"
                },
                ai_todo="Bash tool requires a 'command' field in tool_input"
            )
            return False
            
        # Type guard ensures 'command' exists, now check its type
        command = tool_input.get("command")
        if not isinstance(command, str):
            logger.error(
                "bash_tool_input_validation_failed",
                context={
                    "reason": "Invalid command type",
                    "command_type": type(command).__name__ if command is not None else "None",
                    "tool": "Bash"
                },
                ai_todo="Bash tool 'command' field must be a string"
            )
            return False
            
        return True

    @staticmethod
    def validate_file_input(tool_input: ToolInput) -> bool:
        """Validate file tool input."""
        if not is_file_tool_input(tool_input):
            logger.error(
                "file_tool_input_validation_failed",
                context={
                    "reason": "Missing 'file_path' field",
                    "tool": "File operation"
                },
                ai_todo="File tools require a 'file_path' field in tool_input"
            )
            return False
            
        # Type guard ensures 'file_path' exists, now check its type
        file_path = tool_input.get("file_path")
        if not isinstance(file_path, str):
            logger.error(
                "file_tool_input_validation_failed",
                context={
                    "reason": "Invalid file_path type",
                    "file_path_type": type(file_path).__name__ if file_path is not None else "None",
                    "tool": "File operation"
                },
                ai_todo="File tool 'file_path' field must be a string"
            )
            return False
            
        return True

    @staticmethod
    def validate_search_input(tool_input: ToolInput) -> bool:
        """Validate search tool input."""
        if not is_search_tool_input(tool_input):
            logger.error(
                "search_tool_input_validation_failed",
                context={
                    "reason": "Missing 'pattern' field",
                    "tool": "Search operation"
                },
                ai_todo="Search tools require a 'pattern' field in tool_input"
            )
            return False
            
        # Type guard ensures 'pattern' exists, now check its type
        pattern = tool_input.get("pattern")
        if not isinstance(pattern, str):
            logger.error(
                "search_tool_input_validation_failed",
                context={
                    "reason": "Invalid pattern type",
                    "pattern_type": type(pattern).__name__ if pattern is not None else "None",
                    "tool": "Search operation"
                },
                ai_todo="Search tool 'pattern' field must be a string"
            )
            return False
            
        return True

    @staticmethod
    def validate_web_input(tool_input: ToolInput) -> bool:
        """Validate web tool input."""
        if not is_web_tool_input(tool_input):
            logger.error(
                "web_tool_input_validation_failed",
                context={
                    "reason": "Missing required fields",
                    "has_url": "url" in tool_input,
                    "has_prompt": "prompt" in tool_input,
                    "tool": "Web operation"
                },
                ai_todo="Web tools require both 'url' and 'prompt' fields in tool_input"
            )
            return False
            
        # Type guard ensures both fields exist, now check their types
        url = tool_input.get("url")
        prompt = tool_input.get("prompt")
        
        if not isinstance(url, str):
            logger.error(
                "web_tool_input_validation_failed",
                context={
                    "reason": "Invalid url type",
                    "url_type": type(url).__name__ if url is not None else "None",
                    "tool": "Web operation"
                },
                ai_todo="Web tool 'url' field must be a string"
            )
            return False
            
        if not isinstance(prompt, str):
            logger.error(
                "web_tool_input_validation_failed",
                context={
                    "reason": "Invalid prompt type",
                    "prompt_type": type(prompt).__name__ if prompt is not None else "None",
                    "tool": "Web operation"
                },
                ai_todo="Web tool 'prompt' field must be a string"
            )
            return False
            
        return True


# Thread validation
def validate_thread_exists(
    thread_id: str,
    http_client: "HTTPClient",
    channel_id: str,
    bot_token: str,
) -> bool:
    """Validate that a thread exists and is accessible.

    Args:
        thread_id: Discord thread ID to validate
        http_client: HTTP client instance for API calls
        channel_id: Discord channel ID (not used, kept for backward compatibility)
        bot_token: Discord bot token for authentication

    Returns:
        bool: True if thread exists and is accessible, False otherwise
    """
    try:
        thread_data = http_client.get_thread_details(thread_id, bot_token)
        if thread_data is None:
            logger.warning(
                "thread_validation_failed",
                context={
                    "thread_id": thread_id,
                    "reason": "Thread not found or not accessible"
                },
                ai_todo="Verify thread ID is correct and bot has access to the thread"
            )
            return False
        return True
    except Exception as e:
        logger.error(
            "thread_validation_error",
            exception=e,
            context={
                "thread_id": thread_id,
                "reason": "Exception during thread validation"
            },
            ai_todo="Check Discord API connection and bot permissions"
        )
        return False


# Export all public validators
__all__ = [
    # Validator classes
    'ConfigValidator', 'EventDataValidator', 'ToolInputValidator',
    # Type guards
    'is_tool_event_data', 'is_notification_event_data', 'is_stop_event_data',
    'is_bash_tool_input', 'is_file_tool_input', 'is_search_tool_input',
    'is_web_tool_input', 'is_valid_event_type', 'is_bash_tool', 'is_file_tool', 
    'is_search_tool', 'is_list_tool',
    # Thread validation
    'validate_thread_exists',
]