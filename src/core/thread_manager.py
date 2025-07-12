"""Thread management functions for Discord Notifier.

This module provides comprehensive thread management functionality including:
- Thread validation and existence checking
- Thread search and discovery
- Thread creation and unarchiving
- Session-based thread caching
- Persistent thread storage integration
"""

from src.utils.astolfo_logger import AstolfoLogger

from pathlib import Path
from typing import cast, Any

# Try to import types
try:
    from src.type_defs.config import Config
    from src.type_defs.discord import DiscordThread
except ImportError:
    # Fallback if modules not available
    from discord_notifier import Config, DiscordThread  # type: ignore

# Try to import HTTPClient
try:
    from src.core.http_client import HTTPClient
except ImportError:
    from discord_notifier import HTTPClient  # type: ignore

# Try to import exceptions
try:
    from src.exceptions import (
        DiscordAPIError,
        ThreadManagementError,
        ThreadStorageError,
    )
except ImportError:
    from discord_notifier import (  # type: ignore
        DiscordAPIError,
        ThreadManagementError,
        ThreadStorageError,
    )

# Try to import utils
try:
    from src.utils_helpers import (
        ensure_thread_is_usable as utils_ensure_thread_is_usable,
        SESSION_THREAD_CACHE,
    )
    UTILS_HELPERS_AVAILABLE = True
except ImportError:
    # Define minimal SESSION_THREAD_CACHE if not available
    UTILS_HELPERS_AVAILABLE = False
    # Create a module-level cache
    SESSION_THREAD_CACHE = {}

# Try to import ThreadStorage
try:
    from src.thread_storage import ThreadStorage
    THREAD_STORAGE_AVAILABLE = True
except ImportError:
    try:
        from thread_storage import ThreadStorage  # type: ignore
        THREAD_STORAGE_AVAILABLE = True
    except ImportError:
        THREAD_STORAGE_AVAILABLE = False


def validate_thread_exists(
    thread_id: str, config: Config, http_client: HTTPClient, logger: AstolfoLogger
) -> DiscordThread | None:
    """Validate that a thread still exists and get its current status.

    Args:
        thread_id: Discord thread ID to validate
        config: Discord configuration
        http_client: HTTP client for API calls
        logger: Logger instance

    Returns:
        Thread details dict if thread exists and is accessible, None otherwise
    """
    bot_token = config.get("bot_token")
    if not thread_id or not bot_token:
        return None

    try:
        thread_details = http_client.get_thread_details(thread_id, bot_token)
        if thread_details:
            logger.debug("Thread %s exists and is accessible", thread_id)
            return thread_details
    except DiscordAPIError as e:
        logger.warning("Discord API error validating thread %s: %s", thread_id, e)
        return None
    except ThreadManagementError as e:
        logger.warning("Thread management error validating thread %s: %s", thread_id, e)
        return None
    except (OSError, ValueError, TypeError, KeyError) as e:
        # Catch other errors during thread validation
        logger.exception("Unexpected error validating thread %s: %s", thread_id, type(e).__name__)
        return None

    logger.debug("Thread %s not found or not accessible", thread_id)
    return None


def _find_best_matching_thread(
    threads: list[DiscordThread], thread_name: str, logger: AstolfoLogger
) -> DiscordThread | None:
    """Find the best matching thread from a list of threads.

    Args:
        threads: List of thread details
        thread_name: Exact thread name to match
        logger: Logger instance

    Returns:
        Best matching thread or None
    """
    # First, look for exact match
    for thread in threads:
        if thread.get("name") == thread_name:
            logger.debug("Found exact thread match: %s - %s", thread["id"], thread["name"])
            return thread

    # If no exact match, return the first partial match
    if threads:
        thread = threads[0]
        logger.debug("Found partial thread match: %s - %s", thread["id"], thread["name"])
        return thread

    return None


