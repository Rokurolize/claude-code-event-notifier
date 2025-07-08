#!/usr/bin/env python3
"""Discord Notifier Refactoring Example with Generic Types.

This file demonstrates how to refactor the existing discord_notifier.py
to use Generic types and TypeVar for better type safety and reusability.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import (
    Any,
    Generic,
    NotRequired,
    Protocol,
    TypedDict,
    TypeVar,
    runtime_checkable,
)

# =============================================================================
# Generic Type Variables
# =============================================================================

T = TypeVar("T")
TInput = TypeVar("TInput", bound="BaseToolInput")
TResponse = TypeVar("TResponse")
TEventData = TypeVar("TEventData", bound="BaseEventData")
TConfig = TypeVar("TConfig", bound="ConfigProtocol")

# =============================================================================
# Base Protocols
# =============================================================================


@runtime_checkable
class ConfigProtocol(Protocol):
    """Protocol for configuration objects."""

    webhook_url: str | None
    bot_token: str | None
    channel_id: str | None
    debug: bool
    use_threads: bool
    channel_type: str
    thread_prefix: str
    mention_user_id: str | None


@runtime_checkable
class BaseToolInput(Protocol):
    """Protocol for tool input objects."""


@runtime_checkable
class BaseEventData(Protocol):
    """Protocol for event data objects."""

    session_id: str
    transcript_path: str
    hook_event_name: str


# =============================================================================
# Generic Tool Input System
# =============================================================================


class GenericToolInput(TypedDict, Generic[T]):
    """Generic tool input structure."""

    tool_name: str
    tool_data: T
    description: NotRequired[str]
    timeout: NotRequired[int]


class BashToolData(TypedDict):
    """Bash tool specific data."""

    command: str
    working_directory: NotRequired[str]


class FileToolData(TypedDict):
    """File tool specific data."""

    file_path: str
    operation: str
    old_string: NotRequired[str]
    new_string: NotRequired[str]
    edits: NotRequired[list[dict[str, Any]]]
    offset: NotRequired[int]
    limit: NotRequired[int]


class SearchToolData(TypedDict):
    """Search tool specific data."""

    pattern: str
    path: NotRequired[str]
    include: NotRequired[str]


# Tool input type aliases
BashToolInput = GenericToolInput[BashToolData]
FileToolInput = GenericToolInput[FileToolData]
SearchToolInput = GenericToolInput[SearchToolData]

# =============================================================================
# Generic Event Data System
# =============================================================================


class GenericEventData(TypedDict, Generic[TInput, TResponse]):
    """Generic event data structure."""

    session_id: str
    transcript_path: str
    hook_event_name: str
    tool_name: str
    tool_input: TInput
    tool_response: NotRequired[TResponse]
    timestamp: NotRequired[str]
    metadata: NotRequired[dict[str, Any]]


# Event type aliases
PreToolUseEventData = GenericEventData[TInput, None]
PostToolUseEventData = GenericEventData[TInput, TResponse]

# =============================================================================
# Generic Discord Message System
# =============================================================================


class DiscordEmbed(TypedDict):
    """Discord embed structure."""

    title: NotRequired[str]
    description: NotRequired[str]
    color: NotRequired[int]
    timestamp: NotRequired[str]
    footer: NotRequired[dict[str, str]]


class DiscordMessage(TypedDict):
    """Discord message structure."""

    content: NotRequired[str]
    embeds: NotRequired[list[DiscordEmbed]]


# =============================================================================
# Generic Formatter System
# =============================================================================


class GenericFormatter(Generic[TEventData]):
    """Generic formatter for event data."""

    def __init__(self, format_func: Callable[[TEventData, str], DiscordEmbed]):
        self.format_func = format_func

    def format(self, event_data: TEventData, session_id: str) -> DiscordEmbed:
        """Format event data into Discord embed."""
        return self.format_func(event_data, session_id)


class TypedFormatterRegistry(Generic[TEventData]):
    """Type-safe formatter registry."""

    def __init__(self):
        self._formatters: dict[str, GenericFormatter[TEventData]] = {}

    def register(
        self, event_type: str, formatter: GenericFormatter[TEventData]
    ) -> None:
        """Register a formatter for an event type."""
        self._formatters[event_type] = formatter

    def get_formatter(self, event_type: str) -> GenericFormatter[TEventData] | None:
        """Get formatter for event type."""
        return self._formatters.get(event_type)


# =============================================================================
# Generic HTTP Client System
# =============================================================================


class HTTPResult(Generic[T]):
    """Generic HTTP result."""

    def __init__(
        self, success: bool, data: T, status_code: int, error: str | None = None
    ):
        self.success = success
        self.data = data
        self.status_code = status_code
        self.error = error


class GenericHTTPClient(Generic[TConfig]):
    """Generic HTTP client with typed configuration."""

    def __init__(self, config: TConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger

    def post_webhook(
        self, url: str, data: DiscordMessage
    ) -> HTTPResult[DiscordMessage]:
        """Send message via webhook."""
        # Mock implementation - in real code, this would make the actual HTTP request
        self.logger.debug(f"Posting webhook to {url}")
        return HTTPResult(True, data, 200)

    def post_bot_api(
        self, url: str, data: DiscordMessage, token: str
    ) -> HTTPResult[DiscordMessage]:
        """Send message via bot API."""
        # Mock implementation - in real code, this would make the actual HTTP request
        self.logger.debug(f"Posting to bot API: {url}")
        return HTTPResult(True, data, 200)


# =============================================================================
# Generic Configuration System
# =============================================================================


class TypedConfig(TypedDict):
    """Typed configuration for Discord notifier."""

    webhook_url: str | None
    bot_token: str | None
    channel_id: str | None
    debug: bool
    use_threads: bool
    channel_type: str
    thread_prefix: str
    mention_user_id: str | None


class GenericConfigLoader(Generic[TConfig]):
    """Generic configuration loader."""

    def __init__(self, config_type: type[TConfig]):
        self.config_type = config_type

    def load_config(self) -> TConfig:
        """Load configuration from environment and files."""
        # Mock implementation - in real code, this would load from actual sources
        config_data = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        return self.config_type(config_data)  # type: ignore


# =============================================================================
# Generic Validation System
# =============================================================================


class ValidationResult(Generic[T]):
    """Generic validation result."""

    def __init__(self, is_valid: bool, data: T, errors: list[str] | None = None):
        self.is_valid = is_valid
        self.data = data
        self.errors = errors or []


class GenericValidator(Generic[T]):
    """Generic validator."""

    def __init__(self, validation_rules: list[Callable[[T], bool | str]]):
        self.validation_rules = validation_rules

    def validate(self, item: T) -> ValidationResult[T]:
        """Validate an item against all rules."""
        errors = []

        for rule in self.validation_rules:
            try:
                result = rule(item)
                if isinstance(result, str):
                    errors.append(result)
                elif not result:
                    errors.append(f"Validation failed for {type(item).__name__}")
            except Exception as e:
                errors.append(f"Validation error: {e}")

        return ValidationResult(is_valid=len(errors) == 0, data=item, errors=errors)


# =============================================================================
# Refactored Discord Notifier Components
# =============================================================================


class TypedDiscordNotifier:
    """Type-safe Discord notifier using generic types."""

    def __init__(self):
        self.config_loader = GenericConfigLoader(TypedConfig)
        self.config = self.config_loader.load_config()
        self.logger = self._setup_logging()
        self.http_client = GenericHTTPClient(self.config, self.logger)
        self.formatter_registry = TypedFormatterRegistry[dict[str, Any]]()
        self.validator = self._create_validator()

        # Register formatters
        self._register_formatters()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging based on configuration."""
        logger = logging.getLogger(__name__)
        level = logging.DEBUG if self.config["debug"] else logging.ERROR
        logging.basicConfig(level=level)
        return logger

    def _create_validator(self) -> GenericValidator[TypedConfig]:
        """Create configuration validator."""
        rules = [
            lambda cfg: cfg["webhook_url"] is not None
            or (cfg["bot_token"] is not None and cfg["channel_id"] is not None),
            lambda cfg: cfg["channel_type"] in ["text", "forum"],
        ]
        return GenericValidator(rules)

    def _register_formatters(self) -> None:
        """Register event formatters."""
        # Pre-tool use formatter
        pre_formatter = GenericFormatter[dict[str, Any]](self._format_pre_tool_use)
        self.formatter_registry.register("PreToolUse", pre_formatter)

        # Post-tool use formatter
        post_formatter = GenericFormatter[dict[str, Any]](self._format_post_tool_use)
        self.formatter_registry.register("PostToolUse", post_formatter)

        # Notification formatter
        notification_formatter = GenericFormatter[dict[str, Any]](
            self._format_notification
        )
        self.formatter_registry.register("Notification", notification_formatter)

    def _format_pre_tool_use(
        self, event_data: dict[str, Any], session_id: str
    ) -> DiscordEmbed:
        """Format pre-tool use event."""
        tool_name = event_data.get("tool_name", "Unknown")
        return {
            "title": f"🔧 About to execute: {tool_name}",
            "description": f"**Session:** `{session_id}`\n**Tool:** {tool_name}",
            "color": 0x3498DB,
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": f"Session: {session_id} | Event: PreToolUse"},
        }

    def _format_post_tool_use(
        self, event_data: dict[str, Any], session_id: str
    ) -> DiscordEmbed:
        """Format post-tool use event."""
        tool_name = event_data.get("tool_name", "Unknown")
        return {
            "title": f"✅ Completed: {tool_name}",
            "description": f"**Session:** `{session_id}`\n**Tool:** {tool_name}",
            "color": 0x2ECC71,
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": f"Session: {session_id} | Event: PostToolUse"},
        }

    def _format_notification(
        self, event_data: dict[str, Any], session_id: str
    ) -> DiscordEmbed:
        """Format notification event."""
        message = event_data.get("message", "System notification")
        return {
            "title": "📢 Notification",
            "description": f"**Message:** {message}\n**Session:** `{session_id}`",
            "color": 0xF39C12,
            "timestamp": datetime.now().isoformat(),
            "footer": {"text": f"Session: {session_id} | Event: Notification"},
        }

    def process_event(self, event_type: str, event_data: dict[str, Any]) -> bool:
        """Process an event and send to Discord."""
        # Validate configuration
        validation_result = self.validator.validate(self.config)
        if not validation_result.is_valid:
            self.logger.error(
                f"Configuration validation failed: {validation_result.errors}"
            )
            return False

        # Get formatter
        formatter = self.formatter_registry.get_formatter(event_type)
        if not formatter:
            self.logger.warning(f"No formatter found for event type: {event_type}")
            return False

        # Format event
        session_id = event_data.get("session_id", "unknown")[:8]
        embed = formatter.format(event_data, session_id)

        # Create message
        message: DiscordMessage = {"embeds": [embed]}

        # Send message
        return self._send_message(message)

    def _send_message(self, message: DiscordMessage) -> bool:
        """Send message to Discord."""
        # Try webhook first
        if self.config["webhook_url"]:
            result = self.http_client.post_webhook(self.config["webhook_url"], message)
            if result.success:
                self.logger.info("Message sent via webhook")
                return True

        # Try bot API
        if self.config["bot_token"] and self.config["channel_id"]:
            url = f"https://discord.com/api/v10/channels/{self.config['channel_id']}/messages"
            result = self.http_client.post_bot_api(
                url, message, self.config["bot_token"]
            )
            if result.success:
                self.logger.info("Message sent via bot API")
                return True

        self.logger.error("Failed to send message")
        return False


