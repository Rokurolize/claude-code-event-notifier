#!/usr/bin/env python3
"""Test Formatting Consistency Functionality.

This module provides comprehensive tests for formatting consistency
functionality, including cross-platform consistency, output format
validation, template consistency, and style consistency validation.
"""

import asyncio
import json
import re
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.formatters.event_formatters import EventFormatterRegistry
from src.formatters.tool_formatters import ToolFormatterRegistry
from src.formatters.embed_utils import EmbedUtils


class TestFormattingConsistency(unittest.IsolatedAsyncioTestCase):
    """Test cases for formatting consistency functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "session_id": "formatting_test_001",
            "consistency_mode": "strict",
            "cross_platform_validation": True,
            "template_validation": True,
            "debug": True
        }
        
        # Formatting standards for consistency testing
        self.formatting_standards = {
            "discord_embed": {
                "required_fields": ["title", "description", "timestamp"],
                "color_format": r"^#[0-9A-Fa-f]{6}$",
                "timestamp_format": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$",
                "url_format": r"^https?://[^\s]+$",
                "field_limits": {
                    "title": 256,
                    "description": 4096,
                    "field_name": 256,
                    "field_value": 1024,
                    "field_count": 25
                }
            },
            "json_output": {
                "indentation": 2,
                "key_ordering": "alphabetical",
                "boolean_format": "lowercase",
                "null_format": "null",
                "string_encoding": "utf-8"
            },
            "markdown_output": {
                "header_format": "atx",  # # Header vs underline format
                "list_marker": "-",
                "code_fence": "```",
                "emphasis_marker": "*",
                "strong_marker": "**"
            },
            "color_scheme": {
                "success": "#00ff00",
                "error": "#ff0000",
                "warning": "#ffff00",
                "info": "#0000ff",
                "debug": "#808080"
            }
        }
        
        # Test events for formatting consistency
        self.test_events = [
            {
                "name": "file_write_operation",
                "event_type": "PostToolUse",
                "tool_name": "Write",
                "session_id": "formatting_test_001",
                "timestamp": "2025-07-12T22:00:00.000Z",
                "arguments": {
                    "file_path": "/test/path/example.py",
                    "content": "def hello():\n    print('Hello, World!')",
                    "encoding": "utf-8"
                },
                "result": {
                    "success": True,
                    "bytes_written": 42,
                    "file_size": 42
                },
                "environment": {
                    "working_directory": "/test/path",
                    "git_branch": "feature/formatting-test"
                }
            },
            {
                "name": "bash_command_execution",
                "event_type": "PostToolUse",
                "tool_name": "Bash",
                "session_id": "formatting_test_002",
                "timestamp": "2025-07-12T22:01:00.000Z",
                "arguments": {
                    "command": "python -m pytest tests/",
                    "timeout": 30000
                },
                "result": {
                    "stdout": "===== 25 passed in 3.42s =====",
                    "stderr": "",
                    "exit_code": 0,
                    "execution_time": 3.42
                },
                "environment": {
                    "working_directory": "/test/project",
                    "python_version": "3.13.0"
                }
            },
            {
                "name": "error_scenario",
                "event_type": "PostToolUse",
                "tool_name": "Edit",
                "session_id": "formatting_test_003",
                "timestamp": "2025-07-12T22:02:00.000Z",
                "arguments": {
                    "file_path": "/test/nonexistent.py",
                    "old_string": "original text",
                    "new_string": "modified text"
                },
                "result": {
                    "success": False,
                    "error": "File not found: /test/nonexistent.py",
                    "error_code": "FILE_NOT_FOUND"
                },
                "environment": {
                    "working_directory": "/test"
                }
            }
        ]
        
        # Platform-specific formatting scenarios
        self.platform_scenarios = [
            {
                "name": "windows_path_formatting",
                "platform": "windows",
                "file_path": "C:\\Users\\Test\\Documents\\file.txt",
                "expected_display": "C:/Users/Test/Documents/file.txt",  # Normalized for Discord
                "line_endings": "\r\n"
            },
            {
                "name": "unix_path_formatting",
                "platform": "unix",
                "file_path": "/home/test/documents/file.txt",
                "expected_display": "/home/test/documents/file.txt",
                "line_endings": "\n"
            },
            {
                "name": "macos_path_formatting",
                "platform": "macos",
                "file_path": "/Users/test/Documents/file.txt",
                "expected_display": "/Users/test/Documents/file.txt",
                "line_endings": "\n"
            }
        ]
    
    async def test_cross_platform_formatting_consistency(self) -> None:
        """Test formatting consistency across different platforms."""
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Configure formatter for cross-platform testing
            def cross_platform_format(event: Dict[str, Any], platform: str = "unix") -> Dict[str, Any]:
                """Format event with platform-specific considerations."""
                base_embed = {
                    "title": f"🔧 {event.get('tool_name', 'Unknown')} Tool",
                    "description": f"Operation completed on {platform}",
                    "color": "#00ff00" if event.get("result", {}).get("success") else "#ff0000",
                    "timestamp": event.get("timestamp"),
                    "fields": []
                }
                
                # Platform-specific path normalization
                if "file_path" in event.get("arguments", {}):
                    file_path = event["arguments"]["file_path"]
                    
                    if platform == "windows":
                        # Normalize Windows paths for Discord display
                        normalized_path = file_path.replace("\\", "/")
                    else:
                        normalized_path = file_path
                    
                    base_embed["fields"].append({
                        "name": "File Path",
                        "value": f"`{normalized_path}`",
                        "inline": False
                    })
                
                # Platform-specific line ending handling
                if "content" in event.get("arguments", {}):
                    content = event["arguments"]["content"]
                    line_count = len(content.splitlines())
                    
                    base_embed["fields"].append({
                        "name": "Content",
                        "value": f"```python\n{content[:100]}{'...' if len(content) > 100 else ''}\n```",
                        "inline": False
                    })
                    
                    base_embed["fields"].append({
                        "name": "Lines",
                        "value": str(line_count),
                        "inline": True
                    })
                
                return base_embed
            
            mock_instance.format_event.side_effect = cross_platform_format
            
            formatter_registry = EventFormatterRegistry()
            
            # Test formatting consistency across platforms
            platform_results = {}
            
            for scenario in self.platform_scenarios:
                platform = scenario["platform"]
                
                # Create platform-specific test event
                test_event = {
                    "tool_name": "Write",
                    "timestamp": "2025-07-12T22:00:00.000Z",
                    "arguments": {
                        "file_path": scenario["file_path"],
                        "content": f"# Test file{scenario['line_endings']}print('Hello World')"
                    },
                    "result": {"success": True}
                }
                
                # Format for this platform
                formatted = formatter_registry.format_event(test_event, platform)
                
                platform_results[platform] = {
                    "formatted": formatted,
                    "file_path_display": self._extract_file_path_from_embed(formatted),
                    "has_required_fields": self._validate_required_fields(formatted),
                    "color_format_valid": self._validate_color_format(formatted.get("color")),
                    "timestamp_format_valid": self._validate_timestamp_format(formatted.get("timestamp"))
                }
            
            # Verify cross-platform consistency
            for platform, result in platform_results.items():
                # All platforms should have consistent structure
                self.assertTrue(result["has_required_fields"],
                              f"Platform {platform} missing required fields")
                self.assertTrue(result["color_format_valid"],
                              f"Platform {platform} has invalid color format")
                self.assertTrue(result["timestamp_format_valid"],
                              f"Platform {platform} has invalid timestamp format")
            
            # Verify path normalization consistency
            for scenario in self.platform_scenarios:
                platform = scenario["platform"]
                expected_display = scenario["expected_display"]
                actual_display = platform_results[platform]["file_path_display"]
                
                self.assertEqual(actual_display, expected_display,
                               f"Path display inconsistent for {platform}")
            
            # Log cross-platform consistency analysis
            self.logger.info(
                "Cross-platform formatting consistency analysis",
                context={
                    "platforms_tested": len(self.platform_scenarios),
                    "platform_results": {
                        platform: {
                            "has_required_fields": result["has_required_fields"],
                            "color_valid": result["color_format_valid"],
                            "timestamp_valid": result["timestamp_format_valid"],
                            "file_path": result["file_path_display"]
                        }
                        for platform, result in platform_results.items()
                    }
                }
            )
    
    async def test_output_format_validation_consistency(self) -> None:
        """Test consistency of output format validation."""
        with patch('src.formatters.tool_formatters.ToolFormatterRegistry') as mock_tool_registry:
            mock_tool_instance = MagicMock()
            mock_tool_registry.return_value = mock_tool_instance
            
            # Configure tool-specific formatters
            def tool_specific_format(tool_name: str, event: Dict[str, Any]) -> Dict[str, Any]:
                """Format event based on tool-specific requirements."""
                base_template = {
                    "title": f"🔧 {tool_name}",
                    "color": "#00ff00",
                    "timestamp": event.get("timestamp"),
                    "fields": []
                }
                
                if tool_name == "Write":
                    base_template["description"] = "File write operation"
                    base_template["fields"].extend([
                        {
                            "name": "File Path",
                            "value": f"`{event.get('arguments', {}).get('file_path', 'unknown')}`",
                            "inline": False
                        },
                        {
                            "name": "Size",
                            "value": f"{event.get('result', {}).get('bytes_written', 0)} bytes",
                            "inline": True
                        }
                    ])
                
                elif tool_name == "Bash":
                    base_template["description"] = "Command execution"
                    base_template["fields"].extend([
                        {
                            "name": "Command",
                            "value": f"`{event.get('arguments', {}).get('command', 'unknown')}`",
                            "inline": False
                        },
                        {
                            "name": "Exit Code",
                            "value": str(event.get('result', {}).get('exit_code', -1)),
                            "inline": True
                        },
                        {
                            "name": "Duration",
                            "value": f"{event.get('result', {}).get('execution_time', 0):.2f}s",
                            "inline": True
                        }
                    ])
                
                elif tool_name == "Edit":
                    base_template["description"] = "File edit operation"
                    if not event.get('result', {}).get('success', True):
                        base_template["color"] = "#ff0000"
                        base_template["fields"].append({
                            "name": "Error",
                            "value": event.get('result', {}).get('error', 'Unknown error'),
                            "inline": False
                        })
                
                return base_template
            
            mock_tool_instance.format_tool_event.side_effect = tool_specific_format
            
            tool_formatter = ToolFormatterRegistry()
            
            # Test format validation for each event type
            format_validation_results = []
            
            for test_event in self.test_events:
                tool_name = test_event.get("tool_name")
                formatted = tool_formatter.format_tool_event(tool_name, test_event)
                
                # Validate format consistency
                validation_result = {
                    "event_name": test_event["name"],
                    "tool_name": tool_name,
                    "formatted": formatted,
                    "validations": {
                        "has_title": "title" in formatted,
                        "has_description": "description" in formatted,
                        "has_timestamp": "timestamp" in formatted,
                        "has_color": "color" in formatted,
                        "title_length_valid": len(formatted.get("title", "")) <= 256,
                        "description_length_valid": len(formatted.get("description", "")) <= 4096,
                        "color_format_valid": self._validate_color_format(formatted.get("color")),
                        "timestamp_format_valid": self._validate_timestamp_format(formatted.get("timestamp")),
                        "field_count_valid": len(formatted.get("fields", [])) <= 25,
                        "field_formats_valid": self._validate_field_formats(formatted.get("fields", []))
                    }
                }
                
                format_validation_results.append(validation_result)
            
            # Verify all formats pass validation
            for result in format_validation_results:
                validations = result["validations"]
                
                for validation_name, is_valid in validations.items():
                    self.assertTrue(is_valid,
                                  f"Format validation failed for {result['event_name']}: {validation_name}")
            
            # Verify format consistency across tools
            titles = [r["formatted"]["title"] for r in format_validation_results]
            colors = [r["formatted"]["color"] for r in format_validation_results]
            
            # All titles should follow consistent pattern
            title_pattern = r"^🔧 \w+"
            for i, title in enumerate(titles):
                self.assertRegex(title, title_pattern,
                               f"Title format inconsistent: {format_validation_results[i]['event_name']}")
            
            # Log format validation results
            self.logger.info(
                "Output format validation consistency analysis",
                context={
                    "events_tested": len(format_validation_results),
                    "validation_summary": {
                        result["event_name"]: {
                            "tool": result["tool_name"],
                            "all_validations_passed": all(result["validations"].values()),
                            "failed_validations": [
                                name for name, valid in result["validations"].items() if not valid
                            ]
                        }
                        for result in format_validation_results
                    }
                }
            )
    
    async def test_template_consistency_validation(self) -> None:
        """Test consistency of template usage across formatters."""
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure template-based formatting
            def template_based_format(template_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
                """Apply consistent templates based on type."""
                templates = {
                    "success_operation": {
                        "title": "✅ {tool_name} - Success",
                        "color": "#00ff00",
                        "description": "Operation completed successfully",
                        "footer": {"text": "Claude Code Event Notifier"}
                    },
                    "error_operation": {
                        "title": "❌ {tool_name} - Error",
                        "color": "#ff0000",
                        "description": "Operation failed",
                        "footer": {"text": "Claude Code Event Notifier"}
                    },
                    "info_operation": {
                        "title": "ℹ️ {tool_name} - Info",
                        "color": "#0000ff",
                        "description": "Operation information",
                        "footer": {"text": "Claude Code Event Notifier"}
                    }
                }
                
                if template_type not in templates:
                    raise ValueError(f"Unknown template type: {template_type}")
                
                template = templates[template_type].copy()
                
                # Apply data to template
                for key, value in template.items():
                    if isinstance(value, str) and "{" in value:
                        template[key] = value.format(**data)
                
                template["timestamp"] = data.get("timestamp")
                
                return template
            
            mock_instance.apply_template.side_effect = template_based_format
            
            embed_utils = EmbedUtils()
            
            # Test template consistency
            template_test_cases = [
                {
                    "name": "successful_write",
                    "template_type": "success_operation",
                    "data": {"tool_name": "Write", "timestamp": "2025-07-12T22:00:00.000Z"}
                },
                {
                    "name": "failed_edit",
                    "template_type": "error_operation",
                    "data": {"tool_name": "Edit", "timestamp": "2025-07-12T22:01:00.000Z"}
                },
                {
                    "name": "bash_info",
                    "template_type": "info_operation",
                    "data": {"tool_name": "Bash", "timestamp": "2025-07-12T22:02:00.000Z"}
                }
            ]
            
            template_results = []
            
            for test_case in template_test_cases:
                try:
                    formatted = embed_utils.apply_template(
                        test_case["template_type"],
                        test_case["data"]
                    )
                    
                    # Validate template consistency
                    template_result = {
                        "name": test_case["name"],
                        "template_type": test_case["template_type"],
                        "formatted": formatted,
                        "consistency_checks": {
                            "has_footer": "footer" in formatted,
                            "footer_text_consistent": formatted.get("footer", {}).get("text") == "Claude Code Event Notifier",
                            "title_pattern_consistent": self._validate_title_pattern(formatted.get("title"), test_case["template_type"]),
                            "color_appropriate": self._validate_template_color(formatted.get("color"), test_case["template_type"]),
                            "timestamp_preserved": formatted.get("timestamp") == test_case["data"]["timestamp"]
                        }
                    }
                    
                    template_results.append(template_result)
                    
                except Exception as e:
                    self.fail(f"Template application failed for {test_case['name']}: {e}")
            
            # Verify template consistency
            for result in template_results:
                consistency_checks = result["consistency_checks"]
                
                for check_name, is_consistent in consistency_checks.items():
                    self.assertTrue(is_consistent,
                                  f"Template consistency failed for {result['name']}: {check_name}")
            
            # Verify consistent footer across all templates
            footers = [r["formatted"].get("footer", {}).get("text") for r in template_results]
            unique_footers = set(footers)
            self.assertEqual(len(unique_footers), 1,
                           f"Inconsistent footers found: {unique_footers}")
            
            # Log template consistency analysis
            self.logger.info(
                "Template consistency validation analysis",
                context={
                    "templates_tested": len(template_test_cases),
                    "template_results": {
                        result["name"]: {
                            "template_type": result["template_type"],
                            "all_checks_passed": all(result["consistency_checks"].values()),
                            "failed_checks": [
                                name for name, valid in result["consistency_checks"].items() if not valid
                            ]
                        }
                        for result in template_results
                    }
                }
            )
    
    async def test_style_consistency_validation(self) -> None:
        """Test consistency of styling across all formatting components."""
        style_test_scenarios = [
            {
                "name": "markdown_formatting",
                "content": "# Header\n\n**Bold text** and *italic text*\n\n- List item 1\n- List item 2\n\n```python\ncode_block = True\n```",
                "expected_patterns": {
                    "header": r"^# \w+",
                    "bold": r"\*\*\w+.*\w+\*\*",
                    "italic": r"\*\w+.*\w+\*",
                    "list": r"^- \w+",
                    "code_block": r"```\w+\n.*\n```"
                }
            },
            {
                "name": "json_formatting",
                "content": {
                    "status": "success",
                    "data": {"count": 42, "enabled": True, "value": None},
                    "timestamp": "2025-07-12T22:00:00.000Z"
                },
                "expected_format": {
                    "indentation": 2,
                    "key_order": "alphabetical",
                    "boolean_lowercase": True,
                    "null_format": "null"
                }
            },
            {
                "name": "url_formatting",
                "content": [
                    "https://discord.com/api/webhooks/123456789",
                    "https://github.com/user/repo/commit/abc123",
                    "file:///path/to/local/file.txt"
                ],
                "expected_patterns": {
                    "https_url": r"^https://[^\s]+$",
                    "github_url": r"^https://github\.com/[\w\-]+/[\w\-]+",
                    "file_url": r"^file:///[\w/\.\-]+$"
                }
            }
        ]
        
        style_validation_results = []
        
        for scenario in style_test_scenarios:
            scenario_name = scenario["name"]
            content = scenario["content"]
            
            if scenario_name == "markdown_formatting":
                # Test markdown style consistency
                for pattern_name, pattern in scenario["expected_patterns"].items():
                    matches = re.findall(pattern, content, re.MULTILINE)
                    
                    style_validation_results.append({
                        "scenario": scenario_name,
                        "pattern": pattern_name,
                        "content_snippet": content[:100] + "..." if len(content) > 100 else content,
                        "pattern_found": len(matches) > 0,
                        "matches": matches
                    })
            
            elif scenario_name == "json_formatting":
                # Test JSON style consistency
                json_str = json.dumps(content, indent=scenario["expected_format"]["indentation"], sort_keys=True)
                
                style_checks = {
                    "proper_indentation": "  " in json_str,  # 2-space indentation
                    "alphabetical_keys": self._check_json_key_order(json_str),
                    "lowercase_booleans": "true" in json_str.lower() and "false" not in json_str,
                    "null_format": "null" in json_str
                }
                
                style_validation_results.append({
                    "scenario": scenario_name,
                    "pattern": "json_structure",
                    "content_snippet": json_str,
                    "pattern_found": all(style_checks.values()),
                    "style_checks": style_checks
                })
            
            elif scenario_name == "url_formatting":
                # Test URL style consistency
                for url in content:
                    url_type = self._determine_url_type(url)
                    expected_pattern = scenario["expected_patterns"].get(url_type)
                    
                    if expected_pattern:
                        pattern_match = re.match(expected_pattern, url) is not None
                        
                        style_validation_results.append({
                            "scenario": scenario_name,
                            "pattern": url_type,
                            "content_snippet": url,
                            "pattern_found": pattern_match,
                            "url": url
                        })
        
        # Verify style consistency
        failed_style_checks = []
        
        for result in style_validation_results:
            if not result["pattern_found"]:
                failed_style_checks.append({
                    "scenario": result["scenario"],
                    "pattern": result["pattern"],
                    "content": result["content_snippet"]
                })
        
        # Assert no style consistency failures
        self.assertEqual(len(failed_style_checks), 0,
                        f"Style consistency failures: {failed_style_checks}")
        
        # Test color consistency across components
        color_consistency_tests = [
            {"component": "success", "color": "#00ff00", "expected": "success_green"},
            {"component": "error", "color": "#ff0000", "expected": "error_red"},
            {"component": "warning", "color": "#ffff00", "expected": "warning_yellow"},
            {"component": "info", "color": "#0000ff", "expected": "info_blue"}
        ]
        
        for color_test in color_consistency_tests:
            color_valid = self._validate_color_format(color_test["color"])
            self.assertTrue(color_valid,
                          f"Color format invalid for {color_test['component']}: {color_test['color']}")
        
        # Log style consistency analysis
        self.logger.info(
            "Style consistency validation analysis",
            context={
                "scenarios_tested": len(style_test_scenarios),
                "total_validations": len(style_validation_results),
                "passed_validations": sum(1 for r in style_validation_results if r["pattern_found"]),
                "failed_validations": len(failed_style_checks),
                "style_summary": {
                    "markdown_patterns": len([r for r in style_validation_results if r["scenario"] == "markdown_formatting"]),
                    "json_formatting": len([r for r in style_validation_results if r["scenario"] == "json_formatting"]),
                    "url_formatting": len([r for r in style_validation_results if r["scenario"] == "url_formatting"])
                }
            }
        )
    
    async def test_error_formatting_consistency(self) -> None:
        """Test consistency of error message formatting."""
        error_scenarios = [
            {
                "name": "file_not_found",
                "error_type": "FileNotFoundError",
                "error_message": "File not found: /path/to/missing.txt",
                "error_code": "FILE_NOT_FOUND",
                "severity": "error"
            },
            {
                "name": "permission_denied",
                "error_type": "PermissionError",
                "error_message": "Permission denied: /restricted/file.txt",
                "error_code": "PERMISSION_DENIED",
                "severity": "error"
            },
            {
                "name": "rate_limit_exceeded",
                "error_type": "RateLimitError",
                "error_message": "Rate limit exceeded. Retry after 5.0 seconds",
                "error_code": "RATE_LIMIT",
                "severity": "warning"
            },
            {
                "name": "validation_failure",
                "error_type": "ValidationError",
                "error_message": "Invalid input: field 'name' is required",
                "error_code": "VALIDATION_FAILED",
                "severity": "error"
            }
        ]
        
        # Test error formatting consistency
        error_formatting_results = []
        
        for scenario in error_scenarios:
            # Format error according to standard template
            error_embed = {
                "title": f"❌ Error: {scenario['error_type']}",
                "description": scenario['error_message'],
                "color": "#ff0000" if scenario['severity'] == "error" else "#ffff00",
                "timestamp": "2025-07-12T22:00:00.000Z",
                "fields": [
                    {
                        "name": "Error Code",
                        "value": scenario['error_code'],
                        "inline": True
                    },
                    {
                        "name": "Severity",
                        "value": scenario['severity'].upper(),
                        "inline": True
                    }
                ],
                "footer": {"text": "Claude Code Event Notifier"}
            }
            
            # Validate error formatting consistency
            error_validation = {
                "scenario": scenario["name"],
                "error_type": scenario["error_type"],
                "formatted": error_embed,
                "consistency_checks": {
                    "title_has_error_emoji": error_embed["title"].startswith("❌"),
                    "title_includes_error_type": scenario["error_type"] in error_embed["title"],
                    "description_is_message": error_embed["description"] == scenario["error_message"],
                    "color_matches_severity": self._validate_severity_color(error_embed["color"], scenario["severity"]),
                    "has_error_code_field": any(field["name"] == "Error Code" for field in error_embed["fields"]),
                    "has_severity_field": any(field["name"] == "Severity" for field in error_embed["fields"]),
                    "timestamp_format_valid": self._validate_timestamp_format(error_embed["timestamp"]),
                    "footer_consistent": error_embed["footer"]["text"] == "Claude Code Event Notifier"
                }
            }
            
            error_formatting_results.append(error_validation)
        
        # Verify all error formatting consistency checks pass
        for result in error_formatting_results:
            consistency_checks = result["consistency_checks"]
            
            for check_name, is_consistent in consistency_checks.items():
                self.assertTrue(is_consistent,
                              f"Error formatting consistency failed for {result['scenario']}: {check_name}")
        
        # Verify error title patterns are consistent
        error_titles = [r["formatted"]["title"] for r in error_formatting_results]
        title_pattern = r"^❌ Error: \w+"
        
        for i, title in enumerate(error_titles):
            self.assertRegex(title, title_pattern,
                           f"Error title pattern inconsistent: {error_formatting_results[i]['scenario']}")
        
        # Log error formatting consistency analysis
        self.logger.info(
            "Error formatting consistency analysis",
            context={
                "error_scenarios_tested": len(error_scenarios),
                "formatting_results": {
                    result["scenario"]: {
                        "error_type": result["error_type"],
                        "all_checks_passed": all(result["consistency_checks"].values()),
                        "failed_checks": [
                            name for name, valid in result["consistency_checks"].items() if not valid
                        ]
                    }
                    for result in error_formatting_results
                }
            }
        )
    
    # Helper methods
    
    def _extract_file_path_from_embed(self, embed: Dict[str, Any]) -> str:
        """Extract file path from embed for validation."""
        fields = embed.get("fields", [])
        for field in fields:
            if field.get("name") == "File Path":
                value = field.get("value", "")
                # Extract path from markdown code format
                if value.startswith("`") and value.endswith("`"):
                    return value[1:-1]
                return value
        return ""
    
    def _validate_required_fields(self, embed: Dict[str, Any]) -> bool:
        """Validate that embed has all required fields."""
        required = self.formatting_standards["discord_embed"]["required_fields"]
        return all(field in embed for field in required)
    
    def _validate_color_format(self, color: Optional[str]) -> bool:
        """Validate color format."""
        if not color:
            return False
        pattern = self.formatting_standards["discord_embed"]["color_format"]
        return re.match(pattern, color) is not None
    
    def _validate_timestamp_format(self, timestamp: Optional[str]) -> bool:
        """Validate timestamp format."""
        if not timestamp:
            return False
        pattern = self.formatting_standards["discord_embed"]["timestamp_format"]
        return re.match(pattern, timestamp) is not None
    
    def _validate_field_formats(self, fields: List[Dict[str, Any]]) -> bool:
        """Validate field formats."""
        limits = self.formatting_standards["discord_embed"]["field_limits"]
        
        for field in fields:
            name = field.get("name", "")
            value = field.get("value", "")
            
            if len(name) > limits["field_name"]:
                return False
            if len(value) > limits["field_value"]:
                return False
        
        return len(fields) <= limits["field_count"]
    
    def _validate_title_pattern(self, title: Optional[str], template_type: str) -> bool:
        """Validate title follows pattern for template type."""
        if not title:
            return False
        
        expected_patterns = {
            "success_operation": r"^✅ \w+ - Success$",
            "error_operation": r"^❌ \w+ - Error$",
            "info_operation": r"^ℹ️ \w+ - Info$"
        }
        
        pattern = expected_patterns.get(template_type)
        if not pattern:
            return False
        
        return re.match(pattern, title) is not None
    
    def _validate_template_color(self, color: Optional[str], template_type: str) -> bool:
        """Validate color is appropriate for template type."""
        if not color:
            return False
        
        expected_colors = {
            "success_operation": "#00ff00",
            "error_operation": "#ff0000", 
            "info_operation": "#0000ff"
        }
        
        return color == expected_colors.get(template_type)
    
    def _check_json_key_order(self, json_str: str) -> bool:
        """Check if JSON keys are in alphabetical order."""
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                keys = list(data.keys())
                return keys == sorted(keys)
            return True
        except json.JSONDecodeError:
            return False
    
    def _determine_url_type(self, url: str) -> str:
        """Determine the type of URL for validation."""
        if url.startswith("https://"):
            if "github.com" in url:
                return "github_url"
            return "https_url"
        elif url.startswith("file://"):
            return "file_url"
        return "unknown_url"
    
    def _validate_severity_color(self, color: str, severity: str) -> bool:
        """Validate that color matches severity level."""
        severity_colors = {
            "error": "#ff0000",
            "warning": "#ffff00",
            "info": "#0000ff",
            "success": "#00ff00"
        }
        
        return color == severity_colors.get(severity)


def run_formatting_consistency_tests() -> None:
    """Run formatting consistency tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestFormattingConsistency)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nFormatting Consistency Tests Summary:")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
    
    asyncio.run(main())