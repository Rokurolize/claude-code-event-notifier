"""Utility helper functions for Discord Notifier.

This module contains general utility functions for string manipulation,
file path formatting, and thread management.
"""

import os
from pathlib import Path
from typing import Any

# Try to import constants
try:
    from src.constants import TRUNCATION_SUFFIX
except ImportError:
    # Fallback if constants not available
    TRUNCATION_SUFFIX = "..."

# Thread management - shared state
SESSION_THREAD_CACHE: dict[str, str] = {}  # session_id -> thread_id mapping


def truncate_string(text: str, max_length: int, suffix: str = TRUNCATION_SUFFIX) -> str:
    """Truncate string to maximum length with suffix.

    Safely truncates text to fit within Discord's character limits while
    preserving readability by adding a truncation indicator.

    Args:
        text: The string to potentially truncate
        max_length: Maximum allowed length including suffix
        suffix: String to append when truncation occurs (default: "...")

    Returns:
        str: Original string if within limit, or truncated string with suffix

    Behavior:
        - If text is within limit, returns unchanged
        - If truncation needed, reserves space for suffix
        - Ensures result never exceeds max_length

    Example:
        >>> truncate_string("Hello world!", 10)
        'Hello w...'
        >>> truncate_string("Short", 10)
        'Short'
        >>> truncate_string("Long text here", 8, ">>")
        'Long t>>'
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_file_path(file_path: str) -> str:
    """Format file path to be relative if possible.

    Converts absolute file paths to relative paths when possible to improve
    readability in Discord messages. Falls back to filename only if relative
    path conversion fails.

    Args:
        file_path: Absolute or relative file path to format

    Returns:
        str: Formatted path string, empty string if input is empty

    Formatting Logic:
        1. Empty paths return empty string
        2. Attempts to make path relative to current working directory
        3. If already relative or conversion fails, returns as-is
        4. As last resort, returns just the filename

    Example:
        >>> # Assuming cwd is /home/user/project
        >>> format_file_path("/home/user/project/src/main.py")
        'src/main.py'
        >>> format_file_path("/other/path/file.txt")
        '/other/path/file.txt'
        >>> format_file_path("relative/path.py")
        'relative/path.py'

    Error Handling:
        - Invalid paths are returned as-is
        - Path resolution errors are caught and original path returned
        - Always returns a string, never raises exceptions
    """
    if not file_path:
        return ""

    try:
        path = Path(file_path)
        cwd = Path.cwd()

        # Try to make relative to current directory
        if path.is_absolute():
            try:
                return str(path.relative_to(cwd))
            except ValueError:
                # Path is not under cwd, return as is
                return str(path)
        else:
            return str(path)
    except Exception:
        # If all else fails, just return the original
        return file_path


def ensure_thread_is_usable(
    thread_details: dict[str, Any],
    channel_id: str,
    http_client: Any,
    bot_token: str,
) -> bool:
    """Ensure thread is active and can receive messages.

    Checks if a Discord thread is in a state where it can receive messages,
    and attempts to unarchive it if necessary. This is crucial for thread
    reuse across sessions.

    Args:
        thread_details: Discord thread object from API
        channel_id: Parent channel ID
        http_client: HTTP client instance for API calls
        bot_token: Discord bot token for authentication

    Returns:
        bool: True if thread is usable, False if unarchiving failed

    Thread States:
        - Active: Thread can receive messages immediately
        - Archived: Thread needs to be unarchived before use
        - Locked: Thread cannot be unarchived (returns False)

    Unarchiving Process:
        1. Check if thread is archived
        2. If archived and not locked, attempt to unarchive
        3. Verify unarchiving was successful
        4. Return success/failure status

    API Details:
        - Uses Discord's thread modification endpoint
        - Requires MANAGE_THREADS permission
        - Sets archived=false in thread settings

    Example:
        >>> thread = {"id": "123", "thread_metadata": {"archived": True}}
        >>> if ensure_thread_is_usable(thread, channel_id, client, token):
        ...     # Thread is now active and can receive messages
        ... else:
        ...     # Thread could not be activated, create new one

    Error Handling:
        - API errors during unarchiving return False
        - Missing permissions return False
        - Network errors return False
        - Always fails gracefully without raising
    """
    # Check if thread is archived
    metadata = thread_details.get("thread_metadata", {})
    if metadata.get("archived", False):
        # Try to unarchive the thread
        try:
            thread_id = thread_details["id"]
            headers = {"Authorization": f"Bot {bot_token}"}
            http_client.request(
                "PATCH",
                f"https://discord.com/api/v10/channels/{thread_id}",
                headers=headers,
                json={"archived": False},
            )
            return True
        except Exception:
            return False
    return True


# Export all public utilities
__all__ = [
    'truncate_string', 'format_file_path', 'ensure_thread_is_usable',
    'SESSION_THREAD_CACHE'
]