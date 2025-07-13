#!/usr/bin/env python3
"""Test suite integrator for unified testing across existing and comprehensive QA frameworks.

This module provides integration between the original test structure (unit/feature/integration)
and the comprehensive quality assurance test suites (discord_integration/content_processing/etc.).
It enables unified test execution, reporting, and quality metrics collection.
"""

import asyncio
import subprocess
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict
from dataclasses import dataclass

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger


class TestSuiteResult(TypedDict):
    """Result of a test suite execution."""
    suite_name: str
    category: str
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    execution_time: float
    success_rate: float
    failures: List[Dict[str, str]]
    errors: List[Dict[str, str]]
    output: str


@dataclass
class TestDiscoveryResult:
    """Result of test discovery process."""
    suite_name: str
    test_path: Path
    category: str
    estimated_test_count: int
    dependencies: List[str]
    priority: str  # "high", "medium", "low"


class TestSuiteIntegrator:
    """Integrator for unified test execution across all test frameworks."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize test suite integrator.
        
        Args:
            project_root: Project root directory (auto-detected if None)
        """
        self.logger = AstolfoLogger(__name__)
        
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = project_root
        self.tests_root = project_root / "tests"
        
        # Test category mappings
        self.category_mappings = {
            # Original test structure
            "unit": {
                "priority": "high",
                "description": "Unit tests for individual components",
                "dependencies": [],
                "timeout": 60
            },
            "feature": {
                "priority": "high", 
                "description": "Feature-level functionality tests",
                "dependencies": [],
                "timeout": 120
            },
            "integration": {
                "priority": "high",
                "description": "Integration tests for component interaction",
                "dependencies": [],
                "timeout": 180
            },
            "timestamp": {
                "priority": "high",
                "description": "Timestamp accuracy and timezone validation",
                "dependencies": [],
                "timeout": 90
            },
            
            # Comprehensive QA test structure
            "discord_integration": {
                "priority": "high",
                "description": "Discord API integration and connectivity tests",
                "dependencies": ["DISCORD_TOKEN", "DISCORD_WEBHOOK_URL"],
                "timeout": 240
            },
            "content_processing": {
                "priority": "high",
                "description": "Content formatting and processing validation",
                "dependencies": [],
                "timeout": 180
            },
            "data_management": {
                "priority": "high",
                "description": "Data persistence and configuration management",
                "dependencies": [],
                "timeout": 150
            },
            "quality_validation": {
                "priority": "medium",
                "description": "Quality assurance and validation checks",
                "dependencies": [],
                "timeout": 120
            },
            "integration_control": {
                "priority": "medium",
                "description": "System integration and control mechanisms",
                "dependencies": [],
                "timeout": 180
            },
            "end_to_end": {
                "priority": "low",
                "description": "Complete workflow and user scenario tests",
                "dependencies": ["DISCORD_TOKEN", "DISCORD_CHANNEL_ID"],
                "timeout": 600
            }
        }
        
        self.logger.info(
            "Test suite integrator initialized",
            context={
                "project_root": str(project_root),
                "tests_root": str(self.tests_root),
                "categories": len(self.category_mappings)
            }
        )
    
    def discover_test_suites(self) -> List[TestDiscoveryResult]:
        """Discover all available test suites.
        
        Returns:
            List of discovered test suites with metadata
        """
        self.logger.info("Discovering test suites")
        
        discovered_suites = []
        
        for category, config in self.category_mappings.items():
            category_path = self.tests_root / category
            
            if not category_path.exists():
                self.logger.warning(f"Test category directory not found: {category_path}")
                continue
            
            # Find test files in category
            test_files = list(category_path.glob("test_*.py"))
            
            for test_file in test_files:
                # Estimate test count by counting test methods
                test_count = self._estimate_test_count(test_file)
                
                suite_name = test_file.stem
                
                discovered_suites.append(TestDiscoveryResult(
                    suite_name=suite_name,
                    test_path=test_file,
                    category=category,
                    estimated_test_count=test_count,
                    dependencies=config["dependencies"],
                    priority=config["priority"]
                ))
        
        # Sort by priority and category
        priority_order = {"high": 0, "medium": 1, "low": 2}
        discovered_suites.sort(key=lambda x: (priority_order.get(x.priority, 3), x.category, x.suite_name))
        
        self.logger.info(
            "Test suite discovery completed",
            context={
                "total_suites": len(discovered_suites),
                "by_category": {cat: len([s for s in discovered_suites if s.category == cat]) 
                             for cat in self.category_mappings.keys()},
                "by_priority": {pri: len([s for s in discovered_suites if s.priority == pri])
                              for pri in ["high", "medium", "low"]}
            }
        )
        
        return discovered_suites
    
    def _estimate_test_count(self, test_file: Path) -> int:
        """Estimate number of tests in a test file.
        
        Args:
            test_file: Path to test file
            
        Returns:
            Estimated number of test methods
        """
        try:
            content = test_file.read_text(encoding='utf-8')
            # Count test methods (def test_*)
            import re
            test_methods = re.findall(r'^\s*def test_\w+', content, re.MULTILINE)
            return len(test_methods)
        except Exception as e:
            self.logger.warning(f"Could not estimate test count for {test_file}: {e}")
            return 1
    
    def check_dependencies(self, dependencies: List[str]) -> Tuple[bool, List[str]]:
        """Check if test dependencies are available.
        
        Args:
            dependencies: List of required environment variables or conditions
            
        Returns:
            Tuple of (all_satisfied, missing_dependencies)
        """
        import os
        
        missing = []
        for dep in dependencies:
            if not os.getenv(dep):
                missing.append(dep)
        
        return len(missing) == 0, missing
    
    async def run_test_suite(
        self, 
        suite: TestDiscoveryResult,
        verbose: bool = False,
        timeout_override: Optional[int] = None
    ) -> TestSuiteResult:
        """Run a single test suite.
        
        Args:
            suite: Test suite to run
            verbose: Enable verbose output
            timeout_override: Override default timeout
            
        Returns:
            Test suite execution results
        """
        start_time = time.time()
        
        # Check dependencies
        deps_satisfied, missing_deps = self.check_dependencies(suite.dependencies)
        if not deps_satisfied:
            self.logger.warning(
                f"Skipping {suite.suite_name} due to missing dependencies: {missing_deps}"
            )
            
            return TestSuiteResult(
                suite_name=suite.suite_name,
                category=suite.category,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                tests_skipped=suite.estimated_test_count,
                execution_time=0.0,
                success_rate=0.0,
                failures=[],
                errors=[{"error": f"Missing dependencies: {missing_deps}"}],
                output=f"Skipped due to missing dependencies: {missing_deps}"
            )
        
        # Determine timeout
        timeout = timeout_override or self.category_mappings[suite.category]["timeout"]
        
        # Build command
        cmd = [
            "uv", "run", "--no-sync", "--python", "3.13",
            "python", "-m", "unittest", 
            f"tests.{suite.category}.{suite.suite_name}"
        ]
        
        if verbose:
            cmd.append("-v")
        
        self.logger.info(
            f"Running test suite: {suite.suite_name}",
            context={
                "category": suite.category,
                "estimated_tests": suite.estimated_test_count,
                "timeout": timeout,
                "command": " ".join(cmd)
            }
        )
        
        try:
            # Run tests
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            output = result.stdout + result.stderr
            
            # Parse test results
            test_results = self._parse_unittest_output(output)
            
            success = result.returncode == 0
            
            suite_result = TestSuiteResult(
                suite_name=suite.suite_name,
                category=suite.category,
                tests_run=test_results["tests_run"],
                tests_passed=test_results["tests_passed"],
                tests_failed=test_results["tests_failed"],
                tests_skipped=test_results["tests_skipped"],
                execution_time=execution_time,
                success_rate=(test_results["tests_passed"] / test_results["tests_run"]) * 100 
                           if test_results["tests_run"] > 0 else 0.0,
                failures=test_results["failures"],
                errors=test_results["errors"],
                output=output
            )
            
            self.logger.info(
                f"Test suite completed: {suite.suite_name}",
                context={
                    "success": success,
                    "tests_run": test_results["tests_run"],
                    "tests_passed": test_results["tests_passed"],
                    "execution_time": execution_time,
                    "success_rate": suite_result["success_rate"]
                }
            )
            
            return suite_result
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_msg = f"Test suite {suite.suite_name} timed out after {timeout}s"
            
            self.logger.error(error_msg)
            
            return TestSuiteResult(
                suite_name=suite.suite_name,
                category=suite.category,
                tests_run=0,
                tests_passed=0,
                tests_failed=suite.estimated_test_count,
                tests_skipped=0,
                execution_time=execution_time,
                success_rate=0.0,
                failures=[],
                errors=[{"error": error_msg}],
                output=error_msg
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Failed to run test suite {suite.suite_name}: {e}"
            
            self.logger.error(error_msg)
            
            return TestSuiteResult(
                suite_name=suite.suite_name,
                category=suite.category,
                tests_run=0,
                tests_passed=0,
                tests_failed=suite.estimated_test_count,
                tests_skipped=0,
                execution_time=execution_time,
                success_rate=0.0,
                failures=[],
                errors=[{"error": error_msg}],
                output=error_msg
            )
    
    def _parse_unittest_output(self, output: str) -> Dict[str, Any]:
        """Parse unittest output to extract test results.
        
        Args:
            output: Raw unittest output
            
        Returns:
            Parsed test statistics and failures
        """
        import re
        
        # Initialize results
        results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "failures": [],
            "errors": []
        }
        
        # Parse "Ran X tests" line
        ran_match = re.search(r'Ran (\d+) tests? in', output)
        if ran_match:
            results["tests_run"] = int(ran_match.group(1))
        
        # Parse result line (OK, FAILED, etc.)
        if "OK" in output and "FAILED" not in output:
            results["tests_passed"] = results["tests_run"]
        else:
            # Parse FAILED line
            failed_match = re.search(r'FAILED \(.*?failures=(\d+).*?\)', output)
            if failed_match:
                results["tests_failed"] = int(failed_match.group(1))
            
            # Parse errors
            errors_match = re.search(r'errors=(\d+)', output)
            if errors_match:
                error_count = int(errors_match.group(1))
                results["tests_failed"] += error_count
            
            # Parse skipped
            skipped_match = re.search(r'skipped=(\d+)', output)
            if skipped_match:
                results["tests_skipped"] = int(skipped_match.group(1))
            
            results["tests_passed"] = (results["tests_run"] - 
                                     results["tests_failed"] - 
                                     results["tests_skipped"])
        
        # Extract failure details
        failure_sections = re.findall(
            r'(FAIL|ERROR): (test_\w+) \((.*?)\)\n(.*?)(?=\n(?:FAIL|ERROR|=|$))', 
            output, 
            re.DOTALL
        )
        
        for fail_type, test_name, test_class, details in failure_sections:
            failure_info = {
                "type": fail_type,
                "test": test_name,
                "class": test_class,
                "details": details.strip()
            }
            
            if fail_type == "FAIL":
                results["failures"].append(failure_info)
            else:
                results["errors"].append(failure_info)
        
        return results
    
    async def run_category_tests(
        self, 
        category: str,
        verbose: bool = False,
        parallel: bool = True,
        max_concurrent: int = 3
    ) -> List[TestSuiteResult]:
        """Run all tests in a specific category.
        
        Args:
            category: Test category to run
            verbose: Enable verbose output
            parallel: Run tests in parallel
            max_concurrent: Maximum concurrent test executions
            
        Returns:
            List of test suite results
        """
        discovered_suites = self.discover_test_suites()
        category_suites = [s for s in discovered_suites if s.category == category]
        
        if not category_suites:
            self.logger.warning(f"No test suites found for category: {category}")
            return []
        
        self.logger.info(
            f"Running {len(category_suites)} test suites in category: {category}",
            context={"parallel": parallel, "max_concurrent": max_concurrent}
        )
        
        if parallel and len(category_suites) > 1:
            # Run in parallel with concurrency limit
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def run_with_semaphore(suite):
                async with semaphore:
                    return await self.run_test_suite(suite, verbose)
            
            tasks = [run_with_semaphore(suite) for suite in category_suites]
            results = await asyncio.gather(*tasks)
        else:
            # Run sequentially
            results = []
            for suite in category_suites:
                result = await self.run_test_suite(suite, verbose)
                results.append(result)
        
        return results
    
    async def run_all_tests(
        self,
        categories: Optional[List[str]] = None,
        priorities: Optional[List[str]] = None,
        verbose: bool = False,
        parallel: bool = True,
        max_concurrent: int = 3,
        skip_slow: bool = False
    ) -> Dict[str, List[TestSuiteResult]]:
        """Run all test suites with filtering options.
        
        Args:
            categories: List of categories to run (all if None)
            priorities: List of priorities to include (all if None)
            verbose: Enable verbose output
            parallel: Run tests in parallel within categories
            max_concurrent: Maximum concurrent executions per category
            skip_slow: Skip slow test categories (end_to_end)
            
        Returns:
            Dictionary mapping categories to their test results
        """
        discovered_suites = self.discover_test_suites()
        
        # Filter by categories
        if categories:
            discovered_suites = [s for s in discovered_suites if s.category in categories]
        
        # Filter by priorities
        if priorities:
            discovered_suites = [s for s in discovered_suites if s.priority in priorities]
        
        # Skip slow tests if requested
        if skip_slow:
            discovered_suites = [s for s in discovered_suites if s.category != "end_to_end"]
        
        # Group by category
        category_suites = {}
        for suite in discovered_suites:
            if suite.category not in category_suites:
                category_suites[suite.category] = []
            category_suites[suite.category].append(suite)
        
        self.logger.info(
            "Running comprehensive test suite",
            context={
                "total_categories": len(category_suites),
                "total_suites": len(discovered_suites),
                "filtered_categories": list(category_suites.keys()),
                "parallel": parallel
            }
        )
        
        # Run tests by category
        all_results = {}
        
        for category, suites in category_suites.items():
            self.logger.info(f"Starting category: {category} ({len(suites)} suites)")
            
            category_results = await self.run_category_tests(
                category, verbose, parallel, max_concurrent
            )
            all_results[category] = category_results
        
        return all_results
    
    def generate_integration_report(
        self, 
        results: Dict[str, List[TestSuiteResult]]
    ) -> Dict[str, Any]:
        """Generate comprehensive integration report.
        
        Args:
            results: Test results by category
            
        Returns:
            Comprehensive integration report
        """
        total_suites = sum(len(category_results) for category_results in results.values())
        total_tests = sum(suite["tests_run"] for category_results in results.values() 
                         for suite in category_results)
        total_passed = sum(suite["tests_passed"] for category_results in results.values() 
                          for suite in category_results)
        total_failed = sum(suite["tests_failed"] for category_results in results.values() 
                          for suite in category_results)
        total_skipped = sum(suite["tests_skipped"] for category_results in results.values() 
                           for suite in category_results)
        
        total_execution_time = sum(suite["execution_time"] for category_results in results.values() 
                                  for suite in category_results)
        
        overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0.0
        
        # Category summaries
        category_summaries = {}
        for category, category_results in results.items():
            if not category_results:
                continue
                
            cat_tests = sum(suite["tests_run"] for suite in category_results)
            cat_passed = sum(suite["tests_passed"] for suite in category_results)
            cat_failed = sum(suite["tests_failed"] for suite in category_results)
            cat_time = sum(suite["execution_time"] for suite in category_results)
            
            category_summaries[category] = {
                "suites": len(category_results),
                "tests_run": cat_tests,
                "tests_passed": cat_passed,
                "tests_failed": cat_failed,
                "success_rate": (cat_passed / cat_tests) * 100 if cat_tests > 0 else 0.0,
                "execution_time": cat_time,
                "priority": self.category_mappings[category]["priority"]
            }
        
        # Quality assessment
        quality_level = "excellent"
        if overall_success_rate < 95:
            quality_level = "good"
        if overall_success_rate < 85:
            quality_level = "acceptable"
        if overall_success_rate < 70:
            quality_level = "poor"
        
        report = {
            "summary": {
                "total_categories": len(results),
                "total_suites": total_suites,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "overall_success_rate": overall_success_rate,
                "total_execution_time": total_execution_time,
                "quality_level": quality_level
            },
            "category_summaries": category_summaries,
            "detailed_results": results,
            "recommendations": self._generate_integration_recommendations(results, overall_success_rate)
        }
        
        self.logger.info(
            "Integration report generated",
            context={
                "total_tests": total_tests,
                "success_rate": overall_success_rate,
                "quality_level": quality_level,
                "execution_time": total_execution_time
            }
        )
        
        return report
    
    def _generate_integration_recommendations(
        self, 
        results: Dict[str, List[TestSuiteResult]], 
        success_rate: float
    ) -> List[str]:
        """Generate recommendations based on test results.
        
        Args:
            results: Test results by category
            success_rate: Overall success rate
            
        Returns:
            List of actionable recommendations
        """
        recommendations = []
        
        # Overall recommendations
        if success_rate >= 95:
            recommendations.append("Excellent test coverage and quality - ready for production")
        elif success_rate >= 85:
            recommendations.append("Good test quality - address failing tests before deployment")
        elif success_rate >= 70:
            recommendations.append("Acceptable quality - significant improvement needed")
        else:
            recommendations.append("Poor test quality - critical issues must be resolved")
        
        # Category-specific recommendations
        for category, category_results in results.items():
            if not category_results:
                continue
            
            failed_suites = [s for s in category_results if s["tests_failed"] > 0]
            if failed_suites:
                recommendations.append(
                    f"Fix {len(failed_suites)} failing test suite(s) in {category} category"
                )
            
            slow_suites = [s for s in category_results if s["execution_time"] > 120]
            if slow_suites:
                recommendations.append(
                    f"Optimize {len(slow_suites)} slow test suite(s) in {category} category"
                )
        
        # Integration-specific recommendations
        recommendations.append("Run development checker before committing changes")
        recommendations.append("Execute category-specific tests for modified components")
        recommendations.append("Verify timestamp accuracy for time-related changes")
        
        return recommendations


