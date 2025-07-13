#!/usr/bin/env python3
"""Full Quality Checker.

This module implements the comprehensive full quality check functionality that provides:
- Complete system-wide quality validation
- All 4 levels of quality gates (Basic, Functional, Integration, Production)
- All 5 functional categories (Discord, Content, Data, Quality, Integration)
- Comprehensive reporting and metrics collection
- Production readiness assessment
- Complete quality assurance pipeline

The full checker runs the entire quality assurance suite for comprehensive validation.
"""

import asyncio
import json
import time
import sys
import subprocess
import traceback
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
import concurrent.futures
from enum import Enum

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker
from utils.quality_assurance.gates.level1_basic_gate import Level1BasicQualityGate, Level1ValidationResult
from utils.quality_assurance.gates.level2_functional_gate import Level2FunctionalQualityGate, Level2ValidationResult
from utils.quality_assurance.gates.level3_integration_gate import Level3IntegrationQualityGate, Level3ValidationResult
from utils.quality_assurance.gates.level4_production_gate import Level4ProductionQualityGate, Level4ValidationResult
from utils.quality_assurance.automation.category_checker import CategoryQualityChecker, QualityCategory, CategoryCheckResult


class FullCheckPhase(Enum):
    """Phases of full quality check execution."""
    INITIALIZATION = "initialization"
    LEVEL1_BASIC = "level1_basic"
    LEVEL2_FUNCTIONAL = "level2_functional"
    LEVEL3_INTEGRATION = "level3_integration"
    LEVEL4_PRODUCTION = "level4_production"
    CATEGORY_VALIDATION = "category_validation"
    FINAL_ASSESSMENT = "final_assessment"
    REPORTING = "reporting"


@dataclass
class FullCheckResult:
    """Result of comprehensive full quality check."""
    check_id: str
    timestamp: datetime
    check_duration_ms: float
    overall_status: str  # "pass", "warning", "fail", "error"
    production_ready: bool
    quality_score: float
    phase_results: Dict[str, Any]
    gate_results: Dict[str, Any]
    category_results: Dict[str, CategoryCheckResult]
    issues_summary: Dict[str, int]
    critical_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    next_actions: List[str]
    quality_metrics: Dict[str, float]
    performance_metrics: Dict[str, float]
    security_assessment: Dict[str, Any]
    compliance_status: Dict[str, bool]
    readiness_checklist: Dict[str, bool]
    executive_summary: Dict[str, Any]


@dataclass
class FullCheckConfig:
    """Configuration for full quality checking."""
    project_path: str = ""
    timeout_seconds: float = 1800.0  # 30 minutes default
    parallel_execution: bool = True
    max_concurrent_phases: int = 2
    include_all_categories: bool = True
    include_all_gates: bool = True
    stop_on_critical_failure: bool = False
    generate_detailed_reports: bool = True
    save_intermediate_results: bool = True
    quality_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "min_overall_score": 85.0,
        "min_gate_score": 80.0,
        "min_category_score": 75.0,
        "max_critical_issues": 0,
        "min_production_readiness": 90.0
    })
    notification_settings: Dict[str, bool] = field(default_factory=lambda: {
        "notify_on_start": True,
        "notify_on_phase_complete": True,
        "notify_on_critical_failure": True,
        "notify_on_completion": True
    })


