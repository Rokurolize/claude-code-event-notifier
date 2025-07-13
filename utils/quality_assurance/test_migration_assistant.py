#!/usr/bin/env python3
"""Test migration assistant for integrating existing tests with comprehensive QA system.

This module provides utilities to analyze existing test suites, identify integration
opportunities, and migrate tests to work with the comprehensive quality assurance
framework while maintaining backward compatibility.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, TypedDict
from dataclasses import dataclass

# Add src to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.utils.astolfo_logger import AstolfoLogger


class TestAnalysis(TypedDict):
    """Analysis result for a test file."""
    file_path: str
    test_classes: List[str]
    test_methods: List[str]
    imports: List[str]
    dependencies: List[str]
    category_match: Optional[str]
    integration_opportunities: List[str]
    migration_complexity: str  # "simple", "moderate", "complex"
    recommendations: List[str]


@dataclass 
class MigrationPlan:
    """Migration plan for test integration."""
    source_file: Path
    target_category: str
    target_file: Optional[Path]
    migration_type: str  # "copy", "move", "integrate", "reference"
    dependencies_required: List[str]
    code_changes_needed: List[str]
    integration_points: List[str]
    estimated_effort: str  # "low", "medium", "high"


class TestMigrationAssistant:
    """Assistant for migrating existing tests to comprehensive QA system."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize migration assistant.
        
        Args:
            project_root: Project root directory (auto-detected if None)
        """
        self.logger = AstolfoLogger(__name__)
        
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = project_root
        self.tests_root = project_root / "tests"
        
        # Category mapping rules
        self.category_rules = {
            "discord_integration": {
                "keywords": ["discord", "webhook", "bot", "api", "token", "channel", "message"],
                "imports": ["discord", "requests", "urllib", "http.client"],
                "test_patterns": [r"test.*discord", r"test.*webhook", r"test.*api", r"test.*auth"]
            },
            "content_processing": {
                "keywords": ["format", "embed", "timestamp", "content", "text", "unicode"],
                "imports": ["formatters", "datetime", "timezone"],
                "test_patterns": [r"test.*format", r"test.*embed", r"test.*timestamp", r"test.*content"]
            },
            "data_management": {
                "keywords": ["config", "sqlite", "database", "storage", "session", "cache"],
                "imports": ["sqlite3", "configparser", "json", "pickle"],
                "test_patterns": [r"test.*config", r"test.*db", r"test.*storage", r"test.*session"]
            },
            "quality_validation": {
                "keywords": ["type", "validation", "guard", "safety", "error", "logging"],
                "imports": ["typing", "mypy", "unittest.mock"],
                "test_patterns": [r"test.*type", r"test.*valid", r"test.*error", r"test.*log"]
            },
            "integration_control": {
                "keywords": ["hook", "event", "dispatch", "parallel", "thread", "process"],
                "imports": ["threading", "multiprocessing", "asyncio", "concurrent"],
                "test_patterns": [r"test.*hook", r"test.*event", r"test.*parallel", r"test.*thread"]
            }
        }
        
        # Legacy test structure
        self.legacy_categories = {
            "unit": "Individual component testing",
            "feature": "Feature-level functionality testing", 
            "integration": "Component interaction testing",
            "timestamp": "Timestamp accuracy and timezone testing"
        }
        
        self.logger.info(
            "Test migration assistant initialized",
            context={
                "project_root": str(project_root),
                "tests_root": str(self.tests_root),
                "qa_categories": len(self.category_rules),
                "legacy_categories": len(self.legacy_categories)
            }
        )
    
    def analyze_test_file(self, test_file: Path) -> TestAnalysis:
        """Analyze a test file for migration opportunities.
        
        Args:
            test_file: Path to test file to analyze
            
        Returns:
            Analysis results with migration recommendations
        """
        self.logger.info(f"Analyzing test file: {test_file}")
        
        try:
            content = test_file.read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception as e:
            self.logger.error(f"Failed to parse {test_file}: {e}")
            return self._create_error_analysis(test_file, str(e))
        
        # Extract information
        analysis_data = self._extract_ast_info(tree, content)
        
        # Determine category match
        category_match = self._determine_category_match(analysis_data, test_file)
        
        # Identify integration opportunities
        opportunities = self._identify_integration_opportunities(analysis_data, category_match)
        
        # Assess migration complexity
        complexity = self._assess_migration_complexity(analysis_data, category_match)
        
        # Generate recommendations
        recommendations = self._generate_migration_recommendations(
            analysis_data, category_match, complexity
        )
        
        return TestAnalysis(
            file_path=str(test_file.relative_to(self.project_root)),
            test_classes=analysis_data["test_classes"],
            test_methods=analysis_data["test_methods"],
            imports=analysis_data["imports"],
            dependencies=analysis_data["dependencies"],
            category_match=category_match,
            integration_opportunities=opportunities,
            migration_complexity=complexity,
            recommendations=recommendations
        )
    
    def _extract_ast_info(self, tree: ast.AST, content: str) -> Dict[str, Any]:
        """Extract information from AST and content.
        
        Args:
            tree: Parsed AST
            content: File content
            
        Returns:
            Extracted information dictionary
        """
        info = {
            "test_classes": [],
            "test_methods": [],
            "imports": [],
            "dependencies": [],
            "keywords": [],
            "docstrings": []
        }
        
        for node in ast.walk(tree):
            # Test classes
            if isinstance(node, ast.ClassDef):
                if node.name.endswith("Test") or node.name.startswith("Test"):
                    info["test_classes"].append(node.name)
                    
                    # Extract test methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                            info["test_methods"].append(f"{node.name}.{item.name}")
            
            # Standalone test functions
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    info["test_methods"].append(node.name)
            
            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    info["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    info["imports"].append(node.module)
        
        # Extract keywords from content
        content_lower = content.lower()
        for category, rules in self.category_rules.items():
            for keyword in rules["keywords"]:
                if keyword in content_lower:
                    info["keywords"].append(keyword)
        
        # Extract dependencies
        info["dependencies"] = self._extract_dependencies(content)
        
        return info
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract external dependencies from test content.
        
        Args:
            content: File content
            
        Returns:
            List of detected dependencies
        """
        dependencies = []
        
        # Environment variables
        env_vars = re.findall(r'os\.getenv\(["\']([^"\']+)["\']', content)
        dependencies.extend(env_vars)
        
        # Configuration references
        if "DISCORD_TOKEN" in content or "DISCORD_WEBHOOK_URL" in content:
            dependencies.append("Discord credentials")
        
        if "sqlite" in content.lower() or "database" in content.lower():
            dependencies.append("Database")
        
        if "mock" in content.lower() or "patch" in content.lower():
            dependencies.append("Mocking framework")
        
        return list(set(dependencies))
    
    def _determine_category_match(self, analysis_data: Dict[str, Any], test_file: Path) -> Optional[str]:
        """Determine best matching QA category for test.
        
        Args:
            analysis_data: Extracted test information
            test_file: Test file path
            
        Returns:
            Best matching category or None
        """
        scores = {}
        
        for category, rules in self.category_rules.items():
            score = 0
            
            # Keyword matching
            for keyword in rules["keywords"]:
                if keyword in analysis_data["keywords"]:
                    score += 2
            
            # Import matching
            for import_name in analysis_data["imports"]:
                for rule_import in rules["imports"]:
                    if rule_import in import_name:
                        score += 3
            
            # Pattern matching
            file_content = str(test_file).lower()
            for pattern in rules["test_patterns"]:
                if re.search(pattern, file_content):
                    score += 1
            
            # Method name matching
            for method in analysis_data["test_methods"]:
                for pattern in rules["test_patterns"]:
                    if re.search(pattern, method.lower()):
                        score += 1
            
            if score > 0:
                scores[category] = score
        
        # Return highest scoring category
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _identify_integration_opportunities(
        self, 
        analysis_data: Dict[str, Any], 
        category_match: Optional[str]
    ) -> List[str]:
        """Identify integration opportunities.
        
        Args:
            analysis_data: Extracted test information
            category_match: Matched QA category
            
        Returns:
            List of integration opportunities
        """
        opportunities = []
        
        if category_match:
            opportunities.append(f"Direct integration with {category_match} category")
        
        # Check for timestamp testing
        if any("timestamp" in keyword for keyword in analysis_data["keywords"]):
            opportunities.append("Integration with timestamp accuracy validator")
        
        # Check for Discord testing
        if any("discord" in keyword for keyword in analysis_data["keywords"]):
            opportunities.append("Integration with Discord API testing framework")
        
        # Check for type testing
        if any("type" in keyword for keyword in analysis_data["keywords"]):
            opportunities.append("Integration with type safety validation")
        
        # Check for configuration testing
        if any("config" in keyword for keyword in analysis_data["keywords"]):
            opportunities.append("Integration with configuration validation")
        
        # Check for error handling
        if any("error" in method.lower() for method in analysis_data["test_methods"]):
            opportunities.append("Integration with error handling validation")
        
        return opportunities
    
    def _assess_migration_complexity(
        self, 
        analysis_data: Dict[str, Any], 
        category_match: Optional[str]
    ) -> str:
        """Assess migration complexity.
        
        Args:
            analysis_data: Extracted test information
            category_match: Matched QA category
            
        Returns:
            Complexity level: "simple", "moderate", "complex"
        """
        complexity_score = 0
        
        # Number of test methods
        method_count = len(analysis_data["test_methods"])
        if method_count > 10:
            complexity_score += 2
        elif method_count > 5:
            complexity_score += 1
        
        # Number of dependencies
        dep_count = len(analysis_data["dependencies"])
        if dep_count > 3:
            complexity_score += 2
        elif dep_count > 1:
            complexity_score += 1
        
        # Import complexity
        import_count = len(analysis_data["imports"])
        if import_count > 10:
            complexity_score += 1
        
        # Category match confidence
        if not category_match:
            complexity_score += 3
        
        # Mock usage (indicates complex setup)
        if "Mocking framework" in analysis_data["dependencies"]:
            complexity_score += 1
        
        if complexity_score >= 5:
            return "complex"
        elif complexity_score >= 2:
            return "moderate"
        else:
            return "simple"
    
    def _generate_migration_recommendations(
        self,
        analysis_data: Dict[str, Any],
        category_match: Optional[str],
        complexity: str
    ) -> List[str]:
        """Generate migration recommendations.
        
        Args:
            analysis_data: Extracted test information
            category_match: Matched QA category
            complexity: Migration complexity
            
        Returns:
            List of actionable recommendations
        """
        recommendations = []
        
        if category_match:
            recommendations.append(f"Migrate to {category_match} category for better organization")
        else:
            recommendations.append("Consider creating new specialized test category")
        
        if complexity == "simple":
            recommendations.append("Direct migration possible with minimal changes")
        elif complexity == "moderate":
            recommendations.append("Refactor test setup before migration")
        else:
            recommendations.append("Break down into smaller test modules before migration")
        
        # Specific recommendations based on content
        if "timestamp" in analysis_data["keywords"]:
            recommendations.append("Integrate with TimestampAccuracyValidator for comprehensive validation")
        
        if "discord" in analysis_data["keywords"]:
            recommendations.append("Leverage Discord API testing utilities from QA framework")
        
        if "Mocking framework" in analysis_data["dependencies"]:
            recommendations.append("Consider using QA framework's test utilities instead of manual mocking")
        
        if len(analysis_data["test_methods"]) > 15:
            recommendations.append("Split large test classes into focused test modules")
        
        recommendations.append("Add comprehensive logging using AstolfoLogger")
        recommendations.append("Include quality metrics collection for reporting")
        
        return recommendations
    
    def _create_error_analysis(self, test_file: Path, error: str) -> TestAnalysis:
        """Create error analysis result.
        
        Args:
            test_file: Test file that failed analysis
            error: Error message
            
        Returns:
            Error analysis result
        """
        return TestAnalysis(
            file_path=str(test_file.relative_to(self.project_root)),
            test_classes=[],
            test_methods=[],
            imports=[],
            dependencies=[],
            category_match=None,
            integration_opportunities=[],
            migration_complexity="complex",
            recommendations=[f"Fix parse error: {error}"]
        )
    
    def analyze_all_legacy_tests(self) -> Dict[str, List[TestAnalysis]]:
        """Analyze all legacy test files.
        
        Returns:
            Analysis results grouped by legacy category
        """
        self.logger.info("Analyzing all legacy test files")
        
        results = {}
        
        for category in self.legacy_categories.keys():
            category_path = self.tests_root / category
            
            if not category_path.exists():
                self.logger.warning(f"Legacy category directory not found: {category_path}")
                continue
            
            test_files = list(category_path.glob("test_*.py"))
            category_results = []
            
            for test_file in test_files:
                analysis = self.analyze_test_file(test_file)
                category_results.append(analysis)
            
            results[category] = category_results
            
            self.logger.info(
                f"Analyzed {len(category_results)} test files in {category} category"
            )
        
        return results
    
    def generate_migration_plan(self, analysis_results: Dict[str, List[TestAnalysis]]) -> List[MigrationPlan]:
        """Generate comprehensive migration plan.
        
        Args:
            analysis_results: Analysis results by category
            
        Returns:
            List of migration plans
        """
        self.logger.info("Generating migration plan")
        
        migration_plans = []
        
        for legacy_category, analyses in analysis_results.items():
            for analysis in analyses:
                # Determine migration strategy
                if analysis["category_match"]:
                    target_category = analysis["category_match"]
                    migration_type = "integrate"
                else:
                    # Keep in legacy category but add QA integration
                    target_category = legacy_category
                    migration_type = "reference"
                
                # Determine target file
                source_file = self.project_root / analysis["file_path"]
                
                if migration_type == "integrate":
                    target_file = self.tests_root / target_category / source_file.name
                else:
                    target_file = None
                
                # Assess effort
                if analysis["migration_complexity"] == "simple":
                    effort = "low"
                elif analysis["migration_complexity"] == "moderate":
                    effort = "medium"
                else:
                    effort = "high"
                
                # Code changes needed
                code_changes = []
                if migration_type == "integrate":
                    code_changes.append("Update import paths for new location")
                    code_changes.append("Add AstolfoLogger integration")
                    code_changes.append("Include quality metrics collection")
                
                if "timestamp" in analysis["integration_opportunities"]:
                    code_changes.append("Integrate with TimestampAccuracyValidator")
                
                # Integration points
                integration_points = analysis["integration_opportunities"].copy()
                integration_points.append("Quality assurance reporting")
                integration_points.append("Unified test execution framework")
                
                plan = MigrationPlan(
                    source_file=source_file,
                    target_category=target_category,
                    target_file=target_file,
                    migration_type=migration_type,
                    dependencies_required=analysis["dependencies"],
                    code_changes_needed=code_changes,
                    integration_points=integration_points,
                    estimated_effort=effort
                )
                
                migration_plans.append(plan)
        
        # Sort by effort and category
        effort_order = {"low": 0, "medium": 1, "high": 2}
        migration_plans.sort(key=lambda x: (effort_order.get(x.estimated_effort, 3), x.target_category))
        
        self.logger.info(
            f"Generated {len(migration_plans)} migration plans",
            context={
                "by_effort": {effort: len([p for p in migration_plans if p.estimated_effort == effort])
                            for effort in ["low", "medium", "high"]},
                "by_type": {mtype: len([p for p in migration_plans if p.migration_type == mtype])
                          for mtype in ["integrate", "reference", "copy", "move"]}
            }
        )
        
        return migration_plans
    
    def create_migration_report(
        self, 
        analysis_results: Dict[str, List[TestAnalysis]],
        migration_plans: List[MigrationPlan]
    ) -> Dict[str, Any]:
        """Create comprehensive migration report.
        
        Args:
            analysis_results: Test analysis results
            migration_plans: Migration plans
            
        Returns:
            Comprehensive migration report
        """
        total_tests = sum(len(analyses) for analyses in analysis_results.values())
        
        # Category distribution
        category_distribution = {}
        for plans in migration_plans:
            cat = plans.target_category
            if cat not in category_distribution:
                category_distribution[cat] = 0
            category_distribution[cat] += 1
        
        # Effort distribution
        effort_distribution = {}
        for plan in migration_plans:
            effort = plan.estimated_effort
            if effort not in effort_distribution:
                effort_distribution[effort] = 0
            effort_distribution[effort] += 1
        
        # Integration opportunities
        all_opportunities = []
        for analyses in analysis_results.values():
            for analysis in analyses:
                all_opportunities.extend(analysis["integration_opportunities"])
        
        opportunity_counts = {}
        for opp in all_opportunities:
            opportunity_counts[opp] = opportunity_counts.get(opp, 0) + 1
        
        report = {
            "summary": {
                "total_legacy_tests": total_tests,
                "migration_plans": len(migration_plans),
                "categories_affected": len(category_distribution),
                "integration_opportunities": len(set(all_opportunities))
            },
            "category_distribution": category_distribution,
            "effort_distribution": effort_distribution,
            "integration_opportunities": opportunity_counts,
            "migration_plans": [
                {
                    "source": str(plan.source_file.relative_to(self.project_root)),
                    "target_category": plan.target_category,
                    "migration_type": plan.migration_type,
                    "effort": plan.estimated_effort,
                    "changes_needed": len(plan.code_changes_needed),
                    "integration_points": len(plan.integration_points)
                }
                for plan in migration_plans
            ],
            "recommendations": [
                "Start with low-effort migrations to build confidence",
                "Focus on high-value integration opportunities first", 
                "Maintain backward compatibility during migration",
                "Test migrations thoroughly before committing changes",
                "Update documentation after successful migrations"
            ]
        }
        
        self.logger.info(
            "Migration report created",
            context={
                "total_tests": total_tests,
                "plans": len(migration_plans),
                "opportunities": len(set(all_opportunities))
            }
        )
        
        return report


