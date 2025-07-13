#!/usr/bin/env python3
"""Validation utilities for Discord Notifier.

This module provides validation functions and type guards for
ensuring data integrity throughout the system.

Note: This module contains some deprecated functions that are kept
for backward compatibility. Use src.type_guards module for new code.
"""

from typing import TypeGuard

from src.core.constants import EventType, EventTypes, ToolNames
from src.utils.astolfo_logger import AstolfoLogger

# Initialize logger for this module
logger = AstolfoLogger(__name__)


# Type aliases from main file
class BaseEventData:
    """Base event data structure."""


class ToolEventDataBase:
    """Tool event data base structure."""


class NotificationEventData:
    """Notification event data structure."""


class StopEventDataBase:
    """Stop event data base structure."""


class BashToolInput:
    """Bash tool input structure."""


class FileToolInputBase:
    """File tool input base structure."""


class SearchToolInputBase:
    """Search tool input base structure."""


# Event type validation
# Note: @warnings.deprecated is Python 3.13+ feature
# For now, just document the deprecation
def is_valid_event_type(event_type: str) -> TypeGuard[EventType]:
    """Check if event type is valid.

    .. deprecated:: 2.0.0
        Use :func:`src.type_guards.is_valid_event_type` instead.

    Args:
        event_type: Event type string to validate

    Returns:
        True if event type is valid, False otherwise
    """
    result = event_type in {e.value for e in EventTypes}
    logger.debug(
        "Validated event type",
        extra={"event_type": event_type, "is_valid": result, "function": "is_valid_event_type"}
    )
    return result


# Tool type helpers
def is_bash_tool(tool_name: str) -> bool:
    """Check if tool is Bash.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is Bash, False otherwise
    """
    result = tool_name == ToolNames.BASH.value
    logger.debug(
        "Checked if tool is Bash",
        extra={"tool_name": tool_name, "is_bash": result}
    )
    return result


def is_file_tool(tool_name: str) -> bool:
    """Check if tool is a file operation tool.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is a file operation tool, False otherwise
    """
    result = tool_name in {
        ToolNames.READ.value,
        ToolNames.WRITE.value,
        ToolNames.EDIT.value,
        ToolNames.MULTI_EDIT.value,
    }
    logger.debug(
        "Checked if tool is file operation",
        extra={"tool_name": tool_name, "is_file_tool": result}
    )
    return result


def is_write_tool(tool_name: str) -> bool:
    """Check if tool performs write operations.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool performs write operations, False otherwise
    """
    result = tool_name in {
        ToolNames.WRITE.value,
        ToolNames.EDIT.value,
        ToolNames.MULTI_EDIT.value,
    }
    logger.debug(
        "Checked if tool performs write operations",
        extra={"tool_name": tool_name, "is_write_tool": result}
    )
    return result


def is_search_tool(tool_name: str) -> bool:
    """Check if tool is a search tool.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is a search tool, False otherwise
    """
    result = tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value}
    logger.debug(
        "Checked if tool is search tool",
        extra={"tool_name": tool_name, "is_search_tool": result}
    )
    return result


def is_list_tool(tool_name: str) -> bool:
    """Check if tool returns list results.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool returns list results, False otherwise
    """
    result = tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value, ToolNames.LS.value}
    logger.debug(
        "Checked if tool returns list results",
        extra={"tool_name": tool_name, "is_list_tool": result}
    )
    return result


# Type guard functions
def is_tool_event_data(data: dict[str, object]) -> TypeGuard[ToolEventDataBase]:
    """Check if event data is tool-related.

    Args:
        data: Event data to check

    Returns:
        True if data is tool-related, False otherwise
    """
    result = "tool_name" in data
    logger.debug(
        "Checked if event data is tool-related",
        extra={"has_tool_name": result, "data_keys": list(data.keys())}
    )
    return result


def is_notification_event_data(
    data: dict[str, object],
) -> TypeGuard[NotificationEventData]:
    """Check if event data is notification-related.

    Args:
        data: Event data to check

    Returns:
        True if data is notification-related, False otherwise
    """
    result = "message" in data
    logger.debug(
        "Checked if event data is notification-related",
        extra={"has_message": result, "data_keys": list(data.keys())}
    )
    return result


def is_stop_event_data(data: dict[str, object]) -> TypeGuard[StopEventDataBase]:
    """Check if event data is stop-related.

    Args:
        data: Event data to check

    Returns:
        True if data is stop-related, False otherwise
    """
    result = "hook_event_name" in data
    logger.debug(
        "Checked if event data is stop-related",
        extra={"has_hook_event_name": result, "data_keys": list(data.keys())}
    )
    return result


def is_bash_tool_input(tool_input: dict[str, object]) -> TypeGuard[BashToolInput]:
    """Check if tool input is for Bash tool.

    Args:
        tool_input: Tool input to check

    Returns:
        True if input is for Bash tool, False otherwise
    """
    result = "command" in tool_input
    logger.debug(
        "Checked if tool input is for Bash",
        extra={"has_command": result, "input_keys": list(tool_input.keys())}
    )
    return result


