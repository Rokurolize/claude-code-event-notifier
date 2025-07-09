#!/usr/bin/env python3
"""Custom exception hierarchy for Discord Notifier.

This module provides a comprehensive exception hierarchy for handling
various error conditions in the Discord notification system.
"""


class DiscordNotifierError(Exception):
    """Base exception for Discord notifier.

    This is the root exception class for all Discord notifier-related errors.
    It provides a common base for exception handling and allows catching all
    notifier-specific errors with a single except clause.

    Usage:
        try:
            # Discord notifier operations
            pass
        except DiscordNotifierError as e:
            logger.error("Discord notifier error: %s", e)
    """


class ConfigurationError(DiscordNotifierError):
    """Configuration related errors.

    Raised when there are issues with configuration loading, validation,
    or when required configuration values are missing or invalid.

    Common causes:
        - Missing webhook URL or bot credentials
        - Invalid Discord user IDs for mentions
        - Malformed .env.discord file
        - Thread configuration inconsistencies

    Args:
        message: Descriptive error message

    Example:
        >>> if not config.get('webhook_url'):
        ...     raise ConfigurationError("No webhook URL configured")
    """


class DiscordAPIError(DiscordNotifierError):
    """Discord API related errors.

    Raised when Discord API calls fail, including HTTP errors, network issues,
    or API response validation failures.

    Common causes:
        - Invalid webhook URL or bot token
        - Network connectivity issues
        - Discord API rate limiting
        - Invalid channel IDs or permissions
        - Thread creation failures

    Args:
        message: Descriptive error message including HTTP status if available

    Example:
        >>> try:
        ...     response = urllib.request.urlopen(request)
        ... except urllib.error.HTTPError as e:
        ...     raise DiscordAPIError(f"HTTP {e.code}: {e.reason}")
    """


class EventProcessingError(DiscordNotifierError):
    """Event processing related errors.

    Raised when there are issues processing Claude Code events, including
    JSON parsing errors, missing required fields, or formatting failures.

    Common causes:
        - Malformed JSON input from stdin
        - Missing required event fields
        - Invalid event data structure
        - Event formatting failures

    Args:
        message: Descriptive error message

    Example:
        >>> try:
        ...     event_data = json.loads(stdin_input)
        ... except json.JSONDecodeError as e:
        ...     raise EventProcessingError(f"Invalid JSON: {e}")
    """


class InvalidEventTypeError(EventProcessingError):
    """Invalid event type error.

    Raised when an unsupported or invalid event type is encountered.
    While the system handles unknown event types gracefully, this error
    can be used for strict validation scenarios.

    Common causes:
        - Typos in CLAUDE_HOOK_EVENT environment variable
        - New event types not yet supported
        - Corrupted event data

    Args:
        message: Descriptive error message including the invalid event type

    Example:
        >>> event_type = os.environ.get('CLAUDE_HOOK_EVENT')
        >>> if event_type and not is_valid_event_type(event_type):
        ...     raise InvalidEventTypeError(f"Unknown event type: {event_type}")
    """


class ThreadManagementError(DiscordNotifierError):
    """Thread management related errors.

    Raised when there are issues with Discord thread operations,
    including creation, validation, or state management failures.

    Common causes:
        - Thread creation failures due to permissions
        - Invalid thread IDs or archived threads
        - Thread storage database errors
        - Discord API thread lookup failures

    Args:
        message: Descriptive error message
        session_id: Optional session ID associated with the thread
        thread_id: Optional thread ID that caused the error

    Example:
        >>> if not thread_details:
        ...     raise ThreadManagementError(f"Thread {thread_id} not found", thread_id=thread_id)
    """

    def __init__(self, message: str, session_id: str | None = None, thread_id: str | None = None):
        super().__init__(message)
        self.session_id = session_id
        self.thread_id = thread_id


class ThreadStorageError(DiscordNotifierError):
    """Thread storage persistence errors.

    Raised when there are issues with persistent thread storage operations,
    including database connection failures or data corruption.

    Common causes:
        - SQLite database initialization failures
        - File permission issues
        - Database corruption
        - Thread storage module not available

    Args:
        message: Descriptive error message
        original_error: Optional original exception that caused this error

    Example:
        >>> try:
        ...     storage.save_thread(session_id, thread_id)
        ... except sqlite3.Error as e:
        ...     raise ThreadStorageError(f"Database error: {e}", original_error=e)
    """

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error