# =============================================================================
# Usage Example
# =============================================================================


def demonstrate_refactored_notifier():
    """Demonstrate the refactored Discord notifier."""
    # Create notifier
    notifier = TypedDiscordNotifier()

    # Example event data
    bash_event_data = {
        "session_id": "abc123def456",
        "transcript_path": "/path/to/transcript",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la", "description": "List directory contents"},
    }

    notification_event_data = {
        "session_id": "abc123def456",
        "transcript_path": "/path/to/transcript",
        "hook_event_name": "Notification",
        "message": "Task completed successfully",
        "title": "Success",
    }

    # Process events
    pre_tool_success = notifier.process_event("PreToolUse", bash_event_data)
    notification_success = notifier.process_event(
        "Notification", notification_event_data
    )

    print(f"Pre-tool event processed: {pre_tool_success}")
    print(f"Notification event processed: {notification_success}")

    return notifier


# =============================================================================
# Integration Benefits
# =============================================================================

"""
Benefits of the Refactored Implementation:

1. **Type Safety**:
   - All components are properly typed with generic constraints
   - IDE provides better autocomplete and error detection
   - Runtime type checking where needed

2. **Modularity**:
   - Each component has a single responsibility
   - Generic types allow for easy extension
   - Components can be tested independently

3. **Reusability**:
   - Generic formatters can be reused for different event types
   - HTTP client can be used with different configurations
   - Validation system works with any data type

4. **Maintainability**:
   - Clear separation of concerns
   - Type-safe interfaces between components
   - Easy to add new event types or formatters

5. **Testing**:
   - Each component can be mocked easily
   - Type-safe test data creation
   - Generic test utilities

6. **Configuration**:
   - Type-safe configuration loading
   - Validation with clear error messages
   - Easy to extend with new configuration options

7. **Error Handling**:
   - Structured error reporting
   - Type-safe error propagation
   - Clear failure modes

Migration Path:
1. Replace existing TypedDict definitions with generic versions
2. Update formatter functions to use generic formatter classes
3. Replace HTTP client with generic implementation
4. Add validation layer with generic validators
5. Update configuration loading with type-safe loader
6. Add proper error handling with structured results
"""

if __name__ == "__main__":
    notifier = demonstrate_refactored_notifier()
    print("Refactored Discord notifier demonstration completed successfully!")
