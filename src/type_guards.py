#!/usr/bin/env python3
"""Type guard functions for validating and narrowing types in the Discord notifier.

This module provides comprehensive type guard functions that can validate and narrow types
for the nested structures used throughout the Discord notifier system, including:
- Hook configurations
- Event data structures
- Tool inputs and responses
- Discord API structures
- Configuration objects

All type guards follow the TypeIs protocol and provide both runtime validation
and static type narrowing for improved type safety.
"""

import json
from typing import Any, TypedDict

# TypeIs is available in Python 3.13+
try:
    from typing import TypeIs
except ImportError:
    from typing import TypeIs

# Import Discord notifier types from reorganized modules
from src.core.constants import EventTypes as EventType
from src.core.constants import ToolNames as ToolName
from src.settings_types import (
    ClaudeSettings,
    HookConfig,
    HookEntry,
    HookEventType,
    HooksDict,
    NonToolHookConfig,
    ToolHookConfig,
)
from src.type_aliases import (
    DiscordEmbed,
    DiscordMessage,
)
from src.type_defs.discord import (
    DiscordFooter,
    DiscordThreadMessage,
)
from src.utils.astolfo_logger import AstolfoLogger

# Initialize logger for type guard debugging
logger = AstolfoLogger("type_guards")


# Define TypedDicts for event data structures
class BaseEventData(TypedDict):
    """Base structure for all events."""
    session_id: str
    transcript_path: str
    hook_event_name: str


class ToolEventDataBase(BaseEventData, total=False):
    """Base structure for tool events."""
    tool_name: str
    tool_input: dict[str, str | int | float | bool | list[str] | dict[str, str]]


class PreToolUseEventData(ToolEventDataBase):
    """PreToolUse event data."""


class PostToolUseEventData(ToolEventDataBase, total=False):
    """PostToolUse event data."""
    tool_response: str | dict[str, str | int | float | bool | list[str]] | list[dict[str, str]]
    exit_code: int
    duration_ms: int
    error: str | None


class NotificationEventData(BaseEventData, total=False):
    """Notification event data."""
    message: str
    level: str
    timestamp: str


class StopEventData(BaseEventData, total=False):
    """Stop event data."""
    reason: str
    duration_seconds: int
    tools_used: int
    errors_encountered: int


class SubagentStopEventData(BaseEventData, total=False):
    """Subagent stop event data."""
    subagent_id: str
    result: str
    duration_seconds: int
    tools_used: int


# Tool input TypedDicts
class BashToolInput(TypedDict, total=False):
    """Bash tool input structure."""
    command: str
    description: str
    timeout: int


class FileToolInput(TypedDict, total=False):
    """File tool input structure."""
    file_path: str
    content: str
    old_string: str
    new_string: str
    edits: list[dict[str, str]]
    limit: int
    offset: int


class SearchToolInput(TypedDict, total=False):
    """Search tool input structure."""
    pattern: str
    path: str
    glob: str
    type: str
    output_mode: str


class TaskToolInput(TypedDict, total=False):
    """Task tool input structure."""
    instructions: str
    parent: str


class WebToolInput(TypedDict, total=False):
    """Web tool input structure."""
    url: str
    prompt: str


# Tool response TypedDicts
class BashToolResponse(TypedDict, total=False):
    """Bash tool response structure."""
    stdout: str
    stderr: str
    exit_code: int
    output: str


class FileOperationResponse(TypedDict, total=False):
    """File operation response structure."""
    success: bool
    message: str
    content: str
    lines_written: int


class FileEditOperation(TypedDict):
    """File edit operation structure."""
    old_string: str
    new_string: str
    replace_all: bool | None


# Type aliases for unions
from typing import Union as UnionType

Config = dict[str, str | int | bool]
ToolResponse = UnionType[
    BashToolResponse,
    FileOperationResponse,
    str,
    list[dict[str, str]],
    dict[str, str | int | float | bool]
]
ToolInput = UnionType[
    BashToolInput,
    FileToolInput,
    SearchToolInput,
    TaskToolInput,
    WebToolInput,
    dict[str, str | int | float | bool]
]
EventData = UnionType[
    BaseEventData,
    PreToolUseEventData,
    PostToolUseEventData,
    NotificationEventData,
    StopEventData,
    SubagentStopEventData,
    dict[str, Any]
]

# =============================================================================
# Basic Type Guards
# =============================================================================


def is_non_empty_string(value: object) -> TypeIs[str]:
    """Check if value is a non-empty string."""
    result = isinstance(value, str) and len(value.strip()) > 0
    if not result:
        logger.debug(
            "is_non_empty_string check failed",
            context={
                "value_type": type(value).__name__,
                "value_repr": repr(value)[:100],  # Truncate for safety
                "is_string": isinstance(value, str),
                "is_empty": isinstance(value, str) and len(value.strip()) == 0 if isinstance(value, str) else None
            }
        )
    return result


