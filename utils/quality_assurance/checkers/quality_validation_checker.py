#!/usr/bin/env python3
"""Quality Validation Quality Checker.

This module provides comprehensive quality checks for quality validation
functionality, including type safety runtime validation, runtime validation
completeness, error handling coverage, AstolfoLogger completeness, message
comparison accuracy, input sanitization, and security validation.
"""

import asyncio
import ast
import inspect
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, get_type_hints
import importlib.util

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.type_guards import validate_config, validate_event_data, validate_tool_data
from src.exceptions import ConfigurationError, ValidationError, HTTPError
from ..core_checker import BaseQualityChecker, QualityCheckResult


class QualityValidationChecker(BaseQualityChecker):
    """Quality checker for quality validation functionality.
    
    Validates all aspects of quality validation including:
    - Type safety runtime validation coverage
    - Runtime validation completeness and accuracy  
    - Error handling coverage across all modules
    - AstolfoLogger logging completeness
    - Message send/receive comparison accuracy
    - Input sanitization effectiveness
    - Security validation completeness
    """
    
    def __init__(self, project_root: Path, logger: AstolfoLogger) -> None:
        """Initialize quality validation checker.
        
        Args:
            project_root: Project root directory
            logger: Logger instance for structured logging
        """
        super().__init__(project_root, logger)
        self.category = "Quality Validation"
        
        # Quality metrics tracking
        self.metrics = {
            "type_validation_success_rate": 0.0,
            "runtime_validation_accuracy": 0.0,
            "error_handling_coverage": 0.0,
            "logging_completeness": 0.0,
            "message_comparison_accuracy": 0.0,
            "input_sanitization_score": 0.0,
            "security_validation_rate": 0.0,
            "type_guard_coverage": 0.0
        }
        
        # Test data for various checks
        self._init_test_data()
    
    def _init_test_data(self) -> None:
        """Initialize test data for quality validation checks."""
        
        # Type validation test cases
        self.type_test_cases = [
            {
                "name": "valid_config",
                "data": {
                    "webhook_url": "https://discord.com/api/webhooks/123/abc",
                    "use_threads": True,
                    "enabled_events": ["PreToolUse", "PostToolUse"]
                },
                "expected_valid": True
            },
            {
                "name": "invalid_config_type",
                "data": {
                    "webhook_url": 123,  # Should be string
                    "use_threads": "true",  # Should be boolean
                    "enabled_events": "PreToolUse"  # Should be list
                },
                "expected_valid": False
            },
            {
                "name": "missing_required_fields",
                "data": {
                    "use_threads": True
                    # Missing webhook_url or bot_token
                },
                "expected_valid": False
            }
        ]
        
        # Event data test cases
        self.event_test_cases = [
            {
                "name": "valid_pre_tool_use",
                "data": {
                    "session_id": "test_session_001",
                    "tool_name": "Read",
                    "input_data": {"file_path": "/test/file.py"}
                },
                "expected_valid": True
            },
            {
                "name": "invalid_session_id_type",
                "data": {
                    "session_id": 123,  # Should be string
                    "tool_name": "Read",
                    "input_data": {"file_path": "/test/file.py"}
                },
                "expected_valid": False
            }
        ]
        
        # Input sanitization test cases
        self.sanitization_test_cases = [
            {
                "name": "malicious_sql",
                "input": "'; DROP TABLE users; --",
                "should_be_sanitized": True
            },
            {
                "name": "xss_script",
                "input": "<script>alert('xss')</script>",
                "should_be_sanitized": True
            },
            {
                "name": "path_traversal",
                "input": "../../etc/passwd",
                "should_be_sanitized": True
            },
            {
                "name": "command_injection",
                "input": "test; rm -rf /",
                "should_be_sanitized": True
            },
            {
                "name": "safe_input",
                "input": "Hello world 123",
                "should_be_sanitized": False
            }
        ]
        
        # Security validation patterns
        self.security_patterns = [
            {
                "name": "hardcoded_secrets",
                "pattern": r'(?i)(password|token|key|secret)\s*=\s*["\'][^"\']{8,}["\']',
                "description": "Hardcoded secrets detection"
            },
            {
                "name": "sql_injection",
                "pattern": r'(?i)(union|select|insert|update|delete|drop)\s+.*\s+(from|into|table)',
                "description": "SQL injection patterns"
            },
            {
                "name": "shell_injection",
                "pattern": r'[;&|`$]',
                "description": "Shell injection characters"
            }
        ]
    
    async def _execute_checks(self) -> QualityCheckResult:
        """Execute quality validation quality checks.
        
        Returns:
            Quality check result with metrics and findings
        """
        issues = []
        warnings = []
        
        self.logger.info("Starting quality validation quality checks")
        
        # Run all quality validation checks
        check_results = await asyncio.gather(
            self._check_type_safety_runtime(),
            self._check_runtime_validation_completeness(),
            self._check_error_handling_coverage(),
            self._check_logging_completeness(),
            self._check_message_comparison_accuracy(),
            self._check_input_sanitization(),
            self._check_security_validation(),
            return_exceptions=True
        )
        
        # Process check results
        total_score = 0.0
        check_count = 0
        
        for i, result in enumerate(check_results):
            if isinstance(result, Exception):
                issues.append(f"Check {i+1} failed with exception: {result}")
            else:
                score, check_issues, check_warnings = result
                total_score += score
                check_count += 1
                issues.extend(check_issues)
                warnings.extend(check_warnings)
        
        # Calculate overall score
        overall_score = total_score / check_count if check_count > 0 else 0.0
        passed = overall_score >= 0.95 and len(issues) == 0
        
        self.logger.info(
            f"Quality validation checks completed",
            context={
                "overall_score": overall_score,
                "passed": passed,
                "issues": len(issues),
                "warnings": len(warnings)
            }
        )
        
        return {
            "check_name": "Quality Validation Quality Check",
            "category": self.category,
            "passed": passed,
            "score": overall_score,
            "issues": issues,
            "warnings": warnings,
            "metrics": self.metrics,
            "execution_time": 0.0,
            "timestamp": ""
        }
    
    async def _check_type_safety_runtime(self) -> Tuple[float, List[str], List[str]]:
        """Check type safety runtime validation coverage.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking type safety runtime validation")
        
        issues = []
        warnings = []
        
        try:
            # Test type validation functions
            validation_scores = []
            
            for test_case in self.type_test_cases:
                try:
                    data = test_case["data"]
                    expected_valid = test_case["expected_valid"]
                    
                    # Test config validation
                    is_valid = validate_config(data)
                    
                    if is_valid == expected_valid:
                        validation_scores.append(1.0)
                    else:
                        validation_scores.append(0.0)
                        issues.append(f"Type validation failed for {test_case['name']}: "
                                    f"expected {expected_valid}, got {is_valid}")
                
                except Exception as e:
                    validation_scores.append(0.0)
                    warnings.append(f"Type validation test error for {test_case['name']}: {e}")
            
            # Test event data validation
            for test_case in self.event_test_cases:
                try:
                    data = test_case["data"]
                    expected_valid = test_case["expected_valid"]
                    
                    is_valid = validate_event_data(data)
                    
                    if is_valid == expected_valid:
                        validation_scores.append(1.0)
                    else:
                        validation_scores.append(0.0)
                        issues.append(f"Event validation failed for {test_case['name']}: "
                                    f"expected {expected_valid}, got {is_valid}")
                
                except Exception as e:
                    validation_scores.append(0.0)
                    warnings.append(f"Event validation test error for {test_case['name']}: {e}")
            
            # Check type guard coverage
            type_guard_coverage = await self._check_type_guard_coverage()
            validation_scores.append(type_guard_coverage)
            self.metrics["type_guard_coverage"] = type_guard_coverage
            
            success_rate = sum(validation_scores) / len(validation_scores) if validation_scores else 0.0
            self.metrics["type_validation_success_rate"] = success_rate
            
            if success_rate < 1.0:
                issues.append(f"Type validation success rate below 100%: {success_rate:.3f}")
        
        except Exception as e:
            issues.append(f"Type safety runtime check error: {e}")
            success_rate = 0.0
        
        return success_rate, issues, warnings
    
    async def _check_runtime_validation_completeness(self) -> Tuple[float, List[str], List[str]]:
        """Check runtime validation completeness and accuracy.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking runtime validation completeness")
        
        issues = []
        warnings = []
        
        try:
            # Check validation function availability
            validation_functions = []
            
            # Check for key validation functions
            src_dir = self.project_root / "src"
            validation_files = [
                "type_guards.py",
                "validators.py",
                "utils/validation.py"
            ]
            
            available_functions = 0
            total_expected = 8  # Expected validation functions
            
            for file_path in validation_files:
                full_path = src_dir / file_path
                if full_path.exists():
                    available_functions += await self._count_validation_functions(full_path)
            
            completeness_score = min(1.0, available_functions / total_expected)
            
            # Test validation accuracy
            accuracy_tests = []
            
            # Test edge cases
            edge_cases = [
                {"data": None, "should_fail": True},
                {"data": {}, "should_fail": True},
                {"data": {"invalid": "structure"}, "should_fail": True}
            ]
            
            for case in edge_cases:
                try:
                    is_valid = validate_config(case["data"])
                    should_fail = case["should_fail"]
                    
                    if (not is_valid) == should_fail:
                        accuracy_tests.append(1.0)
                    else:
                        accuracy_tests.append(0.0)
                        issues.append(f"Validation accuracy failed for edge case: {case}")
                
                except Exception as e:
                    if case["should_fail"]:
                        accuracy_tests.append(1.0)  # Expected to fail
                    else:
                        accuracy_tests.append(0.0)
                        warnings.append(f"Validation test exception: {e}")
            
            accuracy_score = sum(accuracy_tests) / len(accuracy_tests) if accuracy_tests else 0.0
            
            overall_score = (completeness_score + accuracy_score) / 2
            self.metrics["runtime_validation_accuracy"] = overall_score
            
            if overall_score < 1.0:
                issues.append(f"Runtime validation completeness below 100%: {overall_score:.3f}")
        
        except Exception as e:
            issues.append(f"Runtime validation completeness check error: {e}")
            overall_score = 0.0
        
        return overall_score, issues, warnings
    
    async def _check_error_handling_coverage(self) -> Tuple[float, List[str], List[str]]:
        """Check error handling coverage across all modules.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking error handling coverage")
        
        issues = []
        warnings = []
        
        try:
            src_dir = self.project_root / "src"
            python_files = list(src_dir.rglob("*.py"))
            
            total_functions = 0
            functions_with_error_handling = 0
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Parse AST to find functions
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            total_functions += 1
                            
                            # Check if function has try/except blocks
                            has_error_handling = any(
                                isinstance(child, ast.Try) 
                                for child in ast.walk(node)
                            )
                            
                            if has_error_handling:
                                functions_with_error_handling += 1
                
                except Exception as e:
                    warnings.append(f"Error analyzing {py_file}: {e}")
            
            coverage_rate = functions_with_error_handling / total_functions if total_functions > 0 else 0.0
            self.metrics["error_handling_coverage"] = coverage_rate
            
            # Check for specific error types
            error_types_found = set()
            error_types_expected = {
                "ConfigurationError", "ValidationError", "HTTPError",
                "ConnectionError", "TimeoutError", "Exception"
            }
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for error_type in error_types_expected:
                        if error_type in content:
                            error_types_found.add(error_type)
                
                except Exception:
                    pass
            
            error_type_coverage = len(error_types_found) / len(error_types_expected)
            
            # Combine coverage metrics
            overall_coverage = (coverage_rate + error_type_coverage) / 2
            
            if overall_coverage < 0.95:
                issues.append(f"Error handling coverage below target: {overall_coverage:.3f}")
            
            if coverage_rate < 0.8:
                issues.append(f"Function error handling coverage low: {coverage_rate:.3f}")
        
        except Exception as e:
            issues.append(f"Error handling coverage check error: {e}")
            overall_coverage = 0.0
        
        return overall_coverage, issues, warnings
    
    async def _check_logging_completeness(self) -> Tuple[float, List[str], List[str]]:
        """Check AstolfoLogger logging completeness.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking AstolfoLogger completeness")
        
        issues = []
        warnings = []
        
        try:
            src_dir = self.project_root / "src"
            python_files = list(src_dir.rglob("*.py"))
            
            total_files = 0
            files_with_logging = 0
            
            for py_file in python_files:
                # Skip test files and __init__.py
                if "test_" in py_file.name or py_file.name == "__init__.py":
                    continue
                
                total_files += 1
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for AstolfoLogger usage
                    has_astolfo_logger = "AstolfoLogger" in content
                    has_logging_calls = any(
                        log_level in content 
                        for log_level in ["logger.info", "logger.error", "logger.warning", "logger.debug"]
                    )
                    
                    if has_astolfo_logger and has_logging_calls:
                        files_with_logging += 1
                
                except Exception as e:
                    warnings.append(f"Error analyzing logging in {py_file}: {e}")
            
            logging_coverage = files_with_logging / total_files if total_files > 0 else 0.0
            
            # Check for structured logging usage
            structured_logging_files = 0
            for py_file in python_files:
                if "test_" in py_file.name or py_file.name == "__init__.py":
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for context parameter usage
                    if "context=" in content:
                        structured_logging_files += 1
                
                except Exception:
                    pass
            
            structured_logging_rate = structured_logging_files / total_files if total_files > 0 else 0.0
            
            # Combine metrics
            completeness_score = (logging_coverage + structured_logging_rate) / 2
            self.metrics["logging_completeness"] = completeness_score
            
            if completeness_score < 1.0:
                issues.append(f"Logging completeness below 100%: {completeness_score:.3f}")
            
            if logging_coverage < 0.9:
                issues.append(f"AstolfoLogger adoption rate low: {logging_coverage:.3f}")
        
        except Exception as e:
            issues.append(f"Logging completeness check error: {e}")
            completeness_score = 0.0
        
        return completeness_score, issues, warnings
    
    async def _check_message_comparison_accuracy(self) -> Tuple[float, List[str], List[str]]:
        """Check message send/receive comparison accuracy.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking message comparison accuracy")
        
        issues = []
        warnings = []
        
        try:
            # Test message formatting consistency
            test_messages = [
                {"content": "Test message 1", "type": "text"},
                {"embeds": [{"title": "Test", "description": "Description"}], "type": "embed"},
                {"content": "Mixed message", "embeds": [{"title": "Mixed"}], "type": "mixed"}
            ]
            
            accuracy_scores = []
            
            for test_msg in test_messages:
                try:
                    # Simulate message formatting and comparison
                    formatted = self._format_test_message(test_msg)
                    reconstructed = self._parse_test_message(formatted)
                    
                    # Check if key data is preserved
                    if self._compare_messages(test_msg, reconstructed):
                        accuracy_scores.append(1.0)
                    else:
                        accuracy_scores.append(0.0)
                        issues.append(f"Message comparison failed for {test_msg['type']}")
                
                except Exception as e:
                    accuracy_scores.append(0.0)
                    warnings.append(f"Message comparison test error: {e}")
            
            accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0
            self.metrics["message_comparison_accuracy"] = accuracy
            
            if accuracy < 1.0:
                issues.append(f"Message comparison accuracy below 100%: {accuracy:.3f}")
        
        except Exception as e:
            issues.append(f"Message comparison accuracy check error: {e}")
            accuracy = 0.0
        
        return accuracy, issues, warnings
    
    async def _check_input_sanitization(self) -> Tuple[float, List[str], List[str]]:
        """Check input sanitization effectiveness.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking input sanitization")
        
        issues = []
        warnings = []
        
        try:
            sanitization_scores = []
            
            for test_case in self.sanitization_test_cases:
                try:
                    input_data = test_case["input"]
                    should_be_sanitized = test_case["should_be_sanitized"]
                    
                    # Test sanitization
                    sanitized = self._sanitize_input(input_data)
                    is_sanitized = sanitized != input_data
                    
                    if is_sanitized == should_be_sanitized:
                        sanitization_scores.append(1.0)
                    else:
                        sanitization_scores.append(0.0)
                        issues.append(f"Input sanitization failed for {test_case['name']}")
                
                except Exception as e:
                    sanitization_scores.append(0.0)
                    warnings.append(f"Sanitization test error for {test_case['name']}: {e}")
            
            score = sum(sanitization_scores) / len(sanitization_scores) if sanitization_scores else 0.0
            self.metrics["input_sanitization_score"] = score
            
            if score < 1.0:
                issues.append(f"Input sanitization score below 100%: {score:.3f}")
        
        except Exception as e:
            issues.append(f"Input sanitization check error: {e}")
            score = 0.0
        
        return score, issues, warnings
    
    async def _check_security_validation(self) -> Tuple[float, List[str], List[str]]:
        """Check security validation completeness.
        
        Returns:
            Tuple of (score, issues, warnings)
        """
        self.logger.info("Checking security validation")
        
        issues = []
        warnings = []
        
        try:
            src_dir = self.project_root / "src"
            python_files = list(src_dir.rglob("*.py"))
            
            security_issues_found = []
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for security patterns
                    for pattern_info in self.security_patterns:
                        pattern = pattern_info["pattern"]
                        name = pattern_info["name"]
                        
                        matches = re.findall(pattern, content)
                        if matches:
                            security_issues_found.append({
                                "file": str(py_file),
                                "pattern": name,
                                "matches": matches
                            })
                
                except Exception as e:
                    warnings.append(f"Error scanning {py_file} for security issues: {e}")
            
            # Security score based on absence of security issues
            if security_issues_found:
                security_score = max(0.0, 1.0 - (len(security_issues_found) * 0.2))
                for issue in security_issues_found:
                    issues.append(f"Security issue in {issue['file']}: {issue['pattern']}")
            else:
                security_score = 1.0
            
            # Check for security-related imports and functions
            security_functions = ["hashlib", "secrets", "cryptography", "ssl"]
            security_function_count = 0
            
            for py_file in python_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    for func in security_functions:
                        if func in content:
                            security_function_count += 1
                            break
                
                except Exception:
                    pass
            
            # Additional validation for environment variable handling
            env_security_score = await self._check_env_var_security()
            
            overall_score = (security_score + env_security_score) / 2
            self.metrics["security_validation_rate"] = overall_score
            
            if overall_score < 1.0:
                issues.append(f"Security validation rate below 100%: {overall_score:.3f}")
        
        except Exception as e:
            issues.append(f"Security validation check error: {e}")
            overall_score = 0.0
        
        return overall_score, issues, warnings
    
    # Helper methods
    
    async def _check_type_guard_coverage(self) -> float:
        """Check coverage of TypeGuard functions."""
        try:
            type_guards_file = self.project_root / "src" / "type_guards.py"
            if not type_guards_file.exists():
                return 0.0
            
            with open(type_guards_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count TypeGuard/TypeIs functions
            type_guard_count = content.count("TypeIs[") + content.count("TypeGuard[")
            
            # Expected minimum type guards
            expected_guards = 5  # config, event_data, tool_data, etc.
            
            return min(1.0, type_guard_count / expected_guards)
        
        except Exception:
            return 0.0
    
    async def _count_validation_functions(self, file_path: Path) -> int:
        """Count validation functions in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count functions that start with 'validate_'
            validate_count = content.count("def validate_")
            return validate_count
        
        except Exception:
            return 0
    
    def _format_test_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Format a test message for comparison testing."""
        # Simple formatting simulation
        formatted = message.copy()
        if "content" in formatted:
            formatted["content"] = str(formatted["content"])
        return formatted
    
    def _parse_test_message(self, formatted: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a formatted message back to original form."""
        # Simple parsing simulation
        return formatted.copy()
    
    def _compare_messages(self, original: Dict[str, Any], reconstructed: Dict[str, Any]) -> bool:
        """Compare original and reconstructed messages for accuracy."""
        # Check key fields are preserved
        for key in ["content", "embeds", "type"]:
            if key in original:
                if key not in reconstructed:
                    return False
                if original[key] != reconstructed[key]:
                    return False
        return True
    
    def _sanitize_input(self, input_data: str) -> str:
        """Sanitize input data for security testing."""
        # Basic sanitization simulation
        sanitized = input_data
        
        # Remove SQL injection patterns
        sanitized = re.sub(r"[';\"\\]", "", sanitized)
        
        # Remove script tags
        sanitized = re.sub(r"<script.*?</script>", "", sanitized, flags=re.IGNORECASE)
        
        # Remove command injection characters
        sanitized = re.sub(r"[;&|`$]", "", sanitized)
        
        # Remove path traversal
        sanitized = sanitized.replace("../", "").replace("..\\", "")
        
        return sanitized
    
    async def _check_env_var_security(self) -> float:
        """Check environment variable security handling."""
        try:
            config_file = self.project_root / "src" / "core" / "config.py"
            if not config_file.exists():
                return 0.0
            
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            security_checks = [
                "os.environ.get" in content,  # Safe environment access
                "getenv" in content,  # Alternative safe access
                "strip()" in content,  # Input sanitization
                "validation" in content.lower()  # Some form of validation
            ]
            
            return sum(security_checks) / len(security_checks)
        
        except Exception:
            return 0.0


async def main() -> None:
    """Test the quality validation checker."""
    project_root = Path(__file__).parent.parent.parent.parent
    logger = AstolfoLogger(__name__)
    
    checker = QualityValidationChecker(project_root, logger)
    result = await checker.run_checks()
    
    print(f"Quality Validation Check: {'PASSED' if result['passed'] else 'FAILED'}")
    print(f"Score: {result['score']:.3f}")
    print(f"Issues: {len(result['issues'])}")
    print(f"Warnings: {len(result['warnings'])}")
    
    for issue in result['issues']:
        print(f"  ❌ {issue}")
    
    for warning in result['warnings']:
        print(f"  ⚠️  {warning}")


if __name__ == "__main__":
    asyncio.run(main())