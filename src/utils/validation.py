#!/usr/bin/env python3
"""Validation utilities for Discord Notifier.

This module provides validation functions and type guards for
ensuring data integrity throughout the system.

Note: This module contains some deprecated functions that are kept
for backward compatibility. Use src.type_guards module for new code.
"""

from typing import Any, TypeGuard

from src.core.constants import EventType, EventTypes, ToolNames


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
    return event_type in {e.value for e in EventTypes}


# Tool type helpers
def is_bash_tool(tool_name: str) -> bool:
    """Check if tool is Bash.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is Bash, False otherwise
    """
    return tool_name == ToolNames.BASH.value


def is_file_tool(tool_name: str) -> bool:
    """Check if tool is a file operation tool.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is a file operation tool, False otherwise
    """
    return tool_name in {
        ToolNames.READ.value,
        ToolNames.WRITE.value,
        ToolNames.EDIT.value,
        ToolNames.MULTI_EDIT.value,
    }


def is_write_tool(tool_name: str) -> bool:
    """Check if tool performs write operations.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool performs write operations, False otherwise
    """
    return tool_name in {
        ToolNames.WRITE.value,
        ToolNames.EDIT.value,
        ToolNames.MULTI_EDIT.value,
    }


def is_search_tool(tool_name: str) -> bool:
    """Check if tool is a search tool.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool is a search tool, False otherwise
    """
    return tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value}


def is_list_tool(tool_name: str) -> bool:
    """Check if tool returns list results.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool returns list results, False otherwise
    """
    return tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value, ToolNames.LS.value}


# Type guard functions
def is_tool_event_data(data: dict[str, Any]) -> TypeGuard[ToolEventDataBase]:
    """Check if event data is tool-related.

    Args:
        data: Event data to check

    Returns:
        True if data is tool-related, False otherwise
    """
    return "tool_name" in data


def is_notification_event_data(
    data: dict[str, Any],
) -> TypeGuard[NotificationEventData]:
    """Check if event data is notification-related.

    Args:
        data: Event data to check

    Returns:
        True if data is notification-related, False otherwise
    """
    return "message" in data


def is_stop_event_data(data: dict[str, Any]) -> TypeGuard[StopEventDataBase]:
    """Check if event data is stop-related.

    Args:
        data: Event data to check

    Returns:
        True if data is stop-related, False otherwise
    """
    return "hook_event_name" in data


def is_bash_tool_input(tool_input: dict[str, Any]) -> TypeGuard[BashToolInput]:
    """Check if tool input is for Bash tool.

    Args:
        tool_input: Tool input to check

    Returns:
        True if input is for Bash tool, False otherwise
    """
    return "command" in tool_input


def is_file_tool_input(tool_input: dict[str, Any]) -> TypeGuard[FileToolInputBase]:
    """Check if tool input is for file operations.

    Args:
        tool_input: Tool input to check

    Returns:
        True if input is for file operations, False otherwise
    """
    return "file_path" in tool_input


def is_search_tool_input(tool_input: dict[str, Any]) -> TypeGuard[SearchToolInputBase]:
    """Check if tool input is for search operations.

    Args:
        tool_input: Tool input to check

    Returns:
        True if input is for search operations, False otherwise
    """
    return "pattern" in tool_input


# Validation classes
class EventDataValidator:
    """Validator for EventData structures."""

    @staticmethod
    def validate_base_event_data(data: dict[str, Any]) -> bool:
        """Validate base event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        required_fields = {"session_id", "hook_event_name"}
        return all(field in data for field in required_fields)

    @staticmethod
    def validate_tool_event_data(data: dict[str, Any]) -> bool:
        """Validate tool event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        if not EventDataValidator.validate_base_event_data(data):
            return False

        required_fields = {"tool_name", "tool_input"}
        return all(field in data for field in required_fields)

    @staticmethod
    def validate_notification_event_data(data: dict[str, Any]) -> bool:
        """Validate notification event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        if not EventDataValidator.validate_base_event_data(data):
            return False

        return "message" in data

    @staticmethod
    def validate_stop_event_data(data: dict[str, Any]) -> bool:
        """Validate stop event data requirements.

        Args:
            data: Event data to validate

        Returns:
            True if data is valid, False otherwise
        """
        return EventDataValidator.validate_base_event_data(data)


class ToolInputValidator:
    """Validator for ToolInput structures."""

    @staticmethod
    def validate_bash_input(tool_input: dict[str, Any]) -> bool:
        """Validate Bash tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        return "command" in tool_input and isinstance(tool_input["command"], str)

    @staticmethod
    def validate_file_input(tool_input: dict[str, Any]) -> bool:
        """Validate file tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        return "file_path" in tool_input and isinstance(tool_input["file_path"], str)

    @staticmethod
    def validate_search_input(tool_input: dict[str, Any]) -> bool:
        """Validate search tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        return "pattern" in tool_input and isinstance(tool_input["pattern"], str)

    @staticmethod
    def validate_web_input(tool_input: dict[str, Any]) -> bool:
        """Validate web tool input.

        Args:
            tool_input: Tool input to validate

        Returns:
            True if input is valid, False otherwise
        """
        return (
            "url" in tool_input
            and isinstance(tool_input["url"], str)
            and "prompt" in tool_input
            and isinstance(tool_input["prompt"], str)
        )
