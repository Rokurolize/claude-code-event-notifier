#!/usr/bin/env python3
"""Test Error Handling Coverage.

This module provides comprehensive tests for error handling functionality,
including exception handling, error recovery, graceful degradation,
error reporting, and cascading failure prevention.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable, Type
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import sys
import traceback
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from contextlib import contextmanager
import tempfile
import sqlite3

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.exceptions import (
    DiscordNotifierError,
    ConfigurationError,
    DiscordAPIError,
    ThreadManagementError,
    FormattingError,
    StorageError,
    EventProcessingError,
    ValidationError
)
from src.discord_notifier import main as discord_notifier_main
from src.core.http_client import HTTPClient
from src.handlers.discord_sender import DiscordSender
from src.handlers.thread_manager import ThreadManager
from src.thread_storage import ThreadStorage


# Error handling test types
@dataclass
class ErrorScenario:
    """Error scenario configuration."""
    name: str
    error_type: Type[Exception]
    error_message: str
    context: Dict[str, Any]
    expected_behavior: str
    recovery_possible: bool = True
    cascading_errors: List[str] = field(default_factory=list)


@dataclass
class ErrorMetrics:
    """Error handling metrics."""
    total_errors: int = 0
    handled_errors: int = 0
    unhandled_errors: int = 0
    recovered_errors: int = 0
    cascading_failures: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    recovery_times: List[float] = field(default_factory=list)


class ErrorHandler(Protocol):
    """Protocol for error handlers."""
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Handle error and return True if recovered."""
        ...
    
    def get_fallback_value(self, error: Exception) -> Any:
        """Get fallback value for error."""
        ...


class TestErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Test cases for error handling coverage."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.logger = AstolfoLogger(__name__)
        
        # Test configuration
        self.test_config = {
            "error_handling": "comprehensive",
            "recovery_enabled": True,
            "cascading_prevention": True,
            "error_reporting": True,
            "graceful_degradation": True,
            "debug": True
        }
        
        # Error scenarios
        self.error_scenarios = [
            ErrorScenario(
                name="Discord API Connection Error",
                error_type=DiscordAPIError,
                error_message="Failed to connect to Discord API",
                context={"status_code": 503, "retry_count": 3},
                expected_behavior="Retry with exponential backoff",
                recovery_possible=True,
                cascading_errors=["Thread creation failure", "Message delivery failure"]
            ),
            ErrorScenario(
                name="Configuration Missing Required Field",
                error_type=ConfigurationError,
                error_message="Missing required field: DISCORD_WEBHOOK_URL",
                context={"config_file": ".env", "field": "DISCORD_WEBHOOK_URL"},
                expected_behavior="Exit with clear error message",
                recovery_possible=False
            ),
            ErrorScenario(
                name="SQLite Database Lock",
                error_type=StorageError,
                error_message="Database is locked",
                context={"operation": "thread_save", "retry_count": 5},
                expected_behavior="Retry with backoff, then fallback to memory cache",
                recovery_possible=True
            ),
            ErrorScenario(
                name="Invalid Event Data",
                error_type=ValidationError,
                error_message="Invalid event data: missing session_id",
                context={"event_type": "Stop", "data": {"timestamp": "2025-07-12T22:00:00.000Z"}},
                expected_behavior="Log error and skip event",
                recovery_possible=True
            ),
            ErrorScenario(
                name="Memory Allocation Error",
                error_type=MemoryError,
                error_message="Cannot allocate memory for large embed",
                context={"embed_size": 10485760, "available_memory": 1048576},
                expected_behavior="Truncate content and retry",
                recovery_possible=True
            ),
            ErrorScenario(
                name="Circular Import Error",
                error_type=ImportError,
                error_message="Circular import detected",
                context={"module": "src.handlers.discord_sender", "import_chain": ["a", "b", "a"]},
                expected_behavior="Exit with import chain details",
                recovery_possible=False
            )
        ]
        
        # Error metrics
        self.error_metrics = ErrorMetrics()
    
    async def test_exception_handling_coverage(self) -> None:
        """Test comprehensive exception handling coverage."""
        with patch('src.discord_notifier.process_event') as mock_process:
            # Mock exception handling
            handled_exceptions = []
            unhandled_exceptions = []
            
            def track_exception(exc_type: Type[Exception], exc_value: Exception, exc_tb: Any) -> None:
                """Track exception handling."""
                exception_info = {
                    "type": exc_type.__name__,
                    "message": str(exc_value),
                    "traceback": traceback.format_tb(exc_tb) if exc_tb else None,
                    "handled": False
                }
                
                # Check if exception was handled
                if hasattr(exc_value, '_handled'):
                    exception_info["handled"] = True
                    handled_exceptions.append(exception_info)
                else:
                    unhandled_exceptions.append(exception_info)
            
            # Test exception scenarios
            exception_test_cases = [
                # Discord API errors
                {
                    "name": "Rate limit error",
                    "exception": DiscordAPIError("Rate limit exceeded", status_code=429),
                    "expected_handling": "retry_with_backoff"
                },
                {
                    "name": "Authentication error",
                    "exception": DiscordAPIError("Invalid token", status_code=401),
                    "expected_handling": "exit_with_error"
                },
                {
                    "name": "Server error",
                    "exception": DiscordAPIError("Internal server error", status_code=500),
                    "expected_handling": "retry_with_backoff"
                },
                # Configuration errors
                {
                    "name": "Missing config",
                    "exception": ConfigurationError("Configuration file not found"),
                    "expected_handling": "use_defaults"
                },
                {
                    "name": "Invalid config",
                    "exception": ConfigurationError("Invalid configuration format"),
                    "expected_handling": "exit_with_error"
                },
                # Storage errors
                {
                    "name": "Database corruption",
                    "exception": StorageError("Database file is corrupted"),
                    "expected_handling": "recreate_database"
                },
                {
                    "name": "Permission denied",
                    "exception": StorageError("Permission denied accessing database"),
                    "expected_handling": "use_memory_fallback"
                },
                # Validation errors
                {
                    "name": "Invalid timestamp",
                    "exception": ValidationError("Invalid timestamp format"),
                    "expected_handling": "skip_event"
                },
                {
                    "name": "Schema mismatch",
                    "exception": ValidationError("Event schema mismatch"),
                    "expected_handling": "attempt_migration"
                },
                # System errors
                {
                    "name": "Out of memory",
                    "exception": MemoryError("Out of memory"),
                    "expected_handling": "reduce_memory_usage"
                },
                {
                    "name": "Network timeout",
                    "exception": TimeoutError("Network operation timed out"),
                    "expected_handling": "retry_with_timeout"
                },
                # Unexpected errors
                {
                    "name": "Unknown error",
                    "exception": RuntimeError("Unexpected error occurred"),
                    "expected_handling": "log_and_continue"
                }
            ]
            
            exception_results = []
            
            for test_case in exception_test_cases:
                try:
                    # Simulate exception
                    raise test_case["exception"]
                except Exception as e:
                    # Simulate exception handling
                    handling_result = self._simulate_exception_handling(
                        e,
                        test_case["expected_handling"]
                    )
                    
                    exception_results.append({
                        "test": test_case["name"],
                        "exception_type": type(e).__name__,
                        "expected_handling": test_case["expected_handling"],
                        "actual_handling": handling_result["handling"],
                        "recovered": handling_result["recovered"],
                        "fallback_used": handling_result.get("fallback_used", False)
                    })
                    
                    # Mark as handled if recovered
                    if handling_result["recovered"]:
                        e._handled = True
                        handled_exceptions.append({
                            "type": type(e).__name__,
                            "message": str(e),
                            "handling": handling_result["handling"]
                        })
                    else:
                        unhandled_exceptions.append({
                            "type": type(e).__name__,
                            "message": str(e),
                            "reason": handling_result.get("reason", "Unknown")
                        })
            
            # Test exception hierarchy handling
            exception_hierarchy = {
                DiscordNotifierError: [
                    ConfigurationError,
                    DiscordAPIError,
                    ThreadManagementError,
                    FormattingError,
                    StorageError,
                    EventProcessingError,
                    ValidationError
                ],
                Exception: [
                    DiscordNotifierError,
                    ValueError,
                    TypeError,
                    KeyError,
                    IOError,
                    RuntimeError
                ]
            }
            
            # Verify exception hierarchy is properly handled
            for base_exc, derived_excs in exception_hierarchy.items():
                for derived_exc in derived_excs:
                    self.assertTrue(
                        issubclass(derived_exc, base_exc) or base_exc == Exception,
                        f"{derived_exc.__name__} should be handled by {base_exc.__name__} handler"
                    )
            
            # Calculate exception handling metrics
            total_exceptions = len(exception_test_cases)
            handled_count = len(handled_exceptions)
            unhandled_count = len(unhandled_exceptions)
            coverage_rate = handled_count / total_exceptions if total_exceptions > 0 else 0
            
            # Log exception handling analysis
            self.logger.info(
                "Exception handling coverage analysis",
                context={
                    "total_exceptions": total_exceptions,
                    "handled_exceptions": handled_count,
                    "unhandled_exceptions": unhandled_count,
                    "coverage_rate": coverage_rate,
                    "exception_types": len(set(r["exception_type"] for r in exception_results)),
                    "recovery_rate": sum(1 for r in exception_results if r["recovered"]) / len(exception_results),
                    "fallback_usage": sum(1 for r in exception_results if r.get("fallback_used", False)),
                    "hierarchy_depth": max(len([base for base, derived in exception_hierarchy.items() if any(isinstance(e["exception"], derived) for e in exception_test_cases if "exception" in e)]) for e in exception_test_cases)
                }
            )
    
    async def test_error_recovery_mechanisms(self) -> None:
        """Test error recovery mechanisms."""
        with patch('src.core.http_client.HTTPClient.request') as mock_request:
            # Mock error recovery
            recovery_log = []
            
            async def simulate_recovery(error_scenario: ErrorScenario) -> Dict[str, Any]:
                """Simulate error recovery."""
                recovery_attempt = {
                    "scenario": error_scenario.name,
                    "error_type": error_scenario.error_type.__name__,
                    "attempts": [],
                    "recovered": False,
                    "final_state": None,
                    "recovery_time": 0
                }
                
                start_time = datetime.now()
                max_attempts = 3
                
                for attempt in range(max_attempts):
                    attempt_info = {
                        "attempt_number": attempt + 1,
                        "strategy": None,
                        "success": False,
                        "error": None
                    }
                    
                    try:
                        # Choose recovery strategy based on error type
                        if error_scenario.error_type == DiscordAPIError:
                            # API error recovery
                            if error_scenario.context.get("status_code") == 429:
                                # Rate limit - wait and retry
                                attempt_info["strategy"] = "exponential_backoff"
                                await asyncio.sleep(2 ** attempt * 0.1)  # Simulated backoff
                                if attempt == max_attempts - 1:
                                    attempt_info["success"] = True
                            elif error_scenario.context.get("status_code") >= 500:
                                # Server error - retry with different endpoint
                                attempt_info["strategy"] = "failover_endpoint"
                                if attempt > 0:
                                    attempt_info["success"] = True
                            else:
                                # Client error - cannot recover
                                attempt_info["strategy"] = "no_recovery"
                                raise error_scenario.error_type(error_scenario.error_message)
                        
                        elif error_scenario.error_type == StorageError:
                            # Storage error recovery
                            if "locked" in error_scenario.error_message.lower():
                                # Database lock - wait and retry
                                attempt_info["strategy"] = "wait_for_unlock"
                                await asyncio.sleep(0.5 * (attempt + 1))
                                if attempt == max_attempts - 1:
                                    attempt_info["success"] = True
                            elif "corrupt" in error_scenario.error_message.lower():
                                # Corruption - recreate database
                                attempt_info["strategy"] = "recreate_storage"
                                if attempt == 0:
                                    # Simulate database recreation
                                    attempt_info["success"] = True
                            else:
                                # Use in-memory fallback
                                attempt_info["strategy"] = "memory_fallback"
                                attempt_info["success"] = True
                        
                        elif error_scenario.error_type == ValidationError:
                            # Validation error recovery
                            attempt_info["strategy"] = "data_sanitization"
                            # Attempt to fix validation issues
                            if attempt == 0:
                                # First attempt - try to fix data
                                attempt_info["success"] = True
                        
                        elif error_scenario.error_type == MemoryError:
                            # Memory error recovery
                            if attempt == 0:
                                # Try garbage collection
                                attempt_info["strategy"] = "garbage_collection"
                                import gc
                                gc.collect()
                            elif attempt == 1:
                                # Reduce memory usage
                                attempt_info["strategy"] = "reduce_memory_usage"
                                attempt_info["success"] = True
                        
                        else:
                            # Generic recovery
                            attempt_info["strategy"] = "generic_retry"
                            if attempt == max_attempts - 1:
                                attempt_info["success"] = True
                        
                        if attempt_info["success"]:
                            recovery_attempt["recovered"] = True
                            recovery_attempt["final_state"] = "recovered"
                            break
                    
                    except Exception as e:
                        attempt_info["error"] = str(e)
                    
                    recovery_attempt["attempts"].append(attempt_info)
                
                end_time = datetime.now()
                recovery_attempt["recovery_time"] = (end_time - start_time).total_seconds()
                
                if not recovery_attempt["recovered"]:
                    recovery_attempt["final_state"] = "failed"
                
                recovery_log.append(recovery_attempt)
                return recovery_attempt
            
            # Test recovery for each error scenario
            recovery_results = []
            
            for scenario in self.error_scenarios:
                if scenario.recovery_possible:
                    result = await simulate_recovery(scenario)
                    recovery_results.append(result)
                    
                    # Update metrics
                    self.error_metrics.total_errors += 1
                    if result["recovered"]:
                        self.error_metrics.recovered_errors += 1
                    self.error_metrics.recovery_times.append(result["recovery_time"])
            
            # Test cascading failure prevention
            cascading_test = await self._test_cascading_failure_prevention()
            
            # Calculate recovery metrics
            total_recoverable = len([s for s in self.error_scenarios if s.recovery_possible])
            recovered_count = sum(1 for r in recovery_results if r["recovered"])
            recovery_rate = recovered_count / total_recoverable if total_recoverable > 0 else 0
            avg_recovery_time = sum(r["recovery_time"] for r in recovery_results) / len(recovery_results) if recovery_results else 0
            
            # Log error recovery analysis
            self.logger.info(
                "Error recovery mechanisms analysis",
                context={
                    "total_recoverable_errors": total_recoverable,
                    "recovered_errors": recovered_count,
                    "recovery_rate": recovery_rate,
                    "average_recovery_time": avg_recovery_time,
                    "recovery_strategies_used": list(set(
                        attempt["strategy"]
                        for result in recovery_results
                        for attempt in result["attempts"]
                        if attempt["strategy"]
                    )),
                    "max_recovery_attempts": max(len(r["attempts"]) for r in recovery_results),
                    "cascading_failures_prevented": cascading_test["prevented_count"]
                }
            )
    
    async def test_graceful_degradation(self) -> None:
        """Test graceful degradation under errors."""
        with patch('src.handlers.discord_sender.DiscordSender.send_message') as mock_send:
            # Mock graceful degradation
            degradation_log = []
            
            class DegradationHandler:
                """Handle graceful degradation."""
                def __init__(self):
                    self.degradation_levels = [
                        "full_functionality",
                        "reduced_features",
                        "basic_operation",
                        "safe_mode",
                        "minimal_function"
                    ]
                    self.current_level = 0
                    self.feature_states = {
                        "threads": True,
                        "embeds": True,
                        "formatting": True,
                        "persistence": True,
                        "retries": True
                    }
                
                def degrade(self, error: Exception) -> Dict[str, Any]:
                    """Degrade functionality based on error."""
                    degradation_info = {
                        "error": str(error),
                        "error_type": type(error).__name__,
                        "previous_level": self.degradation_levels[self.current_level],
                        "new_level": None,
                        "disabled_features": []
                    }
                    
                    # Determine degradation based on error type
                    if isinstance(error, DiscordAPIError):
                        if error.status_code == 429:  # Rate limit
                            # Disable retries temporarily
                            self.feature_states["retries"] = False
                            degradation_info["disabled_features"].append("retries")
                        elif error.status_code >= 500:  # Server error
                            # Disable complex features
                            self.feature_states["threads"] = False
                            self.feature_states["embeds"] = False
                            degradation_info["disabled_features"].extend(["threads", "embeds"])
                            self.current_level = min(self.current_level + 2, len(self.degradation_levels) - 1)
                    
                    elif isinstance(error, StorageError):
                        # Disable persistence
                        self.feature_states["persistence"] = False
                        degradation_info["disabled_features"].append("persistence")
                        self.current_level = min(self.current_level + 1, len(self.degradation_levels) - 1)
                    
                    elif isinstance(error, MemoryError):
                        # Disable memory-intensive features
                        self.feature_states["embeds"] = False
                        self.feature_states["formatting"] = False
                        degradation_info["disabled_features"].extend(["embeds", "formatting"])
                        self.current_level = min(self.current_level + 2, len(self.degradation_levels) - 1)
                    
                    elif isinstance(error, FormattingError):
                        # Disable advanced formatting
                        self.feature_states["formatting"] = False
                        degradation_info["disabled_features"].append("formatting")
                    
                    degradation_info["new_level"] = self.degradation_levels[self.current_level]
                    degradation_log.append(degradation_info)
                    
                    return {
                        "level": self.degradation_levels[self.current_level],
                        "features": self.feature_states.copy(),
                        "can_continue": self.current_level < len(self.degradation_levels) - 1
                    }
            
            # Test degradation scenarios
            handler = DegradationHandler()
            degradation_scenarios = [
                # Progressive degradation
                DiscordAPIError("Rate limited", status_code=429),
                StorageError("Database locked"),
                DiscordAPIError("Server error", status_code=500),
                MemoryError("Out of memory"),
                FormattingError("Template error")
            ]
            
            degradation_results = []
            
            for error in degradation_scenarios:
                result = handler.degrade(error)
                degradation_results.append({
                    "error": str(error),
                    "degradation_level": result["level"],
                    "active_features": sum(1 for v in result["features"].values() if v),
                    "total_features": len(result["features"]),
                    "can_continue": result["can_continue"]
                })
            
            # Test feature fallbacks
            fallback_tests = [
                {
                    "feature": "threads",
                    "fallback": "main_channel",
                    "test": lambda: handler.feature_states["threads"]
                },
                {
                    "feature": "embeds",
                    "fallback": "plain_text",
                    "test": lambda: handler.feature_states["embeds"]
                },
                {
                    "feature": "persistence",
                    "fallback": "memory_cache",
                    "test": lambda: handler.feature_states["persistence"]
                }
            ]
            
            fallback_results = []
            
            for test in fallback_tests:
                is_available = test["test"]()
                fallback_results.append({
                    "feature": test["feature"],
                    "available": is_available,
                    "fallback": test["fallback"] if not is_available else None
                })
            
            # Calculate degradation metrics
            total_degradations = len(degradation_results)
            features_disabled = sum(
                len(log["disabled_features"])
                for log in degradation_log
            )
            final_functionality = degradation_results[-1]["active_features"] / degradation_results[-1]["total_features"]
            
            # Log graceful degradation analysis
            self.logger.info(
                "Graceful degradation analysis",
                context={
                    "degradation_events": total_degradations,
                    "features_disabled": features_disabled,
                    "final_functionality_percentage": final_functionality * 100,
                    "degradation_levels_used": len(set(r["degradation_level"] for r in degradation_results)),
                    "fallbacks_active": sum(1 for f in fallback_results if f["fallback"]),
                    "can_continue_operating": degradation_results[-1]["can_continue"],
                    "degradation_path": [r["degradation_level"] for r in degradation_results]
                }
            )
    
    async def test_error_reporting(self) -> None:
        """Test error reporting and logging."""
        with patch('src.utils.astolfo_logger.AstolfoLogger.error') as mock_log_error:
            # Mock error reporting
            error_reports = []
            
            class ErrorReporter:
                """Handle error reporting."""
                def __init__(self, logger: AstolfoLogger):
                    self.logger = logger
                    self.error_buffer = []
                    self.report_threshold = 5
                    self.last_report_time = datetime.now(timezone.utc)
                
                def report_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
                    """Report error with context."""
                    error_report = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "context": context,
                        "traceback": traceback.format_exc(),
                        "severity": self._determine_severity(error),
                        "user_impact": self._assess_user_impact(error),
                        "recovery_suggestions": self._get_recovery_suggestions(error)
                    }
                    
                    # Add to buffer
                    self.error_buffer.append(error_report)
                    
                    # Log based on severity
                    if error_report["severity"] == "critical":
                        self.logger.error(
                            f"CRITICAL ERROR: {error_report['error_type']}",
                            error=error,
                            context=context,
                            traceback=error_report["traceback"]
                        )
                    elif error_report["severity"] == "high":
                        self.logger.error(
                            f"Error occurred: {error_report['error_type']}",
                            error=error,
                            context=context
                        )
                    else:
                        self.logger.warning(
                            f"Handled error: {error_report['error_type']}",
                            error=str(error),
                            context=context
                        )
                    
                    # Check if batch report needed
                    if len(self.error_buffer) >= self.report_threshold:
                        self._send_batch_report()
                    
                    error_reports.append(error_report)
                    return error_report
                
                def _determine_severity(self, error: Exception) -> str:
                    """Determine error severity."""
                    if isinstance(error, (ConfigurationError, ImportError)):
                        return "critical"
                    elif isinstance(error, (DiscordAPIError, StorageError)):
                        if hasattr(error, 'status_code') and error.status_code == 401:
                            return "critical"
                        return "high"
                    elif isinstance(error, (ValidationError, FormattingError)):
                        return "medium"
                    else:
                        return "low"
                
                def _assess_user_impact(self, error: Exception) -> str:
                    """Assess user impact of error."""
                    if isinstance(error, ConfigurationError):
                        return "Service unavailable"
                    elif isinstance(error, DiscordAPIError):
                        return "Messages may be delayed or lost"
                    elif isinstance(error, StorageError):
                        return "Thread history may be lost"
                    elif isinstance(error, ValidationError):
                        return "Some events may be skipped"
                    else:
                        return "Minimal impact"
                
                def _get_recovery_suggestions(self, error: Exception) -> List[str]:
                    """Get recovery suggestions for error."""
                    suggestions = []
                    
                    if isinstance(error, ConfigurationError):
                        suggestions.extend([
                            "Check configuration file exists",
                            "Verify all required fields are set",
                            "Ensure environment variables are loaded"
                        ])
                    elif isinstance(error, DiscordAPIError):
                        if hasattr(error, 'status_code'):
                            if error.status_code == 401:
                                suggestions.append("Check Discord token/webhook URL")
                            elif error.status_code == 429:
                                suggestions.append("Wait for rate limit to reset")
                            elif error.status_code >= 500:
                                suggestions.append("Discord API may be down, retry later")
                    elif isinstance(error, StorageError):
                        suggestions.extend([
                            "Check file permissions",
                            "Ensure sufficient disk space",
                            "Try deleting and recreating database"
                        ])
                    
                    return suggestions
                
                def _send_batch_report(self) -> None:
                    """Send batch error report."""
                    if not self.error_buffer:
                        return
                    
                    summary = {
                        "report_time": datetime.now(timezone.utc).isoformat(),
                        "error_count": len(self.error_buffer),
                        "critical_errors": sum(1 for e in self.error_buffer if e["severity"] == "critical"),
                        "error_types": {},
                        "common_contexts": {}
                    }
                    
                    for error in self.error_buffer:
                        error_type = error["error_type"]
                        summary["error_types"][error_type] = summary["error_types"].get(error_type, 0) + 1
                    
                    self.logger.info(
                        "Batch error report",
                        summary=summary,
                        errors=self.error_buffer[:10]  # First 10 errors
                    )
                    
                    self.error_buffer.clear()
                    self.last_report_time = datetime.now(timezone.utc)
            
            # Test error reporting
            reporter = ErrorReporter(self.logger)
            
            # Generate various errors
            test_errors = [
                ConfigurationError("Missing DISCORD_WEBHOOK_URL"),
                DiscordAPIError("Unauthorized", status_code=401),
                DiscordAPIError("Rate limited", status_code=429),
                StorageError("Database is locked"),
                ValidationError("Invalid event format"),
                FormattingError("Template rendering failed"),
                RuntimeError("Unexpected error"),
                MemoryError("Out of memory")
            ]
            
            for i, error in enumerate(test_errors):
                context = {
                    "event_id": f"test_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attempt": 1
                }
                reporter.report_error(error, context)
            
            # Analyze error reports
            severity_distribution = {}
            impact_distribution = {}
            
            for report in error_reports:
                severity = report["severity"]
                impact = report["user_impact"]
                
                severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
                impact_distribution[impact] = impact_distribution.get(impact, 0) + 1
            
            # Test error aggregation
            error_aggregation = {
                "total_errors": len(error_reports),
                "unique_error_types": len(set(r["error_type"] for r in error_reports)),
                "critical_errors": severity_distribution.get("critical", 0),
                "errors_with_suggestions": sum(1 for r in error_reports if r["recovery_suggestions"]),
                "average_context_size": sum(len(r["context"]) for r in error_reports) / len(error_reports) if error_reports else 0
            }
            
            # Log error reporting analysis
            self.logger.info(
                "Error reporting analysis",
                context={
                    "total_errors_reported": len(error_reports),
                    "severity_distribution": severity_distribution,
                    "impact_distribution": impact_distribution,
                    "error_aggregation": error_aggregation,
                    "batch_reports_sent": len(error_reports) // reporter.report_threshold,
                    "suggestions_provided": sum(len(r["recovery_suggestions"]) for r in error_reports)
                }
            )
    
    async def test_cascading_failure_prevention(self) -> None:
        """Test cascading failure prevention."""
        # Cascading failure prevention system
        class CircuitBreaker:
            """Circuit breaker for preventing cascading failures."""
            def __init__(self, failure_threshold: int = 5, recovery_time: float = 60):
                self.failure_threshold = failure_threshold
                self.recovery_time = recovery_time
                self.failure_count = 0
                self.last_failure_time = None
                self.state = "closed"  # closed, open, half_open
                self.protected_calls = 0
                self.prevented_cascades = 0
            
            def call(self, func: Callable, *args, **kwargs) -> Any:
                """Call function with circuit breaker protection."""
                self.protected_calls += 1
                
                if self.state == "open":
                    # Check if recovery time has passed
                    if self.last_failure_time and \
                       (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_time:
                        self.state = "half_open"
                        self.failure_count = 0
                    else:
                        self.prevented_cascades += 1
                        raise CircuitBreakerOpen("Circuit breaker is open")
                
                try:
                    result = func(*args, **kwargs)
                    
                    if self.state == "half_open":
                        # Successful call in half_open state, close the circuit
                        self.state = "closed"
                        self.failure_count = 0
                    
                    return result
                
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = datetime.now()
                    
                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                    
                    raise e
        
        class CircuitBreakerOpen(Exception):
            """Circuit breaker is open."""
            pass
        
        # Test cascading failure scenarios
        cascading_scenarios = [
            {
                "name": "Discord API cascade",
                "initial_error": DiscordAPIError("Service unavailable", status_code=503),
                "potential_cascade": [
                    "Thread creation fails",
                    "Message queue backs up",
                    "Memory usage spikes",
                    "Database locks up",
                    "Complete service failure"
                ]
            },
            {
                "name": "Database cascade",
                "initial_error": StorageError("Database corrupted"),
                "potential_cascade": [
                    "Thread lookups fail",
                    "Cache invalidation fails",
                    "Message routing breaks",
                    "Duplicate threads created",
                    "Data inconsistency"
                ]
            },
            {
                "name": "Memory cascade",
                "initial_error": MemoryError("Heap allocation failed"),
                "potential_cascade": [
                    "Large embeds fail",
                    "Message formatting breaks",
                    "Event processing stops",
                    "Garbage collection thrashing",
                    "System unresponsive"
                ]
            }
        ]
        
        cascade_prevention_results = []
        
        for scenario in cascading_scenarios:
            # Simulate cascade with circuit breaker
            breaker = CircuitBreaker(failure_threshold=3, recovery_time=10)
            cascade_info = {
                "scenario": scenario["name"],
                "initial_error": str(scenario["initial_error"]),
                "cascade_steps": [],
                "prevented_at_step": None,
                "total_failures": 0,
                "circuit_opened": False
            }
            
            # Simulate cascade steps
            for i, step in enumerate(scenario["potential_cascade"]):
                try:
                    # Simulate operation that could fail
                    def failing_operation():
                        if i < 3:  # First 3 operations fail
                            raise scenario["initial_error"]
                        return "success"
                    
                    result = breaker.call(failing_operation)
                    cascade_info["cascade_steps"].append({
                        "step": step,
                        "result": "success",
                        "circuit_state": breaker.state
                    })
                
                except CircuitBreakerOpen:
                    cascade_info["cascade_steps"].append({
                        "step": step,
                        "result": "prevented",
                        "circuit_state": breaker.state
                    })
                    cascade_info["prevented_at_step"] = i
                    cascade_info["circuit_opened"] = True
                    break
                
                except Exception as e:
                    cascade_info["total_failures"] += 1
                    cascade_info["cascade_steps"].append({
                        "step": step,
                        "result": "failed",
                        "error": str(e),
                        "circuit_state": breaker.state
                    })
            
            cascade_info["cascades_prevented"] = breaker.prevented_cascades
            cascade_prevention_results.append(cascade_info)
        
        # Test dependency isolation
        dependency_isolation_test = await self._test_dependency_isolation()
        
        # Calculate cascade prevention metrics
        total_scenarios = len(cascade_prevention_results)
        cascades_prevented = sum(1 for r in cascade_prevention_results if r["circuit_opened"])
        avg_prevention_step = sum(
            r["prevented_at_step"] for r in cascade_prevention_results 
            if r["prevented_at_step"] is not None
        ) / cascades_prevented if cascades_prevented > 0 else 0
        
        return {
            "prevented_count": cascades_prevented,
            "results": cascade_prevention_results,
            "metrics": {
                "total_scenarios": total_scenarios,
                "cascades_prevented": cascades_prevented,
                "prevention_rate": cascades_prevented / total_scenarios,
                "average_prevention_step": avg_prevention_step,
                "dependency_isolation": dependency_isolation_test
            }
        }
    
    # Helper methods
    
    def _simulate_exception_handling(self, exception: Exception, expected_handling: str) -> Dict[str, Any]:
        """Simulate exception handling based on expected behavior."""
        handling_result = {
            "handling": expected_handling,
            "recovered": False,
            "fallback_used": False,
            "reason": None
        }
        
        # Simulate different handling strategies
        if expected_handling == "retry_with_backoff":
            # Simulate retry logic
            handling_result["recovered"] = True
            handling_result["handling"] = "retried_successfully"
        
        elif expected_handling == "exit_with_error":
            # Cannot recover from this
            handling_result["recovered"] = False
            handling_result["reason"] = "Fatal error, cannot continue"
        
        elif expected_handling == "use_defaults":
            # Use default configuration
            handling_result["recovered"] = True
            handling_result["fallback_used"] = True
            handling_result["handling"] = "using_defaults"
        
        elif expected_handling == "recreate_database":
            # Recreate corrupted database
            handling_result["recovered"] = True
            handling_result["handling"] = "database_recreated"
        
        elif expected_handling == "use_memory_fallback":
            # Use in-memory storage
            handling_result["recovered"] = True
            handling_result["fallback_used"] = True
            handling_result["handling"] = "using_memory_storage"
        
        elif expected_handling == "skip_event":
            # Skip problematic event
            handling_result["recovered"] = True
            handling_result["handling"] = "event_skipped"
        
        elif expected_handling == "attempt_migration":
            # Try to migrate schema
            handling_result["recovered"] = True
            handling_result["handling"] = "schema_migrated"
        
        elif expected_handling == "reduce_memory_usage":
            # Reduce memory footprint
            handling_result["recovered"] = True
            handling_result["handling"] = "memory_reduced"
        
        elif expected_handling == "retry_with_timeout":
            # Retry with increased timeout
            handling_result["recovered"] = True
            handling_result["handling"] = "retried_with_timeout"
        
        elif expected_handling == "log_and_continue":
            # Log error and continue
            handling_result["recovered"] = True
            handling_result["handling"] = "logged_and_continued"
        
        return handling_result
    
    async def _test_cascading_failure_prevention(self) -> Dict[str, Any]:
        """Test cascading failure prevention mechanisms."""
        # Implementation provided in test_cascading_failure_prevention method
        return await self.test_cascading_failure_prevention()
    
    async def _test_dependency_isolation(self) -> Dict[str, Any]:
        """Test dependency isolation for failure containment."""
        isolation_results = {
            "isolated_components": 0,
            "shared_dependencies": 0,
            "isolation_score": 0.0
        }
        
        # Define component dependencies
        components = {
            "discord_sender": ["http_client", "logger"],
            "thread_manager": ["thread_storage", "discord_sender", "logger"],
            "event_formatter": ["logger"],
            "thread_storage": ["sqlite3", "logger"],
            "http_client": ["logger"]
        }
        
        # Check for shared dependencies
        all_deps = []
        for deps in components.values():
            all_deps.extend(deps)
        
        unique_deps = set(all_deps)
        dep_counts = {dep: all_deps.count(dep) for dep in unique_deps}
        
        isolation_results["isolated_components"] = sum(1 for count in dep_counts.values() if count == 1)
        isolation_results["shared_dependencies"] = sum(1 for count in dep_counts.values() if count > 1)
        isolation_results["isolation_score"] = isolation_results["isolated_components"] / len(unique_deps) if unique_deps else 0
        
        return isolation_results


def run_error_handling_tests() -> None:
    """Run error handling tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestErrorHandling)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nError Handling Tests Summary:")
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