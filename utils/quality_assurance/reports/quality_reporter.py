#!/usr/bin/env python3
"""Quality Reporter.

This module provides comprehensive quality reporting functionality including:
- Detailed quality analysis reports generation
- Multi-format report output (JSON, HTML, Markdown, XML)
- Quality trend analysis and historical comparison
- Performance metrics aggregation and visualization
- Issue categorization and priority assessment
- Executive summary generation for stakeholders
- Integration with external reporting systems
- Real-time quality dashboard data generation
"""

import asyncio
import json
import time
import sys
import os
import statistics
import tempfile
import subprocess
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import base64
import hashlib

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# Quality Report Types
@dataclass
class QualityIssueSummary:
    """Summary of quality issues found."""
    category: str  # "critical", "high", "medium", "low", "info"
    issue_type: str  # "error", "warning", "suggestion", "optimization"
    count: int
    description: str
    affected_components: List[str]
    resolution_suggestions: List[str]
    severity_score: float  # 0-100
    business_impact: str


@dataclass
class QualityMetricsSummary:
    """Summary of quality metrics."""
    metric_name: str
    current_value: float
    target_value: float
    previous_value: Optional[float]
    trend: str  # "improving", "stable", "declining"
    measurement_unit: str
    category: str  # "performance", "reliability", "security", "maintainability"
    status: str  # "excellent", "good", "acceptable", "needs_improvement", "critical"


@dataclass
class ComponentQualityReport:
    """Quality report for a specific component."""
    component_name: str
    component_type: str  # "discord_integration", "content_processing", etc.
    overall_score: float  # 0-100
    issues: List[QualityIssueSummary]
    metrics: List[QualityMetricsSummary]
    recommendations: List[str]
    compliance_status: str
    last_updated: datetime


@dataclass
class QualityTrendData:
    """Quality trend data for historical analysis."""
    timestamp: datetime
    overall_quality_score: float
    component_scores: Dict[str, float]
    issue_counts: Dict[str, int]
    key_metrics: Dict[str, float]
    build_number: Optional[str] = None
    commit_hash: Optional[str] = None


@dataclass
class ExecutiveSummary:
    """Executive summary for stakeholders."""
    overall_quality_score: float
    quality_grade: str  # "A+", "A", "B+", "B", "C+", "C", "D", "F"
    total_issues: int
    critical_issues: int
    improvement_percentage: float
    key_achievements: List[str]
    areas_of_concern: List[str]
    recommended_actions: List[str]
    quality_trend: str  # "improving", "stable", "declining"
    compliance_score: float


