#!/usr/bin/env python3
"""Test Thread Lifecycle Management.

This module provides comprehensive tests for Discord thread lifecycle
management, including thread creation, lookup, persistence, cleanup,
and integration with the thread management system.
"""

import asyncio
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.thread_storage import ThreadStorage
from src.handlers.thread_manager import ThreadManager
from src.core.http_client import HTTPClient
from src.exceptions import ThreadError, HTTPError


class TestThreadLifecycle(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord thread lifecycle management."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration for threads
        self.test_config = {
            "bot_token": "Bot test_token_123456789",
            "channel_id": "123456789012345678",
            "use_threads": True,
            "enabled_events": ["PreToolUse", "PostToolUse", "Stop"],
            "debug": True
        }
        
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # Test thread data
        self.test_session_id = "test_session_001"
        self.test_channel_id = "123456789012345678"
        self.test_thread_id = "987654321098765432"
        self.test_thread_name = "Claude Code Session: test_session_001"
        
        # Mock thread response data
        self.mock_thread_data = {
            "id": self.test_thread_id,
            "type": 11,  # PUBLIC_THREAD
            "name": self.test_thread_name,
            "parent_id": self.test_channel_id,
            "owner_id": "bot_user_id",
            "guild_id": "555666777888999000",
            "thread_metadata": {
                "archived": False,
                "archive_timestamp": None,
                "auto_archive_duration": 1440,
                "locked": False,
                "invitable": True
            },
            "member_count": 1,
            "message_count": 0,
            "rate_limit_per_user": 0,
            "created_at": "2025-07-12T22:00:00.000Z"
        }
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Remove temporary database
        try:
            Path(self.db_path).unlink()
        except FileNotFoundError:
            pass
    
    async def test_thread_creation_successful(self) -> None:
        """Test successful thread creation."""
        with patch('src.handlers.thread_manager.ThreadManager') as mock_thread_manager:
            mock_instance = AsyncMock()
            mock_thread_manager.return_value = mock_instance
            
            # Configure successful thread creation
            mock_instance.create_thread.return_value = self.mock_thread_data
            
            thread_manager = ThreadManager(self.test_config, self.logger)
            
            # Test thread creation
            thread_result = await thread_manager.create_thread(
                session_id=self.test_session_id,
                channel_id=self.test_channel_id
            )
            
            # Verify thread creation
            self.assertIsNotNone(thread_result)
            self.assertEqual(thread_result["id"], self.test_thread_id)
            self.assertEqual(thread_result["name"], self.test_thread_name)
            self.assertEqual(thread_result["parent_id"], self.test_channel_id)
            self.assertEqual(thread_result["type"], 11)  # PUBLIC_THREAD
            self.assertFalse(thread_result["thread_metadata"]["archived"])
            
            # Verify thread manager was called correctly
            mock_instance.create_thread.assert_called_once()
    
    async def test_thread_creation_with_custom_name(self) -> None:
        """Test thread creation with custom thread name."""
        with patch('src.handlers.thread_manager.ThreadManager') as mock_thread_manager:
            mock_instance = AsyncMock()
            mock_thread_manager.return_value = mock_instance
            
            custom_name = "Custom Thread Name"
            custom_thread_data = self.mock_thread_data.copy()
            custom_thread_data["name"] = custom_name
            
            mock_instance.create_thread.return_value = custom_thread_data
            
            thread_manager = ThreadManager(self.test_config, self.logger)
            
            # Test thread creation with custom name
            thread_result = await thread_manager.create_thread(
                session_id=self.test_session_id,
                channel_id=self.test_channel_id,
                thread_name=custom_name
            )
            
            # Verify custom name was used
            self.assertEqual(thread_result["name"], custom_name)
    
    async def test_thread_lookup_by_session_id(self) -> None:
        """Test thread lookup by session ID."""
        with patch('src.thread_storage.ThreadStorage') as mock_storage:
            mock_storage_instance = MagicMock()
            mock_storage.return_value = mock_storage_instance
            
            # Configure thread lookup response
            mock_storage_instance.get_thread.return_value = {
                "session_id": self.test_session_id,
                "thread_id": self.test_thread_id,
                "channel_id": self.test_channel_id,
                "thread_name": self.test_thread_name,
                "created_at": "2025-07-12T22:00:00Z",
                "last_used": "2025-07-12T22:05:00Z",
                "archived": False
            }
            
            thread_storage = ThreadStorage(self.db_path)
            
            # Test thread lookup
            thread_info = thread_storage.get_thread(self.test_session_id)
            
            # Verify lookup result
            self.assertIsNotNone(thread_info)
            self.assertEqual(thread_info["session_id"], self.test_session_id)
            self.assertEqual(thread_info["thread_id"], self.test_thread_id)
            self.assertEqual(thread_info["channel_id"], self.test_channel_id)
            self.assertFalse(thread_info["archived"])
            
            # Verify storage was called correctly
            mock_storage_instance.get_thread.assert_called_once_with(self.test_session_id)
    
    async def test_thread_persistence_to_database(self) -> None:
        """Test thread persistence to SQLite database."""
        # Create real thread storage for testing persistence
        thread_storage = ThreadStorage(self.db_path)
        
        # Test thread data to persist
        thread_data = {
            "session_id": self.test_session_id,
            "thread_id": self.test_thread_id,
            "channel_id": self.test_channel_id,
            "thread_name": self.test_thread_name,
            "created_at": "2025-07-12T22:00:00Z",
            "last_used": "2025-07-12T22:00:00Z",
            "archived": False
        }
        
        # Store thread in database
        thread_storage.store_thread(
            session_id=thread_data["session_id"],
            thread_id=thread_data["thread_id"],
            channel_id=thread_data["channel_id"],
            thread_name=thread_data["thread_name"]
        )
        
        # Retrieve thread from database
        retrieved_thread = thread_storage.get_thread(self.test_session_id)
        
        # Verify persistence
        self.assertIsNotNone(retrieved_thread)
        self.assertEqual(retrieved_thread["session_id"], thread_data["session_id"])
        self.assertEqual(retrieved_thread["thread_id"], thread_data["thread_id"])
        self.assertEqual(retrieved_thread["channel_id"], thread_data["channel_id"])
        self.assertEqual(retrieved_thread["thread_name"], thread_data["thread_name"])
        
        # Verify database structure
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='threads'")
            table_exists = cursor.fetchone()
            self.assertIsNotNone(table_exists)
            
            # Verify thread record exists
            cursor.execute("SELECT * FROM threads WHERE session_id = ?", (self.test_session_id,))
            db_record = cursor.fetchone()
            self.assertIsNotNone(db_record)
    
    async def test_thread_update_last_used(self) -> None:
        """Test updating thread last_used timestamp."""
        thread_storage = ThreadStorage(self.db_path)
        
        # Store initial thread
        thread_storage.store_thread(
            session_id=self.test_session_id,
            thread_id=self.test_thread_id,
            channel_id=self.test_channel_id,
            thread_name=self.test_thread_name
        )
        
        # Get initial last_used time
        initial_thread = thread_storage.get_thread(self.test_session_id)
        initial_last_used = initial_thread["last_used"]
        
        # Wait a moment and update
        await asyncio.sleep(0.1)
        thread_storage.update_last_used(self.test_session_id)
        
        # Get updated thread
        updated_thread = thread_storage.get_thread(self.test_session_id)
        updated_last_used = updated_thread["last_used"]
        
        # Verify last_used was updated
        self.assertNotEqual(initial_last_used, updated_last_used)
        self.assertGreater(updated_last_used, initial_last_used)
    
    async def test_thread_archival_handling(self) -> None:
        """Test thread archival and unarchival handling."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Mock archived thread response
            archived_thread_data = self.mock_thread_data.copy()
            archived_thread_data["thread_metadata"]["archived"] = True
            archived_thread_data["thread_metadata"]["archive_timestamp"] = "2025-07-12T23:00:00.000Z"
            
            # Mock unarchive response
            unarchived_thread_data = self.mock_thread_data.copy()
            unarchived_thread_data["thread_metadata"]["archived"] = False
            unarchived_thread_data["thread_metadata"]["archive_timestamp"] = None
            
            # Configure responses
            mock_instance.get_thread.return_value = archived_thread_data
            mock_instance.unarchive_thread.return_value = unarchived_thread_data
            
            client = HTTPClient(self.test_config, self.logger)
            
            # Test getting archived thread
            thread_info = await client.get_thread(self.test_thread_id)
            self.assertTrue(thread_info["thread_metadata"]["archived"])
            
            # Test unarchiving thread
            unarchived_info = await client.unarchive_thread(self.test_thread_id)
            self.assertFalse(unarchived_info["thread_metadata"]["archived"])
            self.assertIsNone(unarchived_info["thread_metadata"]["archive_timestamp"])
            
            # Verify API calls
            mock_instance.get_thread.assert_called_once_with(self.test_thread_id)
            mock_instance.unarchive_thread.assert_called_once_with(self.test_thread_id)
    
    async def test_thread_cleanup_old_threads(self) -> None:
        """Test cleanup of old unused threads."""
        thread_storage = ThreadStorage(self.db_path)
        
        # Create multiple test threads with different ages
        test_threads = [
            {
                "session_id": "old_session_1",
                "thread_id": "thread_001",
                "channel_id": self.test_channel_id,
                "thread_name": "Old Thread 1",
                "age_days": 8  # Older than 7 days
            },
            {
                "session_id": "recent_session_1",
                "thread_id": "thread_002", 
                "channel_id": self.test_channel_id,
                "thread_name": "Recent Thread 1",
                "age_days": 3  # Recent
            },
            {
                "session_id": "old_session_2",
                "thread_id": "thread_003",
                "channel_id": self.test_channel_id,
                "thread_name": "Old Thread 2",
                "age_days": 15  # Very old
            }
        ]
        
        # Store threads with simulated timestamps
        current_time = time.time()
        for thread in test_threads:
            thread_storage.store_thread(
                session_id=thread["session_id"],
                thread_id=thread["thread_id"],
                channel_id=thread["channel_id"],
                thread_name=thread["thread_name"]
            )
            
            # Manually update timestamp for testing
            old_timestamp = current_time - (thread["age_days"] * 24 * 60 * 60)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE threads SET last_used = ? WHERE session_id = ?",
                    (old_timestamp, thread["session_id"])
                )
                conn.commit()
        
        # Test cleanup (simulate cleanup for threads older than 7 days)
        cleanup_threshold = current_time - (7 * 24 * 60 * 60)
        threads_before_cleanup = thread_storage.get_all_threads()
        
        # Perform cleanup
        thread_storage.cleanup_old_threads(days=7)
        
        threads_after_cleanup = thread_storage.get_all_threads()
        
        # Verify cleanup results
        self.assertEqual(len(threads_before_cleanup), 3)
        self.assertEqual(len(threads_after_cleanup), 1)  # Only recent thread should remain
        
        # Verify the remaining thread is the recent one
        remaining_thread = threads_after_cleanup[0]
        self.assertEqual(remaining_thread["session_id"], "recent_session_1")
    
    async def test_thread_error_handling(self) -> None:
        """Test thread operation error handling."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Test different error scenarios
            error_scenarios = [
                {
                    "name": "thread_not_found",
                    "error": HTTPError("Thread not found", status_code=404),
                    "operation": "get_thread"
                },
                {
                    "name": "insufficient_permissions",
                    "error": HTTPError("Missing permissions", status_code=403),
                    "operation": "create_thread"
                },
                {
                    "name": "rate_limited",
                    "error": HTTPError("Rate limited", status_code=429),
                    "operation": "unarchive_thread"
                }
            ]
            
            client = HTTPClient(self.test_config, self.logger)
            
            for scenario in error_scenarios:
                with self.subTest(scenario=scenario["name"]):
                    # Configure error
                    if scenario["operation"] == "get_thread":
                        mock_instance.get_thread.side_effect = scenario["error"]
                    elif scenario["operation"] == "create_thread":
                        mock_instance.create_thread.side_effect = scenario["error"]
                    elif scenario["operation"] == "unarchive_thread":
                        mock_instance.unarchive_thread.side_effect = scenario["error"]
                    
                    # Test error handling
                    with self.assertRaises(HTTPError) as context:
                        if scenario["operation"] == "get_thread":
                            await client.get_thread(self.test_thread_id)
                        elif scenario["operation"] == "create_thread":
                            await client.create_thread("Test Thread", self.test_channel_id)
                        elif scenario["operation"] == "unarchive_thread":
                            await client.unarchive_thread(self.test_thread_id)
                    
                    # Verify error details
                    error = context.exception
                    self.assertEqual(error.status_code, scenario["error"].status_code)
    
    async def test_thread_concurrent_operations(self) -> None:
        """Test concurrent thread operations."""
        thread_storage = ThreadStorage(self.db_path)
        
        # Test concurrent thread storage
        async def store_thread_task(session_id: str, thread_id: str):
            try:
                thread_storage.store_thread(
                    session_id=session_id,
                    thread_id=thread_id,
                    channel_id=self.test_channel_id,
                    thread_name=f"Thread for {session_id}"
                )
                return True
            except Exception:
                return False
        
        # Create concurrent storage tasks
        concurrent_count = 5
        tasks = []
        
        for i in range(concurrent_count):
            session_id = f"concurrent_session_{i}"
            thread_id = f"concurrent_thread_{i}"
            task = asyncio.create_task(store_thread_task(session_id, thread_id))
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations succeeded
        successful_ops = sum(1 for r in results if r is True)
        self.assertEqual(successful_ops, concurrent_count)
        
        # Verify all threads were stored
        all_threads = thread_storage.get_all_threads()
        self.assertGreaterEqual(len(all_threads), concurrent_count)
        
        # Verify no data corruption
        for i in range(concurrent_count):
            session_id = f"concurrent_session_{i}"
            thread_info = thread_storage.get_thread(session_id)
            self.assertIsNotNone(thread_info)
            self.assertEqual(thread_info["session_id"], session_id)
    
    async def test_thread_search_and_filtering(self) -> None:
        """Test thread search and filtering capabilities."""
        thread_storage = ThreadStorage(self.db_path)
        
        # Create test threads with different properties
        test_threads = [
            {
                "session_id": "session_alpha",
                "thread_id": "thread_alpha",
                "thread_name": "Alpha Test Thread",
                "channel_id": "111111111111111111"
            },
            {
                "session_id": "session_beta",
                "thread_id": "thread_beta",
                "thread_name": "Beta Test Thread",
                "channel_id": "222222222222222222"
            },
            {
                "session_id": "session_gamma",
                "thread_id": "thread_gamma",
                "thread_name": "Gamma Test Thread",
                "channel_id": "111111111111111111"  # Same channel as alpha
            }
        ]
        
        # Store all test threads
        for thread in test_threads:
            thread_storage.store_thread(
                session_id=thread["session_id"],
                thread_id=thread["thread_id"],
                channel_id=thread["channel_id"],
                thread_name=thread["thread_name"]
            )
        
        # Test filtering by channel ID
        channel_1_threads = thread_storage.get_threads_by_channel("111111111111111111")
        channel_2_threads = thread_storage.get_threads_by_channel("222222222222222222")
        
        # Verify filtering results
        self.assertEqual(len(channel_1_threads), 2)  # Alpha and Gamma
        self.assertEqual(len(channel_2_threads), 1)   # Beta only
        
        # Test search by thread name pattern
        alpha_threads = thread_storage.search_threads_by_name("Alpha")
        beta_threads = thread_storage.search_threads_by_name("Beta")
        test_threads_all = thread_storage.search_threads_by_name("Test")
        
        # Verify search results
        self.assertEqual(len(alpha_threads), 1)
        self.assertEqual(len(beta_threads), 1)
        self.assertEqual(len(test_threads_all), 3)  # All contain "Test"
    
    async def test_thread_integration_workflow(self) -> None:
        """Test complete thread integration workflow."""
        with patch('src.handlers.thread_manager.ThreadManager') as mock_thread_manager, \
             patch('src.core.http_client.HTTPClient') as mock_http_client:
            
            # Setup mocks
            mock_tm_instance = AsyncMock()
            mock_thread_manager.return_value = mock_tm_instance
            
            mock_http_instance = AsyncMock()
            mock_http_client.return_value = mock_http_instance
            
            # Configure workflow responses
            mock_tm_instance.get_or_create_thread.return_value = self.mock_thread_data
            mock_http_instance.send_message_to_thread.return_value = {
                "id": "message_123",
                "content": "Thread workflow test message",
                "channel_id": self.test_thread_id,
                "timestamp": "2025-07-12T22:00:00.000Z"
            }
            
            # Execute integration workflow
            thread_manager = ThreadManager(self.test_config, self.logger)
            http_client = HTTPClient(self.test_config, self.logger)
            
            # 1. Get or create thread for session
            thread_info = await thread_manager.get_or_create_thread(
                session_id=self.test_session_id,
                channel_id=self.test_channel_id
            )
            
            # 2. Send message to thread
            message_result = await http_client.send_message_to_thread(
                thread_id=thread_info["id"],
                payload={"content": "Thread workflow test message"}
            )
            
            # 3. Update thread usage
            await thread_manager.update_thread_usage(self.test_session_id)
            
            # Verify workflow
            self.assertIsNotNone(thread_info)
            self.assertEqual(thread_info["id"], self.test_thread_id)
            
            self.assertIsNotNone(message_result)
            self.assertEqual(message_result["channel_id"], self.test_thread_id)
            
            # Verify manager calls
            mock_tm_instance.get_or_create_thread.assert_called_once()
            mock_http_instance.send_message_to_thread.assert_called_once()
    
    async def test_thread_performance_metrics(self) -> None:
        """Test thread operation performance metrics."""
        thread_storage = ThreadStorage(self.db_path)
        
        # Performance test: bulk thread operations
        start_time = time.time()
        
        # Store many threads
        thread_count = 100
        for i in range(thread_count):
            thread_storage.store_thread(
                session_id=f"perf_session_{i}",
                thread_id=f"perf_thread_{i}",
                channel_id=self.test_channel_id,
                thread_name=f"Performance Test Thread {i}"
            )
        
        store_time = time.time() - start_time
        
        # Performance test: bulk retrieval
        start_time = time.time()
        
        all_threads = thread_storage.get_all_threads()
        
        retrieval_time = time.time() - start_time
        
        # Performance test: individual lookups
        start_time = time.time()
        
        for i in range(0, thread_count, 10):  # Test every 10th thread
            thread_info = thread_storage.get_thread(f"perf_session_{i}")
            self.assertIsNotNone(thread_info)
        
        lookup_time = time.time() - start_time
        
        # Verify performance metrics
        self.assertEqual(len(all_threads), thread_count)
        
        # Performance assertions (reasonable thresholds)
        self.assertLess(store_time, 5.0, f"Bulk storage too slow: {store_time:.3f}s")
        self.assertLess(retrieval_time, 1.0, f"Bulk retrieval too slow: {retrieval_time:.3f}s")
        self.assertLess(lookup_time, 1.0, f"Individual lookups too slow: {lookup_time:.3f}s")
        
        # Log performance metrics
        self.logger.info(
            "Thread performance metrics",
            context={
                "thread_count": thread_count,
                "store_time": store_time,
                "retrieval_time": retrieval_time,
                "lookup_time": lookup_time,
                "avg_store_time_per_thread": store_time / thread_count,
                "avg_lookup_time_per_thread": lookup_time / 10
            }
        )


def run_thread_lifecycle_tests() -> None:
    """Run thread lifecycle tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestThreadLifecycle)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nThread Lifecycle Tests Summary:")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    asyncio.run(main())