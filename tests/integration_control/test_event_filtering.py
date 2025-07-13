#!/usr/bin/env python3
"""Test Event Filtering Functionality.

This module provides comprehensive tests for event filtering functionality,
including filter configuration, event matching, whitelist/blacklist logic,
dynamic filtering, and filter performance.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
import sys
import time
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.core.config import ConfigManager
from src.type_defs.events import EventDict, ToolUseEvent
from src.type_defs.base import BaseEvent


# Event filtering test types
@dataclass
class FilterRule:
    """Event filter rule."""
    name: str
    event_type: Optional[str] = None
    tool_name: Optional[str] = None
    session_pattern: Optional[str] = None
    content_pattern: Optional[str] = None
    action: str = "allow"  # allow, block, redirect
    priority: int = 0
    enabled: bool = True


@dataclass
class FilterContext:
    """Context for filter evaluation."""
    event: EventDict
    timestamp: float
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilterResult:
    """Result of filter evaluation."""
    action: str  # allow, block, redirect
    matched_rules: List[FilterRule] = field(default_factory=list)
    reason: str = ""
    redirect_target: Optional[str] = None
    processing_time: float = 0.0


class EventFilter:
    """Event filtering system."""
    
    def __init__(self):
        self.rules: List[FilterRule] = []
        self.enabled_events: Set[str] = set()
        self.disabled_events: Set[str] = set()
        self.default_action = "allow"
    
    def add_rule(self, rule: FilterRule) -> None:
        """Add filter rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove filter rule."""
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        return len(self.rules) < original_count
    
    def set_enabled_events(self, events: List[str]) -> None:
        """Set enabled events list."""
        self.enabled_events = set(events)
    
    def set_disabled_events(self, events: List[str]) -> None:
        """Set disabled events list."""
        self.disabled_events = set(events)
    
    def evaluate(self, context: FilterContext) -> FilterResult:
        """Evaluate event against filter rules."""
        start_time = time.time()
        
        result = FilterResult(action=self.default_action)
        
        # Check basic enabled/disabled lists first
        event_type = context.event.get("event_type", "")
        
        # If explicitly disabled, block
        if event_type in self.disabled_events:
            result.action = "block"
            result.reason = f"Event type '{event_type}' is in disabled list"
            result.processing_time = time.time() - start_time
            return result
        
        # If enabled list exists and event not in it, block
        if self.enabled_events and event_type not in self.enabled_events:
            result.action = "block"
            result.reason = f"Event type '{event_type}' not in enabled list"
            result.processing_time = time.time() - start_time
            return result
        
        # Evaluate custom rules
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if self._matches_rule(rule, context):
                result.matched_rules.append(rule)
                result.action = rule.action
                result.reason = f"Matched rule '{rule.name}'"
                
                # First matching rule wins (highest priority)
                break
        
        result.processing_time = time.time() - start_time
        return result
    
    def _matches_rule(self, rule: FilterRule, context: FilterContext) -> bool:
        """Check if rule matches context."""
        # Event type match
        if rule.event_type and rule.event_type != context.event.get("event_type"):
            return False
        
        # Tool name match (for ToolUse events)
        if rule.tool_name:
            if context.event.get("event_type") != "ToolUse":
                return False
            if rule.tool_name != context.event.get("tool_name"):
                return False
        
        # Session pattern match
        if rule.session_pattern:
            if not re.search(rule.session_pattern, context.session_id):
                return False
        
        # Content pattern match
        if rule.content_pattern:
            event_str = json.dumps(context.event)
            if not re.search(rule.content_pattern, event_str):
                return False
        
        return True


class TestEventFiltering(unittest.IsolatedAsyncioTestCase):
    """Test cases for event filtering functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        self.filter = EventFilter()
        
        # Test events
        self.test_events = [
            {
                "event_type": "Start",
                "timestamp": "2024-01-01T00:00:00Z",
                "session_id": "session-123"
            },
            {
                "event_type": "ToolUse",
                "timestamp": "2024-01-01T00:01:00Z",
                "session_id": "session-123",
                "tool_name": "Edit",
                "tool_input": {"file_path": "/test/file.py"}
            },
            {
                "event_type": "Error",
                "timestamp": "2024-01-01T00:02:00Z",
                "session_id": "session-456",
                "error_type": "ValidationError",
                "error_message": "Invalid input"
            },
            {
                "event_type": "Response",
                "timestamp": "2024-01-01T00:03:00Z",
                "session_id": "session-789",
                "message": "Test response"
            },
            {
                "event_type": "Stop",
                "timestamp": "2024-01-01T00:04:00Z",
                "session_id": "session-123"
            }
        ]
    
    async def test_enabled_events_filtering(self) -> None:
        """Test filtering with enabled events list."""
        enabled_events = ["Start", "ToolUse", "Error"]
        self.filter.set_enabled_events(enabled_events)
        
        for event in self.test_events:
            context = FilterContext(
                event=event,
                timestamp=time.time(),
                session_id=event["session_id"]
            )
            
            result = self.filter.evaluate(context)
            
            if event["event_type"] in enabled_events:
                self.assertEqual(result.action, "allow")
            else:
                self.assertEqual(result.action, "block")
                self.assertIn("not in enabled list", result.reason)
    
    async def test_disabled_events_filtering(self) -> None:
        """Test filtering with disabled events list."""
        disabled_events = ["Response", "Stop"]
        self.filter.set_disabled_events(disabled_events)
        
        for event in self.test_events:
            context = FilterContext(
                event=event,
                timestamp=time.time(),
                session_id=event["session_id"]
            )
            
            result = self.filter.evaluate(context)
            
            if event["event_type"] in disabled_events:
                self.assertEqual(result.action, "block")
                self.assertIn("is in disabled list", result.reason)
            else:
                self.assertEqual(result.action, "allow")
    
    async def test_custom_filter_rules(self) -> None:
        """Test custom filter rules."""
        # Rule to block all Edit tool usage
        edit_block_rule = FilterRule(
            name="block_edit_tool",
            event_type="ToolUse",
            tool_name="Edit",
            action="block",
            priority=10
        )
        self.filter.add_rule(edit_block_rule)
        
        # Rule to allow specific session
        session_allow_rule = FilterRule(
            name="allow_special_session",
            session_pattern="session-123",
            action="allow",
            priority=20
        )
        self.filter.add_rule(session_allow_rule)
        
        for event in self.test_events:
            context = FilterContext(
                event=event,
                timestamp=time.time(),
                session_id=event["session_id"]
            )
            
            result = self.filter.evaluate(context)
            
            # Special session should always be allowed (higher priority)
            if event["session_id"] == "session-123":
                self.assertEqual(result.action, "allow")
                if result.matched_rules:
                    self.assertEqual(result.matched_rules[0].name, "allow_special_session")
            
            # Edit tool from other sessions should be blocked
            elif event.get("tool_name") == "Edit":
                self.assertEqual(result.action, "block")
                self.assertEqual(result.matched_rules[0].name, "block_edit_tool")
    
    async def test_rule_priority_ordering(self) -> None:
        """Test filter rule priority ordering."""
        # Add rules with different priorities
        rules = [
            FilterRule(name="low_priority", event_type="Error", action="allow", priority=1),
            FilterRule(name="high_priority", event_type="Error", action="block", priority=10),
            FilterRule(name="medium_priority", event_type="Error", action="redirect", priority=5)
        ]
        
        for rule in rules:
            self.filter.add_rule(rule)
        
        # Find error event
        error_event = next(e for e in self.test_events if e["event_type"] == "Error")
        context = FilterContext(
            event=error_event,
            timestamp=time.time(),
            session_id=error_event["session_id"]
        )
        
        result = self.filter.evaluate(context)
        
        # Highest priority rule should win
        self.assertEqual(result.action, "block")
        self.assertEqual(result.matched_rules[0].name, "high_priority")
    
    async def test_pattern_matching(self) -> None:
        """Test pattern matching in filter rules."""
        # Rule to block sessions containing "456"
        pattern_rule = FilterRule(
            name="block_456_sessions",
            session_pattern=r".*456.*",
            action="block",
            priority=5
        )
        self.filter.add_rule(pattern_rule)
        
        # Rule to block events containing "ValidationError"
        content_rule = FilterRule(
            name="block_validation_errors",
            content_pattern=r"ValidationError",
            action="block",
            priority=10
        )
        self.filter.add_rule(content_rule)
        
        for event in self.test_events:
            context = FilterContext(
                event=event,
                timestamp=time.time(),
                session_id=event["session_id"]
            )
            
            result = self.filter.evaluate(context)
            
            # Events with ValidationError should be blocked (higher priority)
            if "ValidationError" in json.dumps(event):
                self.assertEqual(result.action, "block")
                self.assertEqual(result.matched_rules[0].name, "block_validation_errors")
            
            # Session 456 should be blocked if no ValidationError
            elif "456" in event["session_id"]:
                self.assertEqual(result.action, "block")
                self.assertEqual(result.matched_rules[0].name, "block_456_sessions")
    
    async def test_dynamic_rule_management(self) -> None:
        """Test dynamic addition and removal of rules."""
        # Add initial rule
        initial_rule = FilterRule(
            name="initial_rule",
            event_type="Start",
            action="block"
        )
        self.filter.add_rule(initial_rule)
        
        # Test with initial rule
        start_event = next(e for e in self.test_events if e["event_type"] == "Start")
        context = FilterContext(
            event=start_event,
            timestamp=time.time(),
            session_id=start_event["session_id"]
        )
        
        result = self.filter.evaluate(context)
        self.assertEqual(result.action, "block")
        
        # Remove rule
        removed = self.filter.remove_rule("initial_rule")
        self.assertTrue(removed)
        
        # Test without rule
        result = self.filter.evaluate(context)
        self.assertEqual(result.action, "allow")  # Default action
        
        # Try to remove non-existent rule
        removed = self.filter.remove_rule("non_existent")
        self.assertFalse(removed)
    
    async def test_rule_enabledisable(self) -> None:
        """Test enabling and disabling rules."""
        # Add disabled rule
        disabled_rule = FilterRule(
            name="disabled_rule",
            event_type="Start",
            action="block",
            enabled=False
        )
        self.filter.add_rule(disabled_rule)
        
        start_event = next(e for e in self.test_events if e["event_type"] == "Start")
        context = FilterContext(
            event=start_event,
            timestamp=time.time(),
            session_id=start_event["session_id"]
        )
        
        # Disabled rule should not match
        result = self.filter.evaluate(context)
        self.assertEqual(result.action, "allow")
        self.assertEqual(len(result.matched_rules), 0)
        
        # Enable rule
        disabled_rule.enabled = True
        
        # Now rule should match
        result = self.filter.evaluate(context)
        self.assertEqual(result.action, "block")
        self.assertEqual(len(result.matched_rules), 1)
    
    async def test_filter_performance(self) -> None:
        """Test filter performance with many rules."""
        # Add many rules
        num_rules = 1000
        for i in range(num_rules):
            rule = FilterRule(
                name=f"rule_{i}",
                event_type="NonExistentType",
                action="block",
                priority=i
            )
            self.filter.add_rule(rule)
        
        # Test performance
        start_event = next(e for e in self.test_events if e["event_type"] == "Start")
        context = FilterContext(
            event=start_event,
            timestamp=time.time(),
            session_id=start_event["session_id"]
        )
        
        # Measure filtering time
        start_time = time.time()
        result = self.filter.evaluate(context)
        filter_time = time.time() - start_time
        
        # Should complete quickly (under 10ms)
        self.assertLess(filter_time, 0.01)
        self.assertLess(result.processing_time, 0.01)
        
        # Should not match any rules (different event type)
        self.assertEqual(result.action, "allow")
        self.assertEqual(len(result.matched_rules), 0)
    
    async def test_complex_filter_scenarios(self) -> None:
        """Test complex filtering scenarios."""
        # Scenario: Block all errors except for specific tools
        rules = [
            # Block all errors (lower priority)
            FilterRule(
                name="block_all_errors",
                event_type="Error",
                action="block",
                priority=1
            ),
            # Allow errors from Read tool (higher priority)
            FilterRule(
                name="allow_read_errors",
                event_type="Error",
                content_pattern=r'"tool_name":\s*"Read"',
                action="allow",
                priority=10
            ),
            # Block errors from specific sessions (medium priority)
            FilterRule(
                name="block_test_session_errors",
                event_type="Error",
                session_pattern=r"test-.*",
                action="block",
                priority=5
            )
        ]
        
        for rule in rules:
            self.filter.add_rule(rule)
        
        # Test different error scenarios
        test_scenarios = [
            # Regular error - should be blocked
            {
                "event": {
                    "event_type": "Error",
                    "session_id": "session-123",
                    "error_message": "General error"
                },
                "expected_action": "block",
                "expected_rule": "block_all_errors"
            },
            # Read tool error - should be allowed
            {
                "event": {
                    "event_type": "Error",
                    "session_id": "session-123",
                    "tool_name": "Read",
                    "error_message": "Read failed"
                },
                "expected_action": "allow",
                "expected_rule": "allow_read_errors"
            },
            # Test session error - should be blocked by specific rule
            {
                "event": {
                    "event_type": "Error",
                    "session_id": "test-session-456",
                    "error_message": "Test error"
                },
                "expected_action": "block",
                "expected_rule": "block_test_session_errors"
            }
        ]
        
        for scenario in test_scenarios:
            context = FilterContext(
                event=scenario["event"],
                timestamp=time.time(),
                session_id=scenario["event"]["session_id"]
            )
            
            result = self.filter.evaluate(context)
            
            self.assertEqual(result.action, scenario["expected_action"])
            if result.matched_rules:
                self.assertEqual(result.matched_rules[0].name, scenario["expected_rule"])
    
    async def test_config_integration(self) -> None:
        """Test integration with configuration system."""
        # Mock configuration
        mock_config = {
            "DISCORD_ENABLED_EVENTS": ["Start", "ToolUse", "Stop"],
            "DISCORD_DISABLED_EVENTS": ["Response"],
            "DISCORD_DEBUG": True
        }
        
        with patch.object(ConfigManager, 'load_config', return_value=mock_config):
            # Simulate config loading
            config = ConfigManager().load_config()
            
            # Apply config to filter
            if "DISCORD_ENABLED_EVENTS" in config:
                enabled = config["DISCORD_ENABLED_EVENTS"]
                if isinstance(enabled, str):
                    enabled = [e.strip() for e in enabled.split(",")]
                self.filter.set_enabled_events(enabled)
            
            if "DISCORD_DISABLED_EVENTS" in config:
                disabled = config["DISCORD_DISABLED_EVENTS"]
                if isinstance(disabled, str):
                    disabled = [e.strip() for e in disabled.split(",")]
                self.filter.set_disabled_events(disabled)
            
            # Test filtering with config
            for event in self.test_events:
                context = FilterContext(
                    event=event,
                    timestamp=time.time(),
                    session_id=event["session_id"]
                )
                
                result = self.filter.evaluate(context)
                
                # Response should be blocked (disabled)
                if event["event_type"] == "Response":
                    self.assertEqual(result.action, "block")
                
                # Error should be blocked (not in enabled list)
                elif event["event_type"] == "Error":
                    self.assertEqual(result.action, "block")
                
                # Others should be allowed
                else:
                    self.assertEqual(result.action, "allow")
    
    async def test_filter_logging(self) -> None:
        """Test filter decision logging."""
        # Add rule with logging
        logged_events = []
        
        def mock_log(message: str, **kwargs):
            logged_events.append({"message": message, "data": kwargs})
        
        # Patch logger
        with patch.object(self.logger, 'info', side_effect=mock_log):
            # Add rule
            rule = FilterRule(
                name="test_logging_rule",
                event_type="Start",
                action="block"
            )
            self.filter.add_rule(rule)
            
            # Process event
            start_event = next(e for e in self.test_events if e["event_type"] == "Start")
            context = FilterContext(
                event=start_event,
                timestamp=time.time(),
                session_id=start_event["session_id"]
            )
            
            result = self.filter.evaluate(context)
            
            # Log the result
            self.logger.info(
                "filter_decision",
                action=result.action,
                matched_rules=[r.name for r in result.matched_rules],
                reason=result.reason,
                processing_time=result.processing_time
            )
            
            # Verify logging
            self.assertEqual(len(logged_events), 1)
            log_entry = logged_events[0]
            self.assertEqual(log_entry["message"], "filter_decision")
            self.assertEqual(log_entry["data"]["action"], "block")


if __name__ == "__main__":
    unittest.main()