#!/usr/bin/env python3
"""Simple event handlers for Discord Event Notifier.

All event handlers in one beautiful, simple file.
"""

import os
from typing import Callable, Optional

from event_types import Config, DiscordMessage, EventData, HandlerFunction
from version import VERSION_STRING

# Python 3.14+ required - pure standard library


# =============================================================================
# Event Handlers - Simple, beautiful functions
# =============================================================================

def handle_pretooluse(data: EventData, config: Config) -> Optional[DiscordMessage]:
    """Handle PreToolUse events."""
    tool_name = data.get("tool_name", "Unknown")
    
    # Skip if tool is disabled
    if not should_process_tool(tool_name, config):
        return None
    
    # Format tool input
    tool_input = data.get("tool_input", {})
    description = format_tool_input(tool_name, tool_input)
    
    # Get project name from working directory
    project_name = os.path.basename(os.getcwd())
    
    return {
        "content": f"[{project_name}] About to execute: {tool_name}",
        "embeds": [{
            "title": f"🔵 Starting: {tool_name}",
            "description": description,
            "color": 0x3498db,  # Blue
            "footer": {"text": f"Session: {data.get('session_id', 'unknown')} | Event: PreToolUse | {VERSION_STRING}"},
            "fields": [
                {"name": "Cwd", "value": os.getcwd(), "inline": False}
            ]
        }]
    }


def handle_posttooluse(data: EventData, config: Config) -> Optional[DiscordMessage]:
    """Handle PostToolUse events."""
    tool_name = data.get("tool_name", "Unknown")
    
    # Skip if tool is disabled
    if not should_process_tool(tool_name, config):
        return None
    
    # Format tool response
    tool_response = data.get("tool_response", {})
    description = format_tool_response(tool_name, tool_response)
    
    # Get project name from working directory
    project_name = os.path.basename(os.getcwd())
    
    return {
        "content": f"[{project_name}] Completed: {tool_name}",
        "embeds": [{
            "title": f"✅ Completed: {tool_name}",
            "description": description,
            "color": 0x2ecc71,  # Green
            "footer": {"text": f"Session: {data.get('session_id', 'unknown')} | Event: PostToolUse | {VERSION_STRING}"},
            "fields": [
                {"name": "Cwd", "value": os.getcwd(), "inline": False}
            ]
        }]
    }


def handle_notification(data: EventData, config: Config) -> Optional[DiscordMessage]:
    """Handle Notification events."""
    message = data.get("message", "No message provided")
    
    # Get project name from working directory
    project_name = os.path.basename(os.getcwd())
    
    # Build content with project name and optional user mention
    content = f"[{project_name}] {message}"
    if user_id := config.get("mention_user_id"):
        content = f"<@{user_id}> {content}"
    
    return {
        "content": content,
        "embeds": [{
            "title": "📢 Notification",
            "description": message,
            "color": 0xf39c12,  # Orange
            "footer": {"text": f"Session: {data.get('session_id', 'unknown')} | Event: Notification | {VERSION_STRING}"},
            "fields": [
                {"name": "Cwd", "value": os.getcwd(), "inline": False}
            ]
        }]
    }


def handle_stop(data: EventData, config: Config) -> Optional[DiscordMessage]:
    """Handle Stop events."""
    # Get project name from working directory
    project_name = os.path.basename(os.getcwd())
    
    # Build content with project name and optional user mention
    content = f"[{project_name}] Session Ended"
    if user_id := config.get("mention_user_id"):
        content = f"<@{user_id}> {content}"
    
    return {
        "content": content,
        "embeds": [{
            "title": "⏹️ Session Ended",
            "description": "Claude Code session has ended.",
            "color": 0x95a5a6,  # Gray
            "footer": {"text": f"Session: {data.get('session_id', 'unknown')} | Event: Stop | {VERSION_STRING}"},
            "fields": [
                {"name": "Cwd", "value": os.getcwd(), "inline": False}
            ]
        }]
    }


def handle_subagent_stop(data: EventData, config: Config) -> Optional[DiscordMessage]:
    """Handle SubagentStop events."""
    # Get project name from working directory
    project_name = os.path.basename(os.getcwd())
    
    return {
        "content": f"[{project_name}] Subagent Completed",
        "embeds": [{
            "title": "🤖 Subagent Completed",
            "description": "A subagent task has been completed.",
            "color": 0x9b59b6,  # Purple
            "footer": {"text": f"Session: {data.get('session_id', 'unknown')} | Event: SubagentStop | {VERSION_STRING}"},
            "fields": [
                {"name": "Cwd", "value": os.getcwd(), "inline": False}
            ]
        }]
    }


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


def get_handler(event_type: str) -> Optional[HandlerFunction]:
    """Get handler for event type."""
    return HANDLERS.get(event_type)


# =============================================================================
# Utility Functions
# =============================================================================

def should_process_event(event_type: str, config: Config) -> bool:
    """Check if event type should be processed."""
    # Check individual event states (new style - highest priority)
    if event_states := config.get("event_states"):
        if event_type in event_states:
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
    if tool_states := config.get("tool_states"):
        if tool_name in tool_states:
            return tool_states[tool_name]
    
    # Check disabled tools list (legacy)
    disabled_tools = config.get("disabled_tools", [])
    return tool_name not in disabled_tools


def format_tool_input(tool_name: str, tool_input: dict) -> str:
    """Format tool input for display."""
    if tool_name == "Write":
        file_path = tool_input.get("file_path", "unknown")
        content = tool_input.get("content", "")
        size = len(content)
        return f"**File**: `{file_path}`\n**Size**: {size:,} chars"
    
    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "unknown")
        return f"**File**: `{file_path}`"
    
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if len(command) > 100:
            command = command[:100] + "..."
        return f"**Command**: `{command}`"
    
    # Default formatting
    formatted = str(tool_input)
    if len(formatted) > 500:
        formatted = formatted[:500] + "..."
    return formatted


def format_tool_response(tool_name: str, tool_response: dict) -> str:
    """Format tool response for display."""
    if error := tool_response.get("error"):
        return f"❌ **Error**: {error}"
    
    if tool_name == "Write":
        return "✅ File written successfully"
    
    elif tool_name == "Read":
        return "✅ File read successfully"
    
    elif tool_name == "Bash":
        return "✅ Command executed"
    
    # Default formatting
    formatted = str(tool_response)
    if len(formatted) > 500:
        formatted = formatted[:500] + "..."
    return formatted