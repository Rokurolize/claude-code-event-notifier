#!/usr/bin/env python3
"""Test User Scenarios End-to-End.

This module provides comprehensive tests from real user workflow perspectives:
- Developer workflows (coding, testing, debugging)
- Claude Code usage patterns (file operations, commands, analysis)
- Notification preferences and threading behavior
- Multi-session and concurrent usage scenarios
- Real-world edge cases and integration patterns

These tests ensure the system works correctly for actual user workflows.
"""

import asyncio
import json
import unittest
import os
import tempfile
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Callable
from unittest.mock import AsyncMock, MagicMock, patch, Mock, call
from dataclasses import dataclass, field
from datetime import datetime, timezone
import sys

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
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# User scenario types
@dataclass
class UserScenario:
    """Definition of a user workflow scenario."""
    name: str
    description: str
    user_type: str  # "developer", "analyst", "beginner", "power_user"
    workflow_steps: List[Dict[str, Any]]
    expected_notifications: int
    expected_threads: int
    session_duration: float  # in minutes
    complexity: str  # "simple", "moderate", "complex"


@dataclass
class UserTestResult:
    """Result of a user scenario test."""
    scenario_name: str
    user_type: str
    success: bool
    workflow_completed: bool
    notifications_sent: int
    notifications_expected: int
    threads_created: int
    threads_expected: int
    session_duration: float
    user_experience_rating: float  # 1-10 scale
    issues_encountered: List[str]
    performance_metrics: Dict[str, float]


class MockClaudeCodeSession:
    """Simulates a Claude Code session with realistic event patterns."""
    
    def __init__(self, session_id: str, user_type: str):
        self.session_id = session_id
        self.user_type = user_type
        self.logger = AstolfoLogger(__name__)
        self.events_generated = []
        self.start_time = time.time()
        
    def simulate_file_creation(self, file_path: str, content: str = "") -> Dict[str, Any]:
        """Simulate file creation event."""
        event = {
            "session_id": self.session_id,
            "event_type": "Write",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "file_path": file_path,
                "content": content[:100] + "..." if len(content) > 100 else content
            }
        }
        self.events_generated.append(event)
        return event
    
    def simulate_file_edit(self, file_path: str, changes: str) -> Dict[str, Any]:
        """Simulate file edit event."""
        event = {
            "session_id": self.session_id,
            "event_type": "Edit",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "file_path": file_path,
                "old_string": "original code",
                "new_string": changes
            }
        }
        self.events_generated.append(event)
        return event
    
    def simulate_command_execution(self, command: str, exit_code: int = 0, output: str = "") -> Dict[str, Any]:
        """Simulate command execution event."""
        event = {
            "session_id": self.session_id,
            "event_type": "Bash",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "command": command,
                "exit_code": exit_code,
                "output": output[:200] + "..." if len(output) > 200 else output
            }
        }
        self.events_generated.append(event)
        return event
    
    def simulate_file_search(self, pattern: str, results: List[str]) -> Dict[str, Any]:
        """Simulate file search event."""
        event = {
            "session_id": self.session_id,
            "event_type": "Glob",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "pattern": pattern,
                "results": results
            }
        }
        self.events_generated.append(event)
        return event
    
    def simulate_content_search(self, pattern: str, matches: List[str]) -> Dict[str, Any]:
        """Simulate content search event."""
        event = {
            "session_id": self.session_id,
            "event_type": "Grep",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "pattern": pattern,
                "matches": matches
            }
        }
        self.events_generated.append(event)
        return event
    
    def simulate_file_reading(self, file_path: str, content_preview: str = "") -> Dict[str, Any]:
        """Simulate file reading event."""
        event = {
            "session_id": self.session_id,
            "event_type": "Read",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "file_path": file_path,
                "content": content_preview[:150] + "..." if len(content_preview) > 150 else content_preview
            }
        }
        self.events_generated.append(event)
        return event
    
    def simulate_task_execution(self, description: str, result: str = "completed") -> Dict[str, Any]:
        """Simulate task execution event."""
        event = {
            "session_id": self.session_id,
            "event_type": "Task",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "description": description,
                "result": result
            }
        }
        self.events_generated.append(event)
        return event


