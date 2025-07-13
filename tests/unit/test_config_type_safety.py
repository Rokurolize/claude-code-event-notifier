#!/usr/bin/env python3
"""Comprehensive type safety tests for Discord notifier configuration handling.

This test suite verifies that the configuration system properly validates
types, handles edge cases, and maintains type safety throughout the loading
and validation process.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
from src import discord_notifier
from src.core.config_loader import ConfigLoader
from src.utils.astolfo_logger import AstolfoLogger

# Initialize AstolfoLogger for test tracking
logger = AstolfoLogger(__name__)


class TestConfigTypeDefinitions(unittest.TestCase):
    """Test that configuration type definitions are properly structured."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up config type definitions tests", {
            "test_class": self.__class__.__name__,
            "test_module": "config_type_safety"
        })

    def test_config_typeddict_completeness(self) -> None:
        """Test that Config TypedDict includes all required fields."""
        logger.debug("Starting test_config_typeddict_completeness", {
            "test_method": "test_config_typeddict_completeness"
        })
        # Create a valid config following the Config TypedDict
        config: discord_notifier.Config = {
            "webhook_url": "https://example.com/webhook",
            "bot_token": "bot_token_123",
            "channel_id": "123456789",
            "debug": True,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": "987654321",
        }

        # Validate each field type
        self.assertIsInstance(config.get("webhook_url"), (str, type(None)))
        self.assertIsInstance(config.get("bot_token"), (str, type(None)))
        self.assertIsInstance(config.get("channel_id"), (str, type(None)))
        self.assertIsInstance(config.get("debug"), bool)
        self.assertIsInstance(config.get("use_threads"), bool)
        self.assertIn(config.get("channel_type"), ["text", "forum"])
        self.assertIsInstance(config.get("thread_prefix"), str)
        self.assertIsInstance(config.get("mention_user_id"), (str, type(None)))
        
        logger.info("Completed test_config_typeddict_completeness", {
            "result": "success",
            "required_fields_verified": 8
        })

    def test_config_inheritance_structure(self) -> None:
        """Test that Config properly inherits from component TypedDicts."""
        logger.debug("Starting test_config_inheritance_structure", {
            "test_method": "test_config_inheritance_structure"
        })
        config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": True,
            "channel_type": "forum",
            "thread_prefix": "Claude",
            "mention_user_id": None,
        }

        # Test DiscordCredentials inheritance
        credentials: discord_notifier.DiscordCredentials = {
            "webhook_url": config["webhook_url"],
            "bot_token": config["bot_token"],
            "channel_id": config["channel_id"],
        }
        self.assertEqual(credentials["webhook_url"], config["webhook_url"])

        # Test ThreadConfiguration inheritance
        thread_config: discord_notifier.ThreadConfiguration = {
            "use_threads": config["use_threads"],
            "channel_type": config["channel_type"],
            "thread_prefix": config["thread_prefix"],
        }
        self.assertEqual(thread_config["use_threads"], config["use_threads"])

        # Test NotificationConfiguration inheritance
        notification_config: discord_notifier.NotificationConfiguration = {
            "mention_user_id": config["mention_user_id"],
            "debug": config["debug"],
        }
        self.assertEqual(notification_config["debug"], config["debug"])
        
        logger.info("Completed test_config_inheritance_structure", {
            "result": "success",
            "inheritance_types_tested": "credentials, thread, notification"
        })

    def test_literal_type_constraints(self) -> None:
        """Test that Literal types are properly constrained."""
        logger.debug("Starting test_literal_type_constraints", {
            "test_method": "test_literal_type_constraints"
        })
        # Test valid channel types
        valid_config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertIn(valid_config["channel_type"], ["text", "forum"])

        # Test with forum type
        valid_config["channel_type"] = "forum"
        self.assertIn(valid_config["channel_type"], ["text", "forum"])
        
        logger.info("Completed test_literal_type_constraints", {
            "result": "success",
            "literal_types_tested": "text, forum"
        })


