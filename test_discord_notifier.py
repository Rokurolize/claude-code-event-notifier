#!/usr/bin/env python3
"""
Unit tests for discord_notifier.py with proper mocking.

Tests the internal logic without making actual network calls.
"""

import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
import discord_notifier


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading with proper precedence."""

    def test_env_vars_override_file(self) -> None:
        """Test that environment variables override file config."""
        # Mock file content
        file_content = """DISCORD_WEBHOOK_URL=file_webhook
DISCORD_TOKEN=file_token
DISCORD_CHANNEL_ID=file_channel
DISCORD_DEBUG=0
"""

        # Mock environment
        with patch.dict(
            os.environ,
            {"DISCORD_WEBHOOK_URL": "env_webhook", "DISCORD_TOKEN": "env_token"},
        ):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=file_content)):
                    config = discord_notifier.ConfigLoader.load()

                    # Env vars should override file
                    self.assertEqual(config.get("webhook_url"), "env_webhook")
                    self.assertEqual(config.get("bot_token"), "env_token")
                    # File value should be used when no env var
                    self.assertEqual(config.get("channel_id"), "file_channel")
                    self.assertFalse(config.get("debug", False))

    def test_file_only_config(self) -> None:
        """Test loading from file when no env vars are set."""
        file_content = """DISCORD_WEBHOOK_URL=test_webhook
DISCORD_DEBUG=1
"""

        with patch.dict(os.environ, {}, clear=True):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data=file_content)):
                    config = discord_notifier.ConfigLoader.load()

                    self.assertEqual(config.get("webhook_url"), "test_webhook")
                    self.assertIsNone(config.get("bot_token"))
                    self.assertTrue(config.get("debug", False))

    def test_no_config_file(self) -> None:
        """Test when config file doesn't exist."""
        with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "env_only"}):
            with patch("pathlib.Path.exists", return_value=False):
                config = discord_notifier.ConfigLoader.load()

                self.assertEqual(config.get("webhook_url"), "env_only")
                self.assertIsNone(config.get("bot_token"))


class TestEventFormatting(unittest.TestCase):
    """Test event formatting functions."""

    def test_format_pre_tool_use_bash(self) -> None:
        """Test formatting PreToolUse event for Bash tool."""
        event_data = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la /home/user/project"},
        }

        result = discord_notifier.format_pre_tool_use(event_data, "12345678")

        self.assertIn("title", result)
        # Type-safe access to optional TypedDict field
        title = result.get("title", "")
        self.assertIn("🔧", title)
        self.assertIn("Bash", title)
        self.assertIn("description", result)
        # Type-safe access to optional TypedDict field
        description = result.get("description", "")
        self.assertIn("ls -la", description)

    def test_format_pre_tool_use_long_command(self) -> None:
        """Test truncation of long commands."""
        # PreToolUse now uses COMMAND_FULL (500 chars), so test with a longer command
        long_command = "x" * 600
        event_data = {"tool_name": "Bash", "tool_input": {"command": long_command}}

        result = discord_notifier.format_pre_tool_use(event_data, "12345678")

        self.assertIn("description", result)
        # Type-safe access to optional TypedDict field
        description = result.get("description", "")
        self.assertIn("...", description)
        # Should contain the truncated command (500 chars) + ...
        self.assertIn("x" * 497 + "...", description)

    def test_format_event_with_unknown_type(self) -> None:
        """Test formatting unknown event types."""
        registry = discord_notifier.FormatterRegistry()
        config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        result = discord_notifier.format_event(
            "UnknownEvent", {"session_id": "test123"}, registry, config
        )

        self.assertIn("embeds", result)
        embeds = result.get("embeds", [])
        self.assertTrue(embeds)  # Check that embeds list is not empty
        embed = embeds[0]
        self.assertIn("title", embed)
        title = embed.get("title", "")
        self.assertIn("UnknownEvent", title)
        self.assertIn("color", embed)
        color = embed.get("color", 0)
        self.assertEqual(color, 0x808080)  # Default gray color

    def test_format_notification_with_mention(self) -> None:
        """Test formatting Notification event with user mention."""
        registry = discord_notifier.FormatterRegistry()
        config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": "123456789012345678",
        }
        result = discord_notifier.format_event(
            "Notification",
            {"session_id": "test123", "message": "Test notification"},
            registry,
            config,
        )

        # Should have content field with mention and message
        self.assertIn("content", result)
        content = result.get("content", "")
        self.assertEqual(content, "<@123456789012345678> Test notification")

        # Should still have embed
        self.assertIn("embeds", result)
        embeds = result.get("embeds", [])
        self.assertTrue(embeds)  # Check that embeds list is not empty
        embed = embeds[0]
        self.assertIn("title", embed)
        title = embed.get("title", "")
        self.assertIn("Notification", title)
        self.assertIn("description", embed)
        description = embed.get("description", "")
        self.assertIn("Test notification", description)