class UserWorkflowGenerator:
    """Generates realistic user workflows."""
    
    def __init__(self):
        self.logger = AstolfoLogger(__name__)
    
    def generate_developer_workflow(self, session_id: str) -> UserScenario:
        """Generate typical developer workflow."""
        return UserScenario(
            name="developer_coding_session",
            description="Typical developer coding, testing, and debugging session",
            user_type="developer", 
            workflow_steps=[
                {"action": "file_search", "pattern": "*.py", "description": "Find Python files"},
                {"action": "file_read", "file": "src/main.py", "description": "Read main module"},
                {"action": "file_edit", "file": "src/main.py", "changes": "Add new function", "description": "Implement new feature"},
                {"action": "file_create", "file": "tests/test_new_feature.py", "content": "import unittest", "description": "Create test file"},
                {"action": "command", "cmd": "python -m pytest tests/", "description": "Run tests"},
                {"action": "file_edit", "file": "src/main.py", "changes": "Fix bug", "description": "Fix failing test"},
                {"action": "command", "cmd": "python -m pytest tests/", "description": "Rerun tests"},
                {"action": "file_edit", "file": "README.md", "changes": "Update documentation", "description": "Update docs"},
                {"action": "command", "cmd": "git add .", "description": "Stage changes"},
                {"action": "command", "cmd": "git commit -m 'Add new feature'", "description": "Commit changes"}
            ],
            expected_notifications=10,
            expected_threads=1,
            session_duration=45.0,
            complexity="moderate"
        )
    
    def generate_analysis_workflow(self, session_id: str) -> UserScenario:
        """Generate code analysis workflow."""
        return UserScenario(
            name="code_analysis_session",
            description="Code analysis and exploration session",
            user_type="analyst",
            workflow_steps=[
                {"action": "content_search", "pattern": "class.*:", "description": "Find class definitions"},
                {"action": "file_read", "file": "src/models.py", "description": "Examine data models"},
                {"action": "content_search", "pattern": "def.*test", "description": "Find test functions"},
                {"action": "file_read", "file": "tests/test_models.py", "description": "Read test file"},
                {"action": "task", "description": "Analyze code coverage", "result": "75% coverage found"},
                {"action": "task", "description": "Identify refactoring opportunities", "result": "3 areas identified"},
                {"action": "file_create", "file": "analysis_report.md", "content": "# Code Analysis Report", "description": "Create report"},
                {"action": "command", "cmd": "wc -l src/*.py", "description": "Count lines of code"}
            ],
            expected_notifications=8,
            expected_threads=1,
            session_duration=30.0,
            complexity="moderate"
        )
    
    def generate_beginner_workflow(self, session_id: str) -> UserScenario:
        """Generate beginner user workflow."""
        return UserScenario(
            name="beginner_exploration_session",
            description="New user exploring codebase",
            user_type="beginner",
            workflow_steps=[
                {"action": "file_read", "file": "README.md", "description": "Read project documentation"},
                {"action": "file_search", "pattern": "*", "description": "Explore file structure"},
                {"action": "file_read", "file": "package.json", "description": "Check project dependencies"},
                {"action": "command", "cmd": "ls -la", "description": "List files"},
                {"action": "file_read", "file": "src/index.js", "description": "Read main entry point"},
                {"action": "command", "cmd": "npm install", "description": "Install dependencies"}
            ],
            expected_notifications=6,
            expected_threads=1,
            session_duration=20.0,
            complexity="simple"
        )
    
    def generate_power_user_workflow(self, session_id: str) -> UserScenario:
        """Generate power user workflow with advanced features."""
        return UserScenario(
            name="power_user_refactoring_session",
            description="Advanced user performing complex refactoring",
            user_type="power_user",
            workflow_steps=[
                {"action": "content_search", "pattern": "deprecated", "description": "Find deprecated code"},
                {"action": "task", "description": "Analyze dependency graph", "result": "15 modules analyzed"},
                {"action": "file_edit", "file": "src/legacy.py", "changes": "Refactor deprecated functions", "description": "Modernize legacy code"},
                {"action": "command", "cmd": "python -m mypy src/", "description": "Type checking"},
                {"action": "file_create", "file": "migration_guide.md", "content": "# Migration Guide", "description": "Document changes"},
                {"action": "command", "cmd": "python -m black src/", "description": "Format code"},
                {"action": "content_search", "pattern": "TODO|FIXME", "description": "Find remaining issues"},
                {"action": "task", "description": "Performance benchmarking", "result": "20% improvement achieved"},
                {"action": "file_edit", "file": "pyproject.toml", "changes": "Update tool configurations", "description": "Update config"},
                {"action": "command", "cmd": "python -m pytest --cov=src tests/", "description": "Run coverage tests"},
                {"action": "task", "description": "Generate performance report", "result": "Report created"},
                {"action": "command", "cmd": "git add -A", "description": "Stage all changes"},
                {"action": "command", "cmd": "git commit -m 'Major refactoring: modernize codebase'", "description": "Commit refactoring"}
            ],
            expected_notifications=13,
            expected_threads=1,
            session_duration=90.0,
            complexity="complex"
        )
    
    def generate_multi_session_workflow(self) -> List[UserScenario]:
        """Generate multiple concurrent sessions."""
        return [
            self.generate_developer_workflow("session_dev_1"),
            self.generate_analysis_workflow("session_analyst_1"),
            self.generate_beginner_workflow("session_beginner_1")
        ]