def _search_threads_with_error_handling(
    channel_id: str,
    thread_name: str,
    bot_token: str,
    http_client: HTTPClient,
    logger: AstolfoLogger,
) -> list[DiscordThread] | None:
    """Search for threads with comprehensive error handling.

    Args:
        channel_id: Discord channel ID
        thread_name: Thread name to search
        bot_token: Bot authentication token
        http_client: HTTP client instance
        logger: Logger instance

    Returns:
        List of matching threads or None on error
    """
    try:
        return http_client.search_threads_by_name(channel_id, thread_name, bot_token)
    except DiscordAPIError as e:
        logger.warning("Discord API error searching for thread '%s': %s", thread_name, e)
    except ThreadManagementError as e:
        logger.warning("Thread management error searching for thread '%s': %s", thread_name, e)
    except (OSError, ValueError, TypeError, KeyError) as e:
        logger.exception("Unexpected error searching for thread '%s': %s", thread_name, type(e).__name__)
    return None


def find_existing_thread_by_name(
    channel_id: str,
    thread_name: str,
    config: Config,
    http_client: HTTPClient,
    logger: AstolfoLogger,
) -> DiscordThread | None:
    """Find an existing thread by name in a channel.

    Args:
        channel_id: Discord channel ID to search in
        thread_name: Thread name to search for
        config: Discord configuration
        http_client: HTTP client for API calls
        logger: Logger instance

    Returns:
        Thread details dict if found, None otherwise
    """
    bot_token = config.get("bot_token")
    if not channel_id or not thread_name or not bot_token:
        return None

    matching_threads = _search_threads_with_error_handling(channel_id, thread_name, bot_token, http_client, logger)

    if matching_threads:
        return _find_best_matching_thread(matching_threads, thread_name, logger)

    logger.debug("No threads found matching name '%s' in channel %s", thread_name, channel_id)
    return None


def _check_thread_state(thread_details: dict[str, object]) -> tuple[bool, bool]:
    """Check if thread is archived or locked.

    Args:
        thread_details: Thread details from Discord API

    Returns:
        Tuple of (is_archived, is_locked)
    """
    thread_metadata: dict[str, object] = cast(dict[str, object], thread_details.get("thread_metadata", {}))
    is_archived = bool(thread_metadata.get("archived", False))
    is_locked = bool(thread_metadata.get("locked", False))
    return is_archived, is_locked


def _try_unarchive_thread(
    thread_id: str,
    bot_token: str,
    http_client: HTTPClient,
    logger: AstolfoLogger,
) -> bool:
    """Try to unarchive a thread with error handling.

    Args:
        thread_id: Thread ID to unarchive
        bot_token: Bot authentication token
        http_client: HTTP client instance
        logger: Logger instance

    Returns:
        True if successfully unarchived, False otherwise
    """
    try:
        if http_client.unarchive_thread(thread_id, bot_token):
            logger.info("Successfully unarchived thread %s", thread_id)
            return True
    except DiscordAPIError as e:
        logger.warning("Discord API error unarchiving thread %s: %s", thread_id, e)
    except ThreadManagementError as e:
        logger.warning("Thread management error unarchiving thread %s: %s", thread_id, e)
    except (OSError, ValueError, TypeError):
        logger.exception("Unexpected error unarchiving thread %s", thread_id)

    logger.warning("Failed to unarchive thread %s", thread_id)
    return False


# ensure_thread_is_usable implementation
def ensure_thread_is_usable(
    thread_details: DiscordThread,
    config: Config,
    http_client: HTTPClient,
    logger: AstolfoLogger,
) -> bool:
    """Ensure a thread is usable by unarchiving if needed."""
    is_archived, is_locked = _check_thread_state(cast(dict[str, object], thread_details))
    
    if is_locked:
        logger.warning("Thread %s is locked and cannot be used", thread_details["id"])
        return False
    
    if is_archived:
        bot_token = config.get("bot_token")
        if bot_token:
            return _try_unarchive_thread(thread_details["id"], bot_token, http_client, logger)
        logger.warning("Thread %s is archived but no bot token available to unarchive", thread_details["id"])
        return False
    
    return True


def _check_cached_thread(
    session_id: str, config: Config, http_client: HTTPClient, logger: AstolfoLogger
) -> str | None:
    """Check in-memory cache for thread and validate it."""
    if session_id not in SESSION_THREAD_CACHE:
        return None

    cached_thread_id = SESSION_THREAD_CACHE[session_id]
    logger.debug("Found cached thread for session %s: %s", session_id, cached_thread_id)

    # Validate that cached thread still exists and is usable
    thread_details = validate_thread_exists(cached_thread_id, config, http_client, logger)
    if thread_details and ensure_thread_is_usable(thread_details, config, http_client, logger):
        logger.debug("Cached thread %s is valid and usable", cached_thread_id)
        return cached_thread_id

    # Remove invalid thread from cache
    logger.warning("Cached thread %s is invalid, removing from cache", cached_thread_id)
    del SESSION_THREAD_CACHE[session_id]
    return None


