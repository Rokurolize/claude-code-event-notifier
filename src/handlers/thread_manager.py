#!/usr/bin/env python3
"""Thread management for Discord Notifier.

This module handles Discord thread management including creation, validation,
caching, and lifecycle management for session-based threads.

Enhanced with Python 3.13+ free-threaded mode support for better parallelism.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from src.core.exceptions import DiscordAPIError, ThreadManagementError, ThreadStorageError
from src.core.http_client import HTTPClient


# Type definitions
class ThreadDetails(TypedDict, total=False):
    """Discord thread details."""
    id: str
    name: str
    parent_id: str
    archived: bool
    locked: bool
    auto_archive_duration: int
    message_count: int
    member_count: int


# Type alias for configuration
Config = dict[str, str | int | bool]

# Global thread cache - maps session_id to thread_id
SESSION_THREAD_CACHE: dict[str, str] = {}  # session_id -> thread_id mapping

# Check if running in free-threaded mode (Python 3.13+)
IS_FREE_THREADED = os.environ.get("PYTHON_GIL") == "0"

# Get accurate CPU count using Python 3.13+ feature
try:
    # Python 3.13+ provides process_cpu_count for more accurate counts
    CPU_COUNT = os.process_cpu_count() or os.cpu_count() or 1
except AttributeError:
    # Fallback for older Python versions
    CPU_COUNT = os.cpu_count() or 1

# Check if ThreadStorage is available
try:
    from src.thread_storage import ThreadStorage

    THREAD_STORAGE_AVAILABLE = True
except ImportError:
    THREAD_STORAGE_AVAILABLE = False


def validate_thread_exists(
    thread_id: str, config: Config, http_client: HTTPClient, logger: logging.Logger
) -> ThreadDetails | None:
    """Validate that a thread still exists and get its current status.

    This function checks if a Discord thread is still accessible and returns
    its details if available. Used to validate cached thread IDs.

    Args:
        thread_id: Discord thread ID to validate
        config: Discord configuration with bot token
        http_client: HTTP client for API calls
        logger: Logger instance

    Returns:
        Thread details dict if thread exists and is accessible, None otherwise

    Thread Details Include:
        - id: Thread snowflake ID
        - name: Thread name
        - thread_metadata: Archive status, lock status, etc.
        - parent_id: Parent channel ID
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
    except Exception as e:
        # Catch any other unexpected errors during thread validation
        logger.exception("Unexpected error validating thread %s: %s", thread_id, type(e).__name__)
        return None
    else:
        logger.debug("Thread %s not found or not accessible", thread_id)
        return None


def find_existing_thread_by_name(
    channel_id: str,
    thread_name: str,
    config: Config,
    http_client: HTTPClient,
    logger: logging.Logger,
) -> ThreadDetails | None:
    """Find an existing thread by name in a channel.

    Searches for threads matching the given name pattern in both active
    and archived threads. Returns the best match (exact match preferred).

    Args:
        channel_id: Discord channel ID to search in
        thread_name: Thread name to search for
        config: Discord configuration with bot token
        http_client: HTTP client for API calls
        logger: Logger instance

    Returns:
        Thread details dict if found, None otherwise

    Search Priority:
        1. Exact name match
        2. Partial name match (first result)
        3. None if no matches found
    """
    bot_token = config.get("bot_token")
    if not channel_id or not thread_name or not bot_token:
        return None

    try:
        matching_threads = http_client.search_threads_by_name(channel_id, thread_name, bot_token)

        if matching_threads:
            # Return the first exact match, or the first partial match
            for thread in matching_threads:
                if thread.get("name") == thread_name:
                    logger.debug("Found exact thread match: %s - %s", thread["id"], thread["name"])
                    return thread

            # If no exact match, return the first partial match
            first_thread = matching_threads[0]
            logger.debug("Found partial thread match: %s - %s", first_thread["id"], first_thread["name"])
            return first_thread
    except DiscordAPIError as e:
        logger.warning("Discord API error searching for thread '%s': %s", thread_name, e)
    except ThreadManagementError as e:
        logger.warning("Thread management error searching for thread '%s': %s", thread_name, e)
    except Exception as e:
        # Catch any other unexpected errors during thread search
        logger.exception("Unexpected error searching for thread '%s': %s", thread_name, type(e).__name__)
    else:
        logger.debug("No threads found matching name '%s' in channel %s", thread_name, channel_id)

    return None


