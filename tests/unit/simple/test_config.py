#!/usr/bin/env python3
"""Unit tests for simple configuration module."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the config module
import sys
# Add simple directory to path for imports
simple_dir = Path(__file__).parent.parent.parent.parent / "src" / "simple"
sys.path.insert(0, str(simple_dir))
from config import load_config


class TestConfig(unittest.TestCase):
    """Test configuration loading and validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_env = os.environ.copy()
        # Clear Discord-related env vars
        for key in list(os.environ.keys()):
            if key.startswith("DISCORD_"):
                del os.environ[key]
    
    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_load_config_with_env_vars(self):
        """Test config loading from environment variables."""
        # Set test environment variables
        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/test"
        os.environ["DISCORD_BOT_TOKEN"] = "test_bot_token"
        os.environ["DISCORD_CHANNEL_ID"] = "123456789"
        os.environ["DISCORD_THREAD_FOR_TASK"] = "1"
        os.environ["DISCORD_DEBUG"] = "true"
        
        config = load_config()
        
        self.assertEqual(config["webhook_url"], "https://discord.com/api/webhooks/test")
        self.assertEqual(config["bot_token"], "test_bot_token")
        self.assertEqual(config["channel_id"], "123456789")
        self.assertTrue(config["use_threads"])
        self.assertTrue(config["debug"])
    
    def test_load_config_with_env_file(self):
        """Test config loading from .env file."""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/file\\n")
            f.write("DISCORD_BOT_TOKEN=file_bot_token\\n")
            f.write("DISCORD_CHANNEL_ID=987654321\\n")
            f.write("DISCORD_THREAD_FOR_TASK=0\\n")
            env_file = f.name
        
        try:
            # Mock the home directory to use our temp file
            with patch.object(Path, 'home', return_value=Path(env_file).parent.parent):
                with patch.object(Path, 'exists', return_value=True):
                    with patch('builtins.open', MagicMock(return_value=open(env_file))):
                        config = load_config()
            
            self.assertEqual(config["webhook_url"], "https://discord.com/api/webhooks/file")
            self.assertEqual(config["bot_token"], "file_bot_token")
            self.assertEqual(config["channel_id"], "987654321")
            self.assertFalse(config["use_threads"])
        finally:
            os.unlink(env_file)
    
    def test_env_vars_override_file(self):
        """Test that environment variables override .env file values."""
        # Set environment variable
        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/env"
        
        # Create temporary .env file with different value
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/file\\n")
            env_file = f.name
        
        try:
            with patch.object(Path, 'home', return_value=Path(env_file).parent.parent):
                with patch.object(Path, 'exists', return_value=True):
                    with patch('builtins.open', MagicMock(return_value=open(env_file))):
                        config = load_config()
            
            # Environment variable should take precedence
            self.assertEqual(config["webhook_url"], "https://discord.com/api/webhooks/env")
        finally:
            os.unlink(env_file)
    
    def test_event_filtering(self):
        """Test event enable/disable filtering."""
        os.environ["DISCORD_EVENT_PRETOOLUSE"] = "0"
        os.environ["DISCORD_EVENT_POSTTOOLUSE"] = "1"
        os.environ["DISCORD_EVENT_NOTIFICATION"] = "true"
        os.environ["DISCORD_EVENT_STOP"] = "false"
        
        config = load_config()
        
        self.assertIn("PostToolUse", config["enabled_events"])
        self.assertIn("Notification", config["enabled_events"])
        self.assertIn("PreToolUse", config["disabled_events"])
        self.assertIn("Stop", config["disabled_events"])
    
    def test_tool_filtering(self):
        """Test tool enable/disable filtering."""
        os.environ["DISCORD_TOOL_READ"] = "0"
        os.environ["DISCORD_TOOL_WRITE"] = "1"
        os.environ["DISCORD_TOOL_BASH"] = "false"
        os.environ["DISCORD_TOOL_TASK"] = "true"
        
        config = load_config()
        
        self.assertIn("Write", config["enabled_tools"])
        self.assertIn("Task", config["enabled_tools"])
        self.assertIn("Read", config["disabled_tools"])
        self.assertIn("Bash", config["disabled_tools"])
    
    def test_default_values(self):
        """Test default configuration values."""
        config = load_config()
        
        # Check defaults
        self.assertIsNone(config.get("webhook_url"))
        self.assertIsNone(config.get("bot_token"))
        self.assertIsNone(config.get("channel_id"))
        self.assertFalse(config.get("use_threads"))
        self.assertFalse(config.get("debug"))
        self.assertEqual(config.get("enabled_events"), [])
        self.assertEqual(config.get("disabled_events"), [])
        self.assertEqual(config.get("enabled_tools"), [])
        self.assertEqual(config.get("disabled_tools"), [])


if __name__ == "__main__":
    unittest.main()