"""Exception classes for Discord Notifier.

This module contains all custom exception classes used throughout
the Discord Notifier system.
"""

from typing import Optional, Any, Dict, Callable, TypeVar, ParamSpec
import traceback
from pathlib import Path
from datetime import UTC, datetime
from functools import wraps

from src.utils.astolfo_logger import AstolfoLogger
from src.utils.astolfo_logger_types import AstolfoLoggerConfig

# Type variables for generic functions
P = ParamSpec('P')
T = TypeVar('T')


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
    
    _logger: Optional[AstolfoLogger] = None
    
    @classmethod
    def get_logger(cls) -> AstolfoLogger:
        """Get or create the exception logger instance."""
        if cls._logger is None:
            # Configure logger for exception tracking
            log_file = str(Path.home() / ".claude" / "hooks" / "logs" / "discord_notifier_exceptions.log")
            config: AstolfoLoggerConfig = {
                "debug_level": 3,  # Maximum debug level for exceptions
                "log_file": log_file,
                "rotation": {
                    "max_size": 10 * 1024 * 1024,  # 10MB
                    "backup_count": 5
                }
            }
            cls._logger = AstolfoLogger(
                name="discord_notifier.exceptions",
                debug_level=3,
                config=config
            )
        return cls._logger
    
    def __init__(self, message: str, **context: Any):
        """Initialize exception with message and optional context.
        
        Args:
            message: Exception message
            **context: Additional context to log with the exception
        """
        super().__init__(message)
        self.context = context
        self._log_exception()
    
    def _log_exception(self) -> None:
        """Log the exception with full context."""
        logger = self.get_logger()
        
        # Build exception context
        exc_context = {
            "exception_type": self.__class__.__name__,
            "message": str(self),
            "traceback": traceback.format_exc(),
            **self.context
        }
        
        # Log with appropriate level based on exception type
        if isinstance(self, ConfigurationError):
            logger.error(
                f"Configuration error: {self}",
                error_type="configuration",
                **exc_context
            )
        elif isinstance(self, DiscordAPIError):
            logger.error(
                f"Discord API error: {self}",
                error_type="discord_api",
                **exc_context
            )
        elif isinstance(self, EventProcessingError):
            logger.error(
                f"Event processing error: {self}",
                error_type="event_processing",
                **exc_context
            )
        elif isinstance(self, ThreadManagementError):
            logger.error(
                f"Thread management error: {self}",
                error_type="thread_management",
                **exc_context
            )
        elif isinstance(self, ThreadStorageError):
            logger.error(
                f"Thread storage error: {self}",
                error_type="thread_storage",
                **exc_context
            )
        else:
            logger.error(
                f"Discord notifier error: {self}",
                error_type="generic",
                **exc_context
            )


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
        self.session_id = session_id
        self.thread_id = thread_id
        context = {}
        if session_id:
            context['session_id'] = session_id
        if thread_id:
            context['thread_id'] = thread_id
        super().__init__(message, **context)


class ThreadStorageError(DiscordNotifierError):
    """Thread storage persistence errors.

    Raised when there are issues with persistent thread storage operations,
    including database connection failures or data corruption.

    Common causes:
        - SQLite database file permissions
        - Database schema corruption
        - Disk space or file system issues
        - Invalid thread record data

    Args:
        message: Descriptive error message
        operation: Storage operation that failed (store, retrieve, remove, etc.)

    Example:
        >>> try:
        ...     storage.store_thread(session_id, thread_id, ...)
        ... except sqlite3.Error as e:
        ...     raise ThreadStorageError(f"Failed to store thread: {e}", operation="store")
    """

    def __init__(self, message: str, operation: str | None = None):
        self.operation = operation
        context = {}
        if operation:
            context['operation'] = operation
        super().__init__(message, **context)


# Utility functions for exception handling

def log_and_reraise(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to log exceptions before re-raising them.
    
    This decorator ensures that any DiscordNotifierError raised from the
    decorated function is logged with full context before being re-raised.
    
    Example:
        @log_and_reraise
        def process_event(event_data: dict) -> None:
            if not event_data.get('session_id'):
                raise EventProcessingError("Missing session_id")
    """
    from functools import wraps
    from typing import Callable, TypeVar, ParamSpec
    
    P = ParamSpec('P')
    T = TypeVar('T')
    
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except DiscordNotifierError:
            # Already logged by exception __init__
            raise
        except Exception as e:
            # Convert to DiscordNotifierError and log
            logger = DiscordNotifierError.get_logger()
            logger.error(
                f"Unexpected error in {func.__name__}: {e}",
                function=func.__name__,
                error_type="unexpected",
                traceback=traceback.format_exc()
            )
            raise
    
    return wrapper


def create_exception_context(
    event_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    **additional_context: Any
) -> Dict[str, Any]:
    """Create a rich context dictionary for exception logging.
    
    Args:
        event_data: Optional event data dictionary
        session_id: Optional session ID
        **additional_context: Any additional context to include
    
    Returns:
        Dictionary with all relevant context for debugging
    """
    import os
    
    context: Dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "process_id": os.getpid(),
    }
    
    if event_data:
        context["event_data"] = event_data
        context["event_type"] = event_data.get("type", "unknown")
    
    if session_id:
        context["session_id"] = session_id
    
    # Add environment context
    context["claude_hook_event"] = os.environ.get("CLAUDE_HOOK_EVENT")
    context["discord_debug"] = os.environ.get("DISCORD_DEBUG", "0") == "1"
    
    # Add any additional context
    context.update(additional_context)
    
    return context


# Export all public exceptions and utilities
__all__ = [
    'DiscordNotifierError', 'ConfigurationError', 'DiscordAPIError',
    'EventProcessingError', 'InvalidEventTypeError',
    'ThreadManagementError', 'ThreadStorageError',
    'log_and_reraise', 'create_exception_context'
]