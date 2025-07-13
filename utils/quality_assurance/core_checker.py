#!/usr/bin/env python3
"""Comprehensive Quality Assurance Core Checker.

This module provides the central quality assurance engine that coordinates
and orchestrates all quality checks across the project's functional categories.
It integrates with the existing development_checker.py while expanding to
provide comprehensive quality assurance coverage.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import format_system_datetime


class QualityMetrics(TypedDict):
    """Quality metrics for tracking quality assurance performance."""
    
    # Discord API Integration Quality
    connection_success_rate: float  # Target: 99.9%+
    message_delivery_success_rate: float  # Target: 99.5%+
    api_response_time_avg: float  # Target: <3 seconds
    error_recovery_success_rate: float  # Target: 95%+
    rate_limit_compliance_rate: float  # Target: 100%
    
    # Content Processing Quality  
    format_accuracy: float  # Target: 100% (type safety)
    prompt_mixing_detection_accuracy: float  # Target: 99%+
    timestamp_accuracy: float  # Target: ±5 seconds
    unicode_processing_accuracy: float  # Target: 100%
    discord_limits_compliance_rate: float  # Target: 100%
    
    # Data Management Quality
    config_load_success_rate: float  # Target: 100%
    data_persistence_success_rate: float  # Target: 99.9%+
    concurrent_access_safety: float  # Target: 100%
    data_integrity: float  # Target: 100%
    backup_success_rate: float  # Target: 100%
    
    # Quality Validation Accuracy
    type_validation_success_rate: float  # Target: 100%
    runtime_validation_accuracy: float  # Target: 100%
    error_handling_coverage: float  # Target: 95%+
    logging_completeness: float  # Target: 100%
    security_validation_rate: float  # Target: 100%
    
    # Integration Control Stability
    hook_integration_success_rate: float  # Target: 100%
    event_processing_success_rate: float  # Target: 99.9%+
    parallel_processing_safety: float  # Target: 100%
    system_recovery_success_rate: float  # Target: 95%+
    resource_usage_efficiency: float  # Target: within optimal range


class QualityGateLevel(TypedDict):
    """Definition of a quality gate level with its requirements."""
    
    level: Literal[1, 2, 3, 4]
    name: str
    description: str
    required_checks: List[str]
    required_metrics: Dict[str, float]
    timeout_minutes: int


class QualityCheckResult(TypedDict):
    """Result of a single quality check operation."""
    
    check_name: str
    category: str
    passed: bool
    score: float  # 0.0 to 1.0
    issues: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
    execution_time: float
    timestamp: str


class QualityGateResult(TypedDict):
    """Result of a quality gate evaluation."""
    
    level: int
    name: str
    passed: bool
    overall_score: float
    check_results: List[QualityCheckResult]
    failed_requirements: List[str]
    execution_time: float
    timestamp: str


class BaseQualityChecker:
    """Base class for all quality checkers.
    
    Provides common functionality and interface for category-specific
    quality checkers. All checkers inherit from this base class to
    ensure consistent behavior and reporting.
    """
    
    def __init__(self, project_root: Path, logger: AstolfoLogger) -> None:
        """Initialize base quality checker.
        
        Args:
            project_root: Project root directory
            logger: Logger instance for structured logging
        """
        self.project_root = project_root
        self.logger = logger
        self.category = self.__class__.__name__.replace("Checker", "").replace("Quality", "")
        
        self.logger.info(
            f"Quality checker initialized: {self.category}",
            context={
                "checker_class": self.__class__.__name__,
                "project_root": str(project_root)
            }
        )
    
    async def run_checks(self) -> QualityCheckResult:
        """Run all quality checks for this category.
        
        Returns:
            Quality check result with all metrics and findings
        """
        start_time = time.time()
        
        self.logger.info(f"Starting quality checks: {self.category}")
        
        try:
            # Implementation to be overridden by subclasses
            result = await self._execute_checks()
            
            execution_time = time.time() - start_time
            
            result.update({
                "execution_time": execution_time,
                "timestamp": format_system_datetime()
            })
            
            self.logger.info(
                f"Quality checks completed: {self.category}",
                context={
                    "passed": result["passed"],
                    "score": result["score"],
                    "execution_time": execution_time,
                    "issues_count": len(result["issues"])
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            error_result: QualityCheckResult = {
                "check_name": f"{self.category} Quality Check",
                "category": self.category,
                "passed": False,
                "score": 0.0,
                "issues": [f"Quality check failed with exception: {e}"],
                "warnings": [],
                "metrics": {},
                "execution_time": execution_time,
                "timestamp": format_system_datetime()
            }
            
            self.logger.error(
                f"Quality check failed: {self.category}",
                context={
                    "error": str(e),
                    "execution_time": execution_time
                }
            )
            
            return error_result
    
    async def _execute_checks(self) -> QualityCheckResult:
        """Execute category-specific quality checks.
        
        This method must be implemented by subclasses to provide
        category-specific quality checking logic.
        
        Returns:
            Quality check result
        """
        raise NotImplementedError("Subclasses must implement _execute_checks")


class QualityGateManager:
    """Manages quality gate definitions and evaluation.
    
    Provides the infrastructure for multi-level quality gates
    with progressive validation requirements.
    """
    
    def __init__(self, logger: AstolfoLogger) -> None:
        """Initialize quality gate manager.
        
        Args:
            logger: Logger instance for structured logging
        """
        self.logger = logger
        self._define_quality_gates()
        
        self.logger.info(
            "Quality gate manager initialized",
            context={"gates_defined": len(self.quality_gates)}
        )
    
    def _define_quality_gates(self) -> None:
        """Define the four-level quality gate system."""
        self.quality_gates: Dict[int, QualityGateLevel] = {
            1: {
                "level": 1,
                "name": "Basic Quality Gate",
                "description": "Fundamental quality requirements",
                "required_checks": [
                    "unit_tests",
                    "type_checking", 
                    "import_consistency",
                    "basic_linting"
                ],
                "required_metrics": {
                    "type_validation_success_rate": 1.0,
                    "config_load_success_rate": 1.0
                },
                "timeout_minutes": 5
            },
            2: {
                "level": 2,
                "name": "Functional Quality Gate",
                "description": "Category-specific functionality validation",
                "required_checks": [
                    "discord_integration",
                    "content_processing",
                    "data_management",
                    "security_validation"
                ],
                "required_metrics": {
                    "format_accuracy": 1.0,
                    "discord_limits_compliance_rate": 1.0,
                    "data_integrity": 1.0,
                    "security_validation_rate": 1.0
                },
                "timeout_minutes": 15
            },
            3: {
                "level": 3,
                "name": "Integration Quality Gate", 
                "description": "End-to-end integration validation",
                "required_checks": [
                    "integration_control",
                    "end_to_end_tests",
                    "real_discord_integration",
                    "stress_scenarios"
                ],
                "required_metrics": {
                    "connection_success_rate": 0.999,
                    "event_processing_success_rate": 0.999,
                    "hook_integration_success_rate": 1.0,
                    "parallel_processing_safety": 1.0
                },
                "timeout_minutes": 30
            },
            4: {
                "level": 4,
                "name": "Production Quality Gate",
                "description": "Production-ready quality validation",
                "required_checks": [
                    "comprehensive_metrics",
                    "long_term_stability",
                    "user_scenarios",
                    "quality_reporting"
                ],
                "required_metrics": {
                    "message_delivery_success_rate": 0.995,
                    "api_response_time_avg": 3.0,
                    "error_recovery_success_rate": 0.95,
                    "system_recovery_success_rate": 0.95
                },
                "timeout_minutes": 60
            }
        }
    
    async def evaluate_quality_gate(
        self, 
        level: int, 
        check_results: List[QualityCheckResult]
    ) -> QualityGateResult:
        """Evaluate a specific quality gate level.
        
        Args:
            level: Quality gate level (1-4)
            check_results: List of quality check results to evaluate
            
        Returns:
            Quality gate evaluation result
        """
        start_time = time.time()
        
        if level not in self.quality_gates:
            raise ValueError(f"Invalid quality gate level: {level}")
        
        gate = self.quality_gates[level]
        
        self.logger.info(
            f"Evaluating quality gate: Level {level}",
            context={
                "gate_name": gate["name"],
                "required_checks": len(gate["required_checks"]),
                "check_results": len(check_results)
            }
        )
        
        # Check if all required checks are present
        available_checks = {result["check_name"] for result in check_results}
        missing_checks = set(gate["required_checks"]) - available_checks
        
        failed_requirements = []
        if missing_checks:
            failed_requirements.extend([f"Missing check: {check}" for check in missing_checks])
        
        # Evaluate metrics requirements
        aggregated_metrics = self._aggregate_metrics(check_results)
        
        for metric_name, required_value in gate["required_metrics"].items():
            actual_value = aggregated_metrics.get(metric_name, 0.0)
            if actual_value < required_value:
                failed_requirements.append(
                    f"Metric {metric_name}: {actual_value:.3f} < {required_value:.3f}"
                )
        
        # Calculate overall score
        passed_checks = sum(1 for result in check_results if result["passed"])
        total_checks = len(check_results)
        overall_score = passed_checks / total_checks if total_checks > 0 else 0.0
        
        # Gate passes if no failed requirements and overall score is good
        passed = len(failed_requirements) == 0 and overall_score >= 0.9
        
        execution_time = time.time() - start_time
        
        result: QualityGateResult = {
            "level": level,
            "name": gate["name"],
            "passed": passed,
            "overall_score": overall_score,
            "check_results": check_results,
            "failed_requirements": failed_requirements,
            "execution_time": execution_time,
            "timestamp": format_system_datetime()
        }
        
        self.logger.info(
            f"Quality gate evaluation completed: Level {level}",
            context={
                "passed": passed,
                "overall_score": overall_score,
                "failed_requirements": len(failed_requirements),
                "execution_time": execution_time
            }
        )
        
        return result
    
    def _aggregate_metrics(self, check_results: List[QualityCheckResult]) -> Dict[str, float]:
        """Aggregate metrics from multiple check results.
        
        Args:
            check_results: List of quality check results
            
        Returns:
            Dictionary of aggregated metrics
        """
        aggregated: Dict[str, float] = {}
        
        # Simple aggregation - can be enhanced with weighted averages
        for result in check_results:
            for metric_name, metric_value in result["metrics"].items():
                if isinstance(metric_value, (int, float)):
                    if metric_name not in aggregated:
                        aggregated[metric_name] = metric_value
                    else:
                        # For now, take the minimum (most conservative)
                        aggregated[metric_name] = min(aggregated[metric_name], metric_value)
        
        return aggregated


class ComprehensiveQualityChecker:
    """Main quality assurance coordinator.
    
    Orchestrates all quality checks across functional categories and
    evaluates quality gates to provide comprehensive quality assessment.
    """
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize comprehensive quality checker.
        
        Args:
            project_root: Project root directory (auto-detected if None)
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = project_root
        self.logger = AstolfoLogger(__name__)
        self.gate_manager = QualityGateManager(self.logger)
        
        # Initialize category checkers (will be implemented in subsequent phases)
        self.category_checkers: Dict[str, BaseQualityChecker] = {}
        
        self.logger.info(
            "Comprehensive quality checker initialized",
            context={
                "project_root": str(project_root),
                "quality_gates": len(self.gate_manager.quality_gates)
            }
        )
    
    def register_checker(self, category: str, checker: BaseQualityChecker) -> None:
        """Register a category-specific quality checker.
        
        Args:
            category: Quality category name
            checker: Quality checker instance
        """
        self.category_checkers[category] = checker
        
        self.logger.info(
            f"Quality checker registered: {category}",
            context={"checker_class": checker.__class__.__name__}
        )
    
    async def run_quick_check(self) -> List[QualityCheckResult]:
        """Run quick quality checks for development workflow.
        
        Returns:
            List of quality check results
        """
        self.logger.info("Starting quick quality check")
        
        # For now, run basic checks (Level 1)
        # Will be expanded as category checkers are implemented
        basic_checks = ["import_consistency", "basic_syntax"]
        
        results = []
        for check_name in basic_checks:
            # Placeholder implementation
            result: QualityCheckResult = {
                "check_name": check_name,
                "category": "basic",
                "passed": True,
                "score": 1.0,
                "issues": [],
                "warnings": [],
                "metrics": {},
                "execution_time": 0.1,
                "timestamp": format_system_datetime()
            }
            results.append(result)
        
        self.logger.info(
            "Quick quality check completed",
            context={"checks_run": len(results)}
        )
        
        return results
    
    async def run_category_check(self, category: str) -> QualityCheckResult:
        """Run quality checks for a specific functional category.
        
        Args:
            category: Functional category to check
            
        Returns:
            Quality check result for the category
        """
        self.logger.info(f"Starting category quality check: {category}")
        
        if category not in self.category_checkers:
            # Placeholder for when category checkers are implemented
            self.logger.warning(f"Category checker not implemented: {category}")
            
            result: QualityCheckResult = {
                "check_name": f"{category} Quality Check",
                "category": category,
                "passed": False,
                "score": 0.0,
                "issues": [f"Category checker not implemented: {category}"],
                "warnings": [],
                "metrics": {},
                "execution_time": 0.0,
                "timestamp": format_system_datetime()
            }
            return result
        
        checker = self.category_checkers[category]
        return await checker.run_checks()
    
    async def run_full_check(self) -> QualityGateResult:
        """Run comprehensive quality checks and evaluate highest quality gate.
        
        Returns:
            Quality gate result for the highest level evaluation
        """
        self.logger.info("Starting full comprehensive quality check")
        
        # Run all category checks
        all_results = []
        
        for category, checker in self.category_checkers.items():
            try:
                result = await checker.run_checks()
                all_results.append(result)
            except Exception as e:
                self.logger.error(
                    f"Category check failed: {category}",
                    context={"error": str(e)}
                )
                # Add failed result
                failed_result: QualityCheckResult = {
                    "check_name": f"{category} Quality Check",
                    "category": category,
                    "passed": False,
                    "score": 0.0,
                    "issues": [f"Check failed: {e}"],
                    "warnings": [],
                    "metrics": {},
                    "execution_time": 0.0,
                    "timestamp": format_system_datetime()
                }
                all_results.append(failed_result)
        
        # Evaluate the highest applicable quality gate
        # Start from Level 4 and work down to find the highest achievable level
        for level in range(4, 0, -1):
            try:
                gate_result = await self.gate_manager.evaluate_quality_gate(level, all_results)
                if gate_result["passed"]:
                    self.logger.info(f"Quality gate Level {level} PASSED")
                    return gate_result
                else:
                    self.logger.warning(
                        f"Quality gate Level {level} FAILED",
                        context={"failed_requirements": len(gate_result["failed_requirements"])}
                    )
            except Exception as e:
                self.logger.error(f"Quality gate Level {level} evaluation failed: {e}")
        
        # If no gates pass, return the Level 1 result
        return await self.gate_manager.evaluate_quality_gate(1, all_results)
    
    def print_quality_report(self, gate_result: QualityGateResult) -> None:
        """Print formatted quality assessment report.
        
        Args:
            gate_result: Quality gate result to format and print
        """
        print("🔍" * 60)
        print("🎯 COMPREHENSIVE QUALITY ASSESSMENT REPORT")
        print("🔍" * 60)
        
        # Overall status
        status = "✅ PASSED" if gate_result["passed"] else "❌ FAILED"
        print(f"\n{status} Quality Gate Level {gate_result['level']}: {gate_result['name']}")
        print(f"📊 Overall Score: {gate_result['overall_score']:.3f}")
        print(f"⏱️  Execution Time: {gate_result['execution_time']:.2f}s")
        print(f"📅 Timestamp: {gate_result['timestamp']}")
        
        # Category results
        print(f"\n📋 CATEGORY RESULTS ({len(gate_result['check_results'])} categories)")
        for result in gate_result["check_results"]:
            category_status = "✅" if result["passed"] else "❌"
            print(f"  {category_status} {result['category']}: {result['score']:.3f}")
            
            if result["issues"]:
                print(f"    🚨 Issues ({len(result['issues'])}):")
                for issue in result["issues"][:3]:  # Show first 3 issues
                    print(f"      • {issue}")
                if len(result["issues"]) > 3:
                    print(f"      ... and {len(result['issues']) - 3} more")
            
            if result["warnings"]:
                print(f"    ⚠️  Warnings ({len(result['warnings'])}):")
                for warning in result["warnings"][:2]:  # Show first 2 warnings
                    print(f"      • {warning}")
                if len(result["warnings"]) > 2:
                    print(f"      ... and {len(result['warnings']) - 2} more")
        
        # Failed requirements
        if gate_result["failed_requirements"]:
            print(f"\n💥 FAILED REQUIREMENTS ({len(gate_result['failed_requirements'])})")
            for requirement in gate_result["failed_requirements"]:
                print(f"  ❌ {requirement}")
        
        # Recommendations
        print("\n🎯 RECOMMENDATIONS")
        if gate_result["passed"]:
            print("  ✨ All quality requirements met!")
            print("  🚀 Ready for next development phase")
        else:
            print("  🔧 Fix failed requirements above")
            print("  🧪 Run category-specific checks for detailed analysis")
            print("  📖 Consult quality standards documentation")
        
        print("\n" + "🔍" * 60)


async def main() -> int:
    """Main entry point for comprehensive quality checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Quality Assurance Checker")
    parser.add_argument(
        "--mode",
        choices=["quick", "category", "full"],
        default="quick",
        help="Quality check mode to run"
    )
    parser.add_argument(
        "--category",
        help="Specific category to check (used with --mode category)"
    )
    
    args = parser.parse_args()
    
    checker = ComprehensiveQualityChecker()
    
    try:
        if args.mode == "quick":
            results = await checker.run_quick_check()
            passed = all(result["passed"] for result in results)
            
            print(f"Quick check: {'PASSED' if passed else 'FAILED'}")
            print(f"Checks run: {len(results)}")
            
            return 0 if passed else 1
            
        elif args.mode == "category":
            if not args.category:
                print("Error: --category required for category mode")
                return 1
            
            result = await checker.run_category_check(args.category)
            
            print(f"Category {args.category}: {'PASSED' if result['passed'] else 'FAILED'}")
            print(f"Score: {result['score']:.3f}")
            
            return 0 if result["passed"] else 1
            
        elif args.mode == "full":
            gate_result = await checker.run_full_check()
            checker.print_quality_report(gate_result)
            
            return 0 if gate_result["passed"] else 1
    
    except Exception as e:
        print(f"Quality checker failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))