def is_string_or_none(value: object) -> TypeIs[str | None]:
    """Check if value is a string or None."""
    return value is None or isinstance(value, str)


def is_boolean_or_none(value: object) -> TypeIs[bool | None]:
    """Check if value is a boolean or None."""
    return value is None or isinstance(value, bool)


def is_number_or_none(value: object) -> TypeIs[int | float | None]:
    """Check if value is a number or None."""
    return value is None or isinstance(value, (int, float))


def is_dict_with_str_keys(value: object) -> TypeIs[dict[str, object]]:
    """Check if value is a dictionary with string keys."""
    if not isinstance(value, dict):
        logger.debug(
            "is_dict_with_str_keys: not a dict",
            context={"value_type": type(value).__name__}
        )
        return False

    non_str_keys = [key for key in value if not isinstance(key, str)]
    if non_str_keys:
        logger.debug(
            "is_dict_with_str_keys: found non-string keys",
            context={
                "non_str_keys": [str(k) for k in non_str_keys[:5]],  # First 5 non-string keys
                "total_non_str": len(non_str_keys)
            }
        )
        return False

    return True


def is_list_of_dicts(value: object) -> TypeIs[list[dict[str, object]]]:
    """Check if value is a list of dictionaries."""
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def is_valid_snowflake(value: object) -> TypeIs[str]:
    """Check if value is a valid Discord snowflake ID.

    Discord snowflakes are 64-bit unsigned integers represented as strings.
    They should be numeric strings between 18-20 characters long.

    Args:
        value: Value to validate

    Returns:
        True if value is a valid snowflake format, False otherwise
    """
    if not isinstance(value, str):
        return False

    # Check if it's a numeric string
    if not value.isdigit():
        return False

    # Check length (Discord snowflakes are typically 18-20 characters)
    if len(value) < 17 or len(value) > 20:
        return False

    # Check if it's a valid integer
    try:
        int_value = int(value)
        # Discord snowflakes are 64-bit unsigned integers
        return 0 <= int_value <= (2**64 - 1)
    except ValueError:
        return False


# =============================================================================
# Hook Configuration Type Guards
# =============================================================================


def is_hook_entry(value: object) -> TypeIs[HookEntry]:
    """Check if value is a valid HookEntry."""
    return isinstance(value, dict) and value.get("type") == "command" and is_non_empty_string(value.get("command"))


def is_hook_entry_list(value: object) -> TypeIs[list[HookEntry]]:
    """Check if value is a list of valid HookEntry objects."""
    return isinstance(value, list) and all(is_hook_entry(entry) for entry in value)


def is_hook_config(value: object) -> TypeIs[HookConfig]:
    """Check if value is a valid HookConfig."""
    if not isinstance(value, dict):
        logger.debug(
            "is_hook_config: not a dict",
            context={"value_type": type(value).__name__}
        )
        return False

    # Must have a hooks list
    if "hooks" not in value:
        logger.debug("is_hook_config: missing 'hooks' key")
        return False

    if not is_hook_entry_list(value["hooks"]):
        logger.debug(
            "is_hook_config: invalid hooks list",
            context={"hooks_type": type(value["hooks"]).__name__}
        )
        return False

    # If matcher is present, it must be a string
    if "matcher" in value and not isinstance(value["matcher"], str):
        logger.debug(
            "is_hook_config: invalid matcher type",
            context={"matcher_type": type(value["matcher"]).__name__}
        )
        return False

    # No other keys should be present
    allowed_keys = {"hooks", "matcher"}
    extra_keys = [key for key in value if key not in allowed_keys]
    if extra_keys:
        logger.debug(
            "is_hook_config: unexpected keys",
            context={"extra_keys": extra_keys}
        )
        return False

    return True


def is_tool_hook_config(value: object) -> TypeIs[ToolHookConfig]:
    """Check if value is a valid ToolHookConfig (requires matcher)."""
    return is_hook_config(value) and "matcher" in value and isinstance(value["matcher"], str)


def is_non_tool_hook_config(value: object) -> TypeIs[NonToolHookConfig]:
    """Check if value is a valid NonToolHookConfig (no matcher)."""
    return is_hook_config(value) and "matcher" not in value


def is_hook_event_type(value: object) -> TypeIs[HookEventType]:
    """Check if value is a valid hook event type."""
    return value in [
        "PreToolUse",
        "PostToolUse",
        "Notification",
        "Stop",
        "SubagentStop",
    ]


