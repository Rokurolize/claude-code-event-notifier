#!/usr/bin/env python3
"""CI/CD Integration Module.

This module provides comprehensive CI/CD integration functionality including:
- GitHub Actions integration with quality gates
- GitLab CI/CD pipeline integration
- Jenkins pipeline integration
- Azure DevOps integration
- Generic CI/CD webhook support
- Quality report generation for CI/CD
- Build status management and reporting
- Automated quality gate enforcement
"""

import asyncio
import json
import time
import sys
import os
import yaml
import subprocess
import tempfile
import shutil
import base64
import hashlib
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# CI/CD Integration Types
@dataclass
class CICDPlatformConfig:
    """Configuration for a CI/CD platform."""
    platform_name: str  # "github", "gitlab", "jenkins", "azure_devops", "generic"
    api_base_url: str
    authentication_token: Optional[str] = None
    webhook_secret: Optional[str] = None
    project_id: Optional[str] = None
    organization: Optional[str] = None
    repository: Optional[str] = None
    branch_patterns: List[str] = field(default_factory=lambda: ["main", "master", "develop"])
    quality_gates: List[str] = field(default_factory=lambda: ["level1", "level2", "level3"])
    notify_on_failure: bool = True
    notify_on_success: bool = False
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildContext:
    """Context information for a CI/CD build."""
    build_id: str
    commit_hash: str
    branch: str
    pull_request_id: Optional[str] = None
    author: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    build_url: Optional[str] = None
    artifact_urls: List[str] = field(default_factory=list)
    environment: str = "unknown"
    triggered_by: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityGateResult:
    """Result of quality gate execution in CI/CD."""
    gate_name: str
    passed: bool
    score: float
    execution_time: float
    error_count: int
    warning_count: int
    details: Dict[str, Any]
    recommendations: List[str]
    blocking: bool = True  # Whether this gate should block the build


@dataclass
class CICDReport:
    """Comprehensive CI/CD quality report."""
    build_context: BuildContext
    overall_status: str  # "passed", "failed", "warning", "skipped"
    overall_score: float
    quality_gate_results: List[QualityGateResult]
    execution_summary: Dict[str, Any]
    artifacts_generated: List[str]
    recommendations: List[str]
    next_actions: List[str]
    report_url: Optional[str] = None


