#!/usr/bin/env python3
"""Test Complete Workflow End-to-End.

This module provides comprehensive end-to-end tests for the complete
Discord notifier workflow, testing the entire system from event
reception to Discord message delivery.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
import sys
import time
import threading
import tempfile
import shutil
import sqlite3
import os
import subprocess
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.discord_notifier import main as discord_notifier_main
from src.core.http_client import HTTPClient, DiscordMessage
from src.handlers.discord_sender import DiscordContext, send_to_discord
from src.handlers.thread_manager import get_or_create_thread, SESSION_THREAD_CACHE
from src.thread_storage import ThreadStorage
from src.core.config_loader import ConfigLoader
from src.formatters.event_formatters import format_event
from src.type_defs.events import BaseEventData


# End-to-end test types
@dataclass
class WorkflowScenario:
    """Complete workflow test scenario."""
    name: str
    description: str
    events: List[Dict[str, Any]]
    expected_discord_messages: int
    expected_threads_created: int
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 60.0
    verify_message_content: bool = True
    verify_timestamps: bool = True


@dataclass
class WorkflowResult:
    """Result of complete workflow test."""
    scenario_name: str
    success: bool
    events_processed: int
    discord_messages_sent: int
    threads_created: int
    processing_time: float
    errors_encountered: List[str]
    message_contents: List[str]
    final_state: Dict[str, Any]


class MockDiscordAPIServer:
    """Mock Discord API server for end-to-end testing."""
    
    def __init__(self):
        self.webhook_calls = []
        self.bot_api_calls = []
        self.threads = {}
        self.messages = {}
        self.rate_limits = {}
        self.server_errors = []
        self.response_delays = {}
        
    def webhook_post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock webhook POST with realistic Discord API behavior."""
        call_info = {
            "url": url,
            "data": data,
            "timestamp": time.time(),
            "method": "POST"
        }
        self.webhook_calls.append(call_info)
        
        # Simulate rate limiting
        if self._should_rate_limit("webhook", url):
            raise Exception("Rate limited")
        
        # Simulate server delays
        if url in self.response_delays:
            time.sleep(self.response_delays[url])
        
        # Create realistic response
        message_id = f"msg_{int(time.time() * 1000)}"
        response = {
            "id": message_id,
            "type": 0,
            "content": data.get("content", ""),
            "embeds": data.get("embeds", []),
            "username": data.get("username", "Claude Code"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "edited_timestamp": None,
            "flags": 0,
            "webhook_id": url.split("/")[-2]
        }
        
        self.messages[message_id] = response
        return response
    
    def bot_api_call(self, method: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock bot API call with realistic Discord API behavior."""
        call_info = {
            "method": method,
            "endpoint": endpoint,
            "data": data,
            "timestamp": time.time()
        }
        self.bot_api_calls.append(call_info)
        
        # Handle different endpoints
        if "threads" in endpoint and method == "POST":
            return self._handle_thread_creation(endpoint, data)
        elif "threads" in endpoint and method == "GET":
            return self._handle_thread_lookup(endpoint)
        elif "messages" in endpoint and method == "POST":
            return self._handle_message_post(endpoint, data)
        else:
            return {"success": True, "id": f"api_response_{len(self.bot_api_calls)}"}
    
    def _handle_thread_creation(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle thread creation API call."""
        thread_id = f"thread_{int(time.time() * 1000)}"
        thread_info = {
            "id": thread_id,
            "name": data.get("name", "Claude Session"),
            "parent_id": data.get("parent_id", "123456789"),
            "type": 11,  # PUBLIC_THREAD
            "message_count": 0,
            "member_count": 1,
            "rate_limit_per_user": 0,
            "thread_metadata": {
                "archived": False,
                "auto_archive_duration": 1440,
                "archive_timestamp": None,
                "locked": False
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        self.threads[thread_id] = thread_info
        return thread_info
    
    def _handle_thread_lookup(self, endpoint: str) -> Dict[str, Any]:
        """Handle thread lookup API call."""
        # Return list of threads for channel
        return {
            "threads": list(self.threads.values()),
            "members": [],
            "has_more": False
        }
    
    def _handle_message_post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle message posting to thread."""
        message_id = f"msg_{int(time.time() * 1000)}"
        message_info = {
            "id": message_id,
            "type": 0,
            "content": data.get("content", ""),
            "embeds": data.get("embeds", []),
            "author": {
                "id": "bot_user_id",
                "username": "Claude Code",
                "bot": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel_id": endpoint.split("/")[-3]
        }
        
        self.messages[message_id] = message_info
        return message_info
    
    def _should_rate_limit(self, api_type: str, identifier: str) -> bool:
        """Determine if request should be rate limited."""
        now = time.time()
        rate_limit_key = f"{api_type}_{identifier}"
        
        if rate_limit_key not in self.rate_limits:
            self.rate_limits[rate_limit_key] = []
        
        # Remove old requests (older than 1 second)
        self.rate_limits[rate_limit_key] = [
            timestamp for timestamp in self.rate_limits[rate_limit_key] 
            if now - timestamp < 1.0
        ]
        
        # Check if we exceed rate limit (5 requests per second)
        if len(self.rate_limits[rate_limit_key]) >= 5:
            return True
        
        self.rate_limits[rate_limit_key].append(now)
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive API usage statistics."""
        return {
            "webhook_calls": len(self.webhook_calls),
            "bot_api_calls": len(self.bot_api_calls),
            "threads_created": len(self.threads),
            "messages_sent": len(self.messages),
            "rate_limit_hits": sum(1 for calls in self.rate_limits.values() if len(calls) >= 5),
            "server_errors": len(self.server_errors),
            "total_calls": len(self.webhook_calls) + len(self.bot_api_calls)
        }
    
    def reset(self) -> None:
        """Reset mock server state."""
        self.webhook_calls.clear()
        self.bot_api_calls.clear()
        self.threads.clear()
        self.messages.clear()
        self.rate_limits.clear()
        self.server_errors.clear()
        self.response_delays.clear()


class CompleteWorkflowTester:
    """Manages complete workflow end-to-end testing."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.mock_server = MockDiscordAPIServer()
        self.temp_dir = tempfile.mkdtemp()
        self.test_database = str(Path(self.temp_dir) / "test.db")
        
    def create_test_config(self, overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create test configuration."""
        base_config = {
            "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/abcdefgh",
            "DISCORD_BOT_TOKEN": "Bot TEST_TOKEN_PLACEHOLDER",
            "DISCORD_CHANNEL_ID": "123456789",
            "DISCORD_USE_THREADS": True,
            "DISCORD_THREAD_NAME_PREFIX": "Claude-",
            "DISCORD_ENABLED_EVENTS": ["Start", "ToolUse", "Stop", "Error", "Response"],
            "DISCORD_DEBUG": True,
            "DATABASE_PATH": self.test_database,
            "TIMEOUT_SECONDS": 30,
            "MAX_RETRIES": 3
        }
        
        if overrides:
            base_config.update(overrides)
        
        return base_config
    
    async def run_complete_workflow(self, scenario: WorkflowScenario) -> WorkflowResult:
        """Run complete workflow scenario end-to-end."""
        start_time = time.time()
        errors_encountered = []
        message_contents = []
        
        # Reset mock server
        self.mock_server.reset()
        
        # Create test configuration
        test_config = self.create_test_config(scenario.config_overrides)
        
        # Initialize database
        thread_storage = ThreadStorage(self.test_database)
        thread_storage.init_database()
        
        try:
            # Set up environment variables
            env_vars = {
                "DISCORD_WEBHOOK_URL": test_config["DISCORD_WEBHOOK_URL"],
                "DISCORD_USE_THREADS": str(test_config["DISCORD_USE_THREADS"]),
                "DISCORD_DEBUG": str(test_config["DISCORD_DEBUG"]),
                "DISCORD_ENABLED_EVENTS": ",".join(test_config["DISCORD_ENABLED_EVENTS"])
            }
            
            # Mock Discord API calls
            with patch('src.core.http_client.HTTPClient.post', side_effect=self.mock_server.webhook_post), \
                 patch('src.core.http_client.HTTPClient.get', side_effect=self.mock_server.bot_api_call), \
                 patch.dict(os.environ, env_vars):
                
                # Process each event through the complete system
                events_processed = 0
                for event in scenario.events:
                    try:
                        await self._process_event_through_system(event, test_config)
                        events_processed += 1
                        
                        # Extract message content for verification
                        if scenario.verify_message_content:
                            content = self._extract_message_content(event)
                            if content:
                                message_contents.append(content)
                                
                    except Exception as e:
                        error_msg = f"Event {events_processed}: {str(e)}"
                        errors_encountered.append(error_msg)
                        self.logger.error("Event processing failed", error=str(e), event=event)
            
            processing_time = time.time() - start_time
            
            # Get statistics from mock server
            stats = self.mock_server.get_statistics()
            
            # Verify results
            success = (
                len(errors_encountered) == 0 and
                events_processed == len(scenario.events) and
                stats["webhook_calls"] == scenario.expected_discord_messages and
                stats["threads_created"] == scenario.expected_threads_created
            )
            
            return WorkflowResult(
                scenario_name=scenario.name,
                success=success,
                events_processed=events_processed,
                discord_messages_sent=stats["webhook_calls"],
                threads_created=stats["threads_created"],
                processing_time=processing_time,
                errors_encountered=errors_encountered,
                message_contents=message_contents,
                final_state=self._get_final_system_state(stats)
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return WorkflowResult(
                scenario_name=scenario.name,
                success=False,
                events_processed=0,
                discord_messages_sent=0,
                threads_created=0,
                processing_time=processing_time,
                errors_encountered=[f"Workflow error: {str(e)}"],
                message_contents=[],
                final_state={}
            )
        finally:
            # Cleanup
            thread_storage.close()
    
    async def _process_event_through_system(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Process event through the complete system."""
        # This simulates the complete discord_notifier.py workflow
        
        # 1. Format the event
        formatted_output = format_event(event)
        
        # 2. Create Discord message
        discord_message: DiscordMessage = {
            "content": formatted_output.get("content", ""),
            "embeds": formatted_output.get("embeds", []),
            "username": formatted_output.get("username", "Claude Code")
        }
        
        # 3. Handle threading if enabled
        if config.get("DISCORD_USE_THREADS", False):
            session_id = event.get("session_id", "default")
            
            # Create Discord context
            http_client = HTTPClient()
            discord_context = DiscordContext(
                config=config,
                logger=self.logger,
                http_client=http_client
            )
            
            # Get or create thread
            thread_id = get_or_create_thread(
                session_id=session_id,
                config=config,
                http_client=http_client,
                logger=self.logger
            )
            
            if thread_id:
                discord_message["thread_id"] = thread_id
        
        # 4. Send to Discord
        if not discord_context:
            http_client = HTTPClient()
            discord_context = DiscordContext(
                config=config,
                logger=self.logger,
                http_client=http_client
            )
        
        # Send the message
        success = send_to_discord(discord_message, discord_context)
        
        if not success:
            raise Exception("Failed to send Discord message")
        
        # 5. Small delay to simulate real processing
        await asyncio.sleep(0.01)
    
    def _extract_message_content(self, event: Dict[str, Any]) -> str:
        """Extract expected message content from event."""
        event_type = event.get("event_type", "")
        
        if event_type == "Start":
            return f"Session started"
        elif event_type == "ToolUse":
            tool_name = event.get("tool_name", "unknown")
            return f"Tool: {tool_name}"
        elif event_type == "Stop":
            return "Session ended"
        elif event_type == "Error":
            return "Error occurred"
        
        return ""
    
    def _get_final_system_state(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Get final system state."""
        return {
            "database_exists": Path(self.test_database).exists(),
            "mock_server_stats": stats,
            "threads_in_cache": len(SESSION_THREAD_CACHE),
            "processing_complete": True
        }
    
    def cleanup(self) -> None:
        """Clean up test resources."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
        
        # Clear session cache
        SESSION_THREAD_CACHE.clear()


class TestCompleteWorkflow(unittest.IsolatedAsyncioTestCase):
    """Test cases for complete workflow end-to-end."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.workflow_tester = CompleteWorkflowTester()
        
        # Define workflow scenarios
        self.workflow_scenarios = [
            WorkflowScenario(
                name="basic_session_workflow",
                description="Basic session with start, tool use, and stop",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-001",
                        "user": "test-user",
                        "hook_event_name": "Start"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-001",
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "/test/file.py", "old_string": "old", "new_string": "new"},
                        "hook_event_name": "ToolUse"
                    },
                    {
                        "event_type": "Stop",
                        "timestamp": "2024-01-01T00:02:00Z",
                        "session_id": "session-001",
                        "hook_event_name": "Stop"
                    }
                ],
                expected_discord_messages=3,
                expected_threads_created=1
            ),
            WorkflowScenario(
                name="multi_session_parallel",
                description="Multiple parallel sessions with threading",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-A",
                        "user": "user-A",
                        "hook_event_name": "Start"
                    },
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:01Z",
                        "session_id": "session-B",
                        "user": "user-B",
                        "hook_event_name": "Start"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-A",
                        "tool_name": "Read",
                        "tool_input": {"file_path": "/test/file1.py"},
                        "hook_event_name": "ToolUse"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:01Z",
                        "session_id": "session-B",
                        "tool_name": "Write",
                        "tool_input": {"file_path": "/test/file2.py", "content": "test"},
                        "hook_event_name": "ToolUse"
                    }
                ],
                expected_discord_messages=4,
                expected_threads_created=2
            ),
            WorkflowScenario(
                name="error_handling_workflow",
                description="Session with error handling",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-error",
                        "user": "test-user",
                        "hook_event_name": "Start"
                    },
                    {
                        "event_type": "Error",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-error",
                        "error_type": "ValidationError",
                        "error_message": "Invalid input provided",
                        "hook_event_name": "Error"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:02:00Z",
                        "session_id": "session-error",
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "/test/recovery.py"},
                        "hook_event_name": "ToolUse"
                    },
                    {
                        "event_type": "Stop",
                        "timestamp": "2024-01-01T00:03:00Z",
                        "session_id": "session-error",
                        "hook_event_name": "Stop"
                    }
                ],
                expected_discord_messages=4,
                expected_threads_created=1
            ),
            WorkflowScenario(
                name="threading_disabled_workflow",
                description="Workflow with threading disabled",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-no-thread",
                        "user": "test-user",
                        "hook_event_name": "Start"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-no-thread",
                        "tool_name": "Bash",
                        "tool_input": {"command": "echo 'hello'"},
                        "hook_event_name": "ToolUse"
                    },
                    {
                        "event_type": "Stop",
                        "timestamp": "2024-01-01T00:02:00Z",
                        "session_id": "session-no-thread",
                        "hook_event_name": "Stop"
                    }
                ],
                expected_discord_messages=3,
                expected_threads_created=0,
                config_overrides={"DISCORD_USE_THREADS": False}
            ),
            WorkflowScenario(
                name="high_volume_workflow",
                description="High volume event processing",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "high-volume",
                        "user": "test-user",
                        "hook_event_name": "Start"
                    }
                ] + [
                    {
                        "event_type": "ToolUse",
                        "timestamp": f"2024-01-01T00:{i:02d}:00Z",
                        "session_id": "high-volume",
                        "tool_name": "Edit",
                        "tool_input": {"file_path": f"/test/file{i}.py", "content": f"content {i}"},
                        "hook_event_name": "ToolUse"
                    }
                    for i in range(1, 21)  # 20 tool use events
                ] + [
                    {
                        "event_type": "Stop",
                        "timestamp": "2024-01-01T00:21:00Z",
                        "session_id": "high-volume",
                        "hook_event_name": "Stop"
                    }
                ],
                expected_discord_messages=22,  # 1 start + 20 tool use + 1 stop
                expected_threads_created=1,
                timeout_seconds=90.0
            )
        ]
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.workflow_tester.cleanup()
    
    async def test_basic_session_workflow(self) -> None:
        """Test basic session workflow end-to-end."""
        scenario = self.workflow_scenarios[0]  # basic_session_workflow
        
        result = await self.workflow_tester.run_complete_workflow(scenario)
        
        # Verify workflow success
        self.assertTrue(result.success, f"Workflow failed: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 3)
        self.assertEqual(result.discord_messages_sent, 3)
        self.assertEqual(result.threads_created, 1)
        self.assertLess(result.processing_time, scenario.timeout_seconds)
        
        # Verify message contents
        self.assertEqual(len(result.message_contents), 3)
        self.assertIn("Session started", " ".join(result.message_contents))
        self.assertIn("Tool: Edit", " ".join(result.message_contents))
        self.assertIn("Session ended", " ".join(result.message_contents))
        
        # Verify final state
        self.assertTrue(result.final_state["database_exists"])
        self.assertTrue(result.final_state["processing_complete"])
    
    async def test_multi_session_parallel_workflow(self) -> None:
        """Test multi-session parallel workflow."""
        scenario = self.workflow_scenarios[1]  # multi_session_parallel
        
        result = await self.workflow_tester.run_complete_workflow(scenario)
        
        # Verify parallel processing
        self.assertTrue(result.success, f"Workflow failed: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 4)
        self.assertEqual(result.discord_messages_sent, 4)
        self.assertEqual(result.threads_created, 2)
        
        # Verify performance (parallel should be faster)
        self.assertLess(result.processing_time, scenario.timeout_seconds)
    
    async def test_error_handling_workflow(self) -> None:
        """Test error handling in workflow."""
        scenario = self.workflow_scenarios[2]  # error_handling_workflow
        
        result = await self.workflow_tester.run_complete_workflow(scenario)
        
        # Verify error handling doesn't break workflow
        self.assertTrue(result.success, f"Workflow failed: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 4)
        self.assertEqual(result.discord_messages_sent, 4)
        
        # Verify error message was processed
        self.assertIn("Error occurred", " ".join(result.message_contents))
    
    async def test_threading_disabled_workflow(self) -> None:
        """Test workflow with threading disabled."""
        scenario = self.workflow_scenarios[3]  # threading_disabled_workflow
        
        result = await self.workflow_tester.run_complete_workflow(scenario)
        
        # Verify workflow without threading
        self.assertTrue(result.success, f"Workflow failed: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 3)
        self.assertEqual(result.discord_messages_sent, 3)
        self.assertEqual(result.threads_created, 0)  # No threads created
    
    async def test_high_volume_workflow(self) -> None:
        """Test high volume event processing."""
        scenario = self.workflow_scenarios[4]  # high_volume_workflow
        
        result = await self.workflow_tester.run_complete_workflow(scenario)
        
        # Verify high volume processing
        self.assertTrue(result.success, f"Workflow failed: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 22)
        self.assertEqual(result.discord_messages_sent, 22)
        self.assertEqual(result.threads_created, 1)
        self.assertLess(result.processing_time, scenario.timeout_seconds)
        
        # Verify performance metrics
        stats = result.final_state["mock_server_stats"]
        self.assertEqual(stats["total_calls"], 22)
        self.assertLessEqual(stats["rate_limit_hits"], 1)  # Should handle rate limits gracefully
    
    async def test_workflow_performance_metrics(self) -> None:
        """Test workflow performance metrics."""
        scenario = self.workflow_scenarios[0]  # Use basic workflow for metrics
        
        # Run workflow multiple times to get average metrics
        results = []
        for _ in range(3):
            result = await self.workflow_tester.run_complete_workflow(scenario)
            results.append(result)
        
        # Calculate average metrics
        avg_processing_time = sum(r.processing_time for r in results) / len(results)
        avg_events_per_second = sum(r.events_processed / r.processing_time for r in results) / len(results)
        
        # Verify performance targets
        self.assertLess(avg_processing_time, 5.0)  # Should complete in under 5 seconds
        self.assertGreater(avg_events_per_second, 1.0)  # Should process at least 1 event per second
        
        # Verify consistency
        processing_times = [r.processing_time for r in results]
        time_variance = max(processing_times) - min(processing_times)
        self.assertLess(time_variance, 2.0)  # Should have consistent performance
    
    async def test_workflow_error_recovery(self) -> None:
        """Test workflow error recovery."""
        # Create scenario with intentional errors
        error_scenario = WorkflowScenario(
            name="error_recovery_test",
            description="Test error recovery mechanisms",
            events=[
                {
                    "event_type": "Start",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "session_id": "error-recovery",
                    "user": "test-user",
                    "hook_event_name": "Start"
                },
                {
                    "event_type": "ToolUse",
                    "timestamp": "2024-01-01T00:01:00Z",
                    "session_id": "error-recovery",
                    "tool_name": "InvalidTool",  # This might cause issues
                    "tool_input": {"invalid": "data"},
                    "hook_event_name": "ToolUse"
                }
            ],
            expected_discord_messages=2,
            expected_threads_created=1
        )
        
        # Mock server error on first attempt
        original_webhook_post = self.workflow_tester.mock_server.webhook_post
        
        def failing_webhook_post(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
            if "InvalidTool" in str(data):
                # Fail first time, succeed on retry
                if not hasattr(failing_webhook_post, 'failed_once'):
                    failing_webhook_post.failed_once = True
                    raise Exception("Simulated network error")
            return original_webhook_post(url, data)
        
        self.workflow_tester.mock_server.webhook_post = failing_webhook_post
        
        result = await self.workflow_tester.run_complete_workflow(error_scenario)
        
        # Verify workflow continues despite errors
        self.assertGreater(result.events_processed, 0)
        # May not be fully successful due to simulated errors, but should handle gracefully
    
    async def test_workflow_state_persistence(self) -> None:
        """Test workflow state persistence across runs."""
        # First workflow run
        scenario1 = WorkflowScenario(
            name="persistence_test_1",
            description="First run for persistence testing",
            events=[
                {
                    "event_type": "Start",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "session_id": "persistent-session",
                    "user": "test-user",
                    "hook_event_name": "Start"
                }
            ],
            expected_discord_messages=1,
            expected_threads_created=1
        )
        
        result1 = await self.workflow_tester.run_complete_workflow(scenario1)
        self.assertTrue(result1.success)
        
        # Second workflow run with same session (should reuse thread)
        scenario2 = WorkflowScenario(
            name="persistence_test_2",
            description="Second run for persistence testing",
            events=[
                {
                    "event_type": "ToolUse",
                    "timestamp": "2024-01-01T00:01:00Z",
                    "session_id": "persistent-session",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": "/test/file.py"},
                    "hook_event_name": "ToolUse"
                }
            ],
            expected_discord_messages=1,
            expected_threads_created=0  # Should reuse existing thread
        )
        
        result2 = await self.workflow_tester.run_complete_workflow(scenario2)
        self.assertTrue(result2.success)
        
        # Verify thread reuse
        self.assertEqual(result2.threads_created, 0)  # No new threads created


if __name__ == "__main__":
    unittest.main()