def _check_persistent_storage(
    session_id: str, config: Config, http_client: HTTPClient, logger: AstolfoLogger
) -> str | None:
    """Check persistent storage for thread and validate it."""
    if not THREAD_STORAGE_AVAILABLE:
        logger.debug("ThreadStorage not available, skipping persistent storage check")
        return None

    try:
        # Use configured storage path or default
        storage_path = None
        thread_storage_path = config.get("thread_storage_path")
        if thread_storage_path:
            storage_path = Path(thread_storage_path)

        cleanup_days = config.get("thread_cleanup_days", 30)
        storage = ThreadStorage(db_path=storage_path, cleanup_days=cleanup_days)
        stored_record = storage.get_thread(session_id)

        if stored_record:
            logger.debug("Found stored thread for session %s: %s", session_id, stored_record.thread_id)

            # Validate that stored thread still exists and is usable
            thread_details = validate_thread_exists(stored_record.thread_id, config, http_client, logger)
            if thread_details and ensure_thread_is_usable(thread_details, config, http_client, logger):
                # Update cache and return valid stored thread
                thread_id = str(stored_record.thread_id)
                SESSION_THREAD_CACHE[session_id] = thread_id
                logger.info("Restored thread %s from storage for session %s", thread_id, session_id)
                return thread_id

            # Remove invalid thread from storage
            logger.warning("Stored thread %s is invalid, removing from storage", stored_record.thread_id)
            storage.remove_thread(session_id)

    except ImportError as e:
        logger.warning("ThreadStorage import error: %s", e)
    except ThreadStorageError as e:
        logger.warning("Thread storage error for session %s: %s", session_id, e)
    except (OSError, ValueError, TypeError) as e:
        logger.warning(
            "Unexpected error checking persistent storage for session %s: %s: %s", session_id, type(e).__name__, e
        )

    return None


def _store_thread_in_storage(
    session_id: str,
    thread_id: str,
    channel_id: str,
    thread_name: str,
    is_archived: bool,
    config: Config,
    logger: AstolfoLogger,
) -> None:
    """Store thread in persistent storage."""
    if not THREAD_STORAGE_AVAILABLE:
        return
        
    try:
        storage_path = None
        thread_storage_path = config.get("thread_storage_path")
        if thread_storage_path:
            storage_path = Path(thread_storage_path)
        cleanup_days = config.get("thread_cleanup_days", 30)
        storage = ThreadStorage(db_path=storage_path, cleanup_days=cleanup_days)

        storage.store_thread(
            session_id=session_id,
            thread_id=thread_id,
            channel_id=channel_id,
            thread_name=thread_name,
            is_archived=is_archived,
        )
    except ThreadStorageError as e:
        logger.warning("Thread storage error storing thread: %s", e)
    except (OSError, ValueError, TypeError) as e:
        logger.warning("Unexpected error storing thread: %s: %s", type(e).__name__, e)


def _search_discord_for_thread(
    session_id: str, thread_name: str, config: Config, http_client: HTTPClient, logger: AstolfoLogger
) -> str | None:
    """Search Discord API for existing thread by name."""
    channel_id = config.get("channel_id")

    if not channel_id or not config.get("bot_token"):
        return None

    logger.debug("Searching Discord API for thread: %s", thread_name)
    existing_thread = find_existing_thread_by_name(channel_id, thread_name, config, http_client, logger)

    if not existing_thread:
        return None

    if not ensure_thread_is_usable(existing_thread, config, http_client, logger):
        logger.warning("Found thread %s but it cannot be made usable", existing_thread["id"])
        return None

    thread_id = str(existing_thread["id"])

    # Cache the discovered thread
    SESSION_THREAD_CACHE[session_id] = thread_id

    # Store in persistent storage for future use
    # existing_thread might have thread_metadata
    thread_data = cast(dict[str, object], existing_thread)
    thread_metadata = cast(dict[str, object], thread_data.get("thread_metadata", {}))
    is_archived = bool(thread_metadata.get("archived", False))
    _store_thread_in_storage(session_id, thread_id, channel_id, thread_name, is_archived, config, logger)
    logger.info("Discovered and restored existing thread %s for session %s", thread_id, session_id)

    return thread_id


