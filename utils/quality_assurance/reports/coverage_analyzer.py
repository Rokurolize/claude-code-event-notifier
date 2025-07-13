#!/usr/bin/env python3
"""Coverage Analyzer.

This module provides comprehensive coverage analysis functionality including:
- Code coverage analysis and reporting
- Test coverage assessment across components
- Quality coverage mapping and gap identification
- Feature coverage verification and validation
- Documentation coverage analysis
- Security coverage assessment
- Performance coverage evaluation
- Integration coverage validation
"""

import asyncio
import json
import time
import sys
import os
import ast
import statistics
import tempfile
import subprocess
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypedDict, Protocol
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import coverage
import xml.etree.ElementTree as ET

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger
from utils.quality_assurance.checkers.base_checker import BaseQualityChecker


# Coverage Analysis Types
@dataclass
class CodeCoverageData:
    """Code coverage data for analysis."""
    file_path: str
    total_lines: int
    covered_lines: int
    missed_lines: int
    coverage_percentage: float
    missing_line_numbers: List[int]
    branch_coverage: Optional[float] = None
    function_coverage: Optional[float] = None


@dataclass
class TestCoverageData:
    """Test coverage data for analysis."""
    component_name: str
    total_functions: int
    tested_functions: int
    total_classes: int
    tested_classes: int
    total_endpoints: int
    tested_endpoints: int
    coverage_percentage: float
    missing_tests: List[str]
    test_types: Dict[str, int]  # unit, integration, e2e counts


@dataclass
class QualityCoverageData:
    """Quality coverage data for analysis."""
    quality_aspect: str  # "security", "performance", "reliability", etc.
    total_checkpoints: int
    covered_checkpoints: int
    coverage_percentage: float
    missing_checkpoints: List[str]
    quality_score: float
    recommendations: List[str]


@dataclass
class FeatureCoverageData:
    """Feature coverage data for analysis."""
    feature_name: str
    implementation_coverage: float
    test_coverage: float
    documentation_coverage: float
    quality_coverage: float
    overall_coverage: float
    status: str  # "complete", "partial", "missing"
    gaps: List[str]


@dataclass
class CoverageReport:
    """Comprehensive coverage report."""
    report_id: str
    generated_at: datetime
    overall_coverage: float
    code_coverage: List[CodeCoverageData]
    test_coverage: List[TestCoverageData]
    quality_coverage: List[QualityCoverageData]
    feature_coverage: List[FeatureCoverageData]
    coverage_trends: Dict[str, List[float]]
    recommendations: List[str]
    critical_gaps: List[str]


