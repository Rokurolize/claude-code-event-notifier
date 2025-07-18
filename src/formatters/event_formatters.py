#!/usr/bin/env python3
"""Event-specific formatters for Discord Notifier.

This module provides formatting functions for different Claude Code event types,
creating Discord embeds with appropriate formatting for each event.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict, Union, cast

from src.core.constants import (
    EVENT_COLORS,
    TOOL_EMOJIS,
    DiscordColors,
    DiscordLimits,
    EventTypes,
    TruncationLimits,
)
from src.core.http_client import DiscordEmbed as BaseDiscordEmbed, DiscordMessage
from src.formatters.base import add_field, format_json_field, truncate_string
from src.utils.message_id_generator import UUIDMessageIDGenerator
from src.utils.markdown_exporter import generate_markdown_content
from src.utils.path_utils import extract_working_directory_from_transcript_path, get_project_name_from_path, format_cd_command
from src.utils.version_info import format_version_footer
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

if TYPE_CHECKING:
    from .tool_formatters import BashToolInput, FileOperationInput, SearchToolInput, TaskToolInput, WebFetchInput
    from .tool_formatters import ToolResponse as ToolFormatterResponse


# Enhanced Discord embed structure with tracking capabilities
class DiscordEmbed(BaseDiscordEmbed, total=False):
    """Enhanced Discord embed structure with unique ID and Markdown support."""

    # 新規追加フィールド
    message_id: str  # 一意ID
    markdown_content: str  # Markdown形式の内容
    raw_content: dict[str, str]  # 生の内容データ


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
    """Enhanced structure for subagent stop events with conversation tracking."""

    # 既存フィールド
    subagent_id: str
    result: str
    duration_seconds: int
    tools_used: int

    # 新規追加フィールド
    conversation_log: str  # 実際の発言内容
    response_content: str  # サブエージェントの回答
    interaction_history: list[str]  # 対話履歴
    message_id: str  # 一意ID
    task_description: str  # タスクの説明
    context_summary: str  # コンテキストの要約
    error_messages: list[str]  # エラーメッセージ（存在する場合）


# Type alias for configuration
Config = dict[str, str | int | bool]

# Type alias for tool response
ToolResponse = str | dict[str, str | int | float | bool | list[str]] | list[dict[str, str]]

# Union type for all event data
EventData = Union[ToolEventData, NotificationEventData, StopEventData, SubagentStopEventData]


def format_pre_tool_use(event_data: ToolEventData, session_id: str) -> DiscordEmbed:
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

    # Initialize embed with all required fields
    embed: DiscordEmbed = {
        "title": f"About to execute: {emoji} {tool_name}",
        "description": None,
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None,
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
        desc_parts.extend(format_task_pre_use(cast("TaskToolInput", tool_input)))
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
    return embed


def format_post_tool_use(event_data: ToolEventData, session_id: str) -> DiscordEmbed:
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

    # Initialize embed with all required fields
    embed: DiscordEmbed = {
        "title": f"Completed: {emoji} {tool_name}",
        "description": None,
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None,
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
    return embed


def format_notification(event_data: NotificationEventData, session_id: str) -> DiscordEmbed:
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

    return {
        "title": "📢 Notification",
        "description": "\n".join(desc_parts),
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None,
    }


def format_stop(event_data: StopEventData, session_id: str) -> DiscordEmbed:
    """Format Stop event with session details and working directory.

    Args:
        event_data: Event data containing stop information
        session_id: Session identifier

    Returns:
        Discord embed with formatted stop event including working directory
    """
    desc_parts: list[str] = []

    add_field(desc_parts, "Session ID", session_id, code=True)
    add_field(desc_parts, "Ended at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))

    # Enhanced transcript path handling with working directory extraction
    transcript_path = event_data.get("transcript_path", "")
    if transcript_path:
        # Extract working directory from transcript path
        working_dir = extract_working_directory_from_transcript_path(transcript_path)
        if working_dir:
            project_name = get_project_name_from_path(working_dir)
            cd_command = format_cd_command(working_dir)
            
            # Add project name for quick identification
            if project_name:
                add_field(desc_parts, "Project", project_name, code=True)
            
            # Add ready-to-use cd command
            add_field(desc_parts, "Working Directory", cd_command, code=True)
        
        # Keep original transcript path for reference
        add_field(desc_parts, "Transcript", transcript_path, code=True)

    # Add any session statistics if available
    for key in ["duration", "tools_used", "messages_exchanged"]:
        if key in event_data:
            label = key.replace("_", " ").title()
            add_field(desc_parts, label, str(event_data[key]))

    return {
        "title": "🏁 Session Ended",
        "description": "\n".join(desc_parts),
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None,
    }


def format_subagent_stop(event_data: SubagentStopEventData, session_id: str) -> DiscordEmbed:
    """Enhanced format SubagentStop event with conversation tracking.

    Args:
        event_data: Enhanced event data containing subagent stop information
        session_id: Session identifier (完全形で保持)

    Returns:
        Enhanced Discord embed with conversation content and unique ID
    """
    # 🔍 デバッグ: event_dataの全フィールドをログ出力
    import logging
    logger = logging.getLogger(__name__)

    logger.info(
        "SubagentStop event_data debug",
        extra={
            "event_data_keys": list(event_data.keys()),
            "event_data_full": event_data,
            "session_id": session_id,
            "ai_todo": "Debug SubagentStop event data for prompt separation analysis",
        },
    )

    # 1. 一意ID生成
    message_id_generator = UUIDMessageIDGenerator()
    message_id = message_id_generator.generate_message_id("SubagentStop", session_id)

    desc_parts: list[str] = []
    raw_content: dict[str, str] = {}

    # 2. 基本情報の追加
    add_field(desc_parts, "Message ID", message_id, code=True)
    add_field(desc_parts, "Session", session_id, code=True)  # 完全形で表示
    add_field(desc_parts, "Completed at", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"))

    # 3. transcript ファイルからサブエージェント情報を抽出
    transcript_path = event_data.get("transcript_path", "")
    if transcript_path:
        try:
            from ..utils.transcript_analyzer import TranscriptAnalyzer
            analyzer = TranscriptAnalyzer(logger)
            latest_response = analyzer.get_latest_subagent_response(transcript_path)
            
            if latest_response:
                # サブエージェント情報
                add_field(desc_parts, "Subagent ID", latest_response["subagent_id"])
                raw_content["subagent_id"] = latest_response["subagent_id"]
                
                # タスク情報
                if latest_response["task_description"]:
                    task_preview = truncate_string(latest_response["task_description"], TruncationLimits.FIELD_VALUE)
                    add_field(desc_parts, "Task", task_preview)
                    raw_content["task_description"] = latest_response["task_description"]
                
                # 発言内容の追跡（新機能）
                if latest_response["response_content"]:
                    response_preview = truncate_string(latest_response["response_content"], TruncationLimits.DESCRIPTION)
                    desc_parts.append(f"**Response:**\n{response_preview}")
                    raw_content["response_content"] = latest_response["response_content"]
                
                # 会話ログ
                if latest_response["conversation_log"]:
                    conversation_preview = truncate_string(latest_response["conversation_log"], TruncationLimits.DESCRIPTION)
                    desc_parts.append(f"**Conversation:**\n{conversation_preview}")
                    raw_content["conversation_log"] = latest_response["conversation_log"]
                
                # メトリクス情報
                if latest_response["duration_seconds"]:
                    add_field(desc_parts, "Duration", f"{latest_response['duration_seconds']:.2f} seconds")
                    raw_content["duration_seconds"] = str(latest_response["duration_seconds"])
                
                if latest_response["tools_used"]:
                    add_field(desc_parts, "Tools Used", str(latest_response["tools_used"]))
                    raw_content["tools_used"] = str(latest_response["tools_used"])
                
                logger.info(f"Successfully extracted subagent response from transcript: {latest_response['subagent_id']}")
            else:
                logger.warning(f"No subagent response found in transcript: {transcript_path}")
                
        except Exception as e:
            logger.error(f"Error analyzing transcript file {transcript_path}: {e}")
            # フォールバック: 基本情報のみ表示
            desc_parts.append("*Unable to extract subagent details from transcript*")

    # 4. フォールバック: 既存のフィールドがある場合は使用
    if "subagent_id" in event_data and not raw_content.get("subagent_id"):
        subagent_id = event_data.get("subagent_id", "unknown")
        add_field(desc_parts, "Subagent ID", subagent_id)
        raw_content["subagent_id"] = subagent_id

    if "conversation_log" in event_data and not raw_content.get("conversation_log"):
        conversation = event_data.get("conversation_log", "")
        conversation_preview = truncate_string(str(conversation), TruncationLimits.DESCRIPTION)
        desc_parts.append(f"**Conversation:**\n{conversation_preview}")
        raw_content["conversation_log"] = conversation

    if "response_content" in event_data and not raw_content.get("response_content"):
        response = event_data.get("response_content", "")
        response_preview = truncate_string(str(response), TruncationLimits.DESCRIPTION)
        desc_parts.append(f"**Response:**\n{response_preview}")
        raw_content["response_content"] = response

    # 5. タスク情報（新機能）
    if "task_description" in event_data:
        task = event_data.get("task_description", "")
        task_preview = truncate_string(str(task), TruncationLimits.FIELD_VALUE)
        add_field(desc_parts, "Task", task_preview)
        raw_content["task_description"] = task

    # 6. 結果情報（既存機能の改良）
    if "result" in event_data:
        result = event_data.get("result", "")
        result_summary = truncate_string(str(result), TruncationLimits.JSON_PREVIEW)
        desc_parts.append(f"**Result:**\n{result_summary}")
        raw_content["result"] = result

    # 7. メトリクス情報
    if "duration_seconds" in event_data:
        duration = event_data.get("duration_seconds", 0)
        add_field(desc_parts, "Duration", f"{duration} seconds")
        raw_content["duration_seconds"] = str(duration)

    if "tools_used" in event_data:
        tools = event_data.get("tools_used", 0)
        add_field(desc_parts, "Tools Used", str(tools))
        raw_content["tools_used"] = str(tools)

    # 8. エラー情報（新機能）
    if "error_messages" in event_data and event_data["error_messages"]:
        error_list = event_data["error_messages"]
        error_preview = truncate_string(str(error_list), TruncationLimits.FIELD_VALUE)
        desc_parts.append(f"**Errors:**\n{error_preview}")
        raw_content["errors"] = str(error_list)

    # 9. Markdown形式の内容生成
    markdown_content = generate_markdown_content(raw_content, message_id)

    return {
        "title": "🤖 Subagent Completed",
        "description": "\n".join(desc_parts),
        "color": None,
        "timestamp": None,
        "footer": {"text": f"ID: {message_id[:16]}..."},
        "fields": None,
        # 新規追加
        "message_id": message_id,
        "markdown_content": markdown_content,
        "raw_content": raw_content,
    }


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
    desc_parts: list[str] = []
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
        "fields": None,
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
    timestamp = datetime.now(UTC).isoformat()
    # Enhanced Session ID extraction with multiple fallback options
    session_id = event_data.get("session_id") or event_data.get("Session") or event_data.get("session") or "unknown"
    # Note: Don't truncate to 8 chars anymore - keep full session ID for better tracking

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

    # Enhanced footer with version information
    version_footer = format_version_footer()
    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type} | {version_footer}"}

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