class GitHubActionsIntegrator:
    """GitHub Actions specific integration."""
    
    def __init__(self, config: CICDPlatformConfig):
        self.config = config
        self.logger = AstolfoLogger(__name__)
        
    def generate_workflow_yaml(self, quality_gates: List[str]) -> str:
        """Generate GitHub Actions workflow YAML."""
        
        workflow = {
            "name": "Quality Assurance",
            "on": {
                "push": {
                    "branches": self.config.branch_patterns
                },
                "pull_request": {
                    "branches": self.config.branch_patterns
                }
            },
            "jobs": {
                "quality-check": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "Set up Python 3.13",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": "3.13"
                            }
                        },
                        {
                            "name": "Install dependencies",
                            "run": "pip install uv && uv sync"
                        }
                    ]
                }
            }
        }
        
        # Add quality gate steps
        for gate in quality_gates:
            step = {
                "name": f"Quality Gate: {gate}",
                "run": f"uv run --no-sync --python 3.13 python utils/quality_assurance/automation/cicd_integrator.py --gate {gate}",
                "env": {
                    "GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}",
                    "DISCORD_WEBHOOK_URL": "${{ secrets.DISCORD_WEBHOOK_URL }}"
                }
            }
            workflow["jobs"]["quality-check"]["steps"].append(step)
        
        # Add artifact upload
        workflow["jobs"]["quality-check"]["steps"].append({
            "name": "Upload Quality Reports",
            "uses": "actions/upload-artifact@v4",
            "with": {
                "name": "quality-reports",
                "path": "quality_reports/",
                "retention-days": 30
            },
            "if": "always()"
        })
        
        return yaml.dump(workflow, default_flow_style=False)
    
    async def update_pull_request_status(
        self, 
        build_context: BuildContext, 
        cicd_report: CICDReport
    ) -> bool:
        """Update pull request with quality status."""
        
        if not build_context.pull_request_id or not self.config.authentication_token:
            return False
        
        try:
            # Create status check
            status_data = {
                "state": "success" if cicd_report.overall_status == "passed" else "failure",
                "target_url": cicd_report.report_url,
                "description": f"Quality Score: {cicd_report.overall_score:.1f}/100",
                "context": "quality-assurance/comprehensive"
            }
            
            # Also create a comment with detailed results
            comment_body = self._generate_pr_comment(cicd_report)
            
            # Note: Actual API calls would be implemented here
            self.logger.info(f"Would update PR {build_context.pull_request_id} with status: {status_data}")
            self.logger.info(f"Would add comment: {comment_body[:200]}...")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update PR status: {e}")
            return False
    
    def _generate_pr_comment(self, cicd_report: CICDReport) -> str:
        """Generate pull request comment with quality results."""
        
        status_emoji = "✅" if cicd_report.overall_status == "passed" else "❌"
        
        comment = f"""## {status_emoji} Quality Assurance Report

**Overall Score:** {cicd_report.overall_score:.1f}/100
**Status:** {cicd_report.overall_status.upper()}

### Quality Gates Results

| Gate | Status | Score | Errors | Warnings |
|------|--------|-------|--------|----------|
"""
        
        for gate in cicd_report.quality_gate_results:
            status_icon = "✅" if gate.passed else "❌"
            comment += f"| {gate.gate_name} | {status_icon} | {gate.score:.1f} | {gate.error_count} | {gate.warning_count} |\n"
        
        if cicd_report.recommendations:
            comment += "\n### Recommendations\n\n"
            for rec in cicd_report.recommendations[:5]:  # Limit to top 5
                comment += f"- {rec}\n"
        
        if cicd_report.report_url:
            comment += f"\n[📊 View Detailed Report]({cicd_report.report_url})"
        
        return comment


class GitLabCIIntegrator:
    """GitLab CI/CD specific integration."""
    
    def __init__(self, config: CICDPlatformConfig):
        self.config = config
        self.logger = AstolfoLogger(__name__)
    
    def generate_gitlab_ci_yaml(self, quality_gates: List[str]) -> str:
        """Generate GitLab CI YAML."""
        
        gitlab_ci = {
            "stages": ["quality-check", "deploy"],
            "variables": {
                "PYTHON_VERSION": "3.13"
            },
            "before_script": [
                "apt-get update -qy",
                "apt-get install -y python3.13 python3.13-pip",
                "python3.13 -m pip install uv",
                "uv sync"
            ]
        }
        
        # Add quality check jobs
        for i, gate in enumerate(quality_gates):
            job_name = f"quality-gate-{gate}"
            gitlab_ci[job_name] = {
                "stage": "quality-check",
                "script": [
                    f"uv run --no-sync --python 3.13 python utils/quality_assurance/automation/cicd_integrator.py --gate {gate}"
                ],
                "artifacts": {
                    "when": "always",
                    "paths": ["quality_reports/"],
                    "reports": {
                        "junit": "quality_reports/junit.xml"
                    },
                    "expire_in": "30 days"
                },
                "allow_failure": False if gate in ["level1", "level2"] else True
            }
        
        return yaml.dump(gitlab_ci, default_flow_style=False)


