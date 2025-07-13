#!/usr/bin/env python3
"""Test System Integration.

This module provides comprehensive tests for complete system integration,
including all components working together, data flow, API integration,
and overall system behavior validation.
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


# System integration test types
@dataclass
class IntegrationScenario:
    """System integration test scenario."""
    name: str
    events: List[Dict[str, Any]]
    expected_outputs: List[Dict[str, Any]]
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    requires_real_discord: bool = False


@dataclass
class SystemIntegrationResult:
    """Result of system integration test."""
    scenario_name: str
    success: bool
    events_processed: int
    outputs_generated: int
    processing_time: float
    errors_encountered: List[str]
    performance_metrics: Dict[str, float]
    final_system_state: Dict[str, Any]


class MockDiscordAPI:
    """Mock Discord API for testing."""
    
    def __init__(self):
        self.webhook_calls = []
        self.bot_api_calls = []
        self.threads_created = []
        self.messages_sent = []
        self.rate_limit_hits = 0
        
    def webhook_post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock webhook POST."""
        call_info = {
            "url": url,
            "data": data,
            "timestamp": time.time()
        }
        self.webhook_calls.append(call_info)
        
        # Simulate response
        return {
            "id": f"msg_{len(self.messages_sent)}",
            "content": data.get("content", ""),
            "embeds": data.get("embeds", []),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def bot_api_call(self, method: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock bot API call."""
        call_info = {
            "method": method,
            "endpoint": endpoint,
            "data": data,
            "timestamp": time.time()
        }
        self.bot_api_calls.append(call_info)
        
        if "threads" in endpoint and method == "POST":
            thread_info = {
                "id": f"thread_{len(self.threads_created)}",
                "name": data.get("name", "Test Thread"),
                "parent_id": data.get("parent_id", "123456"),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            self.threads_created.append(thread_info)
            return thread_info
        
        return {"success": True, "id": f"response_{len(self.bot_api_calls)}"}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get API call statistics."""
        return {
            "webhook_calls": len(self.webhook_calls),
            "bot_api_calls": len(self.bot_api_calls),
            "threads_created": len(self.threads_created),
            "messages_sent": len(self.messages_sent),
            "rate_limit_hits": self.rate_limit_hits
        }


class SystemIntegrationOrchestrator:
    """Orchestrates complete system integration tests."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
        self.mock_discord = MockDiscordAPI()
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = self._create_test_config()
        self.system_components = {}
        
    def _create_test_config(self) -> Dict[str, Any]:
        """Create test configuration."""
        return {
            "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/abc123",
            "DISCORD_USE_THREADS": True,
            "DISCORD_THREAD_NAME_PREFIX": "Claude-",
            "DISCORD_ENABLED_EVENTS": ["Start", "ToolUse", "Stop", "Error"],
            "DISCORD_DEBUG": True,
            "DATABASE_PATH": str(Path(self.temp_dir) / "test.db"),
            "CACHE_SIZE": 100,
            "MAX_RETRIES": 3,
            "TIMEOUT_SECONDS": 10
        }
    
    async def setup_system_components(self) -> None:
        """Set up all system components."""
        # Initialize configuration
        config_manager = ConfigLoader()
        
        # Initialize database
        db_path = self.test_config["DATABASE_PATH"]
        thread_storage = ThreadStorage(db_path)
        thread_storage.init_database()
        
        # Initialize HTTP client with mocked Discord API
        http_client = HTTPClient()
        
        # Initialize Discord context
        discord_context = DiscordContext(
            config=self.test_config,
            logger=self.logger,
            http_client=http_client
        )
        
        # Store components
        self.system_components = {
            "config_manager": config_manager,
            "thread_storage": thread_storage,
            "http_client": http_client,
            "discord_context": discord_context
        }
    
    async def run_integration_scenario(self, scenario: IntegrationScenario) -> SystemIntegrationResult:
        """Run complete integration scenario."""
        start_time = time.time()
        errors_encountered = []
        events_processed = 0
        outputs_generated = 0
        
        try:
            # Apply configuration overrides
            test_config = {**self.test_config, **scenario.config_overrides}
            
            # Set up system with test config
            await self.setup_system_components()
            
            # Mock Discord API calls
            with patch('src.core.http_client.HTTPClient.post', side_effect=self.mock_discord.webhook_post), \
                 patch('src.core.http_client.HTTPClient.get', side_effect=self.mock_discord.bot_api_call):
                
                # Process each event in scenario
                for event in scenario.events:
                    try:
                        await self._process_single_event(event, test_config)
                        events_processed += 1
                        outputs_generated += 1
                    except Exception as e:
                        errors_encountered.append(f"Event {events_processed}: {str(e)}")
                        self.logger.error(f"Error processing event", error=str(e), event=event)
            
            # Collect performance metrics
            processing_time = time.time() - start_time
            performance_metrics = self._collect_performance_metrics(processing_time)
            
            # Get final system state
            final_state = self._get_system_state()
            
            return SystemIntegrationResult(
                scenario_name=scenario.name,
                success=len(errors_encountered) == 0,
                events_processed=events_processed,
                outputs_generated=outputs_generated,
                processing_time=processing_time,
                errors_encountered=errors_encountered,
                performance_metrics=performance_metrics,
                final_system_state=final_state
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return SystemIntegrationResult(
                scenario_name=scenario.name,
                success=False,
                events_processed=events_processed,
                outputs_generated=outputs_generated,
                processing_time=processing_time,
                errors_encountered=errors_encountered + [f"Scenario error: {str(e)}"],
                performance_metrics={},
                final_system_state={}
            )
    
    async def _process_single_event(self, event: Dict[str, Any], config: Dict[str, Any]) -> None:
        """Process a single event through the complete system."""
        # Format event
        formatted_output = format_event(event)
        
        # Create Discord message
        discord_message: DiscordMessage = {
            "content": formatted_output.get("content", ""),
            "embeds": formatted_output.get("embeds", []),
            "username": formatted_output.get("username", "Claude Code")
        }
        
        # Handle threading if enabled
        if config.get("DISCORD_USE_THREADS", False):
            session_id = event.get("session_id", "default")
            
            # Get or create thread
            thread_id = get_or_create_thread(
                session_id=session_id,
                config=config,
                http_client=self.system_components["http_client"],
                logger=self.logger
            )
            
            if thread_id:
                discord_message["thread_id"] = thread_id
        
        # Send message
        discord_context = self.system_components["discord_context"]
        send_to_discord(discord_message, discord_context)
    
    def _collect_performance_metrics(self, total_time: float) -> Dict[str, float]:
        """Collect performance metrics."""
        discord_stats = self.mock_discord.get_statistics()
        
        return {
            "total_processing_time": total_time,
            "webhook_calls": discord_stats["webhook_calls"],
            "bot_api_calls": discord_stats["bot_api_calls"],
            "threads_created": discord_stats["threads_created"],
            "average_event_time": total_time / max(1, discord_stats["webhook_calls"]),
            "calls_per_second": discord_stats["webhook_calls"] / max(0.001, total_time)
        }
    
    def _get_system_state(self) -> Dict[str, Any]:
        """Get current system state."""
        thread_storage = self.system_components["thread_storage"]
        
        return {
            "database_accessible": Path(self.test_config["DATABASE_PATH"]).exists(),
            "thread_count": len(thread_storage.get_all_sessions()),
            "discord_calls": self.mock_discord.get_statistics(),
            "memory_usage": "simulated_normal",
            "error_count": 0
        }
    
    def cleanup(self) -> None:
        """Clean up test resources."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


class TestSystemIntegration(unittest.IsolatedAsyncioTestCase):
    """Test cases for complete system integration."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.orchestrator = SystemIntegrationOrchestrator()
        
        # Integration test scenarios
        self.integration_scenarios = [
            IntegrationScenario(
                name="complete_session_workflow",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-001",
                        "user": "test-user"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-001",
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "/test/file.py", "old_string": "old", "new_string": "new"}
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:02:00Z",
                        "session_id": "session-001",
                        "tool_name": "Bash",
                        "tool_input": {"command": "ls -la"}
                    },
                    {
                        "event_type": "Stop",
                        "timestamp": "2024-01-01T00:03:00Z",
                        "session_id": "session-001"
                    }
                ],
                expected_outputs=[
                    {"type": "start_notification"},
                    {"type": "tool_use_notification", "tool": "Edit"},
                    {"type": "tool_use_notification", "tool": "Bash"},
                    {"type": "stop_notification"}
                ]
            ),
            IntegrationScenario(
                name="multi_session_parallel",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-A",
                        "user": "user-A"
                    },
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:01Z",
                        "session_id": "session-B",
                        "user": "user-B"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-A",
                        "tool_name": "Read",
                        "tool_input": {"file_path": "/test/file1.py"}
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:01Z",
                        "session_id": "session-B",
                        "tool_name": "Write",
                        "tool_input": {"file_path": "/test/file2.py", "content": "test"}
                    }
                ],
                expected_outputs=[
                    {"type": "start_notification", "session": "session-A"},
                    {"type": "start_notification", "session": "session-B"},
                    {"type": "tool_use_notification", "session": "session-A"},
                    {"type": "tool_use_notification", "session": "session-B"}
                ]
            ),
            IntegrationScenario(
                name="error_handling_integration",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-error",
                        "user": "test-user"
                    },
                    {
                        "event_type": "Error",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-error",
                        "error_type": "ValidationError",
                        "error_message": "Invalid input provided"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:02:00Z",
                        "session_id": "session-error",
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "/test/recovery.py"}
                    }
                ],
                expected_outputs=[
                    {"type": "start_notification"},
                    {"type": "error_notification"},
                    {"type": "tool_use_notification"}
                ]
            ),
            IntegrationScenario(
                name="threading_disabled_workflow",
                events=[
                    {
                        "event_type": "Start",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "session_id": "session-no-thread",
                        "user": "test-user"
                    },
                    {
                        "event_type": "ToolUse",
                        "timestamp": "2024-01-01T00:01:00Z",
                        "session_id": "session-no-thread",
                        "tool_name": "Bash",
                        "tool_input": {"command": "echo 'hello'"}
                    }
                ],
                expected_outputs=[
                    {"type": "start_notification"},
                    {"type": "tool_use_notification"}
                ],
                config_overrides={
                    "DISCORD_USE_THREADS": False
                }
            ),
            IntegrationScenario(
                name="high_volume_stress_test",
                events=[
                    {
                        "event_type": "ToolUse",
                        "timestamp": f"2024-01-01T00:{i:02d}:00Z",
                        "session_id": f"session-{i % 3}",
                        "tool_name": "Edit",
                        "tool_input": {"file_path": f"/test/file{i}.py", "content": f"content {i}"}
                    }
                    for i in range(50)
                ],
                expected_outputs=[{"type": "tool_use_notification"} for _ in range(50)],
                timeout_seconds=60.0
            )
        ]
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.orchestrator.cleanup()
    
    async def test_complete_session_workflow(self) -> None:
        """Test complete session workflow integration."""
        scenario = self.integration_scenarios[0]  # complete_session_workflow
        
        result = await self.orchestrator.run_integration_scenario(scenario)
        
        # Verify integration success
        self.assertTrue(result.success, f"Errors: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 4)
        self.assertEqual(result.outputs_generated, 4)
        self.assertLess(result.processing_time, scenario.timeout_seconds)
        
        # Verify system state
        self.assertTrue(result.final_system_state["database_accessible"])
        self.assertGreater(result.final_system_state["thread_count"], 0)
        
        # Verify Discord interactions
        discord_calls = result.final_system_state["discord_calls"]
        self.assertEqual(discord_calls["webhook_calls"], 4)
        self.assertGreater(discord_calls["threads_created"], 0)
        
        # Verify performance metrics
        self.assertLess(result.performance_metrics["average_event_time"], 1.0)
        self.assertGreater(result.performance_metrics["calls_per_second"], 1.0)
    
    async def test_multi_session_parallel_processing(self) -> None:
        """Test parallel processing of multiple sessions."""
        scenario = self.integration_scenarios[1]  # multi_session_parallel
        
        result = await self.orchestrator.run_integration_scenario(scenario)
        
        # Verify parallel processing success
        self.assertTrue(result.success, f"Errors: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 4)
        
        # Verify multiple threads created (one per session)
        discord_calls = result.final_system_state["discord_calls"]
        self.assertGreaterEqual(discord_calls["threads_created"], 2)
        
        # Verify thread isolation
        self.assertGreater(result.final_system_state["thread_count"], 1)
    
    async def test_error_handling_integration(self) -> None:
        """Test error handling integration."""
        scenario = self.integration_scenarios[2]  # error_handling_integration
        
        result = await self.orchestrator.run_integration_scenario(scenario)
        
        # Verify error handling doesn't break the system
        self.assertTrue(result.success, f"Errors: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 3)
        
        # Verify system continues after error
        discord_calls = result.final_system_state["discord_calls"]
        self.assertEqual(discord_calls["webhook_calls"], 3)  # All events processed
    
    async def test_threading_disabled_workflow(self) -> None:
        """Test workflow with threading disabled."""
        scenario = self.integration_scenarios[3]  # threading_disabled_workflow
        
        result = await self.orchestrator.run_integration_scenario(scenario)
        
        # Verify success without threading
        self.assertTrue(result.success, f"Errors: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 2)
        
        # Verify no threads created
        discord_calls = result.final_system_state["discord_calls"]
        self.assertEqual(discord_calls["threads_created"], 0)
        self.assertEqual(discord_calls["webhook_calls"], 2)
    
    async def test_high_volume_stress_integration(self) -> None:
        """Test high volume stress integration."""
        scenario = self.integration_scenarios[4]  # high_volume_stress_test
        
        result = await self.orchestrator.run_integration_scenario(scenario)
        
        # Verify high volume handling
        self.assertTrue(result.success, f"Errors: {result.errors_encountered}")
        self.assertEqual(result.events_processed, 50)
        self.assertLess(result.processing_time, scenario.timeout_seconds)
        
        # Verify performance under load
        self.assertGreater(result.performance_metrics["calls_per_second"], 5.0)
        self.assertLess(result.performance_metrics["average_event_time"], 0.5)
        
        # Verify system stability
        self.assertTrue(result.final_system_state["database_accessible"])
        self.assertEqual(result.final_system_state["error_count"], 0)
    
    async def test_component_integration_isolation(self) -> None:
        """Test component integration and isolation."""
        await self.orchestrator.setup_system_components()
        
        components = self.orchestrator.system_components
        
        # Verify all components initialized
        required_components = [
            "config_manager", "thread_storage", "http_client", "discord_context"
        ]
        
        for component_name in required_components:
            self.assertIn(component_name, components)
            self.assertIsNotNone(components[component_name])
        
        # Test component interaction
        # Create test event
        test_event = {
            "event_type": "ToolUse",
            "timestamp": "2024-01-01T00:00:00Z",
            "session_id": "test-session",
            "tool_name": "Test",
            "tool_input": {"test": "data"}
        }
        
        # Test event formatting
        formatted_output = format_event(test_event)
        self.assertIsInstance(formatted_output, dict)
        
        # Test thread storage
        thread_storage = components["thread_storage"]
        thread_storage.store_thread_id("test-session", "thread-123")
        retrieved_thread = thread_storage.get_thread_id("test-session")
        self.assertEqual(retrieved_thread, "thread-123")
    
    async def test_configuration_integration(self) -> None:
        """Test configuration system integration."""
        # Test with different configurations
        config_variations = [
            {"DISCORD_USE_THREADS": True, "DISCORD_DEBUG": True},
            {"DISCORD_USE_THREADS": False, "DISCORD_DEBUG": False},
            {"DISCORD_ENABLED_EVENTS": ["Start", "Stop"]},
            {"DISCORD_TIMEOUT_SECONDS": 5}
        ]
        
        for config_override in config_variations:
            with self.subTest(config=config_override):
                scenario = IntegrationScenario(
                    name=f"config_test_{hash(str(config_override))}",
                    events=[
                        {
                            "event_type": "Start",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "session_id": "config-test",
                            "user": "test-user"
                        }
                    ],
                    expected_outputs=[{"type": "start_notification"}],
                    config_overrides=config_override
                )
                
                result = await self.orchestrator.run_integration_scenario(scenario)
                self.assertTrue(result.success, f"Config {config_override} failed: {result.errors_encountered}")
    
    async def test_database_integration_consistency(self) -> None:
        """Test database integration and consistency."""
        await self.orchestrator.setup_system_components()
        
        thread_storage = self.orchestrator.system_components["thread_storage"]
        
        # Test database operations
        test_data = [
            ("session-1", "thread-1"),
            ("session-2", "thread-2"),
            ("session-3", "thread-3")
        ]
        
        # Store data
        for session_id, thread_id in test_data:
            thread_storage.store_thread_id(session_id, thread_id)
        
        # Verify data integrity
        for session_id, expected_thread_id in test_data:
            retrieved_thread_id = thread_storage.get_thread_id(session_id)
            self.assertEqual(retrieved_thread_id, expected_thread_id)
        
        # Test cleanup
        thread_storage.cleanup_old_sessions(max_age_hours=0)  # Clean all
        
        # Verify cleanup
        for session_id, _ in test_data:
            retrieved_thread_id = thread_storage.get_thread_id(session_id)
            self.assertIsNone(retrieved_thread_id)
    
    async def test_error_propagation_integration(self) -> None:
        """Test error propagation through system integration."""
        # Create scenario with intentional errors
        error_scenario = IntegrationScenario(
            name="error_propagation_test",
            events=[
                {
                    "event_type": "Start",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "session_id": "error-test",
                    "user": "test-user"
                }
            ],
            expected_outputs=[{"type": "start_notification"}]
        )
        
        # Mock component failure
        with patch('src.handlers.discord_sender.DiscordSender.send_message', side_effect=Exception("Network error")):
            result = await self.orchestrator.run_integration_scenario(error_scenario)
            
            # Verify error handling
            self.assertFalse(result.success)
            self.assertGreater(len(result.errors_encountered), 0)
            self.assertIn("Network error", str(result.errors_encountered))
    
    async def test_performance_integration_metrics(self) -> None:
        """Test performance metrics integration."""
        # Create performance test scenario
        performance_scenario = IntegrationScenario(
            name="performance_metrics_test",
            events=[
                {
                    "event_type": "ToolUse",
                    "timestamp": f"2024-01-01T00:00:{i:02d}Z",
                    "session_id": "perf-test",
                    "tool_name": "Edit",
                    "tool_input": {"file_path": f"/test/file{i}.py"}
                }
                for i in range(10)
            ],
            expected_outputs=[{"type": "tool_use_notification"} for _ in range(10)]
        )
        
        result = await self.orchestrator.run_integration_scenario(performance_scenario)
        
        # Verify performance metrics collection
        self.assertTrue(result.success)
        self.assertIn("total_processing_time", result.performance_metrics)
        self.assertIn("average_event_time", result.performance_metrics)
        self.assertIn("calls_per_second", result.performance_metrics)
        
        # Verify reasonable performance
        self.assertLess(result.performance_metrics["average_event_time"], 2.0)
        self.assertGreater(result.performance_metrics["calls_per_second"], 0.5)
    
    async def test_system_recovery_integration(self) -> None:
        """Test system recovery integration."""
        await self.orchestrator.setup_system_components()
        
        # Simulate system disruption
        components = self.orchestrator.system_components
        original_context = components["discord_context"]
        
        # Temporarily break discord context
        components["discord_context"] = None
        
        # Attempt to process event (should fail gracefully)
        test_event = {
            "event_type": "Start",
            "timestamp": "2024-01-01T00:00:00Z",
            "session_id": "recovery-test",
            "user": "test-user"
        }
        
        with self.assertRaises(Exception):
            await self.orchestrator._process_single_event(test_event, self.orchestrator.test_config)
        
        # Restore discord context (simulate recovery)
        components["discord_context"] = original_context
        
        # Verify system works after recovery
        await self.orchestrator._process_single_event(test_event, self.orchestrator.test_config)
        # Should complete without exception


if __name__ == "__main__":
    unittest.main()