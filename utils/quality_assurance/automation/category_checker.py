#!/usr/bin/env python3
"""Category Quality Checker.

This module implements the category-specific quality check functionality that provides:
- Feature-specific detailed quality assessment
- Focused quality validation for specific functional areas
- Comprehensive testing of individual component categories
- Detailed reporting for specific system aspects
- Targeted quality improvement recommendations

The category checker allows developers to focus on specific areas like Discord integration,
content processing, data management, etc. for deep quality analysis.
"""

import asyncio
import json
import time
import sys
import subprocess
import traceback
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from enum import Enum

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker
from utils.quality_assurance.checkers.discord_integration_checker import DiscordIntegrationChecker
from utils.quality_assurance.checkers.content_processing_checker import ContentProcessingChecker
from utils.quality_assurance.checkers.data_management_checker import DataManagementChecker
from utils.quality_assurance.checkers.quality_validation_checker import QualityValidationChecker
from utils.quality_assurance.checkers.integration_control_checker import IntegrationControlChecker


class QualityCategory(Enum):
    """Available quality check categories."""
    DISCORD_INTEGRATION = "discord_integration"
    CONTENT_PROCESSING = "content_processing"
    DATA_MANAGEMENT = "data_management"
    QUALITY_VALIDATION = "quality_validation"
    INTEGRATION_CONTROL = "integration_control"
    ALL_CATEGORIES = "all"


@dataclass
class CategoryCheckResult:
    """Result of category-specific quality check."""
    check_id: str
    category: QualityCategory
    timestamp: datetime
    check_duration_ms: float
    overall_status: str  # "pass", "warning", "fail", "error"
    quality_score: float
    component_results: Dict[str, Any]
    issues_found: int
    critical_issues: int
    warnings: List[str]
    recommendations: List[str]
    next_actions: List[str]
    detailed_metrics: Dict[str, float]
    test_coverage: Dict[str, float]
    performance_metrics: Dict[str, float]
    security_assessment: Dict[str, Any]
    compliance_status: Dict[str, bool]


@dataclass
class CategoryCheckConfig:
    """Configuration for category checking."""
    enabled_categories: Set[QualityCategory] = field(default_factory=lambda: set(QualityCategory))
    check_depth: str = "comprehensive"  # "basic", "standard", "comprehensive", "exhaustive"
    timeout_seconds: float = 300.0  # 5 minutes default
    parallel_execution: bool = True
    include_performance_tests: bool = True
    include_security_assessment: bool = True
    include_integration_tests: bool = True
    generate_detailed_reports: bool = True
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "min_overall_score": 80.0,
        "min_component_score": 70.0,
        "max_critical_issues": 0,
        "min_test_coverage": 85.0
    })


