"""Validators for Discord Notifier.

This module contains all validation logic including type guards,
configuration validators, and event data validators.
"""

from typing import TYPE_CHECKING, TypeGuard, cast

from src.utils.astolfo_logger import AstolfoLogger

# Try to import types from type_defs module first
try:
    from src.type_defs.base import BaseField
    from src.type_defs.config import Config
    from src.type_defs.events import EventData, NotificationEventData, StopEventDataBase, ToolEventDataBase
    from src.type_defs.tools import BashToolInput, FileToolInputBase, SearchToolInputBase, ToolInput, WebToolInput
except ImportError:
    # Fallback imports from discord_notifier if type_defs not available
    # Create WebToolInput type if not available
    from typing import TypedDict

    from discord_notifier import (  # type: ignore
        BashToolInput,
        Config,
        EventData,
        FileToolInputBase,
        NotificationEventData,
        SearchToolInputBase,
        StopEventDataBase,
        ToolEventDataBase,
        ToolInput,
    )
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

# Initialize AstolfoLogger for validation tracking
logger = AstolfoLogger(__name__)


# Type guard functions
def is_tool_event_data(data: EventData) -> TypeGuard[ToolEventDataBase]:
    """Check if event data is tool-related."""
    logger.debug("Type validation: is_tool_event_data", {
        "input_type": type(data).__name__,
        "has_tool_name": "tool_name" in data if isinstance(data, dict) else False,
        "data_keys": list(data.keys()) if isinstance(data, dict) else "not_dict"
    })
    result = "tool_name" in data
    logger.debug("Tool event validation result", {"is_tool_event": result})
    return result


def is_notification_event_data(
    data: EventData,
) -> TypeGuard[NotificationEventData]:
    """Check if event data is notification-related."""
    logger.debug("Type validation: is_notification_event_data", {
        "input_type": type(data).__name__,
        "has_message": "message" in data if isinstance(data, dict) else False,
        "data_keys": list(data.keys()) if isinstance(data, dict) else "not_dict"
    })
    result = "message" in data
    logger.debug("Notification event validation result", {"is_notification_event": result})
    return result


def is_stop_event_data(data: EventData) -> TypeGuard[StopEventDataBase]:
    """Check if event data is stop-related."""
    logger.debug("Type validation: is_stop_event_data", {
        "input_type": type(data).__name__,
        "has_hook_event_name": "hook_event_name" in data if isinstance(data, dict) else False,
        "data_keys": list(data.keys()) if isinstance(data, dict) else "not_dict"
    })
    result = "hook_event_name" in data
    logger.debug("Stop event validation result", {"is_stop_event": result})
    return result


def is_bash_tool_input(tool_input: ToolInput) -> TypeGuard[BashToolInput]:
    """Check if tool input is for Bash tool."""
    logger.debug("Tool input validation: bash", {
        "input_type": type(tool_input).__name__,
        "has_command": "command" in tool_input if isinstance(tool_input, dict) else False,
        "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
    })
    result = "command" in tool_input
    logger.debug("Bash tool input validation result", {"is_bash_input": result})
    return result


def is_file_tool_input(tool_input: ToolInput) -> TypeGuard[FileToolInputBase]:
    """Check if tool input is for file operations."""
    logger.debug("Tool input validation: file", {
        "input_type": type(tool_input).__name__,
        "has_file_path": "file_path" in tool_input if isinstance(tool_input, dict) else False,
        "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
    })
    result = "file_path" in tool_input
    logger.debug("File tool input validation result", {"is_file_input": result})
    return result


def is_search_tool_input(tool_input: ToolInput) -> TypeGuard[SearchToolInputBase]:
    """Check if tool input is for search operations."""
    logger.debug("Tool input validation: search", {
        "input_type": type(tool_input).__name__,
        "has_pattern": "pattern" in tool_input if isinstance(tool_input, dict) else False,
        "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
    })
    result = "pattern" in tool_input
    logger.debug("Search tool input validation result", {"is_search_input": result})
    return result


def is_web_tool_input(tool_input: ToolInput) -> TypeGuard[WebToolInput]:
    """Check if tool input is for web operations."""
    logger.debug("Tool input validation: web", {
        "input_type": type(tool_input).__name__,
        "has_url": "url" in tool_input if isinstance(tool_input, dict) else False,
        "has_prompt": "prompt" in tool_input if isinstance(tool_input, dict) else False,
        "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
    })
    result = "url" in tool_input and "prompt" in tool_input
    logger.debug("Web tool input validation result", {"is_web_input": result})
    return result


def is_valid_event_type(event_type: str) -> TypeGuard[str]:
    """Check if event type is valid."""
    valid_types = {e.value for e in EventTypes}
    logger.debug("Event type validation", {
        "event_type": event_type,
        "event_type_type": type(event_type).__name__,
        "valid_types": list(valid_types)
    })
    result = event_type in valid_types
    logger.debug("Event type validation result", {
        "is_valid_event_type": result,
        "provided_type": event_type
    })
    return result


