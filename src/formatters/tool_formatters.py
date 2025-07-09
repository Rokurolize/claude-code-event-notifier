#!/usr/bin/env python3
"""Tool-specific formatters for Discord Notifier.

This module provides formatting functions for specific tools used by Claude Code,
including both pre-use and post-use formatting of tool inputs and outputs.
"""

from typing import TypedDict

from src.core.constants import ToolNames, TruncationLimits
from src.formatters.base import (
    add_field,
    format_file_path,
    format_json_field,
    get_truncation_suffix,
    truncate_string,
)
from src.utils.validation import is_list_tool


# Type definitions for tool inputs and responses
class BashToolInput(TypedDict, total=False):
    """Input structure for Bash tool."""
    command: str
    description: str
    timeout: int


class FileOperationInput(TypedDict, total=False):
    """Input structure for file operations."""
    file_path: str
    content: str
    old_string: str
    new_string: str
    edits: list[dict[str, str]]
    limit: int
    offset: int


class SearchToolInput(TypedDict, total=False):
    """Input structure for search tools."""
    pattern: str
    path: str
    glob: str
    type: str
    output_mode: str


class TaskToolInput(TypedDict, total=False):
    """Input structure for Task tool."""
    instructions: str
    parent: str


class WebFetchInput(TypedDict, total=False):
    """Input structure for WebFetch tool."""
    url: str
    prompt: str


# Response type definitions
class BashToolResponse(TypedDict, total=False):
    """Response structure from Bash tool."""
    stdout: str
    stderr: str
    exit_code: int
    output: str


class FileOperationResponse(TypedDict, total=False):
    """Response structure from file operations."""
    success: bool
    message: str
    content: str
    lines_written: int


# Type alias for generic tool input/response
ToolInput = (
    BashToolInput
    | FileOperationInput
    | SearchToolInput
    | TaskToolInput
    | WebFetchInput
    | dict[str, str | int | float | bool]
)
ToolResponse = (
    BashToolResponse
    | FileOperationResponse
    | str
    | list[dict[str, str]]
    | dict[str, str | int | float | bool]
)


# Pre-use formatters
def format_bash_pre_use(tool_input: BashToolInput) -> list[str]:
    """Format Bash tool pre-use details.

    Args:
        tool_input: Input parameters for the Bash tool

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []
    command: str = tool_input.get("command", "")
    desc: str = tool_input.get("description", "")

    # Show full command up to limit
    truncated_command = truncate_string(command, TruncationLimits.COMMAND_FULL)
    add_field(desc_parts, "Command", truncated_command, code=True)

    if desc:
        add_field(desc_parts, "Description", desc)

    return desc_parts


def format_file_operation_pre_use(tool_name: str, tool_input: FileOperationInput) -> list[str]:
    """Format file operation tool pre-use details.

    Args:
        tool_name: Name of the file operation tool
        tool_input: Input parameters for the tool

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []
    file_path: str = tool_input.get("file_path", "")

    if file_path:
        formatted_path = format_file_path(file_path)
        add_field(desc_parts, "File", formatted_path, code=True)

    # Add specific details for each file operation
    if tool_name == ToolNames.EDIT.value:
        old_str: str = tool_input.get("old_string", "")
        new_str: str = tool_input.get("new_string", "")

        if old_str:
            truncated = truncate_string(old_str, TruncationLimits.STRING_PREVIEW)
            suffix = get_truncation_suffix(len(old_str), TruncationLimits.STRING_PREVIEW)
            add_field(desc_parts, "Replacing", f"{truncated}{suffix}", code=True)

        if new_str:
            truncated = truncate_string(new_str, TruncationLimits.STRING_PREVIEW)
            suffix = get_truncation_suffix(len(new_str), TruncationLimits.STRING_PREVIEW)
            add_field(desc_parts, "With", f"{truncated}{suffix}", code=True)

    elif tool_name == ToolNames.MULTI_EDIT.value:
        edits = tool_input.get("edits", [])
        add_field(desc_parts, "Number of edits", str(len(edits)))

    elif tool_name == ToolNames.READ.value:
        offset = tool_input.get("offset")
        limit = tool_input.get("limit")
        if offset or limit:
            start_line = offset or 1
            if limit:
                end_line = start_line + limit
                range_str = f"lines {start_line}-{end_line}"
            else:
                range_str = f"lines {start_line}-end"
            add_field(desc_parts, "Range", range_str)

    return desc_parts


