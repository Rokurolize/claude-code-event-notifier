#!/usr/bin/env python3
"""Unit tests for simple event handlers."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import the handlers module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.simple.handlers import (
    handle_pre_tool_use,
    handle_post_tool_use,
    handle_notification,
    handle_stop,
    handle_subagent_stop,
    is_event_enabled,
    is_tool_enabled
)


class TestHandlers(unittest.TestCase):
    """Test event handler functions."""
    
    def setUp(self):
        """Set up test configuration."""
        self.test_config = {
            "webhook_url": "https://discord.com/api/webhooks/test",
            "bot_token": None,
            "channel_id": None,
            "use_threads": False,
            "debug": False,
            "enabled_events": [],
            "disabled_events": [],
            "enabled_tools": [],
            "disabled_tools": []
        }
    
    def test_is_event_enabled_default(self):
        """Test event filtering with default settings."""
        # All events should be enabled by default
        self.assertTrue(is_event_enabled("PreToolUse", self.test_config))
        self.assertTrue(is_event_enabled("PostToolUse", self.test_config))
        self.assertTrue(is_event_enabled("Notification", self.test_config))
        self.assertTrue(is_event_enabled("Stop", self.test_config))
    
    def test_is_event_enabled_with_disabled_list(self):
        """Test event filtering with disabled events."""
        config = self.test_config.copy()
        config["disabled_events"] = ["PreToolUse", "Stop"]
        
        self.assertFalse(is_event_enabled("PreToolUse", config))
        self.assertTrue(is_event_enabled("PostToolUse", config))
        self.assertTrue(is_event_enabled("Notification", config))
        self.assertFalse(is_event_enabled("Stop", config))
    
    def test_is_event_enabled_with_enabled_list(self):
        """Test event filtering with enabled events only."""
        config = self.test_config.copy()
        config["enabled_events"] = ["Notification", "PostToolUse"]
        
        self.assertFalse(is_event_enabled("PreToolUse", config))
        self.assertTrue(is_event_enabled("PostToolUse", config))
        self.assertTrue(is_event_enabled("Notification", config))
        self.assertFalse(is_event_enabled("Stop", config))
    
    def test_is_tool_enabled_default(self):
        """Test tool filtering with default settings."""
        # All tools should be enabled by default
        self.assertTrue(is_tool_enabled("Read", self.test_config))
        self.assertTrue(is_tool_enabled("Write", self.test_config))
        self.assertTrue(is_tool_enabled("Task", self.test_config))
    
    def test_is_tool_enabled_with_filters(self):
        """Test tool filtering with enabled/disabled lists."""
        config = self.test_config.copy()
        config["enabled_tools"] = ["Task", "Write"]
        config["disabled_tools"] = ["Read"]
        
        self.assertFalse(is_tool_enabled("Read", config))
        self.assertTrue(is_tool_enabled("Write", config))
        self.assertTrue(is_tool_enabled("Task", config))
        self.assertFalse(is_tool_enabled("Bash", config))  # Not in enabled list
    
    @patch('src.simple.handlers.logger')
    def test_handle_pre_tool_use(self, mock_logger):
        """Test PreToolUse event handler."""
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": {"description": "Test task", "prompt": "Do something"}
        }
        
        # Test with event enabled
        result = handle_pre_tool_use(event, self.test_config)
        
        self.assertIsNotNone(result)
        self.assertIn("embeds", result)
        self.assertEqual(len(result["embeds"]), 1)
        embed = result["embeds"][0]
        self.assertEqual(embed["title"], "🔧 Task Execution Started")
        self.assertIn("Test task", embed["description"])
        
        # Test with event disabled
        config = self.test_config.copy()
        config["disabled_events"] = ["PreToolUse"]
        result = handle_pre_tool_use(event, config)
        self.assertIsNone(result)
        
        # Test with tool disabled
        config = self.test_config.copy()
        config["disabled_tools"] = ["Task"]
        result = handle_pre_tool_use(event, config)
        self.assertIsNone(result)
    
    @patch('src.simple.handlers.logger')
    def test_handle_post_tool_use(self, mock_logger):
        """Test PostToolUse event handler."""
        event = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/test/file.py"},
            "tool_response": {"output": "File contents"}
        }
        
        result = handle_post_tool_use(event, self.test_config)
        
        self.assertIsNotNone(result)
        self.assertIn("embeds", result)
        embed = result["embeds"][0]
        self.assertEqual(embed["title"], "✅ Read Completed")
        self.assertIn("/test/file.py", str(embed["fields"]))
    
    def test_handle_notification(self):
        """Test Notification event handler."""
        event = {
            "hook_event_name": "Notification",
            "message": "Test notification message"
        }
        
        result = handle_notification(event, self.test_config)
        
        self.assertIsNotNone(result)
        self.assertIn("embeds", result)
        embed = result["embeds"][0]
        self.assertEqual(embed["title"], "📢 Notification")
        self.assertEqual(embed["description"], "Test notification message")
    
    def test_handle_stop(self):
        """Test Stop event handler."""
        event = {
            "hook_event_name": "Stop",
            "stop_hook_active": True
        }
        
        result = handle_stop(event, self.test_config)
        
        self.assertIsNotNone(result)
        self.assertIn("embeds", result)
        embed = result["embeds"][0]
        self.assertEqual(embed["title"], "🛑 Session Ended")
    
    @patch('src.simple.handlers.TaskTracker')
    @patch('src.simple.handlers.read_subagent_messages')
    def test_handle_subagent_stop(self, mock_read_messages, mock_tracker_class):
        """Test SubagentStop event handler."""
        # Mock task tracker
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        mock_tracker.get_latest_task.return_value = {
            "description": "Test task",
            "prompt": "Do something"
        }
        
        # Mock transcript reader
        mock_read_messages.return_value = {
            "task": {"description": "Test task", "prompt": "Do something"},
            "response": {"content": "Task completed successfully"}
        }
        
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-session",
            "transcript_path": "/test/transcript.jsonl"
        }
        
        result = handle_subagent_stop(event, self.test_config)
        
        self.assertIsNotNone(result)
        self.assertIn("embeds", result)
        embed = result["embeds"][0]
        self.assertEqual(embed["title"], "🤖 Subagent Task Completed")
        self.assertIn("Test task", embed["description"])
    
    def test_handle_subagent_stop_with_threads(self):
        """Test SubagentStop handler with thread support."""
        config = self.test_config.copy()
        config["use_threads"] = True
        config["bot_token"] = "test_token"
        config["channel_id"] = "123456"
        
        event = {
            "hook_event_name": "SubagentStop",
            "session_id": "test-session"
        }
        
        with patch('src.simple.handlers.TaskTracker') as mock_tracker_class:
            mock_tracker = MagicMock()
            mock_tracker_class.return_value = mock_tracker
            mock_tracker.get_latest_task.return_value = None
            
            result = handle_subagent_stop(event, config)
            
            # Should still return a message even without task info
            self.assertIsNotNone(result)
            self.assertIn("embeds", result)


if __name__ == "__main__":
    unittest.main()