#!/usr/bin/env python3
"""Common utility functions for the Simple Discord Event Notifier.

This module contains utility functions that are shared across multiple modules
to avoid code duplication and maintain consistency.
"""

import re

# Python 3.13+ required - pure standard library


def sanitize_log_input(input_str: str) -> str:
    """Sanitize input for safe logging by removing newline characters.
    
    Prevents log injection attacks by removing characters that could
    create fake log entries.
    
    Args:
        input_str: Input string to sanitize
        
    Returns:
        Sanitized string with newlines removed
    """
    if not isinstance(input_str, str):
        input_str = str(input_str)
    # Remove newline and carriage return characters
    return re.sub(r'[\n\r]', '', input_str)


def escape_discord_markdown(text: str | None) -> str:
    """Escape Discord markdown characters to prevent formatting issues.
    
    Args:
        text: Text to escape, can be None
        
    Returns:
        Escaped text safe for Discord messages
    """
    if not text:
        return ""
    
    # Pre-compiled regex pattern for better performance
    markdown_pattern = re.compile(r"[*_`~|>#\-=\[\](){}]")
    return markdown_pattern.sub(lambda m: f"\\{m.group()}", text)


def parse_bool(value: str) -> bool:
    """Parse string to boolean value.
    
    Args:
        value: String value to parse
        
    Returns:
        Boolean value
    """
    return value.lower() in ("true", "1", "yes", "on")