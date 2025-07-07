#!/usr/bin/env python3
"""Enhanced error handling patterns with improved type annotations.

This file demonstrates how to improve error handling in try/except blocks
with better type safety and error recovery mechanisms.
"""

import json
import logging

# Add src to path for imports
import sys
import urllib.error
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, TypeAlias, TypeVar

sys.path.insert(0, str(Path(__file__).parent / "src"))

from discord_notifier import (
    Config,
    ConfigurationError,
    DiscordAPIError,
    DiscordMessage,
)

# Type aliases for better error handling
NetworkError: TypeAlias = urllib.error.HTTPError | urllib.error.URLError
ConfigError: TypeAlias = ConfigurationError | json.JSONDecodeError
ValidationError: TypeAlias = TypeError | ValueError
DiscordError: TypeAlias = DiscordAPIError | NetworkError

# Result type for operations that can fail
T = TypeVar("T")
E = TypeVar("E", bound=Exception)


@dataclass
class Result(Generic[T, E]):
    """Result type for operations that can fail with type-safe error handling."""

    success: bool
    value: T | None = None
    error: E | None = None

    @classmethod
    def ok(cls, value: T) -> "Result[T, E]":
        """Create a successful result."""
        return cls(success=True, value=value)

    @classmethod
    def err(cls, error: E) -> "Result[T, E]":
        """Create an error result."""
        return cls(success=False, error=error)

    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self.success

    def is_err(self) -> bool:
        """Check if result is an error."""
        return not self.success

    def unwrap(self) -> T:
        """Get the value, raising an exception if error."""
        if not self.success or self.value is None:
            raise ValueError(f"Called unwrap() on error result: {self.error}")
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get the value or return default if error."""
        return self.value if self.success and self.value is not None else default


class EnhancedErrorHandler:
    """Enhanced error handler with type-safe patterns."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def safe_json_load(self, data: str) -> Result[dict[str, Any], json.JSONDecodeError]:
        """Load JSON with type-safe error handling."""
        try:
            result = json.loads(data)
            if not isinstance(result, dict):
                # Convert type mismatch to JSON decode error for consistency
                error = json.JSONDecodeError(
                    f"Expected dict, got {type(result).__name__}", data, 0
                )
                return Result.err(error)
            return Result.ok(result)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error at line {e.lineno}: {e.msg}")
            return Result.err(e)

    def safe_config_load(self, config_data: Any) -> Result[Config, ConfigError]:
        """Load config with comprehensive error handling."""
        try:
            # Type validation
            if not isinstance(config_data, dict):
                error = TypeError(
                    f"Config must be dict, got {type(config_data).__name__}"
                )
                return Result.err(error)

            # Required field validation
            if not config_data.get("webhook_url") and not (
                config_data.get("bot_token") and config_data.get("channel_id")
            ):
                error = ConfigurationError(
                    "Must provide either webhook_url or bot_token + channel_id"
                )
                return Result.err(error)

            # Create typed config
            config: Config = {
                "webhook_url": config_data.get("webhook_url"),
                "bot_token": config_data.get("bot_token"),
                "channel_id": config_data.get("channel_id"),
                "debug": config_data.get("debug", False),
                "use_threads": config_data.get("use_threads", False),
                "channel_type": config_data.get("channel_type", "text"),
                "thread_prefix": config_data.get("thread_prefix", "Session"),
                "mention_user_id": config_data.get("mention_user_id"),
            }

            return Result.ok(config)

        except (TypeError, ValueError) as e:
            self.logger.error(f"Config validation error: {e}")
            return Result.err(e)
        except ConfigurationError as e:
            self.logger.error(f"Configuration error: {e}")
            return Result.err(e)

    def safe_network_request(self, url: str, data: bytes) -> Result[bool, NetworkError]:
        """Make network request with type-safe error handling."""
        try:
            import urllib.request

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                return Result.ok(200 <= response.status < 300)

        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP error {e.code}: {e.reason}")
            return Result.err(e)
        except urllib.error.URLError as e:
            self.logger.error(f"URL error: {e.reason}")
            return Result.err(e)

    def safe_discord_send(
        self, message: DiscordMessage, config: Config
    ) -> Result[bool, DiscordError]:
        """Send Discord message with comprehensive error handling."""
        try:
            # Validate message structure
            if not isinstance(message, dict):
                error = DiscordAPIError(
                    f"Message must be dict, got {type(message).__name__}"
                )
                return Result.err(error)

            if "embeds" not in message:
                error = DiscordAPIError("Message must contain embeds")
                return Result.err(error)

            # Try webhook first
            if config.get("webhook_url"):
                webhook_result = self.safe_network_request(
                    config["webhook_url"], json.dumps(message).encode()
                )
                if webhook_result.is_ok():
                    return Result.ok(True)
                self.logger.warning(f"Webhook failed: {webhook_result.error}")

            # Try bot API as fallback
            if config.get("bot_token") and config.get("channel_id"):
                bot_url = f"https://discord.com/api/v10/channels/{config['channel_id']}/messages"
                bot_result = self.safe_network_request(
                    bot_url, json.dumps(message).encode()
                )
                if bot_result.is_ok():
                    return Result.ok(True)
                self.logger.warning(f"Bot API failed: {bot_result.error}")

            # If we get here, both methods failed
            error = DiscordAPIError("All Discord sending methods failed")
            return Result.err(error)

        except DiscordAPIError as e:
            self.logger.error(f"Discord API error: {e}")
            return Result.err(e)
        except Exception as e:
            # Convert unexpected errors to our domain error
            api_error = DiscordAPIError(f"Unexpected error: {type(e).__name__}: {e}")
            return Result.err(api_error)


