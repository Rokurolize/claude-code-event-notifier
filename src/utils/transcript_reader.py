#!/usr/bin/env python3
"""Utilities for reading and parsing Claude Code transcript files.

This module provides functions to extract information from transcript.jsonl files,
including full tool inputs and subagent messages.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def read_transcript_lines(transcript_path: str, max_lines: int = 1000) -> list[dict[str, Any]]:
    """Read the last N lines from a transcript.jsonl file.

    Args:
        transcript_path: Path to the transcript.jsonl file
        max_lines: Maximum number of lines to read from the end

    Returns:
        List of parsed JSON objects from the transcript
    """
    try:
        path = Path(transcript_path)
        if not path.exists():
            logger.warning(f"Transcript file not found: {transcript_path}")
            return []

        # Read lines from the end for efficiency
        lines: list[str] = []
        with open(path, "rb") as f:
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
        parsed_lines: list[dict[str, Any]] = []
        for line in lines:
            try:
                obj = json.loads(line)
                parsed_lines.append(obj)
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse JSON line: {line[:100]}...")

        return parsed_lines

    except Exception as e:
        logger.error(f"Error reading transcript file: {e}")
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
        if line.get("type") == "assistant" and line.get("message"):
            message = line["message"]
            if message.get("content"):
                for content in message["content"]:
                    if (content.get("type") == "tool_use" and
                        content.get("name") == "Task" and
                        content.get("input")):

                        prompt = content["input"].get("prompt")
                        if prompt:
                            logger.info(f"Found Task prompt with {len(prompt)} characters")
                            return prompt

    logger.debug("No Task tool prompt found in transcript")
    return None


def get_subagent_messages(transcript_path: str, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Extract subagent messages from transcript.

    Args:
        transcript_path: Path to the transcript.jsonl file
        session_id: Current session ID to match
        limit: Maximum number of messages to return

    Returns:
        List of subagent messages with metadata
    """
    lines = read_transcript_lines(transcript_path, max_lines=1000)

    subagent_messages: list[dict[str, Any]] = []

    for line in lines:
        # Check if it's a sidechain (subagent) message
        if (line.get("isSidechain") and
            line.get("sessionId") == session_id and
            line.get("message")):

            message = line["message"]
            timestamp = line.get("timestamp", "")

            # Extract relevant information
            msg_info = {
                "timestamp": timestamp,
                "type": line.get("type", ""),
                "role": message.get("role", ""),
                "content": None,
            }

            # Extract content based on message structure
            if message.get("content"):
                content_list = message["content"]
                if isinstance(content_list, list):
                    for content in content_list:
                        if content.get("type") == "text":
                            msg_info["content"] = content.get("text", "")
                            break
                        if content.get("type") == "tool_use":
                            tool_name = content.get("name", "Unknown")
                            msg_info["content"] = f"[Tool: {tool_name}]"

            # Only add if we have content
            if msg_info["content"]:
                subagent_messages.append(msg_info)

                if len(subagent_messages) >= limit:
                    break

    logger.info(f"Found {len(subagent_messages)} subagent messages")
    return subagent_messages