class FullQualityChecker(BaseQualityChecker):
    """Comprehensive full quality checker for complete system validation."""
    
    def __init__(self, config: Optional[FullCheckConfig] = None):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.config = config or FullCheckConfig()
        
        # Initialize quality gates
        self.gates = {
            "level1": Level1BasicQualityGate(),
            "level2": Level2FunctionalQualityGate(),
            "level3": Level3IntegrationQualityGate(),
            "level4": Level4ProductionQualityGate()
        }
        
        # Initialize category checker
        self.category_checker = CategoryQualityChecker()
        
        # Execution state
        self.current_phase = None
        self.phase_start_times = {}
        self.intermediate_results = {}
        self.execution_context = {}
        
    async def run_full_check(self, project_path: str = None) -> FullCheckResult:
        """Run comprehensive full quality check."""
        if not project_path:
            project_path = self.config.project_path or str(project_root)
            
        check_id = f"full_check_{int(time.time() * 1000)}"
        start_time = time.time()
        
        self.logger.info(f"Starting full quality check: {check_id}")
        
        if self.config.notification_settings["notify_on_start"]:
            await self._notify_phase_start("Full Quality Check", check_id)
        
        # Initialize result
        result = FullCheckResult(
            check_id=check_id,
            timestamp=datetime.now(timezone.utc),
            check_duration_ms=0.0,
            overall_status="unknown",
            production_ready=False,
            quality_score=0.0,
            phase_results={},
            gate_results={},
            category_results={},
            issues_summary={},
            critical_issues=[],
            warnings=[],
            recommendations=[],
            next_actions=[],
            quality_metrics={},
            performance_metrics={},
            security_assessment={},
            compliance_status={},
            readiness_checklist={},
            executive_summary={}
        )
        
        try:
            # Phase 1: Initialization
            await self._run_phase(FullCheckPhase.INITIALIZATION, result, project_path)
            
            # Phase 2: Level 1 Basic Gate
            if self.config.include_all_gates:
                await self._run_phase(FullCheckPhase.LEVEL1_BASIC, result, project_path)
                
                # Stop if critical failure and configured to do so
                if self.config.stop_on_critical_failure and result.phase_results.get("level1_basic", {}).get("critical_failures"):
                    result.overall_status = "fail"
                    result.critical_issues.append("Level 1 critical failures prevent further testing")
                    return result
            
            # Phase 3: Level 2 Functional Gate
            if self.config.include_all_gates:
                await self._run_phase(FullCheckPhase.LEVEL2_FUNCTIONAL, result, project_path)
            
            # Phase 4: Level 3 Integration Gate
            if self.config.include_all_gates:
                await self._run_phase(FullCheckPhase.LEVEL3_INTEGRATION, result, project_path)
            
            # Phase 5: Level 4 Production Gate
            if self.config.include_all_gates:
                await self._run_phase(FullCheckPhase.LEVEL4_PRODUCTION, result, project_path)
            
            # Phase 6: Category Validation
            if self.config.include_all_categories:
                await self._run_phase(FullCheckPhase.CATEGORY_VALIDATION, result, project_path)
            
            # Phase 7: Final Assessment
            await self._run_phase(FullCheckPhase.FINAL_ASSESSMENT, result, project_path)
            
            # Phase 8: Reporting
            await self._run_phase(FullCheckPhase.REPORTING, result, project_path)
            
            # Finalize result
            result.check_duration_ms = (time.time() - start_time) * 1000
            
            if self.config.notification_settings["notify_on_completion"]:
                await self._notify_completion(result)
            
            self.logger.info(
                f"Full quality check completed: {check_id} "
                f"(status: {result.overall_status}, score: {result.quality_score:.1f}, "
                f"duration: {result.check_duration_ms / 1000:.1f}s)"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during full quality check: {str(e)}")
            result.overall_status = "error"
            result.critical_issues.append(f"Full check failed: {str(e)}")
            result.check_duration_ms = (time.time() - start_time) * 1000
            return result
    
    async def _run_phase(self, phase: FullCheckPhase, result: FullCheckResult, project_path: str):
        """Run a specific phase of the full check."""
        self.current_phase = phase
        phase_start = time.time()
        self.phase_start_times[phase.value] = phase_start
        
        self.logger.info(f"Starting phase: {phase.value}")
        
        if self.config.notification_settings["notify_on_phase_complete"]:
            await self._notify_phase_start(phase.value.replace("_", " ").title(), result.check_id)
        
        try:
            if phase == FullCheckPhase.INITIALIZATION:
                await self._phase_initialization(result, project_path)
            elif phase == FullCheckPhase.LEVEL1_BASIC:
                await self._phase_level1_basic(result, project_path)
            elif phase == FullCheckPhase.LEVEL2_FUNCTIONAL:
                await self._phase_level2_functional(result, project_path)
            elif phase == FullCheckPhase.LEVEL3_INTEGRATION:
                await self._phase_level3_integration(result, project_path)
            elif phase == FullCheckPhase.LEVEL4_PRODUCTION:
                await self._phase_level4_production(result, project_path)
            elif phase == FullCheckPhase.CATEGORY_VALIDATION:
                await self._phase_category_validation(result, project_path)
            elif phase == FullCheckPhase.FINAL_ASSESSMENT:
                await self._phase_final_assessment(result, project_path)
            elif phase == FullCheckPhase.REPORTING:
                await self._phase_reporting(result, project_path)
            
            phase_duration = (time.time() - phase_start) * 1000
            result.phase_results[phase.value] = {
                "status": "completed",
                "duration_ms": phase_duration,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"Phase completed: {phase.value} ({phase_duration:.1f}ms)")
            
        except Exception as e:
            phase_duration = (time.time() - phase_start) * 1000
            error_msg = f"Phase {phase.value} failed: {str(e)}"
            
            result.phase_results[phase.value] = {
                "status": "failed",
                "duration_ms": phase_duration,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            result.critical_issues.append(error_msg)
            self.logger.error(error_msg)
            
            if self.config.notification_settings["notify_on_critical_failure"]:
                await self._notify_critical_failure(phase.value, str(e))
    
    async def _phase_initialization(self, result: FullCheckResult, project_path: str):
        """Initialize the full check process."""
        # Validate project structure
        project_path_obj = Path(project_path)
        if not project_path_obj.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
        
        # Check for critical files
        critical_files = ["src/discord_notifier.py", "pyproject.toml"]
        missing_files = []
        for file_path in critical_files:
            if not (project_path_obj / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            result.warnings.append(f"Missing critical files: {', '.join(missing_files)}")
        
        # Set up execution context
        self.execution_context = {
            "project_path": project_path,
            "start_time": time.time(),
            "python_version": sys.version,
            "platform": os.name,
            "working_directory": os.getcwd()
        }
        
        # Initialize intermediate results storage
        if self.config.save_intermediate_results:
            self.intermediate_results = {
                "gates": {},
                "categories": {},
                "metrics": {}
            }
        
        result.phase_results["initialization"] = {
            "project_validated": True,
            "missing_files": missing_files,
            "execution_context": self.execution_context
        }
    
    async def _phase_level1_basic(self, result: FullCheckResult, project_path: str):
        """Run Level 1 Basic Quality Gate."""
        gate = self.gates["level1"]
        gate_result = await gate.validate_project(project_path)
        
        result.gate_results["level1"] = gate_result
        
        if self.config.save_intermediate_results:
            self.intermediate_results["gates"]["level1"] = gate_result
        
        # Extract key metrics
        if gate_result["overall_status"] == "fail":
            result.critical_issues.extend(gate_result.get("critical_failures", []))
        
        result.warnings.extend(gate_result.get("warnings", []))
    
    async def _phase_level2_functional(self, result: FullCheckResult, project_path: str):
        """Run Level 2 Functional Quality Gate."""
        gate = self.gates["level2"]
        gate_result = await gate.validate_project(project_path)
        
        result.gate_results["level2"] = gate_result
        
        if self.config.save_intermediate_results:
            self.intermediate_results["gates"]["level2"] = gate_result
        
        # Extract key metrics
        if gate_result["overall_status"] == "fail":
            result.critical_issues.extend(gate_result.get("critical_failures", []))
        
        result.warnings.extend(gate_result.get("warnings", []))
    
    async def _phase_level3_integration(self, result: FullCheckResult, project_path: str):
        """Run Level 3 Integration Quality Gate."""
        gate = self.gates["level3"]
        gate_result = await gate.validate_project(project_path)
        
        result.gate_results["level3"] = gate_result
        
        if self.config.save_intermediate_results:
            self.intermediate_results["gates"]["level3"] = gate_result
        
        # Extract key metrics
        if gate_result["overall_status"] == "fail":
            result.critical_issues.extend(gate_result.get("critical_failures", []))
        
        result.warnings.extend(gate_result.get("warnings", []))
    
    async def _phase_level4_production(self, result: FullCheckResult, project_path: str):
        """Run Level 4 Production Quality Gate."""
        gate = self.gates["level4"]
        gate_result = await gate.validate_project(project_path)
        
        result.gate_results["level4"] = gate_result
        
        if self.config.save_intermediate_results:
            self.intermediate_results["gates"]["level4"] = gate_result
        
        # Extract key metrics
        if gate_result["overall_status"] == "fail":
            result.critical_issues.extend(gate_result.get("critical_failures", []))
        
        result.warnings.extend(gate_result.get("warnings", []))
        
        # Determine production readiness
        result.production_ready = gate_result.get("production_ready", False)
    
    async def _phase_category_validation(self, result: FullCheckResult, project_path: str):
        """Run category-specific validation."""
        # Check all categories
        category_results = {}
        
        if self.config.parallel_execution:
            # Run categories in parallel
            tasks = []
            for category in QualityCategory:
                if category != QualityCategory.ALL_CATEGORIES:
                    task = self.category_checker.check_category(category, project_path)
                    tasks.append((category, task))
            
            # Wait for all category checks
            for category, task in tasks:
                try:
                    category_result = await task
                    category_results[category.value] = category_result
                    result.category_results[category.value] = category_result
                except Exception as e:
                    self.logger.error(f"Category check failed for {category.value}: {str(e)}")
                    result.warnings.append(f"Category check failed: {category.value}")
        else:
            # Run categories sequentially
            for category in QualityCategory:
                if category != QualityCategory.ALL_CATEGORIES:
                    try:
                        category_result = await self.category_checker.check_category(category, project_path)
                        category_results[category.value] = category_result
                        result.category_results[category.value] = category_result
                    except Exception as e:
                        self.logger.error(f"Category check failed for {category.value}: {str(e)}")
                        result.warnings.append(f"Category check failed: {category.value}")
        
        if self.config.save_intermediate_results:
            self.intermediate_results["categories"] = category_results
        
        # Aggregate category issues
        for category_result in category_results.values():
            if category_result.critical_issues > 0:
                result.critical_issues.extend([
                    f"Critical issue in {category_result.category.value}: {issue}"
                    for issue in category_result.recommendations[:category_result.critical_issues]
                ])
            result.warnings.extend(category_result.warnings)
            result.recommendations.extend(category_result.recommendations)
    
    async def _phase_final_assessment(self, result: FullCheckResult, project_path: str):
        """Perform final quality assessment."""
        # Calculate overall quality score
        gate_scores = []
        for gate_name, gate_result in result.gate_results.items():
            if isinstance(gate_result, dict) and "summary" in gate_result:
                score = gate_result["summary"].get("average_quality_score", 0)
                gate_scores.append(score)
        
        category_scores = []
        for category_result in result.category_results.values():
            category_scores.append(category_result.quality_score)
        
        all_scores = gate_scores + category_scores
        if all_scores:
            result.quality_score = sum(all_scores) / len(all_scores)
        
        # Determine overall status
        if result.critical_issues:
            result.overall_status = "fail"
        elif result.quality_score < self.config.quality_thresholds["min_overall_score"]:
            result.overall_status = "warning"
        else:
            result.overall_status = "pass"
        
        # Calculate quality metrics
        result.quality_metrics = {
            "overall_score": result.quality_score,
            "gate_average": sum(gate_scores) / len(gate_scores) if gate_scores else 0,
            "category_average": sum(category_scores) / len(category_scores) if category_scores else 0,
            "critical_issue_count": len(result.critical_issues),
            "warning_count": len(result.warnings),
            "recommendation_count": len(result.recommendations)
        }
        
        # Generate readiness checklist
        result.readiness_checklist = {
            "all_gates_passed": all(
                gate_result.get("overall_status") == "pass" 
                for gate_result in result.gate_results.values()
            ),
            "all_categories_passed": all(
                cat_result.overall_status == "pass"
                for cat_result in result.category_results.values()
            ),
            "no_critical_issues": len(result.critical_issues) == 0,
            "quality_threshold_met": result.quality_score >= self.config.quality_thresholds["min_overall_score"],
            "production_ready": result.production_ready
        }
        
        # Generate recommendations and next actions
        if result.critical_issues:
            result.next_actions.append("Address all critical issues immediately")
        if result.quality_score < self.config.quality_thresholds["min_overall_score"]:
            result.next_actions.append("Improve quality scores in failing areas")
        if not result.production_ready:
            result.next_actions.append("Complete production readiness requirements")
        
        # Remove duplicate recommendations
        result.recommendations = list(set(result.recommendations))
        result.next_actions = list(set(result.next_actions))
    
    async def _phase_reporting(self, result: FullCheckResult, project_path: str):
        """Generate comprehensive reporting."""
        # Create executive summary
        result.executive_summary = {
            "check_id": result.check_id,
            "timestamp": result.timestamp.isoformat(),
            "duration_minutes": result.check_duration_ms / 60000,
            "overall_status": result.overall_status,
            "quality_score": result.quality_score,
            "production_ready": result.production_ready,
            "gates_summary": {
                gate_name: gate_result.get("overall_status", "unknown")
                for gate_name, gate_result in result.gate_results.items()
            },
            "categories_summary": {
                cat_name: cat_result.overall_status
                for cat_name, cat_result in result.category_results.items()
            },
            "key_metrics": {
                "critical_issues": len(result.critical_issues),
                "warnings": len(result.warnings),
                "recommendations": len(result.recommendations)
            },
            "readiness_status": result.readiness_checklist
        }
        
        # Calculate issues summary
        result.issues_summary = {
            "critical": len(result.critical_issues),
            "warnings": len(result.warnings),
            "recommendations": len(result.recommendations),
            "total": len(result.critical_issues) + len(result.warnings) + len(result.recommendations)
        }
        
        # Generate detailed report if configured
        if self.config.generate_detailed_reports:
            await self._generate_detailed_report(result, project_path)
    
    async def _generate_detailed_report(self, result: FullCheckResult, project_path: str):
        """Generate detailed quality report."""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        report_filename = f"{timestamp}-full-quality-check-report.md"
        report_path = Path(project_path) / report_filename
        
        report_content = self._create_markdown_report(result)
        
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            self.logger.info(f"Detailed report generated: {report_path}")
            result.phase_results["reporting"]["detailed_report_path"] = str(report_path)
            
        except Exception as e:
            self.logger.warning(f"Failed to generate detailed report: {str(e)}")
            result.warnings.append("Failed to generate detailed report")
    
    def _create_markdown_report(self, result: FullCheckResult) -> str:
        """Create markdown format quality report."""
        report_lines = [
            f"# Full Quality Check Report",
            f"",
            f"**Check ID:** {result.check_id}",
            f"**Timestamp:** {result.timestamp.isoformat()}",
            f"**Duration:** {result.check_duration_ms / 1000:.1f} seconds",
            f"**Overall Status:** {result.overall_status.upper()}",
            f"**Quality Score:** {result.quality_score:.1f}/100",
            f"**Production Ready:** {'✅ Yes' if result.production_ready else '❌ No'}",
            f"",
            f"## Executive Summary",
            f"",
        ]
        
        # Add readiness checklist
        report_lines.extend([
            f"### Readiness Checklist",
            f"",
        ])
        
        for item, status in result.readiness_checklist.items():
            emoji = "✅" if status else "❌"
            item_name = item.replace("_", " ").title()
            report_lines.append(f"- {emoji} {item_name}")
        
        report_lines.append("")
        
        # Add quality gates summary
        if result.gate_results:
            report_lines.extend([
                f"### Quality Gates Results",
                f"",
            ])
            
            for gate_name, gate_result in result.gate_results.items():
                status = gate_result.get("overall_status", "unknown")
                emoji = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(status, "❓")
                report_lines.append(f"- {emoji} **{gate_name.upper()}**: {status}")
            
            report_lines.append("")
        
        # Add category results summary
        if result.category_results:
            report_lines.extend([
                f"### Category Validation Results",
                f"",
            ])
            
            for cat_name, cat_result in result.category_results.items():
                emoji = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(cat_result.overall_status, "❓")
                report_lines.append(f"- {emoji} **{cat_name.replace('_', ' ').title()}**: {cat_result.overall_status} (Score: {cat_result.quality_score:.1f})")
            
            report_lines.append("")
        
        # Add issues summary
        if result.critical_issues or result.warnings:
            report_lines.extend([
                f"## Issues Summary",
                f"",
                f"- **Critical Issues:** {len(result.critical_issues)}",
                f"- **Warnings:** {len(result.warnings)}",
                f"- **Recommendations:** {len(result.recommendations)}",
                f"",
            ])
            
            if result.critical_issues:
                report_lines.extend([
                    f"### Critical Issues",
                    f"",
                ])
                for issue in result.critical_issues:
                    report_lines.append(f"- ❌ {issue}")
                report_lines.append("")
            
            if result.warnings:
                report_lines.extend([
                    f"### Warnings",
                    f"",
                ])
                for warning in result.warnings[:10]:  # Limit to first 10
                    report_lines.append(f"- ⚠️ {warning}")
                if len(result.warnings) > 10:
                    report_lines.append(f"- ... and {len(result.warnings) - 10} more warnings")
                report_lines.append("")
        
        # Add recommendations
        if result.recommendations:
            report_lines.extend([
                f"### Recommendations",
                f"",
            ])
            for rec in result.recommendations[:10]:  # Limit to first 10
                report_lines.append(f"- 💡 {rec}")
            if len(result.recommendations) > 10:
                report_lines.append(f"- ... and {len(result.recommendations) - 10} more recommendations")
            report_lines.append("")
        
        # Add next actions
        if result.next_actions:
            report_lines.extend([
                f"### Next Actions",
                f"",
            ])
            for action in result.next_actions:
                report_lines.append(f"- 🎯 {action}")
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    async def _notify_phase_start(self, phase_name: str, check_id: str):
        """Notify about phase start."""
        self.logger.info(f"📋 Starting phase: {phase_name} (Check: {check_id})")
    
    async def _notify_completion(self, result: FullCheckResult):
        """Notify about check completion."""
        status_emoji = {"pass": "✅", "warning": "⚠️", "fail": "❌", "error": "💥"}
        emoji = status_emoji.get(result.overall_status, "❓")
        
        self.logger.info(
            f"{emoji} Full quality check completed: {result.check_id} "
            f"({result.overall_status}, score: {result.quality_score:.1f}, "
            f"duration: {result.check_duration_ms / 1000:.1f}s)"
        )
    
    async def _notify_critical_failure(self, phase: str, error: str):
        """Notify about critical failure."""
        self.logger.error(f"💥 Critical failure in {phase}: {error}")
    
    async def get_full_check_status(self) -> Dict[str, Any]:
        """Get current full check status."""
        return {
            "current_phase": self.current_phase.value if self.current_phase else None,
            "execution_context": self.execution_context,
            "phase_start_times": {
                phase: start_time for phase, start_time in self.phase_start_times.items()
            },
            "configuration": {
                "timeout_seconds": self.config.timeout_seconds,
                "parallel_execution": self.config.parallel_execution,
                "include_all_categories": self.config.include_all_categories,
                "include_all_gates": self.config.include_all_gates,
                "quality_thresholds": self.config.quality_thresholds
            },
            "available_gates": list(self.gates.keys()),
            "available_categories": [cat.value for cat in QualityCategory if cat != QualityCategory.ALL_CATEGORIES]
        }
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check full checker quality and readiness."""
        return {
            "checker_type": "FullQualityChecker",
            "version": "1.0.0",
            "supported_gates": len(self.gates),
            "supported_categories": len([cat for cat in QualityCategory if cat != QualityCategory.ALL_CATEGORIES]),
            "configuration": {
                "timeout_seconds": self.config.timeout_seconds,
                "parallel_execution": self.config.parallel_execution,
                "max_concurrent_phases": self.config.max_concurrent_phases
            },
            "capabilities": {
                "comprehensive_validation": True,
                "production_readiness_assessment": True,
                "detailed_reporting": self.config.generate_detailed_reports,
                "parallel_execution": self.config.parallel_execution,
                "intermediate_result_storage": self.config.save_intermediate_results
            },
            "status": "ready"
        }


# CLI Interface for full checking
async def main():
    """CLI interface for full quality checking."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Full Quality Checker")
    parser.add_argument("--project", "-p", help="Project path to check")
    parser.add_argument("--timeout", "-t", type=float, default=1800.0, help="Timeout in seconds")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel execution")
    parser.add_argument("--no-categories", action="store_true", help="Skip category validation")
    parser.add_argument("--no-gates", action="store_true", help="Skip quality gates")
    parser.add_argument("--stop-on-failure", action="store_true", help="Stop on critical failure")
    parser.add_argument("--output", "-o", help="Output file for results")
    parser.add_argument("--status", "-s", action="store_true", help="Show checker status")
    
    args = parser.parse_args()
    
    # Create configuration
    config = FullCheckConfig()
    config.timeout_seconds = args.timeout
    config.parallel_execution = args.parallel
    config.include_all_categories = not args.no_categories
    config.include_all_gates = not args.no_gates
    config.stop_on_critical_failure = args.stop_on_failure
    
    if args.project:
        config.project_path = args.project
    
    # Create checker
    checker = FullQualityChecker(config)
    
    try:
        if args.status:
            # Show status
            status = await checker.get_full_check_status()
            print(json.dumps(status, indent=2))
            
        else:
            # Run full check
            project_path = args.project or str(project_root)
            
            print("Starting comprehensive full quality check...")
            result = await checker.run_full_check(project_path)
            
            # Prepare output
            output_data = {
                "check_id": result.check_id,
                "timestamp": result.timestamp.isoformat(),
                "overall_status": result.overall_status,
                "quality_score": result.quality_score,
                "production_ready": result.production_ready,
                "duration_seconds": result.check_duration_ms / 1000,
                "executive_summary": result.executive_summary,
                "issues_summary": result.issues_summary,
                "critical_issues": result.critical_issues,
                "warnings": result.warnings[:5],  # First 5 warnings
                "recommendations": result.recommendations[:5],  # First 5 recommendations
                "next_actions": result.next_actions,
                "readiness_checklist": result.readiness_checklist
            }
            
            # Output results
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                print(f"Results saved to: {args.output}")
            else:
                print(json.dumps(output_data, indent=2))
                
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    return 0


if __name__ == "__main__":
    asyncio.run(main())