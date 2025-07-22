#!/usr/bin/env python3
"""Simple transcript reader for extracting subagent conversations.

Minimal implementation to read Claude Code transcript files and extract
subagent task execution details.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from utils import sanitize_log_input

# Setup logger
logger = logging.getLogger(__name__)


def _validate_and_resolve_path(transcript_path: str) -> Path | None:
    """Validate and resolve transcript path to prevent directory traversal.

    Args:
        transcript_path: Path to validate

    Returns:
        Resolved Path object or None if invalid
    """
    try:
        transcript_file = Path(transcript_path).resolve(strict=True)
        allowed_dirs = [
            (Path.home() / ".claude").resolve(strict=True),
        ]
        if not any(
            os.path.commonpath([str(transcript_file), str(allowed_dir)]) == str(allowed_dir)
            for allowed_dir in allowed_dirs
        ):
            safe_path = sanitize_log_input(transcript_path)
            logger.error(f"Transcript path outside allowed directories: {safe_path}")
            return None
        return transcript_file
    except (OSError, ValueError, FileNotFoundError) as e:
        logger.exception(f"Path validation error: {e}")
        return None


def _parse_json_entry(line: str, line_num: int, json_errors: int) -> tuple[dict | None, int]:
    """Parse a single JSON line from transcript.

    Args:
        line: JSON line to parse
        line_num: Line number for error reporting
        json_errors: Current error count

    Returns:
        Tuple of (parsed_entry_or_None, updated_error_count)
    """
    try:
        return json.loads(line), json_errors
    except json.JSONDecodeError as e:
        json_errors += 1
        if json_errors <= 3:  # Log first few errors only
            logger.debug(f"JSON decode error at line {line_num}: {e}")
        return None, json_errors


def _match_task_response_pairs(lines: list[str]) -> list[dict]:
    """Process transcript lines to match tasks with responses.

    Args:
        lines: List of transcript lines

    Returns:
        List of task-response pair dictionaries
    """
    task_response_pairs = []
    current_tasks = {}  # Map tool_id to task info
    lines_processed = 0
    json_errors = 0

    # Search from end to beginning for efficiency
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if not line:
            continue

        lines_processed += 1

        entry, json_errors = _parse_json_entry(line, i + 1, json_errors)
        if entry is None:
            continue

        # Found subagent response
        if entry.get("isSidechain") is True and entry.get("type") == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])
            response_text = ""

            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    response_text += item.get("text", "")

            if response_text:
                response_info = {"content": response_text, "timestamp": entry.get("timestamp", "")}

                # For simple tasks, match the most recent task
                if current_tasks:
                    # Get the most recently added task (last in dict)
                    task_id = list(current_tasks.keys())[-1]
                    task_info = current_tasks[task_id]
                    task_response_pairs.append({"task": task_info, "response": response_info})
                    logger.debug(f"Matched task-response pair: {task_info['description']}")
                    # Remove matched task to avoid duplicate matching
                    del current_tasks[task_id]
                else:
                    logger.debug("Found response without any pending tasks")

        # Found task invocation
        else:
            message = entry.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Task":
                        tool_id = item.get("id")
                        tool_input = item.get("input", {})
                        task_info = {
                            "description": tool_input.get("description", "Unknown Task"),
                            "prompt": tool_input.get("prompt", ""),
                            "timestamp": entry.get("timestamp", ""),
                            "tool_id": tool_id,
                        }

                        if tool_id:
                            current_tasks[tool_id] = task_info
                            logger.debug(f"Found Task invocation: {task_info['description']} (tool_id: {tool_id})")

    logger.debug(f"Processed {lines_processed} lines, found {len(task_response_pairs)} task-response pairs")
    return task_response_pairs


def read_subagent_messages(transcript_path: str, event_timestamp: str | None = None) -> dict | None:
    """Extract subagent task and response from transcript file.

    Args:
        transcript_path: Path to the transcript .jsonl file
        event_timestamp: Optional timestamp to match specific task-response pair

    Returns:
        Dict with task info and response, or None if not found
    """
    safe_transcript_path = sanitize_log_input(transcript_path)
    safe_event_timestamp = sanitize_log_input(str(event_timestamp))
    logger.debug(
        f"read_subagent_messages called with path: {safe_transcript_path}, event_timestamp: {safe_event_timestamp}"
    )

    # Validate transcript path is within expected directories
    transcript_file = _validate_and_resolve_path(transcript_path)
    if transcript_file is None:
        return None

    try:
        if not transcript_file.exists():
            logger.debug(f"Transcript file does not exist: {safe_transcript_path}")
            return None

        file_size = transcript_file.stat().st_size
        logger.debug(f"Transcript file exists, size: {file_size} bytes")

        # Read file in reverse to find most recent task/response pair
        lines = []
        with transcript_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        logger.debug(f"Read {len(lines)} lines from transcript file")

        # Process lines to find task-response pairs
        task_response_pairs = _match_task_response_pairs(lines)

        # Return the most recent task-response pair
        if task_response_pairs:
            # If multiple pairs found, log them
            if len(task_response_pairs) > 1:
                logger.debug("Multiple task-response pairs found:")
                for idx, pair in enumerate(task_response_pairs):
                    logger.debug(f"  {idx + 1}. {pair['task']['description']}")

            # Return the most recent one (last in list since we read backwards)
            most_recent = task_response_pairs[-1]
            logger.debug(f"Returning most recent task-response pair: {most_recent['task']['description']}")
            return most_recent
        logger.debug("No complete task-response pairs found")

        return None

    except OSError:
        logger.exception("Unexpected error reading transcript")
        return None


def format_for_discord(subagent_data: dict) -> str:
    """Format subagent data for Discord message.

    Args:
        subagent_data: Dict with task and response info

    Returns:
        Formatted markdown string for Discord
    """
    if not subagent_data:
        return "No subagent data available"

    task = subagent_data.get("task", {})
    response = subagent_data.get("response", {})

    # Calculate duration if timestamps available
    duration = "Unknown"
    if task.get("timestamp") and response.get("timestamp"):
        try:
            task_time = datetime.fromisoformat(task["timestamp"].replace("Z", "+00:00"))
            response_time = datetime.fromisoformat(response["timestamp"].replace("Z", "+00:00"))
            duration_seconds = (response_time - task_time).total_seconds()
            duration = f"{duration_seconds:.1f}s"
        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to calculate duration: {e}")

    # Format message with Discord markdown
    return f"""## Task Execution Summary

**Description**: {task.get("description", "Unknown")}
**Duration**: {duration}

### User Prompt
```
{task.get("prompt", "No prompt available")[:1000]}
```

### Assistant Response
{response.get("content", "No response available")[:2000]}
"""
