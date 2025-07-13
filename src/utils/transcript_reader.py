#!/usr/bin/env python3
"""Utilities for reading and parsing Claude Code transcript files.

This module provides functions to extract information from transcript.jsonl files,
including full tool inputs and subagent messages.
"""

import json
import threading
import time
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, Union

from src.utils.astolfo_logger import AstolfoLogger

logger = AstolfoLogger(__name__)


# Global file locks to prevent concurrent access to the same transcript
_file_locks: dict[str, threading.Lock] = {}
_file_locks_lock = threading.Lock()


def _get_file_lock(file_path: str) -> threading.Lock:
    """Get or create a lock for the specified file path."""
    with _file_locks_lock:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]


class ToolUseContent(TypedDict):
    """Content structure for tool use in messages."""
    type: Literal["tool_use"]
    name: str
    input: dict[str, str]  # Contains 'prompt' for Task tool


class TextContent(TypedDict):
    """Content structure for text in messages."""
    type: Literal["text"]
    text: str


class ImageContent(TypedDict):
    """Content structure for images in messages."""
    type: Literal["image"]
    image: dict[str, str]  # Contains image data


# Union of all content types
MessageContent = Union[ToolUseContent, TextContent, ImageContent]


class Message(TypedDict):
    """Structure of a message in the transcript."""
    role: str
    content: list[MessageContent]


class TranscriptLine(TypedDict):
    """Structure of a line in the transcript file."""
    type: str
    sessionId: str
    timestamp: str
    message: NotRequired[Message]
    isSidechain: NotRequired[bool]


class SubagentMessage(TypedDict):
    """Processed subagent message structure."""
    timestamp: str
    type: str
    role: str
    content: str | None


def read_transcript_lines(transcript_path: str, max_lines: int = 1000) -> list[TranscriptLine]:
    """Read the last N lines from a transcript.jsonl file with file locking.

    Args:
        transcript_path: Path to the transcript.jsonl file
        max_lines: Maximum number of lines to read from the end

    Returns:
        List of parsed JSON objects from the transcript
    """
    # Get file-specific lock to prevent concurrent access
    file_lock = _get_file_lock(transcript_path)
    
    logger.debug(
        "Acquiring file lock for transcript reading",
        context={
            "transcript_path": transcript_path,
            "max_lines": max_lines,
            "lock_id": id(file_lock)
        }
    )
    
    with file_lock:
        logger.debug(
            "File lock acquired, starting transcript read",
            context={"transcript_path": transcript_path}
        )
        
        try:
            path = Path(transcript_path)
            if not path.exists():
                logger.warning(
                    "Transcript file not found",
                    context={"transcript_path": transcript_path}
                )
                return []

            # Read lines from the end for efficiency
            lines: list[str] = []
            with path.open("rb") as f:
                # Seek to end and read backwards
                f.seek(0, 2)  # Go to end of file
                file_size = f.tell()

                # Read chunks from the end
                chunk_size = 8192
                position = file_size
                buffer = ""

                while position > 0 and len(lines) < max_lines:
                    read_size = min(chunk_size, position)
                    position -= read_size
                    f.seek(position)

                    chunk = f.read(read_size).decode("utf-8", errors="ignore")
                    buffer = chunk + buffer

                    # Split by newlines
                    buffer_lines = buffer.split("\n")

                    # Keep the incomplete line for next iteration
                    if position > 0:
                        buffer = buffer_lines[0]
                        buffer_lines = buffer_lines[1:]
                    else:
                        buffer = ""

                    # Add complete lines
                    for line in reversed(buffer_lines):
                        if line.strip() and len(lines) < max_lines:
                            lines.insert(0, line)

            # Parse JSON lines
            parsed_lines: list[TranscriptLine] = []
            for line in lines:
                try:
                    obj: TranscriptLine = json.loads(line)
                    parsed_lines.append(obj)
                except json.JSONDecodeError:
                    logger.debug(
                        "Failed to parse JSON line",
                        context={"line_preview": line[:100]}
                    )
            
            logger.debug(
                "File lock released, transcript read completed",
                context={
                    "transcript_path": transcript_path,
                    "lines_read": len(parsed_lines)
                }
            )
            return parsed_lines

        except Exception as e:
            logger.exception(
                "Error reading transcript file",
                exception=e,
                context={"transcript_path": transcript_path}
            )
            return []