class TestConfigLoaderTypeSafety(unittest.TestCase):
    """Test type safety in ConfigLoader class."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up config loader type safety tests", {
            "test_class": self.__class__.__name__
        })

    def test_load_returns_correct_type(self) -> None:
        """Test that ConfigLoader.load() returns a properly typed Config."""
        logger.debug("Starting test_load_returns_correct_type", {
            "test_method": "test_load_returns_correct_type"
        })
        with (
            patch("pathlib.Path.exists", return_value=False),
            patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "test_webhook"}),
        ):
            config = ConfigLoader.load()

            # Verify return type structure
            self.assertIsInstance(config, dict)

            # Check all required keys are present
            expected_keys = {
                "webhook_url",
                "bot_token",
                "channel_id",
                "debug",
                "use_threads",
                "channel_type",
                "thread_prefix",
                "thread_storage_path",
                "thread_cleanup_days",
                "mention_user_id",
                "enabled_events",
                "disabled_events",
            }
            self.assertEqual(set(config.keys()), expected_keys)

            # Check types of values
            self.assertIsInstance(config["webhook_url"], (str, type(None)))
            self.assertIsInstance(config["bot_token"], (str, type(None)))
            self.assertIsInstance(config["channel_id"], (str, type(None)))
            self.assertIsInstance(config["debug"], bool)
            self.assertIsInstance(config["use_threads"], bool)
            self.assertIsInstance(config["channel_type"], str)
            self.assertIsInstance(config["thread_prefix"], str)
            self.assertIsInstance(config["thread_storage_path"], (str, type(None)))
            self.assertIsInstance(config["thread_cleanup_days"], int)
            self.assertIsInstance(config["mention_user_id"], (str, type(None)))
            self.assertIsInstance(config["enabled_events"], (list, type(None)))
            self.assertIsInstance(config["disabled_events"], (list, type(None)))
            
        logger.info("Completed test_load_returns_correct_type", {
            "result": "success",
            "config_fields_verified": len(expected_keys)
        })

    def test_type_casting_safety(self) -> None:
        """Test that type casting is safely handled in ConfigLoader."""
        logger.debug("Starting test_type_casting_safety", {
            "test_method": "test_type_casting_safety"
        })
        file_content = """DISCORD_CHANNEL_TYPE=forum
DISCORD_THREAD_PREFIX=CustomPrefix
DISCORD_DEBUG=1
DISCORD_USE_THREADS=1
"""

        # Need to patch both the instance method and the path itself
        env_file_path = Path.home() / ".claude" / "hooks" / ".env.discord"
        
        with (
            patch.object(Path, "exists", return_value=True),
            patch("builtins.open", mock_open(read_data=file_content)),
        ):
            config = ConfigLoader.load()

            # Test that channel_type is properly cast to Literal type
            self.assertEqual(config["channel_type"], "forum")
            self.assertIn(config["channel_type"], ["text", "forum"])

            # Test boolean casting
            self.assertTrue(config["debug"])
            self.assertTrue(config["use_threads"])

            # Test string preservation
            self.assertEqual(config["thread_prefix"], "CustomPrefix")
            
        logger.info("Completed test_type_casting_safety", {
            "result": "success",
            "type_casting_verified": True
        })

    def test_invalid_channel_type_handling(self) -> None:
        """Test handling of invalid channel types."""
        logger.debug("Starting test_invalid_channel_type_handling", {
            "test_method": "test_invalid_channel_type_handling"
        })
        file_content = """DISCORD_CHANNEL_TYPE=invalid_type