def is_bash_tool(tool_name: str) -> bool:
    """Check if tool is Bash."""
    bash_value = ToolNames.BASH.value
    logger.debug("Tool name validation: bash", {
        "tool_name": tool_name,
        "expected_bash_value": bash_value
    })
    result = tool_name == bash_value
    logger.debug("Bash tool validation result", {"is_bash_tool": result})
    return result


def is_file_tool(tool_name: str) -> bool:
    """Check if tool is a file operation tool."""
    file_tools = {
        ToolNames.READ.value,
        ToolNames.WRITE.value,
        ToolNames.EDIT.value,
        ToolNames.MULTI_EDIT.value,
    }
    logger.debug("Tool name validation: file", {
        "tool_name": tool_name,
        "file_tool_names": list(file_tools)
    })
    result = tool_name in file_tools
    logger.debug("File tool validation result", {"is_file_tool": result})
    return result


def is_search_tool(tool_name: str) -> bool:
    """Check if tool is a search tool."""
    search_tools = {ToolNames.GLOB.value, ToolNames.GREP.value}
    logger.debug("Tool name validation: search", {
        "tool_name": tool_name,
        "search_tool_names": list(search_tools)
    })
    result = tool_name in search_tools
    logger.debug("Search tool validation result", {"is_search_tool": result})
    return result


def is_list_tool(tool_name: str) -> bool:
    """Check if tool returns list results."""
    list_tools = {ToolNames.GLOB.value, ToolNames.GREP.value, ToolNames.LS.value}
    logger.debug("Tool name validation: list", {
        "tool_name": tool_name,
        "list_tool_names": list(list_tools)
    })
    result = tool_name in list_tools
    logger.debug("List tool validation result", {"is_list_tool": result})
    return result


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
        logger.debug("Starting credential validation", {
            "config_keys": list(config.keys()) if isinstance(config, dict) else "not_dict"
        })

        has_webhook = bool(config.get("webhook_url"))
        has_bot_credentials = bool(config.get("bot_token") and config.get("channel_id"))

        logger.debug("Credential validation analysis", {
            "has_webhook": has_webhook,
            "has_bot_token": bool(config.get("bot_token")),
            "has_channel_id": bool(config.get("channel_id")),
            "has_bot_credentials": has_bot_credentials
        })

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

        logger.debug("Credential validation passed", {
            "authentication_method": "webhook" if has_webhook else "bot_token"
        })
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
        use_threads = config.get("use_threads", False)
        logger.debug("Thread configuration validation started", {
            "use_threads": use_threads,
            "config_keys": list(config.keys()) if isinstance(config, dict) else "not_dict"
        })

        if not use_threads:
            logger.debug("Threads disabled, validation passed")
            return True

        channel_type = cast("str", config.get("channel_type", "text"))
        logger.debug("Thread config analysis", {
            "channel_type": channel_type,
            "has_webhook_url": bool(config.get("webhook_url")),
            "has_bot_token": bool(config.get("bot_token")),
            "has_channel_id": bool(config.get("channel_id"))
        })

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
            logger.debug("Forum channel thread config validated")
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
            logger.debug("Text channel thread config validated")
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
        logger.debug("Mention configuration validation started", {
            "has_mention_user_id": mention_user_id is not None,
            "mention_user_id_length": len(mention_user_id) if mention_user_id else 0,
            "mention_user_id_type": type(mention_user_id).__name__ if mention_user_id else "None"
        })

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

            logger.debug("Mention configuration validated", {
                "mention_user_id_length": len(mention_user_id)
            })
            return True

        logger.debug("No mention configuration to validate")
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
        logger.debug("Starting comprehensive config validation")

        credentials_valid = ConfigValidator.validate_credentials(config)
        thread_config_valid = ConfigValidator.validate_thread_config(config)
        mention_config_valid = ConfigValidator.validate_mention_config(config)

        all_valid = credentials_valid and thread_config_valid and mention_config_valid

        logger.info("Config validation completed", {
            "credentials_valid": credentials_valid,
            "thread_config_valid": thread_config_valid,
            "mention_config_valid": mention_config_valid,
            "all_valid": all_valid
        })

        return all_valid