def is_hooks_dict(value: object) -> TypeIs[HooksDict]:
    """Check if value is a valid HooksDict."""
    if not isinstance(value, dict):
        return False

    for event_type, hook_configs in value.items():
        if not is_hook_event_type(event_type):
            return False

        if not isinstance(hook_configs, list):
            return False

        if not _validate_hook_configs_for_event_type(hook_configs, event_type):
            return False

    return True


def _validate_hook_configs_for_event_type(hook_configs: list[object], event_type: str) -> bool:
    """Validate hook configurations for a specific event type."""
    for hook_config in hook_configs:
        if not is_hook_config(hook_config):
            return False

        # Validate matcher requirements based on event type
        if event_type in ["PreToolUse", "PostToolUse"]:
            # Tool events require matcher field
            if not is_tool_hook_config(hook_config):
                return False
        elif not is_non_tool_hook_config(hook_config):
            # Non-tool events should not have matcher field
            return False  # type: ignore[unreachable]

    return True


def is_claude_settings(value: object) -> TypeIs[ClaudeSettings]:
    """Check if value is a valid ClaudeSettings object."""
    if not isinstance(value, dict):
        return False

    # If hooks are present, they must be valid
    # Other fields are optional and can be any type
    return "hooks" not in value or is_hooks_dict(value["hooks"])


# =============================================================================
# Discord API Type Guards
# =============================================================================


def is_discord_footer(value: object) -> TypeIs[DiscordFooter]:
    """Check if value is a valid DiscordFooter."""
    return isinstance(value, dict) and is_non_empty_string(value.get("text"))


def is_discord_embed(value: object) -> TypeIs[DiscordEmbed]:
    """Check if value is a valid DiscordEmbed."""
    if not isinstance(value, dict):
        logger.debug(
            "is_discord_embed: not a dict",
            context={"value_type": type(value).__name__}
        )
        return False

    # Check optional fields with helper function
    result = _validate_discord_embed_fields(value)
    if not result:
        logger.debug(
            "is_discord_embed: field validation failed",
            context={"value_keys": list(value.keys())}
        )
    return result


def _validate_discord_embed_fields(value: dict[str, object]) -> bool:
    """Validate Discord embed fields."""
    # Check optional fields
    field_checks: list[tuple[str, Any]] = [
        ("title", lambda v: isinstance(v, str)),
        ("description", lambda v: isinstance(v, str)),
        ("color", lambda v: isinstance(v, int)),
        ("timestamp", lambda v: isinstance(v, str)),
        ("footer", lambda v: is_discord_footer(v)),
    ]

    for field_name, validator in field_checks:
        if field_name in value and not validator(value[field_name]):
            return False

    # No other keys should be present
    allowed_keys = {"title", "description", "color", "timestamp", "footer"}
    return all(key in allowed_keys for key in value)


def is_discord_embed_list(value: object) -> TypeIs[list[DiscordEmbed]]:
    """Check if value is a list of valid DiscordEmbed objects."""
    return isinstance(value, list) and all(is_discord_embed(embed) for embed in value)


def is_discord_message(value: object) -> TypeIs[DiscordMessage]:
    """Check if value is a valid DiscordMessage."""
    if not isinstance(value, dict):
        return False

    # Check optional fields
    if "embeds" in value and not is_discord_embed_list(value["embeds"]):
        return False

    if "content" in value and not isinstance(value["content"], str):
        return False

    # No other keys should be present
    allowed_keys = {"embeds", "content"}
    return all(key in allowed_keys for key in value)


def is_discord_thread_message(value: object) -> TypeIs[DiscordThreadMessage]:
    """Check if value is a valid DiscordThreadMessage."""
    if not isinstance(value, dict):
        return False

    # Check optional fields
    if "embeds" in value and not is_discord_embed_list(value["embeds"]):
        return False

    if "thread_name" in value and not isinstance(value["thread_name"], str):
        return False

    # No other keys should be present
    allowed_keys = {"embeds", "thread_name"}
    return all(key in allowed_keys for key in value)


# =============================================================================
# Configuration Type Guards
# =============================================================================


def is_config(value: object) -> TypeIs[Config]:
    """Check if value is a valid Config object."""
    if not isinstance(value, dict):
        return False

    # Check required fields with proper types
    required_fields: dict[str, Any] = {
        "webhook_url": is_string_or_none,
        "bot_token": is_string_or_none,
        "channel_id": is_string_or_none,
        "debug": lambda v: isinstance(v, bool),
        "use_threads": lambda v: isinstance(v, bool),
        "channel_type": lambda v: v in ["text", "forum"],
        "thread_prefix": lambda v: isinstance(v, str),
        "mention_user_id": is_string_or_none,
    }

    for field, validator in required_fields.items():
        if field not in value or not validator(value[field]):
            return False

    # No other keys should be present
    return all(key in required_fields for key in value)


