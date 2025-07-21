#!/usr/bin/env python3
"""Task tracking for session management.

Tracks Task tool executions within sessions to enable proper matching
between Task invocations, responses, and SubagentStop events.

This module now uses persistent storage to handle the fact that Claude Code
hooks run as separate processes.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

# Import persistent storage
from task_storage import TaskStorage

# Setup logger
logger = logging.getLogger(__name__)


class TaskTracker:
    """Manages task tracking across sessions."""
    
    @staticmethod
    def track_task_start(session_id: str, tool_name: str, tool_input: dict) -> str | None:
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
        
        # Store task info using persistent storage
        task_info = {
            "task_id": task_id,
            "description": tool_input.get("description", "Unknown Task"),
            "prompt": tool_input.get("prompt", ""),
            "start_time": datetime.now().isoformat(),
            "status": "started",
            "thread_id": None,
            "response": None
        }
        
        success = TaskStorage.track_task_start(session_id, task_id, task_info)
        if success:
            logger.debug(f"Tracked task start: {task_id} in session {session_id}")
            logger.debug(f"Task description: {task_info['description']}")
        else:
            logger.error(f"Failed to track task start: {task_id}")
        
        return task_id if success else None
    
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
        success = TaskStorage.update_task(session_id, task_id, {"thread_id": thread_id})
        if success:
            logger.debug(f"Updated task {task_id} with thread {thread_id}")
        else:
            logger.error(f"Failed to update task {task_id} with thread")
        return success
    
    @staticmethod
    def track_task_response(session_id: str, tool_name: str, tool_response: dict) -> str | None:
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
            
        # Get all tasks for the session from persistent storage
        tasks = TaskStorage.get_session_tasks(session_id)
        if not tasks:
            logger.debug(f"No session found for task response: {session_id}")
            return None
        
        # Find the most recent started task
        started_tasks = [
            (task_id, info) for task_id, info in tasks.items()
            if info["status"] == "started"
        ]
        
        if not started_tasks:
            logger.debug(f"No started tasks found in session {session_id}")
            return None
        
        # Sort by start time and get the most recent
        started_tasks.sort(key=lambda x: x[1]["start_time"], reverse=True)
        task_id, task_info = started_tasks[0]
        
        # Update task info in persistent storage
        updates = {
            "status": "completed",
            "end_time": datetime.now().isoformat(),
            "response": tool_response
        }
        
        success = TaskStorage.update_task(session_id, task_id, updates)
        if success:
            logger.debug(f"Tracked task response: {task_id} in session {session_id}")
            return task_id
        else:
            logger.error(f"Failed to track task response: {task_id}")
            return None
    
    @staticmethod
    def track_task_response_by_content(session_id: str, tool_name: str, tool_input: dict, tool_response: dict) -> str | None:
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
            
        # Extract matching criteria from tool_input
        match_description = tool_input.get("description", "")
        match_prompt = tool_input.get("prompt", "")
        
        logger.debug(f"Looking for task with description=\"{match_description}\" in session {session_id}")
        
        # Find task by content using persistent storage
        task_info = TaskStorage.get_task_by_content(session_id, match_description, match_prompt)
        
        if not task_info:
            logger.debug(f"No matching tasks found for description=\"{match_description}\" in session {session_id}")
            return None
        
        task_id = task_info.get("task_id")
        logger.debug(f"Found matching task: {task_id}")
        
        # Update task info in persistent storage
        updates = {
            "status": "completed",
            "end_time": datetime.now().isoformat(),
            "response": tool_response
        }
        
        success = TaskStorage.update_task(session_id, task_id, updates)
        if success:
            logger.debug(f"Tracked task response by content: {task_id} in session {session_id}")
            return task_id
        else:
            logger.error(f"Failed to track task response by content: {task_id}")
            return None
    
    @staticmethod
    def get_latest_task(session_id: str) -> dict | None:
        """Get the most recent task for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Task info dict or None if no tasks found
        """
        return TaskStorage.get_latest_task(session_id)
    
    @staticmethod
    def get_task_by_id(session_id: str, task_id: str) -> dict | None:
        """Get specific task info.
        
        Args:
            session_id: Session ID
            task_id: Task ID
            
        Returns:
            Task info dict or None if not found
        """
        return TaskStorage.get_task_by_id(session_id, task_id)
    
    @staticmethod
    def get_session_tasks(session_id: str) -> list[dict]:
        """Get all tasks for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of task info dicts
        """
        tasks_dict = TaskStorage.get_session_tasks(session_id)
        if not tasks_dict:
            return []
        
        tasks = list(tasks_dict.values())
        tasks.sort(key=lambda x: x["start_time"], reverse=True)
        return tasks