#!/usr/bin/env python3
"""Unified test runner for integrated execution of existing and comprehensive QA tests.

This module provides a unified interface to run all test suites (original and QA)
with integrated reporting, quality metrics, and comprehensive analysis.
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
from dataclasses import dataclass

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger

# Import QA components
try:
    from utils.quality_assurance.test_suite_integrator import TestSuiteIntegrator, TestSuiteResult
    from utils.quality_assurance.test_migration_assistant import TestMigrationAssistant
    from utils.development_checker_enhanced import EnhancedDevelopmentChecker
    COMPREHENSIVE_QA_AVAILABLE = True
except ImportError as e:
    COMPREHENSIVE_QA_AVAILABLE = False
    print(f"Note: Comprehensive QA components not available: {e}")


class UnifiedTestResult(TypedDict):
    """Unified test execution result."""
    execution_id: str
    timestamp: str
    total_duration: float
    development_checker_results: Optional[Dict[str, Any]]
    test_suite_results: Dict[str, List[TestSuiteResult]]
    quality_metrics: Dict[str, Any]
    overall_status: str  # "passed", "failed", "partial"
    summary: Dict[str, Any]
    recommendations: List[str]


@dataclass
class TestExecutionConfig:
    """Configuration for test execution."""
    run_development_checker: bool = True
    run_legacy_tests: bool = True
    run_qa_tests: bool = True
    include_slow_tests: bool = False
    parallel_execution: bool = True
    max_concurrent: int = 3
    verbose: bool = False
    categories: Optional[List[str]] = None
    priorities: Optional[List[str]] = None
    timeout_override: Optional[int] = None
    save_artifacts: bool = True
    artifacts_dir: Optional[Path] = None


class UnifiedTestRunner:
    """Unified test runner for comprehensive test execution."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize unified test runner.
        
        Args:
            project_root: Project root directory (auto-detected if None)
        """
        self.logger = AstolfoLogger(__name__)
        
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = project_root
        
        # Initialize components
        self.integrator = TestSuiteIntegrator(project_root) if COMPREHENSIVE_QA_AVAILABLE else None
        self.migration_assistant = TestMigrationAssistant(project_root) if COMPREHENSIVE_QA_AVAILABLE else None
        self.enhanced_checker = EnhancedDevelopmentChecker(project_root) if COMPREHENSIVE_QA_AVAILABLE else None
        
        self.logger.info(
            "Unified test runner initialized",
            context={
                "project_root": str(project_root),
                "comprehensive_qa_available": COMPREHENSIVE_QA_AVAILABLE
            }
        )
    
    async def run_comprehensive_tests(self, config: TestExecutionConfig) -> UnifiedTestResult:
        """Run comprehensive test suite with all components.
        
        Args:
            config: Test execution configuration
            
        Returns:
            Unified test execution results
        """
        execution_id = f"unified_test_{int(time.time())}"
        start_time = time.time()
        
        self.logger.info(
            f"Starting comprehensive test execution: {execution_id}",
            context={
                "config": {
                    "development_checker": config.run_development_checker,
                    "legacy_tests": config.run_legacy_tests,
                    "qa_tests": config.run_qa_tests,
                    "parallel": config.parallel_execution,
                    "categories": config.categories,
                    "priorities": config.priorities
                }
            }
        )
        
        results = {
            "execution_id": execution_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "development_checker_results": None,
            "test_suite_results": {},
            "quality_metrics": {},
            "overall_status": "failed",
            "summary": {},
            "recommendations": []
        }
        
        # Phase 1: Development Checker
        if config.run_development_checker and self.enhanced_checker:
            self.logger.info("Phase 1: Running enhanced development checker")
            try:
                dev_checker_results = await self.enhanced_checker.run_all_enhanced_checks(
                    include_comprehensive=COMPREHENSIVE_QA_AVAILABLE
                )
                results["development_checker_results"] = {
                    "results": dev_checker_results,
                    "passed": all(r["passed"] for r in dev_checker_results),
                    "total_checks": len(dev_checker_results),
                    "passed_checks": sum(1 for r in dev_checker_results if r["passed"]),
                    "average_quality_score": sum(r.get("quality_score", 0) for r in dev_checker_results) / len(dev_checker_results) if dev_checker_results else 0
                }
                
                self.logger.info(
                    "Development checker completed",
                    context={
                        "passed": results["development_checker_results"]["passed"],
                        "checks": len(dev_checker_results),
                        "avg_score": results["development_checker_results"]["average_quality_score"]
                    }
                )
            except Exception as e:
                self.logger.error(f"Development checker failed: {e}")
                results["development_checker_results"] = {"error": str(e), "passed": False}
        
        # Phase 2: Test Suite Execution
        if (config.run_legacy_tests or config.run_qa_tests) and self.integrator:
            self.logger.info("Phase 2: Running test suites")
            try:
                test_results = await self.integrator.run_all_tests(
                    categories=config.categories,
                    priorities=config.priorities,
                    verbose=config.verbose,
                    parallel=config.parallel_execution,
                    max_concurrent=config.max_concurrent,
                    skip_slow=not config.include_slow_tests
                )
                results["test_suite_results"] = test_results
                
                # Calculate test metrics
                total_tests = sum(suite["tests_run"] for category_results in test_results.values() 
                                for suite in category_results)
                passed_tests = sum(suite["tests_passed"] for category_results in test_results.values() 
                                 for suite in category_results)
                
                self.logger.info(
                    "Test suites completed",
                    context={
                        "categories": len(test_results),
                        "total_tests": total_tests,
                        "passed_tests": passed_tests,
                        "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
                    }
                )
            except Exception as e:
                self.logger.error(f"Test suite execution failed: {e}")
                results["test_suite_results"] = {"error": str(e)}
        
        # Phase 3: Quality Metrics Calculation
        results["quality_metrics"] = self._calculate_quality_metrics(results)
        
        # Phase 4: Overall Assessment
        results["overall_status"] = self._determine_overall_status(results)
        results["summary"] = self._generate_summary(results)
        results["recommendations"] = self._generate_recommendations(results)
        
        # Calculate total duration
        results["total_duration"] = time.time() - start_time
        
        # Phase 5: Artifact Generation
        if config.save_artifacts:
            await self._save_artifacts(results, config.artifacts_dir)
        
        self.logger.info(
            f"Comprehensive test execution completed: {execution_id}",
            context={
                "duration": results["total_duration"],
                "status": results["overall_status"],
                "overall_score": results["quality_metrics"].get("overall_quality_score", 0)
            }
        )
        
        return results
    
    def _calculate_quality_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics.
        
        Args:
            results: Partial results from test execution
            
        Returns:
            Quality metrics dictionary
        """
        metrics = {
            "overall_quality_score": 0.0,
            "development_checker_score": 0.0,
            "test_suite_score": 0.0,
            "coverage_metrics": {},
            "performance_metrics": {},
            "reliability_metrics": {}
        }
        
        scores = []
        weights = []
        
        # Development checker score
        if results.get("development_checker_results") and results["development_checker_results"].get("passed"):
            dev_score = results["development_checker_results"].get("average_quality_score", 0)
            metrics["development_checker_score"] = dev_score
            scores.append(dev_score)
            weights.append(0.3)  # 30% weight
        
        # Test suite score
        test_results = results.get("test_suite_results", {})
        if test_results and not test_results.get("error"):
            total_tests = sum(suite["tests_run"] for category_results in test_results.values() 
                            for suite in category_results)
            passed_tests = sum(suite["tests_passed"] for category_results in test_results.values() 
                             for suite in category_results)
            
            test_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
            metrics["test_suite_score"] = test_score
            scores.append(test_score)
            weights.append(0.7)  # 70% weight
            
            # Coverage metrics
            metrics["coverage_metrics"] = {
                "total_test_suites": sum(len(category_results) for category_results in test_results.values()),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": sum(suite["tests_failed"] for category_results in test_results.values() 
                                  for suite in category_results),
                "skipped_tests": sum(suite["tests_skipped"] for category_results in test_results.values() 
                                   for suite in category_results),
                "success_rate": test_score
            }
            
            # Performance metrics
            total_execution_time = sum(suite["execution_time"] for category_results in test_results.values() 
                                     for suite in category_results)
            metrics["performance_metrics"] = {
                "total_execution_time": total_execution_time,
                "average_test_time": total_execution_time / total_tests if total_tests > 0 else 0,
                "slowest_suite": max((suite["execution_time"] for category_results in test_results.values() 
                                    for suite in category_results), default=0)
            }
            
            # Reliability metrics
            category_success_rates = []
            for category_results in test_results.values():
                if category_results:
                    cat_total = sum(suite["tests_run"] for suite in category_results)
                    cat_passed = sum(suite["tests_passed"] for suite in category_results)
                    if cat_total > 0:
                        category_success_rates.append(cat_passed / cat_total * 100)
            
            metrics["reliability_metrics"] = {
                "category_consistency": min(category_success_rates) if category_success_rates else 0,
                "categories_tested": len([cr for cr in test_results.values() if cr]),
                "average_category_success": sum(category_success_rates) / len(category_success_rates) if category_success_rates else 0
            }
        
        # Calculate overall score
        if scores and weights:
            total_weight = sum(weights)
            weighted_score = sum(score * weight for score, weight in zip(scores, weights))
            metrics["overall_quality_score"] = weighted_score / total_weight
        
        return metrics
    
    def _determine_overall_status(self, results: Dict[str, Any]) -> str:
        """Determine overall execution status.
        
        Args:
            results: Complete test results
            
        Returns:
            Overall status: "passed", "failed", "partial"
        """
        dev_checker_passed = (
            results.get("development_checker_results", {}).get("passed", False)
            if results.get("development_checker_results") else True
        )
        
        test_suites_passed = True
        test_results = results.get("test_suite_results", {})
        if test_results and not test_results.get("error"):
            total_failed = sum(suite["tests_failed"] for category_results in test_results.values() 
                             for suite in category_results)
            test_suites_passed = total_failed == 0
        
        overall_score = results.get("quality_metrics", {}).get("overall_quality_score", 0)
        
        if dev_checker_passed and test_suites_passed and overall_score >= 85:
            return "passed"
        elif overall_score >= 60:
            return "partial"
        else:
            return "failed"
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate execution summary.
        
        Args:
            results: Complete test results
            
        Returns:
            Execution summary
        """
        summary = {
            "execution_time": results.get("total_duration", 0),
            "overall_status": results.get("overall_status", "failed"),
            "quality_score": results.get("quality_metrics", {}).get("overall_quality_score", 0)
        }
        
        # Development checker summary
        dev_results = results.get("development_checker_results")
        if dev_results and not dev_results.get("error"):
            summary["development_checker"] = {
                "passed": dev_results.get("passed", False),
                "total_checks": dev_results.get("total_checks", 0),
                "passed_checks": dev_results.get("passed_checks", 0),
                "average_score": dev_results.get("average_quality_score", 0)
            }
        
        # Test suite summary
        test_results = results.get("test_suite_results", {})
        if test_results and not test_results.get("error"):
            coverage = results.get("quality_metrics", {}).get("coverage_metrics", {})
            summary["test_suites"] = {
                "categories_tested": len(test_results),
                "total_suites": coverage.get("total_test_suites", 0),
                "total_tests": coverage.get("total_tests", 0),
                "success_rate": coverage.get("success_rate", 0)
            }
        
        return summary
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations.
        
        Args:
            results: Complete test results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        overall_score = results.get("quality_metrics", {}).get("overall_quality_score", 0)
        status = results.get("overall_status", "failed")
        
        # Overall recommendations
        if status == "passed":
            recommendations.append("Excellent quality! Ready for production deployment")
        elif status == "partial":
            recommendations.append("Good quality with some issues - address failures before deployment")
        else:
            recommendations.append("Poor quality - critical issues must be resolved")
        
        # Development checker recommendations
        dev_results = results.get("development_checker_results")
        if dev_results and not dev_results.get("passed"):
            recommendations.append("Fix development checker violations before proceeding")
        
        # Test suite recommendations
        test_results = results.get("test_suite_results", {})
        if test_results and not test_results.get("error"):
            coverage = results.get("quality_metrics", {}).get("coverage_metrics", {})
            
            if coverage.get("failed_tests", 0) > 0:
                recommendations.append(f"Fix {coverage['failed_tests']} failing test(s)")
            
            if coverage.get("success_rate", 0) < 95:
                recommendations.append("Improve test success rate to at least 95%")
            
            # Performance recommendations
            perf = results.get("quality_metrics", {}).get("performance_metrics", {})
            if perf.get("slowest_suite", 0) > 300:  # 5 minutes
                recommendations.append("Optimize slow test suites to improve execution time")
        
        # Quality score recommendations
        if overall_score < 85:
            recommendations.append("Increase overall quality score to at least 85 for production readiness")
        
        # Integration recommendations
        recommendations.append("Run timestamp accuracy tests for time-related changes")
        recommendations.append("Execute development checker before every commit")
        recommendations.append("Monitor quality trends over time")
        
        return recommendations
    
    async def _save_artifacts(self, results: Dict[str, Any], artifacts_dir: Optional[Path]) -> None:
        """Save test artifacts and reports.
        
        Args:
            results: Complete test results
            artifacts_dir: Directory to save artifacts (auto-generated if None)
        """
        if artifacts_dir is None:
            artifacts_dir = self.project_root / "test_artifacts" / results["execution_id"]
        
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Save main results
        results_file = artifacts_dir / "unified_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Save summary report
        summary_file = artifacts_dir / "test_summary.json"
        with open(summary_file, 'w') as f:
            json.dump({
                "execution_id": results["execution_id"],
                "timestamp": results["timestamp"],
                "summary": results["summary"],
                "quality_metrics": results["quality_metrics"],
                "recommendations": results["recommendations"]
            }, f, indent=2, default=str)
        
        # Save detailed test outputs if available
        test_results = results.get("test_suite_results", {})
        if test_results and not test_results.get("error"):
            for category, category_results in test_results.items():
                category_dir = artifacts_dir / category
                category_dir.mkdir(exist_ok=True)
                
                for suite in category_results:
                    suite_file = category_dir / f"{suite['suite_name']}_output.txt"
                    with open(suite_file, 'w') as f:
                        f.write(suite.get("output", ""))
        
        self.logger.info(f"Test artifacts saved to: {artifacts_dir}")


def main():
    """Main function for unified test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Test Runner")
    parser.add_argument("--no-dev-checker", action="store_true",
                       help="Skip development checker")
    parser.add_argument("--no-legacy", action="store_true",
                       help="Skip legacy tests")
    parser.add_argument("--no-qa", action="store_true",
                       help="Skip QA tests")
    parser.add_argument("--include-slow", action="store_true",
                       help="Include slow tests")
    parser.add_argument("--sequential", action="store_true",
                       help="Run tests sequentially")
    parser.add_argument("--max-concurrent", type=int, default=3,
                       help="Maximum concurrent executions")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--categories", nargs="+",
                       help="Specific categories to run")
    parser.add_argument("--priorities", nargs="+", choices=["high", "medium", "low"],
                       help="Specific priorities to run")
    parser.add_argument("--timeout", type=int,
                       help="Override timeout for test execution")
    parser.add_argument("--artifacts-dir", type=Path,
                       help="Directory to save test artifacts")
    parser.add_argument("--no-artifacts", action="store_true",
                       help="Don't save test artifacts")
    
    args = parser.parse_args()
    
    # Create configuration
    config = TestExecutionConfig(
        run_development_checker=not args.no_dev_checker,
        run_legacy_tests=not args.no_legacy,
        run_qa_tests=not args.no_qa,
        include_slow_tests=args.include_slow,
        parallel_execution=not args.sequential,
        max_concurrent=args.max_concurrent,
        verbose=args.verbose,
        categories=args.categories,
        priorities=args.priorities,
        timeout_override=args.timeout,
        save_artifacts=not args.no_artifacts,
        artifacts_dir=args.artifacts_dir
    )
    
    # Run tests
    async def run_tests():
        runner = UnifiedTestRunner()
        results = await runner.run_comprehensive_tests(config)
        
        # Print summary
        print("\n" + "="*80)
        print("UNIFIED TEST EXECUTION SUMMARY")
        print("="*80)
        
        summary = results["summary"]
        print(f"Execution ID: {results['execution_id']}")
        print(f"Status: {results['overall_status'].upper()}")
        print(f"Quality Score: {results['quality_metrics']['overall_quality_score']:.1f}/100")
        print(f"Execution Time: {results['total_duration']:.1f}s")
        
        if "development_checker" in summary:
            dc = summary["development_checker"]
            print(f"Development Checker: {dc['passed_checks']}/{dc['total_checks']} passed")
        
        if "test_suites" in summary:
            ts = summary["test_suites"]
            print(f"Test Suites: {ts['total_tests']} tests, {ts['success_rate']:.1f}% success rate")
        
        if results["recommendations"]:
            print("\nRecommendations:")
            for rec in results["recommendations"]:
                print(f"  • {rec}")
        
        if config.save_artifacts:
            print(f"\nArtifacts saved to test_artifacts/{results['execution_id']}/")
        
        print("="*80)
        
        # Return appropriate exit code
        return 0 if results["overall_status"] in ["passed", "partial"] else 1
    
    return asyncio.run(run_tests())


if __name__ == "__main__":
    sys.exit(main())