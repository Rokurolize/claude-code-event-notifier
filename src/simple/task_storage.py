#!/usr/bin/env python3
"""Persistent task storage using JSON file.

Since Claude Code hooks run as separate processes, we need persistent storage
to track tasks across PreToolUse and PostToolUse events.
"""

import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)

# Storage file location
STORAGE_DIR = Path.home() / ".claude" / "hooks" / "task_tracking"
STORAGE_FILE = STORAGE_DIR / "tasks.json"
LOCK_FILE = STORAGE_DIR / "tasks.json.lock"

# Cleanup older than this duration
CLEANUP_AFTER_HOURS = 2


class SimpleLock:
    """Simple file-based lock implementation."""

    def __init__(self, lock_file: Path, timeout: int = 5):
        self.lock_file = lock_file
        self.timeout = timeout
        self.acquired = False

    def __enter__(self):
        """Acquire lock with retry."""
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            try:
                # Try to create lock file exclusively
                fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self.acquired = True
                return self
            except FileExistsError:
                # Lock is held by another process, wait and retry
                time.sleep(0.1)
            except Exception as e:
                logger.debug(f"Lock acquisition error: {e}")
                break

        if not self.acquired:
            # Log warning but still proceed to maintain "fail silent" principle
            logger.warning(f"Failed to acquire lock for {self.lock_file} within {self.timeout}s timeout")
        return self

    def __exit__(self, *args):
        """Release lock."""
        if self.acquired:
            try:
                self.lock_file.unlink()
            except (FileNotFoundError, PermissionError) as e:
                logger.debug(f"Failed to remove lock file: {e}")


class TaskStorage:
    """Persistent task storage using JSON file with file locking."""

    @staticmethod
    def _ensure_storage_dir():
        """Ensure storage directory exists with restrictive permissions."""
        STORAGE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)

    @staticmethod
    def _load_data() -> dict[str, dict[str, dict]]:
        """Load task data from file."""
        TaskStorage._ensure_storage_dir()

        if not STORAGE_FILE.exists():
            return {}

        try:
            with STORAGE_FILE.open("r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load task storage")
            return {}

    @staticmethod
    def _save_data(data: dict[str, dict[str, dict]]) -> None:
        """Save task data to file."""
        TaskStorage._ensure_storage_dir()

        try:
            # Write to temporary file first for atomic operation
            temp_file = STORAGE_FILE.with_suffix(".tmp")
            with temp_file.open("w") as f:
                json.dump(data, f, indent=2)
            # Set proper permissions
            temp_file.chmod(0o600)
            # Atomic rename
            temp_file.replace(STORAGE_FILE)
        except OSError:
            logger.exception("Failed to save task storage")

    @staticmethod
    def _validate_session_id(session_id: str) -> bool:
        """Validate session ID format using uuid.UUID."""
        if not session_id or not isinstance(session_id, str):
            return False
        try:
            # Attempt to parse the session_id as a UUID
            uuid.UUID(session_id)
            return True
        except ValueError:
            return False

    @staticmethod
    def track_task_start(session_id: str, task_id: str, task_info: dict) -> bool:
        """Store task start information."""
        # Validate input
        if not TaskStorage._validate_session_id(session_id):
            logger.error(f"Invalid session_id format: {session_id}")
            return False

        with SimpleLock(LOCK_FILE) as lock:
            if not lock.acquired:
                logger.warning(f"Could not acquire lock for task storage {task_id}")
                return False

            data = TaskStorage._load_data()

            # Initialize session if needed
            if session_id not in data:
                data[session_id] = {}

            # Store task info
            data[session_id][task_id] = task_info

            # Cleanup old sessions
            TaskStorage._cleanup_old_sessions(data)

            # Save
            TaskStorage._save_data(data)

            logger.debug(f"Stored task {task_id} in persistent storage")
            return True

    @staticmethod
    def get_session_tasks(session_id: str) -> dict[str, dict]:
        """Get all tasks for a session."""
        with SimpleLock(LOCK_FILE) as lock:
            if not lock.acquired:
                logger.warning(f"Could not acquire lock for session tasks {session_id}")
                return {}

            data = TaskStorage._load_data()
            return data.get(session_id, {})

    @staticmethod
    def update_task(session_id: str, task_id: str, updates: dict) -> bool:
        """Update task information."""
        with SimpleLock(LOCK_FILE) as lock:
            if not lock.acquired:
                logger.warning(f"Could not acquire lock for task update {task_id}")
                return False

            data = TaskStorage._load_data()

            if session_id not in data or task_id not in data[session_id]:
                return False

            # Update task
            data[session_id][task_id].update(updates)

            # Save
            TaskStorage._save_data(data)

            logger.debug(f"Updated task {task_id} in persistent storage")
            return True

    @staticmethod
    def get_task_by_content(session_id: str, description: str, prompt: str) -> dict | None:
        """Find a task by matching content (description and prompt).

        Args:
            session_id: Session ID
            description: Task description to match
            prompt: Task prompt to match

        Returns:
            Task info dict or None if not found
        """
        with SimpleLock(LOCK_FILE) as lock:
            if not lock.acquired:
                logger.warning("Could not acquire lock for task content search")
                return None

            data = TaskStorage._load_data()

            if session_id not in data:
                return None

            # Find tasks that match the content
            matching_tasks = []
            for task_id, task_info in data[session_id].items():
                if (
                    task_info.get("status") == "started"
                    and task_info.get("description") == description
                    and task_info.get("prompt") == prompt
                ):
                    matching_tasks.append((task_id, task_info))

            if not matching_tasks:
                return None

            # If multiple matches, use the oldest one (FIFO)
            if len(matching_tasks) > 1:
                matching_tasks.sort(key=lambda x: x[1]["start_time"])

            return matching_tasks[0][1]

    @staticmethod
    def get_task_by_id(session_id: str, task_id: str) -> dict | None:
        """Get specific task info by ID.

        Args:
            session_id: Session ID
            task_id: Task ID

        Returns:
            Task info dict or None if not found
        """
        with SimpleLock(LOCK_FILE) as lock:
            if not lock.acquired:
                logger.warning(f"Could not acquire lock for task search {session_id}")
                return None

            data = TaskStorage._load_data()

            if session_id in data and task_id in data[session_id]:
                return data[session_id][task_id]
            return None

    @staticmethod
    def get_latest_task(session_id: str) -> dict | None:
        """Get the most recent task for a session.

        Args:
            session_id: Session ID

        Returns:
            Task info dict or None if no tasks found
        """
        with SimpleLock(LOCK_FILE) as lock:
            if not lock.acquired:
                logger.warning(f"Could not acquire lock for latest task {session_id}")
                return None

            data = TaskStorage._load_data()

            if session_id not in data or not data[session_id]:
                return None

            # Get all tasks and sort by start time
            tasks = list(data[session_id].values())
            tasks.sort(key=lambda x: x["start_time"], reverse=True)

            return tasks[0]

    @staticmethod
    def _cleanup_old_sessions(data: dict[str, dict[str, dict]]) -> None:
        """Remove sessions older than CLEANUP_AFTER_HOURS."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=CLEANUP_AFTER_HOURS)
        sessions_to_remove = []

        for session_id, tasks in data.items():
            if not tasks:
                sessions_to_remove.append(session_id)
                continue

            # Check if all tasks in session are old
            all_old = True
            for task_info in tasks.values():
                try:
                    start_time = datetime.fromisoformat(task_info.get("start_time", ""))
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
            logger.debug(f"Cleaned up old session from storage: {session_id}")