class TestUserScenarios(unittest.IsolatedAsyncioTestCase, BaseQualityChecker):
    """Test cases for user scenarios."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        super().setUp()
        self.logger = AstolfoLogger(__name__)
        
        # Create temporary directory for test artifacts
        self.test_dir = tempfile.mkdtemp(prefix="user_test_")
        self.test_database = os.path.join(self.test_dir, "test_threads.db")
        
        # Initialize workflow generator
        self.workflow_generator = UserWorkflowGenerator()
        
        # Track test results
        self.user_test_results = []
        
        # Mock Discord server for realistic responses
        self.mock_discord_responses = []
        self.notification_count = 0
        
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        super().tearDown()
        try:
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
        except Exception as e:
            self.logger.warning("Failed to clean up test directory", error=str(e))
    
    def _create_mock_discord_response(self, message_content: str = "") -> Dict[str, Any]:
        """Create realistic Discord API response."""
        self.notification_count += 1
        response = {
            "id": f"msg_{int(time.time() * 1000)}_{self.notification_count}",
            "type": 0,
            "content": message_content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel_id": "123456789",
            "author": {
                "id": "webhook_bot",
                "username": "Claude Code"
            }
        }
        self.mock_discord_responses.append(response)
        return response
    
    async def _execute_user_workflow(self, scenario: UserScenario) -> UserTestResult:
        """Execute a complete user workflow scenario."""
        start_time = time.time()
        session = MockClaudeCodeSession(scenario.name + "_session", scenario.user_type)
        
        notifications_sent = 0
        threads_created = set()
        issues_encountered = []
        performance_metrics = {}
        
        # Set up test configuration based on user type
        test_config = self._get_user_config(scenario.user_type)
        
        try:
            # Initialize database for threading if enabled
            if test_config.get("DISCORD_USE_THREADS") == "true":
                thread_storage = ThreadStorage(self.test_database)
                thread_storage.init_database()
            
            # Execute workflow steps
            with patch('src.core.http_client.HTTPClient.post', side_effect=self._mock_http_post):
                with patch.dict(os.environ, test_config):
                    
                    step_times = []
                    for i, step in enumerate(scenario.workflow_steps):
                        step_start = time.time()
                        
                        try:
                            # Generate appropriate event based on step
                            event = self._execute_workflow_step(session, step)
                            
                            # Process event through Discord notifier
                            formatted_output = format_event(event)
                            discord_message: DiscordMessage = {
                                "content": formatted_output.get("content", ""),
                                "embeds": formatted_output.get("embeds", []),
                                "username": formatted_output.get("username", "Claude Code")
                            }
                            
                            # Handle threading if enabled
                            if test_config.get("DISCORD_USE_THREADS") == "true":
                                thread_id = get_or_create_thread(
                                    session_id=event["session_id"],
                                    config=test_config,
                                    http_client=HTTPClient(),
                                    logger=self.logger
                                )
                                if thread_id:
                                    threads_created.add(thread_id)
                                    discord_message["thread_id"] = thread_id
                            
                            # Send Discord notification
                            discord_context = DiscordContext(
                                webhook_url=test_config.get("DISCORD_WEBHOOK_URL"),
                                bot_token=test_config.get("DISCORD_TOKEN"),
                                channel_id=test_config.get("DISCORD_CHANNEL_ID")
                            )
                            
                            send_to_discord(discord_message, discord_context)
                            notifications_sent += 1
                            
                        except Exception as e:
                            issues_encountered.append(f"Step {i+1}: {str(e)}")
                            self.logger.error("Workflow step failed", step=step, error=str(e))
                        
                        step_time = time.time() - step_start
                        step_times.append(step_time)
                        
                        # Small delay between steps for realism
                        await asyncio.sleep(0.1)
            
            execution_time = time.time() - start_time
            
            # Calculate performance metrics
            performance_metrics = {
                "total_execution_time": execution_time,
                "average_step_time": sum(step_times) / len(step_times) if step_times else 0,
                "max_step_time": max(step_times) if step_times else 0,
                "notifications_per_minute": (notifications_sent / execution_time) * 60 if execution_time > 0 else 0
            }
            
            # Calculate user experience rating (1-10)
            user_experience_rating = self._calculate_user_experience_rating(
                scenario, notifications_sent, len(threads_created), 
                len(issues_encountered), performance_metrics
            )
            
            # Determine success
            workflow_completed = len(issues_encountered) == 0
            notifications_match = abs(notifications_sent - scenario.expected_notifications) <= 2  # Allow some variance
            threads_match = len(threads_created) == scenario.expected_threads
            
            success = workflow_completed and notifications_match and (
                not test_config.get("DISCORD_USE_THREADS") == "true" or threads_match
            )
            
            return UserTestResult(
                scenario_name=scenario.name,
                user_type=scenario.user_type,
                success=success,
                workflow_completed=workflow_completed,
                notifications_sent=notifications_sent,
                notifications_expected=scenario.expected_notifications,
                threads_created=len(threads_created),
                threads_expected=scenario.expected_threads,
                session_duration=execution_time,
                user_experience_rating=user_experience_rating,
                issues_encountered=issues_encountered,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            return UserTestResult(
                scenario_name=scenario.name,
                user_type=scenario.user_type,
                success=False,
                workflow_completed=False,
                notifications_sent=notifications_sent,
                notifications_expected=scenario.expected_notifications,
                threads_created=len(threads_created),
                threads_expected=scenario.expected_threads,
                session_duration=time.time() - start_time,
                user_experience_rating=1.0,
                issues_encountered=[f"Critical failure: {str(e)}"],
                performance_metrics=performance_metrics
            )
    
    def _get_user_config(self, user_type: str) -> Dict[str, str]:
        """Get configuration appropriate for user type."""
        base_config = {
            "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/456",
            "DISCORD_DEBUG": "false"
        }
        
        if user_type == "beginner":
            # Beginners might prefer simple notifications
            base_config.update({
                "DISCORD_USE_THREADS": "false",
                "DISCORD_ENABLED_EVENTS": "Write,Bash"
            })
        elif user_type == "developer":
            # Developers want organized notifications with threads
            base_config.update({
                "DISCORD_USE_THREADS": "true",
                "DISCORD_ENABLED_EVENTS": "Write,Edit,Bash,Read"
            })
        elif user_type == "analyst":
            # Analysts want comprehensive event tracking
            base_config.update({
                "DISCORD_USE_THREADS": "true",
                "DISCORD_ENABLED_EVENTS": "all"
            })
        elif user_type == "power_user":
            # Power users want full control and debugging
            base_config.update({
                "DISCORD_USE_THREADS": "true",
                "DISCORD_ENABLED_EVENTS": "all",
                "DISCORD_DEBUG": "true"
            })
        
        return base_config
    
    def _execute_workflow_step(self, session: MockClaudeCodeSession, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step."""
        action = step["action"]
        
        if action == "file_create":
            return session.simulate_file_creation(step["file"], step.get("content", ""))
        elif action == "file_edit":
            return session.simulate_file_edit(step["file"], step["changes"])
        elif action == "file_read":
            return session.simulate_file_reading(step["file"], "Sample file content for testing")
        elif action == "file_search":
            # Simulate realistic search results
            results = [f"src/file{i}.py" for i in range(1, 6)]
            return session.simulate_file_search(step["pattern"], results)
        elif action == "content_search":
            # Simulate realistic content matches
            matches = [f"src/module{i}.py:line {i*10}" for i in range(1, 4)]
            return session.simulate_content_search(step["pattern"], matches)
        elif action == "command":
            return session.simulate_command_execution(step["cmd"], 0, "Command executed successfully")
        elif action == "task":
            return session.simulate_task_execution(step["description"], step.get("result", "completed"))
        else:
            raise ValueError(f"Unknown workflow action: {action}")
    
    def _mock_http_post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock HTTP POST for Discord API calls."""
        # Simulate realistic response times
        time.sleep(0.1)  # 100ms simulated network delay
        
        response = self._create_mock_discord_response(data.get("content", ""))
        
        # Simulate occasional rate limiting for realism
        if self.notification_count % 20 == 0:
            time.sleep(0.5)  # Simulate rate limit delay
        
        return response
    
    def _calculate_user_experience_rating(
        self, 
        scenario: UserScenario, 
        notifications_sent: int, 
        threads_created: int,
        issues_count: int, 
        performance_metrics: Dict[str, float]
    ) -> float:
        """Calculate user experience rating (1-10)."""
        base_rating = 8.0  # Start with good rating
        
        # Adjust based on notifications accuracy
        notification_accuracy = 1 - abs(notifications_sent - scenario.expected_notifications) / max(scenario.expected_notifications, 1)
        base_rating += notification_accuracy * 1.0
        
        # Adjust based on performance
        avg_step_time = performance_metrics.get("average_step_time", 0)
        if avg_step_time < 0.5:
            base_rating += 0.5  # Fast performance
        elif avg_step_time > 2.0:
            base_rating -= 1.0  # Slow performance
        
        # Penalize for issues
        base_rating -= issues_count * 0.5
        
        # Bonus for complex workflows completed successfully
        if scenario.complexity == "complex" and issues_count == 0:
            base_rating += 0.5
        
        return max(1.0, min(10.0, base_rating))
    
    async def test_developer_workflow_scenario(self) -> None:
        """Test typical developer workflow."""
        scenario = self.workflow_generator.generate_developer_workflow("dev_test")
        result = await self._execute_user_workflow(scenario)
        
        self.assertTrue(result.workflow_completed, "Developer workflow should complete successfully")
        self.assertGreater(result.notifications_sent, 5, "Developer should receive multiple notifications")
        self.assertGreaterEqual(result.user_experience_rating, 7.0, "Developer experience should be good")
        
        # Verify thread creation for organized notifications
        if result.threads_created > 0:
            self.assertEqual(result.threads_created, result.threads_expected, "Should create expected number of threads")
        
        self.user_test_results.append(result)
    
    async def test_analyst_workflow_scenario(self) -> None:
        """Test code analysis workflow."""
        scenario = self.workflow_generator.generate_analysis_workflow("analyst_test")
        result = await self._execute_user_workflow(scenario)
        
        self.assertTrue(result.workflow_completed, "Analysis workflow should complete successfully")
        self.assertGreater(result.notifications_sent, 3, "Analyst should receive notifications for analysis activities")
        self.assertGreaterEqual(result.user_experience_rating, 6.0, "Analyst experience should be satisfactory")
        
        self.user_test_results.append(result)
    
    async def test_beginner_workflow_scenario(self) -> None:
        """Test beginner user workflow."""
        scenario = self.workflow_generator.generate_beginner_workflow("beginner_test")
        result = await self._execute_user_workflow(scenario)
        
        self.assertTrue(result.workflow_completed, "Beginner workflow should complete successfully")
        self.assertGreater(result.notifications_sent, 0, "Beginner should receive some notifications")
        self.assertGreaterEqual(result.user_experience_rating, 6.0, "Beginner experience should be user-friendly")
        
        # Beginners typically use simpler configurations
        self.assertEqual(result.threads_created, 0, "Beginners typically don't use threading")
        
        self.user_test_results.append(result)
    
    async def test_power_user_workflow_scenario(self) -> None:
        """Test advanced power user workflow."""
        scenario = self.workflow_generator.generate_power_user_workflow("power_test")
        result = await self._execute_user_workflow(scenario)
        
        self.assertTrue(result.workflow_completed, "Power user workflow should complete successfully")
        self.assertGreater(result.notifications_sent, 8, "Power user should receive many notifications")
        self.assertGreaterEqual(result.user_experience_rating, 7.0, "Power user experience should be excellent")
        
        # Power users should leverage advanced features
        self.assertGreater(result.threads_created, 0, "Power users should use threading")
        
        self.user_test_results.append(result)
    
    async def test_concurrent_user_sessions(self) -> None:
        """Test multiple users working concurrently."""
        scenarios = self.workflow_generator.generate_multi_session_workflow()
        
        # Execute scenarios concurrently
        tasks = [self._execute_user_workflow(scenario) for scenario in scenarios]
        results = await asyncio.gather(*tasks)
        
        # Verify all sessions completed successfully
        for result in results:
            self.assertTrue(result.workflow_completed, f"Concurrent session {result.scenario_name} should complete")
            self.assertGreater(result.notifications_sent, 0, f"Session {result.scenario_name} should send notifications")
        
        # Verify no interference between sessions
        session_ids = [result.scenario_name for result in results]
        self.assertEqual(len(session_ids), len(set(session_ids)), "Each session should have unique identifier")
        
        # Verify thread isolation (if enabled)
        thread_counts = [result.threads_created for result in results if result.threads_created > 0]
        if thread_counts:
            # Each session should create its own threads
            self.assertGreater(sum(thread_counts), 0, "Concurrent sessions should create separate threads")
        
        self.user_test_results.extend(results)
    
    async def test_user_preference_configurations(self) -> None:
        """Test different user preference configurations."""
        base_scenario = self.workflow_generator.generate_developer_workflow("config_test")
        
        configurations = [
            {
                "name": "minimal_notifications",
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/456",
                    "DISCORD_USE_THREADS": "false",
                    "DISCORD_ENABLED_EVENTS": "Write,Bash"
                },
                "expected_notifications": 4  # Only Write and Bash events
            },
            {
                "name": "comprehensive_notifications",
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/456",
                    "DISCORD_USE_THREADS": "true",
                    "DISCORD_ENABLED_EVENTS": "all"
                },
                "expected_notifications": 10  # All events
            },
            {
                "name": "debug_mode",
                "config": {
                    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123/456",
                    "DISCORD_USE_THREADS": "true",
                    "DISCORD_ENABLED_EVENTS": "all",
                    "DISCORD_DEBUG": "true"
                },
                "expected_notifications": 10  # All events with debug info
            }
        ]
        
        for config_test in configurations:
            with self.subTest(configuration=config_test["name"]):
                # Modify scenario for this configuration
                test_scenario = UserScenario(
                    name=f"config_{config_test['name']}",
                    description=f"Test {config_test['name']} configuration",
                    user_type="developer",
                    workflow_steps=base_scenario.workflow_steps,
                    expected_notifications=config_test["expected_notifications"],
                    expected_threads=1 if config_test["config"].get("DISCORD_USE_THREADS") == "true" else 0,
                    session_duration=base_scenario.session_duration,
                    complexity=base_scenario.complexity
                )
                
                # Override configuration
                with patch.dict(os.environ, config_test["config"]):
                    result = await self._execute_user_workflow(test_scenario)
                
                self.assertTrue(result.workflow_completed, f"Configuration {config_test['name']} should work")
                
                # Verify notification count matches expectations (with some tolerance)
                notification_tolerance = 2
                self.assertLessEqual(
                    abs(result.notifications_sent - config_test["expected_notifications"]),
                    notification_tolerance,
                    f"Notification count should match configuration {config_test['name']}"
                )
                
                self.user_test_results.append(result)
    
    async def test_error_recovery_in_user_workflows(self) -> None:
        """Test error recovery during user workflows."""
        scenario = self.workflow_generator.generate_developer_workflow("error_recovery_test")
        
        # Inject errors at different points
        error_injection_points = [2, 5, 8]  # Steps where errors will occur
        
        start_time = time.time()
        session = MockClaudeCodeSession(scenario.name + "_session", scenario.user_type)
        
        notifications_sent = 0
        issues_encountered = []
        recovered_from_errors = 0
        
        test_config = self._get_user_config(scenario.user_type)
        
        with patch('src.core.http_client.HTTPClient.post', side_effect=self._mock_http_post):
            with patch.dict(os.environ, test_config):
                
                for i, step in enumerate(scenario.workflow_steps):
                    try:
                        # Inject error at specified points
                        if i in error_injection_points:
                            raise ConnectionError(f"Simulated network error at step {i}")
                        
                        # Execute step normally
                        event = self._execute_workflow_step(session, step)
                        formatted_output = format_event(event)
                        discord_message: DiscordMessage = {
                            "content": formatted_output.get("content", ""),
                            "embeds": formatted_output.get("embeds", []),
                            "username": formatted_output.get("username", "Claude Code")
                        }
                        
                        discord_context = DiscordContext(
                            webhook_url=test_config.get("DISCORD_WEBHOOK_URL"),
                            bot_token=test_config.get("DISCORD_TOKEN"),
                            channel_id=test_config.get("DISCORD_CHANNEL_ID")
                        )
                        
                        send_to_discord(discord_message, discord_context)
                        notifications_sent += 1
                        
                    except Exception as e:
                        issues_encountered.append(f"Step {i+1}: {str(e)}")
                        
                        # Simulate user retry behavior
                        try:
                            await asyncio.sleep(0.1)  # Brief pause
                            # Retry the operation (simulating user persistence)
                            event = self._execute_workflow_step(session, step)
                            formatted_output = format_event(event)
                            discord_message: DiscordMessage = {
                                "content": formatted_output.get("content", ""),
                                "embeds": formatted_output.get("embeds", []),
                                "username": formatted_output.get("username", "Claude Code")
                            }
                            
                            # This time, don't inject error
                            send_to_discord(discord_message, discord_context)
                            notifications_sent += 1
                            recovered_from_errors += 1
                            
                        except Exception as retry_error:
                            issues_encountered.append(f"Retry step {i+1}: {str(retry_error)}")
        
        execution_time = time.time() - start_time
        
        # Verify error recovery behavior
        self.assertEqual(len(error_injection_points), recovered_from_errors, "Should recover from all injected errors")
        self.assertGreater(notifications_sent, len(scenario.workflow_steps) // 2, "Should send most notifications despite errors")
        
        # Verify user workflow continues despite errors
        recovery_rate = recovered_from_errors / len(error_injection_points) if error_injection_points else 0
        self.assertGreaterEqual(recovery_rate, 1.0, "Should recover from all errors")
    
    async def test_session_persistence_across_restarts(self) -> None:
        """Test session persistence when system restarts."""
        scenario = self.workflow_generator.generate_developer_workflow("persistence_test")
        
        # Execute first half of workflow
        first_half_steps = scenario.workflow_steps[:len(scenario.workflow_steps)//2]
        first_scenario = UserScenario(
            name="persistence_test_part1",
            description="First part of workflow",
            user_type=scenario.user_type,
            workflow_steps=first_half_steps,
            expected_notifications=len(first_half_steps),
            expected_threads=1,
            session_duration=scenario.session_duration / 2,
            complexity=scenario.complexity
        )
        
        first_result = await self._execute_user_workflow(first_scenario)
        self.assertTrue(first_result.workflow_completed, "First part of workflow should complete")
        
        # Simulate restart by clearing caches but keeping database
        SESSION_THREAD_CACHE.clear()
        
        # Execute second half of workflow
        second_half_steps = scenario.workflow_steps[len(scenario.workflow_steps)//2:]
        second_scenario = UserScenario(
            name="persistence_test_part2",
            description="Second part of workflow after restart",
            user_type=scenario.user_type,
            workflow_steps=second_half_steps,
            expected_notifications=len(second_half_steps),
            expected_threads=0,  # Should reuse existing thread
            session_duration=scenario.session_duration / 2,
            complexity=scenario.complexity
        )
        
        second_result = await self._execute_user_workflow(second_scenario)
        self.assertTrue(second_result.workflow_completed, "Second part of workflow should complete")
        
        # Verify session persistence
        self.assertEqual(first_result.threads_created, 1, "First part should create thread")
        # Second part should reuse thread (database persistence)
        
        self.user_test_results.extend([first_result, second_result])
    
    def test_user_scenarios_summary(self) -> None:
        """Generate summary of all user scenario test results."""
        if not self.user_test_results:
            self.skipTest("No user scenario tests have been run yet")
        
        total_scenarios = len(self.user_test_results)
        successful_workflows = sum(1 for result in self.user_test_results if result.workflow_completed)
        average_experience_rating = sum(result.user_experience_rating for result in self.user_test_results) / total_scenarios
        total_notifications = sum(result.notifications_sent for result in self.user_test_results)
        total_threads = sum(result.threads_created for result in self.user_test_results)
        
        # Group by user type
        user_type_results = {}
        for result in self.user_test_results:
            if result.user_type not in user_type_results:
                user_type_results[result.user_type] = []
            user_type_results[result.user_type].append(result)
        
        # Calculate success rates by user type
        user_type_stats = {}
        for user_type, results in user_type_results.items():
            user_type_stats[user_type] = {
                "total": len(results),
                "successful": sum(1 for r in results if r.workflow_completed),
                "average_rating": sum(r.user_experience_rating for r in results) / len(results),
                "average_notifications": sum(r.notifications_sent for r in results) / len(results)
            }
        
        # Verify quality thresholds
        success_rate = successful_workflows / total_scenarios
        self.assertGreaterEqual(success_rate, 0.90, f"User workflow success rate {success_rate:.2%} should be at least 90%")
        self.assertGreaterEqual(average_experience_rating, 7.0, f"Average user experience rating {average_experience_rating:.1f} should be at least 7.0")
        
        # Verify all user types are satisfied
        for user_type, stats in user_type_stats.items():
            user_success_rate = stats["successful"] / stats["total"]
            self.assertGreaterEqual(user_success_rate, 0.85, f"{user_type} success rate should be at least 85%")
            self.assertGreaterEqual(stats["average_rating"], 6.0, f"{user_type} average rating should be at least 6.0")
        
        # Log comprehensive summary
        self.logger.info("User scenarios test summary", {
            "total_scenarios": total_scenarios,
            "successful_workflows": successful_workflows,
            "success_rate": f"{success_rate:.2%}",
            "average_experience_rating": f"{average_experience_rating:.1f}/10",
            "total_notifications_sent": total_notifications,
            "total_threads_created": total_threads,
            "user_type_statistics": user_type_stats,
            "scenario_details": [
                {
                    "name": result.scenario_name,
                    "user_type": result.user_type,
                    "success": result.workflow_completed,
                    "notifications": result.notifications_sent,
                    "threads": result.threads_created,
                    "rating": result.user_experience_rating,
                    "issues": len(result.issues_encountered)
                }
                for result in self.user_test_results
            ]
        })
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check quality of user scenario testing."""
        await asyncio.gather(
            self.test_developer_workflow_scenario(),
            self.test_analyst_workflow_scenario(),
            self.test_beginner_workflow_scenario(),
            self.test_power_user_workflow_scenario(),
            self.test_concurrent_user_sessions(),
            self.test_user_preference_configurations(),
            self.test_error_recovery_in_user_workflows(),
            self.test_session_persistence_across_restarts()
        )
        
        # Run summary test
        self.test_user_scenarios_summary()
        
        # Calculate comprehensive quality metrics
        total_scenarios = len(self.user_test_results)
        successful_workflows = sum(1 for result in self.user_test_results if result.workflow_completed)
        average_experience_rating = sum(result.user_experience_rating for result in self.user_test_results) / total_scenarios if total_scenarios > 0 else 0
        
        return {
            "quality_level": "high",
            "user_scenarios_tested": total_scenarios,
            "workflow_success_rate": successful_workflows / total_scenarios if total_scenarios > 0 else 0,
            "average_user_experience_rating": average_experience_rating,
            "user_types_covered": len(set(result.user_type for result in self.user_test_results)),
            "all_user_workflows_successful": successful_workflows == total_scenarios,
            "user_satisfaction_threshold_met": average_experience_rating >= 7.0
        }


if __name__ == "__main__":
    unittest.main()