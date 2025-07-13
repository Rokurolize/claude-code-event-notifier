#!/usr/bin/env python3
"""Development quality checker for preventing timestamp and other issues.

This module provides pre-commit checks and development workflow validation
to prevent issues like UTC timestamp leaks from reaching production.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger


class CheckResult(TypedDict):
    """Result of a development check."""
    check_name: str
    passed: bool
    issues: list[str]
    warnings: list[str]
    details: dict[str, Any]


class DevelopmentChecker:
    """Development quality checker for preventing common issues."""
    
    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize development checker.
        
        Args:
            project_root: Project root directory (auto-detected if None)
        """
        self.logger = AstolfoLogger(__name__)
        
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = project_root
        self.src_path = project_root / "src"
        
        self.logger.info(
            "Development checker initialized",
            context={
                "project_root": str(project_root),
                "src_path": str(self.src_path)
            }
        )
    
    def check_utc_timestamp_leaks(self) -> CheckResult:
        """Check for UTC timestamp patterns in user-facing code.
        
        Returns:
            Check result with any UTC leak violations found
        """
        self.logger.info("Checking for UTC timestamp leaks")
        
        # Patterns that indicate UTC timestamp usage in user-facing code
        utc_patterns = [
            (r"datetime\.now\(UTC\)", "Direct UTC datetime.now() call"),
            (r"datetime\.utcnow\(\)", "Deprecated datetime.utcnow() call"),
            (r"\.strftime.*UTC", "UTC in strftime format"),
            (r"timezone\.utc", "Direct UTC timezone usage"),
            (r"datetime\.now\(\)\.utc", "UTC conversion of current time"),
            (r"time\.gmtime\(\)", "GMT time usage (UTC equivalent)")
        ]
        
        # Files to check (user-facing modules)
        check_patterns = [
            "src/formatters/*.py",
            "src/handlers/*.py", 
            "src/core/config*.py",
            "src/discord_notifier.py"
        ]
        
        violations = []
        warnings = []
        
        for pattern in check_patterns:
            files = list(self.project_root.glob(pattern))
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                try:
                    content = file_path.read_text(encoding='utf-8')
                    lines = content.splitlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        for utc_pattern, description in utc_patterns:
                            if re.search(utc_pattern, line):
                                # Check if it's in a comment or docstring
                                stripped = line.strip()
                                if stripped.startswith('#') or '"""' in line or "'''" in line:
                                    warnings.append(
                                        f"{file_path.relative_to(self.project_root)}:{line_num}: "
                                        f"UTC pattern in comment/docstring: {description}"
                                    )
                                else:
                                    violations.append(
                                        f"{file_path.relative_to(self.project_root)}:{line_num}: "
                                        f"{description} - {line.strip()}"
                                    )
                
                except (UnicodeDecodeError, PermissionError) as e:
                    warnings.append(f"Could not read {file_path}: {e}")
        
        passed = len(violations) == 0
        
        result: CheckResult = {
            "check_name": "UTC Timestamp Leak Detection",
            "passed": passed,
            "issues": violations,
            "warnings": warnings,
            "details": {
                "patterns_checked": len(utc_patterns),
                "files_scanned": sum(len(list(self.project_root.glob(p))) for p in check_patterns),
                "violations_found": len(violations)
            }
        }
        
        self.logger.info(
            "UTC timestamp leak check completed",
            context={
                "passed": passed,
                "violations": len(violations),
                "warnings": len(warnings)
            }
        )
        
        return result
    
    def check_timestamp_test_coverage(self) -> CheckResult:
        """Check that timestamp functionality has adequate test coverage.
        
        Returns:
            Check result for timestamp test coverage
        """
        self.logger.info("Checking timestamp test coverage")
        
        issues = []
        warnings = []
        
        # Check for timestamp-specific tests
        timestamp_test_path = self.project_root / "tests" / "timestamp"
        if not timestamp_test_path.exists():
            issues.append("Timestamp-specific test directory not found")
        else:
            test_files = list(timestamp_test_path.glob("test_*.py"))
            if len(test_files) == 0:
                issues.append("No timestamp test files found")
            elif len(test_files) < 2:
                warnings.append("Limited timestamp test coverage (consider adding more test files)")
        
        # Check for realtime timestamp tests
        required_test_methods = [
            "test_pre_tool_use_timestamp",
            "test_post_tool_use_timestamp", 
            "test_stop_event_timestamp",
            "test_notification_timestamp"
        ]
        
        found_methods = []
        if timestamp_test_path.exists():
            for test_file in timestamp_test_path.glob("*.py"):
                try:
                    content = test_file.read_text()
                    for method in required_test_methods:
                        if f"def {method}" in content:
                            found_methods.append(method)
                except (UnicodeDecodeError, PermissionError):
                    warnings.append(f"Could not read test file: {test_file}")
        
        missing_methods = set(required_test_methods) - set(found_methods)
        if missing_methods:
            issues.extend([f"Missing timestamp test method: {method}" for method in missing_methods])
        
        passed = len(issues) == 0
        
        result: CheckResult = {
            "check_name": "Timestamp Test Coverage",
            "passed": passed,
            "issues": issues,
            "warnings": warnings,
            "details": {
                "required_methods": len(required_test_methods),
                "found_methods": len(found_methods),
                "missing_methods": list(missing_methods),
                "test_directory_exists": timestamp_test_path.exists()
            }
        }
        
        self.logger.info(
            "Timestamp test coverage check completed",
            context={
                "passed": passed,
                "issues": len(issues),
                "found_methods": len(found_methods)
            }
        )
        
        return result
    
    def run_realtime_timestamp_tests(self) -> CheckResult:
        """Run timestamp accuracy tests to verify current implementation.
        
        Returns:
            Check result for realtime timestamp test execution
        """
        self.logger.info("Running realtime timestamp tests")
        
        issues = []
        warnings = []
        test_output = ""
        
        try:
            # Run timestamp tests
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
                timeout=60
            )
            
            test_output = result.stdout + result.stderr
            
            if result.returncode != 0:
                issues.append(f"Timestamp tests failed with exit code {result.returncode}")
                issues.append(f"Test output: {test_output}")
            
        except subprocess.TimeoutExpired:
            issues.append("Timestamp tests timed out after 60 seconds")
        except FileNotFoundError:
            issues.append("Could not run timestamp tests - uv or python not found")
        except Exception as e:
            issues.append(f"Failed to run timestamp tests: {e}")
        
        passed = len(issues) == 0
        
        result: CheckResult = {
            "check_name": "Realtime Timestamp Tests",
            "passed": passed,
            "issues": issues,
            "warnings": warnings,
            "details": {
                "test_output": test_output,
                "command_used": " ".join(cmd) if 'cmd' in locals() else "N/A"
            }
        }
        
        self.logger.info(
            "Realtime timestamp tests completed",
            context={
                "passed": passed,
                "issues": len(issues)
            }
        )
        
        return result
    
    def check_import_consistency(self) -> CheckResult:
        """Check for import consistency and circular import issues.
        
        Returns:
            Check result for import consistency
        """
        self.logger.info("Checking import consistency")
        
        issues = []
        warnings = []
        
        # Check for circular imports by attempting to import main modules
        test_imports = [
            "src.discord_notifier",
            "src.formatters.event_formatters", 
            "src.utils.datetime_utils",
            "src.core.config",
            "src.handlers.discord_sender"
        ]
        
        for import_name in test_imports:
            try:
                __import__(import_name)
            except ImportError as e:
                issues.append(f"Import error for {import_name}: {e}")
            except Exception as e:
                warnings.append(f"Unexpected error importing {import_name}: {e}")
        
        passed = len(issues) == 0
        
        result: CheckResult = {
            "check_name": "Import Consistency",
            "passed": passed,
            "issues": issues,
            "warnings": warnings,
            "details": {
                "imports_tested": len(test_imports),
                "successful_imports": len(test_imports) - len(issues)
            }
        }
        
        self.logger.info(
            "Import consistency check completed",
            context={
                "passed": passed,
                "issues": len(issues)
            }
        )
        
        return result
    
    def run_all_checks(self) -> list[CheckResult]:
        """Run all development quality checks.
        
        Returns:
            List of all check results
        """
        self.logger.info("Running all development quality checks")
        
        checks = [
            self.check_utc_timestamp_leaks,
            self.check_timestamp_test_coverage,
            self.run_realtime_timestamp_tests,
            self.check_import_consistency
        ]
        
        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                self.logger.error(f"Check failed with exception: {e}")
                results.append({
                    "check_name": f"FAILED: {check.__name__}",
                    "passed": False,
                    "issues": [f"Check crashed: {e}"],
                    "warnings": [],
                    "details": {}
                })
        
        passed_checks = sum(1 for r in results if r["passed"])
        total_checks = len(results)
        
        self.logger.info(
            "All development checks completed",
            context={
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "overall_success": passed_checks == total_checks
            }
        )
        
        return results
    
    def print_check_results(self, results: list[CheckResult]) -> None:
        """Print formatted check results to console.
        
        Args:
            results: List of check results to print
        """
        print("🔍" * 50)
        print("🛠️  DEVELOPMENT QUALITY CHECK RESULTS")
        print("🔍" * 50)
        
        overall_passed = 0
        
        for result in results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"\n{status} {result['check_name']}")
            
            if result["passed"]:
                overall_passed += 1
            
            if result["issues"]:
                print(f"  ❌ Issues ({len(result['issues'])}):")
                for issue in result["issues"]:
                    print(f"    • {issue}")
            
            if result["warnings"]:
                print(f"  ⚠️  Warnings ({len(result['warnings'])}):")
                for warning in result["warnings"]:
                    print(f"    • {warning}")
            
            if result["details"]:
                print(f"  📊 Details: {result['details']}")
        
        print("\n" + "🔍" * 50)
        print(f"📊 SUMMARY: {overall_passed}/{len(results)} checks passed")
        
        if overall_passed == len(results):
            print("🎉 ALL CHECKS PASSED! Ready for commit.")
        else:
            print("💥 SOME CHECKS FAILED! Please fix issues before committing.")
        
        print("🔍" * 50)


