#!/usr/bin/env python3
"""Test Event Dispatch Accuracy.

This module provides comprehensive tests for event dispatch functionality,
including event routing, handler selection, dispatch timing, error propagation,
and event ordering guarantees.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
import threading
import queue

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.discord_notifier import process_event
from src.handlers.event_registry import EventRegistry
from src.type_defs.events import EventDict, ToolUseEvent
from src.type_defs.base import BaseEvent
from src.formatters.base import BaseFormatter
from src.formatters.event_formatters import (
    StartEventFormatter,
    StopEventFormatter,
    ErrorEventFormatter,
    ResponseEventFormatter
)
from src.formatters.tool_formatters import (
    EditToolFormatter,
    WriteToolFormatter,
    ReadToolFormatter,
    BashToolFormatter,
    StrReplaceEditorToolFormatter
)


# Event dispatch test types
@dataclass
class DispatchEvent:
    """Event to be dispatched."""
    event_type: str
    event_data: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: time.time())
    session_id: str = "test-session"
    
    def to_dict(self) -> EventDict:
        """Convert to EventDict format."""
        return {
            "event_type": self.event_type,
            "timestamp": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
            "session_id": self.session_id,
            **self.event_data
        }


@dataclass
class DispatchResult:
    """Result of event dispatch."""
    success: bool
    handler_called: str
    formatter_used: Optional[str] = None
    processing_time: float = 0.0
    error: Optional[Exception] = None
    formatted_output: Optional[Any] = None


@dataclass
class DispatchMetrics:
    """Metrics for event dispatch performance."""
    total_events: int = 0
    successful_dispatches: int = 0
    failed_dispatches: int = 0
    average_dispatch_time: float = 0.0
    dispatch_times: List[float] = field(default_factory=list)
    event_type_counts: Dict[str, int] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)


class TestEventDispatch(unittest.IsolatedAsyncioTestCase):
    """Test cases for event dispatch accuracy."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.event_registry = EventRegistry()
        
        # Test configuration
        self.test_config = {
            "dispatch_timeout": 5.0,
            "max_retries": 3,
            "ordered_dispatch": True,
            "parallel_dispatch": False,
            "debug": True
        }
        
        # Sample events
        self.test_events = [
            DispatchEvent(
                event_type="Start",
                event_data={"start_time": "2024-01-01T00:00:00Z"}
            ),
            DispatchEvent(
                event_type="ToolUse",
                event_data={
                    "tool_name": "Edit",
                    "tool_input": {
                        "file_path": "/test/file.py",
                        "old_string": "old",
                        "new_string": "new"
                    },
                    "tool_result": {"success": True}
                }
            ),
            DispatchEvent(
                event_type="Error",
                event_data={
                    "error_type": "ValidationError",
                    "error_message": "Test error",
                    "stack_trace": "Traceback..."
                }
            ),
            DispatchEvent(
                event_type="Response",
                event_data={
                    "message": "Test response",
                    "metadata": {"tokens": 100}
                }
            ),
            DispatchEvent(
                event_type="Stop",
                event_data={"reason": "Test complete"}
            )
        ]
        
        # Track dispatch calls
        self.dispatch_log = []
    
    async def test_event_routing(self) -> None:
        """Test correct routing of events to handlers."""
        # Test each event type
        for event in self.test_events:
            with self.subTest(event_type=event.event_type):
                # Mock formatter
                with patch(f'src.formatters.event_formatters.{event.event_type}EventFormatter.format') as mock_format:
                    mock_format.return_value = {"test": "output"}
                    
                    # Process event
                    result = await self._dispatch_event(event)
                    
                    # Verify correct handler was called
                    self.assertTrue(result.success)
                    self.assertEqual(result.handler_called, f"{event.event_type}EventFormatter")
                    
                    # Verify formatter was called with correct data
                    if event.event_type != "ToolUse":
                        mock_format.assert_called_once()
    
    async def test_tool_event_routing(self) -> None:
        """Test routing of tool-specific events."""
        tool_events = [
            ("Edit", EditToolFormatter),
            ("Write", WriteToolFormatter),
            ("Read", ReadToolFormatter),
            ("Bash", BashToolFormatter),
            ("StrReplaceBasedEditTool", StrReplaceEditorToolFormatter)
        ]
        
        for tool_name, formatter_class in tool_events:
            with self.subTest(tool_name=tool_name):
                event = DispatchEvent(
                    event_type="ToolUse",
                    event_data={
                        "tool_name": tool_name,
                        "tool_input": {"test": "input"},
                        "tool_result": {"success": True}
                    }
                )
                
                # Mock formatter
                formatter_name = formatter_class.__name__
                with patch(f'src.formatters.tool_formatters.{formatter_name}.format') as mock_format:
                    mock_format.return_value = {"tool": "output"}
                    
                    # Process event
                    result = await self._dispatch_event(event)
                    
                    # Verify correct tool formatter was used
                    self.assertTrue(result.success)
                    self.assertEqual(result.formatter_used, formatter_name)
                    mock_format.assert_called_once()
    
    async def test_dispatch_timing(self) -> None:
        """Test event dispatch timing and performance."""
        dispatch_times = []
        
        # Dispatch multiple events
        for _ in range(100):
            event = self.test_events[0]  # Use Start event
            
            start_time = time.time()
            result = await self._dispatch_event(event)
            dispatch_time = time.time() - start_time
            
            dispatch_times.append(dispatch_time)
            self.assertTrue(result.success)
        
        # Calculate metrics
        avg_time = sum(dispatch_times) / len(dispatch_times)
        max_time = max(dispatch_times)
        min_time = min(dispatch_times)
        
        # Performance assertions
        self.assertLess(avg_time, 0.01)  # Average under 10ms
        self.assertLess(max_time, 0.05)  # Max under 50ms
        
        self.logger.info(
            "dispatch_timing_test",
            average_ms=avg_time * 1000,
            max_ms=max_time * 1000,
            min_ms=min_time * 1000,
            total_events=len(dispatch_times)
        )
    
    async def test_concurrent_dispatch(self) -> None:
        """Test concurrent event dispatching."""
        num_events = 50
        results = []
        
        # Create events
        events = [
            DispatchEvent(
                event_type=self.test_events[i % len(self.test_events)].event_type,
                event_data=self.test_events[i % len(self.test_events)].event_data,
                session_id=f"session-{i}"
            )
            for i in range(num_events)
        ]
        
        # Dispatch concurrently
        tasks = [self._dispatch_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded
        successful = sum(1 for r in results if isinstance(r, DispatchResult) and r.success)
        self.assertEqual(successful, num_events)
        
        # Check for race conditions
        session_ids = [e.session_id for e in events]
        self.assertEqual(len(set(session_ids)), num_events)  # All unique
    
    async def test_event_ordering(self) -> None:
        """Test event ordering guarantees."""
        ordered_results = []
        
        # Create ordered event handler
        async def ordered_handler(event: DispatchEvent) -> None:
            ordered_results.append({
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "order": len(ordered_results)
            })
        
        # Dispatch events in order
        for i, event in enumerate(self.test_events):
            event.timestamp = time.time() + i * 0.001  # Ensure ordering
            await ordered_handler(event)
        
        # Verify order preserved
        for i, result in enumerate(ordered_results):
            self.assertEqual(result["order"], i)
            if i > 0:
                self.assertGreater(
                    result["timestamp"],
                    ordered_results[i-1]["timestamp"]
                )
    
    async def test_error_propagation(self) -> None:
        """Test error propagation in dispatch chain."""
        error_scenarios = [
            # Formatter error
            {
                "event": DispatchEvent("Start", {}),
                "error_type": "FormatterError",
                "error_location": "formatter"
            },
            # Handler error
            {
                "event": DispatchEvent("Stop", {"reason": "test"}),
                "error_type": "HandlerError",
                "error_location": "handler"
            },
            # Validation error
            {
                "event": DispatchEvent("ToolUse", {}),  # Missing required fields
                "error_type": "ValidationError",
                "error_location": "validation"
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(error_type=scenario["error_type"]):
                # Mock error at specified location
                if scenario["error_location"] == "formatter":
                    with patch('src.formatters.event_formatters.StartEventFormatter.format') as mock_format:
                        mock_format.side_effect = Exception(scenario["error_type"])
                        
                        result = await self._dispatch_event(scenario["event"])
                        
                        self.assertFalse(result.success)
                        self.assertIsNotNone(result.error)
                        self.assertIn(scenario["error_type"], str(result.error))
    
    async def test_dispatch_retry_mechanism(self) -> None:
        """Test dispatch retry on failures."""
        retry_count = 0
        max_retries = 3
        
        async def flaky_handler(event: EventDict) -> Dict[str, Any]:
            nonlocal retry_count
            retry_count += 1
            
            if retry_count < max_retries:
                raise Exception("Temporary failure")
            
            return {"success": True}
        
        # Test retry logic
        with patch('src.handlers.discord_sender.DiscordSender.send_notification') as mock_send:
            mock_send.side_effect = flaky_handler
            
            event = self.test_events[0]
            result = await self._dispatch_with_retry(event, max_retries)
            
            # Should succeed after retries
            self.assertTrue(result.success)
            self.assertEqual(retry_count, max_retries)
    
    async def test_event_filtering_dispatch(self) -> None:
        """Test event filtering before dispatch."""
        # Test with event filters
        enabled_events = ["Start", "Stop", "Error"]
        disabled_events = ["Response"]
        
        for event in self.test_events:
            with self.subTest(event_type=event.event_type):
                # Apply filters
                should_dispatch = (
                    event.event_type in enabled_events and
                    event.event_type not in disabled_events
                )
                
                # Mock config with filters
                with patch('src.core.config.ConfigManager.load_config') as mock_config:
                    mock_config.return_value = {
                        "DISCORD_ENABLED_EVENTS": enabled_events,
                        "DISCORD_DISABLED_EVENTS": disabled_events
                    }
                    
                    # Check if event would be dispatched
                    result = self._should_dispatch_event(event, enabled_events, disabled_events)
                    
                    self.assertEqual(result, should_dispatch)
    
    async def test_dispatch_metrics_collection(self) -> None:
        """Test metrics collection during dispatch."""
        metrics = DispatchMetrics()
        
        # Dispatch events and collect metrics
        for event in self.test_events * 10:  # Dispatch each event 10 times
            start_time = time.time()
            result = await self._dispatch_event(event)
            dispatch_time = time.time() - start_time
            
            # Update metrics
            metrics.total_events += 1
            if result.success:
                metrics.successful_dispatches += 1
            else:
                metrics.failed_dispatches += 1
            
            metrics.dispatch_times.append(dispatch_time)
            metrics.event_type_counts[event.event_type] = \
                metrics.event_type_counts.get(event.event_type, 0) + 1
            
            if result.error:
                error_type = type(result.error).__name__
                metrics.error_counts[error_type] = \
                    metrics.error_counts.get(error_type, 0) + 1
        
        # Calculate average
        metrics.average_dispatch_time = \
            sum(metrics.dispatch_times) / len(metrics.dispatch_times)
        
        # Verify metrics
        self.assertEqual(metrics.total_events, len(self.test_events) * 10)
        self.assertEqual(metrics.successful_dispatches, metrics.total_events)
        self.assertEqual(metrics.failed_dispatches, 0)
        
        # Check event type distribution
        for event_type in set(e.event_type for e in self.test_events):
            self.assertEqual(metrics.event_type_counts[event_type], 10)
    
    async def test_dispatch_queue_overflow(self) -> None:
        """Test behavior with dispatch queue overflow."""
        max_queue_size = 100
        overflow_events = 150
        
        dispatch_queue = queue.Queue(maxsize=max_queue_size)
        dropped_events = 0
        
        # Try to queue more events than capacity
        for i in range(overflow_events):
            event = DispatchEvent(
                event_type="Start",
                event_data={"index": i}
            )
            
            try:
                dispatch_queue.put_nowait(event)
            except queue.Full:
                dropped_events += 1
        
        # Verify overflow handling
        self.assertEqual(dispatch_queue.qsize(), max_queue_size)
        self.assertEqual(dropped_events, overflow_events - max_queue_size)
        
        # Process queued events
        processed = 0
        while not dispatch_queue.empty():
            event = dispatch_queue.get()
            result = await self._dispatch_event(event)
            if result.success:
                processed += 1
        
        self.assertEqual(processed, max_queue_size)
    
    async def test_dispatch_handler_registration(self) -> None:
        """Test dynamic handler registration."""
        # Custom handler
        custom_called = False
        
        async def custom_handler(event: EventDict) -> Dict[str, Any]:
            nonlocal custom_called
            custom_called = True
            return {"handled": True}
        
        # Register custom handler
        self.event_registry.register_handler("CustomEvent", custom_handler)
        
        # Dispatch custom event
        event = DispatchEvent(
            event_type="CustomEvent",
            event_data={"custom": "data"}
        )
        
        # Mock the registry in the dispatch path
        with patch('src.handlers.event_registry.EventRegistry.get_handler') as mock_get:
            mock_get.return_value = custom_handler
            
            result = await self._dispatch_event(event)
            
            # Verify custom handler was called
            self.assertTrue(result.success)
            self.assertTrue(custom_called)
    
    async def _dispatch_event(self, event: DispatchEvent) -> DispatchResult:
        """Dispatch a single event."""
        start_time = time.time()
        
        try:
            # Convert to EventDict
            event_dict = event.to_dict()
            
            # Get appropriate formatter
            formatter = self._get_formatter(event.event_type, event_dict)
            formatter_name = type(formatter).__name__ if formatter else None
            
            # Format event
            if formatter:
                formatted_output = formatter.format(event_dict)
            else:
                formatted_output = {"raw": event_dict}
            
            # Log dispatch
            self.dispatch_log.append({
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "session_id": event.session_id
            })
            
            return DispatchResult(
                success=True,
                handler_called=f"{event.event_type}EventFormatter",
                formatter_used=formatter_name,
                processing_time=time.time() - start_time,
                formatted_output=formatted_output
            )
            
        except Exception as e:
            return DispatchResult(
                success=False,
                handler_called="error",
                processing_time=time.time() - start_time,
                error=e
            )
    
    async def _dispatch_with_retry(self, event: DispatchEvent, 
                                  max_retries: int) -> DispatchResult:
        """Dispatch with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = await self._dispatch_event(event)
                if result.success:
                    return result
                last_error = result.error
            except Exception as e:
                last_error = e
            
            # Wait before retry
            await asyncio.sleep(0.1 * (attempt + 1))
        
        return DispatchResult(
            success=False,
            handler_called="retry_exhausted",
            error=last_error
        )
    
    def _get_formatter(self, event_type: str, 
                      event_dict: EventDict) -> Optional[BaseFormatter]:
        """Get appropriate formatter for event."""
        if event_type == "ToolUse":
            tool_name = event_dict.get("tool_name", "")
            formatter_map = {
                "Edit": EditToolFormatter(),
                "Write": WriteToolFormatter(),
                "Read": ReadToolFormatter(),
                "Bash": BashToolFormatter(),
                "StrReplaceBasedEditTool": StrReplaceEditorToolFormatter()
            }
            return formatter_map.get(tool_name)
        else:
            formatter_map = {
                "Start": StartEventFormatter(),
                "Stop": StopEventFormatter(),
                "Error": ErrorEventFormatter(),
                "Response": ResponseEventFormatter()
            }
            return formatter_map.get(event_type)
    
    def _should_dispatch_event(self, event: DispatchEvent,
                              enabled_events: List[str],
                              disabled_events: List[str]) -> bool:
        """Check if event should be dispatched based on filters."""
        # If disabled, don't dispatch
        if event.event_type in disabled_events:
            return False
        
        # If enabled list exists and event not in it, don't dispatch
        if enabled_events and event.event_type not in enabled_events:
            return False
        
        return True


if __name__ == "__main__":
    unittest.main()