def _handle_forum_channel_thread(config: Config, logger: AstolfoLogger) -> str | None:
    """Handle thread creation for forum channels.

    Args:
        config: Discord configuration
        logger: Logger instance

    Returns:
        None (thread creation deferred) or None with warning
    """
    if config["webhook_url"]:
        # For forum channels, thread creation happens with the first message
        logger.debug("Forum channel thread creation deferred to message sending")
        return None
    logger.warning("Forum channel threads require webhook URL")
    return None


def _create_text_channel_thread(
    session_id: str,
    thread_name: str,
    config: Config,
    http_client: HTTPClient,
    logger: AstolfoLogger,
) -> str | None:
    """Create a thread in a text channel.

    Args:
        session_id: Session ID for caching
        thread_name: Name for the new thread
        config: Discord configuration
        http_client: HTTP client instance
        logger: Logger instance

    Returns:
        Thread ID if created, None otherwise
    """
    if not config["bot_token"] or not config["channel_id"]:
        logger.warning("Text channel threads require bot token and channel ID")
        return None

    new_thread_id = http_client.create_text_thread(config["channel_id"], thread_name, config["bot_token"])

    if new_thread_id:
        # Cache the new thread
        SESSION_THREAD_CACHE[session_id] = new_thread_id

        # Store in persistent storage
        _store_thread_in_storage(session_id, new_thread_id, config["channel_id"], thread_name, False, config, logger)

        logger.info("Created new text thread %s for session %s", new_thread_id, session_id)
        return new_thread_id

    logger.warning("Failed to create text thread for session %s", session_id)
    return None


def _create_new_thread(
    session_id: str, thread_name: str, config: Config, http_client: HTTPClient, logger: AstolfoLogger
) -> str | None:
    """Create a new thread for the session."""
    logger.debug("No existing thread found, creating new thread: %s", thread_name)

    try:
        if config["channel_type"] == "forum":
            return _handle_forum_channel_thread(config, logger)
        elif config["channel_type"] == "text":
            return _create_text_channel_thread(session_id, thread_name, config, http_client, logger)
        else:
            # Unknown channel type
            logger.warning("Unknown channel type: %s", config.get("channel_type"))  # type: ignore[unreachable]
            return None

    except DiscordAPIError:
        logger.exception("Discord API error creating thread for session %s", session_id)
    except ThreadManagementError:
        logger.exception("Thread management error for session %s", session_id)
    except ThreadStorageError:
        logger.exception("Thread storage error for session %s", session_id)
    except (OSError, ValueError, TypeError, RuntimeError):
        logger.exception("Unexpected error creating thread for session %s", session_id)

    return None


def get_or_create_thread(
    session_id: str, config: Config, http_client: HTTPClient, logger: AstolfoLogger
) -> str | None:
    """Get existing thread ID or create new thread for session using intelligent lookup.

    Priority sequence:
    1. Check in-memory cache
    2. Check persistent storage (ThreadStorage)
    3. Search Discord API for existing threads by name
    4. Create new thread if none found

    Returns thread_id if successful, None otherwise.
    """
    if not config["use_threads"]:
        return None

    # Step 1: Check in-memory cache first (fastest)
    thread_id = _check_cached_thread(session_id, config, http_client, logger)
    if thread_id:
        return thread_id

    # Step 2: Check persistent storage
    thread_id = _check_persistent_storage(session_id, config, http_client, logger)
    if thread_id:
        return thread_id

    # Step 3: Search Discord API for existing threads by name
    thread_name = f"{config['thread_prefix']} {session_id[:8]}"
    thread_id = _search_discord_for_thread(session_id, thread_name, config, http_client, logger)
    if thread_id:
        return thread_id

    # Step 4: Create new thread if none found
    return _create_new_thread(session_id, thread_name, config, http_client, logger)


# Export all public functions
__all__ = [
    'validate_thread_exists',
    'find_existing_thread_by_name',
    'ensure_thread_is_usable',
    'get_or_create_thread',
    '_check_thread_state',
    '_try_unarchive_thread',
]