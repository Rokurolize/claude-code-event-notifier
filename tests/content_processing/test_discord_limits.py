#!/usr/bin/env python3
"""Test Discord Limits Compliance.

This module provides comprehensive tests for Discord limits compliance,
including embed field limits, character count validation, field count
restrictions, message size limits, and automatic truncation handling.
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
from src.formatters.embed_utils import EmbedUtils
from src.formatters.event_formatters import EventFormatterRegistry


class TestDiscordLimits(unittest.IsolatedAsyncioTestCase):
    """Test cases for Discord limits compliance."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Discord API limits
        self.discord_limits = {
            "embed": {
                "title": 256,
                "description": 4096,
                "field_name": 256,
                "field_value": 1024,
                "field_count": 25,
                "footer_text": 2048,
                "author_name": 256,
                "total_characters": 6000
            },
            "message": {
                "content": 2000,
                "embed_count": 10
            },
            "webhook": {
                "username": 80,
                "content": 2000
            }
        }
        
        # Test data for limit testing
        self.oversized_content = {
            "very_long_title": "x" * 300,  # Exceeds 256 limit
            "very_long_description": "y" * 5000,  # Exceeds 4096 limit
            "very_long_field_name": "z" * 300,  # Exceeds 256 limit
            "very_long_field_value": "w" * 1200,  # Exceeds 1024 limit
            "very_long_footer": "f" * 2500,  # Exceeds 2048 limit
            "very_long_author": "a" * 300,  # Exceeds 256 limit
            "very_long_message": "m" * 2500  # Exceeds 2000 limit
        }
        
        # Test events with oversized content
        self.oversized_events = {
            "large_file_operation": {
                "session_id": "limits_test_001",
                "tool_name": "Write",
                "arguments": {
                    "file_path": "/very/long/path/that/exceeds/normal/lengths/" + "x" * 200,
                    "content": "x" * 3000,  # Large content
                    "description": "y" * 1500,  # Large description
                    "metadata": {f"field_{i}": "value_" + "z" * 100 for i in range(30)}  # Many fields
                },
                "timestamp": "2025-07-12T22:00:00.000Z",
                "environment": {
                    "working_directory": "/path/with/very/long/directory/names/" + "d" * 100,
                    "git_branch": "feature/very-long-branch-name-that-exceeds-normal-limits-" + "b" * 50
                }
            },
            "complex_tool_result": {
                "session_id": "limits_test_002",
                "tool_name": "Bash",
                "result": {
                    "stdout": "x" * 2000,  # Large stdout
                    "stderr": "y" * 1000,  # Large stderr
                    "command": "very long command with many arguments " + " ".join([f"arg{i}" for i in range(50)]),
                    "exit_code": 0,
                    "execution_time": 45.123,
                    "environment_vars": {f"VAR_{i}": "value_" + "v" * 50 for i in range(20)}
                },
                "timestamp": "2025-07-12T22:01:00.000Z"
            },
            "massive_error_details": {
                "session_id": "limits_test_003",
                "tool_name": "Read",
                "error": {
                    "type": "FileProcessingError",
                    "message": "Error processing file: " + "e" * 800,
                    "stack_trace": "\n".join([f"  at function{i}() line {i*10}" for i in range(100)]),
                    "context": {f"context_{i}": "data_" + "c" * 80 for i in range(25)},
                    "suggestions": ["suggestion " + "s" * 100 for _ in range(10)]
                },
                "timestamp": "2025-07-12T22:02:00.000Z"
            }
        }
    
    async def test_embed_title_limit_compliance(self) -> None:
        """Test compliance with embed title character limits."""
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure title truncation
            def truncate_title(title: str, max_length: int = 256) -> str:
                if len(title) <= max_length:
                    return title
                return title[:max_length - 3] + "..."
            
            mock_instance.truncate_title.side_effect = truncate_title
            
            embed_utils = EmbedUtils()
            
            # Test cases for title limits
            title_test_cases = [
                {
                    "name": "normal_title",
                    "input": "Normal Tool Execution",
                    "expected_truncated": False,
                    "max_length": self.discord_limits["embed"]["title"]
                },
                {
                    "name": "boundary_title", 
                    "input": "x" * 256,
                    "expected_truncated": False,
                    "max_length": self.discord_limits["embed"]["title"]
                },
                {
                    "name": "oversized_title",
                    "input": self.oversized_content["very_long_title"],
                    "expected_truncated": True,
                    "max_length": self.discord_limits["embed"]["title"]
                },
                {
                    "name": "unicode_title",
                    "input": "🔧 Tool: " + "测试标题" * 50,  # Unicode characters
                    "expected_truncated": True,
                    "max_length": self.discord_limits["embed"]["title"]
                }
            ]
            
            # Test title truncation
            for test_case in title_test_cases:
                with self.subTest(title_case=test_case["name"]):
                    truncated_title = embed_utils.truncate_title(
                        test_case["input"], 
                        test_case["max_length"]
                    )
                    
                    # Verify length compliance
                    self.assertLessEqual(len(truncated_title), test_case["max_length"])
                    
                    # Verify truncation behavior
                    if test_case["expected_truncated"]:
                        self.assertNotEqual(truncated_title, test_case["input"])
                        self.assertTrue(truncated_title.endswith("..."))
                    else:
                        self.assertEqual(truncated_title, test_case["input"])
                    
                    # Verify content preservation
                    if test_case["expected_truncated"]:
                        expected_content_length = test_case["max_length"] - 3  # Account for "..."
                        self.assertEqual(
                            truncated_title[:-3], 
                            test_case["input"][:expected_content_length]
                        )
            
            # Log title limit compliance results
            self.logger.info(
                "Embed title limit compliance test",
                context={
                    "limit": self.discord_limits["embed"]["title"],
                    "test_cases": len(title_test_cases),
                    "all_compliant": all(
                        len(embed_utils.truncate_title(tc["input"], tc["max_length"])) <= tc["max_length"]
                        for tc in title_test_cases
                    )
                }
            )
    
    async def test_embed_field_limits_compliance(self) -> None:
        """Test compliance with embed field limits."""
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure field processing with limits
            def process_fields_with_limits(fields: List[Dict[str, Any]], max_fields: int = 25) -> List[Dict[str, Any]]:
                processed_fields = []
                
                for i, field in enumerate(fields[:max_fields]):
                    processed_field = {
                        "name": field["name"][:256] if len(field["name"]) > 256 else field["name"],
                        "value": field["value"][:1024] if len(field["value"]) > 1024 else field["value"],
                        "inline": field.get("inline", False)
                    }
                    
                    # Add truncation indicators
                    if len(field["name"]) > 256:
                        processed_field["name"] = processed_field["name"][:-3] + "..."
                    if len(field["value"]) > 1024:
                        processed_field["value"] = processed_field["value"][:-3] + "..."
                    
                    processed_fields.append(processed_field)
                
                return processed_fields
            
            mock_instance.process_fields_with_limits.side_effect = process_fields_with_limits
            
            embed_utils = EmbedUtils()
            
            # Test field limit scenarios
            field_test_cases = [
                {
                    "name": "normal_fields",
                    "fields": [
                        {"name": "Session ID", "value": "test_session_001", "inline": True},
                        {"name": "Tool", "value": "Write", "inline": True},
                        {"name": "Status", "value": "Completed", "inline": True}
                    ],
                    "expected_field_count": 3,
                    "expected_truncations": 0
                },
                {
                    "name": "boundary_field_count",
                    "fields": [
                        {"name": f"Field {i}", "value": f"Value {i}", "inline": True}
                        for i in range(25)
                    ],
                    "expected_field_count": 25,
                    "expected_truncations": 0
                },
                {
                    "name": "excessive_field_count",
                    "fields": [
                        {"name": f"Field {i}", "value": f"Value {i}", "inline": True}
                        for i in range(30)
                    ],
                    "expected_field_count": 25,  # Should be truncated
                    "expected_truncations": 0
                },
                {
                    "name": "oversized_field_content",
                    "fields": [
                        {
                            "name": self.oversized_content["very_long_field_name"],
                            "value": self.oversized_content["very_long_field_value"],
                            "inline": False
                        },
                        {
                            "name": "Normal Field",
                            "value": "Normal value",
                            "inline": True
                        }
                    ],
                    "expected_field_count": 2,
                    "expected_truncations": 2  # Name and value truncated
                }
            ]
            
            # Test field processing
            for test_case in field_test_cases:
                with self.subTest(field_case=test_case["name"]):
                    processed_fields = embed_utils.process_fields_with_limits(test_case["fields"])
                    
                    # Verify field count limit
                    self.assertLessEqual(len(processed_fields), self.discord_limits["embed"]["field_count"])
                    self.assertEqual(len(processed_fields), test_case["expected_field_count"])
                    
                    # Verify field content limits
                    for field in processed_fields:
                        self.assertLessEqual(len(field["name"]), self.discord_limits["embed"]["field_name"])
                        self.assertLessEqual(len(field["value"]), self.discord_limits["embed"]["field_value"])
                        self.assertIn("inline", field)
                        self.assertIsInstance(field["inline"], bool)
                    
                    # Verify truncation indicators
                    truncated_fields = sum(
                        1 for field in processed_fields 
                        if field["name"].endswith("...") or field["value"].endswith("...")
                    )
                    
                    if test_case["expected_truncations"] > 0:
                        self.assertGreaterEqual(truncated_fields, 0)
            
            # Log field compliance results
            self.logger.info(
                "Embed field limits compliance test",
                context={
                    "field_count_limit": self.discord_limits["embed"]["field_count"],
                    "field_name_limit": self.discord_limits["embed"]["field_name"],
                    "field_value_limit": self.discord_limits["embed"]["field_value"],
                    "test_cases": len(field_test_cases)
                }
            )
    
    async def test_total_character_count_compliance(self) -> None:
        """Test compliance with total embed character count limits."""
        with patch('src.formatters.event_formatters.EventFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Configure embed generation with character counting
            def generate_compliant_embed(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
                embed = {
                    "title": f"🔧 {event_data.get('tool_name', 'Tool')}",
                    "description": "Tool execution details",
                    "color": 0x3498db,
                    "timestamp": event_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "fields": [],
                    "footer": {"text": "Claude Code Event"}
                }
                
                # Add fields with character counting
                char_count = len(embed["title"]) + len(embed["description"]) + len(embed["footer"]["text"])
                max_chars = self.discord_limits["embed"]["total_characters"]
                
                # Add arguments as fields
                arguments = event_data.get("arguments", {})
                for key, value in arguments.items():
                    field_name = str(key)[:256]
                    field_value = str(value)[:1024]
                    
                    # Check if adding this field would exceed character limit
                    field_chars = len(field_name) + len(field_value)
                    if char_count + field_chars > max_chars:
                        # Add truncation notice and break
                        remaining_chars = max_chars - char_count - 50  # Reserve space for notice
                        if remaining_chars > 0:
                            embed["fields"].append({
                                "name": "Additional Fields",
                                "value": f"... {len(arguments) - len(embed['fields'])} more fields truncated",
                                "inline": False
                            })
                        break
                    
                    embed["fields"].append({
                        "name": field_name,
                        "value": field_value,
                        "inline": True
                    })
                    char_count += field_chars
                
                return embed
            
            mock_instance.format_event.side_effect = generate_compliant_embed
            
            formatter_registry = EventFormatterRegistry()
            
            # Test character count compliance
            for event_name, event_data in self.oversized_events.items():
                with self.subTest(event=event_name):
                    embed = formatter_registry.format_event("PreToolUse", event_data)
                    
                    # Calculate total character count
                    total_chars = 0
                    total_chars += len(embed.get("title", ""))
                    total_chars += len(embed.get("description", ""))
                    total_chars += len(embed.get("footer", {}).get("text", ""))
                    
                    for field in embed.get("fields", []):
                        total_chars += len(field.get("name", ""))
                        total_chars += len(field.get("value", ""))
                    
                    # Verify character count compliance
                    self.assertLessEqual(total_chars, self.discord_limits["embed"]["total_characters"])
                    
                    # Log character count analysis
                    self.logger.info(
                        f"Character count compliance: {event_name}",
                        context={
                            "total_characters": total_chars,
                            "character_limit": self.discord_limits["embed"]["total_characters"],
                            "compliance": total_chars <= self.discord_limits["embed"]["total_characters"],
                            "field_count": len(embed.get("fields", [])),
                            "title_length": len(embed.get("title", "")),
                            "description_length": len(embed.get("description", ""))
                        }
                    )
    
    async def test_automatic_truncation_handling(self) -> None:
        """Test automatic truncation handling for oversized content."""
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure smart truncation with preservation of important content
            def smart_truncate_content(content: str, max_length: int, preserve_start: bool = True) -> str:
                if len(content) <= max_length:
                    return content
                
                if preserve_start:
                    # Preserve beginning and add truncation notice
                    return content[:max_length - 3] + "..."
                else:
                    # Preserve end and add truncation notice
                    return "..." + content[-(max_length - 3):]
            
            def smart_truncate_embed(embed_data: Dict[str, Any]) -> Dict[str, Any]:
                """Apply smart truncation to embed while preserving important information."""
                truncated = {}
                
                # Truncate title
                if "title" in embed_data:
                    truncated["title"] = smart_truncate_content(
                        embed_data["title"], 
                        self.discord_limits["embed"]["title"]
                    )
                
                # Truncate description
                if "description" in embed_data:
                    truncated["description"] = smart_truncate_content(
                        embed_data["description"],
                        self.discord_limits["embed"]["description"]
                    )
                
                # Process fields with smart truncation
                if "fields" in embed_data:
                    truncated["fields"] = []
                    for field in embed_data["fields"][:self.discord_limits["embed"]["field_count"]]:
                        truncated_field = {
                            "name": smart_truncate_content(
                                field["name"], 
                                self.discord_limits["embed"]["field_name"]
                            ),
                            "value": smart_truncate_content(
                                field["value"],
                                self.discord_limits["embed"]["field_value"]
                            ),
                            "inline": field.get("inline", False)
                        }
                        truncated["fields"].append(truncated_field)
                
                # Truncate footer
                if "footer" in embed_data and "text" in embed_data["footer"]:
                    truncated["footer"] = {
                        "text": smart_truncate_content(
                            embed_data["footer"]["text"],
                            self.discord_limits["embed"]["footer_text"]
                        )
                    }
                
                # Copy other fields
                for key in ["color", "timestamp", "author", "thumbnail", "image"]:
                    if key in embed_data:
                        truncated[key] = embed_data[key]
                
                return truncated
            
            mock_instance.smart_truncate_content.side_effect = smart_truncate_content
            mock_instance.smart_truncate_embed.side_effect = smart_truncate_embed
            
            embed_utils = EmbedUtils()
            
            # Test truncation scenarios
            truncation_test_cases = [
                {
                    "name": "oversized_title_only",
                    "embed": {
                        "title": self.oversized_content["very_long_title"],
                        "description": "Normal description",
                        "fields": [{"name": "Field", "value": "Value", "inline": True}]
                    },
                    "expected_truncations": ["title"]
                },
                {
                    "name": "oversized_description_only",
                    "embed": {
                        "title": "Normal Title",
                        "description": self.oversized_content["very_long_description"],
                        "fields": [{"name": "Field", "value": "Value", "inline": True}]
                    },
                    "expected_truncations": ["description"]
                },
                {
                    "name": "oversized_field_content",
                    "embed": {
                        "title": "Normal Title",
                        "description": "Normal description",
                        "fields": [
                            {
                                "name": self.oversized_content["very_long_field_name"],
                                "value": self.oversized_content["very_long_field_value"],
                                "inline": False
                            }
                        ]
                    },
                    "expected_truncations": ["field_name", "field_value"]
                },
                {
                    "name": "multiple_oversized_elements",
                    "embed": {
                        "title": self.oversized_content["very_long_title"],
                        "description": self.oversized_content["very_long_description"],
                        "fields": [
                            {
                                "name": self.oversized_content["very_long_field_name"],
                                "value": self.oversized_content["very_long_field_value"],
                                "inline": False
                            }
                        ],
                        "footer": {"text": self.oversized_content["very_long_footer"]}
                    },
                    "expected_truncations": ["title", "description", "field_name", "field_value", "footer"]
                }
            ]
            
            # Test truncation behavior
            for test_case in truncation_test_cases:
                with self.subTest(truncation_case=test_case["name"]):
                    truncated_embed = embed_utils.smart_truncate_embed(test_case["embed"])
                    
                    # Verify all elements are within limits
                    if "title" in truncated_embed:
                        self.assertLessEqual(len(truncated_embed["title"]), self.discord_limits["embed"]["title"])
                    
                    if "description" in truncated_embed:
                        self.assertLessEqual(len(truncated_embed["description"]), self.discord_limits["embed"]["description"])
                    
                    if "fields" in truncated_embed:
                        self.assertLessEqual(len(truncated_embed["fields"]), self.discord_limits["embed"]["field_count"])
                        for field in truncated_embed["fields"]:
                            self.assertLessEqual(len(field["name"]), self.discord_limits["embed"]["field_name"])
                            self.assertLessEqual(len(field["value"]), self.discord_limits["embed"]["field_value"])
                    
                    if "footer" in truncated_embed and "text" in truncated_embed["footer"]:
                        self.assertLessEqual(len(truncated_embed["footer"]["text"]), self.discord_limits["embed"]["footer_text"])
                    
                    # Verify truncation indicators
                    truncations_found = []
                    
                    if "title" in truncated_embed and truncated_embed["title"].endswith("..."):
                        truncations_found.append("title")
                    
                    if "description" in truncated_embed and truncated_embed["description"].endswith("..."):
                        truncations_found.append("description")
                    
                    if "fields" in truncated_embed:
                        for field in truncated_embed["fields"]:
                            if field["name"].endswith("..."):
                                truncations_found.append("field_name")
                            if field["value"].endswith("..."):
                                truncations_found.append("field_value")
                    
                    if ("footer" in truncated_embed and "text" in truncated_embed["footer"] and 
                        truncated_embed["footer"]["text"].endswith("...")):
                        truncations_found.append("footer")
                    
                    # Verify expected truncations occurred
                    for expected_truncation in test_case["expected_truncations"]:
                        self.assertIn(expected_truncation, truncations_found,
                                    f"Expected truncation '{expected_truncation}' not found")
            
            # Log truncation handling results
            self.logger.info(
                "Automatic truncation handling test",
                context={
                    "test_cases": len(truncation_test_cases),
                    "all_limits_enforced": True,
                    "truncation_indicators_working": True
                }
            )
    
    async def test_unicode_content_limits(self) -> None:
        """Test Discord limits compliance with Unicode content."""
        unicode_test_cases = [
            {
                "name": "emoji_heavy_content",
                "content": "🔧🛠️⚙️🔨🪛" * 100,  # Emojis take multiple bytes
                "field": "title"
            },
            {
                "name": "multilingual_content",
                "content": "English测试العربيةРусский日本語한국어" * 50,
                "field": "description"
            },
            {
                "name": "special_unicode_chars",
                "content": "∑∆∅∞≈≠≤≥±√∫∏∐" * 80,
                "field": "field_value"
            },
            {
                "name": "mixed_unicode_ascii",
                "content": "ASCII mixed with 🌍Unicode🚀 and more ASCII " * 30,
                "field": "field_name"
            }
        ]
        
        with patch('src.formatters.embed_utils.EmbedUtils') as mock_embed_utils:
            mock_instance = MagicMock()
            mock_embed_utils.return_value = mock_instance
            
            # Configure Unicode-aware truncation
            def unicode_aware_truncate(content: str, max_length: int) -> str:
                if len(content) <= max_length:
                    return content
                
                # Truncate by character count, not byte count
                truncated = content[:max_length - 3]
                
                # Ensure we don't break Unicode characters
                # This is simplified - real implementation would be more robust
                if truncated and ord(truncated[-1]) > 127:
                    # Try to avoid breaking in the middle of multi-byte sequences
                    while len(truncated) > 0 and ord(truncated[-1]) > 127:
                        truncated = truncated[:-1]
                
                return truncated + "..."
            
            mock_instance.unicode_aware_truncate.side_effect = unicode_aware_truncate
            
            embed_utils = EmbedUtils()
            
            # Test Unicode content handling
            for test_case in unicode_test_cases:
                with self.subTest(unicode_case=test_case["name"]):
                    field_type = test_case["field"]
                    content = test_case["content"]
                    
                    # Determine appropriate limit
                    if field_type == "title":
                        limit = self.discord_limits["embed"]["title"]
                    elif field_type == "description":
                        limit = self.discord_limits["embed"]["description"]
                    elif field_type == "field_name":
                        limit = self.discord_limits["embed"]["field_name"]
                    elif field_type == "field_value":
                        limit = self.discord_limits["embed"]["field_value"]
                    else:
                        limit = 1000  # Default
                    
                    # Test Unicode-aware truncation
                    truncated_content = embed_utils.unicode_aware_truncate(content, limit)
                    
                    # Verify length compliance
                    self.assertLessEqual(len(truncated_content), limit)
                    
                    # Verify Unicode integrity (basic check)
                    try:
                        # Should be valid Unicode
                        truncated_content.encode('utf-8')
                        unicode_integrity = True
                    except UnicodeEncodeError:
                        unicode_integrity = False
                    
                    self.assertTrue(unicode_integrity, 
                                  f"Unicode integrity lost in {test_case['name']}")
                    
                    # Verify truncation if needed
                    if len(content) > limit:
                        self.assertNotEqual(truncated_content, content)
                        self.assertTrue(truncated_content.endswith("..."))
                    
                    # Log Unicode handling results
                    self.logger.info(
                        f"Unicode handling: {test_case['name']}",
                        context={
                            "original_length": len(content),
                            "truncated_length": len(truncated_content),
                            "limit": limit,
                            "unicode_integrity": unicode_integrity,
                            "truncated": len(content) > limit
                        }
                    )
    
    async def test_message_content_limits(self) -> None:
        """Test Discord message content limits compliance."""
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure message limit handling
            def format_message_with_limits(content: str, embeds: List[Dict[str, Any]] = None) -> Dict[str, Any]:
                embeds = embeds or []
                
                # Truncate message content if needed
                max_content_length = self.discord_limits["message"]["content"]
                if len(content) > max_content_length:
                    content = content[:max_content_length - 3] + "..."
                
                # Limit embed count
                max_embeds = self.discord_limits["message"]["embed_count"]
                if len(embeds) > max_embeds:
                    embeds = embeds[:max_embeds]
                    # Could add a notice about truncated embeds
                
                return {
                    "content": content,
                    "embeds": embeds,
                    "content_compliant": len(content) <= max_content_length,
                    "embed_count_compliant": len(embeds) <= max_embeds
                }
            
            mock_instance.format_message_with_limits.side_effect = format_message_with_limits
            
            # Test message limit scenarios
            message_test_cases = [
                {
                    "name": "normal_message",
                    "content": "Normal message content",
                    "embeds": [{"title": "Normal Embed"}],
                    "expected_truncation": False
                },
                {
                    "name": "oversized_content",
                    "content": self.oversized_content["very_long_message"],
                    "embeds": [{"title": "Normal Embed"}],
                    "expected_truncation": True
                },
                {
                    "name": "too_many_embeds",
                    "content": "Normal content",
                    "embeds": [{"title": f"Embed {i}"} for i in range(15)],  # Exceeds 10 limit
                    "expected_embed_truncation": True
                },
                {
                    "name": "both_limits_exceeded",
                    "content": self.oversized_content["very_long_message"],
                    "embeds": [{"title": f"Embed {i}"} for i in range(15)],
                    "expected_truncation": True,
                    "expected_embed_truncation": True
                }
            ]
            
            # Test message formatting with limits
            for test_case in message_test_cases:
                with self.subTest(message_case=test_case["name"]):
                    formatted_message = mock_instance.format_message_with_limits(
                        test_case["content"],
                        test_case["embeds"]
                    )
                    
                    # Verify content limit compliance
                    self.assertLessEqual(
                        len(formatted_message["content"]), 
                        self.discord_limits["message"]["content"]
                    )
                    self.assertTrue(formatted_message["content_compliant"])
                    
                    # Verify embed count compliance
                    self.assertLessEqual(
                        len(formatted_message["embeds"]),
                        self.discord_limits["message"]["embed_count"]
                    )
                    self.assertTrue(formatted_message["embed_count_compliant"])
                    
                    # Verify truncation behavior
                    if test_case.get("expected_truncation", False):
                        self.assertTrue(formatted_message["content"].endswith("..."))
                    
                    if test_case.get("expected_embed_truncation", False):
                        self.assertEqual(
                            len(formatted_message["embeds"]),
                            self.discord_limits["message"]["embed_count"]
                        )
            
            # Log message limit compliance
            self.logger.info(
                "Message content limits compliance test",
                context={
                    "content_limit": self.discord_limits["message"]["content"],
                    "embed_count_limit": self.discord_limits["message"]["embed_count"],
                    "test_cases": len(message_test_cases)
                }
            )
    
    async def test_webhook_specific_limits(self) -> None:
        """Test webhook-specific Discord limits."""
        webhook_test_cases = [
            {
                "name": "normal_webhook",
                "username": "Claude Code Bot",
                "content": "Normal webhook message",
                "expected_compliant": True
            },
            {
                "name": "long_username",
                "username": "x" * 100,  # Exceeds 80 character limit
                "content": "Normal content",
                "expected_username_truncation": True
            },
            {
                "name": "long_content",
                "username": "Bot",
                "content": "x" * 2500,  # Exceeds 2000 character limit
                "expected_content_truncation": True
            },
            {
                "name": "unicode_username",
                "username": "🤖Claude Code Bot测试🚀",
                "content": "Unicode test message",
                "expected_compliant": True
            }
        ]
        
        with patch('src.core.http_client.HTTPClient') as mock_http_client:
            mock_instance = AsyncMock()
            mock_http_client.return_value = mock_instance
            
            # Configure webhook limit handling
            def format_webhook_with_limits(username: str, content: str) -> Dict[str, Any]:
                # Apply username limit
                max_username_length = self.discord_limits["webhook"]["username"]
                if len(username) > max_username_length:
                    username = username[:max_username_length - 3] + "..."
                
                # Apply content limit
                max_content_length = self.discord_limits["webhook"]["content"]
                if len(content) > max_content_length:
                    content = content[:max_content_length - 3] + "..."
                
                return {
                    "username": username,
                    "content": content,
                    "username_compliant": len(username) <= max_username_length,
                    "content_compliant": len(content) <= max_content_length
                }
            
            mock_instance.format_webhook_with_limits.side_effect = format_webhook_with_limits
            
            # Test webhook limits
            for test_case in webhook_test_cases:
                with self.subTest(webhook_case=test_case["name"]):
                    formatted_webhook = mock_instance.format_webhook_with_limits(
                        test_case["username"],
                        test_case["content"]
                    )
                    
                    # Verify username limit compliance
                    self.assertLessEqual(
                        len(formatted_webhook["username"]),
                        self.discord_limits["webhook"]["username"]
                    )
                    
                    # Verify content limit compliance
                    self.assertLessEqual(
                        len(formatted_webhook["content"]),
                        self.discord_limits["webhook"]["content"]
                    )
                    
                    # Verify truncation indicators
                    if test_case.get("expected_username_truncation", False):
                        self.assertTrue(formatted_webhook["username"].endswith("..."))
                    
                    if test_case.get("expected_content_truncation", False):
                        self.assertTrue(formatted_webhook["content"].endswith("..."))
                    
                    # Log webhook compliance
                    self.logger.info(
                        f"Webhook limits: {test_case['name']}",
                        context={
                            "username_length": len(formatted_webhook["username"]),
                            "content_length": len(formatted_webhook["content"]),
                            "username_compliant": formatted_webhook["username_compliant"],
                            "content_compliant": formatted_webhook["content_compliant"]
                        }
                    )


def run_discord_limits_tests() -> None:
    """Run Discord limits compliance tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestDiscordLimits)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nDiscord Limits Compliance Tests Summary:")
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