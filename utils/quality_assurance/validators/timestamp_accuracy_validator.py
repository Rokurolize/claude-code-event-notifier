#!/usr/bin/env python3
"""Timestamp accuracy validator for comprehensive quality assurance.

This module integrates the existing timestamp accuracy tests into the
comprehensive quality assurance framework, providing both compatibility
with existing tests and enhanced validation capabilities.
"""

import asyncio
import re
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict
from dataclasses import dataclass

# Add src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import get_user_datetime

# Import existing timestamp test functionality
sys.path.insert(0, str(project_root / "tests"))
try:
    from tests.timestamp.test_timestamp_accuracy import TimestampAccuracyTests, UTCLeakDetectionTests
    EXISTING_TESTS_AVAILABLE = True
except ImportError as e:
    EXISTING_TESTS_AVAILABLE = False
    print(f"Warning: Existing timestamp tests not available: {e}")

# Import formatters for direct testing
try:
    from src.formatters.event_formatters import (
        format_notification,
        format_post_tool_use,
        format_pre_tool_use,
        format_stop,
        format_subagent_stop
    )
    FORMATTERS_AVAILABLE = True
except ImportError as e:
    FORMATTERS_AVAILABLE = False
    print(f"Warning: Event formatters not available: {e}")


@dataclass
class TimestampValidationResult:
    """Result of timestamp validation."""
    formatter_name: str
    timestamp_extracted: str
    is_jst_format: bool
    is_recent: bool
    time_difference_seconds: float
    validation_passed: bool
    error_message: Optional[str] = None


@dataclass
class UtcLeakCheckResult:
    """Result of UTC leak detection."""
    file_path: str
    line_number: int
    line_content: str
    pattern_matched: str
    severity: str  # "error", "warning", "info"