class CodeCoverageAnalyzer:
    """Analyzes code coverage using Python coverage tools."""
    
    def __init__(self, project_root: Path):
        self.logger = AstolfoLogger(__name__)
        self.project_root = project_root
        self.coverage_data_file = project_root / ".coverage"
    
    async def analyze_code_coverage(
        self, 
        source_dirs: List[str] = None,
        test_command: str = None
    ) -> List[CodeCoverageData]:
        """Analyze code coverage for the project."""
        
        if source_dirs is None:
            source_dirs = ["src", "utils"]
        
        coverage_results = []
        
        try:
            # Initialize coverage
            cov = coverage.Coverage(
                source=source_dirs,
                branch=True,
                data_file=str(self.coverage_data_file)
            )
            
            # Check if we have existing coverage data
            if self.coverage_data_file.exists():
                cov.load()
                self.logger.info("Loaded existing coverage data")
            else:
                # Run tests with coverage if test command provided
                if test_command:
                    await self._run_tests_with_coverage(test_command, cov)
                else:
                    self.logger.warning("No existing coverage data and no test command provided")
                    return []
            
            # Analyze coverage for each source file
            for source_dir in source_dirs:
                source_path = self.project_root / source_dir
                if not source_path.exists():
                    continue
                
                for py_file in source_path.rglob("*.py"):
                    if py_file.name.startswith("test_") or "__pycache__" in str(py_file):
                        continue
                    
                    try:
                        relative_path = str(py_file.relative_to(self.project_root))
                        coverage_data = await self._analyze_file_coverage(cov, py_file, relative_path)
                        if coverage_data:
                            coverage_results.append(coverage_data)
                    except Exception as e:
                        self.logger.warning(f"Could not analyze coverage for {py_file}: {e}")
            
        except Exception as e:
            self.logger.error(f"Code coverage analysis failed: {e}")
        
        return coverage_results
    
    async def _run_tests_with_coverage(self, test_command: str, cov: coverage.Coverage) -> None:
        """Run tests with coverage measurement."""
        try:
            self.logger.info(f"Running tests with coverage: {test_command}")
            
            # Start coverage
            cov.start()
            
            # Run tests
            process = await asyncio.create_subprocess_shell(
                test_command,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Stop coverage
            cov.stop()
            cov.save()
            
            if process.returncode != 0:
                self.logger.warning(f"Tests failed: {stderr.decode()}")
            else:
                self.logger.info("Tests completed successfully with coverage")
                
        except Exception as e:
            self.logger.error(f"Failed to run tests with coverage: {e}")
    
    async def _analyze_file_coverage(
        self, 
        cov: coverage.Coverage, 
        file_path: Path, 
        relative_path: str
    ) -> Optional[CodeCoverageData]:
        """Analyze coverage for a specific file."""
        try:
            # Get coverage analysis
            analysis = cov.analysis2(str(file_path))
            
            if analysis is None:
                return None
            
            filename, executed, excluded, missing, missing_formatted = analysis
            
            # Count total lines (excluding comments and empty lines)
            total_lines = await self._count_executable_lines(file_path)
            
            covered_lines = len(executed)
            missed_lines = len(missing)
            
            if total_lines > 0:
                coverage_percentage = (covered_lines / total_lines) * 100
            else:
                coverage_percentage = 0.0
            
            # Get branch coverage if available
            branch_coverage = None
            try:
                branch_stats = cov.branch_stats().get(str(file_path))
                if branch_stats:
                    total_branches, covered_branches = branch_stats
                    if total_branches > 0:
                        branch_coverage = (covered_branches / total_branches) * 100
            except:
                pass
            
            return CodeCoverageData(
                file_path=relative_path,
                total_lines=total_lines,
                covered_lines=covered_lines,
                missed_lines=missed_lines,
                coverage_percentage=coverage_percentage,
                missing_line_numbers=list(missing),
                branch_coverage=branch_coverage
            )
            
        except Exception as e:
            self.logger.warning(f"Could not analyze coverage for {file_path}: {e}")
            return None
    
    async def _count_executable_lines(self, file_path: Path) -> int:
        """Count executable lines in a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            # Count nodes that represent executable statements
            executable_count = 0
            for node in ast.walk(tree):
                if isinstance(node, (
                    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                    ast.Return, ast.Assign, ast.AugAssign, ast.AnnAssign,
                    ast.For, ast.AsyncFor, ast.While, ast.If,
                    ast.With, ast.AsyncWith, ast.Raise, ast.Try,
                    ast.Assert, ast.Import, ast.ImportFrom,
                    ast.Global, ast.Nonlocal, ast.Expr
                )):
                    executable_count += 1
            
            return executable_count
            
        except Exception as e:
            self.logger.warning(f"Could not count executable lines in {file_path}: {e}")
            # Fallback: count non-empty, non-comment lines
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                executable_count = 0
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'):
                        executable_count += 1
                
                return executable_count
            except:
                return 0


class TestCoverageAnalyzer:
    """Analyzes test coverage across components."""
    
    def __init__(self, project_root: Path):
        self.logger = AstolfoLogger(__name__)
        self.project_root = project_root
        self.test_dirs = ["tests"]
        self.source_dirs = ["src", "utils"]
    
    async def analyze_test_coverage(self) -> List[TestCoverageData]:
        """Analyze test coverage for all components."""
        
        coverage_results = []
        
        # Define component mapping
        components = {
            "discord_integration": {
                "source_patterns": ["src/discord_notifier.py", "src/handlers/discord_sender.py", "src/core/http_client.py"],
                "test_patterns": ["tests/discord_integration/", "tests/integration/test_*discord*"]
            },
            "content_processing": {
                "source_patterns": ["src/formatters/", "src/handlers/"],
                "test_patterns": ["tests/content_processing/", "tests/unit/test_*format*"]
            },
            "data_management": {
                "source_patterns": ["src/thread_storage.py", "src/core/config*.py"],
                "test_patterns": ["tests/data_management/", "tests/unit/test_*config*", "tests/unit/test_*storage*"]
            },
            "quality_validation": {
                "source_patterns": ["src/type_guards.py", "src/validators*.py", "utils/quality_assurance/"],
                "test_patterns": ["tests/quality_validation/", "tests/unit/test_type_*", "tests/unit/test_*validation*"]
            },
            "integration_control": {
                "source_patterns": ["src/core/", "utils/quality_assurance/checkers/"],
                "test_patterns": ["tests/integration_control/", "tests/integration/"]
            }
        }
        
        for component_name, component_config in components.items():
            coverage_data = await self._analyze_component_coverage(
                component_name, 
                component_config["source_patterns"],
                component_config["test_patterns"]
            )
            if coverage_data:
                coverage_results.append(coverage_data)
        
        return coverage_results
    
    async def _analyze_component_coverage(
        self, 
        component_name: str,
        source_patterns: List[str],
        test_patterns: List[str]
    ) -> Optional[TestCoverageData]:
        """Analyze test coverage for a specific component."""
        
        try:
            # Find source files
            source_files = []
            for pattern in source_patterns:
                source_files.extend(await self._find_files_by_pattern(pattern))
            
            # Find test files
            test_files = []
            for pattern in test_patterns:
                test_files.extend(await self._find_files_by_pattern(pattern))
            
            # Analyze source code
            total_functions = 0
            total_classes = 0
            total_endpoints = 0
            
            for source_file in source_files:
                stats = await self._analyze_source_file(source_file)
                total_functions += stats["functions"]
                total_classes += stats["classes"]
                total_endpoints += stats["endpoints"]
            
            # Analyze test coverage
            tested_functions = 0
            tested_classes = 0
            tested_endpoints = 0
            test_types = {"unit": 0, "integration": 0, "e2e": 0}
            missing_tests = []
            
            for test_file in test_files:
                test_stats = await self._analyze_test_file(test_file)
                tested_functions += test_stats["tested_functions"]
                tested_classes += test_stats["tested_classes"]
                tested_endpoints += test_stats["tested_endpoints"]
                
                # Categorize test types
                if "unit" in str(test_file):
                    test_types["unit"] += test_stats["test_count"]
                elif "integration" in str(test_file):
                    test_types["integration"] += test_stats["test_count"]
                elif "e2e" in str(test_file) or "end_to_end" in str(test_file):
                    test_types["e2e"] += test_stats["test_count"]
                else:
                    test_types["unit"] += test_stats["test_count"]  # Default to unit
            
            # Calculate coverage percentage
            total_testable = total_functions + total_classes + total_endpoints
            total_tested = tested_functions + tested_classes + tested_endpoints
            
            if total_testable > 0:
                coverage_percentage = (total_tested / total_testable) * 100
            else:
                coverage_percentage = 0.0
            
            # Identify missing tests
            missing_tests = await self._identify_missing_tests(source_files, test_files)
            
            return TestCoverageData(
                component_name=component_name,
                total_functions=total_functions,
                tested_functions=tested_functions,
                total_classes=total_classes,
                tested_classes=tested_classes,
                total_endpoints=total_endpoints,
                tested_endpoints=tested_endpoints,
                coverage_percentage=coverage_percentage,
                missing_tests=missing_tests,
                test_types=test_types
            )
            
        except Exception as e:
            self.logger.warning(f"Could not analyze test coverage for {component_name}: {e}")
            return None
    
    async def _find_files_by_pattern(self, pattern: str) -> List[Path]:
        """Find files matching a pattern."""
        files = []
        
        try:
            pattern_path = self.project_root / pattern
            
            if pattern_path.is_file():
                files.append(pattern_path)
            elif pattern_path.is_dir():
                files.extend(pattern_path.rglob("*.py"))
            else:
                # Handle glob patterns
                parent_dir = self.project_root
                if "/" in pattern:
                    parts = pattern.split("/")
                    for part in parts[:-1]:
                        parent_dir = parent_dir / part
                        if not parent_dir.exists():
                            break
                    else:
                        glob_pattern = parts[-1]
                        if glob_pattern.endswith("*"):
                            files.extend(parent_dir.rglob("*.py"))
                        else:
                            files.extend(parent_dir.glob(f"*{glob_pattern}*.py"))
        except Exception as e:
            self.logger.debug(f"Could not find files for pattern {pattern}: {e}")
        
        return files
    
    async def _analyze_source_file(self, file_path: Path) -> Dict[str, int]:
        """Analyze a source file for testable elements."""
        
        stats = {"functions": 0, "classes": 0, "endpoints": 0}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    stats["functions"] += 1
                    
                    # Check if it's an endpoint (simple heuristic)
                    if any(keyword in node.name.lower() for keyword in ["endpoint", "route", "handler", "api"]):
                        stats["endpoints"] += 1
                elif isinstance(node, ast.ClassDef):
                    stats["classes"] += 1
        
        except Exception as e:
            self.logger.debug(f"Could not analyze source file {file_path}: {e}")
        
        return stats
    
    async def _analyze_test_file(self, file_path: Path) -> Dict[str, int]:
        """Analyze a test file for coverage information."""
        
        stats = {
            "test_count": 0,
            "tested_functions": 0,
            "tested_classes": 0,
            "tested_endpoints": 0
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("test_"):
                        stats["test_count"] += 1
                        
                        # Analyze what the test covers (simple heuristic)
                        if "function" in node.name or "method" in node.name:
                            stats["tested_functions"] += 1
                        elif "class" in node.name:
                            stats["tested_classes"] += 1
                        elif any(keyword in node.name for keyword in ["endpoint", "api", "route"]):
                            stats["tested_endpoints"] += 1
                        else:
                            stats["tested_functions"] += 1  # Default assumption
        
        except Exception as e:
            self.logger.debug(f"Could not analyze test file {file_path}: {e}")
        
        return stats
    
    async def _identify_missing_tests(self, source_files: List[Path], test_files: List[Path]) -> List[str]:
        """Identify missing tests by comparing source and test files."""
        
        missing_tests = []
        
        try:
            # Extract function and class names from source files
            source_elements = set()
            for source_file in source_files:
                elements = await self._extract_testable_elements(source_file)
                source_elements.update(elements)
            
            # Extract tested elements from test files
            tested_elements = set()
            for test_file in test_files:
                elements = await self._extract_tested_elements(test_file)
                tested_elements.update(elements)
            
            # Find missing tests
            for element in source_elements:
                if element not in tested_elements:
                    missing_tests.append(element)
        
        except Exception as e:
            self.logger.debug(f"Could not identify missing tests: {e}")
        
        return missing_tests
    
    async def _extract_testable_elements(self, file_path: Path) -> Set[str]:
        """Extract testable element names from a source file."""
        
        elements = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith('_'):  # Skip private functions
                        elements.add(node.name)
                elif isinstance(node, ast.ClassDef):
                    elements.add(node.name)
        
        except Exception as e:
            self.logger.debug(f"Could not extract elements from {file_path}: {e}")
        
        return elements
    
    async def _extract_tested_elements(self, file_path: Path) -> Set[str]:
        """Extract tested element names from a test file."""
        
        elements = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple pattern matching for tested elements
            # Look for common patterns in test names and content
            patterns = [
                r'test_(\w+)',
                r'def test_.*?(\w+)',
                r'self\.(\w+)\(',
                r'await\s+(\w+)\(',
                r'(\w+)\.(\w+)\('
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        elements.update(match)
                    else:
                        elements.add(match)
        
        except Exception as e:
            self.logger.debug(f"Could not extract tested elements from {file_path}: {e}")
        
        return elements


class QualityCoverageAnalyzer:
    """Analyzes quality coverage across different aspects."""
    
    def __init__(self, project_root: Path):
        self.logger = AstolfoLogger(__name__)
        self.project_root = project_root
    
    async def analyze_quality_coverage(self) -> List[QualityCoverageData]:
        """Analyze quality coverage across different aspects."""
        
        quality_aspects = {
            "security": {
                "checkpoints": [
                    "input_validation", "output_sanitization", "authentication",
                    "authorization", "data_encryption", "secure_communication",
                    "secret_management", "vulnerability_scanning"
                ],
                "patterns": ["security", "auth", "validate", "sanitiz", "encrypt"]
            },
            "performance": {
                "checkpoints": [
                    "response_time_monitoring", "resource_usage_tracking",
                    "caching_implementation", "optimization_techniques",
                    "load_testing", "stress_testing", "bottleneck_analysis"
                ],
                "patterns": ["performance", "benchmark", "optimize", "cache", "async"]
            },
            "reliability": {
                "checkpoints": [
                    "error_handling", "retry_mechanisms", "failover_logic",
                    "monitoring_alerts", "health_checks", "circuit_breakers",
                    "graceful_degradation", "data_consistency"
                ],
                "patterns": ["error", "retry", "failover", "monitor", "health", "exception"]
            },
            "maintainability": {
                "checkpoints": [
                    "code_documentation", "type_annotations", "unit_tests",
                    "integration_tests", "code_structure", "dependency_management",
                    "logging_implementation", "configuration_management"
                ],
                "patterns": ["doc", "type", "test", "log", "config", "comment"]
            },
            "scalability": {
                "checkpoints": [
                    "horizontal_scaling", "vertical_scaling", "load_balancing",
                    "resource_pooling", "async_processing", "queue_management",
                    "data_partitioning", "microservices_architecture"
                ],
                "patterns": ["scale", "pool", "queue", "async", "concurrent", "parallel"]
            }
        }
        
        coverage_results = []
        
        for aspect_name, aspect_config in quality_aspects.items():
            coverage_data = await self._analyze_quality_aspect(
                aspect_name,
                aspect_config["checkpoints"],
                aspect_config["patterns"]
            )
            if coverage_data:
                coverage_results.append(coverage_data)
        
        return coverage_results
    
    async def _analyze_quality_aspect(
        self,
        aspect_name: str,
        checkpoints: List[str],
        search_patterns: List[str]
    ) -> Optional[QualityCoverageData]:
        """Analyze coverage for a specific quality aspect."""
        
        try:
            # Find relevant files
            relevant_files = await self._find_relevant_files(search_patterns)
            
            # Analyze coverage for each checkpoint
            covered_checkpoints = 0
            missing_checkpoints = []
            quality_score = 0.0
            
            for checkpoint in checkpoints:
                is_covered = await self._check_checkpoint_coverage(
                    checkpoint, relevant_files, search_patterns
                )
                
                if is_covered:
                    covered_checkpoints += 1
                    quality_score += 100 / len(checkpoints)
                else:
                    missing_checkpoints.append(checkpoint)
            
            coverage_percentage = (covered_checkpoints / len(checkpoints)) * 100
            
            # Generate recommendations
            recommendations = await self._generate_quality_recommendations(
                aspect_name, missing_checkpoints
            )
            
            return QualityCoverageData(
                quality_aspect=aspect_name,
                total_checkpoints=len(checkpoints),
                covered_checkpoints=covered_checkpoints,
                coverage_percentage=coverage_percentage,
                missing_checkpoints=missing_checkpoints,
                quality_score=quality_score,
                recommendations=recommendations
            )
            
        except Exception as e:
            self.logger.warning(f"Could not analyze quality coverage for {aspect_name}: {e}")
            return None
    
    async def _find_relevant_files(self, search_patterns: List[str]) -> List[Path]:
        """Find files relevant to quality aspects."""
        
        relevant_files = []
        
        search_dirs = ["src", "utils", "tests"]
        
        for search_dir in search_dirs:
            dir_path = self.project_root / search_dir
            if not dir_path.exists():
                continue
            
            for py_file in dir_path.rglob("*.py"):
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                    
                    # Check if file contains any search patterns
                    for pattern in search_patterns:
                        if pattern in content:
                            relevant_files.append(py_file)
                            break
                            
                except Exception as e:
                    self.logger.debug(f"Could not read file {py_file}: {e}")
        
        return relevant_files
    
    async def _check_checkpoint_coverage(
        self,
        checkpoint: str,
        relevant_files: List[Path],
        search_patterns: List[str]
    ) -> bool:
        """Check if a specific checkpoint is covered."""
        
        # Define checkpoint-specific patterns
        checkpoint_patterns = {
            "input_validation": ["validate", "sanitize", "check", "verify"],
            "output_sanitization": ["sanitize", "escape", "clean", "filter"],
            "authentication": ["auth", "login", "token", "credential"],
            "authorization": ["authorize", "permission", "access", "role"],
            "error_handling": ["except", "error", "try", "catch"],
            "retry_mechanisms": ["retry", "attempt", "backoff"],
            "response_time_monitoring": ["time", "duration", "latency", "performance"],
            "caching_implementation": ["cache", "memoize", "store"],
            "logging_implementation": ["log", "debug", "info", "error"],
            "type_annotations": [":", "->", "typing", "Type"],
            "unit_tests": ["test_", "unittest", "pytest"],
            "async_processing": ["async", "await", "asyncio"],
            "health_checks": ["health", "status", "alive", "ready"]
        }
        
        patterns = checkpoint_patterns.get(checkpoint, [checkpoint.replace("_", "")])
        
        # Check if patterns exist in relevant files
        for file_path in relevant_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                
                for pattern in patterns:
                    if pattern in content:
                        return True
                        
            except Exception as e:
                self.logger.debug(f"Could not check checkpoint in {file_path}: {e}")
        
        return False
    
    async def _generate_quality_recommendations(
        self,
        aspect_name: str,
        missing_checkpoints: List[str]
    ) -> List[str]:
        """Generate recommendations for improving quality coverage."""
        
        recommendations = []
        
        aspect_recommendations = {
            "security": {
                "input_validation": "Implement comprehensive input validation for all user inputs",
                "output_sanitization": "Add output sanitization to prevent XSS and injection attacks",
                "authentication": "Implement robust authentication mechanisms",
                "secret_management": "Use secure secret management for sensitive data"
            },
            "performance": {
                "response_time_monitoring": "Add response time monitoring and alerting",
                "caching_implementation": "Implement caching for frequently accessed data",
                "optimization_techniques": "Apply performance optimization techniques",
                "async_processing": "Use asynchronous processing where appropriate"
            },
            "reliability": {
                "error_handling": "Add comprehensive error handling and recovery",
                "retry_mechanisms": "Implement retry mechanisms for transient failures",
                "health_checks": "Add health checks for system monitoring",
                "monitoring_alerts": "Set up monitoring and alerting systems"
            },
            "maintainability": {
                "code_documentation": "Add comprehensive code documentation",
                "type_annotations": "Add type annotations for better code clarity",
                "unit_tests": "Increase unit test coverage",
                "logging_implementation": "Implement structured logging throughout"
            },
            "scalability": {
                "async_processing": "Implement asynchronous processing for better scalability",
                "resource_pooling": "Use resource pooling for efficient resource management",
                "load_balancing": "Implement load balancing mechanisms",
                "queue_management": "Add queue management for processing tasks"
            }
        }
        
        aspect_recs = aspect_recommendations.get(aspect_name, {})
        
        for checkpoint in missing_checkpoints[:5]:  # Top 5 missing checkpoints
            rec = aspect_recs.get(checkpoint, f"Implement {checkpoint.replace('_', ' ')}")
            recommendations.append(rec)
        
        return recommendations


class FeatureCoverageAnalyzer:
    """Analyzes feature coverage across implementation, testing, and documentation."""
    
    def __init__(self, project_root: Path):
        self.logger = AstolfoLogger(__name__)
        self.project_root = project_root
    
    async def analyze_feature_coverage(self) -> List[FeatureCoverageData]:
        """Analyze coverage for all features."""
        
        features = {
            "discord_webhook_integration": {
                "implementation_files": ["src/discord_notifier.py", "src/handlers/discord_sender.py"],
                "test_files": ["tests/discord_integration/test_webhook_delivery.py"],
                "docs_files": ["CLAUDE.md", "README.md"]
            },
            "event_formatting": {
                "implementation_files": ["src/formatters/"],
                "test_files": ["tests/content_processing/test_event_formatting.py"],
                "docs_files": ["CLAUDE.md"]
            },
            "thread_management": {
                "implementation_files": ["src/thread_storage.py", "src/handlers/thread_manager.py"],
                "test_files": ["tests/discord_integration/test_thread_lifecycle.py"],
                "docs_files": ["CLAUDE.md"]
            },
            "configuration_management": {
                "implementation_files": ["src/core/config*.py"],
                "test_files": ["tests/data_management/test_config_validation.py"],
                "docs_files": ["CLAUDE.md"]
            },
            "quality_assurance": {
                "implementation_files": ["utils/quality_assurance/"],
                "test_files": ["tests/quality_validation/"],
                "docs_files": ["CLAUDE.md"]
            }
        }
        
        coverage_results = []
        
        for feature_name, feature_config in features.items():
            coverage_data = await self._analyze_feature(feature_name, feature_config)
            if coverage_data:
                coverage_results.append(coverage_data)
        
        return coverage_results
    
    async def _analyze_feature(
        self,
        feature_name: str,
        feature_config: Dict[str, List[str]]
    ) -> Optional[FeatureCoverageData]:
        """Analyze coverage for a specific feature."""
        
        try:
            # Analyze implementation coverage
            impl_coverage = await self._analyze_implementation_coverage(
                feature_config["implementation_files"]
            )
            
            # Analyze test coverage
            test_coverage = await self._analyze_test_coverage_for_feature(
                feature_config["implementation_files"],
                feature_config["test_files"]
            )
            
            # Analyze documentation coverage
            docs_coverage = await self._analyze_documentation_coverage(
                feature_name,
                feature_config["docs_files"]
            )
            
            # Calculate quality coverage (simplified)
            quality_coverage = (impl_coverage + test_coverage + docs_coverage) / 3
            
            # Calculate overall coverage
            overall_coverage = statistics.mean([
                impl_coverage, test_coverage, docs_coverage, quality_coverage
            ])
            
            # Determine status
            if overall_coverage >= 90:
                status = "complete"
            elif overall_coverage >= 60:
                status = "partial"
            else:
                status = "missing"
            
            # Identify gaps
            gaps = []
            if impl_coverage < 90:
                gaps.append("Implementation needs improvement")
            if test_coverage < 80:
                gaps.append("Test coverage insufficient")
            if docs_coverage < 70:
                gaps.append("Documentation incomplete")
            
            return FeatureCoverageData(
                feature_name=feature_name,
                implementation_coverage=impl_coverage,
                test_coverage=test_coverage,
                documentation_coverage=docs_coverage,
                quality_coverage=quality_coverage,
                overall_coverage=overall_coverage,
                status=status,
                gaps=gaps
            )
            
        except Exception as e:
            self.logger.warning(f"Could not analyze feature coverage for {feature_name}: {e}")
            return None
    
    async def _analyze_implementation_coverage(self, file_patterns: List[str]) -> float:
        """Analyze implementation coverage for feature files."""
        
        total_score = 0.0
        file_count = 0
        
        for pattern in file_patterns:
            files = await self._find_files_by_pattern(pattern)
            
            for file_path in files:
                file_count += 1
                score = await self._score_implementation_file(file_path)
                total_score += score
        
        return (total_score / file_count) if file_count > 0 else 0.0
    
    async def _score_implementation_file(self, file_path: Path) -> float:
        """Score an implementation file for completeness."""
        
        score = 0.0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for various implementation aspects
            checks = [
                ("docstrings", '"""' in content or "'''" in content),
                ("type_hints", "->" in content or ": " in content),
                ("error_handling", "except" in content or "raise" in content),
                ("logging", "log" in content.lower()),
                ("async_support", "async" in content or "await" in content),
                ("imports", "import" in content),
                ("classes_or_functions", "def " in content or "class " in content)
            ]
            
            for check_name, check_result in checks:
                if check_result:
                    score += 100 / len(checks)
            
        except Exception as e:
            self.logger.debug(f"Could not score implementation file {file_path}: {e}")
        
        return score
    
    async def _analyze_test_coverage_for_feature(
        self,
        impl_patterns: List[str],
        test_patterns: List[str]
    ) -> float:
        """Analyze test coverage for a feature."""
        
        impl_files = []
        for pattern in impl_patterns:
            impl_files.extend(await self._find_files_by_pattern(pattern))
        
        test_files = []
        for pattern in test_patterns:
            test_files.extend(await self._find_files_by_pattern(pattern))
        
        if not impl_files:
            return 0.0
        
        if not test_files:
            return 0.0
        
        # Simple heuristic: ratio of test files to implementation files
        ratio_score = min(100, (len(test_files) / len(impl_files)) * 100)
        
        # Bonus for comprehensive test files
        test_comprehensiveness = 0.0
        for test_file in test_files:
            test_comprehensiveness += await self._score_test_file(test_file)
        
        if test_files:
            test_comprehensiveness /= len(test_files)
        
        return (ratio_score + test_comprehensiveness) / 2
    
    async def _score_test_file(self, file_path: Path) -> float:
        """Score a test file for comprehensiveness."""
        
        score = 0.0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count test functions
            test_function_count = content.count("def test_")
            
            # Check for various test aspects
            checks = [
                ("setup_teardown", "setUp" in content or "tearDown" in content or "setup" in content),
                ("assertions", "assert" in content),
                ("mocking", "mock" in content.lower() or "patch" in content),
                ("async_tests", "async def test_" in content),
                ("error_testing", "except" in content or "raise" in content),
                ("multiple_tests", test_function_count >= 3)
            ]
            
            for check_name, check_result in checks:
                if check_result:
                    score += 100 / len(checks)
            
            # Bonus for more test functions
            if test_function_count >= 10:
                score = min(100, score + 20)
            elif test_function_count >= 5:
                score = min(100, score + 10)
            
        except Exception as e:
            self.logger.debug(f"Could not score test file {file_path}: {e}")
        
        return score
    
    async def _analyze_documentation_coverage(
        self,
        feature_name: str,
        docs_patterns: List[str]
    ) -> float:
        """Analyze documentation coverage for a feature."""
        
        total_score = 0.0
        docs_found = 0
        
        for pattern in docs_patterns:
            files = await self._find_files_by_pattern(pattern)
            
            for file_path in files:
                docs_found += 1
                score = await self._score_documentation_file(file_path, feature_name)
                total_score += score
        
        return (total_score / docs_found) if docs_found > 0 else 0.0
    
    async def _score_documentation_file(self, file_path: Path, feature_name: str) -> float:
        """Score a documentation file for feature coverage."""
        
        score = 0.0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Check if feature is mentioned
            feature_keywords = feature_name.lower().replace("_", " ").split()
            
            mentions = 0
            for keyword in feature_keywords:
                if keyword in content:
                    mentions += 1
            
            if mentions > 0:
                score += 50  # Base score for being mentioned
                
                # Check for documentation quality indicators
                checks = [
                    ("examples", "example" in content or "```" in content),
                    ("usage", "usage" in content or "how to" in content),
                    ("configuration", "config" in content or "setting" in content),
                    ("troubleshooting", "troubleshoot" in content or "error" in content)
                ]
                
                for check_name, check_result in checks:
                    if check_result:
                        score += 50 / len(checks)
        
        except Exception as e:
            self.logger.debug(f"Could not score documentation file {file_path}: {e}")
        
        return score
    
    async def _find_files_by_pattern(self, pattern: str) -> List[Path]:
        """Find files matching a pattern."""
        files = []
        
        try:
            if pattern.endswith("/"):
                # Directory pattern
                dir_path = self.project_root / pattern.rstrip("/")
                if dir_path.is_dir():
                    files.extend(dir_path.rglob("*.py"))
                    files.extend(dir_path.rglob("*.md"))
            else:
                # File pattern
                file_path = self.project_root / pattern
                if file_path.is_file():
                    files.append(file_path)
                elif "*" in pattern:
                    # Glob pattern
                    parent = self.project_root
                    for part in Path(pattern).parts[:-1]:
                        parent = parent / part
                    if parent.exists():
                        files.extend(parent.glob(Path(pattern).name))
        
        except Exception as e:
            self.logger.debug(f"Could not find files for pattern {pattern}: {e}")
        
        return files