# =============================================================================
# Tool Input Type Guards
# =============================================================================


def is_bash_tool_input(value: object) -> TypeIs[BashToolInput]:
    """Check if value is a valid BashToolInput."""
    if not isinstance(value, dict):
        return False

    # Check optional fields
    if "command" in value and not isinstance(value["command"], str):
        return False

    if "description" in value and not isinstance(value["description"], str):
        return False

    if "timeout" in value and not isinstance(value["timeout"], int):
        return False

    # No other keys should be present
    allowed_keys = {"command", "description", "timeout"}
    return all(key in allowed_keys for key in value)


def is_file_edit(value: object) -> TypeIs[FileEditOperation]:
    """Check if value is a valid FileEdit."""
    if not isinstance(value, dict):
        return False

    # Required fields
    if not is_non_empty_string(value.get("old_string")):
        return False

    if not is_non_empty_string(value.get("new_string")):
        return False

    # Optional field
    if "replace_all" in value and not isinstance(value["replace_all"], bool):
        return False

    # No other keys should be present
    allowed_keys = {"old_string", "new_string", "replace_all"}
    return all(key in allowed_keys for key in value)


def is_file_edit_list(value: object) -> TypeIs[list[FileEditOperation]]:
    """Check if value is a list of valid FileEdit objects."""
    return isinstance(value, list) and all(is_file_edit(edit) for edit in value)


def is_file_tool_input(value: object) -> TypeIs[FileToolInput]:
    """Check if value is a valid FileToolInput."""
    if not isinstance(value, dict):
        return False

    # Define field validators
    field_validators: dict[str, Any] = {
        "file_path": lambda v: isinstance(v, str),
        "old_string": lambda v: isinstance(v, str),
        "new_string": lambda v: isinstance(v, str),
        "edits": is_file_edit_list,
        "offset": is_number_or_none,
        "limit": is_number_or_none,
        "content": lambda v: isinstance(v, str),
    }

    # Check all fields are valid
    for field, validator in field_validators.items():
        if field in value and not validator(value[field]):
            return False

    # No other keys should be present
    allowed_keys = set(field_validators.keys())
    return all(key in allowed_keys for key in value)


def is_search_tool_input(value: object) -> TypeIs[SearchToolInput]:
    """Check if value is a valid SearchToolInput."""
    if not isinstance(value, dict):
        return False

    # Check optional fields
    if "pattern" in value and not isinstance(value["pattern"], str):
        return False

    if "path" in value and not isinstance(value["path"], str):
        return False

    if "glob" in value and not isinstance(value["glob"], str):
        return False

    if "type" in value and not isinstance(value["type"], str):
        return False

    if "output_mode" in value and not isinstance(value["output_mode"], str):
        return False

    # No other keys should be present
    allowed_keys = {"pattern", "path", "glob", "type", "output_mode"}
    return all(key in allowed_keys for key in value)


def is_task_tool_input(value: object) -> TypeIs[TaskToolInput]:
    """Check if value is a valid TaskToolInput."""
    if not isinstance(value, dict):
        return False

    # Check optional fields
    if "instructions" in value and not isinstance(value["instructions"], str):
        return False

    if "parent" in value and not isinstance(value["parent"], str):
        return False

    # No other keys should be present
    allowed_keys = {"instructions", "parent"}
    return all(key in allowed_keys for key in value)


def is_web_tool_input(value: object) -> TypeIs[WebToolInput]:
    """Check if value is a valid WebToolInput."""
    if not isinstance(value, dict):
        return False

    # Check optional fields
    if "url" in value and not isinstance(value["url"], str):
        return False

    if "prompt" in value and not isinstance(value["prompt"], str):
        return False

    # No other keys should be present
    allowed_keys = {"url", "prompt"}
    return all(key in allowed_keys for key in value)


def is_tool_input(value: object) -> TypeIs[ToolInput]:
    """Check if value is a valid ToolInput (union of all tool input types)."""
    return (
        is_bash_tool_input(value)
        or is_file_tool_input(value)
        or is_search_tool_input(value)
        or is_task_tool_input(value)
        or is_web_tool_input(value)
        or is_dict_with_str_keys(value)  # Fallback for unknown tool inputs
    )


# =============================================================================
# Tool Response Type Guards
# =============================================================================