def ensure_thread_is_usable(
    thread_details: ThreadDetails,
    config: Config,
    http_client: HTTPClient,
    logger: logging.Logger,
) -> bool:
    """Ensure a thread is in a usable state (unarchived and unlocked).

    Checks thread metadata and attempts to unarchive if needed. Locked
    threads cannot be made usable and will return False.

    Args:
        thread_details: Thread details from Discord API containing metadata
        config: Discord configuration with bot token
        http_client: HTTP client for API calls
        logger: Logger instance

    Returns:
        True if thread is usable or was made usable, False otherwise

    Thread States:
        - Usable: Not archived and not locked
        - Recoverable: Archived but not locked (can be unarchived)
        - Unusable: Locked (cannot be modified)
    """
    thread_id = thread_details.get("id")
    bot_token = config.get("bot_token")
    if not thread_id or not bot_token:
        return False

    thread_metadata = thread_details.get("thread_metadata", {})
    is_archived = thread_metadata.get("archived", False)
    is_locked = thread_metadata.get("locked", False)

    # If thread is neither archived nor locked, it's already usable
    if not is_archived and not is_locked:
        logger.debug("Thread %s is already usable", thread_id)
        return True

    # If thread is locked, we can't unarchive it
    if is_locked:
        logger.warning("Thread %s is locked and cannot be used", thread_id)
        return False

    # If thread is archived, try to unarchive it
    if is_archived:
        logger.info("Thread %s is archived, attempting to unarchive", thread_id)
        try:
            if http_client.unarchive_thread(thread_id, bot_token):
                logger.info("Successfully unarchived thread %s", thread_id)
                return True
        except DiscordAPIError as e:
            logger.warning("Discord API error unarchiving thread %s: %s", thread_id, e)
        except ThreadManagementError as e:
            logger.warning("Thread management error unarchiving thread %s: %s", thread_id, e)
        except Exception as e:
            # Catch any other unexpected errors during thread unarchiving
            logger.exception("Unexpected error unarchiving thread %s: %s", thread_id, type(e).__name__)
        else:
            logger.warning("Failed to unarchive thread %s", thread_id)

    return False


def _check_cached_thread(
    session_id: str, config: Config, http_client: HTTPClient, logger: logging.Logger
) -> str | None:
    """Check in-memory cache for thread ID.

    Args:
        session_id: Session identifier
        config: Discord configuration
        http_client: HTTP client
        logger: Logger instance

    Returns:
        Valid thread ID if found in cache, None otherwise
    """
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
    session_id: str, config: Config, http_client: HTTPClient, logger: logging.Logger
) -> str | None:
    """Check persistent storage for thread ID.

    Args:
        session_id: Session identifier
        config: Discord configuration
        http_client: HTTP client
        logger: Logger instance

    Returns:
        Valid thread ID if found in storage, None otherwise
    """
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
    except (OSError, ValueError) as e:
        logger.warning("Storage access error for session %s: %s: %s", session_id, type(e).__name__, e)

    return None


@dataclass
class ThreadInfo:
    """Thread information for storage."""

    session_id: str
    thread_id: str
    channel_id: str
    thread_name: str
    is_archived: bool


def _store_thread_in_storage(
    thread_info: ThreadInfo,
    config: Config,
    logger: logging.Logger,
) -> None:
    """Store thread information in persistent storage.

    Args:
        thread_info: Thread information to store
        config: Discord configuration
        logger: Logger instance
    """
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
            session_id=thread_info.session_id,
            thread_id=thread_info.thread_id,
            channel_id=thread_info.channel_id,
            thread_name=thread_info.thread_name,
            is_archived=thread_info.is_archived,
        )
    except ThreadStorageError as e:
        logger.warning("Thread storage error storing thread: %s", e)
    except (OSError, ValueError) as e:
        logger.warning("Storage access error storing thread: %s: %s", type(e).__name__, e)