class QualityReporter:
    """Comprehensive quality reporting system."""
    
    def __init__(self, output_directory: Optional[Path] = None):
        self.logger = AstolfoLogger(__name__)
        self.output_directory = output_directory or Path("quality_reports")
        self.output_directory.mkdir(exist_ok=True)
        
        # Initialize report storage
        self.quality_history: List[QualityTrendData] = []
        self.component_reports: Dict[str, ComponentQualityReport] = {}
        self.current_report_id = self._generate_report_id()
        
        # Load historical data if available
        self._load_historical_data()
    
    def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        hash_input = f"{timestamp}_{time.time()}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"QR_{timestamp}_{hash_suffix}"
    
    def _load_historical_data(self) -> None:
        """Load historical quality data."""
        try:
            history_file = self.output_directory / "quality_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    data = json.load(f)
                
                self.quality_history = []
                for item in data.get("history", []):
                    trend_data = QualityTrendData(
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        overall_quality_score=item["overall_quality_score"],
                        component_scores=item["component_scores"],
                        issue_counts=item["issue_counts"],
                        key_metrics=item["key_metrics"],
                        build_number=item.get("build_number"),
                        commit_hash=item.get("commit_hash")
                    )
                    self.quality_history.append(trend_data)
                
                self.logger.info(f"Loaded {len(self.quality_history)} historical quality records")
        except Exception as e:
            self.logger.warning(f"Could not load historical data: {e}")
    
    def _save_historical_data(self) -> None:
        """Save historical quality data."""
        try:
            history_file = self.output_directory / "quality_history.json"
            
            # Convert to serializable format
            history_data = []
            for trend in self.quality_history:
                data = {
                    "timestamp": trend.timestamp.isoformat(),
                    "overall_quality_score": trend.overall_quality_score,
                    "component_scores": trend.component_scores,
                    "issue_counts": trend.issue_counts,
                    "key_metrics": trend.key_metrics,
                    "build_number": trend.build_number,
                    "commit_hash": trend.commit_hash
                }
                history_data.append(data)
            
            with open(history_file, 'w') as f:
                json.dump({"history": history_data}, f, indent=2)
                
            self.logger.debug(f"Saved {len(self.quality_history)} historical records")
        except Exception as e:
            self.logger.error(f"Failed to save historical data: {e}")
    
    async def add_component_report(
        self, 
        component_name: str,
        quality_result: Dict[str, Any],
        component_type: str = "unknown"
    ) -> None:
        """Add a component quality report."""
        
        # Extract issues
        issues = []
        if "issues" in quality_result:
            for issue_data in quality_result["issues"]:
                issue = QualityIssueSummary(
                    category=issue_data.get("category", "unknown"),
                    issue_type=issue_data.get("type", "error"),
                    count=issue_data.get("count", 1),
                    description=issue_data.get("description", ""),
                    affected_components=issue_data.get("affected_components", [component_name]),
                    resolution_suggestions=issue_data.get("suggestions", []),
                    severity_score=issue_data.get("severity", 50.0),
                    business_impact=issue_data.get("business_impact", "unknown")
                )
                issues.append(issue)
        
        # Extract metrics
        metrics = []
        if "metrics" in quality_result:
            for metric_data in quality_result["metrics"]:
                metric = QualityMetricsSummary(
                    metric_name=metric_data.get("name", "unknown"),
                    current_value=metric_data.get("current_value", 0.0),
                    target_value=metric_data.get("target_value", 100.0),
                    previous_value=metric_data.get("previous_value"),
                    trend=metric_data.get("trend", "stable"),
                    measurement_unit=metric_data.get("unit", ""),
                    category=metric_data.get("category", "general"),
                    status=metric_data.get("status", "unknown")
                )
                metrics.append(metric)
        
        # Create component report
        component_report = ComponentQualityReport(
            component_name=component_name,
            component_type=component_type,
            overall_score=quality_result.get("overall_score", 0.0),
            issues=issues,
            metrics=metrics,
            recommendations=quality_result.get("recommendations", []),
            compliance_status=quality_result.get("compliance_status", "unknown"),
            last_updated=datetime.now(timezone.utc)
        )
        
        self.component_reports[component_name] = component_report
        self.logger.debug(f"Added quality report for component: {component_name}")
    
    async def generate_comprehensive_report(
        self,
        include_trends: bool = True,
        include_executive_summary: bool = True,
        build_number: Optional[str] = None,
        commit_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        
        report_timestamp = datetime.now(timezone.utc)
        
        # Calculate overall metrics
        overall_score = await self._calculate_overall_score()
        total_issues = sum(len(report.issues) for report in self.component_reports.values())
        critical_issues = sum(
            sum(1 for issue in report.issues if issue.category == "critical")
            for report in self.component_reports.values()
        )
        
        # Generate executive summary
        executive_summary = None
        if include_executive_summary:
            executive_summary = await self._generate_executive_summary(
                overall_score, total_issues, critical_issues
            )
        
        # Collect component summaries
        component_summaries = {}
        for name, report in self.component_reports.items():
            component_summaries[name] = {
                "score": report.overall_score,
                "type": report.component_type,
                "issue_count": len(report.issues),
                "critical_issues": sum(1 for issue in report.issues if issue.category == "critical"),
                "compliance_status": report.compliance_status,
                "last_updated": report.last_updated.isoformat()
            }
        
        # Collect all metrics
        all_metrics = {}
        for report in self.component_reports.values():
            for metric in report.metrics:
                key = f"{report.component_name}_{metric.metric_name}"
                all_metrics[key] = {
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "trend": metric.trend,
                    "status": metric.status,
                    "category": metric.category
                }
        
        # Generate trend analysis
        trend_analysis = None
        if include_trends and len(self.quality_history) > 1:
            trend_analysis = await self._generate_trend_analysis()
        
        # Collect all issues with categorization
        issues_by_category = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": []
        }
        
        for report in self.component_reports.values():
            for issue in report.issues:
                issues_by_category[issue.category].append({
                    "component": report.component_name,
                    "type": issue.issue_type,
                    "description": issue.description,
                    "count": issue.count,
                    "severity_score": issue.severity_score,
                    "business_impact": issue.business_impact,
                    "suggestions": issue.resolution_suggestions
                })
        
        # Build comprehensive report
        comprehensive_report = {
            "report_metadata": {
                "report_id": self.current_report_id,
                "generated_at": report_timestamp.isoformat(),
                "report_version": "1.0",
                "build_number": build_number,
                "commit_hash": commit_hash,
                "total_components": len(self.component_reports),
                "report_type": "comprehensive_quality_analysis"
            },
            "summary": {
                "overall_quality_score": overall_score,
                "total_issues": total_issues,
                "critical_issues": critical_issues,
                "quality_grade": self._calculate_quality_grade(overall_score),
                "compliance_percentage": await self._calculate_compliance_percentage()
            },
            "executive_summary": executive_summary,
            "component_analysis": component_summaries,
            "issues_analysis": {
                "by_category": issues_by_category,
                "total_by_severity": {
                    category: len(issues) for category, issues in issues_by_category.items()
                },
                "top_issues": await self._get_top_issues(),
                "resolution_priorities": await self._get_resolution_priorities()
            },
            "metrics_analysis": {
                "current_metrics": all_metrics,
                "performance_indicators": await self._get_performance_indicators(),
                "quality_gates_status": await self._get_quality_gates_status()
            },
            "recommendations": await self._generate_comprehensive_recommendations(),
            "trend_analysis": trend_analysis,
            "detailed_reports": {
                name: await self._generate_detailed_component_report(report)
                for name, report in self.component_reports.items()
            }
        }
        
        # Record this report in history
        if self.component_reports:
            await self._record_quality_trend(
                overall_score, component_summaries, all_metrics, 
                build_number, commit_hash
            )
        
        self.logger.info(f"Generated comprehensive quality report: {self.current_report_id}")
        return comprehensive_report
    
    async def _calculate_overall_score(self) -> float:
        """Calculate overall quality score across all components."""
        if not self.component_reports:
            return 0.0
        
        # Weight components by importance (can be customized)
        component_weights = {
            "discord_integration": 0.25,
            "content_processing": 0.20,
            "data_management": 0.20,
            "quality_validation": 0.15,
            "integration_control": 0.20
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for name, report in self.component_reports.items():
            # Determine component type for weighting
            component_type = report.component_type
            weight = component_weights.get(component_type, 0.1)
            
            weighted_sum += report.overall_score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_quality_grade(self, score: float) -> str:
        """Calculate quality grade from score."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    async def _calculate_compliance_percentage(self) -> float:
        """Calculate overall compliance percentage."""
        if not self.component_reports:
            return 0.0
        
        compliant_components = sum(
            1 for report in self.component_reports.values()
            if report.compliance_status in ["compliant", "excellent"]
        )
        
        return (compliant_components / len(self.component_reports)) * 100
    
    async def _generate_executive_summary(
        self, 
        overall_score: float, 
        total_issues: int, 
        critical_issues: int
    ) -> Dict[str, Any]:
        """Generate executive summary."""
        
        # Calculate improvement from previous report
        improvement_percentage = 0.0
        quality_trend = "stable"
        
        if len(self.quality_history) > 0:
            previous_score = self.quality_history[-1].overall_quality_score
            if previous_score > 0:
                improvement_percentage = ((overall_score - previous_score) / previous_score) * 100
                if improvement_percentage > 2:
                    quality_trend = "improving"
                elif improvement_percentage < -2:
                    quality_trend = "declining"
        
        # Generate key achievements and concerns
        key_achievements = await self._identify_key_achievements()
        areas_of_concern = await self._identify_areas_of_concern()
        recommended_actions = await self._generate_executive_recommendations()
        
        return {
            "overall_quality_score": overall_score,
            "quality_grade": self._calculate_quality_grade(overall_score),
            "total_issues": total_issues,
            "critical_issues": critical_issues,
            "improvement_percentage": improvement_percentage,
            "key_achievements": key_achievements,
            "areas_of_concern": areas_of_concern,
            "recommended_actions": recommended_actions,
            "quality_trend": quality_trend,
            "compliance_score": await self._calculate_compliance_percentage()
        }
    
    async def _identify_key_achievements(self) -> List[str]:
        """Identify key quality achievements."""
        achievements = []
        
        # Check for high-scoring components
        excellent_components = [
            name for name, report in self.component_reports.items()
            if report.overall_score >= 90
        ]
        
        if excellent_components:
            achievements.append(
                f"Excellent quality scores achieved in {len(excellent_components)} components: "
                f"{', '.join(excellent_components)}"
            )
        
        # Check for zero critical issues
        components_no_critical = [
            name for name, report in self.component_reports.items()
            if not any(issue.category == "critical" for issue in report.issues)
        ]
        
        if len(components_no_critical) == len(self.component_reports):
            achievements.append("Zero critical issues across all components")
        elif components_no_critical:
            achievements.append(
                f"No critical issues in {len(components_no_critical)} components"
            )
        
        # Check for improvement trends
        if len(self.quality_history) > 1:
            recent_scores = [trend.overall_quality_score for trend in self.quality_history[-3:]]
            if len(recent_scores) >= 2 and all(
                recent_scores[i] <= recent_scores[i+1] for i in range(len(recent_scores)-1)
            ):
                achievements.append("Consistent quality improvement trend")
        
        return achievements or ["Quality assessment completed successfully"]
    
    async def _identify_areas_of_concern(self) -> List[str]:
        """Identify areas of concern."""
        concerns = []
        
        # Check for low-scoring components
        poor_components = [
            name for name, report in self.component_reports.items()
            if report.overall_score < 70
        ]
        
        if poor_components:
            concerns.append(
                f"Quality scores below acceptable threshold in: {', '.join(poor_components)}"
            )
        
        # Check for critical issues
        critical_issue_components = [
            name for name, report in self.component_reports.items()
            if any(issue.category == "critical" for issue in report.issues)
        ]
        
        if critical_issue_components:
            concerns.append(
                f"Critical issues found in: {', '.join(critical_issue_components)}"
            )
        
        # Check for declining trends
        if len(self.quality_history) > 1:
            recent_scores = [trend.overall_quality_score for trend in self.quality_history[-3:]]
            if len(recent_scores) >= 2 and recent_scores[-1] < recent_scores[-2]:
                concerns.append("Quality score declining from previous assessment")
        
        # Check for compliance issues
        non_compliant = [
            name for name, report in self.component_reports.items()
            if report.compliance_status not in ["compliant", "excellent"]
        ]
        
        if non_compliant:
            concerns.append(f"Compliance issues in: {', '.join(non_compliant)}")
        
        return concerns
    
    async def _generate_executive_recommendations(self) -> List[str]:
        """Generate executive-level recommendations."""
        recommendations = []
        
        # Critical issues first
        critical_components = [
            name for name, report in self.component_reports.items()
            if any(issue.category == "critical" for issue in report.issues)
        ]
        
        if critical_components:
            recommendations.append(
                f"IMMEDIATE ACTION REQUIRED: Address critical issues in {', '.join(critical_components)}"
            )
        
        # Low-scoring components
        low_score_components = [
            name for name, report in self.component_reports.items()
            if report.overall_score < 75
        ]
        
        if low_score_components:
            recommendations.append(
                f"Focus improvement efforts on: {', '.join(low_score_components)}"
            )
        
        # General recommendations
        total_issues = sum(len(report.issues) for report in self.component_reports.values())
        if total_issues > 10:
            recommendations.append("Implement systematic issue resolution process")
        
        # Compliance recommendations
        compliance_percentage = await self._calculate_compliance_percentage()
        if compliance_percentage < 90:
            recommendations.append("Strengthen compliance and quality assurance processes")
        
        return recommendations or ["Continue maintaining current quality standards"]
    
    async def _generate_trend_analysis(self) -> Dict[str, Any]:
        """Generate quality trend analysis."""
        if len(self.quality_history) < 2:
            return {"message": "Insufficient historical data for trend analysis"}
        
        # Analyze overall score trends
        scores = [trend.overall_quality_score for trend in self.quality_history]
        score_trend = self._calculate_trend(scores)
        
        # Analyze component trends
        component_trends = {}
        for component_name in self.component_reports.keys():
            component_scores = [
                trend.component_scores.get(component_name, 0.0)
                for trend in self.quality_history
                if component_name in trend.component_scores
            ]
            if len(component_scores) >= 2:
                component_trends[component_name] = self._calculate_trend(component_scores)
        
        # Analyze issue trends
        issue_trends = {}
        all_categories = ["critical", "high", "medium", "low", "info"]
        for category in all_categories:
            issue_counts = [
                trend.issue_counts.get(category, 0)
                for trend in self.quality_history
            ]
            if len(issue_counts) >= 2:
                issue_trends[category] = self._calculate_trend(issue_counts, invert=True)
        
        return {
            "overall_trend": score_trend,
            "component_trends": component_trends,
            "issue_trends": issue_trends,
            "analysis_period": {
                "start": self.quality_history[0].timestamp.isoformat(),
                "end": self.quality_history[-1].timestamp.isoformat(),
                "data_points": len(self.quality_history)
            },
            "key_insights": self._generate_trend_insights(score_trend, component_trends, issue_trends)
        }
    
    def _calculate_trend(self, values: List[float], invert: bool = False) -> Dict[str, Any]:
        """Calculate trend from a series of values."""
        if len(values) < 2:
            return {"direction": "insufficient_data", "change_percentage": 0.0}
        
        # Calculate linear regression slope
        n = len(values)
        x_values = list(range(n))
        
        mean_x = statistics.mean(x_values)
        mean_y = statistics.mean(values)
        
        numerator = sum((x_values[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((x_values[i] - mean_x) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Calculate percentage change
        if values[0] != 0:
            change_percentage = ((values[-1] - values[0]) / values[0]) * 100
        else:
            change_percentage = 0.0
        
        if invert:
            slope = -slope
            change_percentage = -change_percentage
        
        # Determine direction
        if abs(change_percentage) < 2:
            direction = "stable"
        elif change_percentage > 0:
            direction = "improving"
        else:
            direction = "declining"
        
        return {
            "direction": direction,
            "change_percentage": change_percentage,
            "slope": slope,
            "confidence": min(1.0, len(values) / 10.0)  # Higher confidence with more data points
        }
    
    def _generate_trend_insights(
        self, 
        overall_trend: Dict[str, Any],
        component_trends: Dict[str, Dict[str, Any]],
        issue_trends: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Generate insights from trend analysis."""
        insights = []
        
        # Overall trend insights
        if overall_trend["direction"] == "improving":
            insights.append(f"Overall quality improving by {overall_trend['change_percentage']:.1f}%")
        elif overall_trend["direction"] == "declining":
            insights.append(f"Overall quality declining by {abs(overall_trend['change_percentage']):.1f}%")
        else:
            insights.append("Overall quality remains stable")
        
        # Component trend insights
        improving_components = [
            name for name, trend in component_trends.items()
            if trend["direction"] == "improving" and trend["change_percentage"] > 5
        ]
        if improving_components:
            insights.append(f"Significant improvement in: {', '.join(improving_components)}")
        
        declining_components = [
            name for name, trend in component_trends.items()
            if trend["direction"] == "declining" and abs(trend["change_percentage"]) > 5
        ]
        if declining_components:
            insights.append(f"Attention needed for declining quality in: {', '.join(declining_components)}")
        
        # Issue trend insights
        if "critical" in issue_trends and issue_trends["critical"]["direction"] == "improving":
            insights.append("Critical issues showing positive reduction trend")
        elif "critical" in issue_trends and issue_trends["critical"]["direction"] == "declining":
            insights.append("Critical issues increasing - immediate attention required")
        
        return insights or ["Quality trends within normal variation"]
    
    async def _get_top_issues(self) -> List[Dict[str, Any]]:
        """Get top issues by severity and impact."""
        all_issues = []
        
        for report in self.component_reports.values():
            for issue in report.issues:
                issue_data = {
                    "component": report.component_name,
                    "description": issue.description,
                    "category": issue.category,
                    "severity_score": issue.severity_score,
                    "count": issue.count,
                    "business_impact": issue.business_impact,
                    "resolution_suggestions": issue.resolution_suggestions
                }
                all_issues.append(issue_data)
        
        # Sort by severity score and count
        all_issues.sort(key=lambda x: (x["severity_score"], x["count"]), reverse=True)
        
        return all_issues[:10]  # Top 10 issues
    
    async def _get_resolution_priorities(self) -> List[Dict[str, Any]]:
        """Get issue resolution priorities."""
        priorities = []
        
        # Priority 1: Critical issues
        critical_issues = []
        for report in self.component_reports.values():
            for issue in report.issues:
                if issue.category == "critical":
                    critical_issues.append({
                        "component": report.component_name,
                        "description": issue.description,
                        "count": issue.count
                    })
        
        if critical_issues:
            priorities.append({
                "priority_level": 1,
                "description": "Critical Issues Resolution",
                "issues": critical_issues,
                "timeline": "Immediate (24-48 hours)",
                "impact": "System stability and reliability"
            })
        
        # Priority 2: High severity issues
        high_issues = []
        for report in self.component_reports.values():
            for issue in report.issues:
                if issue.category == "high":
                    high_issues.append({
                        "component": report.component_name,
                        "description": issue.description,
                        "count": issue.count
                    })
        
        if high_issues:
            priorities.append({
                "priority_level": 2,
                "description": "High Priority Issues",
                "issues": high_issues[:5],  # Top 5
                "timeline": "Within 1 week",
                "impact": "Performance and user experience"
            })
        
        # Priority 3: Components with poor scores
        poor_components = [
            name for name, report in self.component_reports.items()
            if report.overall_score < 75
        ]
        
        if poor_components:
            priorities.append({
                "priority_level": 3,
                "description": "Component Quality Improvement",
                "components": poor_components,
                "timeline": "Within 2-4 weeks",
                "impact": "Overall system quality"
            })
        
        return priorities
    
    async def _get_performance_indicators(self) -> Dict[str, Any]:
        """Get key performance indicators."""
        indicators = {}
        
        # Calculate KPIs from metrics
        all_metrics = []
        for report in self.component_reports.values():
            all_metrics.extend(report.metrics)
        
        # Performance metrics
        performance_metrics = [m for m in all_metrics if m.category == "performance"]
        if performance_metrics:
            avg_performance = statistics.mean(m.current_value for m in performance_metrics)
            indicators["average_performance_score"] = avg_performance
        
        # Reliability metrics
        reliability_metrics = [m for m in all_metrics if m.category == "reliability"]
        if reliability_metrics:
            avg_reliability = statistics.mean(m.current_value for m in reliability_metrics)
            indicators["average_reliability_score"] = avg_reliability
        
        # Security metrics
        security_metrics = [m for m in all_metrics if m.category == "security"]
        if security_metrics:
            avg_security = statistics.mean(m.current_value for m in security_metrics)
            indicators["average_security_score"] = avg_security
        
        # Trend indicators
        improving_metrics = sum(1 for m in all_metrics if m.trend == "improving")
        declining_metrics = sum(1 for m in all_metrics if m.trend == "declining")
        
        indicators["metrics_improving"] = improving_metrics
        indicators["metrics_declining"] = declining_metrics
        indicators["improvement_ratio"] = improving_metrics / len(all_metrics) if all_metrics else 0
        
        return indicators
    
    async def _get_quality_gates_status(self) -> Dict[str, Any]:
        """Get quality gates status."""
        gates_status = {}
        
        overall_score = await self._calculate_overall_score()
        
        # Define quality gates
        gates = [
            {"name": "Level1_Basic", "threshold": 60, "description": "Basic quality requirements"},
            {"name": "Level2_Functional", "threshold": 75, "description": "Functional quality standards"},
            {"name": "Level3_Integration", "threshold": 85, "description": "Integration quality standards"},
            {"name": "Level4_Production", "threshold": 90, "description": "Production readiness"}
        ]
        
        for gate in gates:
            passed = overall_score >= gate["threshold"]
            gates_status[gate["name"]] = {
                "passed": passed,
                "score": overall_score,
                "threshold": gate["threshold"],
                "description": gate["description"],
                "gap": max(0, gate["threshold"] - overall_score) if not passed else 0
            }
        
        return gates_status
    
    async def _generate_comprehensive_recommendations(self) -> List[Dict[str, Any]]:
        """Generate comprehensive recommendations."""
        recommendations = []
        
        # Component-specific recommendations
        for name, report in self.component_reports.items():
            if report.overall_score < 80 or report.issues:
                component_recommendations = {
                    "component": name,
                    "priority": "high" if report.overall_score < 70 else "medium",
                    "current_score": report.overall_score,
                    "target_score": 85,
                    "recommendations": report.recommendations,
                    "estimated_effort": self._estimate_effort(report)
                }
                recommendations.append(component_recommendations)
        
        # System-wide recommendations
        total_critical = sum(
            sum(1 for issue in report.issues if issue.category == "critical")
            for report in self.component_reports.values()
        )
        
        if total_critical > 0:
            recommendations.append({
                "scope": "system_wide",
                "priority": "critical",
                "type": "immediate_action",
                "description": f"Address {total_critical} critical issues across all components",
                "estimated_effort": "1-2 days"
            })
        
        # Process improvements
        overall_score = await self._calculate_overall_score()
        if overall_score < 85:
            recommendations.append({
                "scope": "process",
                "priority": "medium",
                "type": "process_improvement",
                "description": "Implement continuous quality monitoring and improvement processes",
                "estimated_effort": "2-4 weeks"
            })
        
        return recommendations
    
    def _estimate_effort(self, report: ComponentQualityReport) -> str:
        """Estimate effort required for component improvement."""
        issue_count = len(report.issues)
        critical_count = sum(1 for issue in report.issues if issue.category == "critical")
        score_gap = max(0, 85 - report.overall_score)
        
        if critical_count > 0:
            return "High (1-2 weeks)"
        elif score_gap > 20:
            return "High (1-2 weeks)"
        elif score_gap > 10 or issue_count > 5:
            return "Medium (3-5 days)"
        else:
            return "Low (1-2 days)"
    
    async def _generate_detailed_component_report(
        self, 
        report: ComponentQualityReport
    ) -> Dict[str, Any]:
        """Generate detailed report for a component."""
        return {
            "component_info": {
                "name": report.component_name,
                "type": report.component_type,
                "last_updated": report.last_updated.isoformat(),
                "overall_score": report.overall_score,
                "compliance_status": report.compliance_status
            },
            "issues_detail": [
                {
                    "category": issue.category,
                    "type": issue.issue_type,
                    "description": issue.description,
                    "count": issue.count,
                    "severity_score": issue.severity_score,
                    "business_impact": issue.business_impact,
                    "affected_components": issue.affected_components,
                    "resolution_suggestions": issue.resolution_suggestions
                }
                for issue in report.issues
            ],
            "metrics_detail": [
                {
                    "name": metric.metric_name,
                    "current_value": metric.current_value,
                    "target_value": metric.target_value,
                    "previous_value": metric.previous_value,
                    "trend": metric.trend,
                    "unit": metric.measurement_unit,
                    "category": metric.category,
                    "status": metric.status
                }
                for metric in report.metrics
            ],
            "recommendations": report.recommendations,
            "improvement_plan": await self._generate_component_improvement_plan(report)
        }
    
    async def _generate_component_improvement_plan(
        self, 
        report: ComponentQualityReport
    ) -> Dict[str, Any]:
        """Generate improvement plan for a component."""
        plan = {
            "current_status": {
                "score": report.overall_score,
                "grade": self._calculate_quality_grade(report.overall_score),
                "compliance": report.compliance_status
            },
            "target_status": {
                "score": 85,
                "grade": "B+",
                "compliance": "compliant"
            },
            "action_items": [],
            "timeline": "2-4 weeks",
            "success_criteria": []
        }
        
        # Generate action items based on issues
        critical_issues = [i for i in report.issues if i.category == "critical"]
        if critical_issues:
            plan["action_items"].append({
                "priority": "immediate",
                "action": f"Resolve {len(critical_issues)} critical issues",
                "timeline": "24-48 hours"
            })
        
        high_issues = [i for i in report.issues if i.category == "high"]
        if high_issues:
            plan["action_items"].append({
                "priority": "high",
                "action": f"Address {len(high_issues)} high priority issues",
                "timeline": "1 week"
            })
        
        # Generate success criteria
        plan["success_criteria"].extend([
            f"Achieve quality score of 85 or higher",
            f"Reduce total issues to fewer than 5",
            f"Eliminate all critical and high priority issues",
            f"Maintain compliance status"
        ])
        
        return plan
    
    async def _record_quality_trend(
        self,
        overall_score: float,
        component_scores: Dict[str, Any],
        metrics: Dict[str, Any],
        build_number: Optional[str] = None,
        commit_hash: Optional[str] = None
    ) -> None:
        """Record quality trend data."""
        
        # Extract component scores
        scores = {name: data["score"] for name, data in component_scores.items()}
        
        # Extract key metrics
        key_metrics = {
            name: data["current_value"] 
            for name, data in metrics.items() 
            if data.get("category") in ["performance", "reliability", "security"]
        }
        
        # Count issues by category
        issue_counts = {
            "critical": sum(data["critical_issues"] for data in component_scores.values()),
            "high": 0,  # Would need to be calculated from actual issues
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        trend_data = QualityTrendData(
            timestamp=datetime.now(timezone.utc),
            overall_quality_score=overall_score,
            component_scores=scores,
            issue_counts=issue_counts,
            key_metrics=key_metrics,
            build_number=build_number,
            commit_hash=commit_hash
        )
        
        self.quality_history.append(trend_data)
        
        # Keep only last 50 records to prevent unlimited growth
        if len(self.quality_history) > 50:
            self.quality_history = self.quality_history[-50:]
        
        # Save to disk
        self._save_historical_data()
    
    async def export_report(
        self, 
        report: Dict[str, Any], 
        format_type: str = "json",
        filename: Optional[str] = None
    ) -> Path:
        """Export report to specified format."""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quality_report_{timestamp}"
        
        if format_type.lower() == "json":
            return await self._export_json(report, filename)
        elif format_type.lower() == "html":
            return await self._export_html(report, filename)
        elif format_type.lower() == "markdown":
            return await self._export_markdown(report, filename)
        elif format_type.lower() == "csv":
            return await self._export_csv(report, filename)
        elif format_type.lower() == "xml":
            return await self._export_xml(report, filename)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    async def _export_json(self, report: Dict[str, Any], filename: str) -> Path:
        """Export report as JSON."""
        filepath = self.output_directory / f"{filename}.json"
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Exported JSON report to: {filepath}")
        return filepath
    
    async def _export_html(self, report: Dict[str, Any], filename: str) -> Path:
        """Export report as HTML."""
        filepath = self.output_directory / f"{filename}.html"
        
        html_content = self._generate_html_report(report)
        
        with open(filepath, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Exported HTML report to: {filepath}")
        return filepath
    
    def _generate_html_report(self, report: Dict[str, Any]) -> str:
        """Generate HTML report content."""
        # This is a simplified HTML generator
        # In production, you might want to use a template engine like Jinja2
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Quality Report - {report['report_metadata']['report_id']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .component {{ margin: 15px 0; padding: 15px; border-left: 4px solid #007bff; }}
                .critical {{ border-left-color: #dc3545; }}
                .warning {{ border-left-color: #ffc107; }}
                .success {{ border-left-color: #28a745; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Quality Assessment Report</h1>
                <p><strong>Report ID:</strong> {report['report_metadata']['report_id']}</p>
                <p><strong>Generated:</strong> {report['report_metadata']['generated_at']}</p>
                <p><strong>Overall Score:</strong> {report['summary']['overall_quality_score']:.1f}/100</p>
                <p><strong>Grade:</strong> {report['summary']['quality_grade']}</p>
            </div>
            
            <div class="summary">
                <h2>Executive Summary</h2>
                <p><strong>Total Issues:</strong> {report['summary']['total_issues']}</p>
                <p><strong>Critical Issues:</strong> {report['summary']['critical_issues']}</p>
                <p><strong>Compliance:</strong> {report['summary']['compliance_percentage']:.1f}%</p>
            </div>
            
            <div>
                <h2>Component Analysis</h2>
        """
        
        # Add component details
        for component_name, component_data in report['component_analysis'].items():
            score = component_data['score']
            css_class = "critical" if score < 70 else "warning" if score < 85 else "success"
            
            html += f"""
                <div class="component {css_class}">
                    <h3>{component_name}</h3>
                    <p><strong>Score:</strong> {score:.1f}/100</p>
                    <p><strong>Issues:</strong> {component_data['issue_count']}</p>
                    <p><strong>Status:</strong> {component_data['compliance_status']}</p>
                </div>
            """
        
        # Add top issues table
        if report['issues_analysis']['by_category']['critical']:
            html += """
                <div>
                    <h2>Critical Issues</h2>
                    <table>
                        <tr>
                            <th>Component</th>
                            <th>Description</th>
                            <th>Impact</th>
                        </tr>
            """
            
            for issue in report['issues_analysis']['by_category']['critical'][:10]:
                html += f"""
                    <tr>
                        <td>{issue['component']}</td>
                        <td>{issue['description']}</td>
                        <td>{issue['business_impact']}</td>
                    </tr>
                """
            
            html += "</table></div>"
        
        html += """
            </body>
        </html>
        """
        
        return html
    
    async def _export_markdown(self, report: Dict[str, Any], filename: str) -> Path:
        """Export report as Markdown."""
        filepath = self.output_directory / f"{filename}.md"
        
        markdown_content = self._generate_markdown_report(report)
        
        with open(filepath, 'w') as f:
            f.write(markdown_content)
        
        self.logger.info(f"Exported Markdown report to: {filepath}")
        return filepath
    
    def _generate_markdown_report(self, report: Dict[str, Any]) -> str:
        """Generate Markdown report content."""
        md = f"""# Quality Assessment Report

## Report Information
- **Report ID:** {report['report_metadata']['report_id']}
- **Generated:** {report['report_metadata']['generated_at']}
- **Components Analyzed:** {report['report_metadata']['total_components']}

## Summary
- **Overall Score:** {report['summary']['overall_quality_score']:.1f}/100
- **Quality Grade:** {report['summary']['quality_grade']}
- **Total Issues:** {report['summary']['total_issues']}
- **Critical Issues:** {report['summary']['critical_issues']}
- **Compliance:** {report['summary']['compliance_percentage']:.1f}%

## Executive Summary
"""
        
        if 'executive_summary' in report and report['executive_summary']:
            exec_summary = report['executive_summary']
            md += f"""
### Key Achievements
{chr(10).join(f"- {achievement}" for achievement in exec_summary.get('key_achievements', []))}

### Areas of Concern
{chr(10).join(f"- {concern}" for concern in exec_summary.get('areas_of_concern', []))}

### Recommended Actions
{chr(10).join(f"- {action}" for action in exec_summary.get('recommended_actions', []))}
"""
        
        md += "\n## Component Analysis\n"
        
        for component_name, component_data in report['component_analysis'].items():
            score_emoji = "🔴" if component_data['score'] < 70 else "🟡" if component_data['score'] < 85 else "🟢"
            md += f"""
### {score_emoji} {component_name}
- **Score:** {component_data['score']:.1f}/100
- **Type:** {component_data['type']}
- **Issues:** {component_data['issue_count']}
- **Critical Issues:** {component_data['critical_issues']}
- **Compliance:** {component_data['compliance_status']}
"""
        
        # Add critical issues section
        critical_issues = report['issues_analysis']['by_category']['critical']
        if critical_issues:
            md += "\n## 🚨 Critical Issues\n"
            for issue in critical_issues[:10]:
                md += f"""
### {issue['component']} - {issue['type']}
- **Description:** {issue['description']}
- **Impact:** {issue['business_impact']}
- **Suggestions:** {', '.join(issue['suggestions'][:2]) if issue['suggestions'] else 'None provided'}
"""
        
        return md
    
    async def _export_csv(self, report: Dict[str, Any], filename: str) -> Path:
        """Export report as CSV."""
        filepath = self.output_directory / f"{filename}.csv"
        
        # Create CSV with component summary
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'Component', 'Type', 'Score', 'Grade', 'Total_Issues', 
                'Critical_Issues', 'Compliance_Status', 'Last_Updated'
            ])
            
            # Write component data
            for component_name, component_data in report['component_analysis'].items():
                grade = self._calculate_quality_grade(component_data['score'])
                writer.writerow([
                    component_name,
                    component_data['type'],
                    component_data['score'],
                    grade,
                    component_data['issue_count'],
                    component_data['critical_issues'],
                    component_data['compliance_status'],
                    component_data['last_updated']
                ])
        
        self.logger.info(f"Exported CSV report to: {filepath}")
        return filepath
    
    async def _export_xml(self, report: Dict[str, Any], filename: str) -> Path:
        """Export report as XML."""
        filepath = self.output_directory / f"{filename}.xml"
        
        # Create XML structure
        root = ET.Element("QualityReport")
        
        # Metadata
        metadata = ET.SubElement(root, "Metadata")
        ET.SubElement(metadata, "ReportID").text = report['report_metadata']['report_id']
        ET.SubElement(metadata, "GeneratedAt").text = report['report_metadata']['generated_at']
        ET.SubElement(metadata, "TotalComponents").text = str(report['report_metadata']['total_components'])
        
        # Summary
        summary = ET.SubElement(root, "Summary")
        ET.SubElement(summary, "OverallScore").text = str(report['summary']['overall_quality_score'])
        ET.SubElement(summary, "QualityGrade").text = report['summary']['quality_grade']
        ET.SubElement(summary, "TotalIssues").text = str(report['summary']['total_issues'])
        ET.SubElement(summary, "CriticalIssues").text = str(report['summary']['critical_issues'])
        
        # Components
        components = ET.SubElement(root, "Components")
        for component_name, component_data in report['component_analysis'].items():
            component = ET.SubElement(components, "Component")
            ET.SubElement(component, "Name").text = component_name
            ET.SubElement(component, "Type").text = component_data['type']
            ET.SubElement(component, "Score").text = str(component_data['score'])
            ET.SubElement(component, "IssueCount").text = str(component_data['issue_count'])
            ET.SubElement(component, "CriticalIssues").text = str(component_data['critical_issues'])
            ET.SubElement(component, "ComplianceStatus").text = component_data['compliance_status']
        
        # Write XML file
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with open(filepath, 'w') as f:
            f.write(xml_str)
        
        self.logger.info(f"Exported XML report to: {filepath}")
        return filepath
    
    async def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for real-time quality dashboard."""
        
        overall_score = await self._calculate_overall_score()
        
        # Component status summary
        component_status = {}
        for name, report in self.component_reports.items():
            status = "excellent" if report.overall_score >= 90 else \
                    "good" if report.overall_score >= 80 else \
                    "warning" if report.overall_score >= 70 else "critical"
            
            component_status[name] = {
                "score": report.overall_score,
                "status": status,
                "issues": len(report.issues),
                "critical_issues": sum(1 for issue in report.issues if issue.category == "critical")
            }
        
        # Recent trends
        trend_data = []
        if len(self.quality_history) >= 5:
            for trend in self.quality_history[-5:]:
                trend_data.append({
                    "timestamp": trend.timestamp.isoformat(),
                    "score": trend.overall_quality_score
                })
        
        # Issue distribution
        issue_distribution = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        for report in self.component_reports.values():
            for issue in report.issues:
                issue_distribution[issue.category] += 1
        
        dashboard_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_score": overall_score,
            "quality_grade": self._calculate_quality_grade(overall_score),
            "total_components": len(self.component_reports),
            "component_status": component_status,
            "issue_distribution": issue_distribution,
            "trend_data": trend_data,
            "compliance_percentage": await self._calculate_compliance_percentage(),
            "alert_level": "critical" if overall_score < 70 else 
                         "warning" if overall_score < 85 else "normal"
        }
        
        return dashboard_data
    
    async def cleanup_old_reports(self, days_to_keep: int = 30) -> None:
        """Clean up old report files."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        cleaned_count = 0
        for file_path in self.output_directory.glob("quality_report_*"):
            if file_path.stat().st_mtime < cutoff_date.timestamp():
                try:
                    file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    self.logger.warning(f"Could not delete old report {file_path}: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old report files")
    
    async def get_report_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated reports."""
        return {
            "total_reports_generated": len(self.quality_history),
            "components_tracked": len(self.component_reports),
            "current_report_id": self.current_report_id,
            "output_directory": str(self.output_directory),
            "historical_data_points": len(self.quality_history),
            "last_report_timestamp": self.quality_history[-1].timestamp.isoformat() if self.quality_history else None
        }


def run_quality_reporter_example():
    """Example usage of QualityReporter."""
    import asyncio
    
    async def example():
        # Initialize reporter
        reporter = QualityReporter()
        
        # Add sample component reports
        sample_discord_report = {
            "overall_score": 85.0,
            "compliance_status": "compliant",
            "issues": [
                {
                    "category": "medium",
                    "type": "warning",
                    "description": "Rate limiting could be optimized",
                    "count": 1,
                    "severity": 40.0,
                    "business_impact": "Performance impact under high load",
                    "suggestions": ["Implement adaptive rate limiting"]
                }
            ],
            "metrics": [
                {
                    "name": "webhook_success_rate",
                    "current_value": 98.5,
                    "target_value": 99.0,
                    "trend": "stable",
                    "category": "reliability",
                    "status": "good"
                }
            ],
            "recommendations": ["Consider implementing webhook retry logic"]
        }
        
        await reporter.add_component_report(
            "discord_integration", 
            sample_discord_report, 
            "discord_integration"
        )
        
        # Generate comprehensive report
        comprehensive_report = await reporter.generate_comprehensive_report()
        
        # Export in multiple formats
        json_path = await reporter.export_report(comprehensive_report, "json")
        html_path = await reporter.export_report(comprehensive_report, "html")
        markdown_path = await reporter.export_report(comprehensive_report, "markdown")
        
        print(f"Reports exported to:")
        print(f"  JSON: {json_path}")
        print(f"  HTML: {html_path}")
        print(f"  Markdown: {markdown_path}")
        
        # Generate dashboard data
        dashboard_data = await reporter.generate_dashboard_data()
        print(f"Dashboard data generated with overall score: {dashboard_data['overall_score']:.1f}")
    
    asyncio.run(example())


if __name__ == "__main__":
    run_quality_reporter_example()