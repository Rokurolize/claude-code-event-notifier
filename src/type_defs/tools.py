"""Tool-related type definitions.

This module contains TypedDict definitions for all tool input and response
structures used in the Discord Notifier system.
"""

from typing import TypedDict, NotRequired, Union
from src.type_defs.base import PathAware


# ------------------------------------------------------------------------------
# TOOL INPUT HIERARCHY
# ------------------------------------------------------------------------------


class ToolInputBase(TypedDict):
    """Base tool input structure."""

    description: NotRequired[str]


class BashToolInput(ToolInputBase):
    """Bash tool input structure."""

    command: str


class FileEditOperation(TypedDict):
    """Individual file edit operation."""

    old_string: str
    new_string: str
    replace_all: NotRequired[bool]


class FileToolInputBase(ToolInputBase, PathAware):
    """Base file tool input structure."""


class ReadToolInput(FileToolInputBase):
    """Read tool input structure."""

    offset: NotRequired[int]
    limit: NotRequired[int]


class WriteToolInput(FileToolInputBase):
    """Write tool input structure."""

    content: str


class EditToolInput(FileToolInputBase):
    """Edit tool input structure."""

    old_string: str
    new_string: str
    replace_all: NotRequired[bool]


class MultiEditToolInput(FileToolInputBase):
    """Multi-edit tool input structure."""

    edits: list[FileEditOperation]


class ListToolInput(ToolInputBase, PathAware):
    """List tool input structure."""

    ignore: NotRequired[list[str]]


class SearchToolInputBase(ToolInputBase):
    """Base search tool input structure."""

    pattern: str
    path: NotRequired[str]


class GlobToolInput(SearchToolInputBase):
    """Glob tool input structure."""


class GrepToolInput(SearchToolInputBase):
    """Grep tool input structure."""

    include: NotRequired[str]


class TaskToolInput(ToolInputBase):
    """Task tool input structure."""

    prompt: str


class WebToolInput(ToolInputBase):
    """Web tool input structure."""

    url: str
    prompt: str


# Legacy FileToolInput for backward compatibility
class FileToolInput(TypedDict, total=False):
    """Legacy file operation tool input structure (for backward compatibility)."""

    file_path: str
    old_string: str
    new_string: str
    edits: list[FileEditOperation]
    offset: int | None
    limit: int | None


# Legacy SearchToolInput for backward compatibility
class SearchToolInput(TypedDict, total=False):
    """Legacy search tool input structure (for backward compatibility)."""

    pattern: str
    path: str
    include: str


# Union type for all tool inputs
ToolInput = (
    BashToolInput
    | ReadToolInput
    | WriteToolInput
    | EditToolInput
    | MultiEditToolInput
    | ListToolInput
    | GlobToolInput
    | GrepToolInput
    | TaskToolInput
    | WebToolInput
    | FileToolInput  # Legacy compatibility
    | SearchToolInput  # Legacy compatibility
    | dict[str, str | int | float | bool | list[str] | dict[str, str]]
)


# ------------------------------------------------------------------------------
# TOOL RESPONSE HIERARCHY
# ------------------------------------------------------------------------------


class ToolResponseBase(TypedDict):
    """Base tool response structure."""

    success: NotRequired[bool]
    error: NotRequired[str]


class BashToolResponse(ToolResponseBase):
    """Bash tool response structure."""

    stdout: str
    stderr: str
    interrupted: bool
    isImage: bool


class FileOperationResponse(ToolResponseBase):
    """File operation response structure."""

    filePath: NotRequired[str]


class SearchResponse(ToolResponseBase):
    """Search operation response structure."""

    results: NotRequired[list[str]]
    count: NotRequired[int]


# Union type for all tool responses
ToolResponse = (
    BashToolResponse
    | FileOperationResponse
    | SearchResponse
    | str
    | dict[str, str | int | float | bool]
    | list[dict[str, str]]
)


# Export all public types
__all__ = [
    'ToolInputBase', 'BashToolInput', 'FileEditOperation',
    'FileToolInputBase', 'ReadToolInput', 'WriteToolInput',
    'EditToolInput', 'MultiEditToolInput', 'ListToolInput',
    'SearchToolInputBase', 'GlobToolInput', 'GrepToolInput',
    'TaskToolInput', 'WebToolInput', 'FileToolInput', 'SearchToolInput',
    'ToolInput', 'ToolResponseBase', 'BashToolResponse',
    'FileOperationResponse', 'SearchResponse', 'ToolResponse'
]