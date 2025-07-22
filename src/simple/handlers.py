#!/usr/bin/env python3
"""Simple event handlers for Discord Event Notifier.

All event handlers in one beautiful, simple file.
"""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from event_types import Config, DiscordMessage, EventData, HandlerFunction

from datetime import UTC

from discord_client import create_thread, send_to_thread
from task_tracker import TaskTracker
from transcript_reader import read_subagent_messages
from version import VERSION_STRING

from utils import escape_discord_markdown

# Setup logger
logger = logging.getLogger(__name__)

# Python 3.14+ required - pure standard library

# Pre-compiled regex pattern for better performance
_MARKDOWN_PATTERN = re.compile(r"[*_`~|>#\-=\[\](){}]")


# =============================================================================
# Event Handlers - Simple, beautiful functions
# =============================================================================


def handle_pretooluse(data: EventData, config: Config) -> DiscordMessage | None:
    """Handle PreToolUse events."""
    tool_name = data.get("tool_name", "Unknown")

    # Skip if tool is disabled
    if not should_process_tool(tool_name, config):
        return None

    session_id = data.get("session_id", "unknown")
    tool_input = data.get("tool_input", {})

    # Track Task tool starts
    task_id = None
    if tool_name == "Task":
        task_id = TaskTracker.track_task_start(session_id, tool_name, tool_input)
        logger.debug(f"Tracked Task start with ID: {task_id}")

    # Format tool input
    description = format_tool_input(tool_name, tool_input)

    # Get current working directory
    try:
        cwd = Path.cwd()
        cwd_str = str(cwd)
        project_name = escape_discord_markdown(cwd.name)
    except OSError:
        cwd_str = "Unknown"
        project_name = "Unknown"

    tool_name_escaped = escape_discord_markdown(tool_name)

    # Enhanced content formatting for important tools using Discord native markdown
    if tool_name == "Task":
        description = tool_input.get("description", "AI task execution")
        prompt = tool_input.get("prompt", "")
        # Use Discord native markdown for better readability
        # Get first meaningful line for preview, but use native formatting
        prompt_lines = prompt.split("\n")
        prompt_preview = prompt_lines[0][:200] + "..." if len(prompt_lines[0]) > 200 else prompt_lines[0]
        content = (
            f"[{project_name}] Starting: **{tool_name_escaped}**\n**Description:** {description}\n*{prompt_preview}*"
        )

        # Create thread for Task execution if enabled
        if config.get("thread_for_task") and config.get("bot_token") and config.get("channel_id") and task_id:
            from datetime import datetime

            thread_name = f"Task: {description[:50]} - {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            thread_id = create_thread(config["channel_id"], thread_name, config["bot_token"])

            if thread_id:
                logger.debug(f"Created thread {thread_id} for task {task_id}")
                TaskTracker.update_task_thread(session_id, task_id, thread_id)

                # Send initial message to thread
                thread_message = {
                    "content": f"## 🚀 Task Started\n\n**Description**: {description}\n\n**Prompt**:\n```\n{prompt[:1500]}\n```"
                }
                send_to_thread(thread_id, thread_message, config["bot_token"])

                # Update main message to include thread link
                content += f"\n\n💬 **Thread**: <#{thread_id}>"

    elif tool_name == "exit_plan_mode":
        plan = tool_input.get("plan", "")
        # Use Discord native markdown for plan preview
        plan_lines = plan.split("\n")
        plan_preview = plan_lines[0][:200] + "..." if len(plan_lines[0]) > 200 else plan_lines[0]
        content = f"[{project_name}] Starting: **{tool_name_escaped}**\n**Plan:** *{plan_preview}*"
    else:
        content = f"[{project_name}] About to execute: {tool_name_escaped}"

    return {
        "content": content,
        "embeds": [
            {
                "title": f"🔵 Starting: {tool_name_escaped}",
                "description": description,
                "color": 0x3498DB,  # Blue
                "footer": {"text": f"Session: {session_id} | Event: PreToolUse | {VERSION_STRING}"},
                "fields": [{"name": "Cwd", "value": escape_discord_markdown(cwd_str), "inline": False}],
            }
        ],
    }


