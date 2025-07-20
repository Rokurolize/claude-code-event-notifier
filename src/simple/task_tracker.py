#!/usr/bin/env python3
"""Task tracking for session management.

Tracks Task tool executions within sessions to enable proper matching
between Task invocations, responses, and SubagentStop events.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any

# Setup logger
logger = logging.getLogger(__name__)

# In-memory storage for task tracking
# Structure: {session_id: {task_id: TaskInfo}}
_task_sessions: Dict[str, Dict[str, dict]] = {}

# Cleanup older than this duration
CLEANUP_AFTER_HOURS = 2


class TaskTracker:
    """Manages task tracking across sessions."""
    
    @staticmethod
    def track_task_start(session_id: str, tool_name: str, tool_input: dict) -> Optional[str]:
        """Track the start of a Task tool execution.
        
        Args:
            session_id: Session ID
            tool_name: Name of the tool (should be "Task")
            tool_input: Tool input data containing description and prompt
            
        Returns:
            Task ID if tracking was successful, None otherwise
        """
        if tool_name != "Task":
            return None
            
        # Generate a simple task ID based on timestamp
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}"
        
        # Initialize session if needed
        if session_id not in _task_sessions:
            _task_sessions[session_id] = {}
            logger.debug(f"Initialized new session tracking: {session_id}")
        
        # Store task info
        task_info = {
            "task_id": task_id,
            "description": tool_input.get("description", "Unknown Task"),
            "prompt": tool_input.get("prompt", ""),
            "start_time": datetime.now().isoformat(),
            "status": "started",
            "thread_id": None,
            "response": None
        }
        
        _task_sessions[session_id][task_id] = task_info
        logger.debug(f"Tracked task start: {task_id} in session {session_id}")
        logger.debug(f"Task description: {task_info['description']}")
        
        # Cleanup old sessions
        TaskTracker._cleanup_old_sessions()
        
        return task_id
    
    @staticmethod
    def update_task_thread(session_id: str, task_id: str, thread_id: str) -> bool:
        """Update task with Discord thread ID.
        
        Args:
            session_id: Session ID
            task_id: Task ID
            thread_id: Discord thread ID
            
        Returns:
            True if update was successful
        """
        if session_id in _task_sessions and task_id in _task_sessions[session_id]:
            _task_sessions[session_id][task_id]["thread_id"] = thread_id
            logger.debug(f"Updated task {task_id} with thread {thread_id}")
            return True
        return False
    
    @staticmethod
    def track_task_response(session_id: str, tool_name: str, tool_response: dict) -> Optional[str]:
        """Track the response of a Task tool execution.
        
        Args:
            session_id: Session ID
            tool_name: Name of the tool (should be "Task")
            tool_response: Tool response data
            
        Returns:
            Task ID if tracking was successful, None otherwise
        """
        if tool_name != "Task":
            return None
            
        if session_id not in _task_sessions:
            logger.debug(f"No session found for task response: {session_id}")
            return None
        
        # Find the most recent started task
        started_tasks = [
            (task_id, info) for task_id, info in _task_sessions[session_id].items()
            if info["status"] == "started"
        ]
        
        if not started_tasks:
            logger.debug(f"No started tasks found in session {session_id}")
            return None
        
        # Sort by start time and get the most recent
        started_tasks.sort(key=lambda x: x[1]["start_time"], reverse=True)
        task_id, task_info = started_tasks[0]
        
        # Update task info
        task_info["status"] = "completed"
        task_info["end_time"] = datetime.now().isoformat()
        task_info["response"] = tool_response
        
        logger.debug(f"Tracked task response: {task_id} in session {session_id}")
        
        return task_id
    
    @staticmethod
    def track_task_response_by_content(session_id: str, tool_name: str, tool_input: dict, tool_response: dict) -> Optional[str]:
        """Track the response of a Task tool execution using content-based matching.
        
        This method matches tasks based on their input content (description and prompt),
        which is more reliable for parallel task execution.
        
        Args:
            session_id: Session ID
            tool_name: Name of the tool (should be "Task")
            tool_input: Tool input data containing description and prompt
            tool_response: Tool response data
            
        Returns:
            Task ID if tracking was successful, None otherwise
        """
        if tool_name != "Task":
            return None
            
        if session_id not in _task_sessions:
            logger.debug(f"No session found for task response: {session_id}")
            return None
        
        # Extract matching criteria from tool_input
        match_description = tool_input.get("description", "")
        match_prompt = tool_input.get("prompt", "")
        
        logger.debug(f"Looking for task with description='{match_description}' in session {session_id}")
        
        # Find tasks that match the content
        matching_tasks = []
        for task_id, task_info in _task_sessions[session_id].items():
            if (task_info["status"] == "started" and 
                task_info.get("description") == match_description and
                task_info.get("prompt") == match_prompt):
                matching_tasks.append((task_id, task_info))
                logger.debug(f"Found matching task: {task_id}")
        
        if not matching_tasks:
            logger.debug(f"No matching tasks found for description='{match_description}' in session {session_id}")
            return None
        
        # If multiple matches (same content tasks), use the oldest one (FIFO)
        if len(matching_tasks) > 1:
            logger.debug(f"Found {len(matching_tasks)} matching tasks, using FIFO strategy")
            matching_tasks.sort(key=lambda x: x[1]["start_time"])
        
        task_id, task_info = matching_tasks[0]
        
        # Update task info
        task_info["status"] = "completed"
        task_info["end_time"] = datetime.now().isoformat()
        task_info["response"] = tool_response
        
        logger.debug(f"Tracked task response by content: {task_id} in session {session_id}")
        
        return task_id
    
    @staticmethod
    def get_latest_task(session_id: str) -> Optional[dict]:
        """Get the most recent task for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Task info dict or None if no tasks found
        """
        if session_id not in _task_sessions or not _task_sessions[session_id]:
            return None
        
        # Get all tasks and sort by start time
        tasks = list(_task_sessions[session_id].values())
        tasks.sort(key=lambda x: x["start_time"], reverse=True)
        
        return tasks[0]
    
    @staticmethod
    def get_task_by_id(session_id: str, task_id: str) -> Optional[dict]:
        """Get specific task info.
        
        Args:
            session_id: Session ID
            task_id: Task ID
            
        Returns:
            Task info dict or None if not found
        """
        if session_id in _task_sessions and task_id in _task_sessions[session_id]:
            return _task_sessions[session_id][task_id]
        return None
    
    @staticmethod
    def get_session_tasks(session_id: str) -> List[dict]:
        """Get all tasks for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of task info dicts
        """
        if session_id not in _task_sessions:
            return []
        
        tasks = list(_task_sessions[session_id].values())
        tasks.sort(key=lambda x: x["start_time"], reverse=True)
        return tasks
    
    @staticmethod
    def _cleanup_old_sessions():
        """Remove sessions older than CLEANUP_AFTER_HOURS."""
        cutoff_time = datetime.now() - timedelta(hours=CLEANUP_AFTER_HOURS)
        sessions_to_remove = []
        
        for session_id, tasks in _task_sessions.items():
            if not tasks:
                sessions_to_remove.append(session_id)
                continue
                
            # Check if all tasks in session are old
            all_old = True
            for task_info in tasks.values():
                try:
                    start_time = datetime.fromisoformat(task_info["start_time"])
                    if start_time > cutoff_time:
                        all_old = False
                        break
                except:
                    pass
            
            if all_old:
                sessions_to_remove.append(session_id)
        
        # Remove old sessions
        for session_id in sessions_to_remove:
            del _task_sessions[session_id]
            logger.debug(f"Cleaned up old session: {session_id}")