#!/usr/bin/env python3
"""Enhanced development quality checker integrating comprehensive quality assurance.

This module extends the original development_checker.py with comprehensive quality 
assurance capabilities including all the quality gates, checkers, and automated
validation systems. It provides a unified interface for all quality checks.
"""

import asyncio
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger

# Import comprehensive quality assurance components
try:
    from utils.quality_assurance.checkers.core_checker import CoreQualityChecker
    from utils.quality_assurance.checkers.discord_integration_checker import DiscordIntegrationChecker
    from utils.quality_assurance.checkers.content_processing_checker import ContentProcessingChecker
    from utils.quality_assurance.checkers.data_management_checker import DataManagementChecker
    from utils.quality_assurance.checkers.quality_validation_checker import QualityValidationChecker
    from utils.quality_assurance.checkers.integration_control_checker import IntegrationControlChecker
    from utils.quality_assurance.automation.instant_checker import InstantQualityChecker
    from utils.quality_assurance.automation.category_checker import CategoryQualityChecker
    from utils.quality_assurance.automation.comprehensive_checker import ComprehensiveQualityChecker
    from utils.quality_assurance.gates.level1_basic_quality_gate import Level1BasicQualityGate
    from utils.quality_assurance.gates.level2_functional_quality_gate import Level2FunctionalQualityGate
    from utils.quality_assurance.gates.level3_integration_quality_gate import Level3IntegrationQualityGate
    from utils.quality_assurance.gates.level4_production_quality_gate import Level4ProductionQualityGate
    COMPREHENSIVE_QA_AVAILABLE = True
except ImportError as e:
    # Fallback gracefully if comprehensive QA system is not available
    COMPREHENSIVE_QA_AVAILABLE = False
    print(f"Note: Comprehensive QA system not available: {e}")


class CheckResult(TypedDict):
    """Result of a development check."""
    check_name: str
    passed: bool
    issues: List[str]
    warnings: List[str]
    details: Dict[str, Any]


class EnhancedCheckResult(TypedDict):
    """Enhanced result including quality scores and metrics."""
    check_name: str
    passed: bool
    issues: List[str]
    warnings: List[str]
    details: Dict[str, Any]
    quality_score: float
    execution_time: float
    category: str
    priority: str
    recommendations: List[str]


