#!/usr/bin/env python3
"""Generic Types Integration Example

This file demonstrates how to integrate generic types with the existing
Discord notifier codebase, showing migration strategies and practical usage.
"""

import json
from collections.abc import Callable
from datetime import datetime
from typing import (
    Any,
    Generic,
    NotRequired,
    Protocol,
    TypedDict,
    TypeVar,
    cast,
)

# =============================================================================
# MIGRATION STRATEGY: GRADUAL ADOPTION
# =============================================================================

# Step 1: Define generic base types that extend existing structures
T = TypeVar("T")
TToolData = TypeVar("TToolData", bound=dict[str, Any])
TEventData = TypeVar("TEventData", bound=dict[str, Any])


# Step 2: Create generic wrappers for existing TypedDict structures
class EnhancedToolInput(TypedDict, Generic[TToolData]):
    """Enhanced version of existing tool input with generic data."""

    # Existing fields from original ToolInputBase
    description: NotRequired[str]

    # New generic field
    typed_data: TToolData

    # Compatibility with existing structure
    raw_input: NotRequired[dict[str, Any]]  # For backward compatibility


class EnhancedEventData(TypedDict, Generic[TToolData]):
    """Enhanced version of existing event data with generic tool data."""

    # Existing fields from BaseEventData
    session_id: str
    hook_event_name: str
    timestamp: NotRequired[str]
    transcript_path: NotRequired[str]

    # Enhanced fields
    tool_name: str
    tool_input: EnhancedToolInput[TToolData]
    tool_response: NotRequired[dict[str, Any]]


# =============================================================================
# BACKWARD COMPATIBLE GENERIC VALIDATORS
# =============================================================================


class LegacyCompatibleValidator(Protocol, Generic[T]):
    """Validator that works with both old and new type structures."""

    def validate_legacy(self, data: dict[str, Any]) -> bool:
        """Validate using legacy structure."""
        ...

    def validate_typed(self, data: T) -> bool:
        """Validate using typed structure."""
        ...

    def migrate_to_typed(self, legacy_data: dict[str, Any]) -> T:
        """Convert legacy data to typed structure."""
        ...


class BashCompatibleValidator(LegacyCompatibleValidator[dict[str, Any]]):
    """Bash validator that works with both old and new structures."""

    def validate_legacy(self, data: dict[str, Any]) -> bool:
        """Validate legacy bash tool input."""
        return (
            isinstance(data, dict)
            and "command" in data
            and isinstance(data["command"], str)
            and bool(data["command"].strip())
        )

    def validate_typed(self, data: dict[str, Any]) -> bool:
        """Validate typed bash tool input."""
        return self.validate_legacy(data) and self._validate_optional_fields(data)

    def migrate_to_typed(self, legacy_data: dict[str, Any]) -> dict[str, Any]:
        """Convert legacy bash data to typed structure."""
        return {
            "command": legacy_data["command"],
            "timeout": legacy_data.get("timeout", 10),
            "working_directory": legacy_data.get("working_directory"),
            "description": legacy_data.get("description"),
        }

    def _validate_optional_fields(self, data: dict[str, Any]) -> bool:
        """Validate optional fields."""
        if "timeout" in data and not isinstance(data["timeout"], (int, float)):
            return False
        if "working_directory" in data and not isinstance(
            data["working_directory"], str
        ):
            return False
        return True


# =============================================================================
# GENERIC FORMATTER REGISTRY WITH FALLBACK
# =============================================================================