def is_file_tool_input(tool_input: dict[str, object]) -> TypeGuard[FileToolInputBase]:
    """Check if tool input is for file operations.

    Args:
        tool_input: Tool input to check

    Returns:
        True if input is for file operations, False otherwise
    """
    result = "file_path" in tool_input
    logger.debug(
        "Checked if tool input is for file operations",
        extra={"has_file_path": result, "input_keys": list(tool_input.keys())}
    )
    return result


def is_search_tool_input(tool_input: dict[str, object]) -> TypeGuard[SearchToolInputBase]:
    """Check if tool input is for search operations.

    Args:
        tool_input: Tool input to check

    Returns:
        True if input is for search operations, False otherwise
    """
    result = "pattern" in tool_input
    logger.debug(
        "Checked if tool input is for search operations",
        extra={"has_pattern": result, "input_keys": list(tool_input.keys())}
    )
    return result


# Validation classes
class EventDataValidator:
    """Validator for EventData structures."""

    @staticmethod
    def validate_base_event_data(data: dict[str, object]) -> bool:
        """Validate base event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        required_fields = {"session_id", "hook_event_name"}
        result = all(field in data for field in required_fields)
        missing_fields = required_fields - set(data.keys())

        logger.debug(
            "Validated base event data",
            extra={
                "is_valid": result,
                "required_fields": list(required_fields),
                "missing_fields": list(missing_fields),
                "data_keys": list(data.keys())
            }
        )
        return result

    @staticmethod
    def validate_tool_event_data(data: dict[str, object]) -> bool:
        """Validate tool event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        if not EventDataValidator.validate_base_event_data(data):
            logger.debug("Tool event data validation failed: base validation failed")
            return False

        required_fields = {"tool_name", "tool_input"}
        result = all(field in data for field in required_fields)
        missing_fields = required_fields - set(data.keys())

        logger.debug(
            "Validated tool event data",
            extra={
                "is_valid": result,
                "required_fields": list(required_fields),
                "missing_fields": list(missing_fields),
                "tool_name": str(data.get("tool_name", ""))
            }
        )
        return result

    @staticmethod
    def validate_notification_event_data(data: dict[str, object]) -> bool:
        """Validate notification event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        if not EventDataValidator.validate_base_event_data(data):
            logger.debug("Notification event data validation failed: base validation failed")
            return False

        result = "message" in data
        logger.debug(
            "Validated notification event data",
            extra={
                "is_valid": result,
                "has_message": result,
                "message_length": len(str(data.get("message", ""))) if "message" in data else 0
            }
        )
        return result

    @staticmethod
    def validate_stop_event_data(data: dict[str, object]) -> bool:
        """Validate stop event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        result = EventDataValidator.validate_base_event_data(data)
        logger.debug(
            "Validated stop event data",
            extra={
                "is_valid": result,
                "session_id": str(data.get("session_id", ""))
            }
        )
        return result


class ToolInputValidator:
    """Validator for ToolInput structures."""

    @staticmethod
    def validate_bash_input(tool_input: dict[str, object]) -> bool:
        """Validate Bash tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        has_command = "command" in tool_input
        is_string = isinstance(tool_input.get("command"), str) if has_command else False
        result = has_command and is_string

        logger.debug(
            "Validated Bash tool input",
            extra={
                "is_valid": result,
                "has_command": has_command,
                "is_string": is_string,
                "command_length": len(str(tool_input.get("command", ""))) if has_command else 0
            }
        )
        return result

    @staticmethod
    def validate_file_input(tool_input: dict[str, object]) -> bool:
        """Validate file tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        has_file_path = "file_path" in tool_input
        is_string = isinstance(tool_input.get("file_path"), str) if has_file_path else False
        result = has_file_path and is_string

        logger.debug(
            "Validated file tool input",
            extra={
                "is_valid": result,
                "has_file_path": has_file_path,
                "is_string": is_string,
                "file_path": str(tool_input.get("file_path", "")) if has_file_path else None
            }
        )
        return result

    @staticmethod
    def validate_search_input(tool_input: dict[str, object]) -> bool:
        """Validate search tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        has_pattern = "pattern" in tool_input
        is_string = isinstance(tool_input.get("pattern"), str) if has_pattern else False
        result = has_pattern and is_string

        logger.debug(
            "Validated search tool input",
            extra={
                "is_valid": result,
                "has_pattern": has_pattern,
                "is_string": is_string,
                "pattern_length": len(str(tool_input.get("pattern", ""))) if has_pattern else 0
            }
        )
        return result

    @staticmethod
    def validate_web_input(tool_input: dict[str, object]) -> bool:
        """Validate web tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        has_url = "url" in tool_input
        url_is_string = isinstance(tool_input.get("url"), str) if has_url else False
        has_prompt = "prompt" in tool_input
        prompt_is_string = isinstance(tool_input.get("prompt"), str) if has_prompt else False

        result = has_url and url_is_string and has_prompt and prompt_is_string

        logger.debug(
            "Validated web tool input",
            extra={
                "is_valid": result,
                "has_url": has_url,
                "url_is_string": url_is_string,
                "has_prompt": has_prompt,
                "prompt_is_string": prompt_is_string,
                "url": str(tool_input.get("url", "")) if has_url else None
            }
        )
        return result
