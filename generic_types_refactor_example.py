#!/usr/bin/env python3
"""Generic Types Refactor Example - Discord Notifier

This file demonstrates how to refactor the existing Discord notifier code
using Generic types and TypeVar to create reusable type definitions for
nested structures.
"""

import json
from collections.abc import Callable
from datetime import datetime
from typing import (
    Any,
    Generic,
    Literal,
    NotRequired,
    Protocol,
    TypedDict,
    TypeVar,
    Union,
)

# =============================================================================
# GENERIC TYPE FOUNDATIONS
# =============================================================================

# Type variables for generic patterns
T = TypeVar("T")
TInput = TypeVar("TInput", bound=dict[str, Any])
TResponse = TypeVar("TResponse")
TEventData = TypeVar("TEventData", bound=dict[str, Any])
TConfig = TypeVar("TConfig", bound=dict[str, Any])
TResult = TypeVar("TResult")
TError = TypeVar("TError")

# =============================================================================
# BASE GENERIC STRUCTURES
# =============================================================================


class GenericResult(TypedDict, Generic[TResult, TError]):
    """Generic result type with success/error handling."""

    success: bool
    data: NotRequired[TResult]
    error: NotRequired[TError]
    timestamp: NotRequired[str]


class GenericToolInput(TypedDict, Generic[T]):
    """Generic tool input structure with type-safe tool data."""

    tool_name: str
    tool_data: T
    description: NotRequired[str]
    session_id: str
    timestamp: NotRequired[str]


class GenericToolResponse(TypedDict, Generic[T]):
    """Generic tool response structure with type-safe result data."""

    success: bool
    result: T
    error: NotRequired[str]
    execution_time: NotRequired[float]
    tool_name: str


class GenericEventData(TypedDict, Generic[TInput, TResponse]):
    """Generic event data with parameterized input/response types."""

    session_id: str
    hook_event_name: str
    timestamp: str
    tool_input: TInput
    tool_response: NotRequired[TResponse]
    transcript_path: NotRequired[str]


# =============================================================================
# GENERIC PROTOCOLS
# =============================================================================


class GenericValidator(Protocol, Generic[T]):
    """Generic validator protocol for type-safe validation."""

    def validate(self, data: Any) -> GenericResult[T, list[str]]:
        """Validate data and return typed result."""
        ...

    def is_valid(self, data: Any) -> bool:
        """Check if data is valid."""
        ...


class GenericFormatter(Protocol, Generic[TEventData]):
    """Generic formatter protocol for type-safe event formatting."""

    def format(self, event_data: TEventData, session_id: str) -> dict[str, Any]:
        """Format event data into Discord embed."""
        ...

    def get_event_type(self) -> str:
        """Get the event type this formatter handles."""
        ...


class GenericProcessor(Protocol, Generic[TInput, TResponse]):
    """Generic processor protocol for type-safe event processing."""

    def process(self, input_data: TInput) -> TResponse:
        """Process input data and return typed response."""
        ...

    def validate_input(self, input_data: TInput) -> bool:
        """Validate input data."""
        ...


# =============================================================================
# GENERIC REGISTRY SYSTEM
# =============================================================================