def main():
    """Main function for test migration assistant."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Test Migration Assistant")
    parser.add_argument("--analyze", action="store_true", 
                       help="Analyze legacy tests for migration opportunities")
    parser.add_argument("--plan", action="store_true",
                       help="Generate migration plan")
    parser.add_argument("--file", help="Analyze specific test file")
    parser.add_argument("--category", help="Analyze specific legacy category")
    parser.add_argument("--report", help="Save report to JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    assistant = TestMigrationAssistant()
    
    if args.file:
        # Analyze single file
        test_file = Path(args.file)
        if not test_file.exists():
            print(f"Error: Test file not found: {test_file}")
            return 1
        
        analysis = assistant.analyze_test_file(test_file)
        
        print(f"Analysis for {analysis['file_path']}:")
        print(f"  Test Methods: {len(analysis['test_methods'])}")
        print(f"  Category Match: {analysis['category_match']}")
        print(f"  Complexity: {analysis['migration_complexity']}")
        print(f"  Opportunities: {len(analysis['integration_opportunities'])}")
        
        if args.verbose:
            print(f"  Integration Opportunities:")
            for opp in analysis['integration_opportunities']:
                print(f"    • {opp}")
            print(f"  Recommendations:")
            for rec in analysis['recommendations']:
                print(f"    • {rec}")
        
        return 0
    
    if args.analyze:
        # Analyze all legacy tests
        if args.category:
            # Single category
            category_path = assistant.tests_root / args.category
            if not category_path.exists():
                print(f"Error: Category not found: {args.category}")
                return 1
            
            test_files = list(category_path.glob("test_*.py"))
            results = {args.category: [assistant.analyze_test_file(f) for f in test_files]}
        else:
            # All categories
            results = assistant.analyze_all_legacy_tests()
        
        print(f"Legacy Test Analysis:")
        for category, analyses in results.items():
            print(f"  {category}: {len(analyses)} test files")
            
            if args.verbose:
                for analysis in analyses:
                    print(f"    {analysis['file_path']}: {analysis['migration_complexity']} complexity")
        
        if args.plan:
            # Generate migration plan
            plans = assistant.generate_migration_plan(results)
            report = assistant.create_migration_report(results, plans)
            
            print(f"\nMigration Plan:")
            print(f"  Total Plans: {len(plans)}")
            print(f"  Effort Distribution: {report['effort_distribution']}")
            print(f"  Target Categories: {list(report['category_distribution'].keys())}")
            
            if args.report:
                with open(args.report, 'w') as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"  Report saved to: {args.report}")
        
        return 0
    
    print("Use --analyze to analyze legacy tests or --file to analyze a specific file")
    return 1


if __name__ == "__main__":
    sys.exit(main())