def get_full_task_prompt(transcript_path: str, session_id: str) -> str | None:
    """Extract the most recent Task tool prompt from transcript.

    Args:
        transcript_path: Path to the transcript.jsonl file
        session_id: Current session ID to match

    Returns:
        Full prompt text from the Task tool call, or None if not found
    """
    lines = read_transcript_lines(transcript_path, max_lines=500)

    # Search from newest to oldest for Task tool use
    for line in reversed(lines):
        # Skip if not from current session
        if line.get("sessionId") != session_id:
            continue

        # Check for assistant message with tool_use
        if line.get("type") == "assistant" and "message" in line:
            message = line["message"]
            if "content" in message:
                for content in message["content"]:
                    # Type guard for tool use content
                    if (isinstance(content, dict) and
                        content.get("type") == "tool_use" and
                        content.get("name") == "Task" and
                        "input" in content):

                        # Cast to ToolUseContent for type safety
                        tool_content = content  # Already validated structure
                        input_dict = tool_content.get("input", {})
                        if isinstance(input_dict, dict):
                            prompt = input_dict.get("prompt")
                            if isinstance(prompt, str):
                                logger.info(
                                    "Found Task prompt",
                                    context={"prompt_length": len(prompt)}
                                )
                                return prompt

    logger.debug("No Task tool prompt found in transcript")
    return None


def get_subagent_messages(transcript_path: str, session_id: str, limit: int = 50) -> list[SubagentMessage]:
    """Extract subagent messages from transcript.

    Args:
        transcript_path: Path to the transcript.jsonl file
        session_id: Current session ID to match
        limit: Maximum number of messages to return

    Returns:
        List of subagent messages with metadata
    """
    lines = read_transcript_lines(transcript_path, max_lines=1000)

    subagent_messages: list[SubagentMessage] = []

    for line in lines:
        # Check if it's a sidechain (subagent) message
        if (line.get("isSidechain") and
            line.get("sessionId") == session_id and
            "message" in line):

            message = line["message"]
            timestamp = line.get("timestamp", "")

            # Extract relevant information
            msg_info: SubagentMessage = {
                "timestamp": timestamp,
                "type": line.get("type", ""),
                "role": message.get("role", ""),
                "content": None,
            }

            # Extract content based on message structure
            if "content" in message:
                content_list = message["content"]
                if isinstance(content_list, list):
                    for content in content_list:
                        if isinstance(content, dict):
                            if content.get("type") == "text":
                                text_value = content.get("text", "")
                                if isinstance(text_value, str):
                                    msg_info["content"] = text_value
                                    break
                            elif content.get("type") == "tool_use":
                                tool_name = content.get("name", "Unknown")
                                if isinstance(tool_name, str):
                                    # Special handling for Task tools - extract the actual prompt
                                    if tool_name == "Task" and "input" in content:
                                        input_dict = content.get("input", {})
                                        if isinstance(input_dict, dict):
                                            prompt = input_dict.get("prompt")
                                            if isinstance(prompt, str):
                                                # Use the actual prompt content instead of generic label
                                                msg_info["content"] = prompt
                                                logger.debug(
                                                    "Extracted Task tool prompt for subagent",
                                                    context={
                                                        "session_id": session_id,
                                                        "prompt_length": len(prompt),
                                                        "timestamp": timestamp
                                                    }
                                                )
                                                break  # Found the prompt, break from content loop

                                    # Fallback to generic tool label for non-Task tools or failed extraction
                                    if msg_info["content"] is None:
                                        msg_info["content"] = f"[Tool: {tool_name}]"

            # Only add if we have content
            if msg_info["content"]:
                subagent_messages.append(msg_info)

                if len(subagent_messages) >= limit:
                    break

    logger.info(
        "Found subagent messages",
        context={"messages_count": len(subagent_messages)}
    )
    return subagent_messages


def get_subagent_messages_with_task_prompts(transcript_path: str, session_id: str, limit: int = 50) -> list[SubagentMessage]:
    """Extract subagent messages from transcript, including Task tool prompts.
    
    This function is an alias for get_subagent_messages, which already includes
    Task tool prompt extraction functionality.

    Args:
        transcript_path: Path to the transcript.jsonl file
        session_id: Current session ID to match
        limit: Maximum number of messages to return

    Returns:
        List of subagent messages with metadata, including extracted Task tool prompts
    """
    logger.debug("get_subagent_messages_with_task_prompts called", {
        "transcript_path": transcript_path,
        "session_id": session_id,
        "limit": limit
    })
    return get_subagent_messages(transcript_path, session_id, limit)
