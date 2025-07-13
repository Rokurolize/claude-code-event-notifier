#!/usr/bin/env python3
"""Test Logging Functionality and AstolfoLogger Completeness.

This module provides comprehensive tests for logging functionality,
including AstolfoLogger coverage, structured logging, log filtering,
performance impact, and log analysis capabilities.
"""

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
import sys
import logging
import tempfile
import os
import re
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
import io
import gzip
import threading
import time

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger, LogLevel, LogEntry, LogContext
from src.utils.session_logger import SessionLogger
from src.discord_notifier import setup_logging
from src.handlers.discord_sender import DiscordSender
from src.core.http_client import HTTPClient
from src.thread_storage import ThreadStorage
from src.formatters.base import BaseFormatter


# Logging test types
@dataclass
class LogScenario:
    """Log scenario configuration."""
    name: str
    log_level: LogLevel
    message: str
    context: LogContext
    expected_output: Dict[str, Any]
    should_log: bool = True
    performance_impact: Optional[float] = None


@dataclass
class LogMetrics:
    """Logging performance metrics."""
    total_logs: int = 0
    logs_per_level: Dict[str, int] = field(default_factory=dict)
    average_log_time: float = 0.0
    max_log_time: float = 0.0
    log_size_bytes: int = 0
    structured_logs: int = 0
    context_richness: float = 0.0
    error_logs: int = 0
    warning_logs: int = 0