def handle_posttooluse(data: EventData, config: Config) -> DiscordMessage | None:
    """Handle PostToolUse events."""
    tool_name = data.get("tool_name", "Unknown")

    # Skip if tool is disabled
    if not should_process_tool(tool_name, config):
        return None

    session_id = data.get("session_id", "unknown")
    tool_response = data.get("tool_response", {})
    tool_input = data.get("tool_input", {})

    # Track Task tool responses with content-based matching
    task_id = None
    if tool_name == "Task":
        # Use content-based matching for better parallel task handling
        task_id = TaskTracker.track_task_response_by_content(session_id, tool_name, tool_input, tool_response)
        if task_id:
            logger.debug(f"Tracked Task response with ID: {task_id} using content-based matching")
        else:
            logger.warning(f"Failed to track Task response for session {session_id}")
            # Fallback to time-based matching if content matching fails
            task_id = TaskTracker.track_task_response(session_id, tool_name, tool_response)
            if task_id:
                logger.debug(f"Tracked Task response with ID: {task_id} using fallback time-based matching")

    # Format tool response
    description = format_tool_response(tool_name, tool_response)

    # Get current working directory
    try:
        cwd = Path.cwd()
        cwd_str = str(cwd)
        project_name = escape_discord_markdown(cwd.name)
    except OSError:
        cwd_str = "Unknown"
        project_name = "Unknown"

    tool_name_escaped = escape_discord_markdown(tool_name)

    # Enhanced content formatting for important tools completion using Discord native markdown
    if tool_name == "Task":
        # For Task completion, show a brief result preview with native markdown
        if tool_response.get("error"):
            content = f"[{project_name}] **Task Failed:** {tool_name_escaped}\n❌ *Execution error occurred*"
        else:
            content = f"[{project_name}] **Task Completed:** {tool_name_escaped}\n✅ *Successfully executed*"

        # Post result to thread if available
        if task_id and config.get("thread_for_task") and config.get("bot_token"):
            task_info = TaskTracker.get_task_by_id(session_id, task_id)
            if task_info and task_info.get("thread_id"):
                thread_id = task_info["thread_id"]

                # Extract response content
                response_text = "No response content"
                if isinstance(tool_response, dict) and "content" in tool_response:
                    content_list = tool_response.get("content", [])
                    text_parts = [
                        item.get("text", "")
                        for item in content_list
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    response_text = "\n".join(text_parts) if text_parts else "No text content"

                # Format execution time
                duration_text = "Unknown"
                if "totalDurationMs" in tool_response:
                    duration_ms = tool_response["totalDurationMs"]
                    duration_text = f"{duration_ms / 1000:.1f}s"

                # Send result to thread
                thread_message = {
                    "content": f"## ✅ Task Completed\n\n**Duration**: {duration_text}\n\n**Response**:\n```\n{response_text[:1500]}\n```"
                }
                if send_to_thread(thread_id, thread_message, config["bot_token"]):
                    logger.debug(f"Posted Task result to thread {thread_id}")
                    content += f"\n\n💬 **Result posted to thread**: <#{thread_id}>"

    elif tool_name == "exit_plan_mode":
        # For exit_plan_mode completion with native markdown
        content = f"[{project_name}] **Plan Approved:** {tool_name_escaped}\n✅ *Ready to execute*"
    else:
        content = f"[{project_name}] Completed: {tool_name_escaped}"

    return {
        "content": content,
        "embeds": [
            {
                "title": f"✅ Completed: {tool_name_escaped}",
                "description": description,
                "color": 0x2ECC71,  # Green
                "footer": {"text": f"Session: {session_id} | Event: PostToolUse | {VERSION_STRING}"},
                "fields": [{"name": "Cwd", "value": escape_discord_markdown(cwd_str), "inline": False}],
            }
        ],
    }


def handle_notification(data: EventData, config: Config) -> DiscordMessage | None:
    """Handle Notification events."""
    message = data.get("message", "No message provided")
    message_escaped = escape_discord_markdown(message)

    # Get current working directory
    try:
        cwd = Path.cwd()
        cwd_str = str(cwd)
        project_name = escape_discord_markdown(cwd.name)
    except OSError:
        cwd_str = "Unknown"
        project_name = "Unknown"

    # Build content with project name and optional user mention
    content = f"[{project_name}] {message_escaped}"
    if user_id := config.get("mention_user_id"):
        content = f"<@{user_id}> {content}"

    return {
        "content": content,
        "embeds": [
            {
                "title": "📢 Notification",
                "description": message_escaped,
                "color": 0xF39C12,  # Orange
                "footer": {
                    "text": f"Session: {data.get('session_id', 'unknown')} | Event: Notification | {VERSION_STRING}"
                },
                "fields": [{"name": "Cwd", "value": escape_discord_markdown(cwd_str), "inline": False}],
            }
        ],
    }


def handle_stop(data: EventData, config: Config) -> DiscordMessage | None:
    """Handle Stop events."""
    # Get current working directory
    try:
        cwd = Path.cwd()
        cwd_str = str(cwd)
        project_name = escape_discord_markdown(cwd.name)
    except OSError:
        cwd_str = "Unknown"
        project_name = "Unknown"

    # Build content with project name and optional user mention
    content = f"[{project_name}] Session Ended"
    if user_id := config.get("mention_user_id"):
        content = f"<@{user_id}> {content}"

    return {
        "content": content,
        "embeds": [
            {
                "title": "⏹️ Session Ended",
                "description": "Claude Code session has ended.",
                "color": 0x95A5A6,  # Gray
                "footer": {"text": f"Session: {data.get('session_id', 'unknown')} | Event: Stop | {VERSION_STRING}"},
                "fields": [{"name": "Cwd", "value": escape_discord_markdown(cwd_str), "inline": False}],
            }
        ],
    }


def handle_subagent_stop(data: EventData, config: Config) -> DiscordMessage | None:
    """Handle SubagentStop events."""
    # Generate unique event ID for tracking
    event_id = str(uuid.uuid4())[:8]
    session_id = data.get("session_id", "unknown")
    logger.debug(f"[event-{event_id}] SubagentStop received for session {session_id}")

    # Get current working directory
    try:
        cwd = Path.cwd()
        cwd_str = str(cwd)
        project_name = escape_discord_markdown(cwd.name)
        logger.debug(f"[event-{event_id}] Working directory: {cwd_str}")
    except OSError as e:
        cwd_str = "Unknown"
        project_name = "Unknown"
        logger.debug(f"[event-{event_id}] OSError getting cwd: {e}")

    # Basic message for regular notification
    basic_message = {
        "content": f"[{project_name}] Subagent Completed",
        "embeds": [
            {
                "title": "🤖 Subagent Completed",
                "description": "A subagent task has been completed.",
                "color": 0x9B59B6,  # Purple
                "footer": {"text": f"Session: {session_id} | Event: SubagentStop | {VERSION_STRING}"},
                "fields": [{"name": "Cwd", "value": escape_discord_markdown(cwd_str), "inline": False}],
            }
        ],
    }

    # Check if thread posting is enabled
    thread_for_task = config.get("thread_for_task")
    logger.debug(f"[event-{event_id}] thread_for_task config: {thread_for_task}")
    if not thread_for_task:
        logger.debug(f"[event-{event_id}] Thread posting disabled, returning basic message")
        return basic_message

    # Check if we have bot token for thread posting
    bot_token = config.get("bot_token")
    if not bot_token:
        logger.debug(f"[event-{event_id}] Missing bot token for thread posting, returning basic message")
        return basic_message

    # Get the latest task for this session from TaskTracker
    latest_task = TaskTracker.get_latest_task(session_id)
    if not latest_task:
        logger.debug(f"[event-{event_id}] No tracked tasks found for session, returning basic message")
        return basic_message

    logger.debug(
        f"[event-{event_id}] Found latest task: {latest_task.get('task_id')} - {latest_task.get('description')}"
    )

    # Check if task has an associated thread
    thread_id = latest_task.get("thread_id")
    if not thread_id:
        logger.debug(f"[event-{event_id}] No thread associated with task, returning basic message")
        return basic_message

    logger.debug(f"[event-{event_id}] Found associated thread: {thread_id}")

    # Get transcript path for summary
    transcript_path = data.get("transcript_path")
    if transcript_path:
        logger.debug(f"[event-{event_id}] Reading transcript for summary...")
        subagent_data = read_subagent_messages(transcript_path)

        if subagent_data:
            # Calculate execution metrics
            from datetime import datetime

            try:
                start_time = datetime.fromisoformat(latest_task.get("start_time", ""))
                end_time = datetime.fromisoformat(latest_task.get("end_time", datetime.now(UTC).isoformat()))
                duration = end_time - start_time
                duration_text = f"{duration.total_seconds():.1f}s"
            except (ValueError, TypeError) as e:
                logger.debug(f"[event-{event_id}] Error calculating duration: {e}")
                duration_text = "Unknown"

            # Count messages
            task_messages = subagent_data.get("task_response_pairs", [])
            message_count = len(task_messages)

            # Build summary message
            summary_parts = [
                "## 📊 Task Summary",
                "",
                f"**Task**: {latest_task.get('description', 'Unknown')}",
                f"**Duration**: {duration_text}",
                f"**Messages Exchanged**: {message_count}",
                f"**Status**: {'✅ Completed' if latest_task.get('status') == 'completed' else '⚠️ ' + latest_task.get('status', 'Unknown')}",
            ]

            # Add brief transcript summary if available
            if task_messages:
                summary_parts.extend(["", "### 📝 Conversation Highlights", "```"])

                # Show first and last exchange
                if len(task_messages) > 0:
                    first_task = task_messages[0].get("task", {})
                    first_response = task_messages[0].get("response", {})
                    summary_parts.append("First Exchange:")
                    summary_parts.append(f"Q: {first_task.get('prompt', '')[:100]}...")
                    summary_parts.append(f"A: {first_response.get('content', '')[:100]}...")

                if len(task_messages) > 1:
                    last_task = task_messages[-1].get("task", {})
                    last_response = task_messages[-1].get("response", {})
                    summary_parts.append("")
                    summary_parts.append("Final Exchange:")
                    summary_parts.append(f"Q: {last_task.get('prompt', '')[:100]}...")
                    summary_parts.append(f"A: {last_response.get('content', '')[:100]}...")

                summary_parts.append("```")

            # Send summary to thread
            thread_message = {
                "content": "\n".join(summary_parts)[:2000]  # Discord message limit
            }

            logger.debug(f"[event-{event_id}] Posting summary to thread...")
            if send_to_thread(thread_id, thread_message, bot_token):
                logger.debug(f"[event-{event_id}] Summary posted successfully")
                # Update basic message to indicate summary was posted
                basic_message["embeds"][0]["description"] = f"Task completed. Summary posted in thread: <#{thread_id}>"
                basic_message["embeds"][0]["fields"].append({
                    "name": "Thread",
                    "value": f"<#{thread_id}>",
                    "inline": True,
                })
            else:
                logger.debug(f"[event-{event_id}] Failed to post summary to thread")

    logger.debug(f"[event-{event_id}] Returning final message")
    return basic_message


# =============================================================================
# Handler Registry - Just a simple dict
# =============================================================================

HANDLERS: dict[str, HandlerFunction] = {
    "PreToolUse": handle_pretooluse,
    "PostToolUse": handle_posttooluse,
    "Notification": handle_notification,
    "Stop": handle_stop,
    "SubagentStop": handle_subagent_stop,
}


def get_handler(event_type: str) -> HandlerFunction | None:
    """Get handler for event type."""
    return HANDLERS.get(event_type)


# =============================================================================
# Utility Functions
# =============================================================================


def should_process_event(event_type: str, config: Config) -> bool:
    """Check if event type should be processed."""
    # Check individual event states (new style - highest priority)
    if (event_states := config.get("event_states")) and event_type in event_states:
        return event_states[event_type]

    # Check enabled events (legacy whitelist)
    if enabled := config.get("enabled_events"):
        return event_type in enabled

    # Check disabled events (legacy blacklist)
    if disabled := config.get("disabled_events"):
        return event_type not in disabled

    # Default: all events enabled
    return True


def should_process_tool(tool_name: str, config: Config) -> bool:
    """Check if tool should be processed."""
    # Check individual tool states (new style - highest priority)
    if (tool_states := config.get("tool_states")) and tool_name in tool_states:
        return tool_states[tool_name]

    # Check disabled tools list (legacy)
    disabled_tools = config.get("disabled_tools", [])
    return tool_name not in disabled_tools


def format_tool_input(tool_name: str, tool_input: dict) -> str:
    """Format tool input for display."""
    if tool_name == "Write":
        file_path = escape_discord_markdown(tool_input.get("file_path", "unknown"))
        content = tool_input.get("content", "")
        size = len(content)
        return f"**File**: `{file_path}`\n**Size**: {size:,} chars"

    if tool_name == "Read":
        file_path = escape_discord_markdown(tool_input.get("file_path", "unknown"))
        return f"**File**: `{file_path}`"

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        # Escape Discord markdown characters (this is particularly important for commands with --flags)
        command = escape_discord_markdown(command)
        if len(command) > 100:
            command = command[:100] + "..."
        return f"**Command**: `{command}`"

    if tool_name == "Task":
        description = tool_input.get("description", "AI task execution")
        prompt = tool_input.get("prompt", "No prompt provided")
        # Format with code blocks for better readability and copy-paste functionality
        description_escaped = escape_discord_markdown(description)
        return f"**Description**: {description_escaped}\n```\n{prompt}\n```"

    if tool_name == "exit_plan_mode":
        plan = tool_input.get("plan", "No plan provided")
        # Format plan content in code blocks for easy copying
        return f"**Plan Content**:\n```\n{plan}\n```"

    # Default formatting
    formatted = escape_discord_markdown(str(tool_input))
    if len(formatted) > 500:
        formatted = formatted[:500] + "..."
    return formatted


def format_tool_response(tool_name: str, tool_response: dict) -> str:
    """Format tool response for display."""
    if error := tool_response.get("error"):
        # Escape error messages since they can contain user-generated content
        return f"❌ **Error**: {escape_discord_markdown(str(error))}"

    if tool_name == "Write":
        return "✅ File written successfully"

    if tool_name == "Read":
        return "✅ File read successfully"

    if tool_name == "Bash":
        return "✅ Command executed"

    # Default formatting
    formatted = escape_discord_markdown(str(tool_response))
    if len(formatted) > 500:
        formatted = formatted[:500] + "..."
    return formatted
