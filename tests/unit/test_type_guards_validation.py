#!/usr/bin/env python3
"""Type guard and event data validation tests for Discord notifier.

These tests verify that type guards correctly identify data structures
and that event data validation maintains type safety.
"""

import sys
import unittest
from pathlib import Path
from typing import Any  # noqa: F401 - Used in test cases

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src import discord_notifier
from src.utils.astolfo_logger import AstolfoLogger
from src.validators import (
    EventDataValidator,
    ToolInputValidator,
    is_bash_tool,
    is_bash_tool_input,
    is_file_tool,
    is_file_tool_input,
    is_list_tool,
    is_notification_event_data,
    is_search_tool,
    is_search_tool_input,
    is_stop_event_data,
    is_tool_event_data,
    is_valid_event_type,
    is_web_tool_input,
)

# Initialize AstolfoLogger for test tracking
logger = AstolfoLogger(__name__)


class TestTypeGuardFunctions(unittest.TestCase):
    """Test type guard functions for proper type detection."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up type guard tests", {
            "test_class": self.__class__.__name__,
            "test_module": "type_guards_validation"
        })

    def test_is_valid_event_type_guard(self) -> None:
        """Test is_valid_event_type type guard function."""
        logger.debug("Starting test_is_valid_event_type_guard", {
            "test_method": "test_is_valid_event_type_guard"
        })
        # Test valid event types
        valid_events = [
            "PreToolUse",
            "PostToolUse",
            "Notification",
            "Stop",
            "SubagentStop",
        ]
        for event in valid_events:
            with self.subTest(event=event):
                assert is_valid_event_type(event)

        # Test invalid event types
        invalid_events = ["InvalidEvent", "pretooluse", "NOTIFICATION", "", "Unknown"]
        for event in invalid_events:
            with self.subTest(event=event):
                assert not is_valid_event_type(event)
        
        logger.info("Completed test_is_valid_event_type_guard", {
            "result": "success",
            "valid_events_tested": len(valid_events),
            "invalid_events_tested": len(invalid_events)
        })

    def test_tool_specific_type_guards(self) -> None:
        """Test tool-specific type guard functions."""
        logger.debug("Starting test_tool_specific_type_guards", {
            "test_method": "test_tool_specific_type_guards"
        })
        # Test is_bash_tool
        assert is_bash_tool("Bash")
        assert not is_bash_tool("bash")
        assert not is_bash_tool("Read")

        # Test is_file_tool
        file_tools = ["Read", "Write", "Edit", "MultiEdit"]
        for tool in file_tools:
            with self.subTest(tool=tool):
                assert is_file_tool(tool)

        non_file_tools = ["Bash", "Glob", "Grep", "LS", "Task", "WebFetch"]
        for tool in non_file_tools:
            with self.subTest(tool=tool):
                assert not is_file_tool(tool)

        # Test is_search_tool
        search_tools = ["Glob", "Grep"]
        for tool in search_tools:
            with self.subTest(tool=tool):
                assert is_search_tool(tool)

        non_search_tools = ["Bash", "Read", "Write", "Edit", "LS", "Task", "WebFetch"]
        for tool in non_search_tools:
            with self.subTest(tool=tool):
                assert not is_search_tool(tool)

        # Test is_list_tool
        list_tools = ["Glob", "Grep", "LS"]
        for tool in list_tools:
            with self.subTest(tool=tool):
                assert is_list_tool(tool)

        non_list_tools = ["Bash", "Read", "Write", "Edit", "Task", "WebFetch"]
        for tool in non_list_tools:
            with self.subTest(tool=tool):
                assert not is_list_tool(tool)
        
        logger.info("Completed test_tool_specific_type_guards", {
            "result": "success",
            "tool_types_tested": "bash, file, search, list"
        })

    def test_event_data_type_guards(self) -> None:
        """Test event data type guard functions."""
        logger.debug("Starting test_event_data_type_guards", {
            "test_method": "test_event_data_type_guards"
        })
        # Test is_tool_event_data
        tool_event_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }
        assert is_tool_event_data(tool_event_data)

        non_tool_event_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification",
        }
        assert not is_tool_event_data(non_tool_event_data)

        # Test is_notification_event_data
        notification_event_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification",
        }
        assert is_notification_event_data(notification_event_data)

        non_notification_event_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
        }
        assert not is_notification_event_data(non_notification_event_data)

        # Test is_stop_event_data
        stop_event_data = {"session_id": "test123", "hook_event_name": "Stop"}
        assert is_stop_event_data(stop_event_data)

        # Any event data with hook_event_name should pass this guard
        any_event_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
        }
        assert is_stop_event_data(any_event_data)
        
        logger.info("Completed test_event_data_type_guards", {
            "result": "success",
            "guard_types_tested": "tool, notification, stop"
        })

    def test_tool_input_type_guards(self) -> None:
        """Test tool input type guard functions."""
        logger.debug("Starting test_tool_input_type_guards", {
            "test_method": "test_tool_input_type_guards"
        })
        # Test is_bash_tool_input
        bash_input = {"command": "ls -la", "description": "List files"}
        assert is_bash_tool_input(bash_input)

        non_bash_input = {"file_path": "/path/to/file", "content": "content"}
        assert not is_bash_tool_input(non_bash_input)

        # Test is_file_tool_input
        file_input = {"file_path": "/path/to/file", "content": "content"}
        assert is_file_tool_input(file_input)

        non_file_input = {"command": "ls -la"}
        assert not is_file_tool_input(non_file_input)

        # Test is_search_tool_input
        search_input = {"pattern": "*.py", "path": "/src"}
        assert is_search_tool_input(search_input)

        non_search_input = {"command": "ls -la"}
        assert not is_search_tool_input(non_search_input)
        
        logger.info("Completed test_tool_input_type_guards", {
            "result": "success",
            "input_types_tested": "bash, file, search"
        })

    def test_type_guard_edge_cases(self) -> None:
        """Test type guard functions with edge cases."""
        logger.debug("Starting test_type_guard_edge_cases", {
            "test_method": "test_type_guard_edge_cases"
        })
        # Test with empty dictionaries
        empty_dict: dict[str, object] = {}
        assert not is_tool_event_data(empty_dict)
        assert not is_notification_event_data(empty_dict)
        assert not is_stop_event_data(empty_dict)
        assert not is_bash_tool_input(empty_dict)
        assert not is_file_tool_input(empty_dict)
        assert not is_search_tool_input(empty_dict)

        # Test with None values - type guards only check key presence, not value validity
        none_values = {
            "tool_name": None,
            "command": None,
            "file_path": None,
            "pattern": None,
            "message": None,
            "hook_event_name": None,
        }
        # Type guards check for key presence only, so these should pass
        assert is_tool_event_data(none_values)
        assert is_notification_event_data(none_values)
        assert is_stop_event_data(none_values)
        assert is_bash_tool_input(none_values)
        assert is_file_tool_input(none_values)
        assert is_search_tool_input(none_values)

        # Test with wrong value types
        wrong_types = {
            "tool_name": 123,
            "command": [],
            "file_path": {},
            "pattern": True,
            "message": 456,
            "hook_event_name": [],
        }
        # Type guards should still work based on key presence, regardless of value type
        assert is_tool_event_data(wrong_types)
        assert is_notification_event_data(wrong_types)
        assert is_stop_event_data(wrong_types)
        assert is_bash_tool_input(wrong_types)
        assert is_file_tool_input(wrong_types)
        assert is_search_tool_input(wrong_types)
        
        logger.info("Completed test_type_guard_edge_cases", {
            "result": "success",
            "edge_cases_tested": "empty, none, wrong_types"
        })


class TestEventDataValidation(unittest.TestCase):
    """Test event data validation functions."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up event data validation tests", {
            "test_class": self.__class__.__name__
        })

    def test_base_event_data_validation(self) -> None:
        """Test base event data validation."""
        logger.debug("Starting test_base_event_data_validation", {
            "test_method": "test_base_event_data_validation"
        })
        # Test valid base event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "timestamp": "2025-01-01T00:00:00Z",
        }
        assert EventDataValidator.validate_base_event_data(valid_data)

        # Test missing required fields
        missing_session = {"hook_event_name": "PreToolUse"}
        assert not EventDataValidator.validate_base_event_data(
            missing_session
        )

        missing_hook_event = {"session_id": "test123"}
        assert not EventDataValidator.validate_base_event_data(
            missing_hook_event
        )

        # Test empty data
        empty_data: dict[str, object] = {}
        assert not EventDataValidator.validate_base_event_data(empty_data)
        
        logger.info("Completed test_base_event_data_validation", {
            "result": "success",
            "validation_cases_tested": "valid, missing_session, missing_hook, empty"
        })

    def test_tool_event_data_validation(self) -> None:
        """Test tool event data validation."""
        logger.debug("Starting test_tool_event_data_validation", {
            "test_method": "test_tool_event_data_validation"
        })
        # Test valid tool event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }
        assert EventDataValidator.validate_tool_event_data(valid_data)

        # Test missing tool-specific fields
        missing_tool_name = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_input": {"command": "ls -la"},
        }
        assert not EventDataValidator.validate_tool_event_data(
            missing_tool_name
        )

        missing_tool_input = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
        }
        assert not EventDataValidator.validate_tool_event_data(
            missing_tool_input
        )

        # Test missing base fields
        missing_base = {"tool_name": "Bash", "tool_input": {"command": "ls -la"}}
        assert not EventDataValidator.validate_tool_event_data(missing_base)
        
        logger.info("Completed test_tool_event_data_validation", {
            "result": "success",
            "validation_cases_tested": "valid, missing_tool_name, missing_tool_input, missing_base"
        })

    def test_notification_event_data_validation(self) -> None:
        """Test notification event data validation."""
        logger.debug("Starting test_notification_event_data_validation", {
            "test_method": "test_notification_event_data_validation"
        })
        # Test valid notification event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification",
        }
        assert EventDataValidator.validate_notification_event_data(
            valid_data
        )

        # Test missing message field
        missing_message = {"session_id": "test123", "hook_event_name": "Notification"}
        assert not EventDataValidator.validate_notification_event_data(
            missing_message
        )

        # Test missing base fields
        missing_base = {"message": "Test notification"}
        assert not EventDataValidator.validate_notification_event_data(
            missing_base
        )
        
        logger.info("Completed test_notification_event_data_validation", {
            "result": "success",
            "validation_cases_tested": "valid, missing_message, missing_base"
        })

    def test_stop_event_data_validation(self) -> None:
        """Test stop event data validation."""
        logger.debug("Starting test_stop_event_data_validation", {
            "test_method": "test_stop_event_data_validation"
        })
        # Test valid stop event data
        valid_data = {
            "session_id": "test123",
            "hook_event_name": "Stop",
            "duration": 120.5,
            "tools_used": 5,
        }
        assert EventDataValidator.validate_stop_event_data(valid_data)

        # Test minimal stop event data
        minimal_data = {"session_id": "test123", "hook_event_name": "Stop"}
        assert EventDataValidator.validate_stop_event_data(minimal_data)

        # Test missing base fields
        missing_base = {"duration": 120.5}
        assert not EventDataValidator.validate_stop_event_data(missing_base)
        
        logger.info("Completed test_stop_event_data_validation", {
            "result": "success",
            "validation_cases_tested": "valid, minimal, missing_base"
        })


