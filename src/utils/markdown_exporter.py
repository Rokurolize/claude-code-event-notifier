"""Markdown export utilities for Discord embed content.

This module provides functionality to export Discord embed content to Markdown format,
enabling easy copying and external tool integration for subagent communications.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from src.formatters.event_formatters import DiscordEmbed


class MarkdownExporter(Protocol):
    """Markdown export protocol."""

    def export_embed_to_markdown(self, embed: "DiscordEmbed") -> str:
        """Export Discord embed to Markdown format.

        Args:
            embed: Discord embed object

        Returns:
            Markdown formatted string
        """
        ...


class SubagentMarkdownExporter:
    """Subagent-specific Markdown exporter.

    Converts SubagentStop Discord embeds to structured Markdown format
    for easy copying and external tool integration.
    """

    def export_embed_to_markdown(self, embed: "DiscordEmbed") -> str:
        """Export SubagentStop embed to Markdown format.

        Args:
            embed: Discord embed containing subagent information

        Returns:
            Markdown formatted string ready for copying
        """
        lines = []

        # Header
        title = embed.get("title", "Unknown Event")
        lines.append(f"# {title}")
        lines.append("")

        # Message ID
        message_id = embed.get("message_id", "unknown")
        lines.append(f"**Message ID**: `{message_id}`")
        lines.append("")

        # Get raw content data for detailed information
        raw_content = embed.get("raw_content", {})

        # Subagent information
        if "subagent_id" in raw_content:
            lines.append(f"**Subagent ID**: {raw_content['subagent_id']}")

        if "task_description" in raw_content:
            lines.append(f"**Task**: {raw_content['task_description']}")
            lines.append("")

        # Conversation content
        if "conversation_log" in raw_content:
            lines.append("## Conversation Log")
            lines.append("```")
            lines.append(raw_content["conversation_log"])
            lines.append("```")
            lines.append("")

        if "response_content" in raw_content:
            lines.append("## Response Content")
            lines.append("```")
            lines.append(raw_content["response_content"])
            lines.append("```")
            lines.append("")

        # Result information
        if "result" in raw_content:
            lines.append("## Result")
            lines.append("```")
            lines.append(raw_content["result"])
            lines.append("```")
            lines.append("")

        # Metrics information
        lines.append("## Metrics")
        if "duration_seconds" in raw_content:
            lines.append(f"- **Duration**: {raw_content['duration_seconds']} seconds")
        if "tools_used" in raw_content:
            lines.append(f"- **Tools Used**: {raw_content['tools_used']}")

        # Error information
        if "errors" in raw_content:
            lines.append("")
            lines.append("## Errors")
            lines.append("```")
            lines.append(raw_content["errors"])
            lines.append("```")

        # Footer
        lines.append("")
        lines.append("---")
        lines.append(f"*Generated at: {datetime.now(ZoneInfo('UTC')).isoformat()}*")

        return "\n".join(lines)


def generate_markdown_content(raw_content: dict[str, str], message_id: str) -> str:
    """Generate Markdown content from raw data.

    Args:
        raw_content: Raw content dictionary from Discord embed
        message_id: Unique message identifier

    Returns:
        Markdown formatted string
    """
    # Import here to avoid circular imports
    from src.formatters.event_formatters import DiscordEmbed

    exporter = SubagentMarkdownExporter()

    # Create pseudo embed object for conversion
    pseudo_embed: DiscordEmbed = {
        "title": "🤖 Subagent Completed",
        "description": "",
        "color": None,
        "timestamp": None,
        "footer": None,
        "fields": None,
        "message_id": message_id,
        "markdown_content": "",
        "raw_content": raw_content,
    }

    return exporter.export_embed_to_markdown(pseudo_embed)