class FormatterRegistry(Generic[TEventData]):
    """Generic formatter registry with legacy fallback support."""

    def __init__(self) -> None:
        self._typed_formatters: dict[
            str, Callable[[TEventData, str], dict[str, Any]]
        ] = {}
        self._legacy_formatters: dict[
            str, Callable[[dict[str, Any], str], dict[str, Any]]
        ] = {}

    def register_typed(
        self, event_type: str, formatter: Callable[[TEventData, str], dict[str, Any]]
    ) -> None:
        """Register a typed formatter."""
        self._typed_formatters[event_type] = formatter

    def register_legacy(
        self,
        event_type: str,
        formatter: Callable[[dict[str, Any], str], dict[str, Any]],
    ) -> None:
        """Register a legacy formatter for backward compatibility."""
        self._legacy_formatters[event_type] = formatter

    def get_formatter(self, event_type: str) -> Callable[[Any, str], dict[str, Any]]:
        """Get formatter with fallback to legacy."""
        if event_type in self._typed_formatters:
            return self._typed_formatters[event_type]
        if event_type in self._legacy_formatters:
            return self._legacy_formatters[event_type]
        return self._default_formatter

    def _default_formatter(self, event_data: Any, session_id: str) -> dict[str, Any]:
        """Default formatter for unknown event types."""
        return {
            "title": f"⚡ Unknown Event: {session_id[:8]}",
            "description": f"**Event Type:** Unknown\n**Session:** `{session_id}`",
            "color": 0x808080,
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# ENHANCED BASH FORMATTER WITH GENERIC SUPPORT
# =============================================================================


def format_bash_event_generic(
    event_data: EnhancedEventData[dict[str, Any]], session_id: str
) -> dict[str, Any]:
    """Enhanced bash formatter using generic types."""
    tool_input = event_data["tool_input"]
    typed_data = tool_input["typed_data"]

    # Type-safe access to bash command
    command = typed_data.get("command", "")
    timeout = typed_data.get("timeout", 10)
    description = tool_input.get("description", "")

    # Build embed with enhanced information
    embed = {
        "title": f"🔧 Bash Command: {session_id[:8]}",
        "color": 0x3498DB,
        "timestamp": datetime.now().isoformat(),
        "fields": [
            {"name": "Command", "value": f"`{command}`", "inline": False},
            {"name": "Timeout", "value": f"{timeout}s", "inline": True},
            {"name": "Session", "value": f"`{session_id}`", "inline": True},
        ],
    }

    if description:
        embed["fields"].append(
            {"name": "Description", "value": description, "inline": False}
        )

    # Add response information if available
    if "tool_response" in event_data:
        response = event_data["tool_response"]
        if isinstance(response, dict):
            stdout = response.get("stdout", "")
            stderr = response.get("stderr", "")
            exit_code = response.get("exit_code", 0)

            # Add response fields
            embed["fields"].extend(
                [
                    {"name": "Exit Code", "value": str(exit_code), "inline": True},
                    {
                        "name": "Output",
                        "value": f"```\n{stdout[:500]}\n```" if stdout else "No output",
                        "inline": False,
                    },
                ]
            )

            if stderr:
                embed["fields"].append(
                    {
                        "name": "Errors",
                        "value": f"```\n{stderr[:500]}\n```",
                        "inline": False,
                    }
                )

    return embed


# =============================================================================
# GENERIC EVENT PROCESSOR
# =============================================================================


class GenericEventProcessor(Generic[TEventData]):
    """Generic event processor with type safety."""

    def __init__(self) -> None:
        self.validators: dict[str, LegacyCompatibleValidator[Any]] = {}
        self.formatters: FormatterRegistry[TEventData] = FormatterRegistry()
        self.processors: list[Callable[[TEventData], TEventData]] = []

    def register_validator(
        self, tool_name: str, validator: LegacyCompatibleValidator[Any]
    ) -> None:
        """Register a validator for a specific tool."""
        self.validators[tool_name] = validator

    def register_formatter(
        self, event_type: str, formatter: Callable[[TEventData, str], dict[str, Any]]
    ) -> None:
        """Register a formatter for a specific event type."""
        self.formatters.register_typed(event_type, formatter)

    def add_processor(self, processor: Callable[[TEventData], TEventData]) -> None:
        """Add a processing step to the pipeline."""
        self.processors.append(processor)

    def process_event(self, event_data: TEventData, event_type: str) -> dict[str, Any]:
        """Process an event through the pipeline."""
        # Apply processing steps
        processed_data = event_data
        for processor in self.processors:
            processed_data = processor(processed_data)

        # Get session ID
        session_id = processed_data.get("session_id", "unknown")

        # Format the event
        formatter = self.formatters.get_formatter(event_type)
        return formatter(processed_data, session_id)


# =============================================================================
# MIGRATION UTILITIES
# =============================================================================


def migrate_legacy_tool_input(
    legacy_input: dict[str, Any], tool_name: str
) -> EnhancedToolInput[dict[str, Any]]:
    """Migrate legacy tool input to enhanced structure."""
    # Extract typed data based on tool name
    typed_data: dict[str, Any] = {}

    if tool_name == "Bash":
        typed_data = {
            "command": legacy_input.get("command", ""),
            "timeout": legacy_input.get("timeout", 10),
            "working_directory": legacy_input.get("working_directory"),
        }
    elif tool_name in ["Read", "Write", "Edit", "MultiEdit"]:
        typed_data = {
            "file_path": legacy_input.get("file_path", ""),
            "operation": tool_name.lower(),
            "content": legacy_input.get("content"),
            "old_string": legacy_input.get("old_string"),
            "new_string": legacy_input.get("new_string"),
        }
    elif tool_name in ["Glob", "Grep"]:
        typed_data = {
            "pattern": legacy_input.get("pattern", ""),
            "path": legacy_input.get("path"),
            "include_filter": legacy_input.get("include"),
            "search_type": tool_name.lower(),
        }

    return {
        "description": legacy_input.get("description"),
        "typed_data": typed_data,
        "raw_input": legacy_input,  # Keep original for fallback
    }


def migrate_legacy_event_data(
    legacy_event: dict[str, Any],
) -> EnhancedEventData[dict[str, Any]]:
    """Migrate legacy event data to enhanced structure."""
    tool_name = legacy_event.get("tool_name", "Unknown")
    tool_input = legacy_event.get("tool_input", {})

    # Migrate tool input
    enhanced_input = migrate_legacy_tool_input(tool_input, tool_name)

    return {
        "session_id": legacy_event.get("session_id", "unknown"),
        "hook_event_name": legacy_event.get("hook_event_name", "Unknown"),
        "timestamp": legacy_event.get("timestamp", datetime.now().isoformat()),
        "transcript_path": legacy_event.get("transcript_path"),
        "tool_name": tool_name,
        "tool_input": enhanced_input,
        "tool_response": legacy_event.get("tool_response"),
    }


# =============================================================================
# PRACTICAL USAGE EXAMPLE
# =============================================================================


def demonstrate_integration() -> None:
    """Demonstrate integration with existing code."""
    # Create enhanced event processor
    processor: GenericEventProcessor[EnhancedEventData[dict[str, Any]]] = (
        GenericEventProcessor()
    )

    # Register validators
    processor.register_validator("Bash", BashCompatibleValidator())

    # Register formatters
    processor.register_formatter("PreToolUse", format_bash_event_generic)

    # Add processing steps
    processor.add_processor(
        lambda data: {**data, "processed_at": datetime.now().isoformat()}
    )

    # Simulate legacy event data (current format)
    legacy_event = {
        "session_id": "session_12345678",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo 'Hello Generic Types!'",
            "timeout": 30,
            "description": "Test bash command",
        },
        "timestamp": "2025-01-07T16:07:00Z",
    }

    # Migrate to enhanced format
    enhanced_event = migrate_legacy_event_data(legacy_event)

    # Process the event
    formatted_result = processor.process_event(enhanced_event, "PreToolUse")

    print("=== Generic Types Integration Demo ===")
    print("\n1. Original Legacy Event:")
    print(json.dumps(legacy_event, indent=2))

    print("\n2. Enhanced Event Structure:")
    print(json.dumps(enhanced_event, indent=2))

    print("\n3. Formatted Discord Embed:")
    print(json.dumps(formatted_result, indent=2))

    # Demonstrate type safety
    print("\n4. Type Safety Demo:")
    validator = BashCompatibleValidator()

    # Valid input
    valid_input = {"command": "ls -la", "timeout": 10}
    print(f"Valid input check: {validator.validate_typed(valid_input)}")

    # Invalid input
    invalid_input = {"command": "", "timeout": "not_a_number"}
    print(f"Invalid input check: {validator.validate_typed(invalid_input)}")

    # Migration demo
    migrated_data = validator.migrate_to_typed(
        {"command": "pwd", "description": "Get current directory"}
    )
    print(f"Migrated data: {migrated_data}")