@contextmanager
def safe_file_operation(filepath: Path) -> Generator[Path, None, None]:
    """Context manager for safe file operations with cleanup."""
    temp_path: Path | None = None
    try:
        temp_path = filepath.with_suffix(".tmp")
        yield temp_path
        # Atomic rename on success
        if temp_path.exists():
            temp_path.rename(filepath)
    except OSError as e:
        logging.exception(f"File operation failed: {e}")
        raise
    except Exception as e:
        logging.exception(
            f"Unexpected error in file operation: {type(e).__name__}: {e}"
        )
        raise
    finally:
        # Clean up temp file if it exists
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def enhanced_main() -> int:
    """Enhanced main function with improved error handling."""
    logger = logging.getLogger(__name__)
    handler = EnhancedErrorHandler(logger)

    try:
        # Read and parse input
        raw_input = sys.stdin.read()
        json_result = handler.safe_json_load(raw_input)

        if json_result.is_err():
            logger.error(f"Failed to parse JSON: {json_result.error}")
            return 1

        event_data = json_result.unwrap()

        # Load configuration
        config_result = handler.safe_config_load(
            {
                "webhook_url": "https://discord.com/api/webhooks/test/test",
                "debug": False,
                "use_threads": False,
                "channel_type": "text",
                "thread_prefix": "Session",
            }
        )

        if config_result.is_err():
            logger.error(f"Failed to load config: {config_result.error}")
            return 1

        config = config_result.unwrap()

        # Create test message
        message: DiscordMessage = {
            "embeds": [
                {
                    "title": "Test Message",
                    "description": "This is a test",
                    "color": 0x00FF00,
                }
            ]
        }

        # Send message
        send_result = handler.safe_discord_send(message, config)

        if send_result.is_ok():
            logger.info("Message sent successfully")
            return 0
        logger.error(f"Failed to send message: {send_result.error}")
        return 1

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        return 1


# Example usage demonstrating type-safe error handling
def demonstrate_error_handling() -> None:
    """Demonstrate enhanced error handling patterns."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    handler = EnhancedErrorHandler(logger)

    # Example 1: JSON parsing with type safety
    print("=== JSON Parsing Example ===")
    valid_json = '{"key": "value"}'
    invalid_json = '{"key": value}'

    for test_json in [valid_json, invalid_json]:
        result = handler.safe_json_load(test_json)
        if result.is_ok():
            print(f"✓ Parsed JSON: {result.unwrap()}")
        else:
            print(f"✗ JSON error: {result.error}")

    # Example 2: Config validation with type safety
    print("\n=== Config Validation Example ===")
    valid_config = {
        "webhook_url": "https://discord.com/api/webhooks/123/abc",
        "debug": False,
    }
    invalid_config = {
        "debug": "not_a_boolean"  # Type error
    }

    for test_config in [valid_config, invalid_config]:
        result = handler.safe_config_load(test_config)
        if result.is_ok():
            print(f"✓ Valid config: {result.unwrap()}")
        else:
            print(f"✗ Config error: {result.error}")

    # Example 3: File operations with context manager
    print("\n=== File Operations Example ===")
    test_file = Path("test_file.txt")

    try:
        with safe_file_operation(test_file) as temp_path:
            temp_path.write_text("Test content")
            print(f"✓ File written to {temp_path}")
        print(f"✓ File moved to {test_file}")
    except Exception as e:
        print(f"✗ File operation failed: {e}")
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    demonstrate_error_handling()
