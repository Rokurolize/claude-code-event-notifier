#!/usr/bin/env python3
"""Thread Storage Management for Discord Notifier.

This module provides persistent storage for Discord thread mappings to prevent
duplicate thread creation across process restarts. Uses SQLite for lightweight,
zero-dependency storage.
"""

import logging
import sqlite3
import threading
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import NamedTuple, TypedDict

try:
    from src.type_guards import is_valid_snowflake
except ImportError:
    from type_guards import is_valid_snowflake


class ThreadStats(TypedDict):
    """Storage statistics structure."""

    total_threads: int
    archived_threads: int
    active_threads: int
    oldest_thread: str | None
    most_recent_use: str | None
    db_path: str
    cleanup_days: int


class ThreadStatsError(TypedDict):
    """Storage statistics error structure."""

    error: str
    db_path: str


class ThreadRecord(NamedTuple):
    """Represents a stored thread record."""

    session_id: str
    thread_id: str
    channel_id: str
    thread_name: str
    created_at: datetime
    last_used: datetime
    is_archived: bool


# Import ThreadStorageError from discord_notifier to maintain consistency
try:
    from src.discord_notifier import ThreadStorageError
except ImportError:
    # Fallback definition if import fails
    class ThreadStorageError(Exception):
        """Base exception for thread storage operations."""

        def __init__(self, message: str, operation: str | None = None):
            super().__init__(message)
            self.operation = operation