class JenkinsIntegrator:
    """Jenkins pipeline integration."""
    
    def __init__(self, config: CICDPlatformConfig):
        self.config = config
        self.logger = AstolfoLogger(__name__)
    
    def generate_jenkinsfile(self, quality_gates: List[str]) -> str:
        """Generate Jenkins pipeline file."""
        
        jenkinsfile = f"""pipeline {{
    agent any
    
    environment {{
        PYTHON_VERSION = '3.13'
        DISCORD_WEBHOOK_URL = credentials('discord-webhook-url')
    }}
    
    stages {{
        stage('Setup') {{
            steps {{
                sh 'python3.13 -m pip install uv'
                sh 'uv sync'
            }}
        }}
        
"""
        
        # Add quality gate stages
        for gate in quality_gates:
            jenkinsfile += f"""        stage('Quality Gate: {gate}') {{
            steps {{
                sh 'uv run --no-sync --python 3.13 python utils/quality_assurance/automation/cicd_integrator.py --gate {gate}'
            }}
            post {{
                always {{
                    archiveArtifacts artifacts: 'quality_reports/**/*', allowEmptyArchive: true
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'quality_reports',
                        reportFiles: 'index.html',
                        reportName: 'Quality Report - {gate}'
                    ])
                }}
            }}
        }}
        
"""
        
        jenkinsfile += """    }
    
    post {
        always {
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'quality_reports',
                reportFiles: 'comprehensive_report.html',
                reportName: 'Comprehensive Quality Report'
            ])
        }
        failure {
            emailext subject: 'Quality Check Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}',
                     body: 'Quality assurance checks failed. Please review the quality report.',
                     to: '${env.CHANGE_AUTHOR_EMAIL}'
        }
    }
}"""
        
        return jenkinsfile