# =============================================================================
# COMPATIBILITY LAYER
# =============================================================================


class CompatibilityLayer:
    """Provides compatibility between old and new type systems."""

    @staticmethod
    def wrap_legacy_formatter(
        legacy_formatter: Callable[[dict[str, Any], str], dict[str, Any]],
    ) -> Callable[[EnhancedEventData[dict[str, Any]], str], dict[str, Any]]:
        """Wrap a legacy formatter to work with enhanced event data."""

        def wrapper(
            event_data: EnhancedEventData[dict[str, Any]], session_id: str
        ) -> dict[str, Any]:
            # Convert enhanced event data back to legacy format
            legacy_data = {
                "session_id": event_data["session_id"],
                "hook_event_name": event_data["hook_event_name"],
                "timestamp": event_data.get("timestamp"),
                "transcript_path": event_data.get("transcript_path"),
                "tool_name": event_data["tool_name"],
                "tool_input": event_data["tool_input"].get("raw_input", {}),
                "tool_response": event_data.get("tool_response"),
            }

            return legacy_formatter(legacy_data, session_id)

        return wrapper

    @staticmethod
    def is_legacy_format(event_data: dict[str, Any]) -> bool:
        """Check if event data is in legacy format."""
        return (
            "tool_input" in event_data
            and isinstance(event_data["tool_input"], dict)
            and "typed_data" not in event_data["tool_input"]
        )

    @staticmethod
    def auto_migrate(event_data: dict[str, Any]) -> EnhancedEventData[dict[str, Any]]:
        """Automatically migrate legacy data if detected."""
        if CompatibilityLayer.is_legacy_format(event_data):
            return migrate_legacy_event_data(event_data)
        return cast("EnhancedEventData[dict[str, Any]]", event_data)


if __name__ == "__main__":
    demonstrate_integration()