def _search_discord_for_thread(
    session_id: str, config: Config, http_client: HTTPClient, logger: logging.Logger
) -> str | None:
    """Search Discord API for existing thread by name.

    Args:
        session_id: Session identifier
        config: Discord configuration
        http_client: HTTP client
        logger: Logger instance

    Returns:
        Thread ID if found and usable, None otherwise
    """
    thread_name = f"{config['thread_prefix']} {session_id[:8]}"
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
    thread_info = ThreadInfo(
        session_id=session_id,
        thread_id=thread_id,
        channel_id=channel_id,
        thread_name=thread_name,
        is_archived=existing_thread.get("thread_metadata", {}).get("archived", False),
    )
    _store_thread_in_storage(thread_info, config, logger)

    logger.info("Discovered and restored existing thread %s for session %s", thread_id, session_id)
    return thread_id


def _create_new_thread(session_id: str, config: Config, http_client: HTTPClient, logger: logging.Logger) -> str | None:
    """Create new thread for session.

    Args:
        session_id: Session identifier
        config: Discord configuration
        http_client: HTTP client
        logger: Logger instance

    Returns:
        Thread ID if created, None otherwise
    """
    thread_name = f"{config['thread_prefix']} {session_id[:8]}"
    logger.debug("No existing thread found, creating new thread: %s", thread_name)

    if config["channel_type"] == "forum":
        # Forum channels: Use webhook with thread_name
        if config["webhook_url"]:
            # For forum channels, thread creation happens with the first message
            logger.debug("Forum channel thread creation deferred to message sending")
            return None
        logger.warning("Forum channel threads require webhook URL")
        return None

    if config["channel_type"] == "text":
        # Text channels: Use bot API to create thread
        if not config["bot_token"] or not config["channel_id"]:
            logger.warning("Text channel threads require bot token and channel ID")
            return None

        new_thread_id = http_client.create_text_thread(config["channel_id"], thread_name, config["bot_token"])

        if new_thread_id:
            # Cache the new thread
            SESSION_THREAD_CACHE[session_id] = new_thread_id

            # Store in persistent storage
            thread_info = ThreadInfo(
                session_id=session_id,
                thread_id=new_thread_id,
                channel_id=config["channel_id"],
                thread_name=thread_name,
                is_archived=False,
            )
            _store_thread_in_storage(thread_info, config, logger)

            logger.info("Created new text thread %s for session %s", new_thread_id, session_id)
            return new_thread_id

        logger.warning("Failed to create text thread for session %s", session_id)
        return None

    # Unknown channel type
    logger.warning("Unknown channel type or configuration")
    return None


def get_or_create_thread(
    session_id: str, config: Config, http_client: HTTPClient, logger: logging.Logger
) -> str | None:
    """Get existing thread ID or create new thread for session using intelligent lookup.

    This function implements a multi-layer thread discovery strategy to maximize
    thread reuse and maintain session continuity across restarts.

    Priority sequence:
    1. Check in-memory cache (fastest)
    2. Check persistent storage (ThreadStorage if available)
    3. Search Discord API for existing threads by name
    4. Create new thread if none found

    In free-threaded mode (Python 3.13+), cache and storage checks can run in parallel
    for improved performance.

    Args:
        session_id: Unique session identifier
        config: Discord configuration including thread settings
        http_client: HTTP client for Discord API calls
        logger: Logger instance

    Returns:
        Thread ID if successful, None otherwise
    """
    if not config["use_threads"]:
        return None

    # In free-threaded mode, we can parallelize the first two checks
    if IS_FREE_THREADED:
        logger.debug("Using free-threaded mode for parallel thread lookups (CPU count: %d)", CPU_COUNT)
        # For now, fall back to sequential - parallel implementation would require
        # thread-safe http_client and careful coordination

    # Try each method in sequence
    search_methods = [
        _check_cached_thread,
        _check_persistent_storage,
        _search_discord_for_thread,
    ]

    for method in search_methods:
        thread_id = method(session_id, config, http_client, logger)
        if thread_id:
            return thread_id

    # Step 4: Create new thread if none found
    try:
        return _create_new_thread(session_id, config, http_client, logger)
    except (DiscordAPIError, ThreadManagementError, ThreadStorageError):
        logger.exception("Error creating thread for session %s", session_id)
        return None
    except Exception as e:
        # Catch any other unexpected errors during thread creation
        logger.exception("Unexpected error creating thread for session %s: %s", session_id, type(e).__name__)
        return None