async def main():
    """Main function for standalone test suite integration."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Test Suite Integrator")
    parser.add_argument("--category", help="Run specific category only")
    parser.add_argument("--categories", nargs="+", help="Run multiple categories")
    parser.add_argument("--priority", choices=["high", "medium", "low"], 
                       help="Run tests of specific priority")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", action="store_true", default=True,
                       help="Run tests in parallel")
    parser.add_argument("--sequential", action="store_true", 
                       help="Run tests sequentially")
    parser.add_argument("--max-concurrent", type=int, default=3,
                       help="Maximum concurrent test executions")
    parser.add_argument("--skip-slow", action="store_true",
                       help="Skip slow test categories")
    parser.add_argument("--discover-only", action="store_true",
                       help="Only discover tests, don't run them")
    parser.add_argument("--report", help="Save report to JSON file")
    
    args = parser.parse_args()
    
    integrator = TestSuiteIntegrator()
    
    if args.discover_only:
        # Discovery only
        discovered = integrator.discover_test_suites()
        
        print(f"Discovered {len(discovered)} test suites:")
        for suite in discovered:
            print(f"  {suite.category}/{suite.suite_name} "
                  f"({suite.estimated_test_count} tests, {suite.priority} priority)")
        
        return 0
    
    # Determine execution mode
    parallel = args.parallel and not args.sequential
    
    # Run tests
    if args.category:
        results = {args.category: await integrator.run_category_tests(
            args.category, args.verbose, parallel, args.max_concurrent
        )}
    else:
        categories = args.categories
        priorities = [args.priority] if args.priority else None
        
        results = await integrator.run_all_tests(
            categories=categories,
            priorities=priorities,
            verbose=args.verbose,
            parallel=parallel,
            max_concurrent=args.max_concurrent,
            skip_slow=args.skip_slow
        )
    
    # Generate report
    report = integrator.generate_integration_report(results)
    
    # Save report if requested
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to: {args.report}")
    
    # Print summary
    summary = report["summary"]
    print(f"\nTest Integration Summary:")
    print(f"  Categories: {summary['total_categories']}")
    print(f"  Test Suites: {summary['total_suites']}")
    print(f"  Tests Run: {summary['total_tests']}")
    print(f"  Passed: {summary['total_passed']}")
    print(f"  Failed: {summary['total_failed']}")
    print(f"  Skipped: {summary['total_skipped']}")
    print(f"  Success Rate: {summary['overall_success_rate']:.1f}%")
    print(f"  Quality Level: {summary['quality_level']}")
    print(f"  Execution Time: {summary['total_execution_time']:.1f}s")
    
    if report["recommendations"]:
        print(f"\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  • {rec}")
    
    # Return exit code based on results
    return 0 if summary["total_failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))