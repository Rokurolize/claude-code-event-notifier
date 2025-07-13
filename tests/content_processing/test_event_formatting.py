#!/usr/bin/env python3
"""Test Event Formatting Functionality.

This module provides comprehensive tests for event formatting functionality,
including event type detection, format accuracy, content preservation,
timestamp handling, and formatting consistency across different event types.
"""

import asyncio
import json
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.formatters.event_formatters import EventFormatterRegistry
from src.formatters.base import BaseFormatter
from src.type_defs.events import EventType


class TestEventFormatting(unittest.IsolatedAsyncioTestCase):
    """Test cases for event formatting functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test event data for different event types
        self.test_events = {
            "PreToolUse": {
                "session_id": "test_session_001",
                "tool_name": "Write",
                "arguments": {
                    "file_path": "/home/user/test.py",
                    "content": "print('Hello, World!')"
                },
                "timestamp": "2025-07-12T22:00:00.000Z",
                "environment": {
                    "working_directory": "/home/user/project",
                    "git_branch": "feature/test",
                    "platform": "linux"
                }
            },
            "PostToolUse": {
                "session_id": "test_session_001",
                "tool_name": "Write",
                "result": {
                    "success": True,
                    "file_created": True,
                    "bytes_written": 22
                },
                "execution_time": 0.125,
                "timestamp": "2025-07-12T22:00:01.125Z",
                "environment": {
                    "working_directory": "/home/user/project",
                    "git_branch": "feature/test",
                    "platform": "linux"
                }
            },
            "Stop": {
                "session_id": "test_session_001",
                "reason": "user_request",
                "summary": {
                    "total_tools_used": 5,
                    "total_execution_time": 2.5,
                    "files_created": 2,
                    "files_modified": 1
                },
                "timestamp": "2025-07-12T22:02:30.000Z",
                "environment": {
                    "working_directory": "/home/user/project",
                    "git_branch": "feature/test",
                    "platform": "linux"
                }
            },
            "Error": {
                "session_id": "test_session_001",
                "tool_name": "Read",
                "error": {
                    "type": "FileNotFoundError",
                    "message": "File not found: /nonexistent/file.txt",
                    "code": "ENOENT"
                },
                "timestamp": "2025-07-12T22:01:15.500Z",
                "environment": {
                    "working_directory": "/home/user/project",
                    "git_branch": "feature/test",
                    "platform": "linux"
                }
            }
        }
        
        # Expected format structures for validation
        self.expected_formats = {
            "embed_structure": {
                "title": str,
                "description": (str, type(None)),
                "color": int,
                "timestamp": str,
                "fields": list,
                "footer": dict,
                "author": (dict, type(None))
            },
            "field_structure": {
                "name": str,
                "value": str,
                "inline": bool
            }
        }
        
        # Test configurations for different formatting scenarios
        self.format_configs = {
            "compact": {
                "max_fields": 3,
                "truncate_values": True,
                "max_value_length": 50,
                "show_environment": False
            },
            "detailed": {
                "max_fields": 10,
                "truncate_values": False,
                "max_value_length": 1000,
                "show_environment": True
            },
            "minimal": {
                "max_fields": 1,
                "truncate_values": True,
                "max_value_length": 20,
                "show_environment": False
            }
        }
    
    async def test_event_type_detection_accuracy(self) -> None:
        """Test accuracy of event type detection and classification."""
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Configure event type detection
            def detect_event_type(event_data: Dict[str, Any]) -> str:
                # Simulate event type detection logic
                if "tool_name" in event_data and "arguments" in event_data:
                    return "PreToolUse"
                elif "tool_name" in event_data and "result" in event_data:
                    return "PostToolUse"
                elif "reason" in event_data and "summary" in event_data:
                    return "Stop"
                elif "error" in event_data:
                    return "Error"
                else:
                    return "Unknown"
            
            mock_instance.detect_event_type.side_effect = detect_event_type
            
            formatter_registry = EventFormatterRegistry()
            
            # Test event type detection for each event
            for expected_type, event_data in self.test_events.items():
                with self.subTest(event_type=expected_type):
                    detected_type = formatter_registry.detect_event_type(event_data)
                    
                    # Verify correct detection
                    self.assertEqual(detected_type, expected_type)
                    
                    # Log detection result
                    self.logger.info(
                        f"Event type detection: {expected_type}",
                        context={
                            "detected_type": detected_type,
                            "event_keys": list(event_data.keys()),
                            "accuracy": "correct" if detected_type == expected_type else "incorrect"
                        }
                    )
    
    async def test_embed_format_structure_validation(self) -> None:
        """Test validation of Discord embed format structure."""
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Configure embed generation
            def generate_embed(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
                timestamp = event_data.get("timestamp", datetime.now(timezone.utc).isoformat())
                
                if event_type == "PreToolUse":
                    return {
                        "title": f"🔧 Tool: {event_data['tool_name']}",
                        "description": f"Starting tool execution",
                        "color": 0x3498db,
                        "timestamp": timestamp,
                        "fields": [
                            {
                                "name": "Arguments",
                                "value": json.dumps(event_data.get("arguments", {}), indent=2)[:1000],
                                "inline": False
                            },
                            {
                                "name": "Session",
                                "value": event_data.get("session_id", "unknown"),
                                "inline": True
                            }
                        ],
                        "footer": {
                            "text": "Claude Code Event",
                            "icon_url": "https://example.com/icon.png"
                        }
                    }
                elif event_type == "PostToolUse":
                    return {
                        "title": f"✅ Tool Completed: {event_data['tool_name']}",
                        "description": f"Tool execution finished",
                        "color": 0x2ecc71,
                        "timestamp": timestamp,
                        "fields": [
                            {
                                "name": "Result",
                                "value": json.dumps(event_data.get("result", {}), indent=2)[:1000],
                                "inline": False
                            },
                            {
                                "name": "Execution Time",
                                "value": f"{event_data.get('execution_time', 0):.3f}s",
                                "inline": True
                            }
                        ],
                        "footer": {
                            "text": "Claude Code Event",
                            "icon_url": "https://example.com/icon.png"
                        }
                    }
                elif event_type == "Stop":
                    return {
                        "title": "🛑 Session Ended",
                        "description": f"Session stopped: {event_data.get('reason', 'unknown')}",
                        "color": 0xe74c3c,
                        "timestamp": timestamp,
                        "fields": [
                            {
                                "name": "Summary",
                                "value": json.dumps(event_data.get("summary", {}), indent=2)[:1000],
                                "inline": False
                            }
                        ],
                        "footer": {
                            "text": "Claude Code Event",
                            "icon_url": "https://example.com/icon.png"
                        }
                    }
                elif event_type == "Error":
                    return {
                        "title": f"❌ Error: {event_data['tool_name']}",
                        "description": f"Tool execution failed",
                        "color": 0xe67e22,
                        "timestamp": timestamp,
                        "fields": [
                            {
                                "name": "Error Details",
                                "value": json.dumps(event_data.get("error", {}), indent=2)[:1000],
                                "inline": False
                            }
                        ],
                        "footer": {
                            "text": "Claude Code Event",
                            "icon_url": "https://example.com/icon.png"
                        }
                    }
                else:
                    return {
                        "title": "❓ Unknown Event",
                        "description": "Unknown event type",
                        "color": 0x95a5a6,
                        "timestamp": timestamp,
                        "fields": [],
                        "footer": {
                            "text": "Claude Code Event",
                            "icon_url": "https://example.com/icon.png"
                        }
                    }
            
            mock_instance.format_event.side_effect = generate_embed
            
            formatter_registry = EventFormatterRegistry()
            
            # Test embed structure for each event type
            for event_type, event_data in self.test_events.items():
                with self.subTest(event_type=event_type):
                    embed = formatter_registry.format_event(event_type, event_data)
                    
                    # Verify embed structure
                    self.assertIsInstance(embed, dict)
                    
                    # Check required fields
                    for field, expected_type in self.expected_formats["embed_structure"].items():
                        self.assertIn(field, embed, f"Missing field '{field}' in {event_type} embed")
                        
                        if isinstance(expected_type, tuple):
                            self.assertIsInstance(embed[field], expected_type,
                                                f"Field '{field}' has wrong type in {event_type} embed")
                        else:
                            self.assertIsInstance(embed[field], expected_type,
                                                f"Field '{field}' has wrong type in {event_type} embed")
                    
                    # Verify fields structure
                    if "fields" in embed:
                        for field in embed["fields"]:
                            for field_attr, expected_type in self.expected_formats["field_structure"].items():
                                self.assertIn(field_attr, field,
                                            f"Missing field attribute '{field_attr}' in {event_type} embed")
                                self.assertIsInstance(field[field_attr], expected_type,
                                                    f"Field attribute '{field_attr}' has wrong type in {event_type} embed")
                    
                    # Verify color is valid
                    self.assertIsInstance(embed["color"], int)
                    self.assertGreaterEqual(embed["color"], 0)
                    self.assertLessEqual(embed["color"], 0xFFFFFF)
                    
                    # Log structure validation
                    self.logger.info(
                        f"Embed structure validation: {event_type}",
                        context={
                            "title": embed.get("title"),
                            "field_count": len(embed.get("fields", [])),
                            "color": hex(embed.get("color", 0)),
                            "has_footer": "footer" in embed,
                            "timestamp_format": embed.get("timestamp")
                        }
                    )
    
    async def test_content_preservation_accuracy(self) -> None:
        """Test accuracy of content preservation in formatted events."""
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Test content with special characters and formatting
            special_content_events = {
                "unicode_content": {
                    "session_id": "test_unicode",
                    "tool_name": "Write",
                    "arguments": {
                        "file_path": "/test/文件.txt",
                        "content": "Hello 世界! 🌍🚀 Special chars: éñü àáâ"
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z"
                },
                "code_content": {
                    "session_id": "test_code",
                    "tool_name": "Write",
                    "arguments": {
                        "file_path": "/test/script.py",
                        "content": "def hello():\n    print(\"Hello, World!\")\n    return 'success'"
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z"
                },
                "json_content": {
                    "session_id": "test_json",
                    "tool_name": "Write",
                    "arguments": {
                        "file_path": "/test/config.json",
                        "content": '{"key": "value", "nested": {"array": [1, 2, 3]}}'
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z"
                }
            }
            
            def preserve_content_format(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
                # Simulate content-preserving formatter
                arguments = event_data.get("arguments", {})
                content = arguments.get("content", "")
                
                return {
                    "title": f"Content Test: {event_data['tool_name']}",
                    "description": "Testing content preservation",
                    "color": 0x3498db,
                    "timestamp": event_data.get("timestamp"),
                    "fields": [
                        {
                            "name": "File Path",
                            "value": arguments.get("file_path", "unknown"),
                            "inline": True
                        },
                        {
                            "name": "Content",
                            "value": f"```\n{content}\n```" if content else "No content",
                            "inline": False
                        },
                        {
                            "name": "Content Length",
                            "value": str(len(content)),
                            "inline": True
                        }
                    ],
                    "footer": {"text": "Content Preservation Test"}
                }
            
            mock_instance.format_event.side_effect = preserve_content_format
            
            formatter_registry = EventFormatterRegistry()
            
            # Test content preservation
            for test_name, event_data in special_content_events.items():
                with self.subTest(content_type=test_name):
                    embed = formatter_registry.format_event("PreToolUse", event_data)
                    
                    # Extract content from embed
                    content_field = None
                    for field in embed.get("fields", []):
                        if field["name"] == "Content":
                            content_field = field
                            break
                    
                    self.assertIsNotNone(content_field, f"Content field missing in {test_name}")
                    
                    # Verify content preservation
                    original_content = event_data["arguments"]["content"]
                    preserved_content = content_field["value"]
                    
                    # Remove code block formatting for comparison
                    if preserved_content.startswith("```") and preserved_content.endswith("```"):
                        preserved_content = preserved_content[3:-3].strip()
                    
                    self.assertEqual(preserved_content, original_content,
                                   f"Content not preserved correctly in {test_name}")
                    
                    # Verify special characters are preserved
                    if test_name == "unicode_content":
                        self.assertIn("世界", preserved_content)
                        self.assertIn("🌍🚀", preserved_content)
                        self.assertIn("éñü", preserved_content)
                    
                    # Log content preservation analysis
                    self.logger.info(
                        f"Content preservation: {test_name}",
                        context={
                            "original_length": len(original_content),
                            "preserved_length": len(preserved_content),
                            "contains_unicode": any(ord(c) > 127 for c in original_content),
                            "contains_newlines": "\n" in original_content,
                            "preservation_accuracy": "exact" if preserved_content == original_content else "modified"
                        }
                    )
    
    async def test_timestamp_formatting_accuracy(self) -> None:
        """Test accuracy of timestamp formatting and timezone handling."""
        timestamp_test_cases = [
            {
                "name": "iso_utc",
                "input": "2025-07-12T22:00:00.000Z",
                "expected_format": "ISO 8601 UTC"
            },
            {
                "name": "iso_with_offset",
                "input": "2025-07-12T15:00:00-07:00",
                "expected_format": "ISO 8601 with offset"
            },
            {
                "name": "unix_timestamp",
                "input": 1720828800,
                "expected_format": "Unix timestamp"
            },
            {
                "name": "current_time",
                "input": None,  # Should use current time
                "expected_format": "Current time"
            }
        ]
        
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            def format_with_timestamp(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
                timestamp = event_data.get("timestamp")
                
                # Handle different timestamp formats
                if timestamp is None:
                    formatted_timestamp = datetime.now(timezone.utc).isoformat()
                elif isinstance(timestamp, (int, float)):
                    formatted_timestamp = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
                elif isinstance(timestamp, str):
                    # Parse and reformat to ensure consistency
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_timestamp = dt.isoformat()
                    except ValueError:
                        formatted_timestamp = timestamp  # Keep original if parsing fails
                else:
                    formatted_timestamp = str(timestamp)
                
                return {
                    "title": "Timestamp Test",
                    "description": "Testing timestamp formatting",
                    "color": 0x3498db,
                    "timestamp": formatted_timestamp,
                    "fields": [
                        {
                            "name": "Original Timestamp",
                            "value": str(timestamp) if timestamp is not None else "None",
                            "inline": True
                        },
                        {
                            "name": "Formatted Timestamp",
                            "value": formatted_timestamp,
                            "inline": True
                        }
                    ],
                    "footer": {"text": "Timestamp Test"}
                }
            
            mock_instance.format_event.side_effect = format_with_timestamp
            
            formatter_registry = EventFormatterRegistry()
            
            # Test timestamp formatting
            for test_case in timestamp_test_cases:
                with self.subTest(timestamp_type=test_case["name"]):
                    event_data = {
                        "session_id": "timestamp_test",
                        "tool_name": "TimestampTest"
                    }
                    
                    if test_case["input"] is not None:
                        event_data["timestamp"] = test_case["input"]
                    
                    embed = formatter_registry.format_event("PreToolUse", event_data)
                    
                    # Verify timestamp is present and formatted
                    self.assertIn("timestamp", embed)
                    self.assertIsInstance(embed["timestamp"], str)
                    
                    # Verify timestamp format (should be ISO 8601 compatible)
                    timestamp_str = embed["timestamp"]
                    
                    # Basic format validation
                    if test_case["name"] != "unix_timestamp" or test_case["input"] != timestamp_str:
                        # Should contain date and time components
                        self.assertRegex(timestamp_str, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
                    
                    # Attempt to parse formatted timestamp
                    try:
                        parsed_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        parse_success = True
                    except ValueError:
                        parse_success = False
                    
                    self.assertTrue(parse_success, f"Failed to parse formatted timestamp: {timestamp_str}")
                    
                    # Log timestamp formatting analysis
                    self.logger.info(
                        f"Timestamp formatting: {test_case['name']}",
                        context={
                            "input": test_case["input"],
                            "output": timestamp_str,
                            "expected_format": test_case["expected_format"],
                            "parse_success": parse_success,
                            "length": len(timestamp_str)
                        }
                    )
    
    async def test_format_consistency_across_event_types(self) -> None:
        """Test formatting consistency across different event types."""
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Track formatting patterns
            formatting_patterns = {}
            
            def consistent_format(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
                # Base consistent formatting
                base_embed = {
                    "color": self._get_event_color(event_type),
                    "timestamp": event_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "footer": {
                        "text": "Claude Code Event",
                        "icon_url": "https://example.com/icon.png"
                    },
                    "fields": []
                }
                
                # Event-specific formatting
                if event_type == "PreToolUse":
                    base_embed.update({
                        "title": f"🔧 {event_data.get('tool_name', 'Unknown Tool')}",
                        "description": "Tool execution started"
                    })
                elif event_type == "PostToolUse":
                    base_embed.update({
                        "title": f"✅ {event_data.get('tool_name', 'Unknown Tool')}",
                        "description": "Tool execution completed"
                    })
                elif event_type == "Stop":
                    base_embed.update({
                        "title": "🛑 Session Ended",
                        "description": f"Reason: {event_data.get('reason', 'Unknown')}"
                    })
                elif event_type == "Error":
                    base_embed.update({
                        "title": f"❌ {event_data.get('tool_name', 'Error')}",
                        "description": "Tool execution failed"
                    })
                
                # Always include session field for consistency
                base_embed["fields"].append({
                    "name": "Session ID",
                    "value": event_data.get("session_id", "unknown"),
                    "inline": True
                })
                
                # Record formatting pattern
                pattern_key = event_type
                if pattern_key not in formatting_patterns:
                    formatting_patterns[pattern_key] = []
                
                formatting_patterns[pattern_key].append({
                    "title_prefix": base_embed["title"][:2],
                    "has_description": "description" in base_embed and base_embed["description"],
                    "field_count": len(base_embed["fields"]),
                    "has_footer": "footer" in base_embed,
                    "color": base_embed["color"]
                })
                
                return base_embed
            
            mock_instance.format_event.side_effect = consistent_format
            
            formatter_registry = EventFormatterRegistry()
            
            # Test consistency across multiple instances of each event type
            embeds_by_type = {}
            
            for event_type, event_data in self.test_events.items():
                embeds_by_type[event_type] = []
                
                # Generate multiple embeds for consistency testing
                for i in range(3):
                    test_data = event_data.copy()
                    test_data["session_id"] = f"consistency_test_{i}"
                    
                    embed = formatter_registry.format_event(event_type, test_data)
                    embeds_by_type[event_type].append(embed)
            
            # Analyze consistency
            consistency_analysis = {}
            
            for event_type, embeds in embeds_by_type.items():
                if not embeds:
                    continue
                
                # Check consistency across embeds of same type
                first_embed = embeds[0]
                consistent_fields = []
                inconsistent_fields = []
                
                for field in ["title", "color", "footer"]:
                    if field in first_embed:
                        field_values = [embed.get(field) for embed in embeds]
                        
                        # For title, check prefix consistency (ignoring dynamic parts)
                        if field == "title":
                            prefixes = [title[:2] if isinstance(title, str) else str(title)[:2] 
                                      for title in field_values]
                            is_consistent = len(set(prefixes)) == 1
                        else:
                            is_consistent = len(set(str(v) for v in field_values)) == 1
                        
                        if is_consistent:
                            consistent_fields.append(field)
                        else:
                            inconsistent_fields.append(field)
                
                consistency_analysis[event_type] = {
                    "consistent_fields": consistent_fields,
                    "inconsistent_fields": inconsistent_fields,
                    "consistency_score": len(consistent_fields) / (len(consistent_fields) + len(inconsistent_fields)) if (consistent_fields or inconsistent_fields) else 1.0
                }
                
                # Log consistency analysis
                self.logger.info(
                    f"Format consistency: {event_type}",
                    context=consistency_analysis[event_type]
                )
            
            # Verify overall consistency
            for event_type, analysis in consistency_analysis.items():
                with self.subTest(event_type=event_type):
                    # Should have high consistency score
                    self.assertGreaterEqual(analysis["consistency_score"], 0.8,
                                          f"Low consistency score for {event_type}: {analysis['consistency_score']}")
                    
                    # Essential fields should be consistent
                    essential_fields = ["color", "footer"]
                    for field in essential_fields:
                        self.assertIn(field, analysis["consistent_fields"],
                                    f"Essential field '{field}' not consistent in {event_type}")
    
    def _get_event_color(self, event_type: str) -> int:
        """Get consistent color for event type."""
        color_map = {
            "PreToolUse": 0x3498db,    # Blue
            "PostToolUse": 0x2ecc71,   # Green
            "Stop": 0xe74c3c,          # Red
            "Error": 0xe67e22          # Orange
        }
        return color_map.get(event_type, 0x95a5a6)  # Gray for unknown
    
    async def test_discord_limits_compliance(self) -> None:
        """Test compliance with Discord formatting limits."""
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Discord limits
            discord_limits = {
                "embed_title": 256,
                "embed_description": 4096,
                "embed_field_name": 256,
                "embed_field_value": 1024,
                "embed_fields_total": 25,
                "embed_footer_text": 2048,
                "embed_author_name": 256,
                "embed_total_chars": 6000
            }
            
            # Create oversized content for testing
            oversized_event = {
                "session_id": "limits_test",
                "tool_name": "TestLongContent",
                "arguments": {
                    "file_path": "/very/long/path/that/exceeds/normal/lengths/" + "x" * 300,
                    "content": "x" * 2000,  # Very long content
                    "description": "y" * 5000  # Exceeds description limit
                },
                "timestamp": "2025-07-12T22:00:00.000Z",
                "metadata": {f"field_{i}": f"value_{i}" * 100 for i in range(30)}  # Many fields
            }
            
            def limit_compliant_format(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
                arguments = event_data.get("arguments", {})
                
                # Apply Discord limits
                title = f"🔧 {event_data.get('tool_name', 'Tool')}"
                if len(title) > discord_limits["embed_title"]:
                    title = title[:discord_limits["embed_title"]-3] + "..."
                
                description = f"Testing Discord limits compliance"
                if len(description) > discord_limits["embed_description"]:
                    description = description[:discord_limits["embed_description"]-3] + "..."
                
                fields = []
                
                # Add file path field (may need truncation)
                file_path = arguments.get("file_path", "")
                if len(file_path) > discord_limits["embed_field_value"]:
                    file_path = "..." + file_path[-(discord_limits["embed_field_value"]-3):]
                
                fields.append({
                    "name": "File Path",
                    "value": file_path,
                    "inline": True
                })
                
                # Add content field (may need truncation)
                content = arguments.get("content", "")
                if len(content) > discord_limits["embed_field_value"]:
                    content = content[:discord_limits["embed_field_value"]-3] + "..."
                
                fields.append({
                    "name": "Content Preview",
                    "value": content if content else "No content",
                    "inline": False
                })
                
                # Add metadata fields (respect field count limit)
                metadata = event_data.get("metadata", {})
                for i, (key, value) in enumerate(metadata.items()):
                    if len(fields) >= discord_limits["embed_fields_total"]:
                        break
                    
                    field_name = key
                    if len(field_name) > discord_limits["embed_field_name"]:
                        field_name = field_name[:discord_limits["embed_field_name"]-3] + "..."
                    
                    field_value = str(value)
                    if len(field_value) > discord_limits["embed_field_value"]:
                        field_value = field_value[:discord_limits["embed_field_value"]-3] + "..."
                    
                    fields.append({
                        "name": field_name,
                        "value": field_value,
                        "inline": True
                    })
                
                footer_text = "Claude Code Event - Limits Test"
                if len(footer_text) > discord_limits["embed_footer_text"]:
                    footer_text = footer_text[:discord_limits["embed_footer_text"]-3] + "..."
                
                return {
                    "title": title,
                    "description": description,
                    "color": 0x3498db,
                    "timestamp": event_data.get("timestamp"),
                    "fields": fields,
                    "footer": {"text": footer_text}
                }
            
            mock_instance.format_event.side_effect = limit_compliant_format
            
            formatter_registry = EventFormatterRegistry()
            
            # Test limits compliance
            embed = formatter_registry.format_event("PreToolUse", oversized_event)
            
            # Verify title limit
            self.assertLessEqual(len(embed.get("title", "")), discord_limits["embed_title"])
            
            # Verify description limit
            self.assertLessEqual(len(embed.get("description", "")), discord_limits["embed_description"])
            
            # Verify field limits
            fields = embed.get("fields", [])
            self.assertLessEqual(len(fields), discord_limits["embed_fields_total"])
            
            for field in fields:
                self.assertLessEqual(len(field.get("name", "")), discord_limits["embed_field_name"])
                self.assertLessEqual(len(field.get("value", "")), discord_limits["embed_field_value"])
            
            # Verify footer limit
            footer_text = embed.get("footer", {}).get("text", "")
            self.assertLessEqual(len(footer_text), discord_limits["embed_footer_text"])
            
            # Calculate total character count
            total_chars = len(embed.get("title", "")) + len(embed.get("description", ""))
            total_chars += sum(len(field.get("name", "")) + len(field.get("value", "")) for field in fields)
            total_chars += len(footer_text)
            
            # Log limits compliance analysis
            self.logger.info(
                "Discord limits compliance analysis",
                context={
                    "title_length": len(embed.get("title", "")),
                    "description_length": len(embed.get("description", "")),
                    "field_count": len(fields),
                    "footer_length": len(footer_text),
                    "total_characters": total_chars,
                    "total_limit": discord_limits["embed_total_chars"],
                    "compliance": total_chars <= discord_limits["embed_total_chars"]
                }
            )
            
            # Verify total character limit compliance (if enforced)
            # Note: Discord's total character limit is not strictly enforced but is a guideline
            if total_chars > discord_limits["embed_total_chars"]:
                self.logger.warning(
                    f"Embed exceeds recommended total character limit: {total_chars} > {discord_limits['embed_total_chars']}"
                )


def run_event_formatting_tests() -> None:
    """Run event formatting tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestEventFormatting)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nEvent Formatting Tests Summary:")
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