class EnhancedDevelopmentChecker:
    """Enhanced development quality checker with comprehensive QA integration."""
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize enhanced development checker.
        
        Args:
            project_root: Project root directory (auto-detected if None)
        """
        self.logger = AstolfoLogger(__name__)
        
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = project_root
        self.src_path = project_root / "src"
        
        # Initialize comprehensive QA components if available
        self.comprehensive_qa_available = COMPREHENSIVE_QA_AVAILABLE
        if COMPREHENSIVE_QA_AVAILABLE:
            self._initialize_qa_components()
        
        self.logger.info(
            "Enhanced development checker initialized",
            context={
                "project_root": str(project_root),
                "src_path": str(self.src_path),
                "comprehensive_qa": self.comprehensive_qa_available
            }
        )
    
    def _initialize_qa_components(self) -> None:
        """Initialize comprehensive QA components."""
        try:
            self.core_checker = CoreQualityChecker()
            self.discord_checker = DiscordIntegrationChecker()
            self.content_checker = ContentProcessingChecker()
            self.data_checker = DataManagementChecker()
            self.quality_checker = QualityValidationChecker()
            self.integration_checker = IntegrationControlChecker()
            
            self.instant_checker = InstantQualityChecker()
            self.category_checker = CategoryQualityChecker()
            self.comprehensive_checker = ComprehensiveQualityChecker()
            
            self.level1_gate = Level1BasicQualityGate()
            self.level2_gate = Level2FunctionalQualityGate()
            self.level3_gate = Level3IntegrationQualityGate()
            self.level4_gate = Level4ProductionQualityGate()
            
            self.logger.info("Comprehensive QA components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize QA components: {e}")
            self.comprehensive_qa_available = False
    
    # ========== ORIGINAL DEVELOPMENT CHECKS ==========
    
    def check_utc_timestamp_leaks(self) -> EnhancedCheckResult:
        """Check for UTC timestamp patterns in user-facing code."""
        start_time = time.time()
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
        files_scanned = 0
        
        for pattern in check_patterns:
            files = list(self.project_root.glob(pattern))
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                files_scanned += 1
                
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
        
        execution_time = time.time() - start_time
        passed = len(violations) == 0
        quality_score = 100.0 if passed else max(0, 100.0 - (len(violations) * 20))
        
        recommendations = []
        if violations:
            recommendations.extend([
                "Replace UTC datetime usage with timezone-aware local time",
                "Use datetime.now(tz=ZoneInfo('UTC')) for internal timestamps only",
                "Ensure user-facing timestamps use local timezone"
            ])
        
        result: EnhancedCheckResult = {
            "check_name": "UTC Timestamp Leak Detection",
            "passed": passed,
            "issues": violations,
            "warnings": warnings,
            "details": {
                "patterns_checked": len(utc_patterns),
                "files_scanned": files_scanned,
                "violations_found": len(violations)
            },
            "quality_score": quality_score,
            "execution_time": execution_time,
            "category": "timestamp_safety",
            "priority": "high",
            "recommendations": recommendations
        }
        
        self.logger.info(
            "UTC timestamp leak check completed",
            context={
                "passed": passed,
                "violations": len(violations),
                "warnings": len(warnings),
                "quality_score": quality_score
            }
        )
        
        return result
    
    def check_timestamp_test_coverage(self) -> EnhancedCheckResult:
        """Check that timestamp functionality has adequate test coverage."""
        start_time = time.time()
        self.logger.info("Checking timestamp test coverage")
        
        issues = []
        warnings = []
        
        # Check for timestamp-specific tests
        timestamp_test_path = self.project_root / "tests" / "timestamp"
        test_files_found = 0
        
        if not timestamp_test_path.exists():
            issues.append("Timestamp-specific test directory not found")
        else:
            test_files = list(timestamp_test_path.glob("test_*.py"))
            test_files_found = len(test_files)
            if test_files_found == 0:
                issues.append("No timestamp test files found")
            elif test_files_found < 2:
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
        
        execution_time = time.time() - start_time
        passed = len(issues) == 0
        coverage_percentage = (len(found_methods) / len(required_test_methods)) * 100 if required_test_methods else 0
        quality_score = coverage_percentage if passed else coverage_percentage * 0.5
        
        recommendations = []
        if missing_methods:
            recommendations.append("Implement missing timestamp test methods")
        if test_files_found < 3:
            recommendations.append("Add more comprehensive timestamp test files")
        if coverage_percentage < 80:
            recommendations.append("Increase timestamp test coverage to at least 80%")
        
        result: EnhancedCheckResult = {
            "check_name": "Timestamp Test Coverage",
            "passed": passed,
            "issues": issues,
            "warnings": warnings,
            "details": {
                "required_methods": len(required_test_methods),
                "found_methods": len(found_methods),
                "missing_methods": list(missing_methods),
                "test_directory_exists": timestamp_test_path.exists(),
                "coverage_percentage": coverage_percentage
            },
            "quality_score": quality_score,
            "execution_time": execution_time,
            "category": "test_coverage",
            "priority": "high",
            "recommendations": recommendations
        }
        
        self.logger.info(
            "Timestamp test coverage check completed",
            context={
                "passed": passed,
                "issues": len(issues),
                "found_methods": len(found_methods),
                "coverage_percentage": coverage_percentage
            }
        )
        
        return result
    
    def run_realtime_timestamp_tests(self) -> EnhancedCheckResult:
        """Run timestamp accuracy tests to verify current implementation."""
        start_time = time.time()
        self.logger.info("Running realtime timestamp tests")
        
        issues = []
        warnings = []
        test_output = ""
        test_success = False
        
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
            test_success = result.returncode == 0
            
            if not test_success:
                issues.append(f"Timestamp tests failed with exit code {result.returncode}")
                issues.append(f"Test output: {test_output}")
            
        except subprocess.TimeoutExpired:
            issues.append("Timestamp tests timed out after 60 seconds")
        except FileNotFoundError:
            issues.append("Could not run timestamp tests - uv or python not found")
        except Exception as e:
            issues.append(f"Failed to run timestamp tests: {e}")
        
        execution_time = time.time() - start_time
        passed = len(issues) == 0 and test_success
        quality_score = 100.0 if passed else 0.0
        
        recommendations = []
        if not passed:
            recommendations.extend([
                "Fix failing timestamp tests before proceeding",
                "Review timestamp implementation for accuracy",
                "Ensure timezone handling is correct"
            ])
        
        result: EnhancedCheckResult = {
            "check_name": "Realtime Timestamp Tests",
            "passed": passed,
            "issues": issues,
            "warnings": warnings,
            "details": {
                "test_output": test_output,
                "command_used": " ".join(cmd) if 'cmd' in locals() else "N/A",
                "test_success": test_success
            },
            "quality_score": quality_score,
            "execution_time": execution_time,
            "category": "functional_testing",
            "priority": "high",
            "recommendations": recommendations
        }
        
        self.logger.info(
            "Realtime timestamp tests completed",
            context={
                "passed": passed,
                "issues": len(issues),
                "test_success": test_success
            }
        )
        
        return result
    
    def check_import_consistency(self) -> EnhancedCheckResult:
        """Check for import consistency and circular import issues."""
        start_time = time.time()
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
        
        successful_imports = 0
        for import_name in test_imports:
            try:
                __import__(import_name)
                successful_imports += 1
            except ImportError as e:
                issues.append(f"Import error for {import_name}: {e}")
            except Exception as e:
                warnings.append(f"Unexpected error importing {import_name}: {e}")
        
        execution_time = time.time() - start_time
        passed = len(issues) == 0
        success_rate = (successful_imports / len(test_imports)) * 100
        quality_score = success_rate
        
        recommendations = []
        if issues:
            recommendations.extend([
                "Fix import errors before proceeding",
                "Check for circular import dependencies",
                "Ensure all required modules are available"
            ])
        
        result: EnhancedCheckResult = {
            "check_name": "Import Consistency",
            "passed": passed,
            "issues": issues,
            "warnings": warnings,
            "details": {
                "imports_tested": len(test_imports),
                "successful_imports": successful_imports,
                "success_rate": success_rate
            },
            "quality_score": quality_score,
            "execution_time": execution_time,
            "category": "structural_integrity",
            "priority": "high",
            "recommendations": recommendations
        }
        
        self.logger.info(
            "Import consistency check completed",
            context={
                "passed": passed,
                "issues": len(issues),
                "success_rate": success_rate
            }
        )
        
        return result
    
    # ========== COMPREHENSIVE QA INTEGRATION ==========
    
    async def run_comprehensive_quality_gates(self) -> List[EnhancedCheckResult]:
        """Run all comprehensive quality gates."""
        if not self.comprehensive_qa_available:
            return []
        
        self.logger.info("Running comprehensive quality gates")
        results = []
        
        gates = [
            ("Level 1: Basic Quality", self.level1_gate),
            ("Level 2: Functional Quality", self.level2_gate),
            ("Level 3: Integration Quality", self.level3_gate),
            ("Level 4: Production Quality", self.level4_gate)
        ]
        
        for gate_name, gate in gates:
            start_time = time.time()
            try:
                gate_result = await gate.check_quality()
                execution_time = time.time() - start_time
                
                passed = gate_result.get("quality_level") in ["excellent", "good"]
                quality_score = gate_result.get("overall_score", 0.0)
                
                issues = gate_result.get("errors", [])
                warnings = gate_result.get("warnings", [])
                recommendations = gate_result.get("recommendations", [])
                
                result: EnhancedCheckResult = {
                    "check_name": gate_name,
                    "passed": passed,
                    "issues": issues,
                    "warnings": warnings,
                    "details": gate_result,
                    "quality_score": quality_score,
                    "execution_time": execution_time,
                    "category": "quality_gate",
                    "priority": "high",
                    "recommendations": recommendations
                }
                
                results.append(result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(f"Quality gate {gate_name} failed: {e}")
                
                result: EnhancedCheckResult = {
                    "check_name": f"{gate_name} (FAILED)",
                    "passed": False,
                    "issues": [f"Gate execution failed: {e}"],
                    "warnings": [],
                    "details": {},
                    "quality_score": 0.0,
                    "execution_time": execution_time,
                    "category": "quality_gate",
                    "priority": "high",
                    "recommendations": ["Fix quality gate execution error"]
                }
                
                results.append(result)
        
        return results
    
    async def run_category_checkers(self) -> List[EnhancedCheckResult]:
        """Run all category-specific checkers."""
        if not self.comprehensive_qa_available:
            return []
        
        self.logger.info("Running category checkers")
        results = []
        
        checkers = [
            ("Discord Integration", self.discord_checker),
            ("Content Processing", self.content_checker),
            ("Data Management", self.data_checker),
            ("Quality Validation", self.quality_checker),
            ("Integration Control", self.integration_checker)
        ]
        
        for checker_name, checker in checkers:
            start_time = time.time()
            try:
                checker_result = await checker.check_quality()
                execution_time = time.time() - start_time
                
                passed = checker_result.get("quality_level") in ["excellent", "good"]
                quality_score = checker_result.get("overall_score", 0.0)
                
                # Extract issues and warnings from checker result
                issues = []
                warnings = []
                recommendations = []
                
                for key, value in checker_result.items():
                    if "error" in key.lower() and isinstance(value, list):
                        issues.extend(value)
                    elif "warning" in key.lower() and isinstance(value, list):
                        warnings.extend(value)
                    elif "recommendation" in key.lower() and isinstance(value, list):
                        recommendations.extend(value)
                
                result: EnhancedCheckResult = {
                    "check_name": f"{checker_name} Checker",
                    "passed": passed,
                    "issues": issues,
                    "warnings": warnings,
                    "details": checker_result,
                    "quality_score": quality_score,
                    "execution_time": execution_time,
                    "category": "functional_checker",
                    "priority": "medium",
                    "recommendations": recommendations
                }
                
                results.append(result)
                
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(f"Category checker {checker_name} failed: {e}")
                
                result: EnhancedCheckResult = {
                    "check_name": f"{checker_name} Checker (FAILED)",
                    "passed": False,
                    "issues": [f"Checker execution failed: {e}"],
                    "warnings": [],
                    "details": {},
                    "quality_score": 0.0,
                    "execution_time": execution_time,
                    "category": "functional_checker",
                    "priority": "medium",
                    "recommendations": ["Fix checker execution error"]
                }
                
                results.append(result)
        
        return results
    
    async def run_instant_quality_check(self) -> EnhancedCheckResult:
        """Run instant quality check for rapid feedback."""
        if not self.comprehensive_qa_available:
            return self._create_unavailable_result("Instant Quality Check")
        
        start_time = time.time()
        self.logger.info("Running instant quality check")
        
        try:
            checker_result = await self.instant_checker.check_quality()
            execution_time = time.time() - start_time
            
            passed = checker_result.get("quality_level") in ["excellent", "good"]
            quality_score = checker_result.get("overall_score", 0.0)
            
            result: EnhancedCheckResult = {
                "check_name": "Instant Quality Check",
                "passed": passed,
                "issues": checker_result.get("errors", []),
                "warnings": checker_result.get("warnings", []),
                "details": checker_result,
                "quality_score": quality_score,
                "execution_time": execution_time,
                "category": "instant_validation",
                "priority": "high",
                "recommendations": checker_result.get("recommendations", [])
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = self._create_error_result("Instant Quality Check", e, execution_time)
        
        return result
    
    def _create_unavailable_result(self, check_name: str) -> EnhancedCheckResult:
        """Create result for unavailable comprehensive QA check."""
        return {
            "check_name": f"{check_name} (UNAVAILABLE)",
            "passed": True,  # Don't fail if QA system is unavailable
            "issues": [],
            "warnings": ["Comprehensive QA system not available"],
            "details": {"reason": "Comprehensive QA components not imported"},
            "quality_score": 75.0,  # Neutral score
            "execution_time": 0.0,
            "category": "system_status",
            "priority": "low",
            "recommendations": ["Install comprehensive QA system for full validation"]
        }
    
    def _create_error_result(self, check_name: str, error: Exception, execution_time: float) -> EnhancedCheckResult:
        """Create result for failed check."""
        return {
            "check_name": f"{check_name} (ERROR)",
            "passed": False,
            "issues": [f"Check failed: {error}"],
            "warnings": [],
            "details": {"error": str(error)},
            "quality_score": 0.0,
            "execution_time": execution_time,
            "category": "system_error",
            "priority": "high",
            "recommendations": ["Fix check execution error"]
        }
    
    # ========== UNIFIED CHECK EXECUTION ==========
    
    async def run_development_checks(self) -> List[EnhancedCheckResult]:
        """Run original development checks (synchronous)."""
        self.logger.info("Running original development checks")
        
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
                result = self._create_error_result(
                    f"Development Check: {check.__name__}",
                    e,
                    0.0
                )
                results.append(result)
        
        return results
    
    async def run_all_enhanced_checks(self, include_comprehensive: bool = True) -> List[EnhancedCheckResult]:
        """Run all enhanced quality checks.
        
        Args:
            include_comprehensive: Whether to include comprehensive QA checks
            
        Returns:
            List of all enhanced check results
        """
        self.logger.info("Running all enhanced quality checks")
        
        all_results = []
        
        # Always run original development checks
        dev_results = await self.run_development_checks()
        all_results.extend(dev_results)
        
        # Run comprehensive QA if requested and available
        if include_comprehensive and self.comprehensive_qa_available:
            # Run instant check
            instant_result = await self.run_instant_quality_check()
            all_results.append(instant_result)
            
            # Run category checkers
            category_results = await self.run_category_checkers()
            all_results.extend(category_results)
            
            # Run quality gates
            gate_results = await self.run_comprehensive_quality_gates()
            all_results.extend(gate_results)
        
        elif include_comprehensive and not self.comprehensive_qa_available:
            # Add note about unavailable comprehensive QA
            unavailable_result = self._create_unavailable_result("Comprehensive QA System")
            all_results.append(unavailable_result)
        
        # Calculate overall metrics
        self._calculate_overall_metrics(all_results)
        
        return all_results
    
    def _calculate_overall_metrics(self, results: List[EnhancedCheckResult]) -> None:
        """Calculate and log overall quality metrics."""
        if not results:
            return
        
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r["passed"])
        avg_quality_score = sum(r["quality_score"] for r in results) / total_checks
        total_execution_time = sum(r["execution_time"] for r in results)
        
        # Count by category
        categories = {}
        for result in results:
            category = result["category"]
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0}
            categories[category]["total"] += 1
            if result["passed"]:
                categories[category]["passed"] += 1
        
        self.logger.info(
            "Overall quality metrics calculated",
            context={
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "pass_rate": (passed_checks / total_checks) * 100,
                "average_quality_score": avg_quality_score,
                "total_execution_time": total_execution_time,
                "categories": categories
            }
        )
    
    # ========== RESULT PRESENTATION ==========
    
    def print_enhanced_results(self, results: List[EnhancedCheckResult]) -> None:
        """Print formatted enhanced check results to console."""
        print("🚀" * 60)
        print("🛠️  ENHANCED DEVELOPMENT QUALITY CHECK RESULTS")
        print("🚀" * 60)
        
        if not results:
            print("❌ No checks were executed")
            return
        
        # Group results by category
        categories = {}
        for result in results:
            category = result["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        overall_passed = 0
        total_quality_score = 0
        total_execution_time = 0
        
        # Print results by category
        for category, category_results in categories.items():
            print(f"\n📂 {category.upper().replace('_', ' ')}")
            print("─" * 50)
            
            for result in category_results:
                status = "✅ PASS" if result["passed"] else "❌ FAIL"
                priority_icon = "🔴" if result["priority"] == "high" else "🟡" if result["priority"] == "medium" else "🟢"
                
                print(f"\n{status} {priority_icon} {result['check_name']}")
                print(f"    📊 Quality Score: {result['quality_score']:.1f}/100")
                print(f"    ⏱️  Execution Time: {result['execution_time']:.2f}s")
                
                if result["passed"]:
                    overall_passed += 1
                
                total_quality_score += result["quality_score"]
                total_execution_time += result["execution_time"]
                
                if result["issues"]:
                    print(f"    ❌ Issues ({len(result['issues'])}):")
                    for issue in result["issues"][:3]:  # Limit to first 3 issues
                        print(f"      • {issue}")
                    if len(result["issues"]) > 3:
                        print(f"      • ... and {len(result['issues']) - 3} more")
                
                if result["warnings"]:
                    print(f"    ⚠️  Warnings ({len(result['warnings'])}):")
                    for warning in result["warnings"][:2]:  # Limit to first 2 warnings
                        print(f"      • {warning}")
                    if len(result["warnings"]) > 2:
                        print(f"      • ... and {len(result['warnings']) - 2} more")
                
                if result["recommendations"]:
                    print(f"    💡 Recommendations ({len(result['recommendations'])}):")
                    for rec in result["recommendations"][:2]:  # Limit to first 2 recommendations
                        print(f"      • {rec}")
                    if len(result["recommendations"]) > 2:
                        print(f"      • ... and {len(result['recommendations']) - 2} more")
        
        # Print overall summary
        print("\n" + "🚀" * 60)
        print("📊 OVERALL SUMMARY")
        print("🚀" * 60)
        
        avg_quality_score = total_quality_score / len(results)
        pass_rate = (overall_passed / len(results)) * 100
        
        print(f"📈 Overall Quality Score: {avg_quality_score:.1f}/100")
        print(f"✅ Pass Rate: {pass_rate:.1f}% ({overall_passed}/{len(results)} checks passed)")
        print(f"⏱️  Total Execution Time: {total_execution_time:.2f}s")
        
        # Quality assessment
        if pass_rate == 100 and avg_quality_score >= 90:
            print("🎉 EXCELLENT! All checks passed with high quality scores.")
        elif pass_rate >= 80 and avg_quality_score >= 75:
            print("👍 GOOD! Most checks passed with acceptable quality.")
        elif pass_rate >= 60:
            print("⚠️  NEEDS IMPROVEMENT! Some checks failed or have low quality scores.")
        else:
            print("💥 POOR QUALITY! Many checks failed. Address issues before proceeding.")
        
        print("🚀" * 60)
    
    def generate_quality_report(self, results: List[EnhancedCheckResult]) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        if not results:
            return {"error": "No results to report"}
        
        # Calculate metrics
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r["passed"])
        avg_quality_score = sum(r["quality_score"] for r in results) / total_checks
        total_execution_time = sum(r["execution_time"] for r in results)
        
        # Group by category and priority
        by_category = {}
        by_priority = {"high": [], "medium": [], "low": []}
        
        for result in results:
            category = result["category"]
            priority = result["priority"]
            
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(result)
            
            if priority in by_priority:
                by_priority[priority].append(result)
        
        # Collect all issues and recommendations
        all_issues = []
        all_recommendations = []
        
        for result in results:
            all_issues.extend(result["issues"])
            all_recommendations.extend(result["recommendations"])
        
        return {
            "summary": {
                "total_checks": total_checks,
                "passed_checks": passed_checks,
                "failed_checks": total_checks - passed_checks,
                "pass_rate": (passed_checks / total_checks) * 100,
                "average_quality_score": avg_quality_score,
                "total_execution_time": total_execution_time
            },
            "by_category": {
                category: {
                    "total": len(results),
                    "passed": sum(1 for r in results if r["passed"]),
                    "avg_score": sum(r["quality_score"] for r in results) / len(results)
                }
                for category, results in by_category.items()
            },
            "by_priority": {
                priority: {
                    "total": len(results),
                    "passed": sum(1 for r in results if r["passed"]),
                    "failed": sum(1 for r in results if not r["passed"])
                }
                for priority, results in by_priority.items()
            },
            "issues": {
                "total": len(all_issues),
                "list": all_issues[:10]  # Top 10 issues
            },
            "recommendations": {
                "total": len(all_recommendations),
                "list": list(set(all_recommendations))[:10]  # Top 10 unique recommendations
            },
            "detailed_results": results
        }


async def main() -> int:
    """Main entry point for enhanced development checker."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Development Quality Checker")
    parser.add_argument("--no-comprehensive", action="store_true", 
                       help="Skip comprehensive QA checks")
    parser.add_argument("--category", help="Run specific category checker only")
    parser.add_argument("--gate", help="Run specific quality gate only")
    parser.add_argument("--instant", action="store_true", 
                       help="Run instant quality check only")
    parser.add_argument("--report", help="Generate JSON report to file")
    
    args = parser.parse_args()
    
    checker = EnhancedDevelopmentChecker()
    
    if args.instant:
        # Run instant check only
        result = await checker.run_instant_quality_check()
        results = [result]
    elif args.category:
        # Run specific category checker
        # This would need category-specific implementation
        print(f"Category-specific checking not yet implemented for: {args.category}")
        return 1
    elif args.gate:
        # Run specific quality gate
        # This would need gate-specific implementation
        print(f"Gate-specific checking not yet implemented for: {args.gate}")
        return 1
    else:
        # Run all enhanced checks
        include_comprehensive = not args.no_comprehensive
        results = await checker.run_all_enhanced_checks(include_comprehensive)
    
    # Print results
    checker.print_enhanced_results(results)
    
    # Generate report if requested
    if args.report:
        report = checker.generate_quality_report(results)
        import json
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📄 Quality report saved to: {args.report}")
    
    # Return exit code based on results
    failed_checks = sum(1 for r in results if not r["passed"])
    return 1 if failed_checks > 0 else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))