class TestToolInputValidation(unittest.TestCase):
    """Test tool input validation functions."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up tool input validation tests", {
            "test_class": self.__class__.__name__
        })

    def test_bash_input_validation(self) -> None:
        """Test Bash tool input validation."""
        logger.debug("Starting test_bash_input_validation", {
            "test_method": "test_bash_input_validation"
        })
        # Test valid Bash input
        valid_input = {"command": "ls -la", "description": "List files"}
        assert ToolInputValidator.validate_bash_input(valid_input)

        # Test minimal Bash input
        minimal_input = {"command": "echo hello"}
        assert ToolInputValidator.validate_bash_input(minimal_input)

        # Test missing command
        missing_command = {"description": "List files"}
        assert not ToolInputValidator.validate_bash_input(missing_command)

        # Test wrong command type
        wrong_type = {"command": 123}
        assert not ToolInputValidator.validate_bash_input(wrong_type)
        
        logger.info("Completed test_bash_input_validation", {
            "result": "success",
            "validation_cases_tested": "valid, minimal, missing_command, wrong_type"
        })

    def test_file_input_validation(self) -> None:
        """Test file tool input validation."""
        logger.debug("Starting test_file_input_validation", {
            "test_method": "test_file_input_validation"
        })
        # Test valid file input
        valid_input = {"file_path": "/path/to/file.txt", "content": "file content"}
        assert ToolInputValidator.validate_file_input(valid_input)

        # Test minimal file input
        minimal_input = {"file_path": "/path/to/file.txt"}
        assert ToolInputValidator.validate_file_input(minimal_input)

        # Test missing file_path
        missing_path = {"content": "file content"}
        assert not ToolInputValidator.validate_file_input(missing_path)

        # Test wrong file_path type
        wrong_type = {"file_path": 123}
        assert not ToolInputValidator.validate_file_input(wrong_type)
        
        logger.info("Completed test_file_input_validation", {
            "result": "success",
            "validation_cases_tested": "valid, minimal, missing_path, wrong_type"
        })

    def test_search_input_validation(self) -> None:
        """Test search tool input validation."""
        logger.debug("Starting test_search_input_validation", {
            "test_method": "test_search_input_validation"
        })
        # Test valid search input
        valid_input = {"pattern": "*.py", "path": "/src", "include": "*.txt"}
        assert ToolInputValidator.validate_search_input(valid_input)

        # Test minimal search input
        minimal_input = {"pattern": "test"}
        assert ToolInputValidator.validate_search_input(minimal_input)

        # Test missing pattern
        missing_pattern = {"path": "/src"}
        assert not ToolInputValidator.validate_search_input(missing_pattern)

        # Test wrong pattern type
        wrong_type = {"pattern": 123}
        assert not ToolInputValidator.validate_search_input(wrong_type)
        
        logger.info("Completed test_search_input_validation", {
            "result": "success",
            "validation_cases_tested": "valid, minimal, missing_pattern, wrong_type"
        })

    def test_web_input_validation(self) -> None:
        """Test web tool input validation."""
        logger.debug("Starting test_web_input_validation", {
            "test_method": "test_web_input_validation"
        })
        # Test valid web input
        valid_input = {"url": "https://example.com", "prompt": "Extract the title"}
        assert ToolInputValidator.validate_web_input(valid_input)

        # Test missing url
        missing_url = {"prompt": "Extract the title"}
        assert not ToolInputValidator.validate_web_input(missing_url)

        # Test missing prompt
        missing_prompt = {"url": "https://example.com"}
        assert not ToolInputValidator.validate_web_input(missing_prompt)

        # Test wrong types
        wrong_url_type = {"url": 123, "prompt": "Extract the title"}
        assert not ToolInputValidator.validate_web_input(wrong_url_type)

        wrong_prompt_type = {"url": "https://example.com", "prompt": 123}
        assert not ToolInputValidator.validate_web_input(wrong_prompt_type)
        
        logger.info("Completed test_web_input_validation", {
            "result": "success",
            "validation_cases_tested": "valid, missing_url, missing_prompt, wrong_types"
        })


class TestTypeGuardIntegration(unittest.TestCase):
    """Test integration between type guards and validation functions."""
    
    def setUp(self) -> None:
        """Set up test environment."""
        logger.debug("Setting up type guard integration tests", {
            "test_class": self.__class__.__name__
        })

    def test_type_guard_and_validator_consistency(self) -> None:
        """Test that type guards and validators work consistently."""
        logger.debug("Starting test_type_guard_and_validator_consistency", {
            "test_method": "test_type_guard_and_validator_consistency"
        })
        # Test tool event data
        tool_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }

        # Type guard should identify it as tool event data
        assert is_tool_event_data(tool_data)

        # Validator should validate it successfully
        assert EventDataValidator.validate_tool_event_data(tool_data)

        # Test notification event data
        notification_data = {
            "session_id": "test123",
            "hook_event_name": "Notification",
            "message": "Test notification",
        }

        # Type guard should identify it as notification event data
        assert is_notification_event_data(notification_data)

        # Validator should validate it successfully
        assert EventDataValidator.validate_notification_event_data(
            notification_data
        )
        
        logger.info("Completed test_type_guard_and_validator_consistency", {
            "result": "success",
            "consistency_verified": True
        })

    def test_type_guard_negative_cases(self) -> None:
        """Test that type guards correctly reject invalid data."""
        logger.debug("Starting test_type_guard_negative_cases", {
            "test_method": "test_type_guard_negative_cases"
        })
        # Test tool event data without tool_name
        invalid_tool_data = {
            "session_id": "test123",
            "hook_event_name": "PreToolUse",
            "tool_input": {"command": "ls -la"},
        }

        # Type guard should still pass (only checks for tool_name presence)
        assert not is_tool_event_data(invalid_tool_data)

        # Validator should fail
        assert not EventDataValidator.validate_tool_event_data(
            invalid_tool_data
        )
        
        logger.info("Completed test_type_guard_negative_cases", {
            "result": "success",
            "negative_cases_verified": True
        })

    def test_complex_event_data_scenarios(self) -> None:
        """Test complex event data scenarios with multiple validations."""
        logger.debug("Starting test_complex_event_data_scenarios", {
            "test_method": "test_complex_event_data_scenarios"
        })
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
                "isImage": False,
            },
        }

        # Should pass tool event validation
        assert is_tool_event_data(post_tool_data)
        assert EventDataValidator.validate_tool_event_data(post_tool_data)

        # Test SubagentStop event
        subagent_stop_data = {
            "session_id": "test123",
            "hook_event_name": "SubagentStop",
            "task_description": "Complete the task",
            "result": "Task completed successfully",
            "execution_time": 45.2,
            "status": "success",
        }

        # Should pass stop event validation
        assert is_stop_event_data(subagent_stop_data)
        assert EventDataValidator.validate_stop_event_data(
            subagent_stop_data
        )
        
        logger.info("Completed test_complex_event_data_scenarios", {
            "result": "success",
            "complex_scenarios_tested": "PostToolUse, SubagentStop"
        })


if __name__ == "__main__":
    unittest.main()