def is_bash_tool_response(value: object) -> TypeIs[BashToolResponse]:
    """Check if value is a valid BashToolResponse."""
    if not isinstance(value, dict):
        return False

    # Check optional fields (all fields are optional in BashToolResponse)
    field_validators: dict[str, Any] = {
        "stdout": lambda v: isinstance(v, str),
        "stderr": lambda v: isinstance(v, str),
        "exit_code": lambda v: isinstance(v, int),
        "output": lambda v: isinstance(v, str),
    }

    for field, validator in field_validators.items():
        if field in value and not validator(value[field]):
            return False

    # No other keys should be present
    allowed_keys = set(field_validators.keys())
    return all(key in allowed_keys for key in value)


def is_file_operation_response(value: object) -> TypeIs[FileOperationResponse]:
    """Check if value is a valid FileOperationResponse."""
    if not isinstance(value, dict):
        return False

    # Check optional fields
    field_validators: dict[str, Any] = {
        "success": lambda v: isinstance(v, bool),
        "message": lambda v: isinstance(v, str),
        "content": lambda v: isinstance(v, str),
        "lines_written": lambda v: isinstance(v, int),
    }

    for field, validator in field_validators.items():
        if field in value and not validator(value[field]):
            return False

    # No other keys should be present
    allowed_keys = set(field_validators.keys())
    return all(key in allowed_keys for key in value)


def is_tool_response(value: object) -> TypeIs[ToolResponse]:
    """Check if value is a valid ToolResponse (union of all tool response types)."""
    return isinstance(value, (str, dict, list)) or is_bash_tool_response(value) or is_file_operation_response(value)


# =============================================================================
# Event Data Type Guards
# =============================================================================


def is_base_event_data(value: object) -> TypeIs[BaseEventData]:
    """Check if value is a valid BaseEventData."""
    if not isinstance(value, dict):
        return False

    # Check required fields
    required_fields: dict[str, Any] = {
        "session_id": lambda v: isinstance(v, str),
        "transcript_path": lambda v: isinstance(v, str),
        "hook_event_name": lambda v: isinstance(v, str),
    }

    return all(field in value and validator(value[field]) for field, validator in required_fields.items())


def is_pre_tool_use_event_data(value: object) -> TypeIs[PreToolUseEventData]:
    """Check if value is a valid PreToolUseEventData."""
    if not isinstance(value, dict):
        logger.debug(
            "is_pre_tool_use_event_data: not a dict",
            context={"value_type": type(value).__name__}
        )
        return False

    # Check base event data fields
    base_fields = ["session_id", "transcript_path", "hook_event_name"]
    missing_fields = [f for f in base_fields if f not in value]
    if missing_fields:
        logger.debug(
            "is_pre_tool_use_event_data: missing base fields",
            context={"missing_fields": missing_fields}
        )
        return False

    invalid_fields = [f for f in base_fields if f in value and not isinstance(value[f], str)]
    if invalid_fields:
        logger.debug(
            "is_pre_tool_use_event_data: invalid base field types",
            context={"invalid_fields": [f"{f}: {type(value[f]).__name__}" for f in invalid_fields]}
        )
        return False

    # Check additional required fields for tool events
    if "tool_name" not in value:
        logger.debug("is_pre_tool_use_event_data: missing 'tool_name'")
        return False

    if not isinstance(value["tool_name"], str):
        logger.debug(
            "is_pre_tool_use_event_data: invalid tool_name type",
            context={"tool_name_type": type(value["tool_name"]).__name__}
        )
        return False

    if "tool_input" not in value:
        logger.debug("is_pre_tool_use_event_data: missing 'tool_input'")
        return False

    if not isinstance(value["tool_input"], dict):
        logger.debug(
            "is_pre_tool_use_event_data: invalid tool_input type",
            context={"tool_input_type": type(value["tool_input"]).__name__}
        )
        return False

    return True


def is_post_tool_use_event_data(value: object) -> TypeIs[PostToolUseEventData]:
    """Check if value is a valid PostToolUseEventData."""
    if not isinstance(value, dict):
        return False

    # Check base event data fields
    if not all(
        field in value and isinstance(value[field], str)
        for field in ["session_id", "transcript_path", "hook_event_name"]
    ):
        return False

    # Check tool event fields
    if "tool_name" not in value or not isinstance(value["tool_name"], str):
        return False

    if "tool_input" not in value or not isinstance(value["tool_input"], dict):
        return False

    # Check additional required field
    # tool_response can be any type
    return "tool_response" in value


def is_notification_event_data(value: object) -> TypeIs[NotificationEventData]:
    """Check if value is a valid NotificationEventData."""
    if not isinstance(value, dict):
        return False

    # Check base event data fields
    if not all(
        field in value and isinstance(value[field], str)
        for field in ["session_id", "transcript_path", "hook_event_name"]
    ):
        return False

    # Check optional fields that are specific to notification events
    if "message" in value and not isinstance(value["message"], str):
        return False

    if "level" in value and not isinstance(value["level"], str):
        return False

    return not ("timestamp" in value and not isinstance(value["timestamp"], str))


