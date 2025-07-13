#!/usr/bin/env python3
"""Complete integration tester for Discord notification system.

This module provides end-to-end testing of the Discord notification system,
including send → receive → validate workflows for comprehensive verification.
"""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TypedDict

from src.core.config import ConfigLoader
from src.core.discord_receiver import DiscordReceiver
# No need to import process_event, we'll use direct formatting
from src.formatters.event_formatters import format_subagent_stop
from src.core.http_client import HTTPClient
from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import get_user_datetime
from src.validators.message_validator import MessageValidator, ValidationResult


class TestScenario(TypedDict):
    """Test scenario configuration."""
    name: str
    description: str
    event_type: str
    event_data: dict[str, Any]
    expected_subagent_id: str
    validation_timeout_seconds: int


class TestResult(TypedDict):
    """Result of a single test."""
    scenario_name: str
    success: bool
    send_success: bool
    receive_success: bool
    validation_result: Optional[ValidationResult]
    errors: list[str]
    warnings: list[str]
    execution_time_seconds: float


class IntegrationTestReport(TypedDict):
    """Complete test execution report."""
    test_run_id: str
    start_time: str
    end_time: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    overall_success: bool
    test_results: list[TestResult]
    summary: dict[str, Any]


class IntegrationTester:
    """Complete integration tester for Discord notifications."""
    
    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize integration tester.
        
        Args:
            config: Optional configuration, loads from ConfigLoader if None
        """
        self.logger = AstolfoLogger(__name__)
        
        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.load()
        
        self.config = config
        self.http_client = HTTPClient(config)
        self.receiver = DiscordReceiver(config)
        self.validator = MessageValidator()
        
        self.logger.info(
            "Integration tester initialized",
            has_http_client=bool(self.http_client),
            has_receiver=bool(self.receiver),
            has_validator=bool(self.validator)
        )
    
    def run_comprehensive_test(self) -> IntegrationTestReport:
        """Run comprehensive integration test suite.
        
        Returns:
            Complete test execution report
        """
        test_run_id = f"integration-test-{int(time.time())}"
        start_time = get_user_datetime()
        
        self.logger.info(
            "Starting comprehensive integration test",
            test_run_id=test_run_id,
            start_time=start_time.isoformat()
        )
        
        # Define test scenarios
        scenarios = self._create_test_scenarios()
        
        # Execute all scenarios
        test_results: list[TestResult] = []
        
        for scenario in scenarios:
            result = self._execute_test_scenario(scenario)
            test_results.append(result)
            
            # Small delay between tests to avoid rate limiting
            time.sleep(2)
        
        end_time = get_user_datetime()
        
        # Calculate summary statistics
        passed_scenarios = sum(1 for result in test_results if result["success"])
        failed_scenarios = len(test_results) - passed_scenarios
        overall_success = failed_scenarios == 0
        
        # Create comprehensive report
        report: IntegrationTestReport = {
            "test_run_id": test_run_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_scenarios": len(scenarios),
            "passed_scenarios": passed_scenarios,
            "failed_scenarios": failed_scenarios,
            "overall_success": overall_success,
            "test_results": test_results,
            "summary": self._generate_test_summary(test_results)
        }
        
        self.logger.info(
            "Comprehensive integration test completed",
            test_run_id=test_run_id,
            total_scenarios=len(scenarios),
            passed=passed_scenarios,
            failed=failed_scenarios,
            overall_success=overall_success
        )
        
        return report
    
    def _create_test_scenarios(self) -> list[TestScenario]:
        """Create comprehensive test scenarios.
        
        Returns:
            List of test scenarios to execute
        """
        # Create temporary transcript file for testing
        temp_transcript = self._create_test_transcript()
        
        scenarios: list[TestScenario] = [
            {
                "name": "basic_subagent_completion",
                "description": "Basic subagent completion with normal content",
                "event_type": "SubagentStop",
                "event_data": {
                    "subagent_id": "test-astolfo-basic",
                    "result": "Discord notification testing completed successfully!",
                    "session_id": "test-session-basic-001",
                    "transcript_path": temp_transcript,
                    "duration_seconds": 30,
                    "tools_used": 5
                },
                "expected_subagent_id": "test-astolfo-basic",
                "validation_timeout_seconds": 30
            },
            {
                "name": "prompt_mixing_detection",
                "description": "Test contamination detection for prompt mixing",
                "event_type": "SubagentStop",
                "event_data": {
                    "subagent_id": "test-astolfo-impl",
                    "result": "Implementation completed with potential contamination",
                    "session_id": "audit-session-contaminated",  # Wrong session ID to trigger contamination
                    "transcript_path": temp_transcript,
                    "duration_seconds": 45,
                    "tools_used": 8
                },
                "expected_subagent_id": "test-astolfo-impl",
                "validation_timeout_seconds": 30
            },
            {
                "name": "jst_timestamp_validation",
                "description": "Verify JST timestamp formatting in notifications",
                "event_type": "SubagentStop",
                "event_data": {
                    "subagent_id": "test-astolfo-jst",
                    "result": "JST timestamp validation test",
                    "session_id": "test-session-jst-002",
                    "transcript_path": temp_transcript,
                    "duration_seconds": 15,
                    "tools_used": 3
                },
                "expected_subagent_id": "test-astolfo-jst",
                "validation_timeout_seconds": 30
            },
            {
                "name": "large_content_handling",
                "description": "Test handling of large message content",
                "event_type": "SubagentStop", 
                "event_data": {
                    "subagent_id": "test-astolfo-large",
                    "result": "Large content test: " + "A" * 1000,  # Large result
                    "session_id": "test-session-large-003",
                    "transcript_path": temp_transcript,
                    "duration_seconds": 60,
                    "tools_used": 12
                },
                "expected_subagent_id": "test-astolfo-large",
                "validation_timeout_seconds": 30
            },
            {
                "name": "empty_session_handling",
                "description": "Test handling of empty session ID",
                "event_type": "SubagentStop",
                "event_data": {
                    "subagent_id": "test-astolfo-empty",
                    "result": "Empty session ID handling test",
                    "session_id": "",  # Empty session ID
                    "transcript_path": temp_transcript,
                    "duration_seconds": 20,
                    "tools_used": 4
                },
                "expected_subagent_id": "test-astolfo-empty",
                "validation_timeout_seconds": 30
            }
        ]
        
        return scenarios
    
    def _execute_test_scenario(self, scenario: TestScenario) -> TestResult:
        """Execute a single test scenario.
        
        Args:
            scenario: Test scenario to execute
            
        Returns:
            Test execution result
        """
        start_time = time.time()
        
        self.logger.info(
            "Executing test scenario",
            scenario_name=scenario["name"],
            description=scenario["description"]
        )
        
        errors: list[str] = []
        warnings: list[str] = []
        send_success = False
        receive_success = False
        validation_result: Optional[ValidationResult] = None
        
        try:
            # Step 1: Send notification
            self.logger.info("Step 1: Sending notification", scenario_name=scenario["name"])
            
            # Format the message
            session_id = str(scenario["event_data"].get("session_id", "unknown"))[:8]
            embed = format_subagent_stop(scenario["event_data"], session_id)
            
            # Send via Discord  
            send_result = self.http_client.send_message({"embeds": [embed], "content": None})
            
            if send_result.get("success", False):
                send_success = True
                self.logger.info("Message sent successfully", scenario_name=scenario["name"])
            else:
                errors.append(f"Failed to send message: {send_result.get('error', 'Unknown error')}")
                self.logger.error("Failed to send message", scenario_name=scenario["name"], error=send_result.get("error"))
            
            # Step 2: Wait and receive
            if send_success:
                self.logger.info("Step 2: Waiting for message delivery", scenario_name=scenario["name"])
                time.sleep(5)  # Allow time for message to be delivered
                
                # Receive recent messages
                try:
                    recent_messages = self.receiver.find_latest_subagent_message(
                        subagent_id=scenario["expected_subagent_id"],
                        time_window_minutes=2
                    )
                    
                    if recent_messages:
                        receive_success = True
                        self.logger.info("Message received successfully", scenario_name=scenario["name"])
                        
                        # Step 3: Validate
                        self.logger.info("Step 3: Validating message content", scenario_name=scenario["name"])
                        validation_result = self.validator.validate_subagent_message(
                            embed,
                            recent_messages,
                            scenario["expected_subagent_id"]
                        )
                        
                        if not validation_result["success"]:
                            errors.extend(validation_result["errors"])
                        
                        warnings.extend(validation_result["warnings"])
                        
                    else:
                        errors.append("Message not found in recent Discord messages")
                        self.logger.warning("Message not found in Discord", scenario_name=scenario["name"])
                        
                except Exception as e:
                    errors.append(f"Failed to receive message: {e}")
                    self.logger.error("Failed to receive message", scenario_name=scenario["name"], error=str(e))
            
        except Exception as e:
            errors.append(f"Test execution error: {e}")
            self.logger.error("Test execution error", scenario_name=scenario["name"], error=str(e))
        
        execution_time = time.time() - start_time
        success = send_success and receive_success and (validation_result is None or validation_result["success"])
        
        result: TestResult = {
            "scenario_name": scenario["name"],
            "success": success,
            "send_success": send_success,
            "receive_success": receive_success,
            "validation_result": validation_result,
            "errors": errors,
            "warnings": warnings,
            "execution_time_seconds": execution_time
        }
        
        self.logger.info(
            "Test scenario completed",
            scenario_name=scenario["name"],
            success=success,
            execution_time=execution_time,
            error_count=len(errors),
            warning_count=len(warnings)
        )
        
        return result
    
    def _create_test_transcript(self) -> str:
        """Create a temporary transcript file for testing.
        
        Returns:
            Path to temporary transcript file
        """
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
        
        # Create test transcript entries
        entries = [
            # Basic test session entry
            {
                "type": "user",
                "sessionId": "test-session-basic-001",
                "timestamp": "2025-07-12T12:00:00.000Z",
                "isSidechain": True,
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {
                                "prompt": "テストアストルフォちゃん♡ Discord通知機能のテストを実行してね！"
                            }
                        }
                    ]
                }
            },
            {
                "type": "assistant",
                "sessionId": "test-session-basic-001",
                "timestamp": "2025-07-12T12:00:30.000Z",
                "isSidechain": True,
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "テストアストルフォ：Discord通知機能のテストを開始します！"
                        }
                    ]
                }
            },
            # Contaminated session for testing contamination detection
            {
                "type": "user",
                "sessionId": "audit-session-contaminated",
                "timestamp": "2025-07-12T12:01:00.000Z",
                "isSidechain": True,
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Task",
                            "input": {
                                "prompt": "監査アストルフォちゃん♡ プロンプト混在テストのための監査を実行してね！"
                            }
                        }
                    ]
                }
            },
            {
                "type": "assistant",
                "sessionId": "audit-session-contaminated",
                "timestamp": "2025-07-12T12:01:30.000Z",
                "isSidechain": True,
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "監査アストルフォ：プロンプト混在の調査を開始します！"
                        }
                    ]
                }
            }
        ]
        
        for entry in entries:
            temp_file.write(json.dumps(entry) + '\n')
        
        temp_file.close()
        return temp_file.name
    
    def _generate_test_summary(self, test_results: list[TestResult]) -> dict[str, Any]:
        """Generate comprehensive test summary.
        
        Args:
            test_results: List of test results
            
        Returns:
            Test summary dictionary
        """
        summary = {
            "execution_statistics": {
                "total_execution_time": sum(r["execution_time_seconds"] for r in test_results),
                "average_execution_time": sum(r["execution_time_seconds"] for r in test_results) / len(test_results) if test_results else 0,
                "fastest_test": min(test_results, key=lambda x: x["execution_time_seconds"])["scenario_name"] if test_results else None,
                "slowest_test": max(test_results, key=lambda x: x["execution_time_seconds"])["scenario_name"] if test_results else None
            },
            "error_analysis": {
                "total_errors": sum(len(r["errors"]) for r in test_results),
                "total_warnings": sum(len(r["warnings"]) for r in test_results),
                "most_common_errors": self._analyze_common_errors(test_results),
                "scenarios_with_errors": [r["scenario_name"] for r in test_results if r["errors"]]
            },
            "feature_validation": {
                "send_success_rate": sum(1 for r in test_results if r["send_success"]) / len(test_results) if test_results else 0,
                "receive_success_rate": sum(1 for r in test_results if r["receive_success"]) / len(test_results) if test_results else 0,
                "validation_success_rate": sum(1 for r in test_results if r["validation_result"] and r["validation_result"]["success"]) / len(test_results) if test_results else 0,
                "contamination_detection_working": any(
                    r["validation_result"] and 
                    r["validation_result"]["details"].get("contamination_detected", False)
                    for r in test_results if r["validation_result"]
                ),
                "jst_timestamp_working": any(
                    r["validation_result"] and 
                    r["validation_result"]["details"].get("timestamp_found", False)
                    for r in test_results if r["validation_result"]
                )
            }
        }
        
        return summary
    
    def _analyze_common_errors(self, test_results: list[TestResult]) -> list[tuple[str, int]]:
        """Analyze most common errors across test results.
        
        Args:
            test_results: List of test results
            
        Returns:
            List of (error_message, count) tuples, sorted by frequency
        """
        error_counts: dict[str, int] = {}
        
        for result in test_results:
            for error in result["errors"]:
                # Normalize error message for grouping
                normalized_error = error.split(":")[0] if ":" in error else error
                error_counts[normalized_error] = error_counts.get(normalized_error, 0) + 1
        
        # Sort by frequency, descending
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
    
    def save_report(self, report: IntegrationTestReport, output_path: Optional[str] = None) -> str:
        """Save test report to file.
        
        Args:
            report: Test report to save
            output_path: Optional output path, generates if None
            
        Returns:
            Path to saved report file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            output_path = f"/home/ubuntu/claude_code_event_notifier/{timestamp}-integration-test-report.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(
            "Test report saved",
            output_path=output_path,
            test_run_id=report["test_run_id"]
        )
        
        return output_path