class ThreadStorage:
    """SQLite-based persistent storage for Discord thread mappings.

    Provides thread-safe operations for storing and retrieving session-to-thread
    mappings with automatic cleanup of stale records.
    """

    def __init__(self, db_path: Path | None = None, cleanup_days: int = 30):
        """Initialize thread storage.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.claude/hooks/threads.db
            cleanup_days: Number of days after which unused threads are considered stale
        """
        self.db_path = db_path or (Path.home() / ".claude" / "hooks" / "threads.db")
        self.cleanup_days = cleanup_days
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS thread_mappings (
                        session_id TEXT PRIMARY KEY,
                        thread_id TEXT NOT NULL,
                        channel_id TEXT NOT NULL,
                        thread_name TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        last_used TIMESTAMP NOT NULL,
                        is_archived BOOLEAN DEFAULT FALSE
                    )
                """)

                # Create indexes for efficient lookups
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_thread_id
                    ON thread_mappings(thread_id)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_channel_id
                    ON thread_mappings(channel_id)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_last_used
                    ON thread_mappings(last_used)
                """)

                conn.commit()
                self._logger.debug("Thread storage database initialized: %s", self.db_path)

        except sqlite3.Error as e:
            raise ThreadStorageError(f"Failed to initialize database: {e}") from e

    def store_thread(
        self,
        session_id: str,
        thread_id: str,
        channel_id: str,
        thread_name: str,
        is_archived: bool = False,
    ) -> bool:
        """Store a thread mapping in the database.

        Args:
            session_id: Unique session identifier
            thread_id: Discord thread ID (snowflake)
            channel_id: Discord channel ID (snowflake)
            thread_name: Human-readable thread name
            is_archived: Whether the thread is archived

        Returns:
            True if stored successfully, False otherwise
        """
        if not session_id or not thread_id or not channel_id:
            self._logger.warning("Invalid parameters for thread storage")
            return False

        if not is_valid_snowflake(thread_id) or not is_valid_snowflake(channel_id):
            self._logger.warning("Invalid Discord snowflake format")
            return False

        with self._lock:
            try:
                now = datetime.now(UTC)
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO thread_mappings
                        (session_id, thread_id, channel_id, thread_name, created_at, last_used, is_archived)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            session_id,
                            thread_id,
                            channel_id,
                            thread_name,
                            now,
                            now,
                            is_archived,
                        ),
                    )

                    conn.commit()
                    self._logger.debug("Stored thread mapping: %s -> %s", session_id, thread_id)
                    return True

            except sqlite3.Error:
                self._logger.exception("Failed to store thread mapping")
                return False

    def get_thread(self, session_id: str) -> ThreadRecord | None:
        """Retrieve a thread record by session ID.

        Args:
            session_id: Unique session identifier

        Returns:
            ThreadRecord if found, None otherwise
        """
        if not session_id:
            return None

        with self._lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        """
                        SELECT session_id, thread_id, channel_id, thread_name,
                               created_at, last_used, is_archived
                        FROM thread_mappings
                        WHERE session_id = ?
                    """,
                        (session_id,),
                    )

                    row = cursor.fetchone()
                    if row:
                        # Update last_used timestamp
                        now = datetime.now(UTC)
                        conn.execute(
                            """
                            UPDATE thread_mappings
                            SET last_used = ?
                            WHERE session_id = ?
                        """,
                            (now, session_id),
                        )
                        conn.commit()

                        return ThreadRecord(
                            session_id=row["session_id"],
                            thread_id=row["thread_id"],
                            channel_id=row["channel_id"],
                            thread_name=row["thread_name"],
                            created_at=datetime.fromisoformat(row["created_at"]),
                            last_used=now,
                            is_archived=bool(row["is_archived"]),
                        )
                    return None

            except sqlite3.Error:
                self._logger.exception("Failed to retrieve thread mapping")
                return None

    def update_thread_status(self, session_id: str, is_archived: bool) -> bool:
        """Update the archived status of a thread.

        Args:
            session_id: Unique session identifier
            is_archived: New archived status

        Returns:
            True if updated successfully, False otherwise
        """
        if not session_id:
            return False

        with self._lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute(
                        """
                        UPDATE thread_mappings
                        SET is_archived = ?, last_used = ?
                        WHERE session_id = ?
                    """,
                        (is_archived, datetime.now(UTC), session_id),
                    )

                    conn.commit()
                    updated = cursor.rowcount > 0

                    if updated:
                        self._logger.debug("Updated thread status: %s -> archived=%s", session_id, is_archived)

                    return updated

            except sqlite3.Error:
                self._logger.exception("Failed to update thread status")
                return False

    def remove_thread(self, session_id: str) -> bool:
        """Remove a thread mapping from storage.

        Args:
            session_id: Unique session identifier

        Returns:
            True if removed successfully, False otherwise
        """
        if not session_id:
            return False

        with self._lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute(
                        """
                        DELETE FROM thread_mappings
                        WHERE session_id = ?
                    """,
                        (session_id,),
                    )

                    conn.commit()
                    removed = cursor.rowcount > 0

                    if removed:
                        self._logger.debug("Removed thread mapping: %s", session_id)

                    return removed

            except sqlite3.Error:
                self._logger.exception("Failed to remove thread mapping")
                return False

    def find_threads_by_channel(self, channel_id: str) -> list[ThreadRecord]:
        """Find all threads in a specific channel.

        Args:
            channel_id: Discord channel ID (snowflake)

        Returns:
            List of ThreadRecord objects
        """
        if not channel_id or not is_valid_snowflake(channel_id):
            return []

        with self._lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        """
                        SELECT session_id, thread_id, channel_id, thread_name,
                               created_at, last_used, is_archived
                        FROM thread_mappings
                        WHERE channel_id = ?
                        ORDER BY last_used DESC
                    """,
                        (channel_id,),
                    )

                    return [
                        ThreadRecord(
                            session_id=row["session_id"],
                            thread_id=row["thread_id"],
                            channel_id=row["channel_id"],
                            thread_name=row["thread_name"],
                            created_at=datetime.fromisoformat(row["created_at"]),
                            last_used=datetime.fromisoformat(row["last_used"]),
                            is_archived=bool(row["is_archived"]),
                        )
                        for row in cursor.fetchall()
                    ]

            except sqlite3.Error:
                self._logger.exception("Failed to find threads by channel")
                return []

    def find_thread_by_name(self, channel_id: str, thread_name: str) -> ThreadRecord | None:
        """Find a thread by its name within a specific channel.

        Args:
            channel_id: Discord channel ID (snowflake)
            thread_name: Thread name to search for

        Returns:
            ThreadRecord if found, None otherwise
        """
        if not channel_id or not thread_name:
            return None

        if not is_valid_snowflake(channel_id):
            return None

        with self._lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute(
                        """
                        SELECT session_id, thread_id, channel_id, thread_name,
                               created_at, last_used, is_archived
                        FROM thread_mappings
                        WHERE channel_id = ? AND thread_name = ?
                        ORDER BY last_used DESC
                        LIMIT 1
                    """,
                        (channel_id, thread_name),
                    )

                    row = cursor.fetchone()
                    if row:
                        return ThreadRecord(
                            session_id=row["session_id"],
                            thread_id=row["thread_id"],
                            channel_id=row["channel_id"],
                            thread_name=row["thread_name"],
                            created_at=datetime.fromisoformat(row["created_at"]),
                            last_used=datetime.fromisoformat(row["last_used"]),
                            is_archived=bool(row["is_archived"]),
                        )

                    return None

            except sqlite3.Error:
                self._logger.exception("Failed to find thread by name")
                return None

    def cleanup_stale_threads(self) -> int:
        """Remove stale thread mappings that haven't been used recently.

        Returns:
            Number of records removed
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=self.cleanup_days)

        with self._lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute(
                        """
                        DELETE FROM thread_mappings
                        WHERE last_used < ?
                    """,
                        (cutoff_date,),
                    )

                    conn.commit()
                    removed_count = cursor.rowcount

                    if removed_count > 0:
                        self._logger.info("Cleaned up %s stale thread mappings", removed_count)

                    return removed_count

            except sqlite3.Error:
                self._logger.exception("Failed to cleanup stale threads")
                return 0

    def get_stats(self) -> ThreadStats | ThreadStatsError:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        with self._lock:
            try:
                with sqlite3.connect(str(self.db_path)) as conn:
                    cursor = conn.execute("""
                        SELECT
                            COUNT(*) as total_threads,
                            COUNT(CASE WHEN is_archived = 1 THEN 1 END) as archived_threads,
                            COUNT(CASE WHEN is_archived = 0 THEN 1 END) as active_threads,
                            MIN(created_at) as oldest_thread,
                            MAX(last_used) as most_recent_use
                        FROM thread_mappings
                    """)

                    row = cursor.fetchone()
                    if row:
                        return ThreadStats(
                            total_threads=row[0],
                            archived_threads=row[1],
                            active_threads=row[2],
                            oldest_thread=row[3],
                            most_recent_use=row[4],
                            db_path=str(self.db_path),
                            cleanup_days=self.cleanup_days,
                        )

                    return ThreadStats(
                        total_threads=0,
                        archived_threads=0,
                        active_threads=0,
                        oldest_thread=None,
                        most_recent_use=None,
                        db_path=str(self.db_path),
                        cleanup_days=self.cleanup_days,
                    )

            except sqlite3.Error as e:
                self._logger.exception("Failed to get storage stats")
                return ThreadStatsError(error=str(e), db_path=str(self.db_path))

    def close(self) -> None:
        """Close the storage connection."""
        try:
            self._logger.debug("Thread storage closed")
        except Exception:
            # Catch any logging errors during close
            pass