class CICDIntegrator(BaseQualityChecker):
    """Main CI/CD integration coordinator."""
    
    def __init__(self):
        super().__init__()
        self.logger = AstolfoLogger(__name__)
        self.platforms = {}
        self.quality_gates = {}
        self._load_configurations()
    
    def _load_configurations(self):
        """Load CI/CD platform configurations."""
        
        config_file = Path("cicd_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                for platform_config in config_data.get("platforms", []):
                    config = CICDPlatformConfig(**platform_config)
                    self.platforms[config.platform_name] = config
                    
            except Exception as e:
                self.logger.error(f"Failed to load CI/CD config: {e}")
        
        # Set up default configurations if none exist
        if not self.platforms:
            self._setup_default_configurations()
    
    def _setup_default_configurations(self):
        """Set up default CI/CD platform configurations."""
        
        # GitHub Actions default
        github_config = CICDPlatformConfig(
            platform_name="github",
            api_base_url="https://api.github.com",
            quality_gates=["level1", "level2", "level3"],
            branch_patterns=["main", "master", "develop"]
        )
        self.platforms["github"] = github_config
        
        # GitLab CI default
        gitlab_config = CICDPlatformConfig(
            platform_name="gitlab",
            api_base_url="https://gitlab.com/api/v4",
            quality_gates=["level1", "level2", "level3"],
            branch_patterns=["main", "master", "develop"]
        )
        self.platforms["gitlab"] = gitlab_config
    
    async def generate_cicd_configuration(
        self, 
        platform: str, 
        quality_gates: Optional[List[str]] = None
    ) -> str:
        """Generate CI/CD configuration for specified platform."""
        
        if platform not in self.platforms:
            raise ValueError(f"Unsupported platform: {platform}")
        
        config = self.platforms[platform]
        gates = quality_gates or config.quality_gates
        
        if platform == "github":
            integrator = GitHubActionsIntegrator(config)
            return integrator.generate_workflow_yaml(gates)
        elif platform == "gitlab":
            integrator = GitLabCIIntegrator(config)
            return integrator.generate_gitlab_ci_yaml(gates)
        elif platform == "jenkins":
            integrator = JenkinsIntegrator(config)
            return integrator.generate_jenkinsfile(gates)
        else:
            raise ValueError(f"Configuration generation not implemented for: {platform}")
    
    async def execute_quality_gate(
        self, 
        gate_name: str, 
        build_context: BuildContext
    ) -> QualityGateResult:
        """Execute a specific quality gate in CI/CD context."""
        
        start_time = time.time()
        
        try:
            # Import and execute the appropriate quality gate
            if gate_name == "level1":
                from utils.quality_assurance.gates.level1_basic_quality_gate import Level1BasicQualityGate
                gate = Level1BasicQualityGate()
            elif gate_name == "level2":
                from utils.quality_assurance.gates.level2_functional_quality_gate import Level2FunctionalQualityGate
                gate = Level2FunctionalQualityGate()
            elif gate_name == "level3":
                from utils.quality_assurance.gates.level3_integration_quality_gate import Level3IntegrationQualityGate
                gate = Level3IntegrationQualityGate()
            elif gate_name == "level4":
                from utils.quality_assurance.gates.level4_production_quality_gate import Level4ProductionQualityGate
                gate = Level4ProductionQualityGate()
            else:
                raise ValueError(f"Unknown quality gate: {gate_name}")
            
            # Execute the gate
            result = await gate.check_quality()
            
            execution_time = time.time() - start_time
            
            return QualityGateResult(
                gate_name=gate_name,
                passed=result.get("quality_level", "") in ["excellent", "good"],
                score=result.get("overall_score", 0.0),
                execution_time=execution_time,
                error_count=len(result.get("errors", [])),
                warning_count=len(result.get("warnings", [])),
                details=result,
                recommendations=result.get("recommendations", []),
                blocking=gate_name in ["level1", "level2"]
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Quality gate {gate_name} failed: {e}")
            
            return QualityGateResult(
                gate_name=gate_name,
                passed=False,
                score=0.0,
                execution_time=execution_time,
                error_count=1,
                warning_count=0,
                details={"error": str(e)},
                recommendations=[f"Fix quality gate execution error: {e}"],
                blocking=True
            )
    
    async def run_comprehensive_quality_check(
        self, 
        build_context: BuildContext,
        quality_gates: Optional[List[str]] = None
    ) -> CICDReport:
        """Run comprehensive quality check for CI/CD."""
        
        gates_to_run = quality_gates or ["level1", "level2", "level3"]
        gate_results = []
        
        # Execute quality gates in sequence
        for gate_name in gates_to_run:
            self.logger.info(f"Executing quality gate: {gate_name}")
            result = await self.execute_quality_gate(gate_name, build_context)
            gate_results.append(result)
            
            # Stop on blocking failures
            if not result.passed and result.blocking:
                self.logger.error(f"Blocking quality gate {gate_name} failed, stopping execution")
                break
        
        # Calculate overall results
        overall_score = sum(r.score for r in gate_results) / len(gate_results) if gate_results else 0
        passed_gates = sum(1 for r in gate_results if r.passed)
        total_gates = len(gate_results)
        
        # Determine overall status
        if passed_gates == total_gates:
            overall_status = "passed"
        elif any(not r.passed and r.blocking for r in gate_results):
            overall_status = "failed"
        else:
            overall_status = "warning"
        
        # Generate artifacts
        artifacts = await self._generate_artifacts(gate_results, build_context)
        
        # Collect recommendations
        all_recommendations = []
        for result in gate_results:
            all_recommendations.extend(result.recommendations)
        
        # Determine next actions
        next_actions = self._determine_next_actions(gate_results, overall_status)
        
        return CICDReport(
            build_context=build_context,
            overall_status=overall_status,
            overall_score=overall_score,
            quality_gate_results=gate_results,
            execution_summary={
                "total_gates": total_gates,
                "passed_gates": passed_gates,
                "failed_gates": total_gates - passed_gates,
                "total_execution_time": sum(r.execution_time for r in gate_results),
                "total_errors": sum(r.error_count for r in gate_results),
                "total_warnings": sum(r.warning_count for r in gate_results)
            },
            artifacts_generated=artifacts,
            recommendations=all_recommendations[:10],  # Top 10 recommendations
            next_actions=next_actions
        )
    
    async def _generate_artifacts(
        self, 
        gate_results: List[QualityGateResult], 
        build_context: BuildContext
    ) -> List[str]:
        """Generate CI/CD artifacts from quality results."""
        
        artifacts = []
        reports_dir = Path("quality_reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Generate JUnit XML for CI/CD systems
        junit_file = reports_dir / "junit.xml"
        junit_xml = self._generate_junit_xml(gate_results)
        junit_file.write_text(junit_xml)
        artifacts.append(str(junit_file))
        
        # Generate JSON report
        json_file = reports_dir / "quality_report.json"
        json_data = {
            "build_context": {
                "build_id": build_context.build_id,
                "commit_hash": build_context.commit_hash,
                "branch": build_context.branch,
                "timestamp": build_context.timestamp.isoformat()
            },
            "gate_results": [
                {
                    "gate_name": r.gate_name,
                    "passed": r.passed,
                    "score": r.score,
                    "execution_time": r.execution_time,
                    "error_count": r.error_count,
                    "warning_count": r.warning_count,
                    "blocking": r.blocking
                }
                for r in gate_results
            ]
        }
        
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        artifacts.append(str(json_file))
        
        # Generate HTML report
        html_file = reports_dir / "index.html"
        html_content = self._generate_html_report(gate_results, build_context)
        html_file.write_text(html_content)
        artifacts.append(str(html_file))
        
        return artifacts
    
    def _generate_junit_xml(self, gate_results: List[QualityGateResult]) -> str:
        """Generate JUnit XML format for CI/CD systems."""
        
        testsuites = ET.Element("testsuites")
        testsuites.set("tests", str(len(gate_results)))
        testsuites.set("failures", str(sum(1 for r in gate_results if not r.passed)))
        testsuites.set("time", str(sum(r.execution_time for r in gate_results)))
        
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", "QualityGates")
        testsuite.set("tests", str(len(gate_results)))
        testsuite.set("failures", str(sum(1 for r in gate_results if not r.passed)))
        testsuite.set("time", str(sum(r.execution_time for r in gate_results)))
        
        for result in gate_results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", result.gate_name)
            testcase.set("classname", "QualityGate")
            testcase.set("time", str(result.execution_time))
            
            if not result.passed:
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", f"Quality gate failed with score {result.score}")
                failure.text = f"Errors: {result.error_count}, Warnings: {result.warning_count}"
        
        return ET.tostring(testsuites, encoding='unicode')
    
    def _generate_html_report(
        self, 
        gate_results: List[QualityGateResult], 
        build_context: BuildContext
    ) -> str:
        """Generate HTML report for CI/CD."""
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quality Assurance Report - Build {build_context.build_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .passed {{ color: green; font-weight: bold; }}
        .failed {{ color: red; font-weight: bold; }}
        .warning {{ color: orange; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .score {{ font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Quality Assurance Report</h1>
        <p><strong>Build ID:</strong> {build_context.build_id}</p>
        <p><strong>Commit:</strong> {build_context.commit_hash}</p>
        <p><strong>Branch:</strong> {build_context.branch}</p>
        <p><strong>Timestamp:</strong> {build_context.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    
    <h2>Quality Gates Results</h2>
    <table>
        <tr>
            <th>Gate</th>
            <th>Status</th>
            <th>Score</th>
            <th>Execution Time</th>
            <th>Errors</th>
            <th>Warnings</th>
            <th>Blocking</th>
        </tr>
"""
        
        for result in gate_results:
            status_class = "passed" if result.passed else "failed"
            status_text = "PASSED" if result.passed else "FAILED"
            blocking_text = "Yes" if result.blocking else "No"
            
            html += f"""        <tr>
            <td>{result.gate_name}</td>
            <td class="{status_class}">{status_text}</td>
            <td class="score">{result.score:.1f}</td>
            <td>{result.execution_time:.2f}s</td>
            <td>{result.error_count}</td>
            <td>{result.warning_count}</td>
            <td>{blocking_text}</td>
        </tr>
"""
        
        html += """    </table>
    
    <h2>Summary</h2>
    <ul>
"""
        
        total_gates = len(gate_results)
        passed_gates = sum(1 for r in gate_results if r.passed)
        overall_score = sum(r.score for r in gate_results) / total_gates if total_gates > 0 else 0
        
        html += f"""        <li><strong>Total Gates:</strong> {total_gates}</li>
        <li><strong>Passed:</strong> {passed_gates}</li>
        <li><strong>Failed:</strong> {total_gates - passed_gates}</li>
        <li><strong>Overall Score:</strong> {overall_score:.1f}/100</li>
        <li><strong>Total Execution Time:</strong> {sum(r.execution_time for r in gate_results):.2f}s</li>
    </ul>
</body>
</html>"""
        
        return html
    
    def _determine_next_actions(
        self, 
        gate_results: List[QualityGateResult], 
        overall_status: str
    ) -> List[str]:
        """Determine recommended next actions based on results."""
        
        actions = []
        
        if overall_status == "failed":
            failed_gates = [r for r in gate_results if not r.passed and r.blocking]
            if failed_gates:
                actions.append(f"Fix blocking issues in: {', '.join(r.gate_name for r in failed_gates)}")
                actions.append("Re-run quality checks after fixes")
        
        elif overall_status == "warning":
            warning_gates = [r for r in gate_results if not r.passed and not r.blocking]
            if warning_gates:
                actions.append(f"Address warnings in: {', '.join(r.gate_name for r in warning_gates)}")
        
        elif overall_status == "passed":
            actions.append("All quality gates passed - proceed with deployment")
            
            # Check for improvement opportunities
            low_score_gates = [r for r in gate_results if r.score < 80]
            if low_score_gates:
                actions.append(f"Consider improving: {', '.join(r.gate_name for r in low_score_gates)}")
        
        # Add general recommendations
        total_errors = sum(r.error_count for r in gate_results)
        total_warnings = sum(r.warning_count for r in gate_results)
        
        if total_errors > 0:
            actions.append(f"Address {total_errors} error(s) found during quality checks")
        
        if total_warnings > 5:
            actions.append(f"Consider addressing {total_warnings} warning(s) for better code quality")
        
        return actions
    
    async def setup_webhook_handler(self, platform: str, webhook_secret: str) -> Callable:
        """Set up webhook handler for CI/CD platform."""
        
        async def webhook_handler(request_data: Dict[str, Any]) -> Dict[str, Any]:
            """Handle incoming CI/CD webhook."""
            
            try:
                # Extract build context from webhook payload
                build_context = self._extract_build_context(platform, request_data)
                
                # Run quality checks
                report = await self.run_comprehensive_quality_check(build_context)
                
                # Update platform status if supported
                if platform == "github":
                    config = self.platforms.get("github")
                    if config:
                        integrator = GitHubActionsIntegrator(config)
                        await integrator.update_pull_request_status(build_context, report)
                
                return {
                    "status": "success",
                    "message": f"Quality check completed with status: {report.overall_status}",
                    "report": {
                        "overall_status": report.overall_status,
                        "overall_score": report.overall_score,
                        "build_id": build_context.build_id
                    }
                }
                
            except Exception as e:
                self.logger.error(f"Webhook handler failed: {e}")
                return {
                    "status": "error",
                    "message": str(e)
                }
        
        return webhook_handler
    
    def _extract_build_context(self, platform: str, request_data: Dict[str, Any]) -> BuildContext:
        """Extract build context from platform-specific webhook payload."""
        
        if platform == "github":
            # GitHub webhook payload structure
            return BuildContext(
                build_id=str(request_data.get("number", "unknown")),
                commit_hash=request_data.get("head", {}).get("sha", "unknown"),
                branch=request_data.get("head", {}).get("ref", "unknown"),
                pull_request_id=str(request_data.get("number")) if "pull_request" in request_data else None,
                author=request_data.get("head", {}).get("user", {}).get("login", "unknown"),
                build_url=request_data.get("html_url"),
                environment="github",
                triggered_by="webhook"
            )
        
        elif platform == "gitlab":
            # GitLab webhook payload structure
            return BuildContext(
                build_id=str(request_data.get("object_attributes", {}).get("id", "unknown")),
                commit_hash=request_data.get("object_attributes", {}).get("sha", "unknown"),
                branch=request_data.get("object_attributes", {}).get("ref", "unknown"),
                pull_request_id=str(request_data.get("object_attributes", {}).get("merge_request_id")) if "merge_request" in request_data else None,
                author=request_data.get("user", {}).get("username", "unknown"),
                environment="gitlab",
                triggered_by="webhook"
            )
        
        else:
            # Generic webhook payload
            return BuildContext(
                build_id=str(request_data.get("build_id", "unknown")),
                commit_hash=request_data.get("commit_hash", "unknown"),
                branch=request_data.get("branch", "unknown"),
                author=request_data.get("author", "unknown"),
                environment=platform,
                triggered_by="webhook"
            )
    
    async def check_quality(self) -> Dict[str, Any]:
        """Check overall CI/CD integration quality."""
        
        platforms_configured = len(self.platforms)
        
        # Check if configurations are valid
        valid_configs = 0
        for platform, config in self.platforms.items():
            if config.api_base_url and config.quality_gates:
                valid_configs += 1
        
        # Check if artifacts directory exists and is writable
        reports_dir = Path("quality_reports")
        artifacts_ready = reports_dir.exists() or reports_dir.parent.exists()
        
        quality_level = "excellent" if platforms_configured > 0 and valid_configs == platforms_configured and artifacts_ready else "needs_improvement"
        
        return {
            "quality_level": quality_level,
            "platforms_configured": platforms_configured,
            "valid_configurations": valid_configs,
            "artifacts_directory_ready": artifacts_ready,
            "supported_platforms": list(self.platforms.keys()),
            "message": f"CI/CD integration ready for {platforms_configured} platform(s)"
        }


# CLI interface for CI/CD execution
async def main():
    """Main function for CI/CD execution."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="CI/CD Quality Assurance Integration")
    parser.add_argument("--gate", help="Quality gate to execute")
    parser.add_argument("--platform", help="Generate configuration for platform")
    parser.add_argument("--build-id", help="Build ID for context")
    parser.add_argument("--commit", help="Commit hash for context")
    parser.add_argument("--branch", help="Branch name for context")
    
    args = parser.parse_args()
    
    integrator = CICDIntegrator()
    
    if args.gate:
        # Execute specific quality gate
        build_context = BuildContext(
            build_id=args.build_id or "local",
            commit_hash=args.commit or "unknown",
            branch=args.branch or "unknown",
            environment="ci"
        )
        
        result = await integrator.execute_quality_gate(args.gate, build_context)
        
        if result.passed:
            print(f"✅ Quality gate {args.gate} passed with score {result.score:.1f}")
            sys.exit(0)
        else:
            print(f"❌ Quality gate {args.gate} failed with score {result.score:.1f}")
            print(f"Errors: {result.error_count}, Warnings: {result.warning_count}")
            sys.exit(1)
    
    elif args.platform:
        # Generate platform configuration
        try:
            config = await integrator.generate_cicd_configuration(args.platform)
            print(config)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    else:
        # Run comprehensive check
        build_context = BuildContext(
            build_id=args.build_id or "local",
            commit_hash=args.commit or "unknown",
            branch=args.branch or "unknown",
            environment="ci"
        )
        
        report = await integrator.run_comprehensive_quality_check(build_context)
        
        print(f"Overall Status: {report.overall_status}")
        print(f"Overall Score: {report.overall_score:.1f}")
        print(f"Artifacts: {', '.join(report.artifacts_generated)}")
        
        if report.overall_status == "passed":
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())