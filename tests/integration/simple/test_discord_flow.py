#!/usr/bin/env python3
"""Integration tests for the complete Discord notification flow."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Import modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.simple.main import process_event
from src.simple.config import get_config


class TestDiscordIntegration(unittest.TestCase):
    """Test complete Discord notification flow."""
    
    def setUp(self):
        """Set up test environment."""
        self.original_env = os.environ.copy()
        # Set test configuration
        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.com/api/webhooks/test/token"
        os.environ["DISCORD_DEBUG"] = "true"
    
    def tearDown(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch('src.simple.discord_client.send_to_discord')
    def test_notification_event_flow(self, mock_send):
        """Test full flow for a Notification event."""
        mock_send.return_value = True
        
        event = {
            "hook_event_name": "Notification",
            "message": "Integration test notification"
        }
        
        # Process the event
        process_event(event)
        
        # Verify Discord was called
        mock_send.assert_called_once()
        message = mock_send.call_args[0][0]
        config = mock_send.call_args[0][1]
        
        # Verify message structure
        self.assertIn("embeds", message)
        self.assertEqual(len(message["embeds"]), 1)
        embed = message["embeds"][0]
        self.assertEqual(embed["title"], "📢 Notification")
        self.assertEqual(embed["description"], "Integration test notification")
        
        # Verify config
        self.assertEqual(config["webhook_url"], "https://discord.com/api/webhooks/test/token")
        self.assertTrue(config["debug"])
    
    @patch('src.simple.discord_client.send_to_discord')
    def test_pre_tool_use_flow(self, mock_send):
        """Test full flow for a PreToolUse event."""
        mock_send.return_value = True
        
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Task",
            "tool_input": {
                "description": "Test task",
                "prompt": "Perform integration test"
            }
        }
        
        process_event(event)
        
        mock_send.assert_called_once()
        message = mock_send.call_args[0][0]
        
        self.assertIn("embeds", message)
        embed = message["embeds"][0]
        self.assertEqual(embed["title"], "🔧 Task Execution Started")
        self.assertIn("Test task", embed["description"])
    
    @patch('src.simple.discord_client.send_to_discord')
    def test_event_filtering(self, mock_send):
        """Test that disabled events are not sent."""
        # Disable PreToolUse events
        os.environ["DISCORD_EVENT_PRETOOLUSE"] = "0"
        
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/test.py"}
        }
        
        process_event(event)
        
        # Should not call Discord
        mock_send.assert_not_called()
    
    @patch('src.simple.discord_client.send_to_discord')
    def test_tool_filtering(self, mock_send):
        """Test that disabled tools are not sent."""
        # Disable Read tool
        os.environ["DISCORD_TOOL_READ"] = "false"
        
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/test.py"}
        }
        
        process_event(event)
        
        # Should not call Discord
        mock_send.assert_not_called()
    
    @patch('src.simple.discord_client.send_to_discord')
    @patch('src.simple.discord_client.create_thread')
    def test_thread_creation_flow(self, mock_create_thread, mock_send):
        """Test thread creation for Task tool."""
        # Enable thread creation
        os.environ["DISCORD_THREAD_FOR_TASK"] = "1"
        os.environ["DISCORD_BOT_TOKEN"] = "test_bot_token"
        os.environ["DISCORD_CHANNEL_ID"] = "123456789"
        
        mock_send.return_value = True
        mock_create_thread.return_value = "987654321"  # Thread ID
        
        event = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Task",
            "tool_input": {
                "description": "Thread test task",
                "prompt": "Test thread creation"
            }
        }
        
        process_event(event)
        
        # Verify thread was created
        mock_create_thread.assert_called_once()
        thread_name = mock_create_thread.call_args[0][1]
        self.assertIn("Thread test task", thread_name)
        
        # Verify message was sent
        mock_send.assert_called_once()
    
    @patch('src.simple.discord_client.send_to_discord')
    def test_error_handling(self, mock_send):
        """Test graceful error handling."""
        # Make send_to_discord raise an exception
        mock_send.side_effect = Exception("Network error")
        
        event = {
            "hook_event_name": "Notification",
            "message": "Test message"
        }
        
        # Should not raise exception (fail-silent principle)
        try:
            process_event(event)
        except Exception:
            self.fail("process_event should not raise exceptions")
        
        # Verify send was attempted
        mock_send.assert_called_once()
    
    def test_invalid_event_handling(self):
        """Test handling of invalid events."""
        # Invalid event structure
        event = {"invalid": "data"}
        
        # Should not raise exception
        try:
            process_event(event)
        except Exception:
            self.fail("process_event should handle invalid events gracefully")
    
    @patch('src.simple.handlers.TaskTracker')
    @patch('src.simple.discord_client.send_to_discord')
    def test_task_tracking_integration(self, mock_send, mock_tracker_class):
        """Test task tracking integration."""
        mock_send.return_value = True
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        # PreToolUse for Task
        event1 = {
            "hook_event_name": "PreToolUse",
            "session_id": "test-session",
            "tool_name": "Task",
            "tool_input": {
                "description": "Tracked task",
                "prompt": "Do something"
            }
        }
        
        process_event(event1)
        
        # Verify task was tracked
        mock_tracker.track_task_start.assert_called_once()
        
        # PostToolUse for Task
        event2 = {
            "hook_event_name": "PostToolUse",
            "session_id": "test-session",
            "tool_name": "Task",
            "tool_input": {
                "description": "Tracked task",
                "prompt": "Do something"
            },
            "tool_response": {"output": "Done"}
        }
        
        process_event(event2)
        
        # Verify task response was tracked
        mock_tracker.track_task_response.assert_called_once()


if __name__ == "__main__":
    unittest.main()