def format_search_tool_pre_use(tool_name: str, tool_input: SearchToolInput) -> list[str]:
    """Format search tool pre-use details.

    Args:
        tool_name: Name of the search tool
        tool_input: Input parameters for the tool

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []
    pattern: str = tool_input.get("pattern", "")
    add_field(desc_parts, "Pattern", pattern, code=True)

    path: str = tool_input.get("path", "")
    if path:
        add_field(desc_parts, "Path", path, code=True)

    if tool_name == ToolNames.GREP.value:
        include: str = tool_input.get("include", "")
        if include:
            add_field(desc_parts, "Include", include, code=True)

    return desc_parts


def format_task_pre_use(tool_input: TaskToolInput) -> list[str]:
    """Format Task tool pre-use details.

    Args:
        tool_input: Input parameters for the Task tool

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []
    desc: str = tool_input.get("description", "")
    prompt: str = tool_input.get("prompt", "")

    if desc:
        add_field(desc_parts, "Task", desc)

    if prompt:
        truncated = truncate_string(prompt, TruncationLimits.PROMPT_PREVIEW)
        suffix = get_truncation_suffix(len(prompt), TruncationLimits.PROMPT_PREVIEW)
        add_field(desc_parts, "Prompt", f"{truncated}{suffix}")

    return desc_parts


def format_web_fetch_pre_use(tool_input: WebFetchInput) -> list[str]:
    """Format WebFetch tool pre-use details.

    Args:
        tool_input: Input parameters for the WebFetch tool

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []
    url: str = tool_input.get("url", "")
    prompt: str = tool_input.get("prompt", "")

    if url:
        add_field(desc_parts, "URL", url, code=True)

    if prompt:
        truncated = truncate_string(prompt, TruncationLimits.STRING_PREVIEW)
        suffix = get_truncation_suffix(len(prompt), TruncationLimits.STRING_PREVIEW)
        add_field(desc_parts, "Query", f"{truncated}{suffix}")

    return desc_parts


def format_unknown_tool_pre_use(tool_input: dict[str, str | int | float | bool]) -> list[str]:
    """Format unknown tool pre-use details.

    Args:
        tool_input: Input parameters for the unknown tool

    Returns:
        List of formatted description parts
    """
    return [format_json_field(tool_input, "Input")]


# Post-use formatters
def format_bash_post_use(tool_input: BashToolInput, tool_response: ToolResponse) -> list[str]:
    """Format Bash tool post-use results.

    Args:
        tool_input: Input parameters that were used
        tool_response: Response from the tool execution

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []

    command: str = truncate_string(tool_input.get("command", ""), TruncationLimits.COMMAND_PREVIEW)
    add_field(desc_parts, "Command", command, code=True)

    if isinstance(tool_response, dict):
        stdout = str(tool_response.get("stdout", "")).strip()
        stderr = str(tool_response.get("stderr", "")).strip()
        interrupted = tool_response.get("interrupted", False)

        if stdout:
            truncated_stdout = truncate_string(stdout, TruncationLimits.OUTPUT_PREVIEW)
            desc_parts.append(f"**Output:**\n```\n{truncated_stdout}\n```")

        if stderr:
            truncated_stderr = truncate_string(stderr, TruncationLimits.ERROR_PREVIEW)
            desc_parts.append(f"**Error:**\n```\n{truncated_stderr}\n```")

        if interrupted:
            desc_parts.append("**Status:** ⚠️ Interrupted")

    return desc_parts


