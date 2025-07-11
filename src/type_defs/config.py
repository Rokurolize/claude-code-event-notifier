"""Configuration-related type definitions.

This module contains TypedDict definitions for all configuration
structures used in the Discord Notifier system.
"""

from typing import TypedDict, Literal


class DiscordCredentials(TypedDict):
    """Discord authentication credentials."""

    webhook_url: str | None
    bot_token: str | None
    channel_id: str | None


class ThreadConfiguration(TypedDict):
    """Thread-specific configuration."""

    use_threads: bool
    channel_type: Literal["text", "forum"]
    thread_prefix: str
    thread_storage_path: str | None
    thread_cleanup_days: int


class NotificationConfiguration(TypedDict):
    """Notification-specific configuration."""

    mention_user_id: str | None
    debug: bool


class EventFilterConfiguration(TypedDict):
    """Event filtering configuration."""

    enabled_events: list[str] | None
    disabled_events: list[str] | None


class Config(
    DiscordCredentials,
    ThreadConfiguration,
    NotificationConfiguration,
    EventFilterConfiguration,
):
    """Complete configuration combining all aspects."""


# Export all public types
__all__ = [
    'DiscordCredentials', 'ThreadConfiguration',
    'NotificationConfiguration', 'EventFilterConfiguration',
    'Config'
]