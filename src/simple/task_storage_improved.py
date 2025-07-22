#!/usr/bin/env python3
"""Improved persistent task storage using JSON file with enhanced error handling and performance.

Since Claude Code hooks run as separate processes, we need persistent storage
to track tasks across PreToolUse and PostToolUse events.
"""

import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar, TypedDict

# Setup logger
logger = logging.getLogger(__name__)

# Storage configuration
STORAGE_DIR = Path.home() / ".claude" / "hooks" / "task_tracking"
STORAGE_FILE = STORAGE_DIR / "tasks.json"
BACKUP_FILE = STORAGE_DIR / "tasks.json.backup"
LOCK_FILE = STORAGE_DIR / "tasks.json.lock"

# Performance configuration
CLEANUP_AFTER_HOURS = 2
MAX_RETRIES = 3
RETRY_DELAY = 0.1
LOCK_TIMEOUT = 5
MAX_FILE_SIZE_MB = 10  # Maximum allowed file size

# Cache configuration
CACHE_TTL_SECONDS = 60  # Cache data for 1 minute


class TaskInfo(TypedDict, total=False):
    """Type definition for task information."""

    task_id: str
    description: str
    prompt: str
    start_time: str
    end_time: str | None
    status: str
    thread_id: str | None
    response: Any | None