def main() -> int:
    """Main entry point for development checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Development Quality Checker")
    parser.add_argument("--enhanced", action="store_true", 
                       help="Use enhanced development checker with comprehensive QA")
    parser.add_argument("--no-comprehensive", action="store_true",
                       help="Skip comprehensive QA checks (only with --enhanced)")
    
    args = parser.parse_args()
    
    if args.enhanced:
        # Use enhanced development checker
        try:
            import asyncio
            from utils.development_checker_enhanced import EnhancedDevelopmentChecker
            
            async def run_enhanced():
                enhanced_checker = EnhancedDevelopmentChecker()
                include_comprehensive = not args.no_comprehensive
                results = await enhanced_checker.run_all_enhanced_checks(include_comprehensive)
                enhanced_checker.print_enhanced_results(results)
                
                failed_checks = sum(1 for r in results if not r["passed"])
                return 1 if failed_checks > 0 else 0
            
            return asyncio.run(run_enhanced())
            
        except ImportError as e:
            print(f"Enhanced checker not available: {e}")
            print("Falling back to original development checker...")
    
    # Use original development checker
    checker = DevelopmentChecker()
    results = checker.run_all_checks()
    checker.print_check_results(results)
    
    # Return exit code based on results
    failed_checks = sum(1 for r in results if not r["passed"])
    return 1 if failed_checks > 0 else 0


if __name__ == "__main__":
    sys.exit(main())