def is_stop_event_data(value: object) -> TypeIs[StopEventData]:
    """Check if value is a valid StopEventData."""
    if not isinstance(value, dict):
        return False

    # Check base event data fields
    if not all(
        field in value and isinstance(value[field], str)
        for field in ["session_id", "transcript_path", "hook_event_name"]
    ):
        return False

    # Check optional fields specific to stop events
    if "reason" in value and not isinstance(value["reason"], str):
        return False

    if "duration_seconds" in value and not isinstance(value["duration_seconds"], int):
        return False

    if "tools_used" in value and not isinstance(value["tools_used"], int):
        return False

    return not ("errors_encountered" in value and not isinstance(value["errors_encountered"], int))


def is_subagent_stop_event_data(value: object) -> TypeIs[SubagentStopEventData]:
    """Check if value is a valid SubagentStopEventData."""
    if not isinstance(value, dict):
        return False

    # Check base event data fields (don't require stop event data)
    if not all(
        field in value and isinstance(value[field], str)
        for field in ["session_id", "transcript_path", "hook_event_name"]
    ):
        return False

    # Check optional fields specific to subagent stop events
    if "subagent_id" in value and not isinstance(value["subagent_id"], str):
        return False

    if "result" in value and not isinstance(value["result"], str):
        return False

    if "duration_seconds" in value and not isinstance(value["duration_seconds"], int):
        return False

    return not ("tools_used" in value and not isinstance(value["tools_used"], int))


def is_event_data(value: object) -> TypeIs[EventData]:
    """Check if value is a valid EventData (union of all event data types)."""
    return (
        is_pre_tool_use_event_data(value)
        or is_post_tool_use_event_data(value)
        or is_notification_event_data(value)
        or is_stop_event_data(value)
        or is_subagent_stop_event_data(value)
        or is_dict_with_str_keys(value)  # Fallback for unknown event data
    )


# =============================================================================
# Literal Type Guards
# =============================================================================


def is_event_type(value: object) -> TypeIs[EventType]:
    """Check if value is a valid EventType."""
    return value in [
        "PreToolUse",
        "PostToolUse",
        "Notification",
        "Stop",
        "SubagentStop",
    ]


