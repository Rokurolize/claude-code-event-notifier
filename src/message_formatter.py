#!/usr/bin/env python3
"""
Message Formatter for Claude Code Event Notifier

This module handles the formatting of Claude Code hook events into
human-readable Discord embed messages.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EventMessageFormatter:
    """Formats Claude Code events into Discord-compatible embed messages."""

    # Tool emoji mapping for visual distinction
    TOOL_EMOJIS = {
        "Bash": "🔧",
        "Read": "📖",
        "Write": "✏️",
        "Edit": "✂️",
        "MultiEdit": "📝",
        "Glob": "🔍",
        "Grep": "🔎",
        "LS": "📁",
        "Task": "🤖",
        "WebFetch": "🌐",
        "mcp__human-in-the-loop__ask_human": "💬",
    }

    # Event colors for Discord embeds
    EVENT_COLORS = {
        "PreToolUse": 0x3498DB,  # Blue
        "PostToolUse": 0x2ECC71,  # Green
        "Notification": 0xF39C12,  # Orange
        "Stop": 0x95A5A6,  # Gray
        "SubagentStop": 0x9B59B6,  # Purple
    }

    def __init__(self):
        """Initialize the message formatter."""
        pass

    def format_event_notification(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format a Claude Code event into a Discord embed message.

        Args:
            event_type: Type of the event (PreToolUse, PostToolUse, etc.)
            event_data: Event data from Claude Code hook

        Returns:
            Discord embed message structure
        """
        logger.debug(f"Formatting notification for event_type: {event_type}")
        logger.debug(f"Event data keys: {list(event_data.keys())}")

        timestamp = datetime.now().isoformat()
        session_id = self._get_session_id(event_data)

        # Base embed structure
        embed = {"timestamp": timestamp, "footer": {"text": f"Session: {session_id}"}}

        # Format based on event type
        if event_type == "PreToolUse":
            self._format_pre_tool_use(embed, event_data)
        elif event_type == "PostToolUse":
            self._format_post_tool_use(embed, event_data)
        elif event_type == "Notification":
            self._format_notification(embed, event_data)
        elif event_type == "Stop":
            self._format_stop_event(embed, event_data)
        elif event_type == "SubagentStop":
            self._format_subagent_stop(embed, event_data)
        else:
            self._format_unknown_event(embed, event_type, event_data)

        # Add color
        embed["color"] = self.EVENT_COLORS.get(event_type, 0x808080)

        logger.debug(f"Created embed: {embed}")
        return {"embeds": [embed]}

    def _get_session_id(self, event_data: Dict[str, Any]) -> str:
        """Extract and truncate session ID from event data."""
        session_id = event_data.get("session_id", "unknown")
        return session_id[:8] if len(session_id) > 8 else session_id

    def _format_pre_tool_use(
        self, embed: Dict[str, Any], event_data: Dict[str, Any]
    ) -> None:
        """Format PreToolUse event."""
        tool_name = event_data.get("tool_name", "Unknown")
        tool_input = event_data.get("tool_input", {})

        embed["title"] = f"About to execute: {self.get_tool_display_name(tool_name)}"

        description_parts = []

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            description_parts.append(self._format_command(command))

        elif tool_name in ["Write", "Edit", "MultiEdit"]:
            file_path = tool_input.get("file_path", "")
            if file_path:
                description_parts.append(
                    f"**File:** {self.format_file_path(file_path)}"
                )

            if tool_name == "Write":
                content = tool_input.get("content", "")
                if content:
                    lines = len(content.split("\n"))
                    chars = len(content)
                    description_parts.append(
                        f"**Content:** {lines} lines, {chars} characters"
                    )

        elif tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            if file_path:
                description_parts.append(
                    f"**Reading:** {self.format_file_path(file_path)}"
                )

        elif tool_name in ["Glob", "Grep"]:
            pattern = tool_input.get("pattern", "")
            if pattern:
                description_parts.append(f"**Pattern:** `{pattern}`")

        elif tool_name == "mcp__human-in-the-loop__ask_human":
            question = tool_input.get("question", "")
            if question:
                preview = question[:100] + "..." if len(question) > 100 else question
                description_parts.append(f"**Question:** {preview}")

        embed["description"] = (
            "\n".join(description_parts) if description_parts else "Executing tool..."
        )

    def _format_post_tool_use(
        self, embed: Dict[str, Any], event_data: Dict[str, Any]
    ) -> None:
        """Format PostToolUse event."""
        tool_name = event_data.get("tool_name", "Unknown")

        embed["title"] = f"Completed: {self.get_tool_display_name(tool_name)}"
        embed["description"] = "Tool execution finished"

        # Add execution time if available
        if "execution_time" in event_data:
            embed["description"] += f" in {event_data['execution_time']:.2f}s"

    def _format_notification(
        self, embed: Dict[str, Any], event_data: Dict[str, Any]
    ) -> None:
        """Format Notification event."""
        embed["title"] = "📢 Notification"
        embed["description"] = event_data.get("message", "System notification")

    def _format_stop_event(
        self, embed: Dict[str, Any], event_data: Dict[str, Any]
    ) -> None:
        """Format Stop event."""
        session_id = self._get_session_id(event_data)
        embed["title"] = "🏁 Session Ended"
        embed["description"] = f"Claude Code session `{session_id}` has finished"

    def _format_subagent_stop(
        self, embed: Dict[str, Any], event_data: Dict[str, Any]
    ) -> None:
        """Format SubagentStop event."""
        session_id = self._get_session_id(event_data)
        embed["title"] = "🤖 Subagent Completed"
        embed["description"] = f"Subagent task completed in session `{session_id}`"

    def _format_unknown_event(
        self, embed: Dict[str, Any], event_type: str, event_data: Dict[str, Any]
    ) -> None:
        """Format unknown event types."""
        embed["title"] = f"⚡ {event_type}"
        embed["description"] = f"Event data: {str(event_data)[:200]}..."

    def _format_command(self, command: str, max_length: int = 100) -> str:
        """Format a command for display, truncating if necessary."""
        if len(command) > max_length:
            command = command[:max_length] + "..."
        return f"**Command:** `{command}`"

    def get_tool_display_name(self, tool_name: str) -> str:
        """Get display name for a tool with appropriate emoji."""
        emoji = self.TOOL_EMOJIS.get(tool_name, "⚡")
        formatted = f"{emoji} {tool_name}"
        logger.debug(f"Formatted tool name: {tool_name} -> {formatted}")
        return formatted

    def format_file_path(self, path: str) -> str:
        """Format file path for display, showing only relevant parts."""
        if not path:
            return ""

        path_obj = Path(path)

        # Show relative path if in current directory
        try:
            rel_path = path_obj.relative_to(Path.cwd())
            if len(str(rel_path)) < len(str(path_obj)):
                formatted = f"`{rel_path}`"
                logger.debug(f"Formatted path as relative: {path} -> {formatted}")
                return formatted
        except ValueError:
            pass

        # Show just filename for long paths
        if len(str(path_obj)) > 50:
            formatted = f"`.../{path_obj.name}`"
            logger.debug(f"Formatted long path: {path} -> {formatted}")
            return formatted

        formatted = f"`{path_obj}`"
        logger.debug(f"Formatted path: {path} -> {formatted}")
        return formatted
