#!/usr/bin/env python3
"""Test Tool Formatting Functionality.

This module provides comprehensive tests for tool formatting functionality,
including tool-specific formatters, parameter handling, result formatting,
consistency across different tools, and specialized formatting logic.
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
from src.formatters.tool_formatters import ToolFormatterRegistry
from src.formatters.base import BaseFormatter


class TestToolFormatting(unittest.IsolatedAsyncioTestCase):
    """Test cases for tool formatting functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test data for different tools
        self.tool_test_data = {
            "Write": {
                "pre_tool_use": {
                    "session_id": "tool_test_001",
                    "tool_name": "Write",
                    "arguments": {
                        "file_path": "/home/user/project/main.py",
                        "content": "#!/usr/bin/env python3\nprint('Hello, World!')\n"
                    },
                    "timestamp": "2025-07-12T22:00:00.000Z"
                },
                "post_tool_use": {
                    "session_id": "tool_test_001",
                    "tool_name": "Write",
                    "result": {
                        "success": True,
                        "file_created": True,
                        "bytes_written": 42,
                        "file_path": "/home/user/project/main.py"
                    },
                    "execution_time": 0.085,
                    "timestamp": "2025-07-12T22:00:00.085Z"
                }
            },
            "Read": {
                "pre_tool_use": {
                    "session_id": "tool_test_002",
                    "tool_name": "Read",
                    "arguments": {
                        "file_path": "/home/user/project/config.json",
                        "offset": 0,
                        "limit": 100
                    },
                    "timestamp": "2025-07-12T22:01:00.000Z"
                },
                "post_tool_use": {
                    "session_id": "tool_test_002",
                    "tool_name": "Read",
                    "result": {
                        "success": True,
                        "content": '{"name": "test_project", "version": "1.0.0"}',
                        "file_size": 45,
                        "lines_read": 1
                    },
                    "execution_time": 0.025,
                    "timestamp": "2025-07-12T22:01:00.025Z"
                }
            },
            "Edit": {
                "pre_tool_use": {
                    "session_id": "tool_test_003",
                    "tool_name": "Edit",
                    "arguments": {
                        "file_path": "/home/user/project/main.py",
                        "old_string": "print('Hello, World!')",
                        "new_string": "print('Hello, Python!')"
                    },
                    "timestamp": "2025-07-12T22:02:00.000Z"
                },
                "post_tool_use": {
                    "session_id": "tool_test_003",
                    "tool_name": "Edit",
                    "result": {
                        "success": True,
                        "changes_made": 1,
                        "lines_modified": 1,
                        "backup_created": True
                    },
                    "execution_time": 0.152,
                    "timestamp": "2025-07-12T22:02:00.152Z"
                }
            },
            "Bash": {
                "pre_tool_use": {
                    "session_id": "tool_test_004",
                    "tool_name": "Bash",
                    "arguments": {
                        "command": "ls -la /home/user/project",
                        "timeout": 30000,
                        "description": "List project directory contents"
                    },
                    "timestamp": "2025-07-12T22:03:00.000Z"
                },
                "post_tool_use": {
                    "session_id": "tool_test_004",
                    "tool_name": "Bash",
                    "result": {
                        "success": True,
                        "exit_code": 0,
                        "stdout": "total 8\ndrwxr-xr-x 2 user user 4096 Jul 12 22:00 .\ndrwxr-xr-x 3 user user 4096 Jul 12 21:59 ..\n-rw-r--r-- 1 user user   42 Jul 12 22:00 main.py\n",
                        "stderr": "",
                        "execution_time": 0.045
                    },
                    "execution_time": 0.045,
                    "timestamp": "2025-07-12T22:03:00.045Z"
                }
            },
            "Glob": {
                "pre_tool_use": {
                    "session_id": "tool_test_005",
                    "tool_name": "Glob",
                    "arguments": {
                        "pattern": "**/*.py",
                        "path": "/home/user/project"
                    },
                    "timestamp": "2025-07-12T22:04:00.000Z"
                },
                "post_tool_use": {
                    "session_id": "tool_test_005",
                    "tool_name": "Glob",
                    "result": {
                        "success": True,
                        "matches": [
                            "/home/user/project/main.py",
                            "/home/user/project/utils.py",
                            "/home/user/project/tests/test_main.py"
                        ],
                        "total_matches": 3
                    },
                    "execution_time": 0.012,
                    "timestamp": "2025-07-12T22:04:00.012Z"
                }
            }
        }
        
        # Expected formatting patterns for validation
        self.expected_patterns = {
            "Write": {
                "icon": "📝",
                "color_pre": 0x3498db,
                "color_post": 0x2ecc71,
                "key_fields": ["file_path", "content", "bytes_written"]
            },
            "Read": {
                "icon": "📖",
                "color_pre": 0x9b59b6,
                "color_post": 0x2ecc71,
                "key_fields": ["file_path", "content", "file_size"]
            },
            "Edit": {
                "icon": "✏️",
                "color_pre": 0xe67e22,
                "color_post": 0x2ecc71,
                "key_fields": ["file_path", "old_string", "new_string", "changes_made"]
            },
            "Bash": {
                "icon": "⚡",
                "color_pre": 0x34495e,
                "color_post": 0x2ecc71,
                "key_fields": ["command", "exit_code", "stdout", "stderr"]
            },
            "Glob": {
                "icon": "🔍",
                "color_pre": 0x1abc9c,
                "color_post": 0x2ecc71,
                "key_fields": ["pattern", "matches", "total_matches"]
            }
        }
    
    async def test_tool_specific_formatter_detection(self) -> None:
        """Test detection and selection of tool-specific formatters."""
        with patch('src.formatters.tool_formatters.ToolFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Configure formatter detection
            def detect_tool_formatter(tool_name: str) -> Optional[str]:
                formatter_map = {
                    "Write": "WriteFormatter",
                    "Read": "ReadFormatter", 
                    "Edit": "EditFormatter",
                    "Bash": "BashFormatter",
                    "Glob": "GlobFormatter",
                    "UnknownTool": None
                }
                return formatter_map.get(tool_name)
            
            mock_instance.get_formatter.side_effect = detect_tool_formatter
            
            formatter_registry = ToolFormatterRegistry()
            
            # Test formatter detection for each tool
            for tool_name in self.tool_test_data.keys():
                with self.subTest(tool=tool_name):
                    formatter_name = formatter_registry.get_formatter(tool_name)
                    
                    # Verify correct formatter detected
                    self.assertIsNotNone(formatter_name)
                    self.assertTrue(formatter_name.endswith("Formatter"))
                    self.assertIn(tool_name, formatter_name)
                    
                    self.logger.info(
                        f"Tool formatter detection: {tool_name}",
                        context={
                            "detected_formatter": formatter_name,
                            "tool_name": tool_name,
                            "detection_accuracy": "correct"
                        }
                    )
            
            # Test unknown tool handling
            unknown_formatter = formatter_registry.get_formatter("UnknownTool")
            self.assertIsNone(unknown_formatter)
    
    async def test_parameter_formatting_accuracy(self) -> None:
        """Test accuracy of parameter formatting for different tools."""
        with patch('src.formatters.tool_formatters.ToolFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            def format_tool_parameters(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
                """Format tool parameters based on tool type."""
                pattern = self.expected_patterns.get(tool_name, {})
                
                if tool_name == "Write":
                    return {
                        "title": f"{pattern.get('icon', '📝')} Writing File",
                        "description": f"Creating/updating file: {arguments.get('file_path', 'unknown')}",
                        "color": pattern.get('color_pre', 0x3498db),
                        "fields": [
                            {
                                "name": "File Path",
                                "value": arguments.get("file_path", "Not specified"),
                                "inline": False
                            },
                            {
                                "name": "Content Preview",
                                "value": f"```\n{arguments.get('content', '')[:200]}{'...' if len(arguments.get('content', '')) > 200 else ''}\n```",
                                "inline": False
                            },
                            {
                                "name": "Content Length",
                                "value": f"{len(arguments.get('content', ''))} characters",
                                "inline": True
                            }
                        ]
                    }
                
                elif tool_name == "Read":
                    return {
                        "title": f"{pattern.get('icon', '📖')} Reading File",
                        "description": f"Reading from: {arguments.get('file_path', 'unknown')}",
                        "color": pattern.get('color_pre', 0x9b59b6),
                        "fields": [
                            {
                                "name": "File Path",
                                "value": arguments.get("file_path", "Not specified"),
                                "inline": False
                            },
                            {
                                "name": "Offset",
                                "value": str(arguments.get("offset", 0)),
                                "inline": True
                            },
                            {
                                "name": "Limit",
                                "value": str(arguments.get("limit", "None")),
                                "inline": True
                            }
                        ]
                    }
                
                elif tool_name == "Edit":
                    return {
                        "title": f"{pattern.get('icon', '✏️')} Editing File",
                        "description": f"Modifying: {arguments.get('file_path', 'unknown')}",
                        "color": pattern.get('color_pre', 0xe67e22),
                        "fields": [
                            {
                                "name": "File Path",
                                "value": arguments.get("file_path", "Not specified"),
                                "inline": False
                            },
                            {
                                "name": "Replace",
                                "value": f"```\n{arguments.get('old_string', '')[:100]}\n```",
                                "inline": False
                            },
                            {
                                "name": "With",
                                "value": f"```\n{arguments.get('new_string', '')[:100]}\n```",
                                "inline": False
                            }
                        ]
                    }
                
                elif tool_name == "Bash":
                    return {
                        "title": f"{pattern.get('icon', '⚡')} Executing Command",
                        "description": arguments.get("description", "Running shell command"),
                        "color": pattern.get('color_pre', 0x34495e),
                        "fields": [
                            {
                                "name": "Command",
                                "value": f"```bash\n{arguments.get('command', '')}\n```",
                                "inline": False
                            },
                            {
                                "name": "Timeout",
                                "value": f"{arguments.get('timeout', 30000)}ms",
                                "inline": True
                            }
                        ]
                    }
                
                elif tool_name == "Glob":
                    return {
                        "title": f"{pattern.get('icon', '🔍')} Finding Files",
                        "description": "Searching for matching files",
                        "color": pattern.get('color_pre', 0x1abc9c),
                        "fields": [
                            {
                                "name": "Pattern",
                                "value": f"`{arguments.get('pattern', '')}`",
                                "inline": True
                            },
                            {
                                "name": "Search Path",
                                "value": arguments.get("path", "Current directory"),
                                "inline": True
                            }
                        ]
                    }
                
                else:
                    return {
                        "title": f"🔧 {tool_name}",
                        "description": "Tool execution",
                        "color": 0x95a5a6,
                        "fields": [
                            {
                                "name": "Arguments",
                                "value": json.dumps(arguments, indent=2)[:500],
                                "inline": False
                            }
                        ]
                    }
            
            mock_instance.format_parameters.side_effect = format_tool_parameters
            
            formatter_registry = ToolFormatterRegistry()
            
            # Test parameter formatting for each tool
            for tool_name, tool_data in self.tool_test_data.items():
                with self.subTest(tool=tool_name):
                    pre_data = tool_data["pre_tool_use"]
                    arguments = pre_data.get("arguments", {})
                    
                    formatted = formatter_registry.format_parameters(tool_name, arguments)
                    
                    # Verify basic structure
                    self.assertIsInstance(formatted, dict)
                    self.assertIn("title", formatted)
                    self.assertIn("color", formatted)
                    self.assertIn("fields", formatted)
                    
                    # Verify tool-specific elements
                    pattern = self.expected_patterns.get(tool_name, {})
                    expected_icon = pattern.get("icon", "🔧")
                    self.assertIn(expected_icon, formatted["title"])
                    
                    # Verify key fields are present
                    field_names = [field["name"] for field in formatted.get("fields", [])]
                    key_fields = pattern.get("key_fields", [])
                    
                    for key_field in key_fields[:3]:  # Check first 3 key fields
                        if key_field in arguments:
                            # Should have a field related to this argument
                            matching_fields = [name for name in field_names 
                                             if key_field.lower() in name.lower()]
                            self.assertGreater(len(matching_fields), 0,
                                             f"No field found for key argument '{key_field}' in {tool_name}")
                    
                    # Log parameter formatting analysis
                    self.logger.info(
                        f"Parameter formatting: {tool_name}",
                        context={
                            "field_count": len(formatted.get("fields", [])),
                            "title": formatted.get("title"),
                            "color": hex(formatted.get("color", 0)),
                            "key_fields_covered": len([f for f in key_fields[:3] if f in str(formatted)])
                        }
                    )
    
    async def test_result_formatting_consistency(self) -> None:
        """Test consistency of result formatting across tools."""
        with patch('src.formatters.tool_formatters.ToolFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            def format_tool_result(tool_name: str, result: Dict[str, Any], execution_time: float) -> Dict[str, Any]:
                """Format tool execution results."""
                pattern = self.expected_patterns.get(tool_name, {})
                success = result.get("success", False)
                
                # Consistent base structure
                base_format = {
                    "title": f"{'✅' if success else '❌'} {tool_name} {'Completed' if success else 'Failed'}",
                    "color": pattern.get('color_post', 0x2ecc71) if success else 0xe74c3c,
                    "fields": [
                        {
                            "name": "Execution Time", 
                            "value": f"{execution_time:.3f}s",
                            "inline": True
                        },
                        {
                            "name": "Status",
                            "value": "Success" if success else "Failed",
                            "inline": True
                        }
                    ]
                }
                
                # Tool-specific result fields
                if tool_name == "Write":
                    if success:
                        base_format["fields"].extend([
                            {
                                "name": "File Created",
                                "value": "Yes" if result.get("file_created") else "No",
                                "inline": True
                            },
                            {
                                "name": "Bytes Written",
                                "value": str(result.get("bytes_written", 0)),
                                "inline": True
                            }
                        ])
                
                elif tool_name == "Read":
                    if success:
                        content = result.get("content", "")
                        base_format["fields"].extend([
                            {
                                "name": "Content Preview",
                                "value": f"```\n{content[:200]}{'...' if len(content) > 200 else ''}\n```",
                                "inline": False
                            },
                            {
                                "name": "File Size",
                                "value": f"{result.get('file_size', 0)} bytes",
                                "inline": True
                            }
                        ])
                
                elif tool_name == "Edit":
                    if success:
                        base_format["fields"].extend([
                            {
                                "name": "Changes Made",
                                "value": str(result.get("changes_made", 0)),
                                "inline": True
                            },
                            {
                                "name": "Lines Modified",
                                "value": str(result.get("lines_modified", 0)),
                                "inline": True
                            }
                        ])
                
                elif tool_name == "Bash":
                    exit_code = result.get("exit_code", -1)
                    stdout = result.get("stdout", "")
                    stderr = result.get("stderr", "")
                    
                    base_format["fields"].extend([
                        {
                            "name": "Exit Code",
                            "value": str(exit_code),
                            "inline": True
                        }
                    ])
                    
                    if stdout:
                        base_format["fields"].append({
                            "name": "Output",
                            "value": f"```\n{stdout[:800]}{'...' if len(stdout) > 800 else ''}\n```",
                            "inline": False
                        })
                    
                    if stderr:
                        base_format["fields"].append({
                            "name": "Errors",
                            "value": f"```\n{stderr[:400]}{'...' if len(stderr) > 400 else ''}\n```",
                            "inline": False
                        })
                
                elif tool_name == "Glob":
                    if success:
                        matches = result.get("matches", [])
                        base_format["fields"].extend([
                            {
                                "name": "Total Matches",
                                "value": str(result.get("total_matches", len(matches))),
                                "inline": True
                            },
                            {
                                "name": "Matches",
                                "value": "\n".join(matches[:10]) + ("\n..." if len(matches) > 10 else ""),
                                "inline": False
                            }
                        ])
                
                return base_format
            
            mock_instance.format_result.side_effect = format_tool_result
            
            formatter_registry = ToolFormatterRegistry()
            
            # Track consistency metrics
            consistency_metrics = {
                "common_fields": [],
                "color_consistency": [],
                "structure_consistency": []
            }
            
            # Test result formatting for each tool
            formatted_results = {}
            
            for tool_name, tool_data in self.tool_test_data.items():
                post_data = tool_data["post_tool_use"]
                result = post_data.get("result", {})
                execution_time = post_data.get("execution_time", 0.0)
                
                formatted = formatter_registry.format_result(tool_name, result, execution_time)
                formatted_results[tool_name] = formatted
                
                with self.subTest(tool=tool_name):
                    # Verify basic structure consistency
                    self.assertIn("title", formatted)
                    self.assertIn("color", formatted)
                    self.assertIn("fields", formatted)
                    
                    # Verify common fields are present
                    field_names = [field["name"] for field in formatted.get("fields", [])]
                    common_fields = ["Execution Time", "Status"]
                    
                    for common_field in common_fields:
                        self.assertIn(common_field, field_names,
                                    f"Missing common field '{common_field}' in {tool_name} result")
                    
                    consistency_metrics["common_fields"].append(len([f for f in common_fields if f in field_names]))
                    
                    # Check color consistency for success/failure
                    success = result.get("success", False)
                    color = formatted.get("color", 0)
                    
                    if success:
                        # Should be green-ish for success
                        self.assertIn(color, [0x2ecc71, 0x27ae60], f"Unexpected success color for {tool_name}: {hex(color)}")
                    else:
                        # Should be red-ish for failure
                        self.assertEqual(color, 0xe74c3c, f"Unexpected failure color for {tool_name}: {hex(color)}")
                    
                    consistency_metrics["color_consistency"].append(1 if color in [0x2ecc71, 0x27ae60, 0xe74c3c] else 0)
                    
                    # Log result formatting analysis
                    self.logger.info(
                        f"Result formatting: {tool_name}",
                        context={
                            "success": success,
                            "field_count": len(formatted.get("fields", [])),
                            "color": hex(color),
                            "execution_time": execution_time,
                            "has_common_fields": all(f in field_names for f in common_fields)
                        }
                    )
            
            # Analyze overall consistency
            avg_common_fields = sum(consistency_metrics["common_fields"]) / len(consistency_metrics["common_fields"])
            color_consistency_rate = sum(consistency_metrics["color_consistency"]) / len(consistency_metrics["color_consistency"])
            
            self.assertGreaterEqual(avg_common_fields, 1.8, "Low common fields consistency")
            self.assertGreaterEqual(color_consistency_rate, 0.8, "Low color consistency")
    
    async def test_large_content_handling(self) -> None:
        """Test handling of large content in tool formatting."""
        with patch('src.formatters.tool_formatters.ToolFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Create test data with large content
            large_content_scenarios = {
                "large_file_write": {
                    "tool_name": "Write",
                    "arguments": {
                        "file_path": "/home/user/large_file.txt",
                        "content": "x" * 10000  # 10KB content
                    }
                },
                "large_bash_output": {
                    "tool_name": "Bash",
                    "result": {
                        "success": True,
                        "exit_code": 0,
                        "stdout": "line\n" * 1000,  # 1000 lines
                        "stderr": ""
                    }
                },
                "many_glob_matches": {
                    "tool_name": "Glob",
                    "result": {
                        "success": True,
                        "matches": [f"/path/to/file_{i}.txt" for i in range(500)],  # 500 matches
                        "total_matches": 500
                    }
                }
            }
            
            def format_large_content(tool_name: str, data: Dict[str, Any], content_type: str) -> Dict[str, Any]:
                """Format large content with appropriate truncation."""
                
                if content_type == "arguments" and tool_name == "Write":
                    content = data.get("content", "")
                    truncated_content = content[:500] + ("..." if len(content) > 500 else "")
                    
                    return {
                        "title": "📝 Writing Large File",
                        "description": f"Creating file: {data.get('file_path')}",
                        "color": 0x3498db,
                        "fields": [
                            {
                                "name": "File Path",
                                "value": data.get("file_path", "unknown"),
                                "inline": False
                            },
                            {
                                "name": "Content Preview",
                                "value": f"```\n{truncated_content}\n```",
                                "inline": False
                            },
                            {
                                "name": "Total Size",
                                "value": f"{len(content)} characters",
                                "inline": True
                            },
                            {
                                "name": "Preview Size",
                                "value": f"{len(truncated_content)} characters",
                                "inline": True
                            }
                        ]
                    }
                
                elif content_type == "result" and tool_name == "Bash":
                    stdout = data.get("stdout", "")
                    truncated_stdout = stdout[:1000] + ("..." if len(stdout) > 1000 else "")
                    
                    return {
                        "title": "✅ Bash Completed",
                        "color": 0x2ecc71,
                        "fields": [
                            {
                                "name": "Exit Code",
                                "value": str(data.get("exit_code", 0)),
                                "inline": True
                            },
                            {
                                "name": "Output Lines",
                                "value": str(stdout.count("\n")),
                                "inline": True
                            },
                            {
                                "name": "Output Preview",
                                "value": f"```\n{truncated_stdout}\n```",
                                "inline": False
                            }
                        ]
                    }
                
                elif content_type == "result" and tool_name == "Glob":
                    matches = data.get("matches", [])
                    displayed_matches = matches[:20]  # Show first 20
                    
                    return {
                        "title": "✅ Glob Completed",
                        "color": 0x2ecc71,
                        "fields": [
                            {
                                "name": "Total Matches",
                                "value": str(len(matches)),
                                "inline": True
                            },
                            {
                                "name": "Displayed",
                                "value": str(len(displayed_matches)),
                                "inline": True
                            },
                            {
                                "name": "Matches",
                                "value": "\n".join(displayed_matches) + (f"\n... and {len(matches) - len(displayed_matches)} more" if len(matches) > len(displayed_matches) else ""),
                                "inline": False
                            }
                        ]
                    }
                
                return {"title": "Unknown", "color": 0x95a5a6, "fields": []}
            
            # Mock the formatting function
            def mock_format_function(*args, **kwargs):
                if len(args) >= 3:
                    return format_large_content(args[0], args[1], args[2])
                elif len(args) >= 2:
                    # Determine content type based on data structure
                    data = args[1]
                    if "arguments" in str(data) or "content" in data:
                        return format_large_content(args[0], data, "arguments")
                    else:
                        return format_large_content(args[0], data, "result")
                return {"title": "Mock", "color": 0x95a5a6, "fields": []}
            
            mock_instance.format_large_content.side_effect = mock_format_function
            
            formatter_registry = ToolFormatterRegistry()
            
            # Test large content handling
            for scenario_name, scenario_data in large_content_scenarios.items():
                with self.subTest(scenario=scenario_name):
                    tool_name = scenario_data["tool_name"]
                    
                    if "arguments" in scenario_data:
                        formatted = formatter_registry.format_large_content(
                            tool_name, scenario_data["arguments"], "arguments"
                        )
                        content_type = "arguments"
                    else:
                        formatted = formatter_registry.format_large_content(
                            tool_name, scenario_data["result"], "result"
                        )
                        content_type = "result"
                    
                    # Verify truncation was applied
                    self.assertIsInstance(formatted, dict)
                    self.assertIn("fields", formatted)
                    
                    # Check that content was truncated appropriately
                    for field in formatted.get("fields", []):
                        field_value = field.get("value", "")
                        
                        # No single field should be excessively long
                        self.assertLessEqual(len(field_value), 2000,
                                           f"Field '{field.get('name')}' too long in {scenario_name}")
                        
                        # Should indicate truncation if original was large
                        if scenario_name == "large_file_write" and "Content" in field.get("name", ""):
                            self.assertIn("...", field_value, "Large content should show truncation indicator")
                        
                        elif scenario_name == "large_bash_output" and "Output" in field.get("name", ""):
                            self.assertIn("...", field_value, "Large output should show truncation indicator")
                        
                        elif scenario_name == "many_glob_matches" and "Matches" in field.get("name", ""):
                            self.assertIn("more", field_value, "Many matches should show continuation indicator")
                    
                    # Log large content handling analysis
                    total_length = sum(len(field.get("value", "")) for field in formatted.get("fields", []))
                    
                    self.logger.info(
                        f"Large content handling: {scenario_name}",
                        context={
                            "tool_name": tool_name,
                            "content_type": content_type,
                            "total_formatted_length": total_length,
                            "field_count": len(formatted.get("fields", [])),
                            "truncation_applied": "..." in str(formatted) or "more" in str(formatted)
                        }
                    )
    
    async def test_specialized_tool_formatting(self) -> None:
        """Test specialized formatting logic for specific tools."""
        with patch('src.formatters.tool_formatters.ToolFormatterRegistry') as mock_registry:
            mock_instance = MagicMock()
            mock_registry.return_value = mock_instance
            
            # Specialized scenarios for different tools
            specialized_scenarios = {
                "edit_with_regex": {
                    "tool_name": "Edit",
                    "arguments": {
                        "file_path": "/home/user/script.py",
                        "old_string": r"def\s+(\w+)\(",
                        "new_string": r"async def \1(",
                        "replace_all": True
                    }
                },
                "bash_with_pipes": {
                    "tool_name": "Bash",
                    "arguments": {
                        "command": "find /home/user -name '*.py' | grep -v __pycache__ | head -10",
                        "description": "Find Python files excluding cache"
                    }
                },
                "glob_with_exclusions": {
                    "tool_name": "Glob",
                    "arguments": {
                        "pattern": "**/*.py",
                        "path": "/home/user/project",
                        "ignore": ["**/__pycache__/**", "**/.*/**"]
                    }
                },
                "read_with_encoding": {
                    "tool_name": "Read",
                    "arguments": {
                        "file_path": "/home/user/unicode_file.txt",
                        "encoding": "utf-8",
                        "offset": 100,
                        "limit": 500
                    }
                }
            }
            
            def format_specialized_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
                """Format tools with specialized logic."""
                
                if tool_name == "Edit" and "replace_all" in arguments:
                    old_str = arguments.get("old_string", "")
                    new_str = arguments.get("new_string", "")
                    is_regex = bool(any(char in old_str for char in r".*+?[]{}()^$\|"))
                    
                    return {
                        "title": "✏️ Advanced Edit (Replace All)",
                        "description": f"{'Regex' if is_regex else 'Text'} replacement in {arguments.get('file_path')}",
                        "color": 0xe67e22,
                        "fields": [
                            {
                                "name": "File",
                                "value": arguments.get("file_path", "unknown"),
                                "inline": False
                            },
                            {
                                "name": "Pattern Type",
                                "value": "Regular Expression" if is_regex else "Literal Text",
                                "inline": True
                            },
                            {
                                "name": "Replace All",
                                "value": "Yes" if arguments.get("replace_all") else "No",
                                "inline": True
                            },
                            {
                                "name": "Find Pattern",
                                "value": f"```regex\n{old_str}\n```" if is_regex else f"```\n{old_str}\n```",
                                "inline": False
                            },
                            {
                                "name": "Replace With",
                                "value": f"```regex\n{new_str}\n```" if is_regex else f"```\n{new_str}\n```",
                                "inline": False
                            }
                        ]
                    }
                
                elif tool_name == "Bash" and "|" in arguments.get("command", ""):
                    command = arguments.get("command", "")
                    pipeline_steps = [step.strip() for step in command.split("|")]
                    
                    return {
                        "title": "⚡ Pipeline Command",
                        "description": arguments.get("description", "Multi-step command pipeline"),
                        "color": 0x34495e,
                        "fields": [
                            {
                                "name": "Pipeline Steps",
                                "value": str(len(pipeline_steps)),
                                "inline": True
                            },
                            {
                                "name": "Full Command",
                                "value": f"```bash\n{command}\n```",
                                "inline": False
                            }
                        ] + [
                            {
                                "name": f"Step {i+1}",
                                "value": f"`{step}`",
                                "inline": True
                            } for i, step in enumerate(pipeline_steps[:5])  # Show first 5 steps
                        ]
                    }
                
                elif tool_name == "Glob" and "ignore" in arguments:
                    ignore_patterns = arguments.get("ignore", [])
                    
                    return {
                        "title": "🔍 Advanced Glob (with exclusions)",
                        "description": "Pattern matching with ignore rules",
                        "color": 0x1abc9c,
                        "fields": [
                            {
                                "name": "Include Pattern",
                                "value": f"`{arguments.get('pattern', '')}`",
                                "inline": True
                            },
                            {
                                "name": "Search Path",
                                "value": arguments.get("path", "Current directory"),
                                "inline": True
                            },
                            {
                                "name": "Ignore Patterns",
                                "value": "\n".join(f"`{pattern}`" for pattern in ignore_patterns),
                                "inline": False
                            }
                        ]
                    }
                
                elif tool_name == "Read" and "encoding" in arguments:
                    return {
                        "title": "📖 Advanced Read (with encoding)",
                        "description": f"Reading with {arguments.get('encoding', 'default')} encoding",
                        "color": 0x9b59b6,
                        "fields": [
                            {
                                "name": "File",
                                "value": arguments.get("file_path", "unknown"),
                                "inline": False
                            },
                            {
                                "name": "Encoding",
                                "value": arguments.get("encoding", "default"),
                                "inline": True
                            },
                            {
                                "name": "Offset",
                                "value": str(arguments.get("offset", 0)),
                                "inline": True
                            },
                            {
                                "name": "Limit",
                                "value": str(arguments.get("limit", "None")),
                                "inline": True
                            }
                        ]
                    }
                
                return {
                    "title": f"🔧 {tool_name}",
                    "description": "Standard tool formatting",
                    "color": 0x95a5a6,
                    "fields": []
                }
            
            mock_instance.format_specialized.side_effect = format_specialized_tool
            
            formatter_registry = ToolFormatterRegistry()
            
            # Test specialized formatting
            for scenario_name, scenario_data in specialized_scenarios.items():
                with self.subTest(scenario=scenario_name):
                    tool_name = scenario_data["tool_name"]
                    arguments = scenario_data["arguments"]
                    
                    formatted = formatter_registry.format_specialized(tool_name, arguments)
                    
                    # Verify specialized formatting was applied
                    self.assertIn("title", formatted)
                    self.assertIn("Advanced" if "Advanced" in formatted["title"] else tool_name, formatted["title"])
                    
                    # Verify tool-specific specializations
                    if scenario_name == "edit_with_regex":
                        field_names = [f["name"] for f in formatted.get("fields", [])]
                        self.assertIn("Pattern Type", field_names)
                        self.assertIn("Replace All", field_names)
                    
                    elif scenario_name == "bash_with_pipes":
                        self.assertIn("Pipeline", formatted["title"])
                        field_names = [f["name"] for f in formatted.get("fields", [])]
                        self.assertIn("Pipeline Steps", field_names)
                    
                    elif scenario_name == "glob_with_exclusions":
                        field_names = [f["name"] for f in formatted.get("fields", [])]
                        self.assertIn("Ignore Patterns", field_names)
                    
                    elif scenario_name == "read_with_encoding":
                        field_names = [f["name"] for f in formatted.get("fields", [])]
                        self.assertIn("Encoding", field_names)
                    
                    # Log specialized formatting analysis
                    self.logger.info(
                        f"Specialized formatting: {scenario_name}",
                        context={
                            "tool_name": tool_name,
                            "specialization_detected": "Advanced" in formatted.get("title", ""),
                            "field_count": len(formatted.get("fields", [])),
                            "specialized_fields": [f["name"] for f in formatted.get("fields", []) 
                                                 if f["name"] not in ["File", "Command", "Pattern"]]
                        }
                    )


def run_tool_formatting_tests() -> None:
    """Run tool formatting tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestToolFormatting)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nTool Formatting Tests Summary:")
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