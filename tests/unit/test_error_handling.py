#!/usr/bin/env python3
"""Tests for enhanced error handling patterns.

This file tests the improved error handling with type annotations.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from examples.error_handling_examples import EnhancedErrorHandler, Result, safe_file_operation
from src.discord_notifier import ConfigurationError, DiscordAPIError


class TestResultType(unittest.TestCase):
    """Test the Result type for error handling."""

    def test_result_ok(self) -> None:
        """Test successful result creation."""
        result = Result.ok("success")
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == "success"
        assert result.unwrap_or("default") == "success"

    def test_result_err(self) -> None:
        """Test error result creation."""
        error = ValueError("test error")
        result = Result.err(error)
        assert not result.is_ok()
        assert result.is_err()
        assert result.error == error
        assert result.unwrap_or("default") == "default"

    def test_result_unwrap_error(self) -> None:
        """Test unwrap() raises exception on error result."""
        error = ValueError("test error")
        result = Result.err(error)

        with pytest.raises(ValueError) as exc_info:
            result.unwrap()

        assert "Called unwrap() on error result" in str(exc_info.value)


class TestEnhancedErrorHandler(unittest.TestCase):
    """Test enhanced error handler with type safety."""

    def setUp(self) -> None:
        self.logger = Mock()
        self.handler = EnhancedErrorHandler(self.logger)

    def test_safe_json_load_success(self) -> None:
        """Test successful JSON loading."""
        result = self.handler.safe_json_load('{"key": "value"}')

        assert result.is_ok()
        assert result.unwrap() == {"key": "value"}

    def test_safe_json_load_invalid_json(self) -> None:
        """Test JSON loading with invalid JSON."""
        result = self.handler.safe_json_load('{"key": value}')

        assert result.is_err()
        assert isinstance(result.error, json.JSONDecodeError)
        self.logger.exception.assert_called_once()

    def test_safe_json_load_non_dict(self) -> None:
        """Test JSON loading with non-dict result."""
        result = self.handler.safe_json_load('["array", "not", "dict"]')

        assert result.is_err()
        assert isinstance(result.error, json.JSONDecodeError)
        assert "Expected dict" in str(result.error)

    def test_safe_config_load_success(self) -> None:
        """Test successful config loading."""
        config_data = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "debug": True,
        }

        result = self.handler.safe_config_load(config_data)

        assert result.is_ok()
        config = result.unwrap()
        assert config["webhook_url"] == "https://discord.com/api/webhooks/123/abc"
        assert config["debug"]

    def test_safe_config_load_invalid_type(self) -> None:
        """Test config loading with invalid type."""
        result = self.handler.safe_config_load("not a dict")

        assert result.is_err()
        assert isinstance(result.error, TypeError)
        assert "Config must be dict" in str(result.error)

    def test_safe_config_load_missing_credentials(self) -> None:
        """Test config loading with missing credentials."""
        config_data = {"debug": True}  # No webhook_url or bot credentials

        result = self.handler.safe_config_load(config_data)

        assert result.is_err()
        assert isinstance(result.error, ConfigurationError)
        assert "Must provide either webhook_url or bot_token" in str(result.error)

    def test_safe_config_load_bot_credentials(self) -> None:
        """Test config loading with bot credentials."""
        config_data = {
            "bot_token": "bot_token_123",
            "channel_id": "channel_123",
            "debug": False,
        }

        result = self.handler.safe_config_load(config_data)

        assert result.is_ok()
        config = result.unwrap()
        assert config["bot_token"] == "bot_token_123"
        assert config["channel_id"] == "channel_123"

    @patch("urllib.request.urlopen")
    def test_safe_network_request_success(self, mock_urlopen) -> None:
        """Test successful network request."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = self.handler.safe_network_request("https://example.com", b'{"test": "data"}')

        assert result.is_ok()
        assert result.unwrap()

    @patch("urllib.request.urlopen")
    def test_safe_network_request_http_error(self, mock_urlopen) -> None:
        """Test network request with HTTP error."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.HTTPError("https://example.com", 404, "Not Found", {}, None)

        result = self.handler.safe_network_request("https://example.com", b'{"test": "data"}')

        assert result.is_err()
        assert isinstance(result.error, urllib.error.HTTPError)
        assert result.error.code == 404

    @patch("urllib.request.urlopen")
    def test_safe_network_request_url_error(self, mock_urlopen) -> None:
        """Test network request with URL error."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")

        result = self.handler.safe_network_request("https://example.com", b'{"test": "data"}')

        assert result.is_err()
        assert isinstance(result.error, urllib.error.URLError)
        assert str(result.error.reason) == "Connection failed"

    def test_safe_discord_send_invalid_message(self) -> None:
        """Test Discord send with invalid message type."""
        config = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }

        result = self.handler.safe_discord_send("not a dict", config)

        assert result.is_err()
        assert isinstance(result.error, DiscordAPIError)
        assert "Message must be dict" in str(result.error)

    def test_safe_discord_send_missing_embeds(self) -> None:
        """Test Discord send with missing embeds."""
        config = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }

        result = self.handler.safe_discord_send({"content": "test"}, config)

        assert result.is_err()
        assert isinstance(result.error, DiscordAPIError)
        assert "Message must contain embeds" in str(result.error)


class TestSafeFileOperation(unittest.TestCase):
    """Test safe file operation context manager."""

    def test_safe_file_operation_success(self) -> None:
        """Test successful file operation."""
        test_file = Path("test_safe_file.txt")

        try:
            with safe_file_operation(test_file) as temp_path:
                temp_path.write_text("Test content")
                assert temp_path.exists()
                assert temp_path.read_text() == "Test content"

            # File should be moved to final location
            assert test_file.exists()
            assert test_file.read_text() == "Test content"
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    def test_safe_file_operation_cleanup_on_error(self) -> None:
        """Test cleanup when operation fails."""
        test_file = Path("test_safe_file_error.txt")

        try:
            with pytest.raises(ValueError):
                with safe_file_operation(test_file) as temp_path:
                    temp_path.write_text("Test content")
                    # Simulate error during operation
                    raise ValueError("Simulated error")

            # Temp file should be cleaned up
            assert not temp_path.exists()
            # Final file should not exist
            assert not test_file.exists()
        finally:
            # Extra cleanup in case test fails
            if test_file.exists():
                test_file.unlink()


class TestTypeAnnotationImprovement(unittest.TestCase):
    """Test that type annotations improve error handling."""

    def test_exception_variable_typing(self) -> None:
        """Test that exception variables are properly typed."""
        try:
            raise ValueError("test error")
        except ValueError as e:
            # e should be typed as ValueError
            assert isinstance(e, ValueError)
            assert str(e) == "test error"

    def test_union_exception_typing(self) -> None:
        """Test handling of Union exception types."""

        def risky_operation(should_fail: str) -> str:
            if should_fail == "value":
                raise ValueError("Value error")
            if should_fail == "type":
                raise TypeError("Type error")
            return "success"

        # Test ValueError case
        try:
            risky_operation("value")
        except (ValueError, TypeError) as e:
            # e is typed as Union[ValueError, TypeError]
            assert isinstance(e, (ValueError, TypeError))
            if isinstance(e, ValueError):
                assert str(e) == "Value error"

        # Test TypeError case
        try:
            risky_operation("type")
        except (ValueError, TypeError) as e:
            # e is typed as Union[ValueError, TypeError]
            assert isinstance(e, (ValueError, TypeError))
            if isinstance(e, TypeError):
                assert str(e) == "Type error"


if __name__ == "__main__":
    unittest.main()
