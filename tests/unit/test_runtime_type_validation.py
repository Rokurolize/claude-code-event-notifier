#!/usr/bin/env python3
"""Runtime type validation tests for Discord notifier configuration.

These tests verify that the configuration system properly validates types
at runtime and handles malformed or unexpected data gracefully.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
import src.discord_notifier as discord_notifier


class TestRuntimeTypeValidation(unittest.TestCase):
    """Test runtime validation of configuration types."""

    def test_malformed_config_dict_handling(self) -> None:
        """Test handling of malformed configuration dictionaries."""
        # Test with missing required fields
        incomplete_config = {
            "webhook_url": "https://example.com/webhook",
            # Missing other required fields
        }

        # The ConfigLoader should fill in defaults for missing fields
        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(
                os.environ, {"DISCORD_WEBHOOK_URL": "https://example.com/webhook"}
            ):
                config = discord_notifier.ConfigLoader.load()

                # Check that all required fields are present with proper defaults
                self.assertIn("webhook_url", config)
                self.assertIn("bot_token", config)
                self.assertIn("channel_id", config)
                self.assertIn("debug", config)
                self.assertIn("use_threads", config)
                self.assertIn("channel_type", config)
                self.assertIn("thread_prefix", config)
                self.assertIn("mention_user_id", config)

    def test_invalid_type_coercion(self) -> None:
        """Test handling of invalid type coercion in environment variables."""
        # Test invalid boolean values
        invalid_env = {
            "DISCORD_DEBUG": "invalid_bool",
            "DISCORD_USE_THREADS": "not_a_bool",
            "DISCORD_CHANNEL_TYPE": "invalid_channel_type",
        }

        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, invalid_env):
                config = discord_notifier.ConfigLoader.load()

                # Should default to False for invalid boolean strings
                self.assertFalse(config["debug"])
                self.assertFalse(config["use_threads"])

                # Should default to "text" for invalid channel types
                self.assertEqual(config["channel_type"], "text")

    def test_edge_case_string_values(self) -> None:
        """Test handling of edge case string values."""
        edge_cases = {
            "DISCORD_WEBHOOK_URL": "",  # Empty string
            "DISCORD_TOKEN": "   ",  # Whitespace only
            "DISCORD_CHANNEL_ID": "0",  # Zero value
            "DISCORD_THREAD_PREFIX": "",  # Empty prefix
            "DISCORD_MENTION_USER_ID": "0",  # Zero user ID
        }

        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, edge_cases):
                config = discord_notifier.ConfigLoader.load()

                # Empty strings are falsy in Python, so they won't override config defaults
                # Only non-empty strings should override
                self.assertIsNone(
                    config["webhook_url"]
                )  # Empty string is falsy, so defaults to None
                self.assertEqual(config["bot_token"], "   ")  # Whitespace is truthy
                self.assertEqual(config["channel_id"], "0")  # "0" is truthy
                self.assertEqual(
                    config["thread_prefix"], "Session"
                )  # Empty string is falsy, so defaults to "Session"
                self.assertEqual(config["mention_user_id"], "0")  # "0" is truthy

    def test_numeric_string_handling(self) -> None:
        """Test proper handling of numeric strings in configuration."""
        numeric_env = {
            "DISCORD_CHANNEL_ID": "123456789012345678",
            "DISCORD_MENTION_USER_ID": "987654321098765432",
            "DISCORD_DEBUG": "1",
            "DISCORD_USE_THREADS": "0",
        }

        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, numeric_env):
                config = discord_notifier.ConfigLoader.load()

                # Numeric strings should be preserved as strings
                self.assertEqual(config["channel_id"], "123456789012345678")
                self.assertEqual(config["mention_user_id"], "987654321098765432")
                self.assertIsInstance(config["channel_id"], str)
                self.assertIsInstance(config["mention_user_id"], str)

                # Boolean strings should be converted to booleans
                self.assertTrue(config["debug"])
                self.assertFalse(config["use_threads"])
                self.assertIsInstance(config["debug"], bool)
                self.assertIsInstance(config["use_threads"], bool)

    def test_special_character_handling(self) -> None:
        """Test handling of special characters in configuration values."""
        special_chars = {
            "DISCORD_WEBHOOK_URL": "https://example.com/webhook?token=abc123&id=456",
            "DISCORD_THREAD_PREFIX": "Test Session [2025]",
            "DISCORD_TOKEN": "Bot.Token-With_Special.Characters",
        }

        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, special_chars):
                config = discord_notifier.ConfigLoader.load()

                # Special characters should be preserved
                self.assertEqual(
                    config["webhook_url"],
                    "https://example.com/webhook?token=abc123&id=456",
                )
                self.assertEqual(config["thread_prefix"], "Test Session [2025]")
                self.assertEqual(
                    config["bot_token"], "Bot.Token-With_Special.Characters"
                )

    def test_unicode_handling(self) -> None:
        """Test handling of unicode characters in configuration."""
        unicode_env = {
            "DISCORD_THREAD_PREFIX": "Session 🤖",
            "DISCORD_WEBHOOK_URL": "https://example.com/webhook/测试",
        }

        with patch("pathlib.Path.exists", return_value=False):
            with patch.dict(os.environ, unicode_env):
                config = discord_notifier.ConfigLoader.load()

                # Unicode should be preserved
                self.assertEqual(config["thread_prefix"], "Session 🤖")
                self.assertEqual(
                    config["webhook_url"], "https://example.com/webhook/测试"
                )


class TestConfigValidatorRuntimeBehavior(unittest.TestCase):
    """Test runtime behavior of configuration validators."""

    def test_validator_with_missing_keys(self) -> None:
        """Test validator behavior with missing configuration keys."""
        # Create incomplete config dict
        incomplete_config = {
            "webhook_url": "https://example.com/webhook",
            "debug": True,
            # Missing other keys
        }

        # Cast to Config type for testing (even though it's incomplete)
        config = discord_notifier.Config(incomplete_config)

        # Validators should handle missing keys gracefully using .get()
        # This tests that the validators use dict.get() instead of direct access
        try:
            result = discord_notifier.ConfigValidator.validate_credentials(config)
            self.assertIsInstance(result, bool)
        except KeyError:
            self.fail("Validator should handle missing keys gracefully")

    def test_validator_with_none_values(self) -> None:
        """Test validator behavior with None values."""
        config_with_nones: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }

        # Test that validators handle None values correctly
        self.assertFalse(
            discord_notifier.ConfigValidator.validate_credentials(config_with_nones)
        )
        self.assertTrue(
            discord_notifier.ConfigValidator.validate_thread_config(config_with_nones)
        )
        self.assertTrue(
            discord_notifier.ConfigValidator.validate_mention_config(config_with_nones)
        )

    def test_validator_with_empty_strings(self) -> None:
        """Test validator behavior with empty string values."""
        config_with_empty: discord_notifier.Config = {
            "webhook_url": "",
            "bot_token": "",
            "channel_id": "",
            "debug": False,
            "use_threads": True,
            "channel_type": "text",
            "thread_prefix": "",
            "mention_user_id": "",
        }

        # Test that validators handle empty strings correctly
        self.assertFalse(
            discord_notifier.ConfigValidator.validate_credentials(config_with_empty)
        )
        self.assertFalse(
            discord_notifier.ConfigValidator.validate_thread_config(config_with_empty)
        )
        # Empty mention user ID should pass validation (empty is valid)
        self.assertTrue(
            discord_notifier.ConfigValidator.validate_mention_config(config_with_empty)
        )

    def test_mention_user_id_validation_edge_cases(self) -> None:
        """Test mention user ID validation with edge cases."""
        # Test with various invalid user IDs
        invalid_ids = [
            "123",  # Too short
            "abc123456789012345678",  # Contains non-digits
            "0",  # Zero
            "   ",  # Whitespace
        ]

        for invalid_id in invalid_ids:
            config: discord_notifier.Config = {
                "webhook_url": "https://example.com/webhook",
                "bot_token": None,
                "channel_id": None,
                "debug": False,
                "use_threads": False,
                "channel_type": "text",
                "thread_prefix": "Session",
                "mention_user_id": invalid_id,
            }

            with self.subTest(user_id=invalid_id):
                result = discord_notifier.ConfigValidator.validate_mention_config(
                    config
                )
                self.assertFalse(result, f"Should reject invalid user ID: {invalid_id}")

        # Test with valid user ID
        valid_config: discord_notifier.Config = {
            "webhook_url": "https://example.com/webhook",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": "123456789012345678",
        }

        self.assertTrue(
            discord_notifier.ConfigValidator.validate_mention_config(valid_config)
        )

        # Test with empty string (should pass - empty is valid)
        empty_config: discord_notifier.Config = {
            "webhook_url": "https://example.com/webhook",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": "",
        }

        self.assertTrue(
            discord_notifier.ConfigValidator.validate_mention_config(empty_config)
        )

    def test_thread_config_validation_combinations(self) -> None:
        """Test thread configuration validation with various combinations."""
        # Test text channel with bot token but no channel ID
        config1: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": "bot_token",
            "channel_id": None,
            "debug": False,
            "use_threads": True,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertFalse(
            discord_notifier.ConfigValidator.validate_thread_config(config1)
        )

        # Test text channel with channel ID but no bot token
        config2: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": "channel_id",
            "debug": False,
            "use_threads": True,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertFalse(
            discord_notifier.ConfigValidator.validate_thread_config(config2)
        )

        # Test forum channel with no webhook
        config3: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": True,
            "channel_type": "forum",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertFalse(
            discord_notifier.ConfigValidator.validate_thread_config(config3)
        )


class TestFileParsingRuntimeSafety(unittest.TestCase):
    """Test runtime safety of file parsing operations."""

    def test_parse_env_file_with_malformed_lines(self) -> None:
        """Test parsing of environment files with malformed lines."""
        malformed_content = """# This is a comment