# Event data validation
class EventDataValidator:
    """Validator for EventData structures."""

    @staticmethod
    def validate_base_event_data(data: EventData) -> bool:
        """Validate base event data requirements."""
        logger.debug("Base event data validation started", {
            "data_type": type(data).__name__,
            "data_keys": list(data.keys()) if isinstance(data, dict) else "not_dict"
        })

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

        logger.debug("Base event data validation passed")
        return True

    @staticmethod
    def validate_tool_event_data(data: EventData) -> bool:
        """Validate tool event data requirements."""
        logger.debug("Tool event data validation started")

        if not EventDataValidator.validate_base_event_data(data):
            logger.debug("Tool event validation failed: base validation failed")
            return False

        required_fields = {"tool_name", "tool_input"}
        missing_fields = [field for field in required_fields if field not in data]

        logger.debug("Tool event specific validation", {
            "required_fields": list(required_fields),
            "missing_fields": missing_fields,
            "present_fields": [f for f in required_fields if f in data]
        })

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

        logger.debug("Tool event data validation passed")
        return True

    @staticmethod
    def validate_notification_event_data(data: EventData) -> bool:
        """Validate notification event data requirements."""
        logger.debug("Notification event data validation started")

        if not EventDataValidator.validate_base_event_data(data):
            logger.debug("Notification event validation failed: base validation failed")
            return False

        has_message = "message" in data
        logger.debug("Notification event specific validation", {
            "has_message": has_message
        })

        if not has_message:
            logger.error(
                "notification_event_data_validation_failed",
                context={
                    "reason": "Missing 'message' field",
                    "event_type": "notification"
                },
                ai_todo="Notification events require a 'message' field"
            )
            return False

        logger.debug("Notification event data validation passed")
        return True

    @staticmethod
    def validate_stop_event_data(data: EventData) -> bool:
        """Validate stop event data requirements."""
        logger.debug("Stop event data validation started")
        result = EventDataValidator.validate_base_event_data(data)
        logger.debug("Stop event data validation completed", {"result": result})
        return result


# Tool input validation
class ToolInputValidator:
    """Validator for ToolInput structures."""

    @staticmethod
    def validate_bash_input(tool_input: ToolInput) -> bool:
        """Validate Bash tool input."""
        logger.debug("Bash input validation started", {
            "input_type": type(tool_input).__name__,
            "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
        })

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
        logger.debug("Bash command type validation", {
            "command_type": type(command).__name__ if command is not None else "None",
            "command_length": len(command) if isinstance(command, str) else "not_string"
        })

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

        logger.debug("Bash input validation passed", {"command_length": len(command)})
        return True

    @staticmethod
    def validate_file_input(tool_input: ToolInput) -> bool:
        """Validate file tool input."""
        logger.debug("File input validation started", {
            "input_type": type(tool_input).__name__,
            "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
        })

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
        logger.debug("File path type validation", {
            "file_path_type": type(file_path).__name__ if file_path is not None else "None",
            "file_path_length": len(file_path) if isinstance(file_path, str) else "not_string"
        })

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

        logger.debug("File input validation passed", {"file_path_length": len(file_path)})
        return True

    @staticmethod
    def validate_search_input(tool_input: ToolInput) -> bool:
        """Validate search tool input."""
        logger.debug("Search input validation started", {
            "input_type": type(tool_input).__name__,
            "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
        })

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
        logger.debug("Search pattern type validation", {
            "pattern_type": type(pattern).__name__ if pattern is not None else "None",
            "pattern_length": len(pattern) if isinstance(pattern, str) else "not_string"
        })

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

        logger.debug("Search input validation passed", {"pattern_length": len(pattern)})
        return True

    @staticmethod
    def validate_web_input(tool_input: ToolInput) -> bool:
        """Validate web tool input."""
        logger.debug("Web input validation started", {
            "input_type": type(tool_input).__name__,
            "input_keys": list(tool_input.keys()) if isinstance(tool_input, dict) else "not_dict"
        })

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

        logger.debug("Web input field type validation", {
            "url_type": type(url).__name__ if url is not None else "None",
            "prompt_type": type(prompt).__name__ if prompt is not None else "None",
            "url_length": len(url) if isinstance(url, str) else "not_string",
            "prompt_length": len(prompt) if isinstance(prompt, str) else "not_string"
        })

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

        logger.debug("Web input validation passed", {
            "url_length": len(url),
            "prompt_length": len(prompt)
        })
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
    import time
    start_time = time.time()

    logger.debug("Thread validation started", {
        "thread_id": thread_id,
        "channel_id": channel_id,
        "has_bot_token": bool(bot_token)
    })

    try:
        thread_data = http_client.get_thread_details(thread_id, bot_token)
        elapsed_time = time.time() - start_time

        logger.debug("Thread details API call completed", {
            "elapsed_time_ms": round(elapsed_time * 1000, 2),
            "thread_data_received": thread_data is not None
        })

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

        logger.debug("Thread validation successful", {
            "thread_id": thread_id,
            "validation_time_ms": round((time.time() - start_time) * 1000, 2)
        })
        return True
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.exception(
            "thread_validation_error",
            exception=e,
            context={
                "thread_id": thread_id,
                "reason": "Exception during thread validation",
                "elapsed_time_ms": round(elapsed_time * 1000, 2)
            },
            ai_todo="Check Discord API connection and bot permissions"
        )
        return False


# Export all public validators
__all__ = [
    # Validator classes
    "ConfigValidator",
    "EventDataValidator",
    "ToolInputValidator",
    "is_bash_tool",
    "is_bash_tool_input",
    "is_file_tool",
    "is_file_tool_input",
    "is_list_tool",
    "is_notification_event_data",
    "is_search_tool",
    "is_search_tool_input",
    "is_stop_event_data",
    # Type guards
    "is_tool_event_data",
    "is_valid_event_type",
    "is_web_tool_input",
    # Thread validation
    "validate_thread_exists",
]