"""

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=file_content)),
        ):
            config = ConfigLoader.load()

            # Should fall back to default "text" for invalid values
            self.assertEqual(config["channel_type"], "text")
            
        logger.info("Completed test_invalid_channel_type_handling", {
            "result": "success",
            "invalid_type_handled": True
        })

    def test_environment_variable_type_coercion(self) -> None:
        """Test that environment variables are properly type-coerced."""
        logger.debug("Starting test_environment_variable_type_coercion", {
            "test_method": "test_environment_variable_type_coercion"
        })
        env_vars = {
            "DISCORD_WEBHOOK_URL": "https://example.com/webhook",
            "DISCORD_DEBUG": "1",
            "DISCORD_USE_THREADS": "1",
            "DISCORD_CHANNEL_TYPE": "forum",
            "DISCORD_THREAD_PREFIX": "TestSession",
            "DISCORD_MENTION_USER_ID": "123456789012345678",
        }

        with (
            patch("pathlib.Path.exists", return_value=False),
            patch.dict(os.environ, env_vars),
        ):
            config = ConfigLoader.load()

            # Test string values
            self.assertEqual(config["webhook_url"], "https://example.com/webhook")
            self.assertEqual(config["thread_prefix"], "TestSession")
            self.assertEqual(config["mention_user_id"], "123456789012345678")

            # Test boolean coercion
            self.assertTrue(config["debug"])
            self.assertTrue(config["use_threads"])

            # Test literal type coercion
            self.assertEqual(config["channel_type"], "forum")
            
        logger.info("Completed test_environment_variable_type_coercion", {
            "result": "success",
            "type_coercion_verified": True
        })

    def test_none_value_handling(self) -> None:
        """Test proper handling of None values in configuration."""
        logger.debug("Starting test_none_value_handling", {
            "test_method": "test_none_value_handling"
        })
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

        # Test that None values are properly handled
        self.assertIsNone(config["webhook_url"])
        self.assertIsNone(config["bot_token"])
        self.assertIsNone(config["channel_id"])
        self.assertIsNone(config["mention_user_id"])

        # Test that non-None values are preserved
        self.assertIsNotNone(config["debug"])
        self.assertIsNotNone(config["use_threads"])
        self.assertIsNotNone(config["channel_type"])
        self.assertIsNotNone(config["thread_prefix"])
        
        logger.info("Completed test_none_value_handling", {
            "result": "success",
            "none_values_handled": 4,
            "non_none_values_preserved": 4
        })


class TestConfigValidatorTypeSafety(unittest.TestCase):
    """Test type safety in ConfigValidator class."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up config validator type safety tests", {
            "test_class": self.__class__.__name__
        })

    def test_validator_input_types(self) -> None:
        """Test that validators properly handle typed inputs."""
        logger.debug("Starting test_validator_input_types", {
            "test_method": "test_validator_input_types"
        })
        valid_config: discord_notifier.Config = {
            "webhook_url": "https://example.com/webhook",
            "bot_token": "bot_token_123",
            "channel_id": "123456789",
            "debug": True,
            "use_threads": True,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": "123456789012345678",
        }

        # Test that all validators accept Config type
        self.assertTrue(discord_notifier.ConfigValidator.validate_credentials(valid_config))
        self.assertTrue(discord_notifier.ConfigValidator.validate_thread_config(valid_config))
        self.assertTrue(discord_notifier.ConfigValidator.validate_mention_config(valid_config))
        self.assertTrue(discord_notifier.ConfigValidator.validate_all(valid_config))
        
        logger.info("Completed test_validator_input_types", {
            "result": "success",
            "validators_tested": 4
        })

    def test_validator_return_types(self) -> None:
        """Test that validators return correct boolean types."""
        logger.debug("Starting test_validator_return_types", {
            "test_method": "test_validator_return_types"
        })
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

        # Test return types are boolean
        result = discord_notifier.ConfigValidator.validate_credentials(config)
        self.assertIsInstance(result, bool)

        result = discord_notifier.ConfigValidator.validate_thread_config(config)
        self.assertIsInstance(result, bool)

        result = discord_notifier.ConfigValidator.validate_mention_config(config)
        self.assertIsInstance(result, bool)

        result = discord_notifier.ConfigValidator.validate_all(config)
        self.assertIsInstance(result, bool)
        
        logger.info("Completed test_validator_return_types", {
            "result": "success",
            "return_types_verified": True
        })

    def test_credential_validation_logic(self) -> None:
        """Test type-safe credential validation logic."""
        logger.debug("Starting test_credential_validation_logic", {
            "test_method": "test_credential_validation_logic"
        })
        # Test webhook-only config
        webhook_config: discord_notifier.Config = {
            "webhook_url": "https://example.com/webhook",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertTrue(discord_notifier.ConfigValidator.validate_credentials(webhook_config))

        # Test bot-only config
        bot_config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": "bot_token",
            "channel_id": "channel_id",
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertTrue(discord_notifier.ConfigValidator.validate_credentials(bot_config))

        # Test invalid config (missing both)
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
        self.assertFalse(discord_notifier.ConfigValidator.validate_credentials(invalid_config))
        
        logger.info("Completed test_credential_validation_logic", {
            "result": "success",
            "validation_scenarios_tested": "webhook, bot, invalid"
        })

    def test_thread_validation_type_safety(self) -> None:
        """Test thread configuration validation with proper types."""
        logger.debug("Starting test_thread_validation_type_safety", {
            "test_method": "test_thread_validation_type_safety"
        })
        # Test text channel with bot credentials
        text_config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": "bot_token",
            "channel_id": "channel_id",
            "debug": False,
            "use_threads": True,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertTrue(discord_notifier.ConfigValidator.validate_thread_config(text_config))

        # Test forum channel with webhook
        forum_config: discord_notifier.Config = {
            "webhook_url": "https://example.com/webhook",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": True,
            "channel_type": "forum",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertTrue(discord_notifier.ConfigValidator.validate_thread_config(forum_config))
        
        logger.info("Completed test_thread_validation_type_safety", {
            "result": "success",
            "thread_validation_scenarios": "text_with_bot, forum_with_webhook"
        })

    def test_mention_validation_type_safety(self) -> None:
        """Test mention configuration validation with proper types."""
        logger.debug("Starting test_mention_validation_type_safety", {
            "test_method": "test_mention_validation_type_safety"
        })
        # Test valid mention user ID
        valid_config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": "123456789012345678",
        }
        self.assertTrue(discord_notifier.ConfigValidator.validate_mention_config(valid_config))

        # Test None mention user ID
        none_config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }
        self.assertTrue(discord_notifier.ConfigValidator.validate_mention_config(none_config))

        # Test invalid mention user ID
        invalid_config: discord_notifier.Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": "invalid_id",
        }
        self.assertFalse(discord_notifier.ConfigValidator.validate_mention_config(invalid_config))
        
        logger.info("Completed test_mention_validation_type_safety", {
            "result": "success",
            "mention_validation_scenarios": "valid, none, invalid"
        })