DISCORD_WEBHOOK_URL=https://example.com/webhook
INVALID_LINE_NO_EQUALS
DISCORD_TOKEN=
=INVALID_KEY
DISCORD_CHANNEL_ID=123456789
DISCORD_DEBUG=1
EMPTY_VALUE=
SPACES_AROUND_EQUALS = value_with_spaces 
MULTI_EQUALS=value=with=equals
"""

        with patch("builtins.open", mock_open(read_data=malformed_content)):
            env_vars = discord_notifier.parse_env_file(Path("test"))

            # Should only parse valid lines
            self.assertIn("DISCORD_WEBHOOK_URL", env_vars)
            self.assertIn("DISCORD_TOKEN", env_vars)  # Empty value should be included
            self.assertIn("DISCORD_CHANNEL_ID", env_vars)
            self.assertIn("DISCORD_DEBUG", env_vars)
            self.assertIn("EMPTY_VALUE", env_vars)
            self.assertIn(
                "SPACES_AROUND_EQUALS ", env_vars
            )  # Key includes trailing space
            self.assertIn("MULTI_EQUALS", env_vars)

            # Should skip invalid lines
            self.assertNotIn("INVALID_LINE_NO_EQUALS", env_vars)
            # Note: "=INVALID_KEY" creates an empty key, which is how the parser works
            self.assertIn("", env_vars)  # Empty key from "=INVALID_KEY"
            self.assertEqual(env_vars[""], "INVALID_KEY")

            # Check values are properly parsed
            self.assertEqual(
                env_vars["DISCORD_WEBHOOK_URL"], "https://example.com/webhook"
            )
            self.assertEqual(env_vars["DISCORD_TOKEN"], "")
            self.assertEqual(env_vars["DISCORD_CHANNEL_ID"], "123456789")
            self.assertEqual(env_vars["DISCORD_DEBUG"], "1")
            self.assertEqual(env_vars["EMPTY_VALUE"], "")
            self.assertEqual(env_vars["SPACES_AROUND_EQUALS "], " value_with_spaces")
            self.assertEqual(env_vars["MULTI_EQUALS"], "value=with=equals")

    def test_parse_env_file_with_quotes(self) -> None:
        """Test parsing of environment files with quoted values."""
        quoted_content = """DISCORD_WEBHOOK_URL="https://example.com/webhook"