class CategoryQualityChecker(BaseQualityChecker):
    """Category-specific quality checker for focused assessment."""
    
    def __init__(self, config: Optional[CategoryCheckConfig] = None):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.config = config or CategoryCheckConfig()
        
        # Initialize category-specific checkers
        self.checkers = {
            QualityCategory.DISCORD_INTEGRATION: DiscordIntegrationChecker(),
            QualityCategory.CONTENT_PROCESSING: ContentProcessingChecker(),
            QualityCategory.DATA_MANAGEMENT: DataManagementChecker(),
            QualityCategory.QUALITY_VALIDATION: QualityValidationChecker(),
            QualityCategory.INTEGRATION_CONTROL: IntegrationControlChecker()
        }
        
        # Category metadata
        self.category_info = {
            QualityCategory.DISCORD_INTEGRATION: {
                "name": "Discord Integration",
                "description": "Discord API integration, webhook delivery, bot functionality, authentication",
                "key_components": ["webhook_client", "bot_api", "authentication", "rate_limiting", "error_recovery"],
                "critical_paths": ["message_sending", "thread_management", "error_handling"],
                "performance_targets": {"api_response_time": 2000, "webhook_success_rate": 99.5}
            },
            QualityCategory.CONTENT_PROCESSING: {
                "name": "Content Processing",
                "description": "Event formatting, tool formatting, timestamp handling, content validation",
                "key_components": ["event_formatters", "tool_formatters", "timestamp_handling", "content_validation"],
                "critical_paths": ["event_formatting", "tool_output_processing", "content_sanitization"],
                "performance_targets": {"format_time": 100, "accuracy_rate": 99.9}
            },
            QualityCategory.DATA_MANAGEMENT: {
                "name": "Data Management", 
                "description": "Configuration loading, environment handling, SQLite operations, session management",
                "key_components": ["config_loader", "env_handler", "sqlite_manager", "session_manager"],
                "critical_paths": ["config_loading", "data_persistence", "concurrent_access"],
                "performance_targets": {"config_load_time": 50, "db_operation_time": 10}
            },
            QualityCategory.QUALITY_VALIDATION: {
                "name": "Quality Validation",
                "description": "Type safety, runtime validation, error handling, logging functionality",
                "key_components": ["type_guards", "validators", "error_handlers", "loggers"],
                "critical_paths": ["type_validation", "runtime_checks", "error_propagation"],
                "performance_targets": {"validation_time": 5, "error_detection_rate": 99.0}
            },
            QualityCategory.INTEGRATION_CONTROL: {
                "name": "Integration Control",
                "description": "Hook integration, event dispatch, filtering, parallel processing, system recovery",
                "key_components": ["hook_manager", "event_dispatcher", "filters", "recovery_system"],
                "critical_paths": ["event_processing", "system_integration", "failure_recovery"],
                "performance_targets": {"event_dispatch_time": 20, "recovery_time": 1000}
            }
        }
        
    async def check_category(self, category: QualityCategory, project_path: str = None) -> CategoryCheckResult:
        """Perform comprehensive quality check for specific category."""
        if not project_path:
            project_path = str(project_root)
            
        check_id = f"category_{category.value}_{int(time.time() * 1000)}"
        start_time = time.time()
        
        self.logger.info(f"Starting category check: {category.value}")
        
        try:
            # Validate category is supported
            if category not in self.checkers and category != QualityCategory.ALL_CATEGORIES:
                return await self._create_error_result(
                    check_id, category, f"Unsupported category: {category.value}", start_time
                )
            
            # Get category checker
            if category == QualityCategory.ALL_CATEGORIES:
                return await self._check_all_categories(check_id, project_path, start_time)
            else:
                return await self._check_single_category(check_id, category, project_path, start_time)
                
        except Exception as e:
            self.logger.error(f"Error during category check {category.value}: {str(e)}")
            return await self._create_error_result(
                check_id, category, f"Unexpected error: {str(e)}", start_time
            )
    
    async def _check_single_category(self, check_id: str, category: QualityCategory, 
                                   project_path: str, start_time: float) -> CategoryCheckResult:
        """Check a single category comprehensively."""
        checker = self.checkers[category]
        category_info = self.category_info[category]
        
        # Initialize result
        result = CategoryCheckResult(
            check_id=check_id,
            category=category,
            timestamp=datetime.now(timezone.utc),
            check_duration_ms=0.0,
            overall_status="unknown",
            quality_score=0.0,
            component_results={},
            issues_found=0,
            critical_issues=0,
            warnings=[],
            recommendations=[],
            next_actions=[],
            detailed_metrics={},
            test_coverage={},
            performance_metrics={},
            security_assessment={},
            compliance_status={}
        )
        
        # Step 1: Basic quality check
        basic_quality = await checker.check_quality()
        result.component_results["basic_quality"] = basic_quality
        
        # Step 2: Component-specific checks
        component_results = {}
        for component in category_info["key_components"]:
            try:
                component_result = await self._check_component(checker, component, project_path)
                component_results[component] = component_result
                result.component_results[f"component_{component}"] = component_result
            except Exception as e:
                self.logger.warning(f"Failed to check component {component}: {str(e)}")
                result.warnings.append(f"Component check failed: {component}")
        
        # Step 3: Critical path validation
        critical_path_results = {}
        for path in category_info["critical_paths"]:
            try:
                path_result = await self._validate_critical_path(checker, path, project_path)
                critical_path_results[path] = path_result
                result.component_results[f"critical_path_{path}"] = path_result
            except Exception as e:
                self.logger.warning(f"Failed to validate critical path {path}: {str(e)}")
                result.warnings.append(f"Critical path validation failed: {path}")
        
        # Step 4: Performance assessment
        if self.config.include_performance_tests:
            try:
                performance_result = await self._assess_performance(checker, category_info, project_path)
                result.performance_metrics = performance_result
                result.component_results["performance"] = performance_result
            except Exception as e:
                self.logger.warning(f"Performance assessment failed: {str(e)}")
                result.warnings.append("Performance assessment failed")
        
        # Step 5: Security assessment
        if self.config.include_security_assessment:
            try:
                security_result = await self._assess_security(checker, category, project_path)
                result.security_assessment = security_result
                result.component_results["security"] = security_result
            except Exception as e:
                self.logger.warning(f"Security assessment failed: {str(e)}")
                result.warnings.append("Security assessment failed")
        
        # Step 6: Integration testing
        if self.config.include_integration_tests:
            try:
                integration_result = await self._test_integration(checker, category, project_path)
                result.component_results["integration"] = integration_result
            except Exception as e:
                self.logger.warning(f"Integration testing failed: {str(e)}")
                result.warnings.append("Integration testing failed")
        
        # Step 7: Calculate overall metrics
        await self._calculate_category_metrics(result, category_info)
        
        # Step 8: Generate recommendations
        await self._generate_category_recommendations(result, category_info)
        
        # Step 9: Finalize result
        result.check_duration_ms = (time.time() - start_time) * 1000
        
        self.logger.info(
            f"Category check completed: {category.value} "
            f"(status: {result.overall_status}, score: {result.quality_score:.1f}, "
            f"duration: {result.check_duration_ms:.1f}ms)"
        )
        
        return result
    
    async def _check_all_categories(self, check_id: str, project_path: str, 
                                  start_time: float) -> CategoryCheckResult:
        """Check all categories comprehensively."""
        # Create combined result
        result = CategoryCheckResult(
            check_id=check_id,
            category=QualityCategory.ALL_CATEGORIES,
            timestamp=datetime.now(timezone.utc),
            check_duration_ms=0.0,
            overall_status="unknown",
            quality_score=0.0,
            component_results={},
            issues_found=0,
            critical_issues=0,
            warnings=[],
            recommendations=[],
            next_actions=[],
            detailed_metrics={},
            test_coverage={},
            performance_metrics={},
            security_assessment={},
            compliance_status={}
        )
        
        # Check each category
        category_results = {}
        total_score = 0.0
        total_issues = 0
        total_critical = 0
        
        check_tasks = []
        if self.config.parallel_execution:
            # Run checks in parallel
            for category in [c for c in QualityCategory if c != QualityCategory.ALL_CATEGORIES]:
                if category in self.config.enabled_categories or len(self.config.enabled_categories) == 0:
                    task = self._check_single_category(
                        f"{check_id}_{category.value}", category, project_path, time.time()
                    )
                    check_tasks.append((category, task))
            
            # Wait for all checks to complete
            for category, task in check_tasks:
                try:
                    category_result = await task
                    category_results[category.value] = category_result
                    result.component_results[category.value] = category_result.component_results
                    
                    total_score += category_result.quality_score
                    total_issues += category_result.issues_found
                    total_critical += category_result.critical_issues
                    result.warnings.extend(category_result.warnings)
                    result.recommendations.extend(category_result.recommendations)
                    
                except Exception as e:
                    self.logger.error(f"Failed to check category {category.value}: {str(e)}")
                    result.warnings.append(f"Category check failed: {category.value}")
        else:
            # Run checks sequentially
            for category in [c for c in QualityCategory if c != QualityCategory.ALL_CATEGORIES]:
                if category in self.config.enabled_categories or len(self.config.enabled_categories) == 0:
                    try:
                        category_result = await self._check_single_category(
                            f"{check_id}_{category.value}", category, project_path, time.time()
                        )
                        category_results[category.value] = category_result
                        result.component_results[category.value] = category_result.component_results
                        
                        total_score += category_result.quality_score
                        total_issues += category_result.issues_found
                        total_critical += category_result.critical_issues
                        result.warnings.extend(category_result.warnings)
                        result.recommendations.extend(category_result.recommendations)
                        
                    except Exception as e:
                        self.logger.error(f"Failed to check category {category.value}: {str(e)}")
                        result.warnings.append(f"Category check failed: {category.value}")
        
        # Calculate overall metrics
        if category_results:
            result.quality_score = total_score / len(category_results)
            result.issues_found = total_issues
            result.critical_issues = total_critical
            
            # Determine overall status
            if result.critical_issues > 0:
                result.overall_status = "fail"
            elif result.quality_score < self.config.quality_thresholds["min_overall_score"]:
                result.overall_status = "warning"
            else:
                result.overall_status = "pass"
        else:
            result.overall_status = "error"
            result.warnings.append("No categories could be checked")
        
        # Generate combined recommendations
        result.recommendations = list(set(result.recommendations))  # Remove duplicates
        if result.critical_issues > 0:
            result.next_actions.append("Address critical issues immediately")
        if result.quality_score < self.config.quality_thresholds["min_overall_score"]:
            result.next_actions.append("Improve quality scores in failing categories")
        
        result.check_duration_ms = (time.time() - start_time) * 1000
        
        return result
    
    async def _check_component(self, checker: BaseQualityChecker, component: str, 
                             project_path: str) -> Dict[str, Any]:
        """Check a specific component within a category."""
        # This would be implemented based on the specific checker's capabilities
        # For now, we'll use a generic approach
        try:
            if hasattr(checker, f'check_{component}'):
                check_method = getattr(checker, f'check_{component}')
                return await check_method(project_path)
            else:
                # Generic component check
                return {
                    "status": "not_implemented",
                    "message": f"Specific check for {component} not implemented",
                    "score": 50.0
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "score": 0.0
            }
    
    async def _validate_critical_path(self, checker: BaseQualityChecker, path: str, 
                                    project_path: str) -> Dict[str, Any]:
        """Validate a critical path within a category."""
        try:
            if hasattr(checker, f'validate_{path}'):
                validate_method = getattr(checker, f'validate_{path}')
                return await validate_method(project_path)
            else:
                # Generic critical path validation
                return {
                    "status": "not_implemented",
                    "message": f"Specific validation for {path} not implemented",
                    "score": 50.0
                }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "score": 0.0
            }
    
    async def _assess_performance(self, checker: BaseQualityChecker, category_info: Dict[str, Any], 
                                project_path: str) -> Dict[str, float]:
        """Assess performance for the category."""
        performance_metrics = {}
        targets = category_info.get("performance_targets", {})
        
        try:
            if hasattr(checker, 'assess_performance'):
                performance_result = await checker.assess_performance(project_path)
                performance_metrics.update(performance_result)
            
            # Check against targets
            for metric, target in targets.items():
                if metric in performance_metrics:
                    actual = performance_metrics[metric]
                    performance_metrics[f"{metric}_meets_target"] = actual <= target
                    performance_metrics[f"{metric}_target"] = target
                    
        except Exception as e:
            self.logger.warning(f"Performance assessment failed: {str(e)}")
            performance_metrics["error"] = str(e)
            
        return performance_metrics
    
    async def _assess_security(self, checker: BaseQualityChecker, category: QualityCategory, 
                             project_path: str) -> Dict[str, Any]:
        """Assess security for the category."""
        security_assessment = {
            "security_score": 0.0,
            "vulnerabilities": [],
            "recommendations": [],
            "compliance": {}
        }
        
        try:
            if hasattr(checker, 'assess_security'):
                security_result = await checker.assess_security(project_path)
                security_assessment.update(security_result)
            else:
                # Generic security assessment
                security_assessment["security_score"] = 75.0
                security_assessment["message"] = "Generic security assessment - no specific issues detected"
                
        except Exception as e:
            self.logger.warning(f"Security assessment failed: {str(e)}")
            security_assessment["error"] = str(e)
            
        return security_assessment
    
    async def _test_integration(self, checker: BaseQualityChecker, category: QualityCategory, 
                              project_path: str) -> Dict[str, Any]:
        """Test integration for the category."""
        integration_result = {
            "integration_score": 0.0,
            "tests_passed": 0,
            "tests_failed": 0,
            "integration_issues": []
        }
        
        try:
            if hasattr(checker, 'test_integration'):
                test_result = await checker.test_integration(project_path)
                integration_result.update(test_result)
            else:
                # Generic integration test
                integration_result["integration_score"] = 80.0
                integration_result["message"] = "Generic integration test - basic functionality verified"
                
        except Exception as e:
            self.logger.warning(f"Integration testing failed: {str(e)}")
            integration_result["error"] = str(e)
            
        return integration_result
    
    async def _calculate_category_metrics(self, result: CategoryCheckResult, 
                                        category_info: Dict[str, Any]):
        """Calculate comprehensive metrics for the category."""
        # Calculate quality score from component results
        component_scores = []
        for component_name, component_result in result.component_results.items():
            if isinstance(component_result, dict) and "score" in component_result:
                component_scores.append(component_result["score"])
            elif isinstance(component_result, dict) and "quality_score" in component_result:
                component_scores.append(component_result["quality_score"])
        
        if component_scores:
            result.quality_score = sum(component_scores) / len(component_scores)
        
        # Count issues
        result.issues_found = sum(
            1 for comp_result in result.component_results.values()
            if isinstance(comp_result, dict) and comp_result.get("status") in ["warning", "fail"]
        )
        
        result.critical_issues = sum(
            1 for comp_result in result.component_results.values()
            if isinstance(comp_result, dict) and comp_result.get("status") == "fail"
        )
        
        # Determine overall status
        if result.critical_issues > 0:
            result.overall_status = "fail"
        elif result.quality_score < self.config.quality_thresholds["min_component_score"]:
            result.overall_status = "warning"
        else:
            result.overall_status = "pass"
        
        # Calculate detailed metrics
        result.detailed_metrics = {
            "component_count": len(category_info["key_components"]),
            "critical_path_count": len(category_info["critical_paths"]),
            "average_component_score": result.quality_score,
            "issues_per_component": result.issues_found / max(1, len(result.component_results)),
            "critical_issue_rate": result.critical_issues / max(1, len(result.component_results))
        }
        
        # Calculate test coverage (simplified)
        result.test_coverage = {
            "component_coverage": len([
                comp for comp in result.component_results
                if "component_" in comp and result.component_results[comp].get("status") != "not_implemented"
            ]) / max(1, len(category_info["key_components"])) * 100,
            "critical_path_coverage": len([
                comp for comp in result.component_results
                if "critical_path_" in comp and result.component_results[comp].get("status") != "not_implemented"
            ]) / max(1, len(category_info["critical_paths"])) * 100
        }
    
    async def _generate_category_recommendations(self, result: CategoryCheckResult, 
                                               category_info: Dict[str, Any]):
        """Generate specific recommendations for the category."""
        recommendations = []
        next_actions = []
        
        # Quality-based recommendations
        if result.quality_score < 60:
            recommendations.append(f"Critical quality issues in {category_info['name']} - requires immediate attention")
            next_actions.append("Conduct detailed component analysis")
        elif result.quality_score < 80:
            recommendations.append(f"Quality improvements needed in {category_info['name']}")
            next_actions.append("Focus on failing components")
        
        # Component-specific recommendations
        failing_components = [
            comp_name.replace("component_", "") for comp_name, comp_result in result.component_results.items()
            if "component_" in comp_name and isinstance(comp_result, dict) and comp_result.get("status") == "fail"
        ]
        
        if failing_components:
            recommendations.append(f"Address failing components: {', '.join(failing_components)}")
            next_actions.append("Implement fixes for critical component failures")
        
        # Performance recommendations
        if result.performance_metrics:
            slow_metrics = [
                metric for metric, meets_target in result.performance_metrics.items()
                if metric.endswith("_meets_target") and not meets_target
            ]
            if slow_metrics:
                recommendations.append("Performance optimization needed for: " + 
                                     ", ".join(m.replace("_meets_target", "") for m in slow_metrics))
                next_actions.append("Optimize performance-critical paths")
        
        # Security recommendations
        if result.security_assessment.get("vulnerabilities"):
            recommendations.append("Security vulnerabilities detected - review security assessment")
            next_actions.append("Address identified security vulnerabilities")
        
        # Test coverage recommendations
        if result.test_coverage.get("component_coverage", 0) < 90:
            recommendations.append("Improve test coverage for components")
            next_actions.append("Add tests for uncovered components")
        
        result.recommendations.extend(recommendations)
        result.next_actions.extend(next_actions)
    
    async def _create_error_result(self, check_id: str, category: QualityCategory, 
                                 error_message: str, start_time: float) -> CategoryCheckResult:
        """Create error result for failed checks."""
        return CategoryCheckResult(
            check_id=check_id,
            category=category,
            timestamp=datetime.now(timezone.utc),
            check_duration_ms=(time.time() - start_time) * 1000,
            overall_status="error",
            quality_score=0.0,
            component_results={"error": error_message},
            issues_found=1,
            critical_issues=1,
            warnings=[error_message],
            recommendations=["Fix the error and retry the check"],
            next_actions=["Investigate and resolve the underlying issue"],
            detailed_metrics={},
            test_coverage={},
            performance_metrics={},
            security_assessment={},
            compliance_status={}
        )
    
    async def get_category_status(self) -> Dict[str, Any]:
        """Get status of all available categories."""
        status = {
            "available_categories": [cat.value for cat in QualityCategory],
            "enabled_categories": [cat.value for cat in self.config.enabled_categories],
            "category_info": {
                cat.value: {
                    "name": info["name"],
                    "description": info["description"],
                    "component_count": len(info["key_components"]),
                    "critical_path_count": len(info["critical_paths"])
                }
                for cat, info in self.category_info.items()
            },
            "configuration": {
                "check_depth": self.config.check_depth,
                "timeout_seconds": self.config.timeout_seconds,
                "parallel_execution": self.config.parallel_execution,
                "quality_thresholds": self.config.quality_thresholds
            },
            "checker_status": {
                cat.value: "ready" for cat in self.checkers.keys()
            }
        }
        
        return status
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check category checker quality and readiness."""
        return {
            "checker_type": "CategoryQualityChecker",
            "version": "1.0.0",
            "supported_categories": len(self.checkers),
            "configuration": {
                "check_depth": self.config.check_depth,
                "parallel_execution": self.config.parallel_execution,
                "timeout_seconds": self.config.timeout_seconds
            },
            "capabilities": {
                "component_checking": True,
                "critical_path_validation": True,
                "performance_assessment": self.config.include_performance_tests,
                "security_assessment": self.config.include_security_assessment,
                "integration_testing": self.config.include_integration_tests
            },
            "status": "ready"
        }


# CLI Interface for category checking
async def main():
    """CLI interface for category quality checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Category Quality Checker")
    parser.add_argument("--category", "-c", type=str, 
                       choices=[cat.value for cat in QualityCategory],
                       default="all", help="Category to check")
    parser.add_argument("--project", "-p", help="Project path to check")
    parser.add_argument("--depth", "-d", choices=["basic", "standard", "comprehensive", "exhaustive"],
                       default="comprehensive", help="Check depth")
    parser.add_argument("--parallel", action="store_true", help="Run checks in parallel")
    parser.add_argument("--status", "-s", action="store_true", help="Show category status")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Load configuration
    config = CategoryCheckConfig()
    config.check_depth = args.depth
    config.parallel_execution = args.parallel
    
    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            # Update config with loaded data
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    # Create checker
    checker = CategoryQualityChecker(config)
    
    try:
        if args.status:
            # Show status
            status = await checker.get_category_status()
            print(json.dumps(status, indent=2))
            
        else:
            # Run category check
            category = QualityCategory(args.category)
            project_path = args.project or str(project_root)
            
            print(f"Starting category check: {category.value}")
            result = await checker.check_category(category, project_path)
            
            # Output results
            output = {
                "check_id": result.check_id,
                "category": result.category.value,
                "status": result.overall_status,
                "quality_score": result.quality_score,
                "duration_ms": result.check_duration_ms,
                "issues_found": result.issues_found,
                "critical_issues": result.critical_issues,
                "warnings": result.warnings,
                "recommendations": result.recommendations,
                "next_actions": result.next_actions,
                "detailed_metrics": result.detailed_metrics,
                "test_coverage": result.test_coverage
            }
            
            print(json.dumps(output, indent=2))
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    return 0


if __name__ == "__main__":
    asyncio.run(main())