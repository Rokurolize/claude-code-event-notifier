#!/usr/bin/env python3
"""Base formatting utilities for Discord Notifier.

This module provides core formatting functions used throughout
the Discord notification system.
"""

import json
from pathlib import Path

from src.core.constants import TRUNCATION_SUFFIX, DiscordLimits, TruncationLimits


def truncate_string(text: str, max_length: int, suffix: str = TRUNCATION_SUFFIX) -> str:
    """Truncate string to maximum length with suffix.

    Safely truncates text to fit within Discord's character limits while
    preserving readability by adding a truncation indicator.

    Args:
        text: The string to potentially truncate
        max_length: Maximum allowed length including suffix
        suffix: String to append when truncation occurs (default: "...")

    Returns:
        str: Original string if within limit, or truncated string with suffix

    Behavior:
        - If text is within limit, returns unchanged
        - If truncation needed, reserves space for suffix
        - Ensures result never exceeds max_length

    Example:
        >>> truncate_string("Hello world!", 10)
        'Hello w...'
        >>> truncate_string("Short", 10)
        'Short'
        >>> truncate_string("Long text here", 8, ">>")
        'Long t>>'
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_file_path(file_path: str) -> str:
    """Format file path to be relative if possible.

    Converts absolute file paths to relative paths when possible to improve
    readability in Discord messages. Falls back to filename only if relative
    path conversion fails.

    Args:
        file_path: Absolute or relative file path to format

    Returns:
        str: Formatted path string, empty string if input is empty

    Formatting Logic:
        1. If empty path, return empty string
        2. Try to convert to relative path from current working directory
        3. If relative conversion fails, return just the filename
        4. If all else fails, return the original path

    Example:
        >>> # Assuming cwd is /home/user/project
        >>> format_file_path("/home/user/project/src/main.py")
        'src/main.py'
        >>> format_file_path("/etc/passwd")
        'passwd'
        >>> format_file_path("")
        ''

    Error Handling:
        - ValueError: Path is not relative to current directory
        - OSError: File system access issues
        - Both errors result in filename-only fallback
    """
    if not file_path:
        return ""

    path = Path(file_path)
    try:
        return str(path.relative_to(Path.cwd()))
    except (ValueError, OSError):
        return path.name


def get_truncation_suffix(original_length: int, limit: int) -> str:
    """Get truncation suffix if text was truncated.

    Returns a formatted truncation indicator if the original text length
    exceeded the specified limit. Used to indicate when content has been
    shortened for display.

    Args:
        original_length: Length of the original text before truncation
        limit: Maximum length limit that was applied

    Returns:
        str: Formatted truncation suffix with space, or empty string if no truncation

    Usage:
        This function is used in formatting functions to indicate when
        content has been truncated for Discord display limits.

    Example:
        >>> get_truncation_suffix(150, 100)
        ' ...'
        >>> get_truncation_suffix(50, 100)
        ''
        >>> # Used in formatting:
        >>> original = "Very long text here"
        >>> truncated = truncate_string(original, 10)
        >>> suffix = get_truncation_suffix(len(original), 10)
        >>> display_text = f"{truncated}{suffix}"
    """
    return f" {TRUNCATION_SUFFIX}" if original_length > limit else ""


def add_field(desc_parts: list[str], label: str, value: str, code: bool = False) -> None:
    """Add a field to description parts.

    Adds a formatted field to a list of description parts, with optional
    code formatting for technical content like file paths and commands.

    Args:
        desc_parts: List to append the formatted field to
        label: Field label/name (will be bolded)
        value: Field value/content
        code: Whether to format value as inline code (default: False)

    Returns:
        None: Modifies desc_parts list in place

    Formatting:
        - Label is always bolded with **label**
        - Value is either plain text or inline code with backticks
        - Code formatting is used for technical content (paths, commands)

    Example:
        >>> parts = []
        >>> add_field(parts, "Status", "Success")
        >>> add_field(parts, "Command", "git status", code=True)
        >>> parts
        ['**Status:** Success', '**Command:** `git status`']

    Usage:
        Primarily used in event formatting functions to build Discord
        embed descriptions with consistent field formatting.
    """
    if code:
        desc_parts.append(f"**{label}:** `{value}`")
    else:
        desc_parts.append(f"**{label}:** {value}")


def format_json_field(value: object, label: str, limit: int = TruncationLimits.JSON_PREVIEW) -> str:
    r"""Format a JSON value as a field.

    Formats complex data structures as JSON code blocks for Discord display.
    Handles truncation for large JSON objects while preserving readability.

    Args:
        value: Any JSON-serializable value to format
        label: Field label for the JSON block
        limit: Maximum character limit for JSON content

    Returns:
        str: Formatted JSON field with markdown code block

    Formatting:
        - JSON is formatted with 2-space indentation
        - Displayed in a ```json code block for syntax highlighting
        - Truncated if exceeds limit, with truncation indicator
        - Label is bolded and appears before the code block

    Example:
        >>> data = {"status": "success", "count": 42}
        >>> format_json_field(data, "Response", 100)
        '**Response:**\n```json\n{\n  "status": "success",\n  "count": 42\n}\n```'

    Usage:
        Used to display complex event data, tool inputs, and responses
        in a readable format within Discord embeds.

    Error Handling:
        - json.dumps() may raise TypeError for non-serializable objects
        - Non-serializable objects should be converted to strings first
    """
    value_str = json.dumps(value, indent=2)
    truncated = truncate_string(value_str, limit)
    suffix = get_truncation_suffix(len(value_str), limit)
    return f"**{label}:**\n```json\n{truncated}{suffix}\n```"


def split_long_text(text: str, label: str, max_length: int = DiscordLimits.MAX_FIELD_VALUE_LENGTH) -> list[str]:
    r"""Split long text into multiple parts for Discord fields.

    Splits text that exceeds Discord's field value limit into multiple parts,
    each with a numbered label for sequential display.

    Args:
        text: The text to potentially split
        label: Base label for the parts (e.g., "Prompt")
        max_length: Maximum length per part (default: Discord field limit)

    Returns:
        list[str]: List of formatted parts, each as "**Label (Part N):**\\ntext"

    Algorithm:
        - If text fits within limit, returns single part
        - Otherwise splits into chunks with part numbers
        - Preserves word boundaries when possible
        - Each part includes label with part number

    Example:
        >>> long_text = "A" * 2000
        >>> parts = split_long_text(long_text, "Content")
        >>> len(parts)
        2
        >>> parts[0].startswith("**Content (Part 1):**")
        True
    """
    if len(text) <= max_length - len(f"**{label}:**\n"):
        return [f"**{label}:**\n{text}"]

    parts: list[str] = []
    remaining = text
    part_num = 1

    # Reserve space for label and formatting
    overhead = 30  # Space for "**Label (Part N):**\n"
    chunk_size = max_length - overhead

    while remaining:
        if len(remaining) <= chunk_size:
            # Last chunk
            parts.append(f"**{label} (Part {part_num}):**\n{remaining}")
            break
        # Find a good split point (prefer newline or space)
        split_point = chunk_size

        # Look for newline first
        newline_pos = remaining[:chunk_size].rfind("\n")
        if newline_pos > chunk_size * 0.8:  # If newline is reasonably close
            split_point = newline_pos + 1
        else:
            # Look for space
            space_pos = remaining[:chunk_size].rfind(" ")
            if space_pos > chunk_size * 0.8:
                split_point = space_pos + 1

        chunk = remaining[:split_point]
        parts.append(f"**{label} (Part {part_num}):**\n{chunk}")
        remaining = remaining[split_point:]
        part_num += 1

        # Safety check to prevent infinite loops
        if part_num > 50:
            parts.append(f"**{label} (Part {part_num}):**\n[Content too long, truncated...]")
            break

    return parts