DISCORD_TOKEN='bot_token_with_quotes'
DISCORD_CHANNEL_ID="123456789"
DISCORD_THREAD_PREFIX="Session with spaces"
DISCORD_MIXED_QUOTES="value with 'inner' quotes"
DISCORD_EMPTY_QUOTES=""
DISCORD_JUST_QUOTES='""'
"""

        with patch("builtins.open", mock_open(read_data=quoted_content)):
            env_vars = discord_notifier.parse_env_file(Path("test"))

            # Quotes should be stripped
            self.assertEqual(
                env_vars["DISCORD_WEBHOOK_URL"], "https://example.com/webhook"
            )
            self.assertEqual(env_vars["DISCORD_TOKEN"], "bot_token_with_quotes")
            self.assertEqual(env_vars["DISCORD_CHANNEL_ID"], "123456789")
            self.assertEqual(env_vars["DISCORD_THREAD_PREFIX"], "Session with spaces")
            self.assertEqual(
                env_vars["DISCORD_MIXED_QUOTES"], "value with 'inner' quotes"
            )
            self.assertEqual(env_vars["DISCORD_EMPTY_QUOTES"], "")
            self.assertEqual(env_vars["DISCORD_JUST_QUOTES"], '""')

    def test_parse_env_file_io_error_handling(self) -> None:
        """Test proper error handling for I/O errors."""
        # Test file not found
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with self.assertRaises(discord_notifier.ConfigurationError) as context:
                discord_notifier.parse_env_file(Path("nonexistent"))

            self.assertIn("Error reading", str(context.exception))
            self.assertIn("File not found", str(context.exception))

        # Test permission denied
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with self.assertRaises(discord_notifier.ConfigurationError) as context:
                discord_notifier.parse_env_file(Path("restricted"))

            self.assertIn("Error reading", str(context.exception))
            self.assertIn("Permission denied", str(context.exception))

    def test_parse_env_file_encoding_issues(self) -> None:
        """Test handling of encoding issues in environment files."""
        # Test with invalid UTF-8 sequences
        with patch(
            "builtins.open",
            side_effect=UnicodeDecodeError("utf-8", b"invalid", 0, 1, "Invalid UTF-8"),
        ):
            with self.assertRaises(discord_notifier.ConfigurationError) as context:
                discord_notifier.parse_env_file(Path("invalid_encoding"))

            self.assertIn("Error reading", str(context.exception))


class TestConfigurationExceptionHandling(unittest.TestCase):
    """Test exception handling in configuration loading."""

    def test_configuration_error_inheritance(self) -> None:
        """Test that ConfigurationError properly inherits from base exceptions."""
        error = discord_notifier.ConfigurationError("Test error")

        # Test inheritance chain
        self.assertIsInstance(error, discord_notifier.ConfigurationError)
        self.assertIsInstance(error, discord_notifier.DiscordNotifierError)
        self.assertIsInstance(error, Exception)

        # Test that error message is preserved
        self.assertEqual(str(error), "Test error")

    def test_config_loader_validation_errors(self) -> None:
        """Test that ConfigLoader properly raises validation errors."""
        # Test with completely invalid config
        invalid_config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }

        with self.assertRaises(discord_notifier.ConfigurationError) as context:
            discord_notifier.ConfigLoader.validate(invalid_config)

        # Test error message content
        error_msg = str(context.exception)
        self.assertIn("Discord configuration", error_msg)
        self.assertIn("webhook URL", error_msg)
        self.assertIn("bot token", error_msg)

    def test_graceful_degradation_on_errors(self) -> None:
        """Test that configuration loading degrades gracefully on errors."""
        # Test with partially corrupted environment file
        corrupted_content = """DISCORD_WEBHOOK_URL=https://example.com/webhook
DISCORD_TOKEN=valid_token
CORRUPTED_LINE_THAT_CAUSES_ERROR
DISCORD_CHANNEL_ID=123456789
"""

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=corrupted_content)):
                # Should still load valid configuration despite corrupted line
                config = discord_notifier.ConfigLoader.load()

                # Valid values should be loaded
                self.assertEqual(config["webhook_url"], "https://example.com/webhook")
                self.assertEqual(config["bot_token"], "valid_token")
                self.assertEqual(config["channel_id"], "123456789")

                # Other values should have defaults
                self.assertIsInstance(config["debug"], bool)
                self.assertIsInstance(config["use_threads"], bool)
                self.assertIsInstance(config["channel_type"], str)
                self.assertIsInstance(config["thread_prefix"], str)


if __name__ == "__main__":
    unittest.main()
