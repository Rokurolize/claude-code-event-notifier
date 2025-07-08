#!/usr/bin/env python3
"""Integration tests for intelligent thread management functionality.

This test suite validates the complete thread lifecycle including:
- Thread discovery and reuse across process restarts
- Persistent storage operations
- Thread validation and unarchiving
- Configuration handling for storage options
- Error handling and recovery scenarios

These tests require network access and a valid Discord configuration
to test actual API interactions.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src directory to Python path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from discord_notifier import (
    SESSION_THREAD_CACHE,
    ConfigLoader,
    HTTPClient,
    ThreadStorageError,
    ensure_thread_is_usable,
    find_existing_thread_by_name,
    get_or_create_thread,
    validate_thread_exists,
)
from thread_storage import ThreadRecord, ThreadStorage


class TestIntelligentThreadManagement(unittest.TestCase):
    """Test intelligent thread management functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clear session cache between tests
        SESSION_THREAD_CACHE.clear()

        # Create temporary directory for test database
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_db_path = self.test_dir / "test_threads.db"

        # Mock configuration
        self.config = {
            "use_threads": True,
            "channel_type": "text",
            "thread_prefix": "TestSession",
            "thread_storage_path": str(self.test_db_path),
            "thread_cleanup_days": 7,
            "bot_token": "test_bot_token",
            "channel_id": "123456789012345678",
            "webhook_url": None,
            "debug": True,
        }

        # Create mock logger
        self.mock_logger = MagicMock()

        # Create mock HTTP client
        self.mock_http_client = MagicMock(spec=HTTPClient)

        # Test session ID
        self.session_id = "test-session-12345678"
        self.thread_id = "987654321098765432"
        self.thread_name = f"{self.config['thread_prefix']} {self.session_id[:8]}"

    def tearDown(self):
        """Clean up test environment."""
        SESSION_THREAD_CACHE.clear()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_thread_storage_basic_operations(self):
        """Test basic ThreadStorage operations."""
        storage = ThreadStorage(db_path=self.test_db_path, cleanup_days=7)

        # Test storing a thread
        success = storage.store_thread(
            session_id=self.session_id,
            thread_id=self.thread_id,
            channel_id=self.config["channel_id"],
            thread_name=self.thread_name,
            is_archived=False,
        )
        self.assertTrue(success)

        # Test retrieving the thread
        record = storage.get_thread(self.session_id)
        self.assertIsNotNone(record)
        self.assertEqual(record.session_id, self.session_id)
        self.assertEqual(record.thread_id, self.thread_id)
        self.assertEqual(record.thread_name, self.thread_name)
        self.assertFalse(record.is_archived)

        # Test updating thread status
        success = storage.update_thread_status(self.session_id, is_archived=True)
        self.assertTrue(success)

        # Verify the update
        record = storage.get_thread(self.session_id)
        self.assertTrue(record.is_archived)

        # Test removing the thread
        success = storage.remove_thread(self.session_id)
        self.assertTrue(success)

        # Verify removal
        record = storage.get_thread(self.session_id)
        self.assertIsNone(record)

    def test_thread_storage_search_operations(self):
        """Test ThreadStorage search and query operations."""
        storage = ThreadStorage(db_path=self.test_db_path)

        # Store multiple threads
        test_threads = [
            ("session-1", "thread-1", "TestSession session-1"),
            ("session-2", "thread-2", "TestSession session-2"),
            ("session-3", "thread-3", "OtherPrefix session-3"),
        ]

        for session_id, thread_id, thread_name in test_threads:
            storage.store_thread(
                session_id=session_id,
                thread_id=thread_id,
                channel_id=self.config["channel_id"],
                thread_name=thread_name,
                is_archived=False,
            )

        # Test finding threads by channel
        threads = storage.find_threads_by_channel(self.config["channel_id"])
        self.assertEqual(len(threads), 3)

        # Test finding thread by name
        found_thread = storage.find_thread_by_name(self.config["channel_id"], "TestSession session-1")
        self.assertIsNotNone(found_thread)
        self.assertEqual(found_thread.session_id, "session-1")

        # Test finding non-existent thread by name
        not_found = storage.find_thread_by_name(self.config["channel_id"], "NonExistent thread")
        self.assertIsNone(not_found)

    def test_thread_storage_cleanup(self):
        """Test ThreadStorage cleanup functionality."""
        storage = ThreadStorage(db_path=self.test_db_path, cleanup_days=1)

        # Store a thread with old last_used timestamp
        storage.store_thread(
            session_id="old-session",
            thread_id="old-thread",
            channel_id=self.config["channel_id"],
            thread_name="Old Session old-sess",
            is_archived=False,
        )

        # Manually update the last_used timestamp to be old
        with sqlite3.connect(str(self.test_db_path)) as conn:
            old_date = datetime.now() - timedelta(days=2)
            conn.execute(
                "UPDATE thread_mappings SET last_used = ? WHERE session_id = ?",
                (old_date, "old-session"),
            )
            conn.commit()

        # Store a recent thread
        storage.store_thread(
            session_id="recent-session",
            thread_id="recent-thread",
            channel_id=self.config["channel_id"],
            thread_name="Recent Session recent-s",
            is_archived=False,
        )

        # Run cleanup
        removed_count = storage.cleanup_stale_threads()
        self.assertEqual(removed_count, 1)

        # Verify only recent thread remains
        old_record = storage.get_thread("old-session")
        recent_record = storage.get_thread("recent-session")

        self.assertIsNone(old_record)
        self.assertIsNotNone(recent_record)

    def test_thread_storage_stats(self):
        """Test ThreadStorage statistics functionality."""
        storage = ThreadStorage(db_path=self.test_db_path)

        # Store some test threads
        storage.store_thread("session-1", "thread-1", self.config["channel_id"], "Session 1", False)
        storage.store_thread("session-2", "thread-2", self.config["channel_id"], "Session 2", True)

        stats = storage.get_stats()

        self.assertEqual(stats["total_threads"], 2)
        self.assertEqual(stats["active_threads"], 1)
        self.assertEqual(stats["archived_threads"], 1)
        self.assertEqual(stats["db_path"], str(self.test_db_path))

    @patch("discord_notifier.ThreadStorage")
    def test_get_or_create_thread_cache_hit(self, mock_storage_class):
        """Test thread retrieval from in-memory cache."""
        # Pre-populate cache
        SESSION_THREAD_CACHE[self.session_id] = self.thread_id

        # Mock thread validation to succeed
        self.mock_http_client.get_thread_details.return_value = {
            "id": self.thread_id,
            "name": self.thread_name,
            "thread_metadata": {"archived": False, "locked": False},
        }

        result = get_or_create_thread(self.session_id, self.config, self.mock_http_client, self.mock_logger)

        self.assertEqual(result, self.thread_id)
        self.mock_http_client.get_thread_details.assert_called_once()
        # Storage should not be accessed for cache hits
        mock_storage_class.assert_not_called()

    @patch("discord_notifier.ThreadStorage")
    def test_get_or_create_thread_storage_recovery(self, mock_storage_class):
        """Test thread recovery from persistent storage."""
        # Mock storage to return a stored thread
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage

        stored_record = ThreadRecord(
            session_id=self.session_id,
            thread_id=self.thread_id,
            channel_id=self.config["channel_id"],
            thread_name=self.thread_name,
            created_at=datetime.now(),
            last_used=datetime.now(),
            is_archived=False,
        )
        mock_storage.get_thread.return_value = stored_record

        # Mock thread validation to succeed
        self.mock_http_client.get_thread_details.return_value = {
            "id": self.thread_id,
            "name": self.thread_name,
            "thread_metadata": {"archived": False, "locked": False},
        }

        result = get_or_create_thread(self.session_id, self.config, self.mock_http_client, self.mock_logger)

        self.assertEqual(result, self.thread_id)
        # Thread should be added to cache
        self.assertEqual(SESSION_THREAD_CACHE[self.session_id], self.thread_id)
        mock_storage.get_thread.assert_called_with(self.session_id)

    @patch("discord_notifier.ThreadStorage")
    def test_get_or_create_thread_api_discovery(self, mock_storage_class):
        """Test thread discovery via Discord API search."""
        # Mock storage to return None (no stored thread)
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_storage.get_thread.return_value = None

        # Mock Discord API to find existing thread
        self.mock_http_client.search_threads_by_name.return_value = [
            {
                "id": self.thread_id,
                "name": self.thread_name,
                "thread_metadata": {"archived": False, "locked": False},
            }
        ]

        result = get_or_create_thread(self.session_id, self.config, self.mock_http_client, self.mock_logger)

        self.assertEqual(result, self.thread_id)
        # Thread should be stored for future use
        mock_storage.store_thread.assert_called_once()
        # Thread should be cached
        self.assertEqual(SESSION_THREAD_CACHE[self.session_id], self.thread_id)

    @patch("discord_notifier.ThreadStorage")
    def test_get_or_create_thread_creation(self, mock_storage_class):
        """Test new thread creation when none exists."""
        # Mock storage to return None
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_storage.get_thread.return_value = None

        # Mock Discord API to find no existing threads
        self.mock_http_client.search_threads_by_name.return_value = []

        # Mock thread creation to succeed
        self.mock_http_client.create_text_thread.return_value = self.thread_id

        result = get_or_create_thread(self.session_id, self.config, self.mock_http_client, self.mock_logger)

        self.assertEqual(result, self.thread_id)
        # Thread creation should be called
        self.mock_http_client.create_text_thread.assert_called_once_with(
            self.config["channel_id"], self.thread_name, self.config["bot_token"]
        )
        # New thread should be stored
        mock_storage.store_thread.assert_called_once()
        # Thread should be cached
        self.assertEqual(SESSION_THREAD_CACHE[self.session_id], self.thread_id)

    def test_validate_thread_exists_success(self):
        """Test successful thread validation."""
        self.mock_http_client.get_thread_details.return_value = {
            "id": self.thread_id,
            "name": self.thread_name,
            "thread_metadata": {"archived": False, "locked": False},
        }

        result = validate_thread_exists(self.thread_id, self.config, self.mock_http_client, self.mock_logger)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], self.thread_id)

    def test_validate_thread_exists_not_found(self):
        """Test thread validation when thread doesn't exist."""
        self.mock_http_client.get_thread_details.return_value = None

        result = validate_thread_exists(self.thread_id, self.config, self.mock_http_client, self.mock_logger)

        self.assertIsNone(result)

    def test_find_existing_thread_by_name_exact_match(self):
        """Test finding thread by exact name match."""
        self.mock_http_client.search_threads_by_name.return_value = [
            {
                "id": self.thread_id,
                "name": self.thread_name,
                "thread_metadata": {"archived": False, "locked": False},
            },
            {
                "id": "other-thread-id",
                "name": "TestSession other-name",
                "thread_metadata": {"archived": False, "locked": False},
            },
        ]

        result = find_existing_thread_by_name(
            self.config["channel_id"],
            self.thread_name,
            self.config,
            self.mock_http_client,
            self.mock_logger,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], self.thread_id)
        self.assertEqual(result["name"], self.thread_name)

    def test_ensure_thread_is_usable_already_active(self):
        """Test ensuring thread usability when already active."""
        thread_details = {
            "id": self.thread_id,
            "thread_metadata": {"archived": False, "locked": False},
        }

        result = ensure_thread_is_usable(thread_details, self.config, self.mock_http_client, self.mock_logger)

        self.assertTrue(result)
        # Should not attempt to unarchive
        self.mock_http_client.unarchive_thread.assert_not_called()

    def test_ensure_thread_is_usable_unarchive_success(self):
        """Test successful thread unarchiving."""
        thread_details = {
            "id": self.thread_id,
            "thread_metadata": {"archived": True, "locked": False},
        }

        self.mock_http_client.unarchive_thread.return_value = True

        result = ensure_thread_is_usable(thread_details, self.config, self.mock_http_client, self.mock_logger)

        self.assertTrue(result)
        self.mock_http_client.unarchive_thread.assert_called_once_with(self.thread_id, self.config["bot_token"])

    def test_ensure_thread_is_usable_locked_thread(self):
        """Test handling of locked threads."""
        thread_details = {
            "id": self.thread_id,
            "thread_metadata": {"archived": False, "locked": True},
        }

        result = ensure_thread_is_usable(thread_details, self.config, self.mock_http_client, self.mock_logger)

        self.assertFalse(result)
        # Should not attempt to unarchive locked threads
        self.mock_http_client.unarchive_thread.assert_not_called()

    def test_configuration_loading_storage_options(self):
        """Test loading of new storage configuration options."""
        # Test environment variable override
        with patch.dict(
            os.environ,
            {
                "DISCORD_THREAD_STORAGE_PATH": "/custom/path/threads.db",
                "DISCORD_THREAD_CLEANUP_DAYS": "14",
            },
        ):
            config = ConfigLoader.load()

            self.assertEqual(config["thread_storage_path"], "/custom/path/threads.db")
            self.assertEqual(config["thread_cleanup_days"], 14)

    def test_configuration_loading_invalid_cleanup_days(self):
        """Test handling of invalid cleanup days configuration."""
        with patch.dict(os.environ, {"DISCORD_THREAD_CLEANUP_DAYS": "invalid"}):
            config = ConfigLoader.load()

            # Should keep default value
            self.assertEqual(config["thread_cleanup_days"], 30)

    @patch("discord_notifier.ThreadStorage")
    def test_error_handling_storage_failure(self, mock_storage_class):
        """Test error handling when storage operations fail."""
        # Mock storage to raise an exception
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_storage.get_thread.side_effect = ThreadStorageError("Database error", operation="retrieve")

        result = get_or_create_thread(self.session_id, self.config, self.mock_http_client, self.mock_logger)

        # Should continue with API search despite storage error
        # (assuming no threads found and creation succeeds)
        self.mock_http_client.search_threads_by_name.assert_called()

    def test_invalid_configuration_handling(self):
        """Test handling of invalid configuration scenarios."""
        # Test with threads disabled
        config_no_threads = self.config.copy()
        config_no_threads["use_threads"] = False

        result = get_or_create_thread(self.session_id, config_no_threads, self.mock_http_client, self.mock_logger)

        self.assertIsNone(result)

        # Test with missing bot token
        config_no_token = self.config.copy()
        config_no_token["bot_token"] = None

        result = get_or_create_thread(self.session_id, config_no_token, self.mock_http_client, self.mock_logger)

        self.assertIsNone(result)


if __name__ == "__main__":
    # Check if Discord configuration is available for integration testing
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    if not env_file.exists():
        print("Warning: Discord configuration not found. Some tests may be skipped.")
        print(f"Create {env_file} for full integration testing.")

    unittest.main(verbosity=2)