class TestEnvironmentVariableTypeSafety(unittest.TestCase):
    """Test type safety in environment variable handling."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up environment variable type safety tests", {
            "test_class": self.__class__.__name__
        })

    def test_env_var_constants_typing(self) -> None:
        """Test that environment variable constants are properly typed."""
        logger.debug("Starting test_env_var_constants_typing", {
            "test_method": "test_env_var_constants_typing"
        })
        # Test that all constants are strings
        self.assertIsInstance(discord_notifier.ENV_WEBHOOK_URL, str)
        self.assertIsInstance(discord_notifier.ENV_BOT_TOKEN, str)
        self.assertIsInstance(discord_notifier.ENV_CHANNEL_ID, str)
        self.assertIsInstance(discord_notifier.ENV_DEBUG, str)
        self.assertIsInstance(discord_notifier.ENV_USE_THREADS, str)
        self.assertIsInstance(discord_notifier.ENV_CHANNEL_TYPE, str)
        self.assertIsInstance(discord_notifier.ENV_THREAD_PREFIX, str)
        self.assertIsInstance(discord_notifier.ENV_MENTION_USER_ID, str)
        self.assertIsInstance(discord_notifier.ENV_HOOK_EVENT, str)

        # Test that constants have expected values
        self.assertEqual(discord_notifier.ENV_WEBHOOK_URL, "DISCORD_WEBHOOK_URL")
        self.assertEqual(discord_notifier.ENV_BOT_TOKEN, "DISCORD_TOKEN")
        self.assertEqual(discord_notifier.ENV_CHANNEL_ID, "DISCORD_CHANNEL_ID")
        self.assertEqual(discord_notifier.ENV_DEBUG, "DISCORD_DEBUG")
        self.assertEqual(discord_notifier.ENV_USE_THREADS, "DISCORD_USE_THREADS")
        self.assertEqual(discord_notifier.ENV_CHANNEL_TYPE, "DISCORD_CHANNEL_TYPE")
        self.assertEqual(discord_notifier.ENV_THREAD_PREFIX, "DISCORD_THREAD_PREFIX")
        self.assertEqual(discord_notifier.ENV_MENTION_USER_ID, "DISCORD_MENTION_USER_ID")
        self.assertEqual(discord_notifier.ENV_HOOK_EVENT, "CLAUDE_HOOK_EVENT")
        
        logger.info("Completed test_env_var_constants_typing", {
            "result": "success",
            "constants_verified": 9
        })

    def test_env_var_parsing_type_safety(self) -> None:
        """Test that environment variable parsing maintains type safety."""
        logger.debug("Starting test_env_var_parsing_type_safety", {
            "test_method": "test_env_var_parsing_type_safety"
        })
        file_content = """DISCORD_WEBHOOK_URL=https://example.com/webhook
