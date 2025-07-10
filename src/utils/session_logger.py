"""Session logger for persisting Claude Code events to local storage."""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SessionLogger:
    """Non-blocking session event logger for Claude Code hooks."""

    def __init__(self, session_id: str, project_path: str):
        """Initialize the session logger.

        Args:
            session_id: The Claude Code session ID
            project_path: The current working directory/project path
        """
        self.session_id = session_id
        self.project_path = project_path
        self.sequence_number = 0
        self.enabled = os.getenv("DISCORD_ENABLE_SESSION_LOGGING", "0") == "1"
        self._shutdown = False

        # Configuration from environment variables
        self.buffer_size = int(os.getenv("DISCORD_SESSION_LOG_BUFFER_SIZE", "10"))
        self.flush_interval = float(os.getenv("DISCORD_SESSION_LOG_FLUSH_INTERVAL", "5.0"))
        self.queue_size = int(os.getenv("DISCORD_SESSION_LOG_QUEUE_SIZE", "1000"))
        self.privacy_filter = os.getenv("DISCORD_SESSION_LOG_PRIVACY_FILTER", "1") == "1"

        # Async queue for event buffering
        self.event_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self.queue_size)
        self.worker_task: Optional[asyncio.Task[None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Any] = None  # threading.Thread

        if self.enabled:
            self.session_dir = self._init_session_directory()
            self._start_worker()

    def _init_session_directory(self) -> Path:
        """Initialize the session directory structure.

        Returns:
            Path to the session directory
        """
        base_dir = Path.home() / ".claude" / "hooks" / "session_logs"
        session_dir = base_dir / "sessions" / self.session_id

        # Create directory structure
        (session_dir / "events").mkdir(parents=True, exist_ok=True)
        (session_dir / "tools").mkdir(exist_ok=True)
        (session_dir / "subagents").mkdir(exist_ok=True)

        # Initialize metadata
        metadata = {
            "session_id": self.session_id,
            "project_path": self.project_path,
            "start_time": datetime.now(UTC).isoformat(),
            "python_version": "3.13+",
            "event_count": 0,
        }

        metadata_path = session_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Update project index
        self._update_project_index()

        return session_dir

    def _update_project_index(self) -> None:
        """Update the project index with this session."""
        import hashlib

        project_hash = hashlib.md5(self.project_path.encode()).hexdigest()
        index_dir = Path.home() / ".claude" / "hooks" / "session_logs" / "projects" / project_hash
        index_dir.mkdir(parents=True, exist_ok=True)

        # Save project info if not exists
        project_info_path = index_dir / "project_info.json"
        if not project_info_path.exists():
            project_info = {
                "project_path": self.project_path,
                "project_name": Path(self.project_path).name,
                "created_at": datetime.now(UTC).isoformat(),
            }
            with open(project_info_path, "w") as f:
                json.dump(project_info, f, indent=2)

        # Add session to sessions list
        sessions_path = index_dir / "sessions.json"
        sessions = []
        if sessions_path.exists():
            with open(sessions_path, "r") as f:
                sessions = json.load(f)

        sessions.append({
            "session_id": self.session_id,
            "start_time": datetime.now(UTC).isoformat(),
            "status": "active",
        })

        with open(sessions_path, "w") as f:
            json.dump(sessions, f, indent=2)

    def _start_worker(self) -> None:
        """Start the async worker task."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No event loop running, create one in a thread
            import threading

            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
            self._thread.start()
            return

        self.worker_task = asyncio.create_task(self._process_events())
        # Add error handling callback
        self.worker_task.add_done_callback(self._worker_done_callback)

    def _run_event_loop(self) -> None:
        """Run event loop in a separate thread."""
        asyncio.set_event_loop(self._loop)
        self.worker_task = self._loop.create_task(self._process_events())
        self.worker_task.add_done_callback(self._worker_done_callback)
        self._loop.run_forever()

    def _worker_done_callback(self, task: asyncio.Task[None]) -> None:
        """Handle worker task completion."""
        try:
            task.result()  # Re-raise any exceptions
        except asyncio.CancelledError:
            pass  # Normal cancellation
        except Exception:
            # Restart worker if it crashed and we're not shutting down
            if self.enabled and not self._shutdown:
                logger.debug("Worker task crashed, restarting...")
                self._start_worker()

    async def _process_events(self) -> None:
        """Process events from the queue."""
        logger.debug("_process_events worker started")
        while self.enabled and not self._shutdown:
            try:
                # Wait for event with timeout
                event_data = await asyncio.wait_for(self.event_queue.get(), timeout=5.0)

                # Write event to file
                await self._write_event(event_data)

            except asyncio.TimeoutError:
                # Timeout is normal (for periodic checks)
                continue
            except Exception as e:
                # Log errors silently
                logger.debug(f"Error processing event: {e}")

    async def _write_event(self, event_data: dict[str, Any]) -> None:
        """Write an event to file.

        Args:
            event_data: The event data to write
        """
        try:
            # Use the sequence number from event data
            sequence = event_data.get("sequence", self.sequence_number + 1)
            self.sequence_number = sequence

            # Simple filename with sequence number
            event_file = self.session_dir / "events" / f"{sequence:06d}.json"

            # Async file write using executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_json_file, event_file, event_data)

            # Update metadata
            await self._update_metadata()

        except Exception as e:
            logger.debug(f"Failed to write event: {e}")

    def _write_json_file(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file (sync function for executor).

        Args:
            path: Path to write to
            data: Data to write
        """
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    async def _update_metadata(self) -> None:
        """Update session metadata."""
        try:
            metadata_path = self.session_dir / "metadata.json"

            # Read existing metadata
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Update fields
            metadata["event_count"] = self.sequence_number
            metadata["last_updated"] = datetime.now(UTC).isoformat()

            # Write back
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

        except Exception:
            pass  # Ignore metadata update failures

    async def _filter_sensitive_data(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Filter sensitive data from events if privacy mode is enabled.

        Args:
            event_data: The raw event data

        Returns:
            Filtered event data
        """
        if not self.privacy_filter:
            return event_data

        # For now, just return the data as-is
        # TODO: Implement actual privacy filtering
        return event_data

    async def log_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Log an event (non-blocking).

        Args:
            event_type: The type of event
            event_data: The event data to log
        """
        if not self.enabled:
            return

        logger.debug(f"SessionLogger.log_event called for {event_type}")
        try:
            # Apply privacy filtering
            filtered_data = await self._filter_sensitive_data(event_data)

            # Add metadata
            enriched_event = {
                "sequence": self.sequence_number + 1,
                "timestamp": datetime.now(UTC).isoformat(),
                "event_type": event_type,
                **filtered_data,
            }

            # If running in thread, use thread-safe method
            if hasattr(self, "_loop") and hasattr(self, "_thread"):
                logger.debug("Using thread-safe method to add event to queue")
                self._loop.call_soon_threadsafe(lambda: asyncio.create_task(self._add_to_queue(enriched_event)))
            else:
                # Add to queue (drop oldest if full)
                if self.event_queue.full():
                    try:
                        self.event_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass

                await self.event_queue.put(enriched_event)

        except Exception:
            # Silently ignore all errors
            pass

    async def _add_to_queue(self, event: dict[str, Any]) -> None:
        """Add event to queue (used for thread-safe operations)."""
        if self.event_queue.full():
            try:
                self.event_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        await self.event_queue.put(event)

    async def close(self) -> None:
        """Clean up resources."""
        self._shutdown = True

        # Stop thread event loop if running
        if hasattr(self, "_loop") and hasattr(self, "_thread") and self._loop:
            # Cancel worker task in the thread's loop
            if self.worker_task:
                self._loop.call_soon_threadsafe(self.worker_task.cancel)
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=1.0)
        elif self.worker_task:
            # Regular async cleanup
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        # Update session status in project index
        if self.enabled:
            try:
                self._mark_session_complete()
            except Exception:
                pass

    def _mark_session_complete(self) -> None:
        """Mark session as complete in project index."""
        import hashlib

        project_hash = hashlib.md5(self.project_path.encode()).hexdigest()
        sessions_path = Path.home() / ".claude" / "hooks" / "session_logs" / "projects" / project_hash / "sessions.json"

        if sessions_path.exists():
            with open(sessions_path, "r") as f:
                sessions = json.load(f)

            # Update status for this session
            for session in sessions:
                if session["session_id"] == self.session_id:
                    session["status"] = "complete"
                    session["end_time"] = datetime.now(UTC).isoformat()
                    break

            with open(sessions_path, "w") as f:
                json.dump(sessions, f, indent=2)
