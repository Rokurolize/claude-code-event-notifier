"""Validators for Discord Notifier.

This module contains all validation logic including type guards,
configuration validators, and event data validators.
"""

from typing import TypeGuard, cast, Any

# Try to import types from type_defs module first
try:
    from src.type_defs.base import BaseField, ToolInput
    from src.type_defs.tools import (
        BashToolInput, FileToolInputBase, SearchToolInputBase
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

# Try to import constants
try:
    from src.constants import EventTypes, ToolNames
except ImportError:
    # Fallback imports from discord_notifier if constants not available
    from discord_notifier import EventTypes, ToolNames  # type: ignore


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
        return bool(config.get("webhook_url") or (config.get("bot_token") and config.get("channel_id")))

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
            return bool(config.get("webhook_url"))
        if channel_type == "text":
            return bool(config.get("bot_token") and config.get("channel_id"))
        # Invalid channel type
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
            return mention_user_id.isdigit() and len(mention_user_id) >= 17
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
        return all(field in data for field in required_fields)

    @staticmethod
    def validate_tool_event_data(data: EventData) -> bool:
        """Validate tool event data requirements."""
        if not EventDataValidator.validate_base_event_data(data):
            return False

        required_fields = {"tool_name", "tool_input"}
        return all(field in data for field in required_fields)

    @staticmethod
    def validate_notification_event_data(data: EventData) -> bool:
        """Validate notification event data requirements."""
        if not EventDataValidator.validate_base_event_data(data):
            return False

        return "message" in data

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
        return "command" in tool_input and isinstance(tool_input["command"], str)

    @staticmethod
    def validate_file_input(tool_input: ToolInput) -> bool:
        """Validate file tool input."""
        return "file_path" in tool_input and isinstance(tool_input["file_path"], str)

    @staticmethod
    def validate_search_input(tool_input: ToolInput) -> bool:
        """Validate search tool input."""
        return "pattern" in tool_input and isinstance(tool_input["pattern"], str)

    @staticmethod
    def validate_web_input(tool_input: ToolInput) -> bool:
        """Validate web tool input."""
        return (
            "url" in tool_input
            and isinstance(tool_input["url"], str)
            and "prompt" in tool_input
            and isinstance(tool_input["prompt"], str)
        )


# Thread validation
def validate_thread_exists(
    thread_id: str,
    http_client: Any,
    channel_id: str,
    bot_token: str,
) -> bool:
    """Validate that a thread exists and is accessible.

    Args:
        thread_id: Discord thread ID to validate
        http_client: HTTP client instance for API calls
        channel_id: Discord channel ID
        bot_token: Discord bot token for authentication

    Returns:
        bool: True if thread exists and is accessible, False otherwise
    """
    try:
        headers = {"Authorization": f"Bot {bot_token}"}
        thread_data = http_client.request(
            "GET",
            f"https://discord.com/api/v10/channels/{thread_id}",
            headers=headers,
        )
        return bool(thread_data)
    except Exception:
        return False


# Export all public validators
__all__ = [
    # Validator classes
    'ConfigValidator', 'EventDataValidator', 'ToolInputValidator',
    # Type guards
    'is_tool_event_data', 'is_notification_event_data', 'is_stop_event_data',
    'is_bash_tool_input', 'is_file_tool_input', 'is_search_tool_input',
    'is_valid_event_type', 'is_bash_tool', 'is_file_tool', 'is_search_tool',
    'is_list_tool',
    # Thread validation
    'validate_thread_exists',
]