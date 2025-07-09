#!/usr/bin/env python3
"""Event-specific formatters for Discord Notifier.

This module provides formatting functions for different Claude Code event types,
creating Discord embeds with appropriate formatting for each event.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from src.core.constants import (
    EVENT_COLORS,
    TOOL_EMOJIS,
    DiscordColors,
    DiscordLimits,
    EventTypes,
    TruncationLimits,
)
from src.core.http_client import DiscordEmbed, DiscordMessage
from src.formatters.base import add_field, format_json_field, truncate_string
from src.formatters.tool_formatters import (
    format_bash_post_use,
    format_bash_pre_use,
    format_file_operation_pre_use,
    format_read_operation_post_use,
    format_search_tool_pre_use,
    format_task_post_use,
    format_task_pre_use,
    format_unknown_tool_post_use,
    format_unknown_tool_pre_use,
    format_web_fetch_post_use,
    format_web_fetch_pre_use,
    format_write_operation_post_use,
)
from src.utils.validation import (
    is_bash_tool,
    is_file_tool,
    is_list_tool,
    is_search_tool,
    is_valid_event_type,
)

# Type alias for configuration
Config = dict[str, Any]

# Type alias for tool response
ToolResponse = dict[str, Any] | str | list[Any]


def format_pre_tool_use(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PreToolUse event with detailed information.

    Args:
        event_data: Event data containing tool information
        session_id: Session identifier

    Returns:
        Discord embed with formatted pre-tool-use information
    """
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"About to execute: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts: list[str] = []
    add_field(desc_parts, "Session", session_id, code=True)

    # Dispatch to tool-specific formatter
    if is_bash_tool(tool_name):
        desc_parts.extend(format_bash_pre_use(tool_input))
    elif is_file_tool(tool_name):
        desc_parts.extend(format_file_operation_pre_use(tool_name, tool_input))
    elif is_search_tool(tool_name):
        desc_parts.extend(format_search_tool_pre_use(tool_name, tool_input))
    elif tool_name == "Task":
        desc_parts.extend(format_task_pre_use(tool_input))
    elif tool_name == "WebFetch":
        desc_parts.extend(format_web_fetch_pre_use(tool_input))
    else:
        desc_parts.extend(format_unknown_tool_pre_use(tool_input))

    # Add timestamp
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    add_field(desc_parts, "Time", timestamp)

    embed["description"] = "\n".join(desc_parts)
    return embed


