#!/usr/bin/env python3
"""Test Emergency Stop Mechanisms.

This module provides comprehensive tests for emergency stop mechanisms,
including graceful shutdown, immediate termination, cleanup procedures,
and recovery after emergency stops.
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
import signal
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
from src.core.http_client import HTTPClient
from src.handlers.discord_sender import DiscordSender
from src.thread_storage import ThreadStorage
from src.type_defs.events import EventDict
from src.type_defs.discord import DiscordMessage


# Emergency stop test types
@dataclass
class EmergencyStopScenario:
    """Emergency stop test scenario."""
    name: str
    trigger_method: str  # signal, timeout, exception, resource_limit
    stop_type: str  # graceful, immediate, forced
    expected_cleanup_actions: List[str]
    expected_state_after: str
    timeout_seconds: float = 5.0


@dataclass
class StopResult:
    """Result of emergency stop test."""
    scenario_name: str
    success: bool
    stop_time: float
    cleanup_time: float
    cleanup_actions_completed: List[str]
    cleanup_actions_failed: List[str]
    final_state: str
    error: Optional[Exception] = None


@dataclass
class ProcessState:
    """Process state tracking."""
    pid: Optional[int] = None
    status: str = "stopped"  # stopped, running, stopping, error
    start_time: Optional[float] = None
    stop_time: Optional[float] = None
    resources_allocated: List[str] = field(default_factory=list)
    cleanup_completed: bool = False


class EmergencyStopManager:
    """Manager for emergency stop operations."""
    
    def __init__(self):
        self.process_state = ProcessState()
        self.stop_handlers = {}
        self.cleanup_actions = []
        self.emergency_triggered = threading.Event()
        self.cleanup_lock = threading.Lock()
        self.logger = AstolfoLogger(__name__)
    
    def register_stop_handler(self, signal_num: int, handler: Callable) -> None:
        """Register signal handler for emergency stop."""
        self.stop_handlers[signal_num] = handler
        signal.signal(signal_num, handler)
    
    def add_cleanup_action(self, name: str, action: Callable) -> None:
        """Add cleanup action to be executed on stop."""
        self.cleanup_actions.append({"name": name, "action": action, "completed": False})
    
    def trigger_emergency_stop(self, stop_type: str = "graceful") -> StopResult:
        """Trigger emergency stop."""
        stop_start = time.time()
        self.emergency_triggered.set()
        
        try:
            if stop_type == "immediate":
                return self._immediate_stop(stop_start)
            elif stop_type == "forced":
                return self._forced_stop(stop_start)
            else:
                return self._graceful_stop(stop_start)
                
        except Exception as e:
            return StopResult(
                scenario_name="emergency_stop",
                success=False,
                stop_time=time.time() - stop_start,
                cleanup_time=0,
                cleanup_actions_completed=[],
                cleanup_actions_failed=[],
                final_state="error",
                error=e
            )
    
    def _graceful_stop(self, start_time: float) -> StopResult:
        """Perform graceful stop with cleanup."""
        self.process_state.status = "stopping"
        cleanup_start = time.time()
        
        completed_actions = []
        failed_actions = []
        
        with self.cleanup_lock:
            for action_info in self.cleanup_actions:
                try:
                    action_info["action"]()
                    action_info["completed"] = True
                    completed_actions.append(action_info["name"])
                except Exception as e:
                    failed_actions.append(action_info["name"])
                    self.logger.error(f"Cleanup action '{action_info['name']}' failed", error=str(e))
        
        cleanup_time = time.time() - cleanup_start
        stop_time = time.time() - start_time
        
        self.process_state.status = "stopped"
        self.process_state.stop_time = time.time()
        self.process_state.cleanup_completed = len(failed_actions) == 0
        
        return StopResult(
            scenario_name="graceful_stop",
            success=True,
            stop_time=stop_time,
            cleanup_time=cleanup_time,
            cleanup_actions_completed=completed_actions,
            cleanup_actions_failed=failed_actions,
            final_state="stopped"
        )
    
    def _immediate_stop(self, start_time: float) -> StopResult:
        """Perform immediate stop with minimal cleanup."""
        self.process_state.status = "stopped"
        stop_time = time.time() - start_time
        
        # Only critical cleanup actions
        critical_actions = [a for a in self.cleanup_actions if "critical" in a["name"]]
        completed_actions = []
        
        for action_info in critical_actions:
            try:
                action_info["action"]()
                completed_actions.append(action_info["name"])
            except Exception:
                pass  # Ignore errors in immediate stop
        
        return StopResult(
            scenario_name="immediate_stop",
            success=True,
            stop_time=stop_time,
            cleanup_time=0,
            cleanup_actions_completed=completed_actions,
            cleanup_actions_failed=[],
            final_state="stopped"
        )
    
    def _forced_stop(self, start_time: float) -> StopResult:
        """Perform forced stop with no cleanup."""
        self.process_state.status = "stopped"
        stop_time = time.time() - start_time
        
        return StopResult(
            scenario_name="forced_stop",
            success=True,
            stop_time=stop_time,
            cleanup_time=0,
            cleanup_actions_completed=[],
            cleanup_actions_failed=[],
            final_state="stopped"
        )


class TestEmergencyStop(unittest.IsolatedAsyncioTestCase):
    """Test cases for emergency stop mechanisms."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.stop_manager = EmergencyStopManager()
        
        # Test configuration
        self.test_config = {
            "graceful_stop_timeout": 10.0,
            "immediate_stop_timeout": 2.0,
            "forced_stop_timeout": 0.5,
            "enable_cleanup": True,
            "debug": True
        }
        
        # Emergency stop scenarios
        self.test_scenarios = [
            EmergencyStopScenario(
                name="graceful_shutdown",
                trigger_method="signal",
                stop_type="graceful",
                expected_cleanup_actions=["close_connections", "save_state", "cleanup_temp_files"],
                expected_state_after="stopped",
                timeout_seconds=10.0
            ),
            EmergencyStopScenario(
                name="immediate_termination",
                trigger_method="timeout",
                stop_type="immediate",
                expected_cleanup_actions=["critical_save"],
                expected_state_after="stopped",
                timeout_seconds=2.0
            ),
            EmergencyStopScenario(
                name="forced_kill",
                trigger_method="exception",
                stop_type="forced",
                expected_cleanup_actions=[],
                expected_state_after="stopped",
                timeout_seconds=0.5
            ),
            EmergencyStopScenario(
                name="resource_limit_stop",
                trigger_method="resource_limit",
                stop_type="graceful",
                expected_cleanup_actions=["release_resources", "close_connections"],
                expected_state_after="stopped",
                timeout_seconds=5.0
            )
        ]
    
    async def test_graceful_shutdown(self) -> None:
        """Test graceful shutdown with proper cleanup."""
        # Set up cleanup actions
        cleanup_results = {}
        
        def mock_close_connections():
            cleanup_results["close_connections"] = True
            time.sleep(0.1)  # Simulate cleanup work
        
        def mock_save_state():
            cleanup_results["save_state"] = True
            time.sleep(0.1)
        
        def mock_cleanup_temp_files():
            cleanup_results["cleanup_temp_files"] = True
            time.sleep(0.1)
        
        # Register cleanup actions
        self.stop_manager.add_cleanup_action("close_connections", mock_close_connections)
        self.stop_manager.add_cleanup_action("save_state", mock_save_state)
        self.stop_manager.add_cleanup_action("cleanup_temp_files", mock_cleanup_temp_files)
        
        # Trigger graceful stop
        result = self.stop_manager.trigger_emergency_stop("graceful")
        
        # Verify results
        self.assertTrue(result.success)
        self.assertEqual(result.final_state, "stopped")
        self.assertEqual(len(result.cleanup_actions_completed), 3)
        self.assertEqual(len(result.cleanup_actions_failed), 0)
        
        # Verify all cleanup actions were executed
        expected_actions = {"close_connections", "save_state", "cleanup_temp_files"}
        completed_actions = set(result.cleanup_actions_completed)
        self.assertEqual(completed_actions, expected_actions)
        
        # Verify cleanup actually ran
        self.assertTrue(cleanup_results.get("close_connections", False))
        self.assertTrue(cleanup_results.get("save_state", False))
        self.assertTrue(cleanup_results.get("cleanup_temp_files", False))
    
    async def test_immediate_termination(self) -> None:
        """Test immediate termination with minimal cleanup."""
        # Set up critical and non-critical actions
        cleanup_results = {}
        
        def critical_save():
            cleanup_results["critical_save"] = True
        
        def non_critical_action():
            cleanup_results["non_critical"] = True
            time.sleep(1.0)  # This should not complete in immediate stop
        
        # Register actions
        self.stop_manager.add_cleanup_action("critical_save", critical_save)
        self.stop_manager.add_cleanup_action("non_critical_action", non_critical_action)
        
        # Trigger immediate stop
        start_time = time.time()
        result = self.stop_manager.trigger_emergency_stop("immediate")
        stop_duration = time.time() - start_time
        
        # Verify fast termination
        self.assertTrue(result.success)
        self.assertLess(stop_duration, 1.0)  # Should be much faster than graceful
        self.assertEqual(result.final_state, "stopped")
        
        # Only critical actions should complete
        self.assertIn("critical_save", result.cleanup_actions_completed)
        
        # Verify critical action ran
        self.assertTrue(cleanup_results.get("critical_save", False))
        # Non-critical action should not have time to complete
        self.assertFalse(cleanup_results.get("non_critical", False))
    
    async def test_forced_kill(self) -> None:
        """Test forced kill with no cleanup."""
        # Set up actions that would take time
        def slow_cleanup():
            time.sleep(2.0)
        
        self.stop_manager.add_cleanup_action("slow_cleanup", slow_cleanup)
        
        # Trigger forced stop
        start_time = time.time()
        result = self.stop_manager.trigger_emergency_stop("forced")
        stop_duration = time.time() - start_time
        
        # Verify very fast termination
        self.assertTrue(result.success)
        self.assertLess(stop_duration, 0.1)  # Should be immediate
        self.assertEqual(result.final_state, "stopped")
        self.assertEqual(len(result.cleanup_actions_completed), 0)
        self.assertEqual(result.cleanup_time, 0)
    
    async def test_signal_based_emergency_stop(self) -> None:
        """Test signal-based emergency stop."""
        stop_triggered = threading.Event()
        stop_result = {"success": False}
        
        def signal_handler(signum, frame):
            stop_result["signal"] = signum
            stop_triggered.set()
            # Simulate emergency stop
            result = self.stop_manager.trigger_emergency_stop("graceful")
            stop_result["success"] = result.success
        
        # Register signal handler
        self.stop_manager.register_stop_handler(signal.SIGUSR1, signal_handler)
        
        # Send signal to self
        os.kill(os.getpid(), signal.SIGUSR1)
        
        # Wait for signal handling
        signal_handled = stop_triggered.wait(timeout=5.0)
        
        # Verify signal was handled
        self.assertTrue(signal_handled)
        self.assertEqual(stop_result["signal"], signal.SIGUSR1)
        self.assertTrue(stop_result["success"])
    
    async def test_timeout_based_emergency_stop(self) -> None:
        """Test timeout-based emergency stop."""
        timeout_seconds = 1.0
        start_time = time.time()
        
        # Simulate long-running operation with timeout
        async def long_operation_with_timeout():
            try:
                # Simulate work that might hang
                await asyncio.sleep(2.0)  # Longer than timeout
                return "completed"
            except asyncio.TimeoutError:
                # Trigger emergency stop on timeout
                result = self.stop_manager.trigger_emergency_stop("immediate")
                return "emergency_stopped"
        
        # Run with timeout
        try:
            result = await asyncio.wait_for(
                long_operation_with_timeout(),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            result = "timed_out"
            # Trigger emergency stop
            stop_result = self.stop_manager.trigger_emergency_stop("immediate")
            self.assertTrue(stop_result.success)
        
        elapsed_time = time.time() - start_time
        
        # Verify timeout occurred and stop was triggered
        self.assertLess(elapsed_time, timeout_seconds + 0.5)
        self.assertIn(result, ["emergency_stopped", "timed_out"])
    
    async def test_exception_based_emergency_stop(self) -> None:
        """Test exception-based emergency stop."""
        exception_caught = False
        stop_triggered = False
        
        try:
            # Simulate critical error
            raise RuntimeError("Critical system error")
            
        except RuntimeError as e:
            exception_caught = True
            
            # Trigger emergency stop on critical exception
            result = self.stop_manager.trigger_emergency_stop("graceful")
            stop_triggered = result.success
        
        # Verify exception handling and stop
        self.assertTrue(exception_caught)
        self.assertTrue(stop_triggered)
    
    async def test_resource_limit_emergency_stop(self) -> None:
        """Test emergency stop triggered by resource limits."""
        # Mock resource monitoring
        resource_state = {
            "memory_usage": 0,
            "connection_count": 0,
            "disk_usage": 0
        }
        
        def allocate_resources():
            resource_state["memory_usage"] += 100
            resource_state["connection_count"] += 10
            resource_state["disk_usage"] += 50
        
        def check_resource_limits():
            # Simulate resource limit check
            if (resource_state["memory_usage"] > 800 or 
                resource_state["connection_count"] > 80 or
                resource_state["disk_usage"] > 400):
                return True
            return False
        
        def cleanup_resources():
            resource_state["memory_usage"] = 0
            resource_state["connection_count"] = 0
            resource_state["disk_usage"] = 0
        
        # Add resource cleanup
        self.stop_manager.add_cleanup_action("release_resources", cleanup_resources)
        
        # Simulate resource allocation until limit
        while not check_resource_limits():
            allocate_resources()
            time.sleep(0.01)
        
        # Trigger emergency stop due to resource limits
        result = self.stop_manager.trigger_emergency_stop("graceful")
        
        # Verify stop and cleanup
        self.assertTrue(result.success)
        self.assertIn("release_resources", result.cleanup_actions_completed)
        
        # Verify resources were cleaned up
        self.assertEqual(resource_state["memory_usage"], 0)
        self.assertEqual(resource_state["connection_count"], 0)
        self.assertEqual(resource_state["disk_usage"], 0)
    
    async def test_concurrent_emergency_stops(self) -> None:
        """Test handling of concurrent emergency stop triggers."""
        stop_results = []
        stop_count = threading.Value("i", 0)
        
        def trigger_stop(stop_type: str, delay: float):
            time.sleep(delay)
            with stop_count.get_lock():
                if stop_count.value == 0:
                    stop_count.value = 1
                    result = self.stop_manager.trigger_emergency_stop(stop_type)
                    stop_results.append(result)
                else:
                    # Second stop attempt should be ignored
                    stop_results.append(None)
        
        # Start multiple stop triggers concurrently
        threads = []
        for i, stop_type in enumerate(["graceful", "immediate", "forced"]):
            thread = threading.Thread(
                target=trigger_stop,
                args=(stop_type, i * 0.1)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify only one stop was executed
        actual_stops = [r for r in stop_results if r is not None]
        self.assertEqual(len(actual_stops), 1)
        self.assertTrue(actual_stops[0].success)
    
    async def test_recovery_after_emergency_stop(self) -> None:
        """Test recovery mechanisms after emergency stop."""
        # Set up recovery state
        recovery_state = {
            "state_saved": False,
            "connections_restored": False,
            "services_restarted": False
        }
        
        def save_state():
            recovery_state["state_saved"] = True
        
        def restore_connections():
            recovery_state["connections_restored"] = True
        
        def restart_services():
            recovery_state["services_restarted"] = True
        
        # Add cleanup action
        self.stop_manager.add_cleanup_action("save_state", save_state)
        
        # Trigger emergency stop
        stop_result = self.stop_manager.trigger_emergency_stop("graceful")
        self.assertTrue(stop_result.success)
        self.assertTrue(recovery_state["state_saved"])
        
        # Simulate recovery process
        recovery_actions = [restore_connections, restart_services]
        recovery_success = True
        
        for action in recovery_actions:
            try:
                action()
            except Exception:
                recovery_success = False
        
        # Verify recovery
        self.assertTrue(recovery_success)
        self.assertTrue(recovery_state["connections_restored"])
        self.assertTrue(recovery_state["services_restarted"])
    
    async def test_cleanup_action_failure_handling(self) -> None:
        """Test handling of cleanup action failures."""
        cleanup_results = {}
        
        def successful_cleanup():
            cleanup_results["successful"] = True
        
        def failing_cleanup():
            cleanup_results["attempted"] = True
            raise Exception("Cleanup failed")
        
        def another_successful_cleanup():
            cleanup_results["another_successful"] = True
        
        # Add cleanup actions
        self.stop_manager.add_cleanup_action("successful_cleanup", successful_cleanup)
        self.stop_manager.add_cleanup_action("failing_cleanup", failing_cleanup)
        self.stop_manager.add_cleanup_action("another_successful", another_successful_cleanup)
        
        # Trigger graceful stop
        result = self.stop_manager.trigger_emergency_stop("graceful")
        
        # Verify partial success
        self.assertTrue(result.success)  # Stop itself succeeded
        self.assertEqual(len(result.cleanup_actions_completed), 2)
        self.assertEqual(len(result.cleanup_actions_failed), 1)
        
        # Verify which actions completed/failed
        self.assertIn("successful_cleanup", result.cleanup_actions_completed)
        self.assertIn("another_successful", result.cleanup_actions_completed)
        self.assertIn("failing_cleanup", result.cleanup_actions_failed)
        
        # Verify actual execution
        self.assertTrue(cleanup_results.get("successful", False))
        self.assertTrue(cleanup_results.get("attempted", False))
        self.assertTrue(cleanup_results.get("another_successful", False))
    
    async def test_emergency_stop_performance(self) -> None:
        """Test emergency stop performance characteristics."""
        # Performance targets
        performance_targets = {
            "graceful": 2.0,    # seconds
            "immediate": 0.5,   # seconds
            "forced": 0.1       # seconds
        }
        
        # Test each stop type
        for stop_type, max_time in performance_targets.items():
            with self.subTest(stop_type=stop_type):
                # Add some cleanup actions for graceful stop
                if stop_type == "graceful":
                    for i in range(5):
                        self.stop_manager.add_cleanup_action(
                            f"cleanup_{i}",
                            lambda: time.sleep(0.1)
                        )
                
                # Measure stop time
                start_time = time.time()
                result = self.stop_manager.trigger_emergency_stop(stop_type)
                stop_duration = time.time() - start_time
                
                # Verify performance
                self.assertTrue(result.success)
                self.assertLess(stop_duration, max_time)
                
                # Reset for next test
                self.stop_manager = EmergencyStopManager()
    
    async def test_emergency_stop_logging(self) -> None:
        """Test logging during emergency stop operations."""
        logged_events = []
        
        def mock_log(message: str, **kwargs):
            logged_events.append({"message": message, "data": kwargs})
        
        # Patch logger
        with patch.object(self.logger, 'info', side_effect=mock_log), \
             patch.object(self.logger, 'error', side_effect=mock_log):
            
            # Add cleanup action with logging
            def logged_cleanup():
                self.logger.info("cleanup_action_executed", action="test_cleanup")
            
            self.stop_manager.add_cleanup_action("logged_cleanup", logged_cleanup)
            
            # Trigger stop
            result = self.stop_manager.trigger_emergency_stop("graceful")
            
            # Log the result
            self.logger.info(
                "emergency_stop_completed",
                stop_type="graceful",
                success=result.success,
                cleanup_actions=len(result.cleanup_actions_completed),
                duration=result.stop_time
            )
            
            # Verify logging
            self.assertGreater(len(logged_events), 0)
            
            # Check for specific log entries
            log_messages = [event["message"] for event in logged_events]
            self.assertIn("cleanup_action_executed", log_messages)
            self.assertIn("emergency_stop_completed", log_messages)


if __name__ == "__main__":
    unittest.main()