def format_read_operation_post_use(
    tool_name: str, tool_input: FileOperationInput, tool_response: ToolResponse
) -> list[str]:
    """Format read operation tool post-use results.

    Args:
        tool_name: Name of the read operation tool
        tool_input: Input parameters that were used
        tool_response: Response from the tool execution

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []

    if tool_name == ToolNames.READ.value:
        file_path = format_file_path(tool_input.get("file_path", ""))
        add_field(desc_parts, "File", file_path, code=True)

        if isinstance(tool_response, str):
            lines = tool_response.count("\n") + 1
            add_field(desc_parts, "Lines read", str(lines))
        elif isinstance(tool_response, dict) and "error" in tool_response:
            # Type assertion: if "error" exists, we can safely access it
            error_value = tool_response.get("error")
            if error_value:
                add_field(desc_parts, "Error", str(error_value))

    elif is_list_tool(tool_name):
        if isinstance(tool_response, list):
            add_field(desc_parts, "Results found", str(len(tool_response)))
            if tool_response:
                preview = tool_response[:5]
                preview_str = "\n".join(f"  • `{item}`" for item in preview)
                desc_parts.append(f"**Preview:**\n{preview_str}")
                if len(tool_response) > 5:
                    desc_parts.append(f"  *... and {len(tool_response) - 5} more*")
        elif isinstance(tool_response, str):
            result_lines: list[str] = tool_response.strip().split("\n") if tool_response.strip() else []
            add_field(desc_parts, "Results found", str(len(result_lines)))

    return desc_parts


def format_write_operation_post_use(tool_input: FileOperationInput, tool_response: ToolResponse) -> list[str]:
    """Format write operation tool post-use results.

    Args:
        tool_input: Input parameters that were used
        tool_response: Response from the tool execution

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []

    file_path = format_file_path(tool_input.get("file_path", ""))
    add_field(desc_parts, "File", file_path, code=True)

    if isinstance(tool_response, dict):
        if tool_response.get("success"):
            desc_parts.append("**Status:** ✅ Success")
        elif "error" in tool_response:
            # Type assertion: if "error" exists, we can safely access it
            error_value = tool_response.get("error")
            if error_value:
                add_field(desc_parts, "Error", str(error_value))
    elif isinstance(tool_response, str) and "error" in tool_response.lower():
        error_msg = truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)
        add_field(desc_parts, "Error", error_msg)
    else:
        desc_parts.append("**Status:** ✅ Completed")

    return desc_parts


def format_task_post_use(tool_input: TaskToolInput, tool_response: ToolResponse) -> list[str]:
    """Format Task tool post-use results.

    Args:
        tool_input: Input parameters that were used
        tool_response: Response from the tool execution

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []

    desc: str = tool_input.get("description", "")
    if desc:
        add_field(desc_parts, "Task", desc)

    if isinstance(tool_response, str):
        summary = truncate_string(tool_response, TruncationLimits.RESULT_PREVIEW)
        desc_parts.append(f"**Result:**\n{summary}")

    return desc_parts


def format_web_fetch_post_use(tool_input: WebFetchInput, tool_response: ToolResponse) -> list[str]:
    """Format WebFetch tool post-use results.

    Args:
        tool_input: Input parameters that were used
        tool_response: Response from the tool execution

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []

    url: str = tool_input.get("url", "")
    add_field(desc_parts, "URL", url, code=True)

    if isinstance(tool_response, str):
        if "error" in tool_response.lower():
            error_msg = truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)
            add_field(desc_parts, "Error", error_msg)
        else:
            add_field(desc_parts, "Content length", f"{len(tool_response)} chars")

    return desc_parts


def format_unknown_tool_post_use(tool_response: ToolResponse) -> list[str]:
    """Format unknown tool post-use results.

    Args:
        tool_response: Response from the tool execution

    Returns:
        List of formatted description parts
    """
    desc_parts: list[str] = []

    if isinstance(tool_response, dict):
        desc_parts.append(format_json_field(tool_response, "Response", TruncationLimits.RESULT_PREVIEW))
    elif isinstance(tool_response, str):
        response_str = truncate_string(tool_response, TruncationLimits.RESULT_PREVIEW)
        add_field(desc_parts, "Response", response_str)

    return desc_parts