def format_post_tool_use(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PostToolUse event with execution results.

    Args:
        event_data: Event data containing tool results
        session_id: Session identifier

    Returns:
        Discord embed with formatted post-tool-use information
    """
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    tool_response = event_data.get("tool_response", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"Completed: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts: list[str] = []
    add_field(desc_parts, "Session", session_id, code=True)

    # Dispatch to tool-specific formatter
    if is_bash_tool(tool_name):
        desc_parts.extend(format_bash_post_use(tool_input, tool_response))
    elif tool_name == "Read" or is_list_tool(tool_name):
        desc_parts.extend(format_read_operation_post_use(tool_name, tool_input, tool_response))
    elif is_file_tool(tool_name):
        desc_parts.extend(format_write_operation_post_use(tool_input, tool_response))
    elif tool_name == "Task":
        desc_parts.extend(format_task_post_use(tool_input, tool_response))
    elif tool_name == "WebFetch":
        desc_parts.extend(format_web_fetch_post_use(tool_input, tool_response))
    else:
        desc_parts.extend(format_unknown_tool_post_use(tool_response))

    # Add execution time
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    add_field(desc_parts, "Completed at", timestamp)

    embed["description"] = "\n".join(desc_parts)
    return embed


def format_notification(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Notification event with full details.

    Args:
        event_data: Event data containing notification information
        session_id: Session identifier

    Returns:
        Discord embed with formatted notification
    """
    message = event_data.get("message", "System notification")

    desc_parts: list[str] = [
        f"**Message:** {message}",
        f"**Session:** `{session_id}`",
        f"**Time:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Add any additional data from the event
    extra_keys: list[str] = [
        k for k in event_data if k not in ["message", "session_id", "transcript_path", "hook_event_name"]
    ]

    if extra_keys:
        for key in extra_keys:
            value = event_data[key]
            if isinstance(value, (str, int, float, bool)):
                add_field(desc_parts, key.title(), str(value))
            else:
                # For complex types, show as JSON
                desc_parts.append(format_json_field(value, key.title(), TruncationLimits.PROMPT_PREVIEW))

    return {"title": "📢 Notification", "description": "\n".join(desc_parts)}


def format_stop(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Stop event with session details.

    Args:
        event_data: Event data containing stop information
        session_id: Session identifier

    Returns:
        Discord embed with formatted stop event
    """
    desc_parts: list[str] = []

    add_field(desc_parts, "Session ID", session_id, code=True)
    add_field(desc_parts, "Ended at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))

    # Add transcript path if available
    transcript_path = event_data.get("transcript_path", "")
    if transcript_path:
        add_field(desc_parts, "Transcript", transcript_path, code=True)

    # Add any session statistics if available
    for key in ["duration", "tools_used", "messages_exchanged"]:
        if key in event_data:
            label = key.replace("_", " ").title()
            add_field(desc_parts, label, str(event_data[key]))

    return {"title": "🏁 Session Ended", "description": "\n".join(desc_parts)}


def format_subagent_stop(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format SubagentStop event with task results.

    Args:
        event_data: Event data containing subagent stop information
        session_id: Session identifier

    Returns:
        Discord embed with formatted subagent stop event
    """
    desc_parts: list[str] = []

    add_field(desc_parts, "Session", session_id, code=True)
    add_field(desc_parts, "Completed at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))

    # Add task description if available
    task_desc = event_data.get("task_description", "")
    if task_desc:
        add_field(desc_parts, "Task", task_desc)

    # Add result summary if available
    result = event_data.get("result", "")
    if result:
        if isinstance(result, str):
            result_summary = truncate_string(result, TruncationLimits.JSON_PREVIEW)
            desc_parts.append(f"**Result:**\n{result_summary}")
        else:
            desc_parts.append(format_json_field(result, "Result", TruncationLimits.JSON_PREVIEW))

    # Add execution stats if available
    for key in ["execution_time", "tools_used", "status"]:
        if key in event_data:
            label = key.replace("_", " ").title()
            add_field(desc_parts, label, str(event_data[key]))

    return {"title": "🤖 Subagent Completed", "description": "\n".join(desc_parts)}


def format_default_impl(event_type: str, event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format unknown event types.

    Args:
        event_type: Type of the event
        event_data: Event data
        session_id: Session identifier

    Returns:
        Discord embed with generic event formatting
    """
    desc_parts: list[str] = []
    desc_parts.append(f"**Session:** `{session_id}`")
    desc_parts.append(f"**Event Type:** {event_type}")

    # Show event data if available
    if event_data:
        desc_parts.append("\n**Event Data:**")
        desc_parts.append(format_json_field(event_data, "", TruncationLimits.JSON_PREVIEW))

    return {"title": f"⚡ {event_type}", "description": "\n".join(desc_parts)}


def format_default(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Wrapper for format_default_impl that matches the formatter signature.

    Args:
        event_data: Event data
        session_id: Session identifier

    Returns:
        Discord embed with generic event formatting
    """
    return format_default_impl("Unknown", event_data, session_id)


def format_event(
    event_type: str,
    event_data: dict[str, Any],
    formatter_func: Callable[[dict[str, Any], str], DiscordEmbed],
    config: Config,
) -> DiscordMessage:
    """Format Claude Code event into Discord embed with length limits.

    Args:
        event_type: Type of the event
        event_data: Event data to format
        formatter_func: Function to use for formatting
        config: Configuration dictionary

    Returns:
        Discord message with formatted embed
    """
    timestamp = datetime.now(UTC).isoformat()
    session_id = event_data.get("session_id", "unknown")[:8]

    # Format the event using the appropriate formatter
    embed = formatter_func(event_data, session_id)

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
