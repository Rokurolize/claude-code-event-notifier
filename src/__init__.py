"""
Claude Code Event Notifier

A notification system that sends Claude Code hook events to Discord channels.
This package monitors Claude Code operations and provides real-time visibility
through Discord notifications.
"""

from .event_notifier import ClaudeEventNotifier, main
from .message_formatter import EventMessageFormatter
from .discord_sender import DiscordNotificationSender

__version__ = "1.0.0"
__author__ = "Claude Code Event Notifier Contributors"
__all__ = [
    "ClaudeEventNotifier",
    "EventMessageFormatter",
    "DiscordNotificationSender",
    "main",
]