class TestDiscordSending(unittest.TestCase):
    """Test Discord message sending with mocked network calls."""

    def setUp(self) -> None:
        self.config: discord_notifier.Config = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "bot_token": "bot_token_123",
            "channel_id": "channel_123",
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.logger = Mock()

    @patch("urllib.request.urlopen")
    def test_send_webhook_success(self, mock_urlopen: MagicMock) -> None:
        """Test successful webhook send."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        message: discord_notifier.DiscordMessage = {"embeds": [{"title": "Test"}]}
        http_client = discord_notifier.HTTPClient(self.logger)
        result = discord_notifier.send_to_discord(
            message, self.config, self.logger, http_client
        )

        self.assertTrue(result)
        mock_urlopen.assert_called_once()

        # Verify the request
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.full_url, self.config.get("webhook_url"))
        # Check Content-Type header (case-insensitive)
        content_type = None
        for header_name, header_value in request.headers.items():
            if header_name.lower() == "content-type":
                content_type = header_value
                break
        self.assertEqual(content_type, "application/json")

    @patch("urllib.request.urlopen")
    def test_send_webhook_failure_fallback_to_bot(self, mock_urlopen: MagicMock) -> None:
        """Test fallback to bot API when webhook fails."""
        # First call (webhook) fails
        mock_urlopen.side_effect = [
            urllib.error.URLError("Webhook failed"),
            # Second call (bot API) succeeds
            self._create_mock_response(200),
        ]

        message: discord_notifier.DiscordMessage = {"embeds": [{"title": "Test"}]}
        http_client = discord_notifier.HTTPClient(self.logger)
        result = discord_notifier.send_to_discord(
            message, self.config, self.logger, http_client
        )

        self.assertTrue(result)
        self.assertEqual(mock_urlopen.call_count, 2)

        # Verify bot API was called
        bot_request = mock_urlopen.call_args_list[1][0][0]
        channel_id = self.config.get("channel_id")
        self.assertIsNotNone(channel_id)
        self.assertIn(channel_id, bot_request.full_url)
        self.assertIn("Bot", bot_request.headers["Authorization"])

    @patch("urllib.request.urlopen")
    def test_send_both_methods_fail(self, mock_urlopen: MagicMock) -> None:
        """Test when both webhook and bot API fail."""
        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        message: discord_notifier.DiscordMessage = {"embeds": [{"title": "Test"}]}
        http_client = discord_notifier.HTTPClient(self.logger)
        result = discord_notifier.send_to_discord(
            message, self.config, self.logger, http_client
        )

        self.assertFalse(result)
        self.assertEqual(self.logger.error.call_count, 2)

    def _create_mock_response(self, status: int) -> MagicMock:
        """Helper to create mock HTTP response."""
        mock_response = MagicMock()
        mock_response.status = status
        mock_response.__enter__.return_value = mock_response
        return mock_response


class TestMainFunction(unittest.TestCase):
    """Test the main function with mocked stdin and Discord sending."""

    @patch("sys.stdin.read")
    @patch("discord_notifier.send_to_discord")
    @patch("discord_notifier.ConfigLoader.load")
    def test_main_success(
        self, 
        mock_load_config: MagicMock, 
        mock_send: MagicMock, 
        mock_stdin: MagicMock
    ) -> None:
        """Test successful event processing."""
        # Mock configuration
        mock_load_config.return_value = {
            "webhook_url": "test_webhook",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }

        # Mock stdin with valid event
        event_data = {
            "event_type": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo test"},
            "session_id": "test_session_123",
        }
        mock_stdin.return_value = json.dumps(event_data)

        # Mock successful send
        mock_send.return_value = True

        # Run main with mocked sys.exit
        with patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                discord_notifier.main()
            mock_exit.assert_called_once_with(0)

        # Verify send was called
        mock_send.assert_called_once()
        sent_message = mock_send.call_args[0][0]
        self.assertIn("embeds", sent_message)

    @patch("sys.stdin.read")
    @patch("discord_notifier.ConfigLoader.load")
    def test_main_invalid_json(
        self, 
        mock_load_config: MagicMock, 
        mock_stdin: MagicMock
    ) -> None:
        """Test handling of invalid JSON input."""
        mock_load_config.return_value = {
            "webhook_url": "test",
            "debug": True,
            "bot_token": None,
            "channel_id": None,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        mock_stdin.return_value = "invalid json{{"

        with patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                discord_notifier.main()
            mock_exit.assert_called_once_with(0)  # Should still exit 0

    @patch("sys.stdin.read")
    @patch("discord_notifier.ConfigLoader.load")
    def test_main_no_credentials(
        self, 
        mock_load_config: MagicMock, 
        mock_stdin: MagicMock
    ) -> None:
        """Test when no Discord credentials are configured."""
        mock_load_config.return_value = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        # Mock stdin in case it somehow continues past the early exit
        mock_stdin.return_value = ""

        with patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                discord_notifier.main()
            # Should only exit once, at the credential check
            mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