class TimestampAccuracyValidator:
    """Validator for timestamp accuracy and UTC leak detection."""
    
    def __init__(self):
        """Initialize timestamp accuracy validator."""
        self.logger = AstolfoLogger(__name__)
        self.project_root = project_root
        self.src_path = project_root / "src"
        
        # UTC leak detection patterns
        self.utc_patterns = [
            (r"datetime\.now\(UTC\)", "Direct UTC datetime.now() call", "error"),
            (r"datetime\.utcnow\(\)", "Deprecated datetime.utcnow() call", "error"),
            (r"\.strftime.*UTC", "UTC in strftime format", "warning"),
            (r"timezone\.utc", "Direct UTC timezone usage", "warning"),
            (r"datetime\.now\(\)\.utc", "UTC conversion of current time", "error"),
            (r"time\.gmtime\(\)", "GMT time usage (UTC equivalent)", "warning"),
            (r"pytz\.UTC", "PyTZ UTC timezone usage", "warning"),
            (r"pytz\.utc", "PyTZ UTC timezone usage", "warning"),
            (r"timezone\.UTC", "Timezone UTC constant", "warning")
        ]
        
        # Test formatters and their timestamp field mappings
        self.formatter_test_configs = {
            "format_pre_tool_use": {
                "function": format_pre_tool_use if FORMATTERS_AVAILABLE else None,
                "test_data": {"tool_name": "TestTool", "input": {"test": "data"}},
                "timestamp_field": "Time",
                "session_id": "test-001"
            },
            "format_post_tool_use": {
                "function": format_post_tool_use if FORMATTERS_AVAILABLE else None,
                "test_data": {"tool_name": "TestTool", "success": True, "output": "Test completed"},
                "timestamp_field": "Completed at",
                "session_id": "test-001"
            },
            "format_stop": {
                "function": format_stop if FORMATTERS_AVAILABLE else None,
                "test_data": {"session_id": "test-session-001"},
                "timestamp_field": "Ended at",
                "session_id": "test-001"
            },
            "format_notification": {
                "function": format_notification if FORMATTERS_AVAILABLE else None,
                "test_data": {"message": "Test notification", "session_id": "test-session-001"},
                "timestamp_field": "Time",
                "session_id": "test-001"
            },
            "format_subagent_stop": {
                "function": format_subagent_stop if FORMATTERS_AVAILABLE else None,
                "test_data": {
                    "subagent_id": "test-astolfo",
                    "result": "Test completed",
                    "session_id": "test-session-001",
                    "transcript_path": None,  # Will be set during test
                    "duration_seconds": 30,
                    "tools_used": 5
                },
                "timestamp_field": "Completed at",
                "session_id": "test-001"
            }
        }
        
        self.logger.info(
            "Timestamp accuracy validator initialized",
            context={
                "existing_tests_available": EXISTING_TESTS_AVAILABLE,
                "formatters_available": FORMATTERS_AVAILABLE,
                "utc_patterns_count": len(self.utc_patterns),
                "formatter_configs": len(self.formatter_test_configs)
            }
        )
    
    def extract_timestamp_from_embed(self, embed: Dict[str, Any], field_name: str) -> str:
        """Extract timestamp from embed description or fields.
        
        Args:
            embed: Discord embed dictionary
            field_name: Field name to search for
            
        Returns:
            Extracted timestamp string
            
        Raises:
            ValueError: If timestamp field is not found
        """
        description = embed.get("description", "")
        
        # Search in description
        pattern = rf"\*\*{re.escape(field_name)}:\*\* (.+)"
        match = re.search(pattern, description)
        if match:
            return match.group(1).strip()
        
        # Search in fields
        for field in embed.get("fields", []):
            if field.get("name") == field_name:
                return field.get("value", "").strip()
        
        raise ValueError(f"Timestamp field '{field_name}' not found in embed")
    
    def validate_jst_timestamp(
        self, 
        timestamp_str: str, 
        tolerance_minutes: int = 2
    ) -> Tuple[bool, bool, float, Optional[str]]:
        """Validate JST timestamp format and recency.
        
        Args:
            timestamp_str: Timestamp string to validate
            tolerance_minutes: Allowed difference from current time
            
        Returns:
            Tuple of (is_jst_format, is_recent, time_diff_seconds, error_message)
        """
        try:
            # Check JST suffix
            is_jst_format = timestamp_str.endswith(" JST")
            if not is_jst_format:
                return False, False, 0.0, f"Timestamp should end with ' JST': {timestamp_str}"
            
            # Parse timestamp (remove JST suffix)
            time_part = timestamp_str.replace(" JST", "")
            try:
                parsed_time = datetime.strptime(time_part, "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                return False, False, 0.0, f"Failed to parse timestamp '{time_part}': {e}"
            
            # Check if timestamp is recent
            current_time = get_user_datetime().replace(tzinfo=None)
            time_diff = abs((current_time - parsed_time).total_seconds())
            
            max_diff = tolerance_minutes * 60
            is_recent = time_diff <= max_diff
            
            if not is_recent:
                error_message = f"Timestamp {timestamp_str} is {time_diff:.0f}s old, max allowed: {max_diff}s"
            else:
                error_message = None
            
            return is_jst_format, is_recent, time_diff, error_message
            
        except Exception as e:
            return False, False, 0.0, f"Unexpected error validating timestamp: {e}"
    
    async def validate_formatter_timestamp(
        self, 
        formatter_name: str, 
        tolerance_minutes: int = 2
    ) -> TimestampValidationResult:
        """Validate timestamp accuracy for a specific formatter.
        
        Args:
            formatter_name: Name of the formatter to test
            tolerance_minutes: Allowed time difference tolerance
            
        Returns:
            TimestampValidationResult with validation details
        """
        if not FORMATTERS_AVAILABLE:
            return TimestampValidationResult(
                formatter_name=formatter_name,
                timestamp_extracted="",
                is_jst_format=False,
                is_recent=False,
                time_difference_seconds=0.0,
                validation_passed=False,
                error_message="Formatters not available for testing"
            )
        
        config = self.formatter_test_configs.get(formatter_name)
        if not config or not config["function"]:
            return TimestampValidationResult(
                formatter_name=formatter_name,
                timestamp_extracted="",
                is_jst_format=False,
                is_recent=False,
                time_difference_seconds=0.0,
                validation_passed=False,
                error_message=f"Formatter {formatter_name} not configured or not available"
            )
        
        try:
            # Create temporary transcript if needed for subagent tests
            temp_transcript = None
            if formatter_name == "format_subagent_stop":
                temp_transcript = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
                temp_transcript.write('{"type":"test","sessionId":"test-001","timestamp":"2025-07-12T13:00:00.000Z"}\n')
                temp_transcript.close()
                config["test_data"]["transcript_path"] = temp_transcript.name
            
            # Call formatter
            embed = config["function"](config["test_data"], config["session_id"])
            
            # Extract timestamp
            timestamp = self.extract_timestamp_from_embed(embed, config["timestamp_field"])
            
            # Validate timestamp
            is_jst, is_recent, time_diff, error_msg = self.validate_jst_timestamp(
                timestamp, tolerance_minutes
            )
            
            validation_passed = is_jst and is_recent
            
            result = TimestampValidationResult(
                formatter_name=formatter_name,
                timestamp_extracted=timestamp,
                is_jst_format=is_jst,
                is_recent=is_recent,
                time_difference_seconds=time_diff,
                validation_passed=validation_passed,
                error_message=error_msg
            )
            
            # Clean up temporary file
            if temp_transcript:
                Path(temp_transcript.name).unlink(missing_ok=True)
            
            self.logger.info(
                f"Formatter timestamp validation completed: {formatter_name}",
                context={
                    "timestamp": timestamp,
                    "is_jst": is_jst,
                    "is_recent": is_recent,
                    "time_diff": time_diff,
                    "passed": validation_passed
                }
            )
            
            return result
            
        except Exception as e:
            return TimestampValidationResult(
                formatter_name=formatter_name,
                timestamp_extracted="",
                is_jst_format=False,
                is_recent=False,
                time_difference_seconds=0.0,
                validation_passed=False,
                error_message=f"Error testing formatter {formatter_name}: {e}"
            )
    
    async def validate_all_formatters(
        self, 
        tolerance_minutes: int = 2
    ) -> List[TimestampValidationResult]:
        """Validate timestamp accuracy for all formatters.
        
        Args:
            tolerance_minutes: Allowed time difference tolerance
            
        Returns:
            List of TimestampValidationResult for each formatter
        """
        self.logger.info("Starting comprehensive formatter timestamp validation")
        
        results = []
        for formatter_name in self.formatter_test_configs.keys():
            result = await self.validate_formatter_timestamp(formatter_name, tolerance_minutes)
            results.append(result)
        
        # Summary logging
        passed_count = sum(1 for r in results if r.validation_passed)
        failed_count = len(results) - passed_count
        
        self.logger.info(
            "Formatter timestamp validation completed",
            context={
                "total_formatters": len(results),
                "passed": passed_count,
                "failed": failed_count,
                "success_rate": (passed_count / len(results)) * 100 if results else 0
            }
        )
        
        return results
    
    async def detect_utc_leaks(
        self, 
        file_patterns: Optional[List[str]] = None
    ) -> List[UtcLeakCheckResult]:
        """Detect UTC timestamp usage patterns in source files.
        
        Args:
            file_patterns: File patterns to check (defaults to common patterns)
            
        Returns:
            List of UtcLeakCheckResult for violations found
        """
        if file_patterns is None:
            file_patterns = [
                "src/formatters/*.py",
                "src/handlers/*.py",
                "src/core/*.py",
                "src/utils/*.py",
                "src/discord_notifier.py"
            ]
        
        self.logger.info("Starting UTC leak detection")
        
        violations = []
        files_scanned = 0
        
        for pattern in file_patterns:
            files = list(self.project_root.glob(pattern))
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                files_scanned += 1
                
                try:
                    content = file_path.read_text(encoding='utf-8')
                    lines = content.splitlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        for utc_pattern, description, severity in self.utc_patterns:
                            if re.search(utc_pattern, line):
                                # Skip comments and docstrings unless they're suspicious
                                stripped = line.strip()
                                is_comment = stripped.startswith('#') or '"""' in line or "'''" in line
                                
                                if is_comment and severity != "error":
                                    continue
                                
                                violations.append(UtcLeakCheckResult(
                                    file_path=str(file_path.relative_to(self.project_root)),
                                    line_number=line_num,
                                    line_content=line.strip(),
                                    pattern_matched=description,
                                    severity=severity
                                ))
                
                except (UnicodeDecodeError, PermissionError) as e:
                    self.logger.warning(f"Could not read {file_path}: {e}")
        
        # Summary logging
        error_count = sum(1 for v in violations if v.severity == "error")
        warning_count = sum(1 for v in violations if v.severity == "warning")
        
        self.logger.info(
            "UTC leak detection completed",
            context={
                "files_scanned": files_scanned,
                "total_violations": len(violations),
                "errors": error_count,
                "warnings": warning_count
            }
        )
        
        return violations
    
    async def run_existing_timestamp_tests(self) -> Dict[str, Any]:
        """Run existing timestamp accuracy tests and return results.
        
        Returns:
            Dictionary with test results and statistics
        """
        if not EXISTING_TESTS_AVAILABLE:
            return {
                "available": False,
                "error": "Existing timestamp tests not available",
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }
        
        self.logger.info("Running existing timestamp accuracy tests")
        
        try:
            # Create test suite
            loader = unittest.TestLoader()
            suite = unittest.TestSuite()
            
            # Add timestamp accuracy tests
            suite.addTests(loader.loadTestsFromTestCase(TimestampAccuracyTests))
            suite.addTests(loader.loadTestsFromTestCase(UTCLeakDetectionTests))
            
            # Run tests with custom result collector
            result = unittest.TestResult()
            suite.run(result)
            
            # Collect results
            tests_run = result.testsRun
            tests_passed = tests_run - len(result.failures) - len(result.errors)
            tests_failed = len(result.failures) + len(result.errors)
            
            # Detailed failure information
            failures = []
            for test, traceback in result.failures:
                failures.append({
                    "test": str(test),
                    "error": "Test failure",
                    "traceback": traceback
                })
            
            for test, traceback in result.errors:
                failures.append({
                    "test": str(test),
                    "error": "Test error",
                    "traceback": traceback
                })
            
            test_results = {
                "available": True,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "success_rate": (tests_passed / tests_run) * 100 if tests_run > 0 else 0,
                "failures": failures,
                "errors": []
            }
            
            self.logger.info(
                "Existing timestamp tests completed",
                context={
                    "tests_run": tests_run,
                    "tests_passed": tests_passed,
                    "tests_failed": tests_failed,
                    "success_rate": test_results["success_rate"]
                }
            )
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"Failed to run existing timestamp tests: {e}")
            return {
                "available": True,
                "error": str(e),
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0
            }
    
    async def run_subprocess_timestamp_tests(self) -> Dict[str, Any]:
        """Run timestamp tests via subprocess (like development_checker does).
        
        Returns:
            Dictionary with subprocess test results
        """
        self.logger.info("Running timestamp tests via subprocess")
        
        try:
            cmd = [
                "uv", "run", "--no-sync", "--python", "3.13",
                "python", "-m", "unittest",
                "tests.timestamp.test_timestamp_accuracy", "-v"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            test_output = result.stdout + result.stderr
            test_success = result.returncode == 0
            
            # Parse test output for more details
            test_count = 0
            if "Ran " in test_output:
                try:
                    ran_line = [line for line in test_output.split('\n') if line.startswith("Ran ")][0]
                    test_count = int(ran_line.split()[1])
                except (IndexError, ValueError):
                    pass
            
            return {
                "subprocess_success": test_success,
                "return_code": result.returncode,
                "output": test_output,
                "test_count": test_count,
                "command": " ".join(cmd)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "subprocess_success": False,
                "return_code": -1,
                "output": "Test execution timed out after 120 seconds",
                "test_count": 0,
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "subprocess_success": False,
                "return_code": -1,
                "output": f"Failed to run tests: {e}",
                "test_count": 0,
                "command": "N/A"
            }
    
    async def comprehensive_timestamp_validation(
        self, 
        tolerance_minutes: int = 2,
        include_subprocess_tests: bool = True
    ) -> Dict[str, Any]:
        """Run comprehensive timestamp accuracy validation.
        
        Args:
            tolerance_minutes: Time tolerance for timestamp validation
            include_subprocess_tests: Whether to include subprocess test execution
            
        Returns:
            Comprehensive validation results
        """
        self.logger.info("Starting comprehensive timestamp validation")
        
        start_time = time.time()
        
        # Run formatter validations
        formatter_results = await self.validate_all_formatters(tolerance_minutes)
        
        # Run UTC leak detection
        utc_leaks = await self.detect_utc_leaks()
        
        # Run existing tests
        existing_test_results = await self.run_existing_timestamp_tests()
        
        # Run subprocess tests if requested
        subprocess_results = None
        if include_subprocess_tests:
            subprocess_results = await self.run_subprocess_timestamp_tests()
        
        execution_time = time.time() - start_time
        
        # Calculate overall results
        formatter_passed = sum(1 for r in formatter_results if r.validation_passed)
        formatter_failed = len(formatter_results) - formatter_passed
        
        utc_errors = sum(1 for leak in utc_leaks if leak.severity == "error")
        utc_warnings = sum(1 for leak in utc_leaks if leak.severity == "warning")
        
        # Determine overall status
        overall_passed = (
            formatter_failed == 0 and
            utc_errors == 0 and
            existing_test_results.get("tests_failed", 0) == 0 and
            (subprocess_results is None or subprocess_results.get("subprocess_success", False))
        )
        
        # Calculate quality score
        quality_score = 0.0
        total_weight = 0.0
        
        # Formatter tests (40% weight)
        if formatter_results:
            formatter_score = (formatter_passed / len(formatter_results)) * 100
            quality_score += formatter_score * 0.4
            total_weight += 0.4
        
        # UTC leak tests (30% weight) - errors are more serious than warnings
        if utc_leaks:
            utc_score = max(0, 100 - (utc_errors * 30) - (utc_warnings * 10))
        else:
            utc_score = 100
        quality_score += utc_score * 0.3
        total_weight += 0.3
        
        # Existing tests (30% weight)
        if existing_test_results.get("tests_run", 0) > 0:
            existing_score = existing_test_results.get("success_rate", 0)
            quality_score += existing_score * 0.3
            total_weight += 0.3
        
        # Normalize score
        if total_weight > 0:
            quality_score = quality_score / total_weight
        
        comprehensive_results = {
            "overall_passed": overall_passed,
            "quality_score": quality_score,
            "execution_time": execution_time,
            "formatter_validation": {
                "total_formatters": len(formatter_results),
                "passed": formatter_passed,
                "failed": formatter_failed,
                "results": [
                    {
                        "formatter": r.formatter_name,
                        "passed": r.validation_passed,
                        "timestamp": r.timestamp_extracted,
                        "jst_format": r.is_jst_format,
                        "recent": r.is_recent,
                        "time_diff": r.time_difference_seconds,
                        "error": r.error_message
                    }
                    for r in formatter_results
                ]
            },
            "utc_leak_detection": {
                "total_violations": len(utc_leaks),
                "errors": utc_errors,
                "warnings": utc_warnings,
                "violations": [
                    {
                        "file": leak.file_path,
                        "line": leak.line_number,
                        "content": leak.line_content,
                        "pattern": leak.pattern_matched,
                        "severity": leak.severity
                    }
                    for leak in utc_leaks
                ]
            },
            "existing_tests": existing_test_results,
            "subprocess_tests": subprocess_results,
            "summary": {
                "components_tested": [
                    "formatter_validation",
                    "utc_leak_detection", 
                    "existing_tests"
                ] + (["subprocess_tests"] if subprocess_results else []),
                "critical_issues": utc_errors + formatter_failed,
                "warnings": utc_warnings,
                "recommendations": self._generate_recommendations(
                    formatter_results, utc_leaks, existing_test_results
                )
            }
        }
        
        self.logger.info(
            "Comprehensive timestamp validation completed",
            context={
                "overall_passed": overall_passed,
                "quality_score": quality_score,
                "execution_time": execution_time,
                "formatter_success_rate": (formatter_passed / len(formatter_results)) * 100 if formatter_results else 0,
                "utc_violations": len(utc_leaks),
                "existing_tests_success": existing_test_results.get("success_rate", 0)
            }
        )
        
        return comprehensive_results
    
    def _generate_recommendations(
        self,
        formatter_results: List[TimestampValidationResult],
        utc_leaks: List[UtcLeakCheckResult],
        existing_test_results: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on validation results.
        
        Args:
            formatter_results: Formatter validation results
            utc_leaks: UTC leak detection results
            existing_test_results: Existing test results
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Formatter recommendations
        failed_formatters = [r for r in formatter_results if not r.validation_passed]
        if failed_formatters:
            recommendations.append(
                f"Fix timestamp issues in formatters: {', '.join(r.formatter_name for r in failed_formatters)}"
            )
        
        # UTC leak recommendations
        error_leaks = [leak for leak in utc_leaks if leak.severity == "error"]
        if error_leaks:
            recommendations.append(
                f"Fix critical UTC timestamp usage in {len(error_leaks)} location(s)"
            )
        
        warning_leaks = [leak for leak in utc_leaks if leak.severity == "warning"]
        if warning_leaks:
            recommendations.append(
                f"Review {len(warning_leaks)} potential UTC timestamp usage warning(s)"
            )
        
        # Existing test recommendations
        if existing_test_results.get("tests_failed", 0) > 0:
            recommendations.append(
                f"Fix {existing_test_results['tests_failed']} failing timestamp accuracy test(s)"
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append("All timestamp validation checks passed successfully")
        else:
            recommendations.append("Run timestamp tests before deployment")
            recommendations.append("Ensure all user-facing timestamps use JST timezone")
        
        return recommendations


async def main():
    """Main function for standalone timestamp validation."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Timestamp Accuracy Validator")
    parser.add_argument("--tolerance", type=int, default=2,
                       help="Time tolerance in minutes (default: 2)")
    parser.add_argument("--no-subprocess", action="store_true",
                       help="Skip subprocess test execution")
    parser.add_argument("--formatters-only", action="store_true",
                       help="Run only formatter validation")
    parser.add_argument("--utc-leaks-only", action="store_true",
                       help="Run only UTC leak detection")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    validator = TimestampAccuracyValidator()
    
    if args.formatters_only:
        results = await validator.validate_all_formatters(args.tolerance)
        output = {
            "type": "formatter_validation",
            "results": [
                {
                    "formatter": r.formatter_name,
                    "passed": r.validation_passed,
                    "timestamp": r.timestamp_extracted,
                    "error": r.error_message
                }
                for r in results
            ]
        }
    elif args.utc_leaks_only:
        leaks = await validator.detect_utc_leaks()
        output = {
            "type": "utc_leak_detection",
            "violations": [
                {
                    "file": leak.file_path,
                    "line": leak.line_number,
                    "pattern": leak.pattern_matched,
                    "severity": leak.severity
                }
                for leak in leaks
            ]
        }
    else:
        output = await validator.comprehensive_timestamp_validation(
            tolerance_minutes=args.tolerance,
            include_subprocess_tests=not args.no_subprocess
        )
    
    # Save output if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"Results saved to {args.output}")
    
    # Print summary
    if "overall_passed" in output:
        status = "PASSED" if output["overall_passed"] else "FAILED"
        score = output.get("quality_score", 0)
        print(f"\nTimestamp Validation: {status}")
        print(f"Quality Score: {score:.1f}/100")
        
        if output.get("summary", {}).get("recommendations"):
            print("\nRecommendations:")
            for rec in output["summary"]["recommendations"]:
                print(f"  • {rec}")
    
    return 0 if output.get("overall_passed", False) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))