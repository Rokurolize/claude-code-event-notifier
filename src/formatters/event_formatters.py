#!/usr/bin/env python3
"""Event-specific formatters for Discord Notifier.

This module provides formatting functions for different Claude Code event types,
creating Discord embeds with appropriate formatting for each event.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict, Union, cast

from src.utils.astolfo_logger import AstolfoLogger
from src.core.constants import (
    EVENT_COLORS,
    TOOL_EMOJIS,
    DiscordColors,
    DiscordLimits,
    EventTypes,
    TruncationLimits,
)
from src.core.http_client import DiscordEmbed, DiscordMessage
from src.formatters.base import add_field, format_json_field, split_long_text, truncate_string
from src.formatters.embed_utils import create_embed_with_fields
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
from src.utils.transcript_reader import get_full_task_prompt, get_subagent_messages
from src.utils.validation import (
    is_bash_tool,
    is_file_tool,
    is_list_tool,
    is_search_tool,
    is_valid_event_type,
)

if TYPE_CHECKING:
    from .tool_formatters import BashToolInput, FileOperationInput, SearchToolInput, TaskToolInput, WebFetchInput
    from .tool_formatters import ToolResponse as ToolFormatterResponse


# Type definitions for event data structures
class ToolEventData(TypedDict, total=False):
    """Common structure for tool-related events."""

    tool_name: str
    tool_input: dict[str, str | int | float | bool | list[str] | dict[str, str]]
    tool_response: str | dict[str, str | int | float | bool | list[str]] | list[dict[str, str]]
    exit_code: int
    duration_ms: int
    error: str | None


class NotificationEventData(TypedDict, total=False):
    """Structure for notification events."""

    message: str
    level: str
    timestamp: str


class StopEventData(TypedDict, total=False):
    """Structure for stop events."""

    reason: str
    duration_seconds: int
    tools_used: int
    errors_encountered: int


class SubagentStopEventData(TypedDict, total=False):
    """Structure for subagent stop events."""

    subagent_id: str
    result: str
    duration_seconds: int
    tools_used: int


# Type alias for configuration
Config = dict[str, str | int | bool]

# Type alias for tool response
ToolResponse = str | dict[str, str | int | float | bool | list[str]] | list[dict[str, str]]

# Union type for all event data
EventData = Union[ToolEventData, NotificationEventData, StopEventData, SubagentStopEventData]

# Type for subagent message
class SubagentMessage(TypedDict):
    """Structure for subagent messages from transcript."""
    timestamp: str
    type: str
    role: str
    content: str | None


def format_pre_tool_use(event_data: ToolEventData, session_id: str) -> DiscordEmbed:
    """Format PreToolUse event with detailed information.

    Args:
        event_data: Event data containing tool information
        session_id: Session identifier (truncated for display)

    Returns:
        Discord embed with formatted pre-tool-use information
    """
    logger = AstolfoLogger(__name__)
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")
    
    logger.info(
        "Formatting PreToolUse event",
        event_type="PreToolUse",
        tool_name=tool_name,
        session_id=session_id,
        has_tool_input=bool(tool_input)
    )

    # Get full session ID for transcript lookup
    full_session_id = str(event_data.get("session_id", ""))

    # Initialize embed with all required fields
    embed: DiscordEmbed = {
        "title": f"About to execute: {emoji} {tool_name}",
        "description": None,
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None
    }

    # Build detailed description
    desc_parts: list[str] = []
    add_field(desc_parts, "Session", session_id, code=True)

    # Dispatch to tool-specific formatter
    # Import types locally to avoid circular imports

    if is_bash_tool(tool_name):
        desc_parts.extend(format_bash_pre_use(cast("BashToolInput", tool_input)))
    elif is_file_tool(tool_name):
        desc_parts.extend(format_file_operation_pre_use(tool_name, cast("FileOperationInput", tool_input)))
    elif is_search_tool(tool_name):
        desc_parts.extend(format_search_tool_pre_use(tool_name, cast("SearchToolInput", tool_input)))
    elif tool_name == "Task":
        # For Task tool, handle prompt specially to use full description space
        task_input_typed = cast("TaskToolInput", tool_input)
        task_desc = str(task_input_typed.get("description", ""))
        task_prompt = str(task_input_typed.get("prompt", ""))
        
        if task_desc:
            add_field(desc_parts, "Task", task_desc)
            
        # Try to get full prompt from transcript if available
        transcript_path_raw = event_data.get("transcript_path")
        if transcript_path_raw and isinstance(transcript_path_raw, str):
            full_prompt = get_full_task_prompt(transcript_path_raw, full_session_id)
            if full_prompt:
                task_prompt = full_prompt
                
        # Add prompt to description if it exists
        if task_prompt:
            # Separate the prompt with a clear header
            desc_parts.append("\n**Prompt:**")
            desc_parts.append(task_prompt)
    elif tool_name == "WebFetch":
        desc_parts.extend(format_web_fetch_pre_use(cast("WebFetchInput", tool_input)))
    else:
        # For unknown tools, pass a simplified dict
        simple_input = {k: v for k, v in tool_input.items() if isinstance(v, (str, int, float, bool))}
        desc_parts.extend(format_unknown_tool_pre_use(simple_input))

    # Add timestamp
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    add_field(desc_parts, "Time", timestamp)

    embed["description"] = "\n".join(desc_parts)
    
    logger.debug(
        "PreToolUse embed created",
        tool_name=tool_name,
        description_length=len(embed["description"]) if embed["description"] else 0,
        session_id=session_id
    )
    
    return embed


def format_post_tool_use(event_data: ToolEventData, session_id: str) -> DiscordEmbed:
    """Format PostToolUse event with execution results.

    Args:
        event_data: Event data containing tool results
        session_id: Session identifier

    Returns:
        Discord embed with formatted post-tool-use information
    """
    logger = AstolfoLogger(__name__)
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    tool_response = event_data.get("tool_response", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")
    
    logger.info(
        "Formatting PostToolUse event",
        event_type="PostToolUse",
        tool_name=tool_name,
        session_id=session_id,
        has_response=bool(tool_response),
        exit_code=event_data.get("exit_code", -1)
    )

    # Initialize embed with all required fields
    embed: DiscordEmbed = {
        "title": f"Completed: {emoji} {tool_name}",
        "description": None,
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None
    }

    # Build detailed description
    desc_parts: list[str] = []
    add_field(desc_parts, "Session", session_id, code=True)

    # Dispatch to tool-specific formatter
    # Import types locally to avoid circular imports

    if is_bash_tool(tool_name):
        desc_parts.extend(
            format_bash_post_use(
                cast("BashToolInput", tool_input),
                cast("ToolFormatterResponse", tool_response),
            )
        )
    elif tool_name == "Read" or is_list_tool(tool_name):
        desc_parts.extend(
            format_read_operation_post_use(
                tool_name,
                cast("FileOperationInput", tool_input),
                cast("ToolFormatterResponse", tool_response),
            )
        )
    elif is_file_tool(tool_name):
        desc_parts.extend(
            format_write_operation_post_use(
                cast("FileOperationInput", tool_input),
                cast("ToolFormatterResponse", tool_response),
            )
        )
    elif tool_name == "Task":
        desc_parts.extend(
            format_task_post_use(
                cast("TaskToolInput", tool_input),
                cast("ToolFormatterResponse", tool_response),
            )
        )
    elif tool_name == "WebFetch":
        desc_parts.extend(
            format_web_fetch_post_use(
                cast("WebFetchInput", tool_input),
                cast("ToolFormatterResponse", tool_response),
            )
        )
    else:
        desc_parts.extend(format_unknown_tool_post_use(cast("ToolFormatterResponse", tool_response)))

    # Add execution time
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    add_field(desc_parts, "Completed at", timestamp)

    embed["description"] = "\n".join(desc_parts)
    
    logger.debug(
        "PostToolUse embed created",
        tool_name=tool_name,
        description_length=len(embed["description"]) if embed["description"] else 0,
        session_id=session_id
    )
    
    return embed


def format_notification(event_data: NotificationEventData | dict[str, object], session_id: str) -> DiscordEmbed:
    """Format Notification event with full details.

    Args:
        event_data: Event data containing notification information
        session_id: Session identifier

    Returns:
        Discord embed with formatted notification
    """
    logger = AstolfoLogger(__name__)
    message = event_data.get("message", "System notification")
    
    logger.info(
        "Formatting Notification event",
        event_type="Notification",
        session_id=session_id,
        message_preview=str(message)[:100]
    )

    desc_parts: list[str] = [
        f"**Message:** {message}",
        f"**Session:** `{session_id}`",
        f"**Time:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Add any additional data from the event
    if isinstance(event_data, dict):
        extra_keys: list[str] = [
            k for k in event_data if k not in ["message", "session_id", "transcript_path", "hook_event_name"]
        ]

        if extra_keys:
            for key in extra_keys:
                if key in ["message", "level", "timestamp"]:
                    value = event_data.get(key, "")
                    if isinstance(value, (str, int, float, bool)):
                        add_field(desc_parts, key.title(), str(value))
                else:
                    # For other keys, try to get value safely
                    value = event_data.get(key)
                    if value is not None:
                        if isinstance(value, (str, int, float, bool)):
                            add_field(desc_parts, key.title(), str(value))
                        else:
                            # For complex types, show as JSON
                            desc_parts.append(format_json_field(value, key.title(), TruncationLimits.PROMPT_PREVIEW))

    return {
        "title": "📢 Notification",
        "description": "\n".join(desc_parts),
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None
    }


def format_stop(event_data: StopEventData | dict[str, object], session_id: str) -> DiscordEmbed:
    """Format Stop event with session details.

    Args:
        event_data: Event data containing stop information
        session_id: Session identifier

    Returns:
        Discord embed with formatted stop event
    """
    logger = AstolfoLogger(__name__)
    desc_parts: list[str] = []
    
    logger.info(
        "Formatting Stop event",
        event_type="Stop",
        session_id=session_id,
        has_transcript_path="transcript_path" in event_data
    )

    add_field(desc_parts, "Session ID", session_id, code=True)
    add_field(desc_parts, "Ended at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))

    # Add transcript path if available
    transcript_path_raw = event_data.get("transcript_path", "")
    if transcript_path_raw and isinstance(transcript_path_raw, str):
        add_field(desc_parts, "Transcript", transcript_path_raw, code=True)

    # Add any session statistics if available
    if isinstance(event_data, dict):
        for key in ["duration", "tools_used", "messages_exchanged"]:
            if key in event_data:
                value = event_data.get(key)
                if value is not None:
                    label = key.replace("_", " ").title()
                    add_field(desc_parts, label, str(value))

    return {
        "title": "🏁 Session Ended",
        "description": "\n".join(desc_parts),
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None
    }


def format_subagent_stop(event_data: SubagentStopEventData, session_id: str) -> DiscordEmbed:
    """Format SubagentStop event with task results and message history.

    Args:
        event_data: Event data containing subagent stop information
        session_id: Session identifier (truncated for display)

    Returns:
        Discord embed with formatted subagent stop event
    """
    logger = AstolfoLogger(__name__)
    desc_parts: list[str] = []
    fields_content: list[tuple[str, str]] = []
    
    logger.info(
        "Formatting SubagentStop event",
        event_type="SubagentStop",
        session_id=session_id,
        subagent_id=event_data.get("subagent_id", "unknown")
    )

    # Get full session ID for transcript lookup
    full_session_id = str(event_data.get("session_id", ""))

    add_field(desc_parts, "Session", session_id, code=True)
    add_field(desc_parts, "Completed at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))

    # Add subagent details
    if "subagent_id" in event_data:
        subagent_id = event_data.get("subagent_id", "unknown")
        add_field(desc_parts, "Subagent ID", subagent_id)

    # Add result
    if "result" in event_data:
        result = event_data.get("result", "")
        result_summary = truncate_string(str(result), TruncationLimits.JSON_PREVIEW)
        desc_parts.append(f"**Result:**\n{result_summary}")

    # Add metrics if available
    if "duration_seconds" in event_data:
        duration = event_data.get("duration_seconds", 0)
        add_field(desc_parts, "Duration", f"{duration} seconds")

    if "tools_used" in event_data:
        tools = event_data.get("tools_used", 0)
        add_field(desc_parts, "Tools Used", str(tools))

    # Try to get subagent messages from transcript
    transcript_path_raw = event_data.get("transcript_path")
    if transcript_path_raw and isinstance(transcript_path_raw, str):
        subagent_msgs = get_subagent_messages(transcript_path_raw, full_session_id, limit=50)
        if subagent_msgs:
            # Add messages as separate fields for better readability
            for i, msg in enumerate(subagent_msgs):
                # Extract content safely
                content = msg.get("content")
                if content is not None and isinstance(content, str):
                    # Each message becomes a field
                    field_name = f"Message {i+1}"
                    fields_content.append((field_name, content))

    # Create embed with fields
    description = "\n".join(desc_parts)

    embed = create_embed_with_fields(
        title="🤖 Subagent Completed",
        description=description,
        fields_content=fields_content,
        color=None,
        timestamp=None,
        footer_text=None
    )
    
    logger.debug(
        "SubagentStop embed created",
        session_id=session_id,
        field_count=len(fields_content),
        has_messages=len(fields_content) > 0
    )
    
    return embed


def format_default_impl(
    event_type: str, event_data: dict[str, str | int | float | bool], session_id: str
) -> DiscordEmbed:
    """Format unknown event types.

    Args:
        event_type: Type of the event
        event_data: Event data
        session_id: Session identifier

    Returns:
        Discord embed with generic event formatting
    """
    logger = AstolfoLogger(__name__)
    desc_parts: list[str] = []
    
    logger.warning(
        "Formatting unknown event type",
        event_type=event_type,
        session_id=session_id,
        data_keys=list(event_data.keys()) if event_data else []
    )
    desc_parts.append(f"**Session:** `{session_id}`")
    desc_parts.append(f"**Event Type:** {event_type}")

    # Show event data if available
    if event_data:
        desc_parts.append("\n**Event Data:**")
        desc_parts.append(format_json_field(event_data, "", TruncationLimits.JSON_PREVIEW))

    return {
        "title": f"⚡ {event_type}",
        "description": "\n".join(desc_parts),
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None
    }


def format_default(event_data: dict[str, str | int | float | bool], session_id: str) -> DiscordEmbed:
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
    event_data: EventData,
    formatter_func: Callable[[EventData, str], DiscordEmbed],
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
    logger = AstolfoLogger(__name__)
    timestamp = datetime.now(UTC).isoformat()
    session_id_raw = event_data.get("session_id", "unknown")
    session_id = str(session_id_raw)[:8] if session_id_raw else "unknown"
    
    logger.info(
        "Formatting event",
        event_type=event_type,
        session_id=session_id,
        formatter=formatter_func.__name__
    )

    # Format the event using the appropriate formatter
    embed = formatter_func(event_data, session_id)

    # Enforce Discord's length limits
    title = embed.get("title")
    if title is not None and len(title) > DiscordLimits.MAX_TITLE_LENGTH:
        embed["title"] = truncate_string(title, DiscordLimits.MAX_TITLE_LENGTH)

    description = embed.get("description")
    if description is not None and len(description) > DiscordLimits.MAX_DESCRIPTION_LENGTH:
        embed["description"] = truncate_string(description, DiscordLimits.MAX_DESCRIPTION_LENGTH)

    # Add common fields
    embed["timestamp"] = timestamp

    # Get color for event type
    if is_valid_event_type(event_type):
        embed["color"] = EVENT_COLORS.get(event_type, DiscordColors.DEFAULT)
    else:
        embed["color"] = DiscordColors.DEFAULT

    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type}"}

    # Create message with embeds
    message: DiscordMessage = {"embeds": [embed], "content": None}

    # Add user mention for Notification and Stop events if configured
    if event_type in [
        EventTypes.NOTIFICATION.value,
        EventTypes.STOP.value,
    ] and config.get("mention_user_id"):
        # Extract appropriate message based on event type
        if event_type == EventTypes.NOTIFICATION.value:
            display_message = str(event_data.get("message", "System notification"))
        else:  # Stop event
            display_message = "Session ended"
        # Include both mention and message for better Windows notification visibility
        message["content"] = f"<@{config['mention_user_id']}> {display_message}"
        
        logger.debug(
            "Added user mention to message",
            event_type=event_type,
            user_id=config["mention_user_id"]
        )

    logger.debug(
        "Event formatting complete",
        event_type=event_type,
        session_id=session_id,
        has_mention=message["content"] is not None,
        embed_title=embed.get("title", "")
    )

    return message
