"""Message ID generation utilities for Discord message tracking.

This module provides unique message ID generation capabilities for Discord messages,
enabling precise tracking and correlation of subagent communications.
"""

from datetime import datetime
from typing import Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo


class MessageIDGenerator(Protocol):
    """Message ID generation protocol."""

    def generate_message_id(self, event_type: str, session_id: str) -> str:
        """Generate unique message ID for Discord messages.

        Args:
            event_type: Type of event (e.g., "SubagentStop")
            session_id: Session identifier

        Returns:
            Unique message ID string
        """
        ...


class UUIDMessageIDGenerator:
    """UUID-based message ID generator.

    Generates unique message IDs using UUID and timestamp for Discord message tracking.
    Format: {event_type}_{session_id}_{timestamp}_{uuid}
    """

    def generate_message_id(self, event_type: str, session_id: str) -> str:
        """Generate unique message ID using UUID and timestamp.

        Args:
            event_type: Type of event (e.g., "SubagentStop")
            session_id: Session identifier

        Returns:
            Unique message ID in format: {event_type}_{session_id}_{timestamp}_{uuid}

        Example:
            >>> generator = UUIDMessageIDGenerator()
            >>> message_id = generator.generate_message_id("SubagentStop", "abc123def456")
            >>> # Returns: "SubagentStop_abc123def456_20250715214700_a1b2c3d4"
        """
        # Generate UTC timestamp
        timestamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%d%H%M%S")

        # Generate unique ID using first 8 characters of UUID
        unique_id = str(uuid4()).replace("-", "")[:8]

        # Combine components
        return f"{event_type}_{session_id}_{timestamp}_{unique_id}"