class CoverageAnalyzer:
    """Main coverage analyzer that coordinates all coverage analysis."""
    
    def __init__(self, project_root: Path = None):
        self.logger = AstolfoLogger(__name__)
        self.project_root = project_root or Path.cwd()
        
        # Initialize sub-analyzers
        self.code_analyzer = CodeCoverageAnalyzer(self.project_root)
        self.test_analyzer = TestCoverageAnalyzer(self.project_root)
        self.quality_analyzer = QualityCoverageAnalyzer(self.project_root)
        self.feature_analyzer = FeatureCoverageAnalyzer(self.project_root)
        
        # Coverage history
        self.coverage_history: List[CoverageReport] = []
        self.history_file = self.project_root / "coverage_history.json"
        
        self._load_coverage_history()
    
    def _load_coverage_history(self) -> None:
        """Load coverage history from file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                
                # Note: This is a simplified version
                # In production, you'd properly deserialize the dataclasses
                self.coverage_history = data.get("reports", [])
                self.logger.info(f"Loaded {len(self.coverage_history)} historical coverage reports")
        
        except Exception as e:
            self.logger.warning(f"Could not load coverage history: {e}")
    
    def _save_coverage_history(self) -> None:
        """Save coverage history to file."""
        try:
            # Simplified serialization
            data = {
                "reports": [
                    {
                        "report_id": report.report_id,
                        "generated_at": report.generated_at.isoformat(),
                        "overall_coverage": report.overall_coverage
                    }
                    for report in self.coverage_history
                ]
            }
            
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save coverage history: {e}")
    
    async def generate_comprehensive_coverage_report(
        self,
        include_code_coverage: bool = True,
        include_test_coverage: bool = True,
        include_quality_coverage: bool = True,
        include_feature_coverage: bool = True,
        test_command: str = None
    ) -> CoverageReport:
        """Generate comprehensive coverage report."""
        
        report_id = f"COV_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        generated_at = datetime.now(timezone.utc)
        
        # Initialize results
        code_coverage = []
        test_coverage = []
        quality_coverage = []
        feature_coverage = []
        
        try:
            # Analyze code coverage
            if include_code_coverage:
                self.logger.info("Analyzing code coverage...")
                code_coverage = await self.code_analyzer.analyze_code_coverage(
                    test_command=test_command
                )
            
            # Analyze test coverage
            if include_test_coverage:
                self.logger.info("Analyzing test coverage...")
                test_coverage = await self.test_analyzer.analyze_test_coverage()
            
            # Analyze quality coverage
            if include_quality_coverage:
                self.logger.info("Analyzing quality coverage...")
                quality_coverage = await self.quality_analyzer.analyze_quality_coverage()
            
            # Analyze feature coverage
            if include_feature_coverage:
                self.logger.info("Analyzing feature coverage...")
                feature_coverage = await self.feature_analyzer.analyze_feature_coverage()
            
            # Calculate overall coverage
            overall_coverage = await self._calculate_overall_coverage(
                code_coverage, test_coverage, quality_coverage, feature_coverage
            )
            
            # Generate coverage trends
            coverage_trends = await self._generate_coverage_trends()
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(
                code_coverage, test_coverage, quality_coverage, feature_coverage
            )
            
            # Identify critical gaps
            critical_gaps = await self._identify_critical_gaps(
                code_coverage, test_coverage, quality_coverage, feature_coverage
            )
            
            # Create report
            report = CoverageReport(
                report_id=report_id,
                generated_at=generated_at,
                overall_coverage=overall_coverage,
                code_coverage=code_coverage,
                test_coverage=test_coverage,
                quality_coverage=quality_coverage,
                feature_coverage=feature_coverage,
                coverage_trends=coverage_trends,
                recommendations=recommendations,
                critical_gaps=critical_gaps
            )
            
            # Add to history
            self.coverage_history.append(report)
            
            # Keep only last 20 reports
            if len(self.coverage_history) > 20:
                self.coverage_history = self.coverage_history[-20:]
            
            # Save history
            self._save_coverage_history()
            
            self.logger.info(f"Generated comprehensive coverage report: {report_id}")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate coverage report: {e}")
            raise
    
    async def _calculate_overall_coverage(
        self,
        code_coverage: List[CodeCoverageData],
        test_coverage: List[TestCoverageData],
        quality_coverage: List[QualityCoverageData],
        feature_coverage: List[FeatureCoverageData]
    ) -> float:
        """Calculate overall coverage score."""
        
        scores = []
        
        # Code coverage (weight: 25%)
        if code_coverage:
            avg_code_coverage = statistics.mean(c.coverage_percentage for c in code_coverage)
            scores.append(avg_code_coverage * 0.25)
        
        # Test coverage (weight: 30%)
        if test_coverage:
            avg_test_coverage = statistics.mean(c.coverage_percentage for c in test_coverage)
            scores.append(avg_test_coverage * 0.30)
        
        # Quality coverage (weight: 25%)
        if quality_coverage:
            avg_quality_coverage = statistics.mean(c.coverage_percentage for c in quality_coverage)
            scores.append(avg_quality_coverage * 0.25)
        
        # Feature coverage (weight: 20%)
        if feature_coverage:
            avg_feature_coverage = statistics.mean(c.overall_coverage for c in feature_coverage)
            scores.append(avg_feature_coverage * 0.20)
        
        return sum(scores) if scores else 0.0
    
    async def _generate_coverage_trends(self) -> Dict[str, List[float]]:
        """Generate coverage trends from history."""
        
        trends = {
            "overall": [],
            "code": [],
            "test": [],
            "quality": [],
            "feature": []
        }
        
        # This would be implemented with proper historical data
        # For now, return empty trends
        return trends
    
    async def _generate_recommendations(
        self,
        code_coverage: List[CodeCoverageData],
        test_coverage: List[TestCoverageData],
        quality_coverage: List[QualityCoverageData],
        feature_coverage: List[FeatureCoverageData]
    ) -> List[str]:
        """Generate coverage improvement recommendations."""
        
        recommendations = []
        
        # Code coverage recommendations
        if code_coverage:
            avg_code_coverage = statistics.mean(c.coverage_percentage for c in code_coverage)
            if avg_code_coverage < 80:
                recommendations.append(f"Increase code coverage from {avg_code_coverage:.1f}% to 80%+")
                
                # Find files with lowest coverage
                low_coverage_files = [c for c in code_coverage if c.coverage_percentage < 60]
                if low_coverage_files:
                    file_names = [Path(c.file_path).name for c in low_coverage_files[:3]]
                    recommendations.append(f"Focus on improving coverage in: {', '.join(file_names)}")
        
        # Test coverage recommendations
        if test_coverage:
            components_with_low_coverage = [c for c in test_coverage if c.coverage_percentage < 70]
            if components_with_low_coverage:
                component_names = [c.component_name for c in components_with_low_coverage]
                recommendations.append(f"Add more tests for: {', '.join(component_names)}")
        
        # Quality coverage recommendations
        if quality_coverage:
            for qc in quality_coverage:
                if qc.coverage_percentage < 70:
                    recommendations.extend(qc.recommendations[:2])  # Top 2 recommendations
        
        # Feature coverage recommendations
        if feature_coverage:
            incomplete_features = [f for f in feature_coverage if f.status != "complete"]
            if incomplete_features:
                feature_names = [f.feature_name for f in incomplete_features[:3]]
                recommendations.append(f"Complete implementation for: {', '.join(feature_names)}")
        
        return recommendations[:10]  # Top 10 recommendations
    
    async def _identify_critical_gaps(
        self,
        code_coverage: List[CodeCoverageData],
        test_coverage: List[TestCoverageData],
        quality_coverage: List[QualityCoverageData],
        feature_coverage: List[FeatureCoverageData]
    ) -> List[str]:
        """Identify critical coverage gaps."""
        
        critical_gaps = []
        
        # Critical code coverage gaps
        critical_code_files = [c for c in code_coverage if c.coverage_percentage < 50]
        if critical_code_files:
            critical_gaps.append(f"CRITICAL: {len(critical_code_files)} files with <50% code coverage")
        
        # Critical test coverage gaps
        untested_components = [c for c in test_coverage if c.coverage_percentage < 30]
        if untested_components:
            component_names = [c.component_name for c in untested_components]
            critical_gaps.append(f"CRITICAL: Insufficient tests for {', '.join(component_names)}")
        
        # Critical quality gaps
        security_gaps = [q for q in quality_coverage if q.quality_aspect == "security" and q.coverage_percentage < 60]
        if security_gaps:
            critical_gaps.append("CRITICAL: Security coverage below acceptable threshold")
        
        # Critical feature gaps
        broken_features = [f for f in feature_coverage if f.status == "missing" and f.overall_coverage < 30]
        if broken_features:
            feature_names = [f.feature_name for f in broken_features]
            critical_gaps.append(f"CRITICAL: Broken or missing features: {', '.join(feature_names)}")
        
        return critical_gaps
    
    async def export_coverage_report(
        self,
        report: CoverageReport,
        format_type: str = "json",
        output_file: Path = None
    ) -> Path:
        """Export coverage report to file."""
        
        if output_file is None:
            output_dir = self.project_root / "coverage_reports"
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"{report.report_id}.{format_type}"
        
        if format_type == "json":
            await self._export_json_report(report, output_file)
        elif format_type == "html":
            await self._export_html_report(report, output_file)
        elif format_type == "xml":
            await self._export_xml_report(report, output_file)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        self.logger.info(f"Exported coverage report to: {output_file}")
        return output_file
    
    async def _export_json_report(self, report: CoverageReport, output_file: Path) -> None:
        """Export report as JSON."""
        # This would serialize the dataclasses properly
        # Simplified version for demonstration
        data = {
            "report_id": report.report_id,
            "generated_at": report.generated_at.isoformat(),
            "overall_coverage": report.overall_coverage,
            "recommendations": report.recommendations,
            "critical_gaps": report.critical_gaps
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def _export_html_report(self, report: CoverageReport, output_file: Path) -> None:
        """Export report as HTML."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Coverage Report - {report.report_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; }}
                .section {{ margin: 20px 0; }}
                .critical {{ color: #dc3545; font-weight: bold; }}
                .good {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Coverage Analysis Report</h1>
                <p><strong>Report ID:</strong> {report.report_id}</p>
                <p><strong>Generated:</strong> {report.generated_at.isoformat()}</p>
                <p><strong>Overall Coverage:</strong> {report.overall_coverage:.1f}%</p>
            </div>
            
            <div class="section">
                <h2>Critical Gaps</h2>
                {'<ul>' + ''.join(f'<li class="critical">{gap}</li>' for gap in report.critical_gaps) + '</ul>' if report.critical_gaps else '<p>No critical gaps identified.</p>'}
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
                <ul>
                    {''.join(f'<li>{rec}</li>' for rec in report.recommendations)}
                </ul>
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    async def _export_xml_report(self, report: CoverageReport, output_file: Path) -> None:
        """Export report as XML."""
        root = ET.Element("CoverageReport")
        ET.SubElement(root, "ReportID").text = report.report_id
        ET.SubElement(root, "GeneratedAt").text = report.generated_at.isoformat()
        ET.SubElement(root, "OverallCoverage").text = str(report.overall_coverage)
        
        # Add recommendations
        recommendations_elem = ET.SubElement(root, "Recommendations")
        for rec in report.recommendations:
            ET.SubElement(recommendations_elem, "Recommendation").text = rec
        
        # Add critical gaps
        gaps_elem = ET.SubElement(root, "CriticalGaps")
        for gap in report.critical_gaps:
            ET.SubElement(gaps_elem, "Gap").text = gap
        
        tree = ET.ElementTree(root)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)


def run_coverage_analyzer_example():
    """Example usage of CoverageAnalyzer."""
    import asyncio
    
    async def example():
        # Initialize analyzer
        analyzer = CoverageAnalyzer()
        
        # Generate comprehensive coverage report
        report = await analyzer.generate_comprehensive_coverage_report(
            test_command="python -m unittest discover -s tests"
        )
        
        print(f"Coverage Report: {report.report_id}")
        print(f"Overall Coverage: {report.overall_coverage:.1f}%")
        print(f"Critical Gaps: {len(report.critical_gaps)}")
        print(f"Recommendations: {len(report.recommendations)}")
        
        # Export reports
        json_file = await analyzer.export_coverage_report(report, "json")
        html_file = await analyzer.export_coverage_report(report, "html")
        
        print(f"Reports exported:")
        print(f"  JSON: {json_file}")
        print(f"  HTML: {html_file}")
    
    asyncio.run(example())


if __name__ == "__main__":
    run_coverage_analyzer_example()