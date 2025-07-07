#!/usr/bin/env python3
"""
Type guard and event data validation tests for Discord notifier.

These tests verify that type guards correctly identify data structures
and that event data validation maintains type safety.
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))
import discord_notifier


class TestTypeGuardFunctions(unittest.TestCase):
    """Test type guard functions for proper type detection."""

    def test_is_valid_event_type_guard(self) -> None:
        """Test is_valid_event_type type guard function."""
        # Test valid event types
        valid_events = ["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]
        for event in valid_events:
            with self.subTest(event=event):
                self.assertTrue(discord_notifier.is_valid_event_type(event))
        
        # Test invalid event types
        invalid_events = ["InvalidEvent", "pretooluse", "NOTIFICATION", "", "Unknown"]
        for event in invalid_events:
            with self.subTest(event=event):
                self.assertFalse(discord_notifier.is_valid_event_type(event))

    def test_tool_specific_type_guards(self) -> None:
        """Test tool-specific type guard functions."""
        # Test is_bash_tool
        self.assertTrue(discord_notifier.is_bash_tool("Bash"))
        self.assertFalse(discord_notifier.is_bash_tool("bash"))
        self.assertFalse(discord_notifier.is_bash_tool("Read"))
        
        # Test is_file_tool
        file_tools = ["Read", "Write", "Edit", "MultiEdit"]
        for tool in file_tools:
            with self.subTest(tool=tool):
                self.assertTrue(discord_notifier.is_file_tool(tool))
        
        non_file_tools = ["Bash", "Glob", "Grep", "LS", "Task", "WebFetch"]
        for tool in non_file_tools:
            with self.subTest(tool=tool):
                self.assertFalse(discord_notifier.is_file_tool(tool))
        
        # Test is_search_tool
        search_tools = ["Glob", "Grep"]
        for tool in search_tools:
            with self.subTest(tool=tool):
                self.assertTrue(discord_notifier.is_search_tool(tool))
        
        non_search_tools = ["Bash", "Read", "Write", "Edit", "LS", "Task", "WebFetch"]
        for tool in non_search_tools:
            with self.subTest(tool=tool):
                self.assertFalse(discord_notifier.is_search_tool(tool))
        
        # Test is_list_tool
        list_tools = ["Glob", "Grep", "LS"]
        for tool in list_tools:
            with self.subTest(tool=tool):
                self.assertTrue(discord_notifier.is_list_tool(tool))
        
        non_list_tools = ["Bash", "Read", "Write", "Edit", "Task", "WebFetch"]
        for tool in non_list_tools:
            with self.subTest(tool=tool):
                self.assertFalse(discord_notifier.is_list_tool(tool))

    def test_event_data_type_guards(self) -> None:
        """Test event data type guard functions."""
        # Test is_tool_event_data
        tool_event_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"}
        }
        self.assertTrue(discord_notifier.is_tool_event_data(tool_event_data))
        
        non_tool_event_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification"
        }
        self.assertFalse(discord_notifier.is_tool_event_data(non_tool_event_data))
        
        # Test is_notification_event_data
        notification_event_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification"
        }
        self.assertTrue(discord_notifier.is_notification_event_data(notification_event_data))
        
        non_notification_event_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash"
        }
        self.assertFalse(discord_notifier.is_notification_event_data(non_notification_event_data))
        
        # Test is_stop_event_data
        stop_event_data = {
            "session_id": "test123",
            "hook_event_name": "Stop"
        }
        self.assertTrue(discord_notifier.is_stop_event_data(stop_event_data))
        
        # Any event data with hook_event_name should pass this guard
        any_event_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash"
        }
        self.assertTrue(discord_notifier.is_stop_event_data(any_event_data))

    def test_tool_input_type_guards(self) -> None:
        """Test tool input type guard functions."""
        # Test is_bash_tool_input
        bash_input = {"command": "ls -la", "description": "List files"}
        self.assertTrue(discord_notifier.is_bash_tool_input(bash_input))
        
        non_bash_input = {"file_path": "/path/to/file", "content": "content"}
        self.assertFalse(discord_notifier.is_bash_tool_input(non_bash_input))
        
        # Test is_file_tool_input
        file_input = {"file_path": "/path/to/file", "content": "content"}
        self.assertTrue(discord_notifier.is_file_tool_input(file_input))
        
        non_file_input = {"command": "ls -la"}
        self.assertFalse(discord_notifier.is_file_tool_input(non_file_input))
        
        # Test is_search_tool_input
        search_input = {"pattern": "*.py", "path": "/src"}
        self.assertTrue(discord_notifier.is_search_tool_input(search_input))
        
        non_search_input = {"command": "ls -la"}
        self.assertFalse(discord_notifier.is_search_tool_input(non_search_input))

    def test_type_guard_edge_cases(self) -> None:
        """Test type guard functions with edge cases."""
        # Test with empty dictionaries
        empty_dict: Dict[str, Any] = {}
        self.assertFalse(discord_notifier.is_tool_event_data(empty_dict))
        self.assertFalse(discord_notifier.is_notification_event_data(empty_dict))
        self.assertFalse(discord_notifier.is_stop_event_data(empty_dict))
        self.assertFalse(discord_notifier.is_bash_tool_input(empty_dict))
        self.assertFalse(discord_notifier.is_file_tool_input(empty_dict))
        self.assertFalse(discord_notifier.is_search_tool_input(empty_dict))
        
        # Test with None values - type guards only check key presence, not value validity
        none_values = {
            "tool_name": None,
            "command": None,
            "file_path": None,
            "pattern": None,
            "message": None,
            "hook_event_name": None
        }
        # Type guards check for key presence only, so these should pass
        self.assertTrue(discord_notifier.is_tool_event_data(none_values))
        self.assertTrue(discord_notifier.is_notification_event_data(none_values))
        self.assertTrue(discord_notifier.is_stop_event_data(none_values))
        self.assertTrue(discord_notifier.is_bash_tool_input(none_values))
        self.assertTrue(discord_notifier.is_file_tool_input(none_values))
        self.assertTrue(discord_notifier.is_search_tool_input(none_values))
        
        # Test with wrong value types
        wrong_types = {
            "tool_name": 123,
            "command": [],
            "file_path": {},
            "pattern": True,
            "message": 456,
            "hook_event_name": []
        }
        # Type guards should still work based on key presence, regardless of value type
        self.assertTrue(discord_notifier.is_tool_event_data(wrong_types))
        self.assertTrue(discord_notifier.is_notification_event_data(wrong_types))
        self.assertTrue(discord_notifier.is_stop_event_data(wrong_types))
        self.assertTrue(discord_notifier.is_bash_tool_input(wrong_types))
        self.assertTrue(discord_notifier.is_file_tool_input(wrong_types))
        self.assertTrue(discord_notifier.is_search_tool_input(wrong_types))


class TestEventDataValidation(unittest.TestCase):
    """Test event data validation functions."""

    def test_base_event_data_validation(self) -> None:
        """Test base event data validation."""
        # Test valid base event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "timestamp": "2025-01-01T00:00:00Z"
        }
        self.assertTrue(discord_notifier.EventDataValidator.validate_base_event_data(valid_data))
        
        # Test missing required fields
        missing_session = {
            "hook_event_name": "PreToolUse"
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_base_event_data(missing_session))
        
        missing_hook_event = {
            "session_id": "test123"
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_base_event_data(missing_hook_event))
        
        # Test empty data
        empty_data: Dict[str, Any] = {}
        self.assertFalse(discord_notifier.EventDataValidator.validate_base_event_data(empty_data))

    def test_tool_event_data_validation(self) -> None:
        """Test tool event data validation."""
        # Test valid tool event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"}
        }
        self.assertTrue(discord_notifier.EventDataValidator.validate_tool_event_data(valid_data))
        
        # Test missing tool-specific fields
        missing_tool_name = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_input": {"command": "ls -la"}
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_tool_event_data(missing_tool_name))
        
        missing_tool_input = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash"
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_tool_event_data(missing_tool_input))
        
        # Test missing base fields
        missing_base = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"}
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_tool_event_data(missing_base))

    def test_notification_event_data_validation(self) -> None:
        """Test notification event data validation."""
        # Test valid notification event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification"
        }
        self.assertTrue(discord_notifier.EventDataValidator.validate_notification_event_data(valid_data))
        
        # Test missing message field
        missing_message = {
            "session_id": "test123",
            "hook_event_name": "Notification"
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_notification_event_data(missing_message))
        
        # Test missing base fields
        missing_base = {
            "message": "Test notification"
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_notification_event_data(missing_base))

    def test_stop_event_data_validation(self) -> None:
        """Test stop event data validation."""
        # Test valid stop event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "Stop",
            "duration": 120.5,
            "tools_used": 5
        }
        self.assertTrue(discord_notifier.EventDataValidator.validate_stop_event_data(valid_data))
        
        # Test minimal stop event data
        minimal_data = {
            "session_id": "test123",
            "hook_event_name": "Stop"
        }
        self.assertTrue(discord_notifier.EventDataValidator.validate_stop_event_data(minimal_data))
        
        # Test missing base fields
        missing_base = {
            "duration": 120.5
        }
        self.assertFalse(discord_notifier.EventDataValidator.validate_stop_event_data(missing_base))


class TestToolInputValidation(unittest.TestCase):
    """Test tool input validation functions."""

    def test_bash_input_validation(self) -> None:
        """Test Bash tool input validation."""
        # Test valid Bash input
        valid_input = {
            "command": "ls -la",
            "description": "List files"
        }
        self.assertTrue(discord_notifier.ToolInputValidator.validate_bash_input(valid_input))
        
        # Test minimal Bash input
        minimal_input = {
            "command": "echo hello"
        }
        self.assertTrue(discord_notifier.ToolInputValidator.validate_bash_input(minimal_input))
        
        # Test missing command
        missing_command = {
            "description": "List files"
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_bash_input(missing_command))
        
        # Test wrong command type
        wrong_type = {
            "command": 123
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_bash_input(wrong_type))

    def test_file_input_validation(self) -> None:
        """Test file tool input validation."""
        # Test valid file input
        valid_input = {
            "file_path": "/path/to/file.txt",
            "content": "file content"
        }
        self.assertTrue(discord_notifier.ToolInputValidator.validate_file_input(valid_input))
        
        # Test minimal file input
        minimal_input = {
            "file_path": "/path/to/file.txt"
        }
        self.assertTrue(discord_notifier.ToolInputValidator.validate_file_input(minimal_input))
        
        # Test missing file_path
        missing_path = {
            "content": "file content"
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_file_input(missing_path))
        
        # Test wrong file_path type
        wrong_type = {
            "file_path": 123
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_file_input(wrong_type))

    def test_search_input_validation(self) -> None:
        """Test search tool input validation."""
        # Test valid search input
        valid_input = {
            "pattern": "*.py",
            "path": "/src",
            "include": "*.txt"
        }
        self.assertTrue(discord_notifier.ToolInputValidator.validate_search_input(valid_input))
        
        # Test minimal search input
        minimal_input = {
            "pattern": "test"
        }
        self.assertTrue(discord_notifier.ToolInputValidator.validate_search_input(minimal_input))
        
        # Test missing pattern
        missing_pattern = {
            "path": "/src"
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_search_input(missing_pattern))
        
        # Test wrong pattern type
        wrong_type = {
            "pattern": 123
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_search_input(wrong_type))

    def test_web_input_validation(self) -> None:
        """Test web tool input validation."""
        # Test valid web input
        valid_input = {
            "url": "https://example.com",
            "prompt": "Extract the title"
        }
        self.assertTrue(discord_notifier.ToolInputValidator.validate_web_input(valid_input))
        
        # Test missing url
        missing_url = {
            "prompt": "Extract the title"
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_web_input(missing_url))
        
        # Test missing prompt
        missing_prompt = {
            "url": "https://example.com"
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_web_input(missing_prompt))
        
        # Test wrong types
        wrong_url_type = {
            "url": 123,
            "prompt": "Extract the title"
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_web_input(wrong_url_type))
        
        wrong_prompt_type = {
            "url": "https://example.com",
            "prompt": 123
        }
        self.assertFalse(discord_notifier.ToolInputValidator.validate_web_input(wrong_prompt_type))


class TestTypeGuardIntegration(unittest.TestCase):
    """Test integration between type guards and validation functions."""

    def test_type_guard_and_validator_consistency(self) -> None:
        """Test that type guards and validators work consistently."""
        # Test tool event data
        tool_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"}
        }
        
        # Type guard should identify it as tool event data
        self.assertTrue(discord_notifier.is_tool_event_data(tool_data))
        
        # Validator should validate it successfully
        self.assertTrue(discord_notifier.EventDataValidator.validate_tool_event_data(tool_data))
        
        # Test notification event data
        notification_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification"
        }
        
        # Type guard should identify it as notification event data
        self.assertTrue(discord_notifier.is_notification_event_data(notification_data))
        
        # Validator should validate it successfully
        self.assertTrue(discord_notifier.EventDataValidator.validate_notification_event_data(notification_data))

    def test_type_guard_negative_cases(self) -> None:
        """Test that type guards correctly reject invalid data."""
        # Test tool event data without tool_name
        invalid_tool_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_input": {"command": "ls -la"}
        }
        
        # Type guard should still pass (only checks for tool_name presence)
        self.assertFalse(discord_notifier.is_tool_event_data(invalid_tool_data))
        
        # Validator should fail
        self.assertFalse(discord_notifier.EventDataValidator.validate_tool_event_data(invalid_tool_data))

    def test_complex_event_data_scenarios(self) -> None:
        """Test complex event data scenarios with multiple validations."""
        # Test PostToolUse event with complex response
        post_tool_data = {
            "session_id": "test123",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_response": {
                "stdout": "file1.txt\nfile2.txt",
                "stderr": "",
                "interrupted": False,
                "isImage": False
            }
        }
        
        # Should pass tool event validation
        self.assertTrue(discord_notifier.is_tool_event_data(post_tool_data))
        self.assertTrue(discord_notifier.EventDataValidator.validate_tool_event_data(post_tool_data))
        
        # Test SubagentStop event
        subagent_stop_data = {
            "session_id": "test123",
            "hook_event_name": "SubagentStop",
            "task_description": "Complete the task",
            "result": "Task completed successfully",
            "execution_time": 45.2,
            "status": "success"
        }
        
        # Should pass stop event validation
        self.assertTrue(discord_notifier.is_stop_event_data(subagent_stop_data))
        self.assertTrue(discord_notifier.EventDataValidator.validate_stop_event_data(subagent_stop_data))


if __name__ == "__main__":
    unittest.main()