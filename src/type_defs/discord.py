"""Discord-specific type definitions.

This module contains TypedDict definitions for Discord API structures
including embeds, messages, channels, and threads.
"""

from typing import TypedDict, NotRequired
from src.type_defs.base import BaseField, TimestampedField


class DiscordFooter(TypedDict):
    """Discord footer structure.

    Represents the footer section of a Discord embed. Footers appear at the
    bottom of embeds and typically contain metadata or contextual information.

    Attributes:
        text: Footer text content (max 2048 characters per Discord API)

    Usage:
        Footers are used to display session information and event metadata:

        >>> footer: DiscordFooter = {
        ...     "text": "Session: abc123de | Event: PreToolUse"
        ... }
    """

    text: str


class DiscordFieldBase(TypedDict):
    """Base Discord field structure.

    Represents the basic structure of a Discord embed field. Fields are
    key-value pairs that appear in the embed body and provide structured
    information display.

    Attributes:
        name: Field name/label (max 256 characters per Discord API)
        value: Field value/content (max 1024 characters per Discord API)

    Usage:
        This is the base class for Discord fields. Use DiscordField for
        full functionality including inline support.

    Example:
        >>> field_base: DiscordFieldBase = {
        ...     "name": "Command",
        ...     "value": "git status"
        ... }
    """

    name: str
    value: str


class DiscordField(DiscordFieldBase):
    """Discord field with optional inline support.

    Extends DiscordFieldBase to add inline positioning support. Inline fields
    appear side-by-side in the embed, allowing for more compact layouts.

    Attributes:
        name: Field name/label (inherited from DiscordFieldBase)
        value: Field value/content (inherited from DiscordFieldBase)
        inline: Optional boolean to display field inline (default: False)

    Usage:
        >>> field: DiscordField = {
        ...     "name": "Status",
        ...     "value": "Success",
        ...     "inline": True
        ... }

    Layout:
        - inline=True: Fields appear side-by-side (up to 3 per row)
        - inline=False: Fields appear stacked vertically
    """

    inline: NotRequired[bool]


class DiscordEmbedBase(TypedDict):
    """Base Discord embed structure."""

    title: NotRequired[str]
    description: NotRequired[str]
    color: NotRequired[int]


class DiscordEmbed(DiscordEmbedBase, TimestampedField):
    """Complete Discord embed structure."""

    footer: NotRequired[DiscordFooter]
    fields: NotRequired[list[DiscordField]]


class DiscordMessageBase(TypedDict):
    """Base Discord message structure."""

    embeds: NotRequired[list[DiscordEmbed]]


class DiscordMessage(DiscordMessageBase):
    """Discord message with optional content."""

    content: NotRequired[str]  # For mentions


# Discord API response types
class DiscordChannel(TypedDict, total=False):
    """Discord channel response structure."""

    id: str
    type: int
    name: str
    parent_id: str | None
    position: int
    topic: str | None
    nsfw: bool
    last_message_id: str | None


class DiscordThread(TypedDict, total=False):
    """Discord thread response structure."""

    id: str
    type: int
    name: str
    parent_id: str
    owner_id: str
    message_count: int
    member_count: int
    archived: bool
    auto_archive_duration: int
    archive_timestamp: str
    locked: bool
    invitable: bool
    create_timestamp: str | None


class DiscordThreadMessage(DiscordMessageBase):
    """Discord message with thread support."""

    thread_name: NotRequired[str]  # For creating new threads


# Export all public types
__all__ = [
    'DiscordFooter', 'DiscordFieldBase', 'DiscordField',
    'DiscordEmbedBase', 'DiscordEmbed', 'DiscordMessageBase',
    'DiscordMessage', 'DiscordChannel', 'DiscordThread',
    'DiscordThreadMessage'
]