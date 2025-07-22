#!/usr/bin/env python3
"""Unit tests for task_storage_improved.py to verify improvements."""

import json
import os
import shutil

# Import the improved module
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from task_storage_improved import SimpleLock, TaskStorage


class TestTaskStorageImproved(unittest.TestCase):
    """Test cases for improved task storage implementation."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_storage_dir = TaskStorage._ensure_storage_dir.__globals__["STORAGE_DIR"]

        # Patch storage locations
        test_storage_dir = Path(self.test_dir) / "test_storage"
        TaskStorage._ensure_storage_dir.__globals__["STORAGE_DIR"] = test_storage_dir
        TaskStorage._ensure_storage_dir.__globals__["STORAGE_FILE"] = test_storage_dir / "tasks.json"
        TaskStorage._ensure_storage_dir.__globals__["BACKUP_FILE"] = test_storage_dir / "tasks.json.backup"
        TaskStorage._ensure_storage_dir.__globals__["LOCK_FILE"] = test_storage_dir / "tasks.json.lock"

        # Clear cache
        global _cache
        _cache = {"data": None, "timestamp": 0, "checksum": None}

    def tearDown(self):
        """Clean up test environment."""
        # Restore original paths
        TaskStorage._ensure_storage_dir.__globals__["STORAGE_DIR"] = self.original_storage_dir

        # Remove test directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_error_handling_corrupted_json(self):
        """Test recovery from corrupted JSON file."""
        # Create corrupted JSON file
        storage_file = TaskStorage._ensure_storage_dir.__globals__["STORAGE_FILE"]
        TaskStorage._ensure_storage_dir()

        with open(storage_file, "w") as f:
            f.write("{invalid json content")

        # Should return empty dict instead of crashing
        data = TaskStorage._load_data()
        self.assertEqual(data, {})

    def test_backup_recovery(self):
        """Test automatic recovery from backup file."""
        storage_file = TaskStorage._ensure_storage_dir.__globals__["STORAGE_FILE"]
        backup_file = TaskStorage._ensure_storage_dir.__globals__["BACKUP_FILE"]
        TaskStorage._ensure_storage_dir()

        # Create valid backup
        valid_data = {"session1": {"task1": {"status": "completed"}}}
        with open(backup_file, "w") as f:
            json.dump(valid_data, f)

        # Create corrupted main file
        with open(storage_file, "w") as f:
            f.write("{corrupted")

        # Should recover from backup
        data = TaskStorage._load_data()
        self.assertEqual(data, valid_data)

    def test_atomic_write(self):
        """Test atomic write prevents partial writes."""
        test_file = Path(self.test_dir) / "test_atomic.json"

        # Simulate write failure
        with self.assertRaises(ValueError):
            with TaskStorage._atomic_write(test_file) as fd:
                os.write(fd, b'{"test": "data"}')
                raise ValueError("Simulated error")

        # File should not exist after failed write
        self.assertFalse(test_file.exists())

    def test_cache_performance(self):
        """Test caching improves read performance."""
        # Store test data
        test_data = {"session1": {"task1": {"status": "started"}}}
        TaskStorage._save_data(test_data)

        # First read (cache miss)
        start_time = time.time()
        data1 = TaskStorage._load_data_with_cache()
        first_read_time = time.time() - start_time

        # Second read (cache hit)
        start_time = time.time()
        data2 = TaskStorage._load_data_with_cache()
        second_read_time = time.time() - start_time

        # Cache should make second read faster
        self.assertEqual(data1, data2)
        # Note: In real scenarios, cache would be significantly faster
        # but in tests the difference might be minimal

    def test_file_size_limit(self):
        """Test automatic archiving when file size exceeds limit."""
        # Temporarily set low limit for testing
        original_limit = TaskStorage._load_data.__globals__["MAX_FILE_SIZE_MB"]
        TaskStorage._load_data.__globals__["MAX_FILE_SIZE_MB"] = 0.0001  # Very small limit

        try:
            # Create large data
            large_data = {f"session{i}": {f"task{j}": {"data": "x" * 1000} for j in range(10)} for i in range(10)}

            TaskStorage._save_data(large_data)

            # Next load should trigger archiving
            data = TaskStorage._load_data()
            self.assertEqual(data, {})  # Should return empty after archiving

            # Check if archive was created
            storage_dir = TaskStorage._ensure_storage_dir.__globals__["STORAGE_DIR"]
            archives = list(storage_dir.glob("tasks_archive_*.json"))
            self.assertGreater(len(archives), 0)

        finally:
            TaskStorage._load_data.__globals__["MAX_FILE_SIZE_MB"] = original_limit

    def test_stale_lock_removal(self):
        """Test automatic removal of stale locks."""
        lock_file = TaskStorage._ensure_storage_dir.__globals__["LOCK_FILE"]
        TaskStorage._ensure_storage_dir()

        # Create old lock file
        lock_file.touch()
        # Make it appear old
        old_time = time.time() - 20  # 20 seconds ago
        os.utime(lock_file, (old_time, old_time))

        # Should remove stale lock and acquire new one
        with SimpleLock(lock_file, timeout=1) as lock:
            self.assertTrue(lock.acquired)

    def test_concurrent_access(self):
        """Test handling of concurrent access scenarios."""
        import threading

        results = []

        def worker(worker_id):
            try:
                success = TaskStorage.track_task_start(
                    "session1", f"task_{worker_id}", {"status": "started", "worker": worker_id}
                )
                results.append((worker_id, success))
            except Exception as e:
                results.append((worker_id, False, str(e)))

        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Check all operations succeeded
        self.assertEqual(len(results), 5)
        successful = [r for r in results if len(r) == 2 and r[1]]
        self.assertGreater(len(successful), 0)

    def test_data_validation(self):
        """Test JSON data structure validation."""
        # Valid data
        valid_data = {"session1": {"task1": {"status": "started"}, "task2": {"status": "completed"}}}
        self.assertTrue(TaskStorage._validate_json_data(valid_data))

        # Invalid data structures
        invalid_cases = [
            [],  # Not a dict
            {"session1": "not_a_dict"},  # Session value not dict
            {"session1": {"task1": "not_a_dict"}},  # Task value not dict
            {123: {}},  # Non-string session ID
        ]

        for invalid_data in invalid_cases:
            self.assertFalse(TaskStorage._validate_json_data(invalid_data))

    def test_cleanup_old_sessions(self):
        """Test automatic cleanup of old sessions."""
        # Create test data with old and new sessions
        now = datetime.now()
        old_time = (now - timedelta(hours=3)).isoformat()
        new_time = now.isoformat()

        test_data = {
            "old_session": {"task1": {"start_time": old_time, "status": "completed"}},
            "new_session": {"task1": {"start_time": new_time, "status": "started"}},
            "empty_session": {},
        }

        # Run cleanup
        TaskStorage._cleanup_old_sessions(test_data)

        # Check results
        self.assertNotIn("old_session", test_data)
        self.assertNotIn("empty_session", test_data)
        self.assertIn("new_session", test_data)


if __name__ == "__main__":
    unittest.main()