def is_tool_name(value: object) -> TypeIs[ToolName]:
    """Check if value is a valid ToolName."""
    return value in [
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


# =============================================================================
# Utility Type Guards
# =============================================================================


def is_json_serializable(value: object) -> bool:
    """Check if value can be serialized to JSON."""
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return False
    else:
        return True


def is_valid_url(value: object) -> bool:
    """Check if value is a valid URL string."""
    if not isinstance(value, str):
        return False

    return value.startswith(("http://", "https://")) and len(value) > 10 and "." in value


def is_valid_discord_webhook_url(value: object) -> bool:
    """Check if value is a valid Discord webhook URL."""
    if not isinstance(value, str):
        return False

    return value.startswith("https://discord.com/api/webhooks/") and len(value.split("/")) >= 7


def is_valid_discord_user_id(value: object) -> bool:
    """Check if value is a valid Discord user ID."""
    if not isinstance(value, str):
        return False

    return (
        value.isdigit()
        and len(value) >= 17  # Discord IDs are typically 17-19 digits
        and len(value) <= 19
    )


# =============================================================================
# Validation Helper Functions
# =============================================================================


def validate_and_narrow_hook_config(value: object, event_type: str) -> ToolHookConfig | NonToolHookConfig:
    """Validate and narrow a hook configuration for a specific event type."""
    if not is_hook_config(value):
        raise TypeError(f"Invalid hook configuration: {value}")

    if event_type in ["PreToolUse", "PostToolUse"]:
        if not is_tool_hook_config(value):
            raise ValueError(f"Tool event {event_type} requires a matcher field")
        return value  # Already type narrowed by is_tool_hook_config
    if not is_non_tool_hook_config(value):
        raise ValueError(f"Non-tool event {event_type} should not have a matcher field")
    return value  # Already type narrowed by is_non_tool_hook_config


def validate_and_narrow_event_data(value: object, event_type: str) -> EventData:
    """Validate and narrow event data for a specific event type."""
    logger.debug(
        "validate_and_narrow_event_data",
        context={
            "event_type": event_type,
            "value_type": type(value).__name__
        }
    )

    if not is_event_data(value):
        logger.error(
            "validate_and_narrow_event_data: not valid event data",
            context={
                "event_type": event_type,
                "value_type": type(value).__name__,
                "value_repr": repr(value)[:200]
            }
        )
        raise TypeError(f"Invalid event data: {value}")

    if event_type == "PreToolUse":
        if not is_pre_tool_use_event_data(value):
            logger.error(
                "validate_and_narrow_event_data: invalid PreToolUse data",
                context={"value_keys": list(value.keys()) if isinstance(value, dict) else None}
            )
            raise ValueError(f"Invalid PreToolUse event data: {value}")
        return value  # Type narrowed by type guard
    if event_type == "PostToolUse":
        if not is_post_tool_use_event_data(value):
            logger.error(
                "validate_and_narrow_event_data: invalid PostToolUse data",
                context={"value_keys": list(value.keys()) if isinstance(value, dict) else None}
            )
            raise ValueError(f"Invalid PostToolUse event data: {value}")
        return value  # Type narrowed by type guard
    if event_type == "Notification":
        if not is_notification_event_data(value):
            logger.error(
                "validate_and_narrow_event_data: invalid Notification data",
                context={"value_keys": list(value.keys()) if isinstance(value, dict) else None}
            )
            raise ValueError(f"Invalid Notification event data: {value}")
        return value  # Type narrowed by type guard
    if event_type == "Stop":
        if not is_stop_event_data(value):
            logger.error(
                "validate_and_narrow_event_data: invalid Stop data",
                context={"value_keys": list(value.keys()) if isinstance(value, dict) else None}
            )
            raise ValueError(f"Invalid Stop event data: {value}")
        return value  # Type narrowed by type guard
    if event_type == "SubagentStop":
        if not is_subagent_stop_event_data(value):
            logger.error(
                "validate_and_narrow_event_data: invalid SubagentStop data",
                context={"value_keys": list(value.keys()) if isinstance(value, dict) else None}
            )
            raise ValueError(f"Invalid SubagentStop event data: {value}")
        return value  # Type narrowed by type guard
    # For unknown event types, return as generic dict
    if isinstance(value, dict):
        logger.warning(
            "validate_and_narrow_event_data: unknown event type",
            context={"event_type": event_type}
        )
        return value
    logger.error(  # type: ignore[unreachable]
        "validate_and_narrow_event_data: unknown event type with non-dict data",
        context={
            "event_type": event_type,
            "value_type": type(value).__name__
        }
    )
    raise ValueError(f"Unknown event type {event_type} with non-dict data: {value}")


def validate_and_narrow_tool_input(value: object, tool_name: str) -> ToolInput:
    """Validate and narrow tool input for a specific tool type."""
    if not is_tool_input(value):
        raise TypeError(f"Invalid tool input: {value}")

    if tool_name == "Bash":
        if not is_bash_tool_input(value):
            raise ValueError(f"Invalid Bash tool input: {value}")
        return value  # Type narrowed by type guard
    if tool_name in ["Read", "Write", "Edit", "MultiEdit"]:
        if not is_file_tool_input(value):
            raise ValueError(f"Invalid file tool input for {tool_name}: {value}")
        return value  # Type narrowed by type guard
    if tool_name in ["Glob", "Grep"]:
        if not is_search_tool_input(value):
            raise ValueError(f"Invalid search tool input for {tool_name}: {value}")
        return value  # Type narrowed by type guard
    if tool_name == "Task":
        if not is_task_tool_input(value):
            raise ValueError(f"Invalid Task tool input: {value}")
        return value  # Type narrowed by type guard
    if tool_name == "WebFetch":
        if not is_web_tool_input(value):
            raise ValueError(f"Invalid WebFetch tool input: {value}")
        return value  # Type narrowed by type guard
    # For unknown tool types, return as generic dict
    if isinstance(value, dict):
        return value
    raise ValueError(f"Unknown tool {tool_name} with non-dict input: {value}")


# =============================================================================
# Comprehensive Validation Functions
# =============================================================================


def validate_complete_settings(settings_data: object) -> ClaudeSettings:
    """Perform comprehensive validation of Claude settings and return typed object."""
    if not is_claude_settings(settings_data):
        raise TypeError("Invalid Claude settings structure")

    # Additional validation for hooks if present
    if isinstance(settings_data, dict) and "hooks" in settings_data:
        hooks = settings_data["hooks"]
        if isinstance(hooks, dict):
            for event_type, hook_configs in hooks.items():
                if isinstance(hook_configs, list):
                    for i, hook_config in enumerate(hook_configs):
                        try:
                            validate_and_narrow_hook_config(hook_config, event_type)
                        except (TypeError, ValueError) as e:
                            raise ValueError(f"Invalid hook config at {event_type}[{i}]: {e}") from e

    return settings_data  # Type already narrowed by is_claude_settings


def validate_complete_config(config_data: object) -> Config:
    """Perform comprehensive validation of Discord config and return typed object."""
    if not is_config(config_data):
        raise TypeError("Invalid Discord configuration structure")

    # Additional validation for Discord-specific fields
    config = config_data  # Type already narrowed by is_config

    if "webhook_url" in config and config["webhook_url"] and not is_valid_discord_webhook_url(config["webhook_url"]):
        raise ValueError("Invalid Discord webhook URL format")

    if "mention_user_id" in config and config["mention_user_id"] and not is_valid_discord_user_id(config["mention_user_id"]):
        raise ValueError("Invalid Discord user ID format")

    if ("webhook_url" not in config or not config["webhook_url"]) and \
       ("bot_token" not in config or not config["bot_token"] or \
        "channel_id" not in config or not config["channel_id"]):
        raise ValueError("Must provide either webhook URL or bot token + channel ID")

    return config


def validate_complete_discord_message(message_data: object) -> DiscordMessage:
    """Perform comprehensive validation of Discord message and return typed object."""
    if not is_discord_message(message_data):
        raise TypeError("Invalid Discord message structure")

    message = message_data  # Type already narrowed by is_discord_message

    # Additional validation for Discord API limits
    if "embeds" in message and isinstance(message["embeds"], list):
        if len(message["embeds"]) > 10:  # Discord limit
            raise ValueError("Discord message cannot have more than 10 embeds")

        for i, embed in enumerate(message["embeds"]):
            if isinstance(embed, dict):
                if "title" in embed and isinstance(embed["title"], str) and len(embed["title"]) > 256:
                    raise ValueError(f"Embed {i} title exceeds 256 characters")
                if "description" in embed and isinstance(embed["description"], str) and len(embed["description"]) > 4096:
                    raise ValueError(f"Embed {i} description exceeds 4096 characters")

    return message


# =============================================================================
# Type Guard Registration for Runtime Discovery
# =============================================================================

# Registry of all type guards for runtime discovery
TYPE_GUARDS: dict[str, type | object] = {
    # Basic types
    "non_empty_string": is_non_empty_string,
    "string_or_none": is_string_or_none,
    "boolean_or_none": is_boolean_or_none,
    "number_or_none": is_number_or_none,
    "dict_with_str_keys": is_dict_with_str_keys,
    "list_of_dicts": is_list_of_dicts,
    # Hook configuration types
    "hook_entry": is_hook_entry,
    "hook_entry_list": is_hook_entry_list,
    "hook_config": is_hook_config,
    "tool_hook_config": is_tool_hook_config,
    "non_tool_hook_config": is_non_tool_hook_config,
    "hook_event_type": is_hook_event_type,
    "hooks_dict": is_hooks_dict,
    "claude_settings": is_claude_settings,
    # Discord API types
    "discord_footer": is_discord_footer,
    "discord_embed": is_discord_embed,
    "discord_embed_list": is_discord_embed_list,
    "discord_message": is_discord_message,
    "discord_thread_message": is_discord_thread_message,
    # Configuration types
    "config": is_config,
    # Tool input types
    "bash_tool_input": is_bash_tool_input,
    "file_edit": is_file_edit,
    "file_edit_list": is_file_edit_list,
    "file_tool_input": is_file_tool_input,
    "search_tool_input": is_search_tool_input,
    "task_tool_input": is_task_tool_input,
    "web_tool_input": is_web_tool_input,
    "tool_input": is_tool_input,
    # Tool response types
    "bash_tool_response": is_bash_tool_response,
    "file_operation_response": is_file_operation_response,
    "tool_response": is_tool_response,
    # Event data types
    "base_event_data": is_base_event_data,
    "pre_tool_use_event_data": is_pre_tool_use_event_data,
    "post_tool_use_event_data": is_post_tool_use_event_data,
    "notification_event_data": is_notification_event_data,
    "stop_event_data": is_stop_event_data,
    "subagent_stop_event_data": is_subagent_stop_event_data,
    "event_data": is_event_data,
    # Literal types
    "event_type": is_event_type,
    "tool_name": is_tool_name,
}

# Validation functions registry
VALIDATORS = {
    "complete_settings": validate_complete_settings,
    "complete_config": validate_complete_config,
    "complete_discord_message": validate_complete_discord_message,
    "hook_config": validate_and_narrow_hook_config,
    "event_data": validate_and_narrow_event_data,
    "tool_input": validate_and_narrow_tool_input,
}


def get_type_guard(name: str) -> object:
    """Get a type guard function by name."""
    return TYPE_GUARDS.get(name)


def get_validator(name: str) -> object:
    """Get a validator function by name."""
    return VALIDATORS.get(name)


def list_type_guards() -> list[str]:
    """List all available type guard names."""
    return list(TYPE_GUARDS.keys())


def list_validators() -> list[str]:
    """List all available validator names."""
    return list(VALIDATORS.keys())