class TypedRegistry(Generic[T]):
    """Generic registry for type-safe collections."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def register(self, key: str, item: T) -> None:
        """Register an item with type safety."""
        self._items[key] = item

    def get(self, key: str) -> T | None:
        """Get an item by key."""
        return self._items.get(key)

    def get_all(self) -> dict[str, T]:
        """Get all registered items."""
        return self._items.copy()

    def has(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._items

    def remove(self, key: str) -> T | None:
        """Remove and return an item."""
        return self._items.pop(key, None)


# =============================================================================
# SPECIFIC TOOL TYPE DEFINITIONS
# =============================================================================


# Bash Tool Types
class BashToolData(TypedDict):
    """Bash tool specific data structure."""

    command: str
    timeout: NotRequired[int]
    working_directory: NotRequired[str]


class BashToolResult(TypedDict):
    """Bash tool specific result structure."""

    stdout: str
    stderr: str
    exit_code: int
    interrupted: bool
    execution_time: float


# File Tool Types
class FileToolData(TypedDict):
    """File tool specific data structure."""

    file_path: str
    operation: Literal["read", "write", "edit", "multi_edit"]
    content: NotRequired[str]
    old_string: NotRequired[str]
    new_string: NotRequired[str]


class FileToolResult(TypedDict):
    """File tool specific result structure."""

    success: bool
    file_path: str
    lines_affected: NotRequired[int]
    content_length: NotRequired[int]


# Search Tool Types
class SearchToolData(TypedDict):
    """Search tool specific data structure."""

    pattern: str
    path: NotRequired[str]
    include_filter: NotRequired[str]
    search_type: Literal["glob", "grep", "list"]


class SearchToolResult(TypedDict):
    """Search tool specific result structure."""

    matches: list[str]
    match_count: int
    search_time: float


# =============================================================================
# TYPED TOOL STRUCTURES
# =============================================================================

# Type-safe tool input/response combinations
BashToolInput = GenericToolInput[BashToolData]
BashToolResponse = GenericToolResponse[BashToolResult]
BashEventData = GenericEventData[BashToolInput, BashToolResponse]

FileToolInput = GenericToolInput[FileToolData]
FileToolResponse = GenericToolResponse[FileToolResult]
FileEventData = GenericEventData[FileToolInput, FileToolResponse]

SearchToolInput = GenericToolInput[SearchToolData]
SearchToolResponse = GenericToolResponse[SearchToolResult]
SearchEventData = GenericEventData[SearchToolInput, SearchToolResponse]

# Union type for all tool event data
ToolEventData = Union[BashEventData, FileEventData, SearchEventData]


# =============================================================================
# GENERIC VALIDATOR IMPLEMENTATIONS
# =============================================================================


class BashValidator(GenericValidator[BashToolData]):
    """Validator for Bash tool data."""

    def validate(self, data: Any) -> GenericResult[BashToolData, list[str]]:
        """Validate Bash tool data."""
        errors: list[str] = []

        if not isinstance(data, dict):
            errors.append("Data must be a dictionary")
            return {"success": False, "error": errors}

        if "command" not in data:
            errors.append("Missing required field: command")
        elif not isinstance(data["command"], str):
            errors.append("Field 'command' must be a string")
        elif not data["command"].strip():
            errors.append("Field 'command' cannot be empty")

        if "timeout" in data and not isinstance(data["timeout"], (int, float)):
            errors.append("Field 'timeout' must be a number")

        if errors:
            return {"success": False, "error": errors}

        return {
            "success": True,
            "data": {
                "command": data["command"],
                "timeout": data.get("timeout"),
                "working_directory": data.get("working_directory"),
            },
        }

    def is_valid(self, data: Any) -> bool:
        """Check if data is valid."""
        return self.validate(data)["success"]


class FileValidator(GenericValidator[FileToolData]):
    """Validator for File tool data."""

    def validate(self, data: Any) -> GenericResult[FileToolData, list[str]]:
        """Validate File tool data."""
        errors: list[str] = []

        if not isinstance(data, dict):
            errors.append("Data must be a dictionary")
            return {"success": False, "error": errors}

        if "file_path" not in data:
            errors.append("Missing required field: file_path")
        elif not isinstance(data["file_path"], str):
            errors.append("Field 'file_path' must be a string")

        if "operation" not in data:
            errors.append("Missing required field: operation")
        elif data["operation"] not in ["read", "write", "edit", "multi_edit"]:
            errors.append(
                "Field 'operation' must be one of: read, write, edit, multi_edit"
            )

        if errors:
            return {"success": False, "error": errors}

        return {
            "success": True,
            "data": {
                "file_path": data["file_path"],
                "operation": data["operation"],
                "content": data.get("content"),
                "old_string": data.get("old_string"),
                "new_string": data.get("new_string"),
            },
        }

    def is_valid(self, data: Any) -> bool:
        """Check if data is valid."""
        return self.validate(data)["success"]


# =============================================================================
# GENERIC FORMATTER IMPLEMENTATIONS
# =============================================================================


class BashFormatter(GenericFormatter[BashEventData]):
    """Formatter for Bash events with type safety."""

    def format(self, event_data: BashEventData, session_id: str) -> dict[str, Any]:
        """Format Bash event data into Discord embed."""
        tool_input = event_data["tool_input"]
        tool_data = tool_input["tool_data"]

        # Type-safe access to bash-specific data
        command = tool_data["command"]
        timeout = tool_data.get("timeout", 10)

        embed = {
            "title": f"🔧 Bash Command: {session_id[:8]}",
            "description": f"**Command:** `{command}`\n**Timeout:** {timeout}s",
            "color": 0x3498DB,
            "timestamp": datetime.now().isoformat(),
        }

        # Add response data if available
        if "tool_response" in event_data:
            response = event_data["tool_response"]
            result = response["result"]

            # Type-safe access to bash result data
            stdout = result["stdout"]
            stderr = result["stderr"]
            exit_code = result["exit_code"]

            embed["fields"] = [
                {"name": "Exit Code", "value": str(exit_code), "inline": True},
                {
                    "name": "Stdout",
                    "value": f"```\n{stdout[:500]}\n```",
                    "inline": False,
                },
                {
                    "name": "Stderr",
                    "value": f"```\n{stderr[:500]}\n```",
                    "inline": False,
                },
            ]

        return embed

    def get_event_type(self) -> str:
        """Get the event type this formatter handles."""
        return "BashEvent"


class FileFormatter(GenericFormatter[FileEventData]):
    """Formatter for File events with type safety."""

    def format(self, event_data: FileEventData, session_id: str) -> dict[str, Any]:
        """Format File event data into Discord embed."""
        tool_input = event_data["tool_input"]
        tool_data = tool_input["tool_data"]

        # Type-safe access to file-specific data
        file_path = tool_data["file_path"]
        operation = tool_data["operation"]

        embed = {
            "title": f"📁 File {operation.title()}: {session_id[:8]}",
            "description": f"**File:** `{file_path}`\n**Operation:** {operation}",
            "color": 0x2ECC71,
            "timestamp": datetime.now().isoformat(),
        }

        # Add response data if available
        if "tool_response" in event_data:
            response = event_data["tool_response"]
            result = response["result"]

            # Type-safe access to file result data
            success = result["success"]
            lines_affected = result.get("lines_affected", 0)

            embed["fields"] = [
                {"name": "Success", "value": "✅" if success else "❌", "inline": True},
                {
                    "name": "Lines Affected",
                    "value": str(lines_affected),
                    "inline": True,
                },
            ]

        return embed

    def get_event_type(self) -> str:
        """Get the event type this formatter handles."""
        return "FileEvent"


# =============================================================================
# GENERIC HTTP CLIENT
# =============================================================================


class HTTPConfig(TypedDict):
    """HTTP client configuration."""

    timeout: int
    max_retries: int
    user_agent: str
    base_headers: dict[str, str]


class HTTPRequest(TypedDict, Generic[T]):
    """Generic HTTP request structure."""

    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    url: str
    headers: NotRequired[dict[str, str]]
    data: NotRequired[T]
    params: NotRequired[dict[str, str]]


class HTTPResponse(TypedDict, Generic[T]):
    """Generic HTTP response structure."""

    status_code: int
    success: bool
    data: NotRequired[T]
    error: NotRequired[str]
    headers: dict[str, str]
    response_time: float


class GenericHTTPClient(Generic[TConfig]):
    """Generic HTTP client with typed configuration."""

    def __init__(self, config: TConfig) -> None:
        self.config = config

    def execute[TReq, TRes](self, request: HTTPRequest[TReq]) -> HTTPResponse[TRes]:
        """Execute HTTP request with type safety."""
        start_time = datetime.now()

        try:
            # Mock implementation - in real code, this would make actual HTTP calls
            result: HTTPResponse[TRes] = {
                "status_code": 200,
                "success": True,
                "headers": {"Content-Type": "application/json"},
                "response_time": (datetime.now() - start_time).total_seconds(),
            }

            return result

        except Exception as e:
            return {
                "status_code": 500,
                "success": False,
                "error": str(e),
                "headers": {},
                "response_time": (datetime.now() - start_time).total_seconds(),
            }


# =============================================================================
# GENERIC PROCESSING PIPELINE
# =============================================================================


class ProcessingPipeline(Generic[T]):
    """Generic processing pipeline for composable operations."""

    def __init__(self) -> None:
        self._processors: list[Callable[[T], T]] = []

    def add_processor(self, processor: Callable[[T], T]) -> "ProcessingPipeline[T]":
        """Add a processor to the pipeline."""
        self._processors.append(processor)
        return self

    def process(self, data: T) -> T:
        """Process data through the pipeline."""
        result = data
        for processor in self._processors:
            result = processor(result)
        return result

    def validate_pipeline(self) -> bool:
        """Validate the processing pipeline."""
        return len(self._processors) > 0


# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================


def demonstrate_generic_usage() -> None:
    """Demonstrate the usage of generic types."""
    # Create type-safe registry
    formatter_registry: TypedRegistry[GenericFormatter[Any]] = TypedRegistry()
    validator_registry: TypedRegistry[GenericValidator[Any]] = TypedRegistry()

    # Register formatters and validators
    formatter_registry.register("bash", BashFormatter())
    formatter_registry.register("file", FileFormatter())

    validator_registry.register("bash", BashValidator())
    validator_registry.register("file", FileValidator())

    # Create sample bash event data
    bash_event_data: BashEventData = {
        "session_id": "session_123",
        "hook_event_name": "PreToolUse",
        "timestamp": datetime.now().isoformat(),
        "tool_input": {
            "tool_name": "Bash",
            "tool_data": {"command": "ls -la", "timeout": 30},
            "session_id": "session_123",
        },
        "tool_response": {
            "success": True,
            "result": {
                "stdout": "total 8\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 .\ndrwxr-xr-x 3 user user 4096 Jan 1 12:00 ..",
                "stderr": "",
                "exit_code": 0,
                "interrupted": False,
                "execution_time": 0.1,
            },
            "tool_name": "Bash",
        },
    }

    # Type-safe formatter usage
    bash_formatter = formatter_registry.get("bash")
    if bash_formatter:
        formatted_embed = bash_formatter.format(bash_event_data, "session_123")
        print("Formatted embed:", json.dumps(formatted_embed, indent=2))

    # Type-safe validator usage
    bash_validator = validator_registry.get("bash")
    if bash_validator:
        validation_result = bash_validator.validate(
            {"command": "echo 'Hello World'", "timeout": 10}
        )
        print("Validation result:", validation_result)

    # Generic HTTP client usage
    http_config: HTTPConfig = {
        "timeout": 30,
        "max_retries": 3,
        "user_agent": "DiscordNotifier/1.0",
        "base_headers": {"Content-Type": "application/json"},
    }

    http_client: GenericHTTPClient[HTTPConfig] = GenericHTTPClient(http_config)

    # Type-safe request
    discord_request: HTTPRequest[dict[str, Any]] = {
        "method": "POST",
        "url": "https://discord.com/api/webhooks/123/abc",
        "data": {"embeds": [formatted_embed]},
    }

    response = http_client.execute(discord_request)
    print("HTTP Response:", response)

    # Processing pipeline usage
    pipeline: ProcessingPipeline[dict[str, Any]] = ProcessingPipeline()
    pipeline.add_processor(lambda x: {**x, "processed": True})
    pipeline.add_processor(lambda x: {**x, "timestamp": datetime.now().isoformat()})

    processed_data = pipeline.process({"original": "data"})
    print("Processed data:", processed_data)


if __name__ == "__main__":
    demonstrate_generic_usage()