class SimpleLock:
    """Improved file-based lock implementation with better error handling."""

    def __init__(self, lock_file: Path, timeout: int = LOCK_TIMEOUT):
        self.lock_file = lock_file
        self.timeout = timeout
        self.acquired = False
        self.lock_fd = None

    def __enter__(self):
        """Acquire lock with retry and stale lock detection."""
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                # Check for stale lock (older than timeout * 2)
                if self.lock_file.exists():
                    lock_age = time.time() - self.lock_file.stat().st_mtime
                    if lock_age > self.timeout * 2:
                        logger.warning(f"Removing stale lock (age: {lock_age:.1f}s)")
                        try:
                            self.lock_file.unlink()
                        except FileNotFoundError:
                            pass

                # Try to create lock file exclusively
                self.lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                # Write PID for debugging
                os.write(self.lock_fd, str(os.getpid()).encode())
                self.acquired = True
                return self

            except FileExistsError:
                # Lock is held by another process
                time.sleep(RETRY_DELAY)
            except OSError as e:
                logger.error(f"Lock acquisition error: {e}")
                raise

        if not self.acquired:
            raise TimeoutError(f"Failed to acquire lock within {self.timeout}s")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock safely."""
        if self.acquired and self.lock_fd is not None:
            try:
                os.close(self.lock_fd)
                self.lock_file.unlink()
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Error releasing lock: {e}")
            finally:
                self.acquired = False
                self.lock_fd = None


class TaskStorage:
    """Improved persistent task storage with better error handling and performance."""

    # Class-level cache to avoid global variable
    _cache: ClassVar[dict[str, Any]] = {"data": None, "timestamp": 0, "checksum": None}

    @staticmethod
    def _ensure_storage_dir():
        """Ensure storage directory exists with proper permissions."""
        try:
            STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            # Ensure directory is writable
            test_file = STORAGE_DIR / ".test"
            test_file.touch()
            test_file.unlink()
        except OSError as e:
            logger.error(f"Cannot create/access storage directory: {e}")
            raise

    @staticmethod
    def _calculate_checksum(data: bytes) -> str:
        """Calculate checksum for data integrity."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _validate_json_data(data: Any) -> bool:
        """Validate the structure of loaded JSON data."""
        if not isinstance(data, dict):
            return False

        # Basic structure validation
        for session_id, tasks in data.items():
            if not isinstance(session_id, str) or not isinstance(tasks, dict):
                return False
            for task_id, task_info in tasks.items():
                if not isinstance(task_id, str) or not isinstance(task_info, dict):
                    return False

        return True

    @staticmethod
    @contextmanager
    def _atomic_write(filepath: Path):
        """Context manager for atomic file writes."""
        temp_fd, temp_path = tempfile.mkstemp(dir=filepath.parent, prefix=f".{filepath.name}.", suffix=".tmp")

        try:
            yield temp_fd
            os.close(temp_fd)

            # Atomic rename (on POSIX systems)
            Path(temp_path).replace(filepath)

        except Exception:
            os.close(temp_fd)
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _load_data_with_cache() -> dict[str, dict[str, TaskInfo]]:
        """Load task data with caching for better performance."""
        # Check cache validity
        if TaskStorage._cache["data"] is not None:
            cache_age = time.time() - TaskStorage._cache["timestamp"]
            if cache_age < CACHE_TTL_SECONDS:
                # Verify file hasn't changed
                try:
                    if STORAGE_FILE.exists():
                        with open(STORAGE_FILE, "rb") as f:
                            current_checksum = TaskStorage._calculate_checksum(f.read())
                        if current_checksum == TaskStorage._cache["checksum"]:
                            return TaskStorage._cache["data"].copy()
                except OSError:
                    pass

        # Load from file
        data = TaskStorage._load_data()

        # Update cache
        if STORAGE_FILE.exists():
            try:
                with open(STORAGE_FILE, "rb") as f:
                    TaskStorage._cache["checksum"] = TaskStorage._calculate_checksum(f.read())
                TaskStorage._cache["data"] = data.copy()
                TaskStorage._cache["timestamp"] = time.time()
            except OSError:
                pass

        return data

    @staticmethod
    def _load_data() -> dict[str, dict[str, TaskInfo]]:
        """Load task data from file with error recovery."""
        TaskStorage._ensure_storage_dir()

        # Check file size limit
        if STORAGE_FILE.exists():
            file_size_mb = STORAGE_FILE.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.warning(f"Storage file too large ({file_size_mb:.1f}MB), archiving...")
                archive_path = STORAGE_DIR / f"tasks_archive_{int(time.time())}.json"
                shutil.move(str(STORAGE_FILE), str(archive_path))
                return {}

        for attempt in range(MAX_RETRIES):
            try:
                if not STORAGE_FILE.exists():
                    return {}

                with open(STORAGE_FILE) as f:
                    data = json.load(f)

                if TaskStorage._validate_json_data(data):
                    return data
                logger.error("Invalid JSON structure, attempting recovery")

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error (attempt {attempt + 1}): {e}")

                # Try to recover from backup
                if attempt == 0 and BACKUP_FILE.exists():
                    try:
                        shutil.copy2(str(BACKUP_FILE), str(STORAGE_FILE))
                        logger.info("Recovered from backup file")
                        continue
                    except OSError:
                        pass

            except OSError as e:
                logger.error(f"Failed to load task storage (attempt {attempt + 1}): {e}")

            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))

        # All attempts failed, return empty data
        logger.error("All load attempts failed, starting with empty storage")
        return {}

    @staticmethod
    def _save_data(data: dict[str, dict[str, TaskInfo]]):
        """Save task data to file atomically with backup."""
        TaskStorage._ensure_storage_dir()

        # Invalidate cache
        TaskStorage._cache["data"] = None

        try:
            # Create backup of existing file
            if STORAGE_FILE.exists():
                shutil.copy2(str(STORAGE_FILE), str(BACKUP_FILE))

            # Atomic write with pretty formatting
            with TaskStorage._atomic_write(STORAGE_FILE) as fd:
                json_data = json.dumps(data, indent=2, ensure_ascii=False)
                os.write(fd, json_data.encode("utf-8"))

        except OSError as e:
            logger.error(f"Failed to save task storage: {e}")
            raise

    @staticmethod
    def track_task_start(session_id: str, task_id: str, task_info: TaskInfo) -> bool:
        """Store task start information with proper error handling."""
        try:
            with SimpleLock(LOCK_FILE):
                data = TaskStorage._load_data()

                # Initialize session if needed
                if session_id not in data:
                    data[session_id] = {}

                # Store task info with timestamp validation
                task_info["start_time"] = task_info.get("start_time", datetime.now().isoformat())
                data[session_id][task_id] = task_info

                # Cleanup old sessions
                TaskStorage._cleanup_old_sessions(data)

                # Save
                TaskStorage._save_data(data)

                logger.debug(f"Stored task {task_id} in persistent storage")
                return True

        except Exception as e:
            logger.error(f"Failed to track task start: {e}")
            return False

    @staticmethod
    def get_session_tasks(session_id: str) -> dict[str, TaskInfo]:
        """Get all tasks for a session with caching."""
        try:
            # Try cache first for read operations
            data = TaskStorage._load_data_with_cache()
            return data.get(session_id, {})
        except Exception as e:
            logger.error(f"Failed to get session tasks: {e}")
            return {}

    @staticmethod
    def update_task(session_id: str, task_id: str, updates: dict[str, Any]) -> bool:
        """Update task information with validation."""
        try:
            with SimpleLock(LOCK_FILE):
                data = TaskStorage._load_data()

                if session_id not in data or task_id not in data[session_id]:
                    logger.warning(f"Task not found: {session_id}/{task_id}")
                    return False

                # Update task with timestamp
                updates["last_updated"] = datetime.now().isoformat()
                data[session_id][task_id].update(updates)

                # Save
                TaskStorage._save_data(data)

                logger.debug(f"Updated task {task_id} in persistent storage")
                return True

        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            return False

    @staticmethod
    def get_task_by_content(session_id: str, description: str, prompt: str) -> TaskInfo | None:
        """Find a task by matching content with optimized search."""
        try:
            tasks = TaskStorage.get_session_tasks(session_id)

            if not tasks:
                return None

            # Find matching tasks
            matching_tasks = []
            for task_id, task_info in tasks.items():
                if (
                    task_info.get("status") == "started"
                    and task_info.get("description") == description
                    and task_info.get("prompt") == prompt
                ):
                    matching_tasks.append((task_id, task_info))

            if not matching_tasks:
                return None

            # Return the oldest one (FIFO)
            matching_tasks.sort(key=lambda x: x[1].get("start_time", ""))
            return matching_tasks[0][1]

        except Exception as e:
            logger.error(f"Failed to get task by content: {e}")
            return None

    @staticmethod
    def get_task_by_id(session_id: str, task_id: str) -> TaskInfo | None:
        """Get specific task info by ID with caching."""
        try:
            tasks = TaskStorage.get_session_tasks(session_id)
            return tasks.get(task_id)
        except Exception as e:
            logger.error(f"Failed to get task by ID: {e}")
            return None

    @staticmethod
    def get_latest_task(session_id: str) -> TaskInfo | None:
        """Get the most recent task for a session with optimized sorting."""
        try:
            tasks = TaskStorage.get_session_tasks(session_id)

            if not tasks:
                return None

            # Sort by start time (most recent first)
            sorted_tasks = sorted(tasks.values(), key=lambda x: x.get("start_time", ""), reverse=True)

            return sorted_tasks[0] if sorted_tasks else None

        except Exception as e:
            logger.error(f"Failed to get latest task: {e}")
            return None

    @staticmethod
    def _cleanup_old_sessions(data: dict[str, dict[str, TaskInfo]]):
        """Remove sessions older than CLEANUP_AFTER_HOURS with better error handling."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=CLEANUP_AFTER_HOURS)
            sessions_to_remove = []

            for session_id, tasks in data.items():
                if not tasks:
                    sessions_to_remove.append(session_id)
                    continue

                # Check if all tasks in session are old
                all_old = True
                for task_info in tasks.values():
                    try:
                        start_time_str = task_info.get("start_time", "")
                        if start_time_str:
                            start_time = datetime.fromisoformat(start_time_str)
                            if start_time > cutoff_time:
                                all_old = False
                                break
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Invalid timestamp in task: {e}")

                if all_old:
                    sessions_to_remove.append(session_id)

            # Remove old sessions
            for session_id in sessions_to_remove:
                del data[session_id]
                logger.debug(f"Cleaned up old session: {session_id}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Don't raise - cleanup failure shouldn't break main functionality


# Performance monitoring decorator (optional)
def measure_performance(func):
    """Decorator to measure function execution time."""

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        if duration > 1.0:  # Log slow operations
            logger.warning(f"{func.__name__} took {duration:.2f}s")
        return result

    return wrapper


# Apply performance monitoring to critical functions
TaskStorage.track_task_start = measure_performance(TaskStorage.track_task_start)
TaskStorage._save_data = measure_performance(TaskStorage._save_data)