class LogAnalyzer(Protocol):
    """Protocol for log analysis."""
    def analyze_logs(self, log_entries: List[LogEntry]) -> Dict[str, Any]:
        """Analyze log entries and return insights."""
        ...
    
    def detect_patterns(self, log_entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Detect patterns in logs."""
        ...


class TestLoggingFunctionality(unittest.IsolatedAsyncioTestCase):
    """Test cases for logging functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test_logs.json"
        
        # Test configuration
        self.test_config = {
            "log_level": "DEBUG",
            "structured_logging": True,
            "log_filtering": True,
            "performance_tracking": True,
            "log_rotation": True,
            "debug": True
        }
        
        # Create test logger
        self.logger = AstolfoLogger("test_logger", log_file=self.log_file)
        
        # Log scenarios
        self.log_scenarios = [
            LogScenario(
                name="Debug message",
                log_level=LogLevel.DEBUG,
                message="Debug information",
                context={"component": "test", "operation": "setup"},
                expected_output={"level": "DEBUG", "message": "Debug information"},
                should_log=True
            ),
            LogScenario(
                name="Info with context",
                log_level=LogLevel.INFO,
                message="Operation completed",
                context={
                    "duration": 1.23,
                    "records_processed": 100,
                    "success_rate": 0.98
                },
                expected_output={"level": "INFO", "has_context": True},
                should_log=True
            ),
            LogScenario(
                name="Warning with error details",
                log_level=LogLevel.WARNING,
                message="Retry attempt failed",
                context={
                    "attempt": 2,
                    "max_attempts": 3,
                    "error": "Connection timeout"
                },
                expected_output={"level": "WARNING", "has_error": True},
                should_log=True
            ),
            LogScenario(
                name="Error with traceback",
                log_level=LogLevel.ERROR,
                message="Critical operation failed",
                context={
                    "error_type": "DatabaseError",
                    "traceback": "Full traceback here...",
                    "recovery_attempted": True
                },
                expected_output={"level": "ERROR", "has_traceback": True},
                should_log=True
            ),
            LogScenario(
                name="Filtered debug",
                log_level=LogLevel.DEBUG,
                message="Sensitive data: password=secret123",
                context={"contains_sensitive": True},
                expected_output={"should_be_filtered": True},
                should_log=False  # Should be filtered
            )
        ]
        
        # Log metrics
        self.log_metrics = LogMetrics()
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir)
    
    async def test_astolfo_logger_coverage(self) -> None:
        """Test AstolfoLogger coverage across the codebase."""
        with patch('src.utils.astolfo_logger.AstolfoLogger') as mock_logger_class:
            # Track logger usage across modules
            logger_usage = {
                "discord_notifier": [],
                "http_client": [],
                "discord_sender": [],
                "thread_manager": [],
                "thread_storage": [],
                "formatters": [],
                "validators": [],
                "config": []
            }
            
            # Mock logger instance
            mock_logger = MagicMock()
            mock_logger_class.return_value = mock_logger
            
            # Test module imports and logger usage
            modules_to_test = [
                ("src.discord_notifier", "discord_notifier"),
                ("src.core.http_client", "http_client"),
                ("src.handlers.discord_sender", "discord_sender"),
                ("src.handlers.thread_manager", "thread_manager"),
                ("src.thread_storage", "thread_storage"),
                ("src.formatters.event_formatters", "formatters"),
                ("src.validators", "validators"),
                ("src.core.config", "config")
            ]
            
            coverage_results = []
            
            for module_path, category in modules_to_test:
                try:
                    # Check if module uses AstolfoLogger
                    module_file = Path(project_root) / f"{module_path.replace('.', '/')}.py"
                    if module_file.exists():
                        with open(module_file, 'r') as f:
                            content = f.read()
                            
                            # Check for AstolfoLogger usage
                            has_import = "from src.utils.astolfo_logger import AstolfoLogger" in content or \
                                       "from utils.astolfo_logger import AstolfoLogger" in content or \
                                       "import astolfo_logger" in content
                            
                            logger_instances = re.findall(r'AstolfoLogger\(["\']([^"\']+)["\']', content)
                            log_calls = {
                                "debug": len(re.findall(r'\.debug\(', content)),
                                "info": len(re.findall(r'\.info\(', content)),
                                "warning": len(re.findall(r'\.warning\(', content)),
                                "error": len(re.findall(r'\.error\(', content))
                            }
                            
                            coverage_results.append({
                                "module": module_path,
                                "category": category,
                                "has_logger": has_import,
                                "logger_instances": logger_instances,
                                "log_calls": log_calls,
                                "total_log_calls": sum(log_calls.values()),
                                "uses_structured_logging": "context=" in content
                            })
                            
                            if has_import:
                                logger_usage[category].extend(logger_instances)
                
                except Exception as e:
                    coverage_results.append({
                        "module": module_path,
                        "category": category,
                        "error": str(e)
                    })
            
            # Calculate coverage metrics
            total_modules = len(coverage_results)
            modules_with_logger = sum(1 for r in coverage_results if r.get("has_logger", False))
            coverage_percentage = modules_with_logger / total_modules * 100 if total_modules > 0 else 0
            
            # Test structured logging usage
            structured_logging_count = sum(1 for r in coverage_results if r.get("uses_structured_logging", False))
            
            # Test log levels distribution
            log_level_distribution = {
                "debug": sum(r.get("log_calls", {}).get("debug", 0) for r in coverage_results),
                "info": sum(r.get("log_calls", {}).get("info", 0) for r in coverage_results),
                "warning": sum(r.get("log_calls", {}).get("warning", 0) for r in coverage_results),
                "error": sum(r.get("log_calls", {}).get("error", 0) for r in coverage_results)
            }
            
            # Test logger initialization patterns
            initialization_patterns = {
                "module_name": 0,
                "custom_name": 0,
                "with_config": 0
            }
            
            for result in coverage_results:
                for instance in result.get("logger_instances", []):
                    if instance == "__name__":
                        initialization_patterns["module_name"] += 1
                    elif "config" in instance.lower():
                        initialization_patterns["with_config"] += 1
                    else:
                        initialization_patterns["custom_name"] += 1
            
            # Log AstolfoLogger coverage analysis
            self.logger.info(
                "AstolfoLogger coverage analysis",
                context={
                    "total_modules": total_modules,
                    "modules_with_logger": modules_with_logger,
                    "coverage_percentage": coverage_percentage,
                    "structured_logging_modules": structured_logging_count,
                    "log_level_distribution": log_level_distribution,
                    "initialization_patterns": initialization_patterns,
                    "category_coverage": {
                        category: len(instances) > 0
                        for category, instances in logger_usage.items()
                    }
                }
            )
            
            # Assert minimum coverage
            self.assertGreaterEqual(coverage_percentage, 60, "AstolfoLogger coverage should be at least 60%")
            self.assertGreater(structured_logging_count, 0, "At least some modules should use structured logging")
    
    async def test_structured_logging(self) -> None:
        """Test structured logging capabilities."""
        # Test structured log entry creation
        structured_logs = []
        
        # Test various structured logging scenarios
        test_cases = [
            # Simple structured log
            {
                "message": "User action",
                "context": {
                    "user_id": "123",
                    "action": "login",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            # Nested structure
            {
                "message": "API request",
                "context": {
                    "request": {
                        "method": "POST",
                        "endpoint": "/api/messages",
                        "headers": {"Authorization": "Bearer ***"}
                    },
                    "response": {
                        "status": 200,
                        "duration_ms": 145,
                        "size_bytes": 2048
                    }
                }
            },
            # Error with details
            {
                "message": "Operation failed",
                "context": {
                    "error": {
                        "type": "ValidationError",
                        "message": "Invalid input",
                        "field": "email",
                        "value": "[REDACTED]"
                    },
                    "recovery": {
                        "attempted": True,
                        "strategy": "default_value",
                        "success": True
                    }
                }
            },
            # Performance metrics
            {
                "message": "Batch processing complete",
                "context": {
                    "performance": {
                        "total_items": 1000,
                        "processed": 998,
                        "failed": 2,
                        "duration_seconds": 45.3,
                        "items_per_second": 22.03
                    },
                    "memory": {
                        "start_mb": 256,
                        "peak_mb": 512,
                        "end_mb": 280
                    }
                }
            }
        ]
        
        # Log each test case
        for test_case in test_cases:
            # Use actual logger to create structured log
            self.logger.info(test_case["message"], context=test_case["context"])
            
            # Track structured log
            structured_logs.append({
                "message": test_case["message"],
                "context": test_case["context"],
                "timestamp": datetime.now(timezone.utc)
            })
        
        # Test log serialization
        serialization_tests = [
            # JSON serialization
            {
                "format": "json",
                "test": lambda log: json.dumps({"message": log["message"], "context": log["context"]})
            },
            # Custom serialization with filtering
            {
                "format": "filtered_json",
                "test": lambda log: json.dumps(self._filter_sensitive_data(log))
            }
        ]
        
        serialization_results = []
        
        for test in serialization_tests:
            try:
                for log in structured_logs:
                    serialized = test["test"](log)
                    serialization_results.append({
                        "format": test["format"],
                        "success": True,
                        "size": len(serialized)
                    })
            except Exception as e:
                serialization_results.append({
                    "format": test["format"],
                    "success": False,
                    "error": str(e)
                })
        
        # Test log querying
        # Read actual log file
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                log_lines = f.readlines()
                
                # Parse JSON logs
                parsed_logs = []
                for line in log_lines:
                    try:
                        parsed_logs.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
                
                # Query examples
                queries = [
                    # Find all errors
                    lambda log: log.get("level") == "ERROR",
                    # Find logs with specific context
                    lambda log: "user_id" in log.get("context", {}),
                    # Find performance-related logs
                    lambda log: "performance" in log.get("context", {})
                ]
                
                query_results = []
                for i, query in enumerate(queries):
                    matching_logs = [log for log in parsed_logs if query(log)]
                    query_results.append({
                        "query_index": i,
                        "matches": len(matching_logs),
                        "total_logs": len(parsed_logs)
                    })
        
        # Calculate structured logging metrics
        total_structured = len(structured_logs)
        avg_context_depth = sum(self._calculate_context_depth(log["context"]) for log in structured_logs) / total_structured
        avg_context_keys = sum(self._count_context_keys(log["context"]) for log in structured_logs) / total_structured
        
        # Log structured logging analysis
        self.logger.info(
            "Structured logging analysis",
            context={
                "total_structured_logs": total_structured,
                "average_context_depth": avg_context_depth,
                "average_context_keys": avg_context_keys,
                "serialization_results": serialization_results,
                "query_results": query_results if 'query_results' in locals() else [],
                "log_formats_tested": len(serialization_tests)
            }
        )
    
    async def test_log_filtering_and_levels(self) -> None:
        """Test log filtering and level control."""
        # Test log level filtering
        log_level_tests = []
        
        # Test each log level
        for level in [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]:
            # Create logger with specific level
            level_logger = AstolfoLogger(f"test_level_{level.value}", level=level)
            
            # Test logging at each level
            test_results = {
                "configured_level": level.value,
                "logged_messages": {}
            }
            
            # Capture logs
            with self._capture_logs(level_logger) as captured:
                # Log at each level
                level_logger.debug("Debug message")
                level_logger.info("Info message")
                level_logger.warning("Warning message")
                level_logger.error("Error message")
                
                # Check which messages were logged
                for log_level in ["debug", "info", "warning", "error"]:
                    test_results["logged_messages"][log_level] = f"{log_level.title()} message" in captured.getvalue()
            
            log_level_tests.append(test_results)
        
        # Test content filtering
        filter_tests = [
            # Sensitive data filter
            {
                "name": "password_filter",
                "filter": lambda msg, ctx: not any(word in msg.lower() for word in ["password", "secret", "token"]),
                "test_messages": [
                    ("User logged in", {}, True),  # Should log
                    ("Password: secret123", {}, False),  # Should not log
                    ("API token refreshed", {}, False),  # Should not log
                    ("Configuration loaded", {"has_secrets": True}, True)  # Context doesn't affect message filter
                ]
            },
            # Context-based filter
            {
                "name": "context_filter",
                "filter": lambda msg, ctx: not ctx.get("internal_only", False),
                "test_messages": [
                    ("Public message", {}, True),
                    ("Internal metrics", {"internal_only": True}, False),
                    ("Debug info", {"internal_only": False}, True)
                ]
            },
            # Severity filter
            {
                "name": "severity_filter",
                "filter": lambda msg, ctx: ctx.get("severity", 0) >= 5,
                "test_messages": [
                    ("Low priority", {"severity": 1}, False),
                    ("Medium priority", {"severity": 5}, True),
                    ("High priority", {"severity": 9}, True)
                ]
            }
        ]
        
        filter_results = []
        
        for filter_test in filter_tests:
            # Create logger with filter
            filtered_logger = AstolfoLogger(f"test_filter_{filter_test['name']}")
            
            # Apply filter (in practice, this would be done through configuration)
            filter_result = {
                "filter_name": filter_test["name"],
                "test_results": []
            }
            
            for message, context, should_log in filter_test["test_messages"]:
                # Simulate filter application
                would_log = filter_test["filter"](message, context)
                
                filter_result["test_results"].append({
                    "message": message,
                    "context": context,
                    "expected": should_log,
                    "actual": would_log,
                    "passed": would_log == should_log
                })
            
            filter_results.append(filter_result)
        
        # Test dynamic level adjustment
        dynamic_logger = AstolfoLogger("test_dynamic")
        dynamic_tests = []
        
        # Test changing log levels
        level_changes = [
            (LogLevel.INFO, ["debug", "info", "warning", "error"], ["info", "warning", "error"]),
            (LogLevel.WARNING, ["debug", "info", "warning", "error"], ["warning", "error"]),
            (LogLevel.DEBUG, ["debug", "info", "warning", "error"], ["debug", "info", "warning", "error"])
        ]
        
        for new_level, test_levels, expected_logged in level_changes:
            dynamic_logger.set_level(new_level)
            
            with self._capture_logs(dynamic_logger) as captured:
                for level in test_levels:
                    getattr(dynamic_logger, level)(f"{level} message")
                
                logged_output = captured.getvalue()
                actually_logged = [level for level in test_levels if f"{level} message" in logged_output.lower()]
                
                dynamic_tests.append({
                    "set_level": new_level.value,
                    "expected_logged": expected_logged,
                    "actually_logged": actually_logged,
                    "passed": set(actually_logged) == set(expected_logged)
                })
        
        # Calculate filtering metrics
        total_filter_tests = sum(len(f["test_results"]) for f in filter_results)
        passed_filter_tests = sum(1 for f in filter_results for r in f["test_results"] if r["passed"])
        filter_accuracy = passed_filter_tests / total_filter_tests if total_filter_tests > 0 else 0
        
        # Log filtering analysis
        self.logger.info(
            "Log filtering and levels analysis",
            context={
                "log_level_tests": log_level_tests,
                "filter_tests_count": len(filter_tests),
                "filter_accuracy": filter_accuracy,
                "dynamic_level_tests": dynamic_tests,
                "filters_tested": [f["filter_name"] for f in filter_results],
                "level_control_working": all(t["passed"] for t in dynamic_tests)
            }
        )
    
    async def test_logging_performance_impact(self) -> None:
        """Test logging performance impact."""
        # Performance test scenarios
        performance_scenarios = [
            {
                "name": "Simple logging",
                "iterations": 1000,
                "log_func": lambda i: self.logger.info(f"Simple message {i}")
            },
            {
                "name": "Structured logging",
                "iterations": 1000,
                "log_func": lambda i: self.logger.info(
                    "Structured message",
                    context={
                        "iteration": i,
                        "data": {"value": i * 2, "squared": i ** 2},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )
            },
            {
                "name": "Heavy context logging",
                "iterations": 100,
                "log_func": lambda i: self.logger.info(
                    "Heavy context",
                    context={
                        "large_data": {
                            f"key_{j}": {
                                "value": j * i,
                                "metadata": {"index": j, "group": i}
                            }
                            for j in range(50)
                        }
                    }
                )
            },
            {
                "name": "Error logging with traceback",
                "iterations": 100,
                "log_func": lambda i: self.logger.error(
                    f"Error {i}",
                    error=Exception(f"Test error {i}"),
                    traceback="Simulated traceback\n" * 10
                )
            }
        ]
        
        performance_results = []
        
        for scenario in performance_scenarios:
            # Measure baseline (no logging)
            baseline_start = time.perf_counter()
            for i in range(scenario["iterations"]):
                # Simulate work without logging
                _ = f"Message {i}"
            baseline_end = time.perf_counter()
            baseline_time = baseline_end - baseline_start
            
            # Measure with logging
            logging_start = time.perf_counter()
            for i in range(scenario["iterations"]):
                scenario["log_func"](i)
            logging_end = time.perf_counter()
            logging_time = logging_end - logging_start
            
            # Calculate metrics
            overhead = logging_time - baseline_time
            overhead_percentage = (overhead / baseline_time * 100) if baseline_time > 0 else 0
            per_log_overhead = overhead / scenario["iterations"]
            
            performance_results.append({
                "scenario": scenario["name"],
                "iterations": scenario["iterations"],
                "baseline_time": baseline_time,
                "logging_time": logging_time,
                "overhead": overhead,
                "overhead_percentage": overhead_percentage,
                "per_log_overhead_ms": per_log_overhead * 1000
            })
        
        # Test concurrent logging performance
        concurrent_results = await self._test_concurrent_logging_performance()
        
        # Test log file I/O impact
        io_impact_test = await self._test_log_io_impact()
        
        # Test memory impact
        memory_impact = {
            "before_logging": self._get_memory_usage(),
            "after_simple": 0,
            "after_structured": 0,
            "after_heavy": 0
        }
        
        # Simple logging memory test
        for i in range(1000):
            self.logger.info(f"Memory test {i}")
        memory_impact["after_simple"] = self._get_memory_usage()
        
        # Structured logging memory test
        for i in range(1000):
            self.logger.info("Memory test", context={"index": i, "data": [i] * 10})
        memory_impact["after_structured"] = self._get_memory_usage()
        
        # Heavy logging memory test
        for i in range(100):
            self.logger.info("Memory test", context={"large": "x" * 1000})
        memory_impact["after_heavy"] = self._get_memory_usage()
        
        # Calculate performance metrics
        avg_overhead_percentage = sum(r["overhead_percentage"] for r in performance_results) / len(performance_results)
        max_per_log_overhead = max(r["per_log_overhead_ms"] for r in performance_results)
        
        # Log performance analysis
        self.logger.info(
            "Logging performance impact analysis",
            context={
                "scenarios_tested": len(performance_scenarios),
                "average_overhead_percentage": avg_overhead_percentage,
                "max_per_log_overhead_ms": max_per_log_overhead,
                "performance_results": performance_results,
                "concurrent_performance": concurrent_results,
                "io_impact": io_impact_test,
                "memory_impact": memory_impact,
                "acceptable_overhead": avg_overhead_percentage < 10  # Less than 10% overhead
            }
        )
    
    async def test_log_analysis_capabilities(self) -> None:
        """Test log analysis and querying capabilities."""
        # Generate diverse log data
        await self._generate_test_logs()
        
        # Test log analysis features
        analysis_results = {}
        
        # 1. Pattern detection
        patterns = self._detect_log_patterns()
        analysis_results["patterns"] = patterns
        
        # 2. Error clustering
        error_clusters = self._cluster_errors()
        analysis_results["error_clusters"] = error_clusters
        
        # 3. Performance anomaly detection
        performance_anomalies = self._detect_performance_anomalies()
        analysis_results["performance_anomalies"] = performance_anomalies
        
        # 4. Log volume analysis
        volume_analysis = self._analyze_log_volume()
        analysis_results["volume_analysis"] = volume_analysis
        
        # 5. Context correlation
        context_correlations = self._find_context_correlations()
        analysis_results["context_correlations"] = context_correlations
        
        # Test log querying
        query_tests = [
            # Time-based queries
            {
                "name": "Last hour logs",
                "query": lambda log: (datetime.now(timezone.utc) - 
                                    datetime.fromisoformat(log.get("timestamp", "").replace("Z", "+00:00"))) < timedelta(hours=1)
            },
            # Level-based queries
            {
                "name": "Errors and warnings",
                "query": lambda log: log.get("level") in ["ERROR", "WARNING"]
            },
            # Context-based queries
            {
                "name": "High duration operations",
                "query": lambda log: log.get("context", {}).get("duration", 0) > 1.0
            },
            # Pattern matching
            {
                "name": "Failed operations",
                "query": lambda log: "failed" in log.get("message", "").lower() or 
                                   log.get("context", {}).get("success") is False
            }
        ]
        
        query_results = []
        
        # Read and parse logs
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                all_logs = [json.loads(line) for line in f if line.strip()]
            
            for query_test in query_tests:
                matching_logs = [log for log in all_logs if query_test["query"](log)]
                query_results.append({
                    "query_name": query_test["name"],
                    "total_logs": len(all_logs),
                    "matching_logs": len(matching_logs),
                    "match_percentage": len(matching_logs) / len(all_logs) * 100 if all_logs else 0
                })
        
        # Test log aggregation
        aggregation_results = self._test_log_aggregation()
        
        # Test log export formats
        export_tests = [
            ("json", self._export_logs_json),
            ("csv", self._export_logs_csv),
            ("compressed", self._export_logs_compressed)
        ]
        
        export_results = []
        for format_name, export_func in export_tests:
            try:
                export_size = export_func()
                export_results.append({
                    "format": format_name,
                    "success": True,
                    "size_bytes": export_size
                })
            except Exception as e:
                export_results.append({
                    "format": format_name,
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate analysis metrics
        total_patterns = len(patterns.get("patterns", []))
        total_anomalies = len(performance_anomalies.get("anomalies", []))
        query_efficiency = sum(r["match_percentage"] for r in query_results) / len(query_results) if query_results else 0
        
        # Log analysis capabilities
        self.logger.info(
            "Log analysis capabilities",
            context={
                "patterns_detected": total_patterns,
                "error_clusters": len(error_clusters.get("clusters", [])),
                "performance_anomalies": total_anomalies,
                "query_tests_run": len(query_tests),
                "average_query_efficiency": query_efficiency,
                "export_formats_supported": len([r for r in export_results if r["success"]]),
                "aggregation_metrics": aggregation_results,
                "analysis_features": list(analysis_results.keys())
            }
        )
    
    # Helper methods
    
    @contextmanager
    def _capture_logs(self, logger: AstolfoLogger):
        """Capture logger output."""
        # Create StringIO to capture output
        string_buffer = io.StringIO()
        
        # Temporarily redirect logger output
        original_handlers = logger._logger.handlers[:]
        logger._logger.handlers = []
        
        # Add StringIO handler
        handler = logging.StreamHandler(string_buffer)
        handler.setLevel(logging.DEBUG)
        logger._logger.addHandler(handler)
        
        try:
            yield string_buffer
        finally:
            # Restore original handlers
            logger._logger.handlers = original_handlers
    
    def _filter_sensitive_data(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from log entry."""
        filtered = log_entry.copy()
        
        # Filter sensitive keys
        sensitive_keys = ["password", "token", "secret", "key", "auth"]
        
        def filter_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            filtered_dict = {}
            for k, v in d.items():
                if any(sensitive in k.lower() for sensitive in sensitive_keys):
                    filtered_dict[k] = "[REDACTED]"
                elif isinstance(v, dict):
                    filtered_dict[k] = filter_dict(v)
                else:
                    filtered_dict[k] = v
            return filtered_dict
        
        if "context" in filtered and isinstance(filtered["context"], dict):
            filtered["context"] = filter_dict(filtered["context"])
        
        return filtered
    
    def _calculate_context_depth(self, context: Dict[str, Any], depth: int = 0) -> int:
        """Calculate maximum depth of context dictionary."""
        if not isinstance(context, dict):
            return depth
        
        max_depth = depth
        for value in context.values():
            if isinstance(value, dict):
                max_depth = max(max_depth, self._calculate_context_depth(value, depth + 1))
        
        return max_depth
    
    def _count_context_keys(self, context: Dict[str, Any]) -> int:
        """Count total keys in context dictionary."""
        if not isinstance(context, dict):
            return 0
        
        count = len(context)
        for value in context.values():
            if isinstance(value, dict):
                count += self._count_context_keys(value)
        
        return count
    
    async def _test_concurrent_logging_performance(self) -> Dict[str, Any]:
        """Test logging performance under concurrent load."""
        results = {
            "threads": 10,
            "logs_per_thread": 100,
            "total_time": 0,
            "conflicts": 0
        }
        
        start_time = time.perf_counter()
        threads = []
        
        def thread_logging(thread_id: int):
            for i in range(results["logs_per_thread"]):
                self.logger.info(
                    f"Thread {thread_id} log {i}",
                    context={"thread_id": thread_id, "index": i}
                )
        
        # Start threads
        for i in range(results["threads"]):
            thread = threading.Thread(target=thread_logging, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        results["total_time"] = time.perf_counter() - start_time
        results["logs_per_second"] = (results["threads"] * results["logs_per_thread"]) / results["total_time"]
        
        return results
    
    async def _test_log_io_impact(self) -> Dict[str, Any]:
        """Test I/O impact of logging."""
        results = {
            "sync_writes": 0,
            "buffered_writes": 0,
            "io_wait_time": 0
        }
        
        # Test synchronous writes
        sync_start = time.perf_counter()
        for i in range(100):
            self.logger.info(f"Sync write {i}")
            # Force flush
            for handler in self.logger._logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
        results["sync_writes"] = time.perf_counter() - sync_start
        
        # Test buffered writes
        buffered_start = time.perf_counter()
        for i in range(100):
            self.logger.info(f"Buffered write {i}")
        results["buffered_writes"] = time.perf_counter() - buffered_start
        
        results["io_improvement"] = (results["sync_writes"] - results["buffered_writes"]) / results["sync_writes"] * 100
        
        return results
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss
    
    async def _generate_test_logs(self) -> None:
        """Generate diverse test logs for analysis."""
        # Generate various log patterns
        for i in range(100):
            # Normal operation logs
            self.logger.info(
                "Operation completed",
                context={
                    "operation_id": f"op_{i}",
                    "duration": 0.5 + (i % 10) * 0.1,
                    "success": i % 10 != 0
                }
            )
            
            # Error logs
            if i % 10 == 0:
                self.logger.error(
                    "Operation failed",
                    error=f"Error type {i % 3}",
                    context={
                        "operation_id": f"op_{i}",
                        "retry_count": i % 3,
                        "error_code": f"ERR_{i % 5}"
                    }
                )
            
            # Performance logs
            if i % 5 == 0:
                self.logger.info(
                    "Performance metric",
                    context={
                        "metric": "response_time",
                        "value": 100 + i * 10,
                        "threshold": 1000
                    }
                )
    
    def _detect_log_patterns(self) -> Dict[str, Any]:
        """Detect patterns in logs."""
        patterns = {
            "patterns": [],
            "frequency": {}
        }
        
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                logs = [json.loads(line) for line in f if line.strip()]
            
            # Detect message patterns
            message_counts = {}
            for log in logs:
                msg_pattern = re.sub(r'\d+', 'N', log.get("message", ""))
                message_counts[msg_pattern] = message_counts.get(msg_pattern, 0) + 1
            
            # Find frequent patterns
            for pattern, count in message_counts.items():
                if count > 5:
                    patterns["patterns"].append({
                        "pattern": pattern,
                        "count": count,
                        "percentage": count / len(logs) * 100
                    })
        
        return patterns
    
    def _cluster_errors(self) -> Dict[str, Any]:
        """Cluster similar errors."""
        clusters = {"clusters": []}
        
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                error_logs = [
                    json.loads(line) 
                    for line in f 
                    if line.strip() and json.loads(line).get("level") == "ERROR"
                ]
            
            # Simple clustering by error type
            error_groups = {}
            for log in error_logs:
                error_type = log.get("context", {}).get("error_code", "UNKNOWN")
                if error_type not in error_groups:
                    error_groups[error_type] = []
                error_groups[error_type].append(log)
            
            for error_type, logs in error_groups.items():
                clusters["clusters"].append({
                    "error_type": error_type,
                    "count": len(logs),
                    "first_occurrence": logs[0].get("timestamp"),
                    "last_occurrence": logs[-1].get("timestamp")
                })
        
        return clusters
    
    def _detect_performance_anomalies(self) -> Dict[str, Any]:
        """Detect performance anomalies in logs."""
        anomalies = {"anomalies": []}
        
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                perf_logs = [
                    json.loads(line)
                    for line in f
                    if line.strip() and "duration" in json.loads(line).get("context", {})
                ]
            
            if perf_logs:
                # Calculate statistics
                durations = [log["context"]["duration"] for log in perf_logs]
                avg_duration = sum(durations) / len(durations)
                
                # Find anomalies (> 2 standard deviations)
                std_dev = (sum((d - avg_duration) ** 2 for d in durations) / len(durations)) ** 0.5
                
                for log in perf_logs:
                    duration = log["context"]["duration"]
                    if abs(duration - avg_duration) > 2 * std_dev:
                        anomalies["anomalies"].append({
                            "timestamp": log.get("timestamp"),
                            "duration": duration,
                            "deviation": (duration - avg_duration) / std_dev
                        })
        
        return anomalies
    
    def _analyze_log_volume(self) -> Dict[str, Any]:
        """Analyze log volume over time."""
        volume = {
            "total_logs": 0,
            "logs_per_level": {},
            "logs_per_hour": {}
        }
        
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                logs = [json.loads(line) for line in f if line.strip()]
            
            volume["total_logs"] = len(logs)
            
            # Count by level
            for log in logs:
                level = log.get("level", "UNKNOWN")
                volume["logs_per_level"][level] = volume["logs_per_level"].get(level, 0) + 1
            
            # Count by hour
            for log in logs:
                timestamp = datetime.fromisoformat(log.get("timestamp", "").replace("Z", "+00:00"))
                hour_key = timestamp.strftime("%Y-%m-%d %H:00")
                volume["logs_per_hour"][hour_key] = volume["logs_per_hour"].get(hour_key, 0) + 1
        
        return volume
    
    def _find_context_correlations(self) -> Dict[str, Any]:
        """Find correlations in log context."""
        correlations = {"correlations": []}
        
        # This would be more sophisticated in a real implementation
        # For now, just return a simple structure
        correlations["correlations"] = [
            {
                "fields": ["operation_id", "error_code"],
                "correlation": 0.85,
                "significance": "high"
            }
        ]
        
        return correlations
    
    def _test_log_aggregation(self) -> Dict[str, Any]:
        """Test log aggregation capabilities."""
        return {
            "aggregation_types": ["count", "sum", "average", "min", "max"],
            "grouping_fields": ["level", "error_code", "operation_id"],
            "time_windows": ["1m", "5m", "1h", "1d"]
        }
    
    def _export_logs_json(self) -> int:
        """Export logs as JSON."""
        if self.log_file.exists():
            export_file = self.log_file.with_suffix('.export.json')
            with open(self.log_file, 'r') as f:
                logs = [json.loads(line) for line in f if line.strip()]
            
            with open(export_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            return export_file.stat().st_size
        return 0
    
    def _export_logs_csv(self) -> int:
        """Export logs as CSV."""
        if self.log_file.exists():
            export_file = self.log_file.with_suffix('.export.csv')
            
            # Simple CSV export (would be more sophisticated in practice)
            with open(export_file, 'w') as f:
                f.write("timestamp,level,message\n")
                
                with open(self.log_file, 'r') as log_f:
                    for line in log_f:
                        if line.strip():
                            log = json.loads(line)
                            f.write(f"{log.get('timestamp','')},{log.get('level','')},{log.get('message','')}\n")
            
            return export_file.stat().st_size
        return 0
    
    def _export_logs_compressed(self) -> int:
        """Export logs as compressed file."""
        if self.log_file.exists():
            export_file = self.log_file.with_suffix('.log.gz')
            
            with open(self.log_file, 'rb') as f_in:
                with gzip.open(export_file, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            return export_file.stat().st_size
        return 0


def run_logging_functionality_tests() -> None:
    """Run logging functionality tests."""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    # For standalone execution
    import asyncio
    
    async def main():
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestLoggingFunctionality)
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Run tests
        result = runner.run(suite)
        
        # Print summary
        print(f"\nLogging Functionality Tests Summary:")
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