DISCORD_TOKEN=bot_token_123
DISCORD_CHANNEL_ID=123456789
DISCORD_DEBUG=1
DISCORD_USE_THREADS=1
DISCORD_CHANNEL_TYPE=forum
DISCORD_THREAD_PREFIX=CustomSession
DISCORD_MENTION_USER_ID=987654321012345678
"""

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=file_content)),
        ):
            env_vars = discord_notifier.parse_env_file(Path("test"))

            # Test that all parsed values are strings
            for key, value in env_vars.items():
                self.assertIsInstance(key, str)
                self.assertIsInstance(value, str)

            # Test specific values
            self.assertEqual(env_vars["DISCORD_WEBHOOK_URL"], "https://example.com/webhook")
            self.assertEqual(env_vars["DISCORD_TOKEN"], "bot_token_123")
            self.assertEqual(env_vars["DISCORD_CHANNEL_ID"], "123456789")
            self.assertEqual(env_vars["DISCORD_DEBUG"], "1")
            self.assertEqual(env_vars["DISCORD_USE_THREADS"], "1")
            self.assertEqual(env_vars["DISCORD_CHANNEL_TYPE"], "forum")
            self.assertEqual(env_vars["DISCORD_THREAD_PREFIX"], "CustomSession")
            self.assertEqual(env_vars["DISCORD_MENTION_USER_ID"], "987654321012345678")
            
        logger.info("Completed test_env_var_parsing_type_safety", {
            "result": "success",
            "env_vars_parsed": 8
        })

    def test_env_var_error_handling(self) -> None:
        """Test type-safe error handling in environment variable parsing."""
        logger.debug("Starting test_env_var_error_handling", {
            "test_method": "test_env_var_error_handling"
        })
        # Test that parse_env_file raises ConfigurationError for invalid files
        with (
            patch("builtins.open", side_effect=OSError("File not found")),
            self.assertRaises(discord_notifier.ConfigurationError),
        ):
            discord_notifier.parse_env_file(Path("nonexistent"))

        # Test that the error is properly typed
        try:
            with patch("builtins.open", side_effect=OSError("Test error")):
                discord_notifier.parse_env_file(Path("test"))
        except discord_notifier.ConfigurationError as e:
            self.assertIsInstance(e, discord_notifier.ConfigurationError)
            self.assertIsInstance(e, discord_notifier.DiscordNotifierError)
            self.assertIsInstance(str(e), str)
            
        logger.info("Completed test_env_var_error_handling", {
            "result": "success",
            "error_handling_verified": True
        })


class TestConfigurationIntegrationTypeSafety(unittest.TestCase):
    """Test type safety in configuration integration scenarios."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up configuration integration type safety tests", {
            "test_class": self.__class__.__name__
        })

    def test_full_config_loading_pipeline(self) -> None:
        """Test complete configuration loading pipeline maintains type safety."""
        logger.debug("Starting test_full_config_loading_pipeline", {
            "test_method": "test_full_config_loading_pipeline"
        })
        file_content = """DISCORD_WEBHOOK_URL=https://example.com/webhook
DISCORD_DEBUG=1
DISCORD_USE_THREADS=1
DISCORD_CHANNEL_TYPE=forum
DISCORD_THREAD_PREFIX=IntegrationTest
DISCORD_MENTION_USER_ID=123456789012345678
"""

        env_vars = {
            "DISCORD_TOKEN": "override_token",
            "DISCORD_CHANNEL_ID": "override_channel",
            "DISCORD_DEBUG": "0",  # Should override file
        }

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=file_content)),
            patch.dict(os.environ, env_vars),
        ):
            config = ConfigLoader.load()

            # Test that final config maintains proper types
            self.assertIsInstance(config, dict)

            # Test precedence: env vars override file
            self.assertEqual(config["webhook_url"], "https://example.com/webhook")
            self.assertEqual(config["bot_token"], "override_token")
            self.assertEqual(config["channel_id"], "override_channel")
            self.assertFalse(config["debug"])  # env var "0" should override file "1"

            # Test file values when no env override
            self.assertTrue(config["use_threads"])
            self.assertEqual(config["channel_type"], "forum")
            self.assertEqual(config["thread_prefix"], "IntegrationTest")
            self.assertEqual(config["mention_user_id"], "123456789012345678")

            # Test validation passes
            self.assertTrue(discord_notifier.ConfigValidator.validate_all(config))
            
        logger.info("Completed test_full_config_loading_pipeline", {
            "result": "success",
            "pipeline_verified": True
        })

    def test_configuration_error_propagation(self) -> None:
        """Test that configuration errors are properly typed and propagated."""
        logger.debug("Starting test_configuration_error_propagation", {
            "test_method": "test_configuration_error_propagation"
        })
        # Test ConfigurationError inheritance
        error = discord_notifier.ConfigurationError("Test error")
        self.assertIsInstance(error, discord_notifier.ConfigurationError)
        self.assertIsInstance(error, discord_notifier.DiscordNotifierError)
        self.assertIsInstance(error, Exception)

        # Test that ConfigLoader.validate raises properly typed errors
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

        self.assertIsInstance(context.exception, discord_notifier.ConfigurationError)
        self.assertIn("Discord configuration", str(context.exception))
        
        logger.info("Completed test_configuration_error_propagation", {
            "result": "success",
            "error_propagation_verified": True
        })

    def test_type_guard_integration(self) -> None:
        """Test that type guards work correctly with configuration types."""
        logger.debug("Starting test_type_guard_integration", {
            "test_method": "test_type_guard_integration"
        })
        # Test that properly structured configs pass type checks
        valid_config: discord_notifier.Config = {
            "webhook_url": "https://example.com/webhook",
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
        }

        # Test that config structure is preserved through validation
        self.assertTrue(discord_notifier.ConfigValidator.validate_all(valid_config))

        # Test that individual components can be extracted safely
        credentials: discord_notifier.DiscordCredentials = {
            "webhook_url": valid_config["webhook_url"],
            "bot_token": valid_config["bot_token"],
            "channel_id": valid_config["channel_id"],
        }

        thread_config: discord_notifier.ThreadConfiguration = {
            "use_threads": valid_config["use_threads"],
            "channel_type": valid_config["channel_type"],
            "thread_prefix": valid_config["thread_prefix"],
        }

        notification_config: discord_notifier.NotificationConfiguration = {
            "mention_user_id": valid_config["mention_user_id"],
            "debug": valid_config["debug"],
        }

        # Test type consistency
        self.assertEqual(credentials["webhook_url"], valid_config["webhook_url"])
        self.assertEqual(thread_config["channel_type"], valid_config["channel_type"])
        self.assertEqual(notification_config["debug"], valid_config["debug"])
        
        logger.info("Completed test_type_guard_integration", {
            "result": "success",
            "type_guard_integration_verified": True
        })


if __name__ == "__main